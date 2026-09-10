#!/usr/bin/env python3
"""Offline mutations of a completed physical case; original files are never edited."""
import argparse
import json
from pathlib import Path
import tempfile
import struct
import re
from phase11_4_three_radio_audit import audit, has_answer, pcap


def assess(root, resumed_sessions=False):
    original = audit(root, resumed_sessions)
    results = []
    def trial(label, relative, edit, extra=None):
        with tempfile.TemporaryDirectory(prefix='three-radio-audit-') as name:
            target = Path(name)
            for p in root.rglob('*'):
                q = target / p.relative_to(root)
                if p.is_dir():
                    q.mkdir(exist_ok=True)
                else:
                    q.symlink_to(p.resolve())
            p = target / relative
            data = p.read_bytes()
            p.unlink()
            p.write_bytes(edit(data))
            for relative_extra, change in (extra or {}).items():
                p = target / relative_extra
                data = p.read_bytes()
                p.unlink()
                p.write_bytes(change(data))
            try:
                audit(target, resumed_sessions)
            except ValueError as e:
                results.append(dict(case=label, rejected=True, reason=str(e)))
            else:
                raise RuntimeError('Adversarial evidence admitted: ' + label)
    def events(edit):
        def apply(data):
            values = [json.loads(line) for line in data.splitlines()]
            edit(values)
            return ('\n'.join(json.dumps(v) for v in values) + '\n').encode()
        return apply
    def first(values, kind, predicate=lambda r: True):
        return next(r for r in values if r['kind'] == kind and predicate(r))
    ev = 'events.jsonl'
    trial('different boot', ev, events(lambda r: first(r,'INFO')['value']['status'].__setitem__('boot_id','wrong')))
    trial('active output', ev, events(lambda r: first(r,'INFO')['value']['status'].__setitem__('output_active',True)))
    trial('wrong firmware', ev, events(lambda r: first(r,'INFO')['value'].__setitem__('revision','other')))
    trial('recovery boot', ev, events(lambda r: first(r,'INFO')['value'].__setitem__('recovery_boot',True)))
    trial('network allocation failure', ev, events(lambda r: first(r,'INFO')['value'].__setitem__('tls_allocation_failures',1)))
    trial('observer fault retained', ev, events(lambda r: first(r,'CASE_PASS').__setitem__('kind','OBSERVER_FAILURE')))
    trial('second peer lookup timeout', ev, events(lambda r: first(r,'NSS',lambda x:x['value']['peer']==2 and x['value']['label']=='off-3')['value'].__setitem__('exit',124)))
    trial('alternate native address', ev, events(lambda r: first(r,'NSS',lambda x:x['value']['label'].startswith('recovery-'))['value'].__setitem__('stdout','10.77.14.20 STREAM other.local\n')))
    trial('missing second peer recovery lookup', ev, events(lambda r:r.remove(first(r,'NSS',lambda x:x['value']['peer']==2 and x['value']['label']=='recovery-0'))))
    trial('missing repeated authentication', ev, events(lambda r:r.remove(first(r,'AUTH',lambda x:x['value']['peer']==2 and x['value']['label']=='recovery-0'))))
    trial('shared resolver namespace', ev, events(lambda r:first(r,'PEER_STATES')['value']['2'].__setitem__('mountns',first(r,'PEER_STATES')['value']['1']['mountns'])))
    trial('drifted client AP', ev, events(lambda r:first(r,'PEER_STATES_FINAL')['value']['1'].__setitem__('link','Connected to other')))
    trial('late local recovery', ev, events(lambda r:first(r,'local_active')['value'].__setitem__('seconds_after_on',41)))
    trial('wrong WTP owner', 'peer1-recovery-0/events.jsonl', events(lambda r:first(r,'client_received',lambda x:x['value']['op']=='STATUS')['value']['body'].__setitem__('owner_id','1'*32)))
    trial('wrong authenticated certificate', 'peer2-recovery-0/events.jsonl', events(lambda r:first(r,'CLIENT_PASS')['value'].__setitem__('fingerprint','wrong')))
    trial('missing authenticated WTP session', 'peer2-recovery-0/events.jsonl', events(lambda r:r.remove(first(r,'client_tls'))))
    if resumed_sessions:
        def churn(records):
            for row in records:
                if row['kind'] in ('client_request', 'client_received'):
                    row['value']['session_id'] = '0' * 31 + '1'
        trial('new session per poll', 'peer2-recovery-0/events.jsonl', events(churn))
    trial('wrong HTTPS boot', 'peer1-recovery-0/events.jsonl', events(lambda r:first(r,'CLIENT_PASS')['value']['status']['job'].__setitem__('boot_id','wrong')))
    trial('missing USB wire byte', 'usb-wire.bin', lambda data:data[:-1])
    trial('USB framing garbage', 'usb-wire.bin', lambda data:b'x'+data)
    for label in ('ap','peer1','peer2'):
        trial(label+' truncated mDNS capture', label+'-mdns.pcap', lambda data:data[:-1])
        trial(label+' dropped capture packets', label+'-mdns.log', lambda data:data.replace(b'0 packets dropped by kernel',b'1 packets dropped by kernel'))
    packets = pcap(root / 'peer2-mdns.pcap')
    index = next(i for i, packet in enumerate(packets) if has_answer(packet, 0))
    def remove_goodbye(data):
        output, offset, count = bytearray(data[:24]), 24, 0
        while offset < len(data):
            size = struct.unpack_from('<I', data, offset + 8)[0]
            end = offset + 16 + size
            if count != index:
                output.extend(data[offset:end])
            offset, count = end, count + 1
        return bytes(output)
    trial('missing goodbye with valid capture structure and counts', 'peer2-mdns.pcap', remove_goodbye,
          {'peer2-mdns.log': lambda data: re.sub(rb'\d+ packets captured',
               str(len(packets)-1).encode() + b' packets captured', data)})
    reassessed = audit(root, resumed_sessions)
    assert reassessed == original
    return dict(refusals=results, count=len(results), final_reassessment=reassessed,
                new_actionable_findings=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('--resumed-sessions', action='store_true')
    args = p.parse_args()
    print(json.dumps(assess(args.root.resolve(), args.resumed_sessions), indent=2))
