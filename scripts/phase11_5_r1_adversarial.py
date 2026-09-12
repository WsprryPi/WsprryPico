#!/usr/bin/env python3
"""Offline mutations of a private R1 evidence copy; no device or network access."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import tempfile
from audit_phase11_5_r1 import audit


def without_target_packets(data):
    endian = '<' if data[:4] in (b'\xd4\xc3\xb2\xa1',b'\x4d\x3c\xb2\xa1') else '>'
    output = bytearray(data[:24]); offset = 24
    while offset < len(data):
        size = struct.unpack_from(endian+'I',data,offset+8)[0]
        record = data[offset:offset+16+size]; frame = record[16:]; offset += 16+size
        if len(frame)>=34 and frame[12:14]==b'\x08\x00' and b'\x0a\x4d\x0f\x0a' in (frame[26:30],frame[30:34]):
            continue
        output.extend(record)
    return bytes(output)


def exercise(root):
    root = root.resolve(strict=True)
    audit(root)
    cases = [
        ('failed supervisor', 'r1-result.json', lambda v:v.update(status='FAILED')),
        ('missing quiet interval', 'r1-result.json', lambda v:v['intervals'].pop('r1-quiet-after')),
        ('false retention summary', 'r1-result.json', lambda v:v.update(quiet_delta_bytes=2048)),
        ('changed probe size', 'r1-result.json', lambda v:v['probes'][0].update(bytes=1)),
        ('wrong image', 'packet.json', lambda v:v['images']['physical'].update(sha256='0'*64)),
        ('wrong clock', 'packet.json', lambda v:v.update(selected_physical_clock_hz=150000000)),
        ('wrong native address', 'fixture-time-inhibited.stdout',
         lambda v:v.update(native_resolution='time.local\t192.168.1.54')),
        ('wrong NTP peer', 'fixture-time-inhibited.stdout',
         lambda v:v['ntp'].update(peer=['192.168.1.54',123])),
        ('unsynchronized NTP', 'fixture-time-inhibited.stdout',
         lambda v:v['ntp'].update(reply_hex='e4'+v['ntp']['reply_hex'][2:])),
        ('false operation count', 'management-state.json', lambda v:v['counts'].update(config=27)),
        ('unrestored host', 'host-fixture-state.json', lambda v:v.update(restored=False)),
    ]
    rejected = []
    with tempfile.TemporaryDirectory(prefix='phase115-r1-review-') as temporary:
        copy = Path(temporary)/'evidence'; shutil.copytree(root,copy)
        for name, relative, mutate in cases:
            path=copy/relative;original=path.read_bytes()
            try:
                value=json.loads(original);mutate(value);path.write_text(json.dumps(value)+'\n')
                try: audit(copy)
                except (ValueError,KeyError,FileNotFoundError): rejected.append(name)
                else: raise AssertionError('False acceptance: '+name)
            finally: path.write_bytes(original)
        for name,relative,transform in (
            ('missing mDNS/NTP capture','capture-client.pcap',lambda data:data[:24]),
            ('incomplete final capture record','capture-client.pcap',lambda data:data+b'\x00'),
            ('missing target time exchanges','capture-ap.pcap',without_target_packets),
            ('truncated USB interval','r1-quiet-after.jsonl',lambda data:data[:data.rstrip().rfind(b'\n')+1]),
            ('changed staged helper','scripts/phase11_5_idle_observer.py',lambda data:data+b'\n')):
            path=copy/relative;original=path.read_bytes()
            try:
                path.write_bytes(transform(original))
                try: audit(copy)
                except (ValueError,KeyError,FileNotFoundError): rejected.append(name)
                else: raise AssertionError('False acceptance: '+name)
            finally: path.write_bytes(original)
        audit(copy)
    return dict(original='PASS',rejected_mutations=rejected,repeated_original='PASS',hardware_access=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    print(json.dumps(exercise(parser.parse_args().root),indent=2))
