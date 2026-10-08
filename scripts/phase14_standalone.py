#!/usr/bin/env python3
"""Finite ordinary standalone WSPR recurrence with independent complete IQ capture."""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time
import zlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.live import Rig,CAPTURE,save
from phase14.plan import validate_capture
from led_closeout.runner import require,sha256


def original_config(settings):
    raw=Path(settings).read_bytes();require(len(raw)==32768,'settings experiment region')
    records=[]
    for offset in range(16384,24576,2048):
        record=raw[offset:offset+2048]
        if record==b'\xff'*2048:continue
        magic,seq,size=struct.unpack_from('<QQI',record)
        require(magic==0x32524f5453505757 and seq>0 and size<=1984 and
                zlib.crc32(record[:-4])==struct.unpack_from('<I',record,2044)[0],'original configuration journal')
        records.append((seq,json.loads(record[32:32+size])))
    require(records and len({v[0] for v in records})==len(records),'unambiguous config sequence')
    value=max(records,key=lambda v:v[0])[1];require(not value['enabled'],'original disabled schedule')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--settings',type=Path,required=True);p.add_argument('--frames',type=int,choices=(1,2,3),default=3)
    a=p.parse_args();require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux bench ownership')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    old=original_config(a.settings)
    def interrupted(signum,frame):raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    os.umask(0o077);rig=Rig(a.output,ROOT,board='B',receiver=True,reference=True)
    process=None;changed=False;record=None
    try:
        from phase14.candidate import candidate
        manifest,image,_=candidate(ROOT)
        before=rig.idle('B');rig.idle('A')
        require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000 and
                before['provisioning_source']=='provisioned','standalone engineering candidate')
        clock=rig.device.peer('B').request('GET_CLOCK',{})
        require(clock['state']=='synchronized' and int(clock['uncertainty_ns'])<=500000000,'standalone UTC admission')
        now=int(clock['utc_now_ns'])/1e9
        first=(int(now)//120+1)*120+1
        if first-now<35:first+=120
        slots=[first+120*i for i in range(a.frames)]
        config=copy.deepcopy(old);config.update(enabled=True,expires_utc_s=slots[-1]+113,
            station=dict(callsign='AA0NT',locator='EM18',power_dbm=37),
            schedules=[dict(period_s=86400,phase_s=(slot-1)%86400) for slot in slots])
        from phase14_reference import gps
        reference=gps(3530100)
        seconds=math.ceil(slots[-1]-now)+127
        require(120<=seconds<=530,'finite standalone capture')
        settings=dict(format='CF32',sample_rate_hz=250000,bandwidth_hz=200000,center_frequency_hz=3545100,gain_db=20,channel=0,agc=False,bias_tee=False)
        argv=[CAPTURE,'--enable-physical-sdr','sdrplay','2404058C60','3545100',str(seconds*250000),'20','250000','200000','0','false','false','100000',str(seconds+12),str(rig.e.root/'capture.cf32'),str(rig.e.root/'capture.json'),'phase14-standalone']
        record=dict(schema='phase14-standalone/1',before=before,slots_utc_s=slots,frames=a.frames,
            configuration_sha256=__import__('hashlib').sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
            reference=reference,receiver_settings=settings,receiver_helper_sha256=sha256(CAPTURE),
            source_revision=before['revision'],status=[],result='PENDING')
        save(rig.e.root/'result.json',record)
        with (rig.e.root/'receiver.log').open('x') as log:
            process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            end=time.monotonic()+8
            while not (rig.e.root/'capture.cf32.incomplete').exists() or (rig.e.root/'capture.cf32.incomplete').stat().st_size<65536:
                require(process.poll() is None and time.monotonic()<end,'capture readiness');time.sleep(.05)
            time.sleep(1)
            changed=True;configured=rig.device.console('B','CONFIG '+json.dumps(config,separators=(',',':')))
            require(configured['enabled'] and not configured['reboot_required'] and not configured['suspended'],'standalone configuration active')
            expected=['eeeeeeeeeeeeeeee'+format(slot*1000000000,'016x') for slot in slots]
            observed=set();end=time.monotonic()+seconds-5
            while time.monotonic()<end:
                info=rig.info('B');s=info['status'];record['status'].append(dict(utc_ns=time.time_ns(),info=info))
                require(s['boot_id']==before['status']['boot_id'] and info['revision']==before['revision'],'standalone source/boot continuity')
                if s['state'] in ('loaded','armed','running'):
                    require(s['owner_id']=='eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee' and s['job_id'] in expected,'actual standalone authority')
                if s['state']=='running':observed.add(s['job_id'])
                if len(observed)==a.frames and s['owner_id'] is None and not s['output_active'] and s['state'] in ('empty','complete'):
                    break
                time.sleep(.5)
            else:raise TimeoutError('all finite standalone frames not completed')
            require(int(info['status']['watermark_utc_ns'])==slots[-1]*1000000000,'durable final reservation')
            require(info['status']['last_error'] is None,'standalone job error')
            record['completed_info']=info
            restored=rig.device.console('B','CONFIG '+json.dumps(old,separators=(',',':')));changed=False
            require(not restored['enabled'] and not restored['reboot_required'],'original disabled config restored')
            record['after']=rig.idle('B')
            require(process.wait(timeout=max(1,end-time.monotonic()+20))==0,'complete standalone capture')
            meta=json.loads((rig.e.root/'capture.json').read_text());validate_capture(meta,rig.e.root/'capture.cf32',settings)
            record.update(result='CONTROL_COMPLETE',job_ids=expected,capture_sha256=meta['output']['sha256'],metadata_sha256=sha256(rig.e.root/'capture.json'))
            save(rig.e.root/'result.json',record)
        print(json.dumps(dict(result=record['result'],frames=a.frames,slots_utc_s=slots)))
    except BaseException as error:
        if record:record.update(result='FAILED',error=repr(error));save(rig.e.root/'result.json',record)
        raise
    finally:
        try:
            if changed:
                info=rig.info('B');s=info['status']
                if s['owner_id']=='eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee' and s['state'] in ('loaded','armed','running'):
                    rig.device.console('B','ABORT')
                info=rig.info('B');require(not info['status']['output_active'],'standalone cleanup output unknown')
                rig.device.console('B','CONFIG '+json.dumps(old,separators=(',',':')))
                require(not rig.info('B')['status']['enabled'],'standalone recurrence cleanup')
        finally:
            try:
                if process and process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
            finally:rig.close()


if __name__=='__main__':main()
