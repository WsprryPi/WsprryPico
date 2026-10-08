#!/usr/bin/env python3
"""Explicit B engineering-profile experiment; preserve only the affected settings region."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from phase14.live import Rig,save
from phase14.profiles import profile,engineering_record
from led_closeout.runner import require,sha256
from led_closeout.device import retained_settings


def ready(rig):
    end=time.monotonic()+90
    while time.monotonic()<end:
        try:
            value=rig.device.console('B','INFO')
            ready_transport=(value['lan_wtp_ready'] if value['provisioning_source']=='consumer_preclock' else
                             value['provisioning_source']=='provisioned' and value['network']['control_listening'])
            if ready_transport and value['status']['clock_state']=='synchronized':
                return rig.idle('B')
        except (FileNotFoundError,TimeoutError,ValueError):pass
        time.sleep(.5)
    raise TimeoutError('B runtime readiness')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('enter','restore'));parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--settings',type=Path,required=True);parser.add_argument('--credentials',type=Path)
    a=parser.parse_args();require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux bench ownership')
    for path in (a.output,a.settings):require(path.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    if a.operation=='enter':require(a.credentials is not None and not a.settings.exists(),'fresh concrete settings preservation')
    os.umask(0o077);rig=Rig(a.output,ROOT,board='B',receiver=False);mutated=False;rom=False
    def interrupted(signum,frame):raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        from phase14.candidate import candidate
        manifest,image,_=candidate(ROOT)
        before=rig.idle('B');require(before['revision']==manifest['source_commit'][:12],'reviewed candidate source')
        rig.device.rom('B');rom=True
        if a.operation=='enter':
            rig.device.pt('B',['save','-r','0x103f7000','0x103ff000','-v',str(a.settings),'-t','bin'])
            original=a.settings.read_bytes();require(len(original)==32768,'profile plus standalone settings range')
            sequence,source,value=profile(original[:16384]);require(source==5 and sequence==int(before['provisioning_generation']),'current consumer profile')
            require(value['device_id']==before['device_id'],'profile identity')
            credentials=a.credentials
            engineering=dict(version=1,device_id=value['device_id'],
                 wifi=dict(ssid=value['network']['ssid'],password=value['network']['password'],time_server='192.168.1.54'),
                 tls=dict(hostname=value['tls']['hostname'],port=443,
                     server_certificate=(credentials/'server/server.crt').read_text(),
                     server_private_key=(credentials/'server/server.key').read_text(),
                     client_ca=(credentials/'server/client-ca.crt').read_text()))
            temporary=rig.e.root/'engineering-profile.bin';temporary.write_bytes(engineering_record(sequence+1,engineering))
            save(a.settings.with_suffix('.json'),dict(settings_sha256=sha256(a.settings),before=before,firmware_sha256=image['sha256'],source_commit=manifest['source_commit'],
                 purpose='Temporary engineering USB/browser/standalone tests require changing only profile/configuration settings; application, access, bonds and E10 preserved.',
                 engineering_profile_sha256=sha256(temporary)))
            mutated=True
            rig.device.pt('B',['load','-v',str(temporary),'-t','bin','-o','0x103f7000'])
        else:
            receipt=json.loads(a.settings.with_suffix('.json').read_text());require(sha256(a.settings)==receipt['settings_sha256'],'original settings identity')
            require(before['provisioning_source']=='provisioned','expected temporary engineering profile')
            rig.device.pt('B',['load','-v',str(a.settings),'-t','bin','-o','0x103f7000'])
        rig.device.pt('B',['reboot']);rom=False;after=ready(rig)
        if a.operation=='enter':
            require(after['provisioning_source']=='provisioned' and int(after['provisioning_generation'])==sequence+1,
                    'engineering profile activation')
            require(after['network']['ntp_server']=='192.168.1.54','owned NTP reference selection')
        else:
            require(retained_settings(after)==retained_settings(receipt['before']),'original settings restoration')
        rig.inventory(['B']);save(rig.e.root/'result.json',dict(operation=a.operation,before=before,after=after,firmware_sha256=image['sha256'],source_commit=manifest['source_commit'],settings_sha256=sha256(a.settings),result='VERIFIED'))
        print(json.dumps(dict(operation=a.operation,result='VERIFIED',source=after['provisioning_source'])))
    except BaseException:
        if a.operation=='enter' and mutated:
            if not rom:rig.device.rom('B')
            receipt=json.loads(a.settings.with_suffix('.json').read_text())
            require(sha256(a.settings)==receipt['settings_sha256'],'rollback settings identity')
            rig.device.pt('B',['load','-v',str(a.settings),'-t','bin','-o','0x103f7000'])
            rig.device.pt('B',['reboot']);rom=False
            restored=ready(rig)
            require(retained_settings(restored)==retained_settings(receipt['before']),'failed experiment settings rollback')
            save(rig.e.root/'rollback.json',dict(result='VERIFIED',info=restored))
        elif rom:
            rig.device.pt('B',['reboot']);rom=False
        raise
    finally:rig.close()


if __name__=='__main__':main()
