#!/usr/bin/env python3
"""Finite installed WsprryPi job, independent Console observation and full IQ capture."""
import argparse
import configparser
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from phase14.live import Rig,CAPTURE,save
from phase14.plan import validate_capture
from led_closeout.runner import require,sha256


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--template',type=Path,required=True);p.add_argument('--mode',choices=('WSPR','QRSS','FSKCW','DFCW'),required=True)
    p.add_argument('--message',choices=('ETE','T'*32),default='ETE');p.add_argument('--dot',type=float,default=3)
    a=p.parse_args();require(os.geteuid()==0 and sys.platform.startswith('linux'),'exclusive Linux owner')
    require(0<a.dot<=3 and 1<=len(a.message)<=32,'finite message workload')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    def interrupted(signum,frame):raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    os.umask(0o077);rig=Rig(a.output,ROOT,board='A',receiver=True,reference=True)
    capture=controller=None;current_job=None;before=None
    try:
        from phase14.candidate import candidate
        manifest,image,_=candidate(ROOT)
        before=rig.idle('A');rig.idle('B');require(before['system_clock_hz']==138000000 and before['revision']==manifest['source_commit'][:12],'qualified candidate identity')
        config=configparser.ConfigParser();config.optionxform=str;config.read(a.template)
        for section,values in {
            'Meta':{'Loop TX':'false','TX Iterations':'1','debug_logging':'true'},
            'Operation':{'Mode':a.mode,'Transmit':'true' if a.mode=='WSPR' else 'false','Transmit Backend':'wtp',
                'Enable on Boot':'Never','Use LED':'false','Use Amp':'false','Use Shutdown':'false','Web Port':'31580','Socket Port':'31581'},
            'WTP Server':{'Enabled':'false'},'Experimental':{'Allow Unqualified Frequency':'true'},
            'WTP':{'Transport':'network_plain','Hostname':before['network']['ipv4'],'TCP Port':'31417',
                'Device ID':before['device_id'],'Start Uncertainty ns':'500000000','Allow Frequency Adjustment':'true'},
            'WSPR':{'Call Sign':'AA0NT','Grid Square':'EM18','TX Power':'37','Frequency':'3568600','Use Random Offset':'false'},
            'CW':{'Fade Shape':'none','Fade In Ms':'0','Fade Out Ms':'0','Fade Slice Ms':'5','DFCW Inter Character Gap':'1.0'}}.items():
            if section not in config:config[section]={}
            config[section].update(values)
        ini=rig.e.root/'controller.ini'
        with ini.open('x') as f:config.write(f)
        argv=['/usr/local/bin/wsprrypi','--backend','wtp','--ini-file',str(ini),'--no-web','--no-led','--no-amp-pin','--no-shutdown']
        require(Path(argv[0]).exists(),'installed controller path')
        if a.mode=='QRSS':argv+=['--qrss-message',a.message,'--qrss-frequency','3570100','--qrss-dot-seconds',str(a.dot)]
        elif a.mode=='FSKCW':argv+=['--fskcw-message',a.message,'--fskcw-mark-frequency','3570100','--fskcw-space-frequency','3570095','--fskcw-dot-seconds',str(a.dot)]
        elif a.mode=='DFCW':argv+=['--dfcw-message',a.message,'--dfcw-dot-frequency','3570100','--dfcw-dash-frequency','3570095','--dfcw-dot-seconds',str(a.dot)]
        # Largest supported message at dot <=3 is <=2,016 seconds (32 all-dash Morse digits),
        # but the requested ETE or 32 T workload is much shorter. Cap all invocations.
        seconds=270 if a.mode=='WSPR' else (650 if len(a.message)>3 else 85)
        from phase14_reference import gps
        reference=gps(3530100)
        settings=dict(format='CF32',sample_rate_hz=250000,bandwidth_hz=200000,center_frequency_hz=3545100,gain_db=20,channel=0,agc=False,bias_tee=False)
        command=[CAPTURE,'--enable-physical-sdr','sdrplay','2404058C60','3545100',str(seconds*250000),'20','250000','200000','0','false','false','100000',str(seconds+12),str(rig.e.root/'capture.cf32'),str(rig.e.root/'capture.json'),'phase14-controller-'+a.mode]
        record=dict(schema='phase14-controller/1',mode=a.mode,message=a.message,dot_s=a.dot,before=before,firmware_sha256=image['sha256'],source_commit=manifest['source_commit'],
                    controller_command=argv,controller_sha256=sha256(argv[0]),receiver_command=command,
                    receiver_settings=settings,reference=reference,status=[],result='PENDING')
        save(rig.e.root/'result.json',record)
        with (rig.e.root/'receiver.log').open('x') as caplog,(rig.e.root/'controller.log').open('x') as ctrlog:
            capture=subprocess.Popen(command,stdout=caplog,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+8
            while not (rig.e.root/'capture.cf32.incomplete').exists() or (rig.e.root/'capture.cf32.incomplete').stat().st_size<65536:
                require(capture.poll() is None and time.monotonic()<deadline,'capture readiness');time.sleep(.05)
            time.sleep(1)
            controller=subprocess.Popen(argv,stdout=ctrlog,stderr=subprocess.STDOUT,start_new_session=True)
            end=time.monotonic()+seconds-5;seen_running=False;last=None
            while time.monotonic()<end:
                info=rig.info('A');s=info['status'];record['status'].append(dict(utc_ns=time.time_ns(),info=info))
                require(info['revision']==before['revision'] and s['boot_id']==before['status']['boot_id'],'source/boot continuity')
                if s['state'] in ('loaded','armed','running'):
                    require(s['owner_id'] is not None and s['job_id'] is not None,'current controller identity')
                    require(current_job in (None,s['job_id']),'unexpected repeated controller job');current_job=s['job_id']
                if s['state']=='running':seen_running=True
                if controller.poll() is not None:
                    require(controller.returncode==0 and seen_running and not s['output_active'] and s['owner_id'] is None,'finite controller completion')
                    break
                time.sleep(.5)
            else:raise TimeoutError('finite controller deadline')
            record['after']=rig.idle('A');require(capture.wait(timeout=max(1,end-time.monotonic()+20))==0,'complete capture')
            meta=json.loads((rig.e.root/'capture.json').read_text());validate_capture(meta,rig.e.root/'capture.cf32',settings)
            record.update(result='CONTROL_COMPLETE',job_id=current_job,capture_sha256=meta['output']['sha256'],metadata_sha256=sha256(rig.e.root/'capture.json'))
            save(rig.e.root/'result.json',record)
        print(json.dumps(dict(mode=a.mode,result=record['result'],job_id=current_job)))
    except BaseException as error:
        if 'record' in locals():
            record.update(result='FAILED',error=repr(error));save(rig.e.root/'result.json',record)
        raise
    finally:
        try:
            if controller and controller.poll() is None:
                os.killpg(controller.pid,signal.SIGINT)
                try:controller.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(controller.pid,signal.SIGKILL);controller.wait(timeout=3)
            if before:
                info=rig.info('A');s=info['status']
                if current_job and s['job_id']==current_job and s['state'] in ('loaded','armed','running'):
                    rig.device.console('A','ABORT')
                require(rig.info('A')['status']['output_active'] is False,'controller cleanup output unknown')
        finally:
            try:
                if capture and capture.poll() is None:
                    os.killpg(capture.pid,signal.SIGTERM)
                    try:capture.wait(timeout=3)
                    except subprocess.TimeoutExpired:os.killpg(capture.pid,signal.SIGKILL);capture.wait(timeout=3)
            finally:rig.close()


if __name__=='__main__':main()
