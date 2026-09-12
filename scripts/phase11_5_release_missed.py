#!/usr/bin/env python3
"""Opt-in retirement of the exact reconciled, inactive, unowned R2 missed job.

Only HELLO/STATUS/CLAIM/RELEASE. Retain the terminal record. No RF or reset.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from phase11_5_device_fixture import DeviceFixture
from phase11_5_inventory import exclusive_port,require
from phase11_5_pilot import Peer,SERIAL,DEVICE
from phase11_5_pilot_supervisor import finished

BOOT='0da88dc334efa649cbc097ed6dd48c63'
JOB='ba324fb4e892e8dbf57200aee89fe7ff'
SOURCE='e20ae8bea2d5237af017dbd5f73bfe9332ce144e'


def admit(current, expected):
    status=current['wtp']['STATUS'];info=current['info']
    require(status==expected and status['boot_id']==BOOT and status['state']=='missed' and
            status['job_id']==JOB and status['owner_id'] is None and status['output_active'] is False,
            'Exact reconciled inactive unowned Missed job required')
    records=status['terminal_records']
    require(len(records)==1 and records[0]['job_id']==JOB and records[0]['state']=='missed' and
            records[0]['output_active'] is False and records[0]['error']==dict(
                code='MISSED_START',message='MISSED_START',retryable=False), 'Exact missed terminal record')
    require(info['revision']==SOURCE[:12] and info['device_id']==DEVICE and info['system_clock_hz']==138000000 and
            info['rf_render_in_ram'] is True and info['status']['boot_id']==BOOT and
            info['status']['state']=='missed' and info['status']['output_active'] is False and
            info['status']['enabled'] is False and info['status']['storage_healthy'] is True and
            info['status']['last_error'] is None and not info['recovery_boot'] and not info['engine_diagnostic'] and
            all(info[k]==0 for k in ('fault_stage','fault_status','fault_pc','fault_hash','dma_errors',
                'dma_irqs','tail_irqs','refill_irq_unpaired','refill_invalid_reserves','exhausted_successor_links')) and
            int(info['launch_epoch'])==int(info['launch_observed_ns'])==0 and info['alarm_irqs']==1,
            'Unexpected firmware/output/launch fault')
    require(all(info[f'core{c}_stack_guard_valid']==1 and info[f'core{c}_stack_fault_status']==0 for c in (0,1)),
            'Stack fault')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--baseline-sha256',required=True)
    p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no access.');return
    require(sys.platform=='linux' and os.geteuid()==0,'wspr5 root required')
    os.umask(0o077);root=a.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077==0,'Private root required')
    require(hashlib.sha256(a.baseline.read_bytes()).hexdigest()==a.baseline_sha256,'Reconciliation changed')
    original=finished(a.baseline,'READ_ONLY_INVENTORY');expected=original['wtp']['STATUS'];admit(original,expected)
    d=DeviceFixture(root);d.verify_helpers()
    require(d.state['boot']==BOOT and d.state['kind']=='physical' and not d.state.get('pending') and
            time.monotonic_ns()+90*10**9<d.state['deadline_monotonic_ns'],'Lifecycle admission')
    with (root/'device.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        current=d.inventory('missed-release-before');admit(current,expected)
        with (root/'missed-release.jsonl').open('x') as log:
            def emit(kind,value):
                log.write(json.dumps(dict(kind=kind,value=value,monotonic_ns=time.monotonic_ns()))+'\n')
                log.flush();os.fsync(log.fileno())
            end=time.monotonic()+30
            def checkpoint():require(time.monotonic()<end,'Retirement deadline')
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
                peer=Peer(fd,emit,checkpoint,BOOT)
                hello=peer.request('HELLO',dict(versions=['WTP/1'],client_name='R2-missed-retirement',client_version='1'))
                require(hello['device_id']==DEVICE and hello['boot_id']==BOOT,'HELLO identity')
                require(peer.request('STATUS')==expected,'Status changed before retirement')
                owner=secrets.token_hex(16);lease=peer.request('CLAIM',dict(owner_id=owner,lease_ms=60000))
                require(lease['owner_id']==owner and lease['granted_lease_ms']==60000,'Retirement lease')
                peer.request('RELEASE')
                after=peer.request('STATUS')
                require(after==dict(boot_id=BOOT,state='empty',output_active=False,owner_id=None,job_id=None,
                    terminal_records=expected['terminal_records']),'Retirement changed record or output')
                emit('retired',after)
        final=d.check_current('missed-release-after')
        require(final['wtp']['STATUS']==after,'Final retirement differs')
    print('Exact Missed current slot retired; terminal record unchanged; no RF or reset')

if __name__=='__main__':main()
