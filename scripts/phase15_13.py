#!/usr/bin/env python3
"""Finite P15.13 plan/acquisition/analysis; physical execution requires --run."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from phase15_13.plan import plan, validate, CLOCK, FREQUENCIES, repair_plan, fskcw_repair_plan
from phase14.live import Rig, save
from phase14.profiles import durable_settings, restoration_settings
from led_closeout.runner import require, sha256


def configuration(raw):
    """Newest valid config, rejecting torn/ambiguous journals without rollback."""
    require(len(raw)==32768, 'exact private settings region')
    records = []
    from phase11_5_inventory import loads_console
    for offset in range(16384,24576,2048):
        record=raw[offset:offset+2048]
        if record==b'\xff'*2048: continue
        magic,sequence,size=struct.unpack_from('<QQI',record)
        require(magic==0x32524f5453505757 and sequence>0 and size<=1984 and
                zlib.crc32(record[:-4])==struct.unpack_from('<I',record,2044)[0],
                'invalid configuration journal')
        records.append((sequence,loads_console(record[32:32+size].decode())))
    require(records and len({s for s,_ in records})==len(records),'ambiguous configuration journal')
    return max(records,key=lambda v:v[0])[1]


def gps_enable(enabled):
    from phase14_reference import GPSPY
    code=('import sys;sys.path.insert(0,"/home/pi/lbgpsdo");import lbe142x;'
          'd=lbe142x.GPSDODevice.open(serial="0673ED0FA107");'
          f'd.enable({bool(enabled)!r},None);d.close()')
    subprocess.run([GPSPY,'-c',code],check=True,timeout=20)


def boot_pins(config):
    # parse_config() defaults an absent legacy pins field to PinPlan{}.
    from led_closeout.candidates import pins
    return copy.deepcopy(config.get('pins',pins(0)))


def wait_idle(rig,board,seconds=30):
    deadline=time.monotonic()+seconds
    while True:
        try:return rig.idle(board)
        except (FileNotFoundError,TimeoutError):
            if time.monotonic()>=deadline:raise
            time.sleep(.5)


def permission(rig,password,allow):
    info=rig.idle('A')
    value=dict(address=info['network']['ipv4'],password=password,
               device_id=info['device_id'],boot_id=info['status']['boot_id'],allow=allow)
    result=subprocess.run(['node',str(ROOT.parent/'radio-client.mjs')],
        input=json.dumps(value),text=True,capture_output=True,timeout=100)
    require(result.returncode==0,'authenticated opt-in failed: '+result.stderr[-1500:])
    receipt=json.loads(result.stdout)
    save(rig.e.root/('permission-on.json' if allow else 'permission-restored.json'),receipt)
    return receipt


def ready(rig,seconds=180):
    deadline=time.monotonic()+seconds
    while True:
        current=rig.idle('A')
        if current['lan_wtp_ready'] and current['status']['clock_state']=='synchronized':return current
        require(time.monotonic()<deadline,'current firmware LAN/time readiness unavailable')
        time.sleep(2)


def execute(args):
    from phase14_reference import gps
    from phase15_13.live import group
    from check_standalone_image import validate_uf2
    require(args.run and sys.platform.startswith('linux') and os.geteuid()==0,
            'explicit --run and Linux exclusive bench owner required')
    require(args.output.resolve().is_relative_to(ROOT/'build'),'private build evidence required')
    require(args.manifest is not None and args.image is not None,'source manifest and fresh image required')
    manifest=json.loads(args.manifest.read_text())
    source=manifest['source_revision']
    image=manifest['artifacts']['WsprryPico-StandaloneRF.uf2']
    require(source=='165303458e49feaac1de54c8344058f56578d533' and
            sha256(args.image)==image['sha256'] and manifest['clock_hz']==CLOCK,
            'fresh current-developer-branch image binding')
    validate_uf2(args.image.read_bytes(),application_end=0x103f0000)
    os.umask(0o077)
    rig=Rig(args.output,ROOT)
    rig.device.setup['wtp_request_timeout']=10
    original=None;password=None;before=None;reference=None;service_active=False;service_stopped=False
    changed=False;in_rom=False;restored=False;paths=[];errors=[]
    def interrupted(signum,frame): raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        validate(plan());save(rig.e.root/'plan.json',plan())
        before={b:rig.idle(b) for b in ('A','B')}
        reference=gps();save(rig.e.root/'before.json',dict(boards=before,reference=reference))
        service_active=subprocess.run(['systemctl','is-active','--quiet','wsprrypi']).returncode==0
        save(rig.e.root/'service-before.json',dict(active=service_active))
        if service_active:
            subprocess.run(['systemctl','stop','wsprrypi'],check=True,timeout=30);service_stopped=True
        settings=rig.e.root/'original-settings.bin'
        prior=None
        if args.resume_from:
            prior=json.loads((args.resume_from/'deployment.json').read_text())
            require(prior['source']==source and prior['uf2_sha256']==image['sha256'] and
                    prior['info']['status']['boot_id']==before['A']['status']['boot_id'] and
                    before['A']['revision']==source[:12], 'resume exact flashed boot/image')
            saved=args.resume_from/'original-settings.bin'
            require(sha256(saved)==prior['settings_sha256'],'resume private settings hash')
            settings.write_bytes(saved.read_bytes())
        else:
            rig.device.rom('A');in_rom=True
            rig.device.pt('A',['save','-r','0x103f0000','0x103ff000','-v',str(settings),'-t','bin'])
        require(settings.stat().st_size==0xf000,'all current journals preserved')
        original=configuration(settings.read_bytes()[0x7000:])
        from phase14.profiles import profile
        _,profile_source,profile_value=profile(settings.read_bytes()[0x7000:0xb000])
        require(profile_source==5 and profile_value['device_id']==before['A']['device_id'],
                'saved consumer profile authority')
        password=profile_value['network']['password']
        require(original['enabled'] is False and original.get('allow_non_amateur_frequency',False) is False,
                'disabled scheduling and no non-amateur permission required')
        rig.verified_pins=boot_pins(original)
        require(rig.verified_pins['engine']=='direct' and rig.verified_pins['rf_gp']==2,'saved GP2 direct pin authority')
        if prior is None:
            rig.device.pt('A',['load','-v',str(args.image)])
            rig.device.pt('A',['verify',str(settings),'-t','bin','-o','0x103f0000'])
            rig.device.pt('A',['reboot']);in_rom=False
            deadline=time.monotonic()+120
            while True:
                try:
                    current=rig.info('A')
                    if current['revision']==source[:12]: break
                except (FileNotFoundError,TimeoutError,ValueError): pass
                require(time.monotonic()<deadline,'fresh candidate boot unavailable');time.sleep(.5)
        rig.device.console('A','ABORT')
        current=rig.idle('A')
        require((prior is not None or current['status']['boot_id']!=before['A']['status']['boot_id']) and
                current['system_clock_hz']==CLOCK and current['status']['engine']=='pio-dma-gp2',
                'fresh source/boot/clock/engine identity')
        require(durable_settings(current)==durable_settings(before['A']),'load changed settings')
        if args.cold_focused:
            old_boot=current['status']['boot_id']
            rig.device.console('A','REBOOT')
            rig.device.close_peer('A')
            deadline=time.monotonic()+90
            while True:
                try:
                    current=rig.info('A')
                    if current['status']['boot_id']!=old_boot:break
                except (FileNotFoundError,TimeoutError,ValueError):pass
                require(time.monotonic()<deadline,'known inactive cold-start identity unavailable')
                time.sleep(.5)
            rig.device.console('A','ABORT');current=rig.idle('A')
            require(current['revision']==source[:12] and current['system_clock_hz']==CLOCK and
                    durable_settings(current)==durable_settings(before['A']), 'cold-start changed source/clock/settings')
        save(rig.e.root/'deployment.json',dict(source=source,uf2_sha256=image['sha256'],
            settings_sha256=sha256(settings),boot_pins=rig.verified_pins,info=current,
            resumed_deployment=str(args.resume_from) if prior else None))
        save(rig.e.root/'ready.json',ready(rig))
        changed=True
        if not rig.info('A')['status']['allow_unqualified_frequency']:
            permission(rig,password,True)
        else:
            save(rig.e.root/'permission-on.json',dict(resumed_existing_task_opt_in=True,
                 original_allow_unqualified_frequency=original.get('allow_unqualified_frequency',False)))
        rig.device.console('A','ABORT')
        gps_enable(True)
        require(gps()['out1'] is True,'measurement output 1 enable readback')
        groups=plan()['groups']
        if args.cold_focused:
            require(args.resume_from is not None,'retained original failures required')
            events=[json.loads(line) for line in (args.resume_from/'events.jsonl').read_text().splitlines()]
            require(not any(e['kind']=='planned_window_armed' and 'DIAG' in e['value']['id'] for e in events),
                    'focused RF retest has already been attempted')
            require((args.resume_from/'5m-FSKCW/failure.json').exists(),'retained FSKCW observer failure required')
            save(rig.e.root/'focused-retest-plan.json',repair_plan())
            save(rig.e.root/'fskcw-retest-plan.json',fskcw_repair_plan())
            groups=repair_plan()['groups']+fskcw_repair_plan()['groups']
        if args.focused_fskcw:
            require(args.resume_from is not None,'retained FSKCW failure required')
            failed=json.loads((args.resume_from/'5m-FSKCW/failure.json').read_text())
            require(len(failed['records'])==1 and 'arm' in failed['records'][0] and
                    'terminal' not in failed['records'][0], 'one preserved interrupted FSKCW window required')
            save(rig.e.root/'fskcw-retest-plan.json',fskcw_repair_plan())
            groups=fskcw_repair_plan()['groups']
        if args.final_five_metre:
            require(args.resume_from is not None,'retained failed sequence required')
            failed=args.resume_from/'5m-WSPR/failure.json'
            records=json.loads(failed.read_text())['records']
            require(len(records)==2 and records[0]['terminal']['state']=='complete' and
                    'arm' not in records[1], 'focused retest requires exactly the recorded first-frame/second-LOAD failure')
            save(rig.e.root/'focused-retest-plan.json',repair_plan())
            groups=[g for g in groups if g['band']=='5m' and g['mode'] in ('QRSS','FSKCW','DFCW')]+repair_plan()['groups']
        if args.remaining_band:
            require(args.remaining_band=='5m' and args.resume_from is not None,
                    'only the seven unused 5 m windows may continue')
            previous=json.loads((args.resume_from/'closure.json').read_text())
            require(not any('5m' in Path(path).name for path in previous['paths']),
                    'continuation would repeat a completed 5 m window')
            events=[json.loads(line) for line in (args.resume_from/'events.jsonl').read_text().splitlines()]
            armed=[e['value']['id'] for e in events if e['kind']=='planned_window_armed']
            require(len(armed)==7 and all('-8m-' in identifier for identifier in armed),
                    'continuation requires exactly seven original 8 m windows and zero 5 m ARMs')
            groups=[g for g in groups if g['band']=='5m']
        for selected in groups:
            try:
                paths.extend(str(p) for p in group(rig,selected,image['sha256'],source))
            except Exception as error:
                errors.append(dict(band=selected['band'],mode=selected['mode'],error=repr(error)))
                current=rig.info('A')['status']
                require(current['owner_id'] is None and current['output_active'] is False and
                        current['state'] not in ('loaded','armed','running','failed'),
                        'control integrity does not permit remaining tests')
            save(rig.e.root/'acquisition.json',dict(paths=paths,errors=errors))
            time.sleep(5)
    finally:
        cleanup_errors=[];after={}
        try:
            try:
                if in_rom:rig.device.pt('A',['reboot'])
                wait_idle(rig,'A')
                if changed and original is not None:
                    if rig.info('A')['status']['allow_unqualified_frequency']!=original.get('allow_unqualified_frequency',False):
                        ready(rig)
                        permission(rig,password,original.get('allow_unqualified_frequency',False))
                    rig.device.console('A','ABORT')
                after={b:wait_idle(rig,b) for b in ('A','B')}
                if before:
                    require(durable_settings(after['A'])==restoration_settings(before['A'],after['A']),
                            'A durable settings restoration')
                    require(durable_settings(after['B'])==durable_settings(before['B']) and
                            after['B']['status']['boot_id']==before['B']['status']['boot_id'],
                            'inactive B changed')
            except Exception as error:cleanup_errors.append(dict(stage='boards',error=repr(error)))
            try:
                if reference:
                    gps(reference['f1']);gps_enable(reference['out1'])
                    require(gps()==reference,'GPSDO complete state restoration')
            except Exception as error:cleanup_errors.append(dict(stage='reference',error=repr(error)))
            try:
                if service_stopped:
                    subprocess.run(['systemctl','start','wsprrypi'],check=True,timeout=30)
                    require(subprocess.run(['systemctl','is-active','--quiet','wsprrypi']).returncode==0,
                            'transmitter service restoration')
            except Exception as error:cleanup_errors.append(dict(stage='service',error=repr(error)))
            restored=not cleanup_errors
            save(rig.e.root/'restoration.json',dict(boards=after,reference=gps(),service_active=service_active,
                 settings_restored=restored,cleanup_errors=cleanup_errors,paths=paths,errors=errors,
                 firmware_sha256=image['sha256']))
        finally:
            save(rig.e.root/'closure.json',dict(restoration_verified=restored,paths=paths,errors=errors,
                                              cleanup_errors=cleanup_errors))
            rig.close()
        require(restored,'one or more restoration stages failed')


def analyze(args):
    from phase14.analysis import analyze as observation
    from phase15_13.assessment import assess
    root=args.output
    acquisition=json.loads((root/'acquisition.json').read_text())
    rows=[]
    for path in acquisition['paths']:
        directory=Path(path)
        if not (directory/'analysis/result.json').exists():
            observation(directory,band_frequencies=FREQUENCIES)
        value=assess(directory)
        rows.append(value)
        print(json.dumps({k:value[k] for k in ('window_id','passed','issues')}),flush=True)
    save(root/'analysis-summary.json',dict(rows=rows,acquisition_errors=acquisition['errors']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('plan','execute','analyze'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--image',type=Path)
    parser.add_argument('--resume-from',type=Path)
    selected=parser.add_mutually_exclusive_group()
    selected.add_argument('--remaining-band',choices=('5m',))
    selected.add_argument('--final-five-metre',action='store_true')
    selected.add_argument('--focused-fskcw',action='store_true')
    selected.add_argument('--cold-focused',action='store_true')
    args=parser.parse_args()
    if args.operation=='plan':save(args.output,plan())
    elif args.operation=='execute':execute(args)
    else:analyze(args)


if __name__=='__main__':main()
