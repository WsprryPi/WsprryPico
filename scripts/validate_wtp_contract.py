#!/usr/bin/env python3
"""Validate the WTP/1 contract artifacts without third-party dependencies."""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_DIR = ROOT / "docs" / "protocol"
SCHEMA_PATH = PROTOCOL_DIR / "wtp-1.schema.json"
CONTRACT_PATH = PROTOCOL_DIR / "wtp-1-contract.json"
VECTORS_PATH = PROTOCOL_DIR / "test-vectors" / "wtp-1.json"
SPEC_PATH = PROTOCOL_DIR / "WTP.md"
U64_MAX = (1 << 64) - 1


class ValidationError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def reject_float(value: str) -> None:
    raise ValidationError(f"floating-point number {value!r} is forbidden")


def reject_constant(value: str) -> None:
    raise ValidationError(f"non-finite number {value!r} is forbidden")


def bounded_int(value: str) -> int:
    parsed = int(value)
    if parsed < -2147483648 or parsed > 2147483647:
        raise ValidationError(f"JSON integer {value!r} exceeds WTP/1 range")
    return parsed


def loads_strict(source: str) -> Any:
    value = json.loads(
        source,
        object_pairs_hook=unique_object,
        parse_int=bounded_int,
        parse_float=reject_float,
        parse_constant=reject_constant,
    )
    if json_depth(value) > 16:
        raise ValidationError("JSON nesting exceeds WTP/1 maximum of 16")
    validate_unicode(value)
    return value


def json_depth(value: Any) -> int:
    if isinstance(value, dict):
        return 1 + max((json_depth(child) for child in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((json_depth(child) for child in value), default=0)
    return 0


def validate_unicode(value: Any) -> None:
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValidationError("JSON contains an unpaired Unicode surrogate") from error
    elif isinstance(value, dict):
        for key, child in value.items():
            validate_unicode(key)
            validate_unicode(child)
    elif isinstance(value, list):
        for child in value:
            validate_unicode(child)


def load_json(path: Path) -> Any:
    return loads_strict(path.read_text(encoding="utf-8"))


def crc32c(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x82F63B78 if crc & 1 else 0)
    return crc ^ 0xFFFFFFFF


def frame(payload: bytes) -> bytes:
    return b"WTPF" + bytes((1, 1)) + b"\x00\x00" + struct.pack(">II", len(payload), crc32c(payload)) + payload


def json_type_matches(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    raise ValidationError(f"validator does not support schema type {expected!r}")


class SchemaValidator:
    """Small Draft 2020-12 evaluator for keywords used by this contract."""

    def __init__(self, root: dict[str, Any]):
        self.root = root

    def resolve(self, reference: str) -> dict[str, Any]:
        if not reference.startswith("#/"):
            raise ValidationError(f"external schema reference {reference!r} is forbidden")
        node: Any = self.root
        for part in reference[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        if not isinstance(node, dict):
            raise ValidationError(f"schema reference {reference!r} is not an object")
        return node

    def errors(self, instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
        errors: list[str] = []
        if "$ref" in schema:
            return self.errors(instance, self.resolve(schema["$ref"]), path)

        if "allOf" in schema:
            for child in schema["allOf"]:
                errors.extend(self.errors(instance, child, path))
        if "oneOf" in schema:
            matches = sum(not self.errors(instance, child, path) for child in schema["oneOf"])
            if matches != 1:
                errors.append(f"{path}: expected exactly one oneOf match, got {matches}")
        if "not" in schema and not self.errors(instance, schema["not"], path):
            errors.append(f"{path}: matched forbidden schema")

        condition = schema.get("if")
        if condition is not None:
            branch = "then" if not self.errors(instance, condition, path) else "else"
            if branch in schema:
                errors.extend(self.errors(instance, schema[branch], path))

        if "const" in schema and instance != schema["const"]:
            errors.append(f"{path}: expected constant {schema['const']!r}")
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{path}: value is not in enum")

        expected_type = schema.get("type")
        if expected_type is not None and not json_type_matches(instance, expected_type):
            errors.append(f"{path}: expected {expected_type}")
            return errors

        if isinstance(instance, dict):
            required = schema.get("required", [])
            for name in required:
                if name not in instance:
                    errors.append(f"{path}: missing required member {name!r}")
            properties = schema.get("properties", {})
            for name, value in instance.items():
                if name in properties:
                    errors.extend(self.errors(value, properties[name], f"{path}.{name}"))
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{path}: unknown member {name!r}")
            if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
                errors.append(f"{path}: too many members")

        if isinstance(instance, list):
            if len(instance) < schema.get("minItems", 0):
                errors.append(f"{path}: too few items")
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                errors.append(f"{path}: too many items")
            if schema.get("uniqueItems"):
                encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in instance]
                if len(encoded) != len(set(encoded)):
                    errors.append(f"{path}: items are not unique")
            if "items" in schema:
                for index, value in enumerate(instance):
                    errors.extend(self.errors(value, schema["items"], f"{path}[{index}]"))

        if isinstance(instance, str):
            if len(instance) < schema.get("minLength", 0):
                errors.append(f"{path}: string is too short")
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                errors.append(f"{path}: string is too long")
            if "x-maxUtf8Bytes" in schema and len(instance.encode("utf-8")) > schema["x-maxUtf8Bytes"]:
                errors.append(f"{path}: UTF-8 representation is too long")
            if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
                errors.append(f"{path}: string does not match pattern")
            if "x-maximum" in schema:
                try:
                    above_maximum = int(instance) > int(schema["x-maximum"])
                except ValueError:
                    above_maximum = False
                if above_maximum:
                    errors.append(f"{path}: decimal string exceeds maximum")

        if isinstance(instance, int) and not isinstance(instance, bool):
            if instance < schema.get("minimum", instance):
                errors.append(f"{path}: integer is below minimum")
            if instance > schema.get("maximum", instance):
                errors.append(f"{path}: integer is above maximum")
            if instance < -2147483648 or instance > 2147483647:
                errors.append(f"{path}: JSON integer exceeds WTP/1 range")
        return errors


def validate_message_semantics(message: dict[str, Any]) -> list[str]:
    if message.get("type") == "response" and message.get("op") == "CAPS" and message.get("ok") is True:
        errors = []
        if int(message["body"]["minimum_arm_lead_ns"]) > int(message["body"]["maximum_arm_ahead_ns"]):
            errors.append("$.body: minimum arm lead exceeds maximum arm horizon")
        for index, frequency_range in enumerate(message["body"]["frequency_ranges"]):
            if int(frequency_range["minimum_nhz"]) > int(frequency_range["maximum_nhz"]):
                errors.append(f"$.body.frequency_ranges[{index}]: minimum exceeds maximum")
        return errors
    if message.get("type") != "request" or message.get("op") != "LOAD":
        return []
    job = message["body"]
    events = job["events"]
    expected_offset = 0
    errors: list[str] = []
    for index, event in enumerate(events):
        offset = int(event["offset_ns"])
        duration = int(event["duration_ns"])
        if offset != expected_offset:
            errors.append(f"$.body.events[{index}]: expected offset {expected_offset}")
        if expected_offset > U64_MAX - duration:
            errors.append(f"$.body.events[{index}]: unsigned 64-bit duration overflow")
            break
        expected_offset += duration
    if expected_offset != int(job["total_duration_ns"]):
        errors.append("$.body: event end does not equal total_duration_ns")
    if int(job["total_duration_ns"]) > 86400000000000:
        errors.append("$.body.total_duration_ns: exceeds WTP/1 maximum")
    return errors


def walk_references(value: Any) -> list[str]:
    references: list[str] = []
    if isinstance(value, dict):
        if "$ref" in value:
            references.append(value["$ref"])
        for child in value.values():
            references.extend(walk_references(child))
    elif isinstance(value, list):
        for child in value:
            references.extend(walk_references(child))
    return references


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    contract = load_json(CONTRACT_PATH)
    vectors = load_json(VECTORS_PATH)
    specification = SPEC_PATH.read_text(encoding="utf-8")
    validator = SchemaValidator(schema)
    failures: list[str] = []

    if crc32c(b"123456789") != 0xE3069283:
        failures.append("CRC-32C implementation fails the standard check value")

    for reference in walk_references(schema):
        try:
            validator.resolve(reference)
        except (KeyError, ValidationError) as error:
            failures.append(f"schema reference {reference}: {error}")

    for case in vectors["schema_cases"]:
        errors = validator.errors(case["message"], schema)
        if not errors:
            errors.extend(validate_message_semantics(case["message"]))
        actual = not errors
        if actual != case["valid"]:
            failures.append(f"schema case {case['name']!r}: expected valid={case['valid']}, errors={errors}")

    for case in vectors["raw_json_cases"]:
        try:
            value = loads_strict(case["json"])
            actual = isinstance(value, dict)
        except (json.JSONDecodeError, ValidationError):
            actual = False
        if actual != case["valid"]:
            failures.append(f"raw JSON case {case['name']!r}: expected valid={case['valid']}")

    for case in vectors["framing_cases"]:
        payload = case["payload_utf8"].encode("utf-8")
        actual_crc = f"{crc32c(payload):08x}"
        actual_frame = frame(payload).hex()
        if actual_crc != case["crc32c_hex"]:
            failures.append(f"framing case {case['name']!r}: CRC expected {case['crc32c_hex']}, got {actual_crc}")
        if actual_frame != case["frame_hex"]:
            failures.append(f"framing case {case['name']!r}: frame bytes differ")

    transitions = contract["transitions"]
    for case in vectors["transition_cases"]:
        actual = case["to"] in transitions[case["from"]]
        if actual != case["valid"]:
            failures.append(f"transition {case['from']} -> {case['to']}: expected valid={case['valid']}")

    defined = set(schema["$defs"]["errorCode"]["enum"])
    if defined != set(contract["errors"]):
        failures.append("schema and contract error-code sets differ")
    request_variants = schema["$defs"]["request"]["allOf"][1]["oneOf"]
    request_operations = {variant["properties"]["op"]["const"] for variant in request_variants}
    if set(contract["operations"]) != request_operations:
        failures.append("schema and contract operation sets differ")
    success_variants = schema["$defs"]["successResponse"]["oneOf"]
    success_operations: set[str] = set()
    for variant in success_variants:
        operation_schema = variant["properties"]["op"]
        success_operations.update(operation_schema.get("enum", [operation_schema.get("const")]))
    success_operations.discard(None)
    if set(contract["operations"]) != success_operations:
        failures.append("success-response and contract operation sets differ")
    if set(contract["states"]) != set(schema["$defs"]["state"]["enum"]):
        failures.append("schema and contract state sets differ")
    for token in contract["operations"] + contract["errors"]:
        if f"`{token}`" not in specification:
            failures.append(f"specification does not name {token}")
    if contract["framing"]["max_json_depth"] != 16:
        failures.append("contract JSON-depth limit differs from validator")
    framing = contract["framing"]
    expected_framing = {
        "magic_hex": "57545046", "version": 1, "encoding_json": 1,
        "flags": 0, "header_bytes": 16, "max_payload_bytes": 65536,
    }
    for key, expected in expected_framing.items():
        if framing[key] != expected:
            failures.append(f"contract framing value {key} differs from validator")
    if contract["job"]["modes"] != schema["$defs"]["mode"]["enum"]:
        failures.append("schema and contract mode lists differ")
    if contract["clock"]["max_arm_ahead_ns"] != "604800000000000":
        failures.append("contract arm horizon differs from schema policy")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "WTP/1 contract valid: "
        f"{len(vectors['schema_cases'])} schema cases, "
        f"{len(vectors['raw_json_cases'])} raw JSON cases, "
        f"{len(vectors['framing_cases'])} framing case, and "
        f"{len(vectors['transition_cases'])} transition cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
