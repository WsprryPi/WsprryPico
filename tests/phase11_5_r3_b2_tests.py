"""Adversarial mutations of complete B2 target evidence."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_phase11_5_r3_b2 import audit


@unittest.skipUnless(os.environ.get('PHASE115_R3_B2_EVIDENCE'), 'Private B2 archive not provided')
class B2Tests(unittest.TestCase):
    def test_intact_independent_acceptance_and_adversarial_mutations(self):
        original = Path(os.environ['PHASE115_R3_B2_EVIDENCE'])
        expected = audit(original)
        self.assertEqual(expected['accepted_b2_pressure_cases'], 14)
        self.assertFalse(expected['family_closed'])
        for mutation in ('nft-address', 'nft-length', 'nft-chain', 'nft-counter-bytes', 'nft-extra-rule',
                         'filter-too-early', 'filter-removed-early', 'deferred-flight-size', 'alert-identity',
                         'pressure-epoch', 'tls-peer', 'summary-counter', 'raw-capture-truncation',
                         'observer-summary', 'supervisor-restoration', 'helper-changed'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / 'evidence'; shutil.copytree(original, root)
                case = root / 'tls-a1'
                if mutation.startswith('nft-') or mutation in ('filter-too-early', 'filter-removed-early',
                        'deferred-flight-size', 'alert-identity', 'pressure-epoch', 'tls-peer', 'summary-counter'):
                    path = case / 'pressure.jsonl'
                    rows = [json.loads(s) for s in path.read_text().splitlines()]
                    if mutation.startswith('nft-'):
                        row = next(r for r in rows if r['kind'] == 'ack_filter_counters')
                        value = json.loads(row['value']['raw_json'])
                        rule = next(x['rule'] for x in value['nftables'] if 'rule' in x)
                        if mutation == 'nft-address': rule['expr'][1]['match']['right'] = '192.168.1.54'
                        elif mutation == 'nft-length': rule['expr'][6]['match']['right'] += 1
                        elif mutation == 'nft-chain': rule['chain'] = 'forward'
                        elif mutation == 'nft-counter-bytes': rule['expr'][8]['counter']['bytes'] += 1
                        else: value['nftables'].append({'rule': rule})
                        row['value']['raw_json'] = json.dumps(value)
                    elif mutation == 'filter-too-early':
                        row = next(r for r in rows if r['kind'] == 'server_flight_complete')
                        row['monotonic_ns'] += 5000000000
                    elif mutation == 'filter-removed-early':
                        row = next(r for r in rows if r['kind'] == 'ack_filter_removed')
                        row['monotonic_ns'] -= 5000000000
                    elif mutation == 'deferred-flight-size':
                        next(r for r in rows if r['kind'] == 'server_flight_complete')['value']['deferred_client_bytes'] += 1
                    elif mutation == 'alert-identity':
                        next(r for r in rows if r['kind'] == 'fatal_alert')['value']['alert'] = 42
                    elif mutation == 'pressure-epoch': rows[1]['value']['launch_epoch'] += 1
                    elif mutation == 'tls-peer': next(r for r in rows if r['kind'] == 'tls')['value']['peer_sha256'] = '0' * 64
                    else: rows[5]['value']['transport']['timeouts'] += 1
                    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
                elif mutation == 'raw-capture-truncation':
                    path = case / 'transport.pcap'; path.write_bytes(path.read_bytes()[:-1])
                elif mutation == 'observer-summary':
                    path = case / 'usb-health.jsonl'
                    rows = [json.loads(s) for s in path.read_text().splitlines()]
                    next(r for r in rows if r['kind'] == 'info')['value']['value']['heap_allocated_bytes'] += 1
                    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
                elif mutation == 'helper-changed':
                    path = root / 'scripts/phase11_5_r3_transport_pressure.py'; path.write_text(path.read_text() + '\n')
                else:
                    path = root / 'retained-result.json'; value = json.loads(path.read_text())
                    value['host_restored'] = False; path.write_text(json.dumps(value))
                with self.assertRaises((ValueError, KeyError, StopIteration)):
                    audit(root)
        self.assertEqual(audit(original), expected)


if __name__ == '__main__':
    unittest.main()
