"""Evaluate the single current control schema with the existing bounded evaluator."""
import copy
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_wtp_contract import SchemaValidator, loads_strict
SCHEMA = json.loads((ROOT / 'engineering/protocol/control-1.schema.json').read_text())

class Validator(SchemaValidator):
    def __init__(self, family):
        super().__init__(SCHEMA)
        self.definition = SCHEMA['$defs'][family]
    def errors(self, instance, schema=None, path='$'):
        selected = self.definition if schema is None else schema
        # JSON Schema anyOf is used only for nullable disjoint core fields.
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
