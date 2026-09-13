#!/usr/bin/env python3
"""Opt-in D0: one approved diagnostic flash and one idle maximum request, no RF."""
import argparse
import errno
import json
import os
from pathlib import Path
import re
import subprocess
import time

from phase11_5_inventory import require, exclusive_port, exchange
from phase11_5_pilot import Peer, SERIAL, DEVICE
from phase11_5_pilot_supervisor import B_SERIAL, B_DEVICE, PICOTOOL, PICOTOOL_SHA, finished, configuration
from phase11_5_device_management import digest, save
from phase11_5_network_fixture import HOST_BOOT
from phase11_5_r3_capacity_plan import identity, wtp_capacity_frame
from phase11_5_r3_capacity_probe import exchange_capacity

SCHEMA='phase11.5-r3-allocation-diagnostic-d0-v1'
PRIOR_BOOT='bccea7c09794539c4f64bc22b0e76c56'


def inactive(value):
    status=value['wtp']['STATUS']; info=value['info']
    require(status['state']=='empty' and status['output_active'] is False and
            status['owner_id'] is None and status['job_id'] is None and
            info['status']['output_active'] is False and info['status']['state']=='empty' and
            info['status']['enabled'] is False and info['status']['storage_healthy'] is True and
            info['status']['last_error'] is None,
            'D0 inactive/unowned/configuration admission')


def saved_configuration(value):
    station,network=configuration(value)
    # Recovery deliberately leaves the live station MAC empty. Compare the
    # saved identity and station/schedules without confusing runtime with storage.
    return station,{key:network[key] for key in ('configured_hostname','control_configured')}


def request_bootsel(emit):
    acknowledged=False
    try:
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
            reply=exchange(fd,b'BOOTSEL\n',time.monotonic()+5,emit,False)
            require(reply.get('ok') is True and reply.get('rebooting') is True,'D0 BOOTSEL not acknowledged')
            emit('bootsel_acknowledged',reply)
            acknowledged=True
    except OSError as error:
        # A positively acknowledged BOOTSEL can remove this very USB endpoint
        # before DTR cleanup. The next gate still requires this serial in ROM.
        if not acknowledged or error.errno not in (errno.EIO,errno.ENODEV):
            raise
        emit('bootsel_disconnect_cleanup',dict(errno=error.errno,error=str(error)))


def validate(packet):
    for key in ('runtime_seconds','flashes','bootsel_commands','maximum_payload_requests','maximum_payload_bytes',
                'rf_jobs','wifi_cycles','configuration_writes','heap_probes'):
        require(type(packet[key]) is int,'D0 integer scope')
    require(packet['schema']==packet['r3_scope']==SCHEMA and packet['host_boot_id']==HOST_BOOT and
            packet['serial']==SERIAL and packet['device_id']==DEVICE and packet['prior_boot']==PRIOR_BOOT and
            packet['runtime_seconds']==600 and packet['flashes']==1 and packet['bootsel_commands']==1 and
            packet['maximum_payload_requests']==1 and packet['maximum_payload_bytes']==65536 and
            packet['rf_jobs']==packet['wifi_cycles']==packet['configuration_writes']==packet['heap_probes']==0,
            'D0 exact scope')
    require(packet['image_file']=='diagnostic.uf2' and re.fullmatch('[0-9a-f]{64}',packet['image_sha256']) and
            re.fullmatch('[0-9a-f]{40}',packet['source_revision']) and packet['embedded_revision']==packet['source_revision'][:12],
            'D0 candidate identity')
    keys=('a_session','b_session','peer_session','request_id')
    require(len({identity(packet[k]) for k in keys})==len(keys),'D0 distinct request/session identities')
    return packet


def run(root,packet):
    deadline=time.monotonic()+600
    result=dict(status='RUNNING',flashes_started=0,bootsel_commands=0,maximum_requests_started=0,
                rf_jobs=0,configuration_writes=0,wifi_cycles=0,heap_probes=0)
    save(root/'diagnostic-result.json',result)
    log=(root/'diagnostic.jsonl').open('x');sequence=0
    def emit(kind,value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence,monotonic_ns=time.monotonic_ns(),kind=kind,value=value))+'\n')
        log.flush();os.fsync(log.fileno());sequence+=1
    def checkpoint():require(time.monotonic()<deadline,'D0 overall deadline')
    def inventory(label,b=False):
        checkpoint()
        with (root/(label+'.stdout')).open('xb') as out,(root/(label+'.stderr')).open('xb') as err:
            code=subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),'--serial',B_SERIAL if b else SERIAL,
                '--device-id',B_DEVICE if b else DEVICE,'--session-id',packet['b_session'] if b else packet['a_session'],
                '--run'],stdout=out,stderr=err,timeout=65).returncode
        require(code==0,'D0 inventory failed: '+label)
        return finished(root/(label+'.stdout'),'READ_ONLY_INVENTORY')
    before=before_b=after_flash=None
    try:
        emit('start',dict(packet_sha256=digest(root/'packet.json')))
        before_b=inventory('before-b',True);inactive(before_b)
        before=inventory('before-a');inactive(before)
        require(before['wtp']['STATUS']['boot_id']==PRIOR_BOOT and before['info']['revision']=='2e43110f0530' and
                before['info']['recovery_boot'] is True and before['info']['fault_hash']==3833354787 and
                before['info']['fault_stage']==5 and
                before_b['wtp']['STATUS']['boot_id']=='feffcd075ab6cb0b74e7e0c2fde6c87f','D0 exact stopped state')
        require(digest(PICOTOOL)==PICOTOOL_SHA and digest(root/packet['image_file'])==packet['image_sha256'],
                'D0 image/tool changed')
        result['bootsel_commands']=1;save(root/'diagnostic-result.json',result)
        emit('bootsel_pending',dict(serial=SERIAL))
        request_bootsel(emit)
        until=time.monotonic()+15;found=False
        while time.monotonic()<until:
            checkpoint()
            for serial in Path('/sys/bus/usb/devices').glob('*/serial'):
                try:
                    found |= (serial.read_text().strip().upper()==SERIAL and
                        (serial.parent/'idVendor').read_text().strip()=='2e8a' and
                        (serial.parent/'idProduct').read_text().strip()=='000f')
                except OSError:pass
            if found:break
            time.sleep(.2)
        require(found,'D0 serial-specific bootloader missing; no retry')
        result['flashes_started']=1;save(root/'diagnostic-result.json',result)
        command=[str(PICOTOOL),'load','-v','-x',str(root/packet['image_file']),'--ser',SERIAL]
        emit('flash_pending',dict(argv=command,sha256=packet['image_sha256']))
        with (root/'flash.stdout').open('xb') as out,(root/'flash.stderr').open('xb') as err:
            code=subprocess.run(command,stdout=out,stderr=err,timeout=60).returncode
        emit('flash_exit',dict(exit=code));require(code==0,'D0 flash failed; no retry')
        until=time.monotonic()+15
        path=Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')
        while not path.exists() and time.monotonic()<until:time.sleep(.2)
        require(path.exists(),'D0 application enumeration missing')
        after_flash=inventory('after-flash-a');inactive(after_flash)
        info=after_flash['info'];boot=after_flash['wtp']['STATUS']['boot_id']
        require(boot!=PRIOR_BOOT and info['revision']==packet['embedded_revision'] and
                info['recovery_boot'] is False and info['fault_stage']==info['fault_hash']==0 and
                info['fault_allocation_recorded'] is False and info['fault_allocation_returned_null'] is None and
                info['system_clock_hz']==138000000 and info['status']['engine']=='pio-dma-gp2' and
                info['rf_render_in_ram'] is True and info['allocator_failures']=='0' and
                info['heap_capacity_bytes']-info['allocator_peak_bytes']>=32768 and
                saved_configuration(after_flash)==saved_configuration(before) and
                after_flash['wtp']['CAPS']['max_payload_bytes']==65536, 'D0 candidate admission')
        for core in (0,1):
            require(info[f'core{core}_stack_guard_valid']==1 and info[f'core{core}_stack_fault_status']==0 and
                    info[f'core{core}_stack_guard_limit']-info[f'core{core}_stack_guard_bottom']==4096,'D0 guards')
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
            peer=Peer(fd,emit,checkpoint,boot);peer.session=packet['peer_session']
            hello=peer.request('HELLO',dict(versions=['WTP/1'],client_name='R3-allocation-diagnostic',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==boot,'D0 peer identity')
            raw=wtp_capacity_frame(peer.session,packet['request_id'])
            result['maximum_requests_started']=1;save(root/'diagnostic-result.json',result)
            status=exchange_capacity(peer,raw,json.loads(raw[16:]),emit)
            require(status['boot_id']==boot and status['state']=='empty' and status['output_active'] is False and
                    status['owner_id'] is None and status['job_id'] is None,'D0 maximum response authority')
            emit('maximum_response',status)
            result['status']='MAXIMUM_RESPONDED_REQUIRES_AUDIT'
    except BaseException as error:
        result.update(status='STOPPED_REQUIRES_DIAGNOSIS',error=type(error).__name__+': '+str(error),
                      error_notes=getattr(error,'__notes__',[]))
        emit('failure',dict(type=type(error).__name__,error=str(error),notes=getattr(error,'__notes__',[])))
    finally:
        # A failed probe may reach the eight-second watchdog after its five-second
        # transfer deadline. This bounded observation delay issues no recovery.
        if result['maximum_requests_started']:
            until=min(deadline,time.monotonic()+12)
            while time.monotonic()<until:time.sleep(.2)
        for label,b in (('final-a',False),('final-b',True)):
            try:
                value=inventory(label,b);inactive(value)
                result[label]=value['wtp']['STATUS']
                if b:
                    require(before_b is not None and configuration(value)==configuration(before_b) and
                            value['info']['revision']==before_b['info']['revision'] and
                            value['wtp']['STATUS']['boot_id']==before_b['wtp']['STATUS']['boot_id'],'D0 B changed')
                else:
                    require(before is not None and saved_configuration(value)==saved_configuration(before),
                            'D0 A saved configuration changed')
                    result['final_fault']={k:value['info'][k] for k in ('revision','recovery_boot','fault_stage','fault_hash',
                        'fault_pc','fault_status','fault_allocation_recorded','fault_allocation_request_bytes',
                        'fault_allocation_returned_null') if k in value['info']}
                    if after_flash is not None:
                        require(value['info']['revision']==packet['embedded_revision'],'D0 final image changed')
                        for key in ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs'):
                            require(int(value['info'][key])==int(after_flash['info'][key])==0,
                                    'D0 unexpected RF work')
                        if (value['wtp']['STATUS']['boot_id']!=after_flash['wtp']['STATUS']['boot_id'] or
                                value['info']['recovery_boot']):
                            result['status']='STOPPED_REQUIRES_DIAGNOSIS'
            except BaseException as error:
                result[label+'-error']=type(error).__name__+': '+str(error)
                result['status']='STOPPED_FINAL_STATE_UNVERIFIED'
        emit('finish',result);save(root/'diagnostic-result.json',result);log.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');args=p.parse_args()
    if not args.run:print('Plan only; no file, device or network access.');return
    require(os.geteuid()==0 and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==HOST_BOOT,'D0 host')
    os.umask(0o077);root=args.root.resolve(strict=True)
    require(digest(root/'packet.json')==args.packet_sha256,'D0 packet changed')
    packet=validate(json.loads((root/'packet.json').read_text()));require(packet['root']==str(root),'D0 root')
    for name,sha in packet['stage_sha256'].items():
        require((root/name).resolve().is_relative_to(root) and digest(root/name)==sha,'D0 staged bytes changed')
    with (root/'diagnostic-result.json').open('x') as f:json.dump({'status':'STARTING'},f)
    run(root,packet)


if __name__=='__main__':main()
