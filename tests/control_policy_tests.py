"""Meaningful lifecycle boundaries without changing the actual release policy."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_control_policy import check_files, schema_digest, validate
policy, schema = check_files()
original_policy = copy.deepcopy(policy)
# The fixture remains prerelease even after the real project transitions.
policy = {**policy, 'phase': 'prerelease', 'first_release': None, 'schema_sha256': None}
def rejected(p, s, stable=False):
    try: validate(p, s, stable)
    except ValueError: return
    raise AssertionError('Invalid lifecycle transition accepted')
changed = copy.deepcopy(schema)
changed['$defs']['capabilities']['properties']['max_body_bytes']['maximum'] = 16384
validate(policy, changed) # Even breaking current content evolves before first release.
added = copy.deepcopy(schema)
added['resource_descriptors']['new_feature'] = {'schema': 'new-feature', 'path': '/api/control/v1/new-feature'}
added['management_routes']['GET'].append('new-feature')
validate(policy, added) # New unversioned resources remain available during prerelease.
for key, value in [('major', 2), ('contract', 'Wsprry-Control/2'), ('namespace', '/api/control/v2/'), ('schema_id', 'urn:wsprry:control:2'), ('public_prefix', '/api/consumer/v2/read/')]:
    rejected({**policy, key: value}, schema)
for key, value in [('contract', 'Wsprry-Control/2'), ('namespace', '/api/control/v2/'), ('$id', 'urn:wsprry:control:2'), ('public_prefix', '/api/consumer/v2/read/')]:
    rejected(policy, {**schema, key: value})
for mutation in ['route', 'descriptor', 'selector', 'suffix-selector', 'suffix-schema', 'enum-schema']:
    bad = copy.deepcopy(schema)
    if mutation == 'route': bad['management_routes']['GET'].append('application/2')
    if mutation == 'descriptor': bad['resource_descriptors']['gpio_drive']['schema'] = 'gpio-drive/2'
    if mutation == 'suffix-selector': bad['resource_descriptors']['gpio_drive_v2'] = bad['resource_descriptors']['gpio_drive']
    if mutation == 'suffix-schema': bad['$defs']['application']['$defs']['station_read']['properties']['schema']['const'] = 'station-v2'
    if mutation == 'enum-schema': bad['$defs']['application']['$defs']['station_read']['properties']['schema'] = {'enum': ['station/2']}
    if mutation == 'selector': bad['$defs']['capabilities']['properties']['api_version'] = {'const': 1}
    rejected(policy, bad)
for mutation in ['public-generation', 'descriptor-selector', 'progress-selector', 'oneof-selector', 'wire-drift', 'document-contract', 'foreign-namespace']:
    bad = copy.deepcopy(schema)
    if mutation == 'public-generation': bad['public_resources'].append('application/2')
    if mutation == 'descriptor-selector': bad['resource_descriptors']['gpio_drive']['update_schema'] = 'config-update/2'
    if mutation == 'progress-selector': bad['resource_descriptors']['amplifier_enable']['progress_schema'] = 'progress-v2'
    if mutation == 'oneof-selector': bad['$defs']['application']['$defs']['station_read']['properties']['schema'] = {'oneOf': [{'const': 'station'}, {'const': 'station/2'}]}
    if mutation == 'foreign-namespace': bad['resource_descriptors']['gpio_drive']['read'] = '/api/v2/gpio-drive'
    if mutation == 'document-contract': bad['$defs']['management']['properties']['contract'] = {'const': 'Wsprry-Control/2'}
    if mutation == 'wire-drift': bad['$defs']['udp-logging-capabilities']['oneOf'][0]['properties']['wire_schema'] = {'const': 'wsprry-udp/2'}
    rejected(policy, bad)
for mutation in ['unknown-method', 'duplicate', 'outside-producer', 'wrong-method', 'generation', 'wrong-type', 'unknown-role']:
    bad = copy.deepcopy(schema)
    role = bad['client_routes']['pi_management']
    if mutation == 'unknown-method': role['DELETE'] = ['config']
    if mutation == 'duplicate': role['GET'].append(role['GET'][0])
    if mutation == 'outside-producer': role['GET'].append('unknown-resource')
    if mutation == 'wrong-method': role['POST'].append('hardware')
    if mutation == 'generation':
        bad['management_routes']['GET'].append('application/2')
        role['GET'].append('application/2')
    if mutation == 'wrong-type': role['GET'] = [None]
    if mutation == 'unknown-role': bad['client_routes']['pi_management_v2'] = role
    rejected(policy, bad)
for mutation in ['missing','extra','foreign-read','wrong-read','header']:
    bad = copy.deepcopy(schema)
    adapter = bad['controller_adapter']
    if mutation == 'missing': del adapter['reconciliation_reads']['wifi']
    if mutation == 'extra': adapter['reconciliation_reads']['jobs'] = 'configuration'
    if mutation == 'foreign-read': adapter['reconciliation_reads']['wifi'] = 'https://untrusted.invalid'
    if mutation == 'wrong-read': adapter['reconciliation_reads']['restart'] = 'wifi'
    if mutation == 'header': adapter['headers']['recovery'] = 'Location'
    rejected(policy, bad)
for mutation in ['missing-method', 'extra-method', 'duplicate-route', 'foreign-route', 'wrong-method', 'missing-document']:
    bad = copy.deepcopy(schema)
    adapter = bad['controller_adapter']
    if mutation == 'missing-method': del adapter['host_routes']['PUT']
    if mutation == 'extra-method': adapter['host_routes']['DELETE'] = ['host/configuration-recovery']
    if mutation == 'duplicate-route': adapter['host_routes']['GET'].append('host/readiness')
    if mutation == 'foreign-route': adapter['host_routes']['GET'][0] = 'https://untrusted.invalid/readiness'
    if mutation == 'wrong-method': adapter['host_routes']['POST'].append('host/readiness')
    if mutation == 'missing-document': adapter['documents'].remove('configuration-recovery-save')
    rejected(policy, bad)
validate(policy, schema) # Log wire, host storage and owner-read boundaries remain valid.
from check_control_policy import pi_resource_descriptors
for field in ['configuration','management']:
    changed_policy=copy.deepcopy(schema)
    changed_policy['pi_management_policies'][field]['revision']='f'*40
    assert pi_resource_descriptors(changed_policy)!=pi_resource_descriptors(schema)
changed_shape=copy.deepcopy(schema)
changed_shape['$defs']['pi-config']['properties']['CW']['properties']['Message']['maxLength']=1024
assert pi_resource_descriptors(changed_shape)!=pi_resource_descriptors(schema)
for invalid in [None,[],{}, {'revision':'f'*40,'paths':[{}]}]:
    bad=copy.deepcopy(schema);bad['pi_management_policies']['configuration']=invalid
    rejected(policy,bad)
rejected(policy, schema, True)
released = {**policy, 'phase': 'released', 'first_release': '1.0.0', 'schema_sha256': schema_digest(schema)}
validate(released, schema, True)
rejected(released, changed)
rejected({**released, 'first_release': '1.0.0-beta.1'}, schema)
rejected({**policy, 'schema_sha256': schema_digest(schema)}, schema)
with tempfile.TemporaryDirectory() as directory:
    p, s = Path(directory) / 'policy.json', Path(directory) / 'schema.json'
    p.write_text(json.dumps(policy)); s.write_text(json.dumps(schema))
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_control_policy.py'), '--schema', str(s), '--policy', str(p), '--record-first-release', '1.0.0'], check=True)
    recorded = json.loads(p.read_text())
    assert recorded == released
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_control_policy.py'), '--schema', str(s), '--policy', str(p), '--stable-release'], check=True)
assert check_files()[0] == original_policy # No release was performed by this test.
print('PASS prerelease evolution, frozen identifiers, forbidden resource generations, stable gate and released digest immutability')
