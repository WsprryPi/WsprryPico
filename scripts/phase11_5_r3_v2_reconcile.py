#!/usr/bin/env python3
"""Finite idle terminal reconciliation; never starts or aborts RF."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from phase11_5_inventory import require, exclusive_port
from phase11_5_pilot import Peer, SERIAL, DEVICE
from phase11_5_pilot_supervisor import finished, configuration, B_SERIAL, B_DEVICE
from phase11_5_device_management import digest, save
from phase11_5_r3_capacity_plan import identity
from phase11_5_r3_v2_rf import validate_info, comparator_required, DIAGNOSTIC_SOURCE, DIAGNOSTIC_IMAGE

C4_TERMINAL=dict(job_id='9f0ae5cb9bf19c6366c53c33a75d86e0',state='missed',
    ended_monotonic_ns='264396496000',output_active=False,
    error=dict(code='MISSED_START',message='MISSED_START',retryable=False))


def known_missed(packet):
    if 'allowed_missed_terminal' not in packet:return False
    require(packet['allowed_missed_terminal']==C4_TERMINAL and
        packet['source_revision']==DIAGNOSTIC_SOURCE and packet['image_sha256']==DIAGNOSTIC_IMAGE and
        packet['boot_id']=='0bd82f1324920c360d796988cf31cb5b' and
        packet.get('missed_evidence_sha256')=='a039135d8db909f288599c960ddd433872b40ab69357226ec0378335c23372e3' and
        packet['allowed_complete_jobs']==[], 'Exact independently verified C4 Missed terminal required')
    return True


def validate_stage(root, packet):
    required = {'scripts/phase11_5_inventory.py', 'scripts/phase11_5_pilot.py',
                'docs/protocol/wtp-1.schema.json'}
    require(required <= set(packet['stage_sha256']), 'Missing inventory dependency manifest')
    for name, sha in packet['stage_sha256'].items():
        path = (root/name).resolve()
        require(path.is_relative_to(root) and path.is_file() and digest(path) == sha,
                'Missing or changed staged dependency: ' + name)
    schema = json.loads((root/'docs/protocol/wtp-1.schema.json').read_text())
    require(isinstance(schema, dict) and '$schema' in schema, 'Invalid staged WTP schema')


def admission(value, packet):
    s, i = value['wtp']['STATUS'], value['info']
    missed=known_missed(packet)
    require(s['boot_id'] == i['status']['boot_id'] == packet['boot_id'] and
            s['state'] == i['status']['state'] and s['state'] in (['empty','missed'] if missed else ['empty','complete']) and
            s['output_active'] is i['status']['output_active'] is False and s['owner_id'] is None,
            'Reconciliation requires authoritative inactive/unowned state')
    validate_info(i, value, packet,allow_missed=missed)
    if s['state'] == 'complete':
        require(s['job_id'] in packet['allowed_complete_jobs'] and any(
            r['job_id'] == s['job_id'] and r['state'] == 'complete' and r['output_active'] is False and
            'error' not in r for r in s['terminal_records']), 'Unknown terminal job')
    elif s['state']=='missed':
        require(s['job_id']==C4_TERMINAL['job_id'] and C4_TERMINAL in s['terminal_records'],
                'Missing or changed C4 terminal record')
    else:
        require(s['job_id'] is None, 'Empty job identity')
    return s['state'] != 'empty'


def validate_final(value, baseline, packet, b=False):
    s = value['wtp']['STATUS']
    require(baseline is not None and s['boot_id'] == baseline['wtp']['STATUS']['boot_id'] and
            s['state'] == 'empty' and s['output_active'] is False and
            s['owner_id'] is s['job_id'] is None and configuration(value) == configuration(baseline),
            'Final identity/authority/configuration')
    if b:
        # The inhibited comparator image has no RF-engine telemetry fields.
        require(s == baseline['wtp']['STATUS'] and
                value['info']['revision'] == baseline['info']['revision'], 'B changed')
    else:
        for key in ['launch_epoch', 'dma_irqs', 'alarm_irqs', 'tail_irqs']:
            require(value['info'][key] == baseline['info'][key], 'Unexpected RF work')
        validate_info(value['info'], baseline, packet)


def run(root, packet):
    end = time.monotonic() + 150
    def checkpoint(): require(time.monotonic() < end, 'Finite reconciliation deadline')
    def inventory(label, b=False):
        checkpoint()
        require(not b or comparator_required(packet), 'Independent B is outside this reconciliation')
        with (root/(label+'.stdout')).open('xb') as out, (root/(label+'.stderr')).open('xb') as err:
            code = subprocess.run(['python3', str(root/'scripts/phase11_5_inventory.py'),
                '--serial', B_SERIAL if b else SERIAL, '--device-id', B_DEVICE if b else DEVICE,
                '--session-id', packet['b_session'] if b else packet['inventory_session'], '--run'],
                stdout=out, stderr=err, timeout=min(30,max(.001,end-time.monotonic()))).returncode
        require(code == 0, 'Inventory failure '+label)
        return finished(root/(label+'.stdout'), 'READ_ONLY_INVENTORY')
    result = dict(status='RUNNING', rf_jobs=0, rf_duration_ns_charged=0, claim_attempts=0, release_attempts=0)
    save(root/'result.json', result)
    before = before_b = None
    try:
        if comparator_required(packet):
            before_b = inventory('before-b', True)
        before = inventory('before-a')
        needed = admission(before, packet)
        if before_b is not None:
            s = before_b['wtp']['STATUS']
            require(s['boot_id'] == packet['b_boot_id'] and s['state'] == 'empty' and
                    s['owner_id'] is s['job_id'] is None and s['output_active'] is False, 'B initial authority')
        with (root/'reconcile.jsonl').open('x') as log:
            def emit(kind,value):
                log.write(json.dumps(dict(kind=kind,value=value,monotonic_ns=time.monotonic_ns()))+'\n')
                log.flush(); os.fsync(log.fileno())
            emit('start',dict(packet_sha256=digest(root/'packet.json'),needed=needed))
            if needed:
                with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
                    peer = Peer(fd,emit,checkpoint,packet['boot_id']);peer.session=packet['peer_session']
                    h=peer.request('HELLO',dict(versions=['WTP/1'],client_name='R3-v2-idle-reconcile',client_version='1'))
                    require(h['device_id']==DEVICE and h['boot_id']==packet['boot_id'],'Reconcile peer')
                    require(peer.request('STATUS')==before['wtp']['STATUS'],'Terminal changed before claim')
                    result['claim_attempts']=1;save(root/'result.json',result)
                    claim=peer.request('CLAIM',dict(owner_id=packet['owner_id'],lease_ms=60000))
                    require(claim['owner_id']==packet['owner_id'],'Reconcile owner')
                    result['release_attempts']=1;save(root/'result.json',result);peer.request('RELEASE')
                    s=peer.request('STATUS')
                    require(s['boot_id']==packet['boot_id'] and s['state']=='empty' and
                            s['owner_id'] is s['job_id'] is None and s['output_active'] is False and
                            s['terminal_records']==before['wtp']['STATUS']['terminal_records'], 'Reconcile final authority/history')
            emit('finish', dict(released=needed))
        result['status']='RECONCILED_REQUIRES_FINAL_INVENTORY'
    except BaseException as error:
        result.update(status='FAILED',error=str(error))
    finally:
        for label,b in ([('after-a',False),('after-b',True)] if comparator_required(packet) else [('after-a',False)]):
            try:
                value=inventory(label,b);s=value['wtp']['STATUS'];baseline=before_b if b else before
                validate_final(value, baseline, packet, b)
                result[label]=s
            except BaseException as error:result.update(status='FAILED',**{label+'-error':str(error)})
        if result['status']=='RECONCILED_REQUIRES_FINAL_INVENTORY':result['status']='RECONCILED_INACTIVE_UNOWNED'
        save(root/'result.json',result)
    require(result['status']=='RECONCILED_INACTIVE_UNOWNED','Reconciliation requires diagnosis')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no device control.');return
    root=a.root.resolve(strict=True);os.umask(0o077)
    require(os.geteuid()==0 and digest(root/'packet.json')==a.packet_sha256,'Root/hash')
    packet=json.loads((root/'packet.json').read_text())
    require(packet['standing_authority']=='R3-COMPLETE-20260913-v2' and packet['root']==str(root) and
            packet['schema']=='phase11.5-r3-v2-idle-reconcile-v1' and packet['runtime_seconds']==150 and
            packet['rf_jobs']==packet['flashes']==packet['wifi_cycles']==packet['configuration_writes']==0 and
            Path('/proc/sys/kernel/random/boot_id').read_text().strip()==packet['host_boot_id'], 'Finite idle scope')
    for key in ['owner_id','peer_session','inventory_session','b_session','boot_id','b_boot_id']:identity(packet[key])
    if not known_missed(packet):
        require(len(packet['allowed_complete_jobs'])==1,'Exactly one known terminal job')
        identity(packet['allowed_complete_jobs'][0])
    validate_stage(root, packet)
    with (root/'result.json').open('x') as out:json.dump(dict(status='STARTING'),out)
    run(root,packet)

if __name__=='__main__':main()
