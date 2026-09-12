"""Bounded USB actor integrated into the sole WTP observer endpoint owner."""
import json
from pathlib import Path
import time
from phase11_5_inventory import require
from phase11_5_browser_jobs import admit_snapshot


class USBJobs:
    def __init__(self,packet,root,peer,emit,checkpoint):
        self.packet,self.root,self.peer,self.emit,self.checkpoint=packet,root,peer,emit,checkpoint
        self.index=0;self.phase='idle';self.lease=None;self.renewals=0;self.complete=False
        self.baseline_epoch=None;self.blocked=False

    def info(self):
        value=json.loads((self.root/'observer-info.json').read_text())
        require(time.monotonic_ns()-value['monotonic_ns']<=2_000_000_000,'USB actor INFO freshness')
        return value['value']['value']

    def observe(self,status):
        if self.complete:return
        ready=self.root/'ready.json'
        if not ready.exists():return
        if self.blocked or (self.root/'load-failed.json').exists():
            self.blocked=True
            return  # Keep the sole endpoint observing until its original deadline.
        start=json.loads(ready.read_text())
        require(start['boot_id']==self.packet['boot_id'],'USB load boot')
        end=start['start_monotonic_ns']+self.packet['nominal_seconds']*10**9
        job=self.packet['jobs'][self.index]
        now=time.monotonic_ns()
        require(now<end, 'USB actor outlived nominal load')
        if self.phase=='idle':
            require(status['state']=='empty' and status['owner_id'] is None and not status['output_active'],
                    'USB next job requires authoritative released idle')
            require(now+int(job['total_duration_ns'])+40_000_000_000<end,'USB finite-job time reserve')
            self.baseline_epoch=int(self.info()['launch_epoch'])
            self.lease=self.peer.request('CLAIM',dict(owner_id=self.packet['owner_id'],lease_ms=60000))
            self.peer.request('LOAD',job)
            self.phase='loaded'
        elif self.phase=='loaded':
            require(status['state']=='loaded' and status['job_id']==job['job_id'], 'USB Loaded evidence')
            clock=self.peer.request('GET_CLOCK')
            require(clock['state']=='synchronized' and clock['leap']=='normal' and
                    int(clock['uncertainty_ns'])<=500000000,'USB ARM clock')
            target=((int(clock['utc_now_ns'])+10_000_000_000+999)//1000)*1000
            arm=self.peer.request('ARM',dict(job_id=job['job_id'],start_utc_ns=str(target),max_start_uncertainty_ns='500000000'))
            require(arm['start_utc_ns']==str(target),'USB ARM target changed')
            self.emit('armed_job',dict(job=job,start_utc_ns=str(target)))
            self.phase='executing'
        elif self.phase=='executing':
            require(status['job_id']==job['job_id'] and status['state'] in ('armed','running','complete'),
                    'USB finite lifecycle')
            if status['state']=='complete':
                require(not status['output_active'],'USB completed output active')
                limit=time.monotonic()+1.5
                while True:
                    info=self.info()
                    if info['status']['state']=='complete' and int(info['launch_epoch'])>self.baseline_epoch:break
                    require(time.monotonic()<limit,'USB completed INFO missing')
                    self.checkpoint();time.sleep(.025)
                self.peer.request('RELEASE')
                self.phase='released'
            elif int(self.lease['expires_monotonic_ns'])-int(self.info()['status']['monotonic_now_ns'])<=20_000_000_000:
                require(self.renewals<self.packet['maximum_renewals'],'USB renewal limit')
                self.lease=self.peer.request('RENEW',dict(owner_id=self.packet['owner_id'],lease_ms=60000))
                self.renewals+=1
        elif self.phase=='released':
            require(status['state']=='empty' and status['owner_id'] is None and not status['output_active'],
                    'USB released authority')
            self.index+=1
            self.complete=self.index==len(self.packet['jobs'])
            self.phase='idle'
