"""Current selector schemas against production documents."""
import sys
from control_schema_support import Validator, documents, closed
families=['filter-selector-capabilities','filter-selector-resource','filter-selector','filter-selector-resource']
for value,family in zip(documents(sys.argv[1],'--documents'),families,strict=True):
    closed(value,Validator(family))
print('PASS selector capability, readback and request schemas')
