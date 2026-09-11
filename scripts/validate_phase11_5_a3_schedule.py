#!/usr/bin/env python3
"""Hardware-free A3 scheduling check against an explicitly selected Pi driver."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

from phase11_5_browser_jobs import ARM_LEAD_NS,finite_start


def scenario(schedule,lead,durations,phase):
    now=[0.];available=[0.];steps=['HELLO']+['CLAIM','LOAD','ARM','RELEASE']*3
    controls=[];requests=[]
    class Stop:
        def is_set(self):return False
        def wait(self,seconds):now[0]+=seconds
    def observed(t):return math.ceil((t-phase)/5)*5+phase
    def get(path):
        requests.append((path,now[0]))
        now[0]+=durations[0] if path=='/api/v1/status' else durations[1]
    def grant(deadline):
        if not steps or now[0]<available[0]:return False
        op=steps.pop(0);began=now[0];now[0]+=durations[2]
        assert now[0]<=deadline,'Request exceeds browser permit'
        if op=='LOAD':available[0]=observed(now[0])+2
        elif op=='ARM':
            if lead==ARM_LEAD_NS/1e9:
                finite_start(dict(clock_state='synchronized',uncertainty_ns='500000000',
                                  utc_now_ns='1000000000000'),
                             round(began*1e9),180_000_000_000,10_000_000_000)
            available[0]=observed(began+lead+10)
        elif op=='RELEASE':available[0]=observed(now[0])
        else:available[0]=now[0]
        controls.append((op,began));return True
    schedule(0,180,Stop(),get,clock=lambda:now[0],grant_control=grant)
    assert sum(p=='/api/v1/status' for p,t in requests)==36
    for begin in range(0,180,30):
        assert sorted(p for p,t in requests if begin<=t<begin+30 and p!='/api/v1/status')==[
            '/','/app.js','/style.css']
    return dict(lead_seconds=lead,durations=durations,usb_phase_seconds=phase,
                controls=len(controls),final_observation_seconds=available[0],
                complete=not steps and available[0]<=180)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',type=Path,required=True);args=parser.parse_args()
    sys.path.insert(0,str(args.driver.resolve().parent))
    spec=importlib.util.spec_from_file_location('tested_pi_driver',args.driver)
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    rows=[scenario(driver.browser_schedule,lead,durations,phase)
          for lead in (12,ARM_LEAD_NS/1e9)
          for durations in ((1.5,2,2),(2,2,2),(2.3,2.5,2.3)) for phase in range(5)]
    assert any(not r['complete'] for r in rows if r['lead_seconds']==12)
    assert all(r['complete'] for r in rows if r['lead_seconds']==ARM_LEAD_NS/1e9)
    print(json.dumps(dict(driver_sha256=hashlib.sha256(args.driver.read_bytes()).hexdigest(),
        scenarios=rows,limitation='Deterministic scheduling feasibility; no target or RF acceptance'),indent=2))


if __name__=='__main__':main()
