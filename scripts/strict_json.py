"""Strict generic JSON checks shared by Console and diagnostic tools."""
from typing import Any

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
