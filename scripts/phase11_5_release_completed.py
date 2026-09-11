#!/usr/bin/env python3
"""Opt-in release of the one reconciled completed A3 job; retain its terminal record."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import re
import time

from phase11_5_device_fixture import DeviceFixture
from phase11_5_inventory import exclusive_port,require
from phase11_5_pilot import Peer,SERIAL,DEVICE,check_rf_observation
from phase11_5_pilot_supervisor import idle,finished

BOOT='c282a09bdc59600f588a7abe5675e633'
JOB='926a539c60a48ccda6960d7b3781d707'


def admit(status,expected=None):
    job=JOB if expected is None else expected['job_id']
    require(expected is None or status==expected,'Reconciled status changed')
    require(status['boot_id']==BOOT and status['state']=='complete' and
            status['output_active'] is False and status['owner_id'] is None and
            status['job_id']==job and 1<=len(status['terminal_records'])<=8 and
            (expected is not None or len(status['terminal_records'])==1),
            'Exact completed, inactive, unowned job required')
    require(any(r['job_id']==job for r in status['terminal_records']) and
            all(r['state']=='complete' and r['output_active'] is False and 'error' not in r
                for r in status['terminal_records']),'Completed record differs')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--run',action='store_true')
    parser.add_argument('--baseline',type=Path);parser.add_argument('--baseline-sha256')
    parser.add_argument('--attempt',default='')
    args=parser.parse_args()
    if not args.run:print('Plan only; no hardware or file access');return
    require(os.geteuid()==0,'wspr5 root required');os.umask(0o077)
    root=args.root.resolve(strict=True);d=DeviceFixture(root);d.verify_helpers()
    require(not args.attempt or re.fullmatch('[a-z0-9-]{1,32}',args.attempt),'Invalid release attempt')
    label='completed-release'+('-'+args.attempt if args.attempt else '')
    expected=None
    if args.baseline:
        path=args.baseline.resolve(strict=True)
        require(args.attempt and path.is_relative_to(root) and
                hashlib.sha256(path.read_bytes()).hexdigest()==args.baseline_sha256,'Reconciled baseline changed')
        expected=finished(path,'READ_ONLY_INVENTORY')['wtp']['STATUS'];admit(expected,expected)
    require(d.state['boot']==BOOT and d.state['kind']=='physical' and not d.state.get('pending') and
            time.monotonic_ns()+180_000_000_000<d.state['deadline_monotonic_ns'],'Lifecycle admission')
    current=d.inventory(label+'-before');admit(current['wtp']['STATUS'],expected)
    info=current['info'];require(info['revision']=='8fb3894253ef' and info['device_id']==DEVICE and
        info['system_clock_hz']==138000000 and info['rf_render_in_ram'] is True and
        all(info[k]==0 for k in ('fault_stage','fault_status','fault_hash','fault_pc')) and
        info['status']['enabled'] is False and info['status']['last_error'] is None,'Firmware/configuration admission')
    check_rf_observation(info)
    history=current['wtp']['STATUS']['terminal_records'];end=time.monotonic()+30;owner=secrets.token_hex(16)
    with (root/(label+'.jsonl')).open('x') as log:
        def emit(kind,value):
            log.write(json.dumps(dict(kind=kind,value=value,monotonic_ns=time.monotonic_ns()))+'\n')
            log.flush();os.fsync(log.fileno())
        def checkpoint():require(time.monotonic()<end,'Release packet deadline')
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
            peer=Peer(fd,emit,checkpoint,BOOT)
            hello=peer.request('HELLO',dict(versions=['WTP/1'],client_name='phase11-5-completed-release',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==BOOT,'HELLO identity')
            admit(peer.request('STATUS'),current['wtp']['STATUS'])
            lease=peer.request('CLAIM',dict(owner_id=owner,lease_ms=60000))
            require(lease['owner_id']==owner and lease['granted_lease_ms']==60000,'Exact cleanup lease')
            peer.request('RELEASE')
            after=peer.request('STATUS')
            require(after['boot_id']==BOOT and after['state']=='empty' and after['output_active'] is False and
                    after['owner_id'] is None and after['job_id'] is None and
                    after['terminal_records']==history,'Release or retained history differs')
            emit('released',after)
    final=d.check_current(label+'-after');idle(final)
    require(final['wtp']['STATUS']['terminal_records']==history,'Final retained history differs')
    print('Released completed current job; exact terminal record retained; no RF, flash or journal erasure')


if __name__=='__main__':main()
