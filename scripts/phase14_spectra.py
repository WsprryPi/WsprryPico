#!/usr/bin/env python3
"""Finite raw-GP2 harmonic/image survey with on/off and receiver-gain controls."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.live import Rig,CAPTURE,save
from phase14.candidate import candidate
from phase14.plan import BANDS,job,accepted_events,validate_capture,validate_spectral_window
from phase14.spectral_control import wait_complete
from led_closeout.runner import require,sha256


def capture(rig,label,frequency,gain):
    root=rig.e.root/label;root.mkdir(mode=0o700)
    settings=dict(format='CF32',sample_rate_hz=250000,bandwidth_hz=200000,center_frequency_hz=frequency-25000,gain_db=gain,channel=0,agc=False,bias_tee=False)
    argv=[CAPTURE,'--enable-physical-sdr','sdrplay','2404058C60',str(frequency-25000),'500000',str(gain),'250000','200000','0','false','false','100000','15',str(root/'capture.cf32'),str(root/'capture.json'),label]
    with (root/'receiver.log').open('x') as log:
        subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,timeout=20,check=True)
    meta=json.loads((root/'capture.json').read_text());validate_capture(meta,root/'capture.cf32',settings)
    require(meta['requested_sample_count']==meta['retained_sample_count']==500000,'complete two-second spectral capture required')
    from analyze_rf_bench import load_capture
    import numpy as np
    iq,_,digest=load_capture(root/'capture.cf32',root/'capture.json')
    n=262144;window=np.hanning(n);power=np.abs(np.fft.fft(iq[:n]*window))**2/(window.sum()**2)
    bins=frequency-25000+np.fft.fftfreq(n,1/250000)
    selected=np.flatnonzero(np.abs(bins-frequency)<2000);at=selected[np.argmax(power[selected])]
    noise=power[(np.abs(bins-frequency)>5000)&(np.abs(bins-frequency)<15000)]
    value=dict(path=str(root),frequency_hz=frequency,gain_db=gain,receiver_settings=settings,
        capture_sha256=digest,metadata_sha256=sha256(root/'capture.json'),receiver_helper_sha256=sha256(CAPTURE),
        peak_hz=float(bins[at]),peak_dbfs=float(10*np.log10(max(float(power[at]),1e-300))),
        local_noise_dbfs=float(10*np.log10(max(float(np.median(noise)),1e-300))),fft_samples=n,bin_width_hz=250000/n)
    save(root/'spectrum.json',value);return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--board',choices=('A','B'),required=True);p.add_argument('--band',choices=('80m','6m'),required=True)
    a=p.parse_args();require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    manifest,image,_=candidate(ROOT);os.umask(0o077);rig=Rig(a.output,ROOT,board=a.board,receiver=True)
    peer=None;owner=uuid.uuid4().hex;claimed=False;submitted=None
    record=dict(schema='phase14-spectra/1',board=a.board,band=a.band,source_commit=manifest['source_commit'],firmware_sha256=image['sha256'],
        spectra_script_sha256=sha256(__file__),result='PENDING',captures=[],status=[],release_qualified=False,
        limitations=['Raw unfiltered path; operator develops and applies LPF.',
            'Relative dBFS at each receiver tune/gain; uncalibrated cross-frequency path and receiver response.',
            'On/off attribution and gain controls do not exclude every receiver-generated product.'])
    try:
        before=rig.idle(a.board);rig.idle('B' if a.board=='A' else 'A')
        require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000,'spectral candidate source/clock')
        from phase14_reference import gps
        record['reference_before']=gps()
        record['before']=before;record['boot_id']=before['status']['boot_id'];frequency=BANDS[a.band];clock=138000000
        targets=[('harmonic-'+str(n),frequency*n) for n in range(1,6)]+[
            ('clock-minus',clock-frequency),('clock-plus',clock+frequency),('2clock-minus',2*clock-frequency),
            ('2clock-plus',2*clock+frequency),('clock',clock),('2clock',2*clock)]
        record['targets']=targets;save(rig.e.root/'result.json',record)
        for label,tune in targets:
            for gain in (12,20):record['captures'].append(dict(state='off',target=label,measurement=capture(rig,'off-'+label+'-'+str(gain),tune,gain)))
        peer=rig.device.peer(a.board);peer.request('CLAIM',dict(owner_id=owner,lease_ms=60000));claimed=True
        # Twenty-two separately initialized captures leave little margin in
        # the previous 120-second window at the observed helper cadence. Keep
        # a finite margin and reject any capture that reaches completion.
        submitted=job('TONE',a.band,138000000,uuid.uuid4().hex,240)
        loaded=peer.request('LOAD',submitted,timeout=30);record['accepted_job']=accepted_events(submitted,loaded['adjustments']);record['load']=loaded
        utc=peer.request('GET_CLOCK',{});require(utc['state']=='synchronized' and int(utc['uncertainty_ns'])<=500000000,'spectral UTC admission')
        record['arm']=peer.request('ARM',dict(job_id=submitted['job_id'],start_utc_ns=str((int(utc['utc_now_ns'])//1000000000+4)*1000000000),max_start_uncertainty_ns='500000000'))
        end=time.monotonic()+250
        while time.monotonic()<end:
            s=peer.request('STATUS',{});record['status'].append(s)
            if s['state']=='running':break
            require(s['state']=='armed','spectral launch did not run');time.sleep(.2)
        require(s['state']=='running','spectral launch deadline')
        for label,tune in targets:
            for gain in (12,20):
                before_capture=peer.request('STATUS',{})
                validate_spectral_window(before_capture,before_capture,record['boot_id'],submitted['job_id'])
                measurement=capture(rig,'on-'+label+'-'+str(gain),tune,gain)
                after_capture=peer.request('STATUS',{})
                validate_spectral_window(before_capture,after_capture,record['boot_id'],submitted['job_id'])
                record['captures'].append(dict(state='on',target=label,measurement=measurement,
                    status_before=before_capture,status_after=after_capture))
                peer.request('RENEW',dict(owner_id=owner,lease_ms=60000));rig.info(a.board)
        wait_complete(peer,owner,record['boot_id'],submitted['job_id'],end,record['status'])
        peer.request('RELEASE',{});claimed=False;record['after']=rig.idle(a.board)
        record['final_off']=capture(rig,'final-off-fundamental',frequency,20)
        on_fundamental=next(v['measurement'] for v in record['captures'] if v['state']=='on' and v['target']=='harmonic-1' and v['measurement']['gain_db']==20)
        quiet_contrast=on_fundamental['peak_dbfs']-record['final_off']['peak_dbfs']
        record['final_quiet_contrast_db']=quiet_contrast
        require(quiet_contrast>=10,'spectral RF-off capture contrast insufficient')
        record['reference_after']=gps()
        require(record['reference_after']==record['reference_before'],'spectral reference settings/readiness changed')
        pairs=[]
        for label,tune in targets:
            for gain in (12,20):
                off=next(v['measurement'] for v in record['captures'] if v['state']=='off' and v['target']==label and v['measurement']['gain_db']==gain)
                on=next(v['measurement'] for v in record['captures'] if v['state']=='on' and v['target']==label and v['measurement']['gain_db']==gain)
                pairs.append(dict(target=label,tune_hz=tune,gain_db=gain,on_minus_off_db=on['peak_dbfs']-off['peak_dbfs'],on_peak_hz=on['peak_hz'],on_peak_dbfs=on['peak_dbfs']))
        record.update(result='CONTROL_COMPLETE',comparisons=pairs);save(rig.e.root/'result.json',record)
        print(json.dumps(dict(result=record['result'],board=a.board,band=a.band,targets=len(targets))))
    except BaseException as error:
        record.update(result='FAILED',error=repr(error));save(rig.e.root/'result.json',record);raise
    finally:
        try:
            if claimed:
                s=rig.info(a.board)['status']
                if submitted and s['job_id']==submitted['job_id'] and s['state'] in ('loaded','armed','running'):rig.device.console(a.board,'ABORT')
                require(not rig.info(a.board)['status']['output_active'],'spectral cleanup output unknown')
                if peer:peer.request('RELEASE',{})
        finally:rig.close()


if __name__=='__main__':main()
