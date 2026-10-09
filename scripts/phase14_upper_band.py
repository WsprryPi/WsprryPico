#!/usr/bin/env python3
"""Complete finite 4 m repetitions and verify direct 2 m rejection at every clock."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.plan import job,BANDS
from phase14.live import Rig,save
from phase14.candidate import candidate
from led_closeout.runner import require,sha256


def reject_2m(peer,evidence,mode,clock):
    from phase11_5_inventory import exchange
    from validate_wtp_contract import frame
    value=job(mode,'80m',clock,uuid.uuid4().hex)
    for event in value['events']:
        if event['rf_on']:event['frequency_nhz']=str(int(event['frequency_nhz'])+(BANDS['2m']-BANDS['80m'])*1000000000)
    owner=uuid.uuid4().hex;claimed=False;response=None
    try:
        peer.request('CLAIM',dict(owner_id=owner,lease_ms=60000));claimed=True
        request=dict(type='request',protocol='WTP/1',session_id=peer.session,request_id=uuid.uuid4().hex,op='LOAD',body=value)
        response=exchange(peer.fd,frame(json.dumps(request,separators=(',',':')).encode()),time.monotonic()+30,
            peer.emit,True,expected=request,receive_buffer=peer.received)
        evidence.event('direct_2m_load_observation',dict(request=request,response=response,arm_attempted=False))
        require(not peer.validator.errors(response,peer.schema) and response.get('ok') is False and
            response.get('error',{}).get('code')=='FREQUENCY_REJECTED','direct 2 m did not reject outside its advertised range')
        return dict(mode=mode,clock_hz=clock,frequency_hz=BANDS['2m'],request=request,response=response,
            arm_attempted=False,disposition='UNSUPPORTED_CONFIGURATION')
    finally:
        if claimed:
            s=peer.request('STATUS',{})
            require(s['owner_id']==owner,'negative frequency probe authority changed')
            if s['job_id']==value['job_id'] and s['state'] in ('loaded','armed','running'):
                peer.request('ABORT',dict(job_id=value['job_id']))
            require(peer.request('STATUS',{})['output_active'] is False,'negative frequency probe output uncertain')
            peer.request('RELEASE',{})


def main():
    from phase14.analysis import analyze
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--comparison',type=Path,required=True);a=p.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private upper-band evidence')
    old=json.loads((a.comparison/'rows.json').read_text())
    os.umask(0o077);a.output.mkdir(parents=True,mode=0o700,exist_ok=False)
    record=dict(schema='phase14-upper-band/1',comparison_sha256=sha256(a.comparison/'rows.json'),initial_4m=[],jobs=[],negative_loads=[],result='PENDING',release_qualified=False)
    for clock in (132000000,150000000,138000000):
        manifest,image,uf2=candidate(ROOT,clock)
        for board in ('A','B'):
            rig=Rig(a.output/(str(clock)+'-'+board),ROOT,board=board,receiver=True,reference=True)
            try:
                rig.image_hash=image['sha256'];rig.deploy(board,uf2,manifest['source_commit'])
                sequence=0
                if clock==150000000:
                    for mode in ('TONE','WSPR','QRSS','FSKCW','DFCW'):
                        prior=[r for r in old if r['board']==board and r['clock_hz']==clock and r['band']=='4m' and r['mode']==mode]
                        require(len(prior)==1,'one exact initial 4 m screen required')
                        accepted=False
                        if prior[0].get('path'):
                            path=Path(prior[0]['path']);analysis=path/'analysis-clock-comparison/result.json'
                            require(path.resolve().is_relative_to(a.comparison.resolve()),'initial 4 m path binding')
                            if analysis.exists():
                                report=json.loads(analysis.read_text())
                                require(report['source_revision']==manifest['source_commit'][:12] and report['firmware_sha256']==image['sha256'] and
                                    report['board']==board and report['clock_hz']==clock and report['mode']==mode and report['band']=='4m','initial 4 m candidate binding')
                                accepted=report['resources']['passed'] and (report['wspr_decode_acceptance']['passed'] if mode=='WSPR' else
                                    report['human_copy']['overall_screen_passed'] if mode!='TONE' else report['disposition']=='OPERATIONAL_SCREEN_PASS')
                                record['initial_4m'].append(dict(board=board,mode=mode,path=str(analysis),sha256=sha256(analysis),accepted_for_reuse=accepted))
                        required=1 if mode=='TONE' else 3
                        for repeat in range(required-int(bool(accepted))):
                            sequence+=1;directory=rig.execute(board,clock,'4m',mode,sequence,image_hash=image['sha256'])
                            analyze(directory,'analysis-upper-band');r=json.loads((directory/'analysis-upper-band/result.json').read_text())
                            record['jobs'].append(dict(board=board,clock_hz=clock,band='4m',mode=mode,path=str(directory),analysis_sha256=sha256(directory/'analysis-upper-band/result.json'),
                                wspr_decode_acceptance=r.get('wspr_decode_acceptance'),human_copy=r.get('human_copy'),resources=r['resources'],legacy_disposition=r['disposition']))
                            save(a.output/'result.json',record)
                peer=rig.device.peer(board)
                for mode in ('TONE','WSPR','QRSS','FSKCW','DFCW'):
                    record['negative_loads'].append(dict(board=board,**reject_2m(peer,rig.e,mode,clock)));save(a.output/'result.json',record)
                rig.inventory([board])
            except BaseException as error:
                record.update(result='FAILED',error=repr(error));save(a.output/'result.json',record);raise
            finally:rig.close()
    require(len(record['negative_loads'])==30,'both boards/all clocks/all modes direct 2 m coverage')
    record['result']='FINITE_UPPER_BAND_COMPLETE';save(a.output/'result.json',record)
    print(json.dumps(dict(result=record['result'],additional_4m_jobs=len(record['jobs']),direct_2m_negative_loads=30,release_qualified=False)))


if __name__=='__main__':
    def interrupted(signum,frame):signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted);main()
