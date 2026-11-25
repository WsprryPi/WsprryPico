"""Evaluate the single current control schema with the existing bounded evaluator."""
import json
from pathlib import Path
import subprocess
import re
from typing import Any
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from strict_json import ValidationError
SCHEMA = json.loads((ROOT / 'engineering/protocol/control-1.schema.json').read_text())


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
            if "multipleOf" in schema and instance % schema["multipleOf"] != 0:
                errors.append(f"{path}: integer is not a permitted multiple")
            if instance < -2147483648 or instance > 2147483647:
                errors.append(f"{path}: JSON integer exceeds the supported 32-bit range")
        return errors


class Validator(SchemaValidator):
    def __init__(self, family):
        super().__init__(SCHEMA)
        self.definition = SCHEMA['$defs'][family]
    def errors(self, instance, schema=None, path='$'):
        selected = self.definition if schema is None else schema
        # Nullable core fields and overlapping complete/partial update shapes.
        if 'anyOf' in selected:
            if any(not self.errors(instance, variant, path) for variant in selected['anyOf']):
                return []
            return [path + ': no permitted alternative']
        errors = super().errors(instance, selected, path)
        if 'const' in selected and isinstance(instance, bool) != isinstance(selected['const'], bool):
            errors.append(path + ': boolean/number constant mismatch')
        if isinstance(instance, dict) and 'propertyNames' in selected:
            for key in instance:
                errors.extend(self.errors(key, selected['propertyNames'], path + '.' + key))
        if isinstance(instance, dict) and isinstance(selected.get('additionalProperties'), dict):
            properties = selected.get('properties', {})
            for key, value in instance.items():
                if key not in properties:
                    errors.extend(self.errors(value, selected['additionalProperties'], path + '.' + key))
        return errors
    def validate(self, value):
        errors = self.errors(value)
        assert not errors, errors
    def is_valid(self, value):
        return not self.errors(value)
    def iter_errors(self, value):
        return iter(self.errors(value))

def documents(driver, *args):
    text = subprocess.check_output([driver, *args], text=True)
    values = []
    while text.strip():
        text = text.lstrip()
        value, end = json.JSONDecoder().raw_decode(text)
        values.append(value)
        text = text[end:]
    return values

def closed(value, validator):
    validator.validate(value)
    assert validator.errors({**value, 'unknown': True})
    if 'schema' in value:
        assert validator.errors({**value, 'schema': 'unsupported-resource'})
    if 'contract' in value:
        assert validator.errors({**value, 'contract': 'Wsprry-Control/99'})
