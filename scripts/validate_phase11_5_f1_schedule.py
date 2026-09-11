#!/usr/bin/env python3
"""Hardware-free finite F1/lease feasibility against the actual Pi browser scheduler."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

from phase11_5_f1_plan import jobs,MAX_RENEWALS,NOMINAL_SECONDS
from phase11_5_browser_jobs import finite_start


def scenario(schedule,durations,phase):
    now=[0.];state=['HELLO'];available=[0.];lease=[0.];complete=[0.]
    index=[0];renewals=[0];requests=[];controls=[];sequence=jobs('d'*32)
    def observed(t):return math.ceil((t-phase)/5)*5+phase
    class Stop:
        def is_set(self):return False
        def wait(self,seconds):now[0]+=seconds
    def get(path):
        requests.append((path,now[0]))
        now[0]+=durations[0] if path=='/api/v1/status' else durations[1]
    def grant(deadline):
        if state[0]=='DONE' or now[0]<available[0]:return False
        operation=state[0]
        if operation=='WAIT':
            if now[0]>=complete[0]:operation='RELEASE'
            elif now[0]>=lease[0]-40:operation='RENEW'
            else:return False
        began=now[0];now[0]+=durations[2]
        assert now[0]<=deadline,'Control exceeds permit'
        if operation not in ('HELLO','CLAIM'):
            assert now[0]<lease[0],'Ownership expires before control completes'
        controls.append((operation,began))
        if operation=='HELLO':state[0]='CLAIM';available[0]=now[0]
        elif operation=='CLAIM':state[0]='LOAD';available[0]=now[0];lease[0]=began+60
        elif operation=='LOAD':state[0]='ARM';available[0]=observed(now[0])+2
        elif operation=='ARM':
            duration=int(sequence[index[0]]['total_duration_ns'])
            finite_start(dict(clock_state='synchronized',uncertainty_ns='500000000',
                              utc_now_ns='1000000000000'),round(began*1e9),NOMINAL_SECONDS*1_000_000_000,duration)
            state[0]='WAIT';available[0]=now[0];complete[0]=observed(began+10+duration/1e9)
        elif operation=='RENEW':
            state[0]='WAIT';available[0]=now[0];lease[0]=began+60;renewals[0]+=1
            assert renewals[0]<=MAX_RENEWALS,'Finite renewal budget exceeded'
        elif operation=='RELEASE':
            index[0]+=1;state[0]='DONE' if index[0]==15 else 'CLAIM';available[0]=observed(now[0])
        return True
    schedule(0,NOMINAL_SECONDS,Stop(),get,clock=lambda:now[0],grant_control=grant)
    assert state[0]=='DONE' and available[0]<=NOMINAL_SECONDS,'Incomplete finite family'
    assert sum(path=='/api/v1/status' for path,t in requests)==NOMINAL_SECONDS//5
    for begin in range(0,NOMINAL_SECONDS,30):
        assert sorted(path for path,t in requests if begin<=t<begin+30 and path!='/api/v1/status')==[
            '/','/app.js','/style.css']
    assert [op for op,t in controls if op!='RENEW']==['HELLO']+['CLAIM','LOAD','ARM','RELEASE']*15
    return dict(durations=durations,usb_phase_seconds=phase,jobs=index[0],renewals=renewals[0],
                final_observation_seconds=available[0])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',type=Path,required=True);args=parser.parse_args()
    sys.path.insert(0,str(args.driver.resolve().parent))
    spec=importlib.util.spec_from_file_location('tested_pi_driver',args.driver)
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    rows=[scenario(driver.browser_schedule,durations,phase)
          for durations in ((1.5,2,2),(2,2,2),(2.3,2.5,2.3)) for phase in range(5)]
    assert any(row['renewals']>30 for row in rows),'Initial insufficient renewal budget not reproduced'
    print(json.dumps(dict(driver_sha256=hashlib.sha256(args.driver.read_bytes()).hexdigest(),
        scenarios=rows,limitation='Deterministic scheduling feasibility; no target or RF acceptance'),indent=2))


if __name__=='__main__':main()
