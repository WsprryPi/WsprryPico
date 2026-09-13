#!/usr/bin/env python3
"""Opt-in v2 deployment and idle boundary admission; never ARM or change CONFIG."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import subprocess
import time
import uuid

from phase11_5_inventory import require, exclusive_port
from phase11_5_pilot import Peer, SERIAL, DEVICE
from phase11_5_pilot_supervisor import B_SERIAL, B_DEVICE, PICOTOOL, PICOTOOL_SHA, finished, configuration
from phase11_5_r3_allocation_diagnostic import inactive, saved_configuration, request_bootsel
from phase11_5_device_management import digest, save
from phase11_5_r3_capacity_plan import identity, wtp_capacity_frame
from phase11_5_r3_capacity_probe import exchange_capacity
from validate_wtp_contract import frame

SCHEMA = 'phase11.5-r3-v2-idle-admission-v1'
DURATION = 3600_000_000_000


def maximum_job(job_id, count=512, duration=DURATION):
    identity(job_id)
    require(type(count) is int and 1 <= count <= 513 and type(duration) is int and
            0 < duration <= DURATION + 1, 'Idle job construction bound')
    edges = [duration * i // count for i in range(count + 1)]
    return dict(job_id=job_id, profile='rf-events/1', mode='fskcw',
                total_duration_ns=str(duration), allow_frequency_adjustment=True,
                events=[dict(offset_ns=str(a), duration_ns=str(b-a), rf_on=True,
                    frequency_nhz=str(135500_000_000_000 if i % 2 == 0 else 135495_000_000_000))
                    for i, (a, b) in enumerate(zip(edges, edges[1:]))])


def validate(packet):
    require(packet['schema'] == packet['r3_scope'] == SCHEMA and
            packet['serial'] == SERIAL and packet['device_id'] == DEVICE and
            packet['runtime_seconds'] == 600 and packet['flashes'] == 1 and
            packet['bootsel_commands'] == 1 and packet['rf_jobs'] == 0 and
            packet['wifi_cycles'] == packet['configuration_writes'] == packet['heap_probes'] == 0,
            'v2 idle admission scope')
    for key in ('runtime_seconds','flashes','bootsel_commands','rf_jobs','wifi_cycles',
                'configuration_writes','heap_probes'):
        require(type(packet[key]) is int, 'Integer operation budget')
    for key in ('source_revision','prior_revision'):
        require(re.fullmatch('[0-9a-f]{40}', packet[key]), 'Full source identity')
    for key in ('image_sha256','installed_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', packet[key]), 'Hash identity')
    require(packet['image_file'] == 'candidate.uf2' and packet['installed_pid'] > 0,
            'Reviewed image/service')
    keys = ('prior_boot','b_boot','a_session','b_session','peer_session','owner_id',
            'maximum_job_id','oversized_job_id','overduration_job_id')
    for key in keys: identity(packet[key])
    require(len({packet[key] for key in keys}) == len(keys), 'Distinct identities')
    require(packet['maximum_job'] == maximum_job(packet['maximum_job_id']), 'Frozen maximum job')
    require(packet['root'].startswith('/home/pi/phase11-5-r3-v2-') and
            str(Path(packet['root'])) == packet['root'] and '..' not in Path(packet['root']).parts,
            'Fresh v2 root')
    return packet


def status_idle(status, boot):
    require(status['boot_id'] == boot and status['output_active'] is False and
            status['state'] == 'empty' and status['owner_id'] is None and status['job_id'] is None,
            'Authoritative Empty/inactive/unowned')


def candidate(value, packet, *, boot=None):
    inactive(value)
    info = value['info']; status = value['wtp']['STATUS']; caps = value['wtp']['CAPS']
    require(info['device_id'] == DEVICE and info['revision'] == packet['source_revision'][:12] and
            info['status']['boot_id'] == status['boot_id'] and (boot is None or status['boot_id'] == boot) and
            info['recovery_boot'] is False and info['system_clock_hz'] == 138000000 and
            info['status']['engine'] == 'pio-dma-gp2' and info['rf_render_in_ram'] is True and
            all(info[k] == 0 for k in ('fault_stage','fault_hash','fault_pc','fault_status')) and
            int(info['allocator_failures']) == 0 and
            info['heap_capacity_bytes'] - info['allocator_peak_bytes'] >= 32768 and
            caps['max_events'] == 512 and int(caps['max_job_duration_ns']) == DURATION and
            caps['max_payload_bytes'] == 65536, 'Extended candidate identity/capacity/resource')
    for core in (0,1):
        require(type(info[f'core{core}_stack_guard_valid']) is int and
                info[f'core{core}_stack_guard_valid'] == 1 and info[f'core{core}_stack_fault_status'] == 0 and
                info[f'core{core}_stack_guard_limit'] - info[f'core{core}_stack_guard_bottom'] == 4096,
                'Extended candidate stack guards')
    require(all(int(info[k]) == 0 for k in ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs')),
            'Idle packet unexpectedly executed RF')
    return status['boot_id']


class IdlePeer(Peer):
    """Full-write evidence and deliberate schema-invalid LOAD, never an ARM path."""
    def operation(self, op, body=None, expected_error=None):
        require(op in ('HELLO','CAPS','STATUS','CLAIM','LOAD','ABORT','RELEASE'), 'Idle operation only')
        request = dict(type='request', protocol='WTP/1', session_id=self.session,
                       request_id=uuid.uuid4().hex, op=op, body=body or {})
        raw = frame(json.dumps(request, separators=(',',':')).encode()); require(raw, 'Frame bound')
        self.emit('idle_tx', dict(request=request, hex=raw.hex(), expected_error=expected_error))
        pending = raw; deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.checkpoint()
            reads, writes, _ = select.select([self.fd], [self.fd] if pending else [], [], .025)
            if writes:
                try:
                    n = os.write(self.fd, pending[:4096]); require(n > 0, 'USB no write progress')
                    pending = pending[n:]
                    self.emit('idle_write', dict(bytes=n,total_written=len(raw)-len(pending)))
                except BlockingIOError: pass
            if not reads: continue
            try: data = os.read(self.fd, 4096)
            except BlockingIOError: continue
            require(data, 'USB EOF; output unknown'); self.emit('idle_rx', dict(hex=data.hex()))
            response = None
            for value in self.decoder.feed(data):
                require(not self.validator.errors(value,self.schema) and value['session_id'] == self.session,
                        'Malformed/foreign idle response')
                self.emit('idle_message',value)
                if value['type'] == 'event':
                    require(value['boot_id'] == self.boot and value['event'] in ('JOB_STATE','OWNER_RELEASED'),
                            'Unexpected idle event')
                    continue
                require(not pending and response is None and value['request_id'] == request['request_id'] and
                        value['op'] == op, 'Duplicate/unmatched/premature idle response')
                require((expected_error is None and value['ok'] is True) or
                        (expected_error is not None and value['ok'] is False and
                         value['error']['code'] == expected_error), 'Unexpected operation outcome')
                response = value
            if response is not None: return response.get('body', response.get('error'))
        raise TimeoutError('Five-second idle operation deadline; no mutation retry')


def run(root, packet):
    deadline = time.monotonic()+packet['runtime_seconds']
    result = dict(status='RUNNING',flashes_started=0,bootsel_commands=0,rf_jobs=0,
                  wifi_cycles=0,configuration_writes=0,heap_probes=0,passed_assertions=[])
    log = (root/'admission.jsonl').open('x'); sequence = 0
    def emit(kind,value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence,kind=kind,value=value,
            monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns()))+'\n')
        log.flush();os.fsync(log.fileno());sequence += 1
    def checkpoint(): require(time.monotonic() < deadline, 'Admission overall deadline')
    def passed(name):
        result['passed_assertions'].append(name); emit('assertion_observed',name)
        save(root/'admission-result.json',result)
    def inventory(label,b=False):
        checkpoint()
        with (root/(label+'.stdout')).open('xb') as out, (root/(label+'.stderr')).open('xb') as err:
            code = subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),'--serial',
                B_SERIAL if b else SERIAL,'--device-id',B_DEVICE if b else DEVICE,'--session-id',
                packet['b_session'] if b else packet['a_session'],'--run'],stdout=out,stderr=err,timeout=65).returncode
        require(code == 0, 'Inventory failed: '+label)
        return finished(root/(label+'.stdout'),'READ_ONLY_INVENTORY')
    def host():
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == packet['host_boot_id'], 'Host boot')
        pid = int(subprocess.check_output(['systemctl','show','wsprrypi','-p','MainPID','--value'],timeout=5))
        require(pid == packet['installed_pid'] and digest(Path(f'/proc/{pid}/exe')) == packet['installed_sha256'],
                'Protected installed service changed')
    before = before_b = after = None
    try:
        emit('start',dict(packet_sha256=digest(root/'packet.json')));host()
        before_b=inventory('before-b',True);inactive(before_b)
        before=inventory('before-a');inactive(before)
        require(before['wtp']['STATUS']['boot_id'] == packet['prior_boot'] and
                before['info']['revision'] == packet['prior_revision'][:12] and
                before['info']['recovery_boot'] is False and
                before_b['wtp']['STATUS']['boot_id'] == packet['b_boot'], 'Prior identity')
        require(digest(PICOTOOL) == PICOTOOL_SHA and digest(root/packet['image_file']) == packet['image_sha256'],
                'Image/tool hash changed')
        result['bootsel_commands']=1; save(root/'admission-result.json',result)
        emit('bootsel_pending',dict(serial=SERIAL));request_bootsel(emit)
        end=time.monotonic()+15;found=False
        while time.monotonic()<end and not found:
            for p in Path('/sys/bus/usb/devices').glob('*/serial'):
                try:
                    found |= (p.read_text().strip().upper()==SERIAL and
                        (p.parent/'idVendor').read_text().strip()=='2e8a' and
                        (p.parent/'idProduct').read_text().strip()=='000f')
                except OSError:pass
            if not found:time.sleep(.2)
        require(found,'Serial-specific bootloader not found')
        result['flashes_started']=1;save(root/'admission-result.json',result)
        command=[str(PICOTOOL),'load','-v','-x',str(root/packet['image_file']),'--ser',SERIAL]
        emit('flash_pending',dict(argv=command,sha256=packet['image_sha256']))
        with (root/'flash.stdout').open('xb') as out,(root/'flash.stderr').open('xb') as err:
            code=subprocess.run(command,stdout=out,stderr=err,timeout=60).returncode
        emit('flash_exit',dict(exit=code));require(code==0,'Flash failed; no retry')
        end=time.monotonic()+15;port=Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')
        while not port.exists() and time.monotonic()<end:time.sleep(.2)
        require(port.exists(),'Application enumeration missing')
        after=inventory('after-flash-a');boot=candidate(after,packet)
        require(boot != packet['prior_boot'] and saved_configuration(after)==saved_configuration(before),
                'Flash boot/configuration');passed('clean_extended_image_idle')
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
            peer=IdlePeer(fd,emit,checkpoint,boot);peer.session=packet['peer_session']
            hello=peer.operation('HELLO',dict(versions=['WTP/1'],client_name='R3-v2-idle',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==boot,'Peer identity')
            raw=wtp_capacity_frame(peer.session,uuid.uuid4().hex)
            status_idle(exchange_capacity(peer,raw,json.loads(raw[16:]),emit),boot)
            passed('wtp_65536_full_write')
            oversized=wtp_capacity_frame(peer.session,uuid.uuid4().hex,True)
            recovery=dict(type='request',protocol='WTP/1',session_id=peer.session,
                          request_id=uuid.uuid4().hex,op='STATUS',body={})
            raw=oversized+frame(json.dumps(recovery,separators=(',',':')).encode())
            status_idle(exchange_capacity(peer,raw,recovery,emit,invalid_frames=1),boot)
            passed('wtp_65537_rejected_same_connection_recovered')
            peer.operation('CLAIM',dict(owner_id=packet['owner_id'],lease_ms=60000))
            for label,job,error in [('events_513',maximum_job(packet['oversized_job_id'],513),'INVALID_MESSAGE'),
                    ('duration_3600_plus_ns',maximum_job(packet['overduration_job_id'],1,DURATION+1),'JOB_LIMIT_EXCEEDED')]:
                peer.operation('LOAD',job,error)
                status=peer.operation('STATUS')
                require(status['state']=='empty' and status['output_active'] is False and
                        status['owner_id']==packet['owner_id'],'Rejected LOAD changed authority')
                passed(label+'_atomic_rejection')
            load=peer.operation('LOAD',packet['maximum_job'])
            require(load['job_id']==packet['maximum_job_id'] and load['state']=='loaded' and
                    len(load['adjustments'])==512,'Maximum LOAD/adjustment response')
            status=peer.operation('STATUS')
            require(status['boot_id']==boot and status['state']=='loaded' and status['output_active'] is False and
                    status['owner_id']==packet['owner_id'] and status['job_id']==packet['maximum_job_id'],
                    'Maximum LOAD authority');passed('events_512_duration_3600_idle_load')
            peer.operation('ABORT',dict(job_id=packet['maximum_job_id']))
            peer.operation('RELEASE');status_idle(peer.operation('STATUS'),boot)
            passed('loaded_abort_release')
        result['status']='OBSERVED_REQUIRES_INDEPENDENT_AUDIT'
    except BaseException as error:
        result.update(status='STOPPED_REQUIRES_DIAGNOSIS',error=type(error).__name__+': '+str(error),
                      notes=getattr(error,'__notes__',[]));emit('failure',result['error'])
    finally:
        for label,b in [('final-a',False),('final-b',True)]:
            try:
                value=inventory(label,b);inactive(value)
                if b:
                    require(before_b is not None and configuration(value)==configuration(before_b) and
                            value['wtp']['STATUS']['boot_id']==packet['b_boot'] and
                            value['info']['revision']==before_b['info']['revision'],'B changed')
                else:
                    require(before is not None and saved_configuration(value)==saved_configuration(before),
                            'Saved A configuration changed')
                    if after is not None:candidate(value,packet,boot=after['wtp']['STATUS']['boot_id'])
                result[label]=value['wtp']['STATUS']
            except BaseException as error:
                result[label+'-error']=str(error);result['status']='STOPPED_FINAL_STATE_UNVERIFIED'
        try:host()
        except BaseException as error:result['host-error']=str(error);result['status']='STOPPED_HOST_UNVERIFIED'
        emit('finish',result);save(root/'admission-result.json',result);log.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no device, network or file mutations.');return
    require(os.geteuid()==0,'wspr5 root required');os.umask(0o077);root=a.root.resolve(strict=True)
    require(digest(root/'packet.json')==a.packet_sha256,'Packet changed')
    packet=validate(json.loads((root/'packet.json').read_text()));require(packet['root']==str(root),'Root changed')
    for name,sha in packet['stage_sha256'].items():
        require((root/name).resolve().is_relative_to(root) and digest(root/name)==sha,'Staged input changed')
    with (root/'admission-result.json').open('x') as stream:json.dump(dict(status='STARTING'),stream)
    run(root,packet)


if __name__=='__main__':main()
