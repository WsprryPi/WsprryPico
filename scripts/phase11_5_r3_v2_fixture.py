#!/usr/bin/env python3
"""Hash-bound host-only extended R3 fixture; no USB, CONFIG or RF operation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_network_fixture import Fixture, HOST_BOOT, runtime_budget


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no host, device or network mutations.');return
    require(os.geteuid()==0 and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==HOST_BOOT,
            'Expected root/host boot')
    root=a.root.resolve(strict=True);require(digest(root/'packet.json')==a.packet_sha256,'Fixture packet changed')
    packet=json.loads((root/'packet.json').read_text())
    require(packet['schema']==packet['r3_scope']=='phase11.5-r3-v2-fixture-v1' and packet['root']==str(root) and
            packet['rf_jobs']==packet['flashes']==packet['bootsel_commands']==packet['configuration_writes']==
            packet['wifi_cycles']==packet['heap_probes']==0,'Host-only fixture scope')
    runtime_budget(packet)
    for name,sha in packet['stage_sha256'].items():
        require((root/name).resolve().is_relative_to(root) and digest(root/name)==sha,'Fixture helper changed')
    os.umask(0o077)
    import fcntl
    with (root/'fixture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fixture=Fixture(root)
        try:fixture.setup();fixture.verify()
        except BaseException:
            fixture.cleanup();raise

if __name__=='__main__':main()
