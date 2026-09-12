"""Hardware-free adversarial remaining-mode scope, USB sequencing and evidence checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r2_modes_plan import SCHEMA,SOURCE,PHYSICAL,jobs,validate
from phase11_5_r2_usb_jobs import USBJobs
from phase11_5_r2_modes import main
from audit_phase11_5_r2_modes import transactions,timing


def packet(path='usb'):
    p=dict(schema=SCHEMA,source_revision=SOURCE,revision=SOURCE[:12],uf2_sha256=PHYSICAL,
        serial='0BF4B4AEC9FFB344',device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',
        system_clock_hz=138000000,pio_divider=1,listener_enabled=True,rf_render_in_ram=True,
        boot_id='2'*32,owner_id='3'*32,nonce='1'*32,submission_path=path,nominal_seconds=300,
        browser_profile='N',maximum_renewals=12,jobs=jobs('1'*32,path))
    if path=='production':
        p['production_binding']=dict(phase='waiting',owner_id=p['owner_id'],identity=dict(
            boot_id=p['boot_id'],device_id=p['device_id']),job_id='a'*16+'0000000000000001',start_utc_ns='10000000000')
        p['jobs'][0]['job_id']=p['production_binding']['job_id']
    return p


class ModesTests(unittest.TestCase):
    def test_dry_run_does_not_access_host(self):
        with patch.object(sys,'argv',['modes','--root','/absent','--packet-sha256','absent']), \
             patch('phase11_5_r2_modes.Path.resolve',side_effect=AssertionError('access')):
            main()

    def test_exact_plan_and_native_duration(self):
        for path in ('usb','production'):validate(packet(path))
        self.assertEqual([j['total_duration_ns'] for j in packet()['jobs']],['35000000000','17000000000','110592000000'])
        self.assertEqual(packet('production')['jobs'][0]['total_duration_ns'],'33000000000')
        for change in (lambda p:p['jobs'].pop(),lambda p:p['jobs'][0]['events'][0].update(duration_ns='2'),
                       lambda p:p.update(source_revision='f'*40),lambda p:p.update(system_clock_hz=150000000),
                       lambda p:p.update(maximum_renewals=13),lambda p:p.update(nominal_seconds=600),
                       lambda p:p.update(owner_id='0'*32)):
            p=packet();change(p)
            with self.assertRaises(ValueError):validate(p)
        for change in (lambda p:p['production_binding'].update(phase='executing'),
                       lambda p:p['production_binding'].update(job_id='a'*16+'0000000000000002'),
                       lambda p:p['production_binding']['identity'].update(boot_id='4'*32)):
            p=packet('production');change(p)
            with self.assertRaises(ValueError):validate(p)

    def test_upload_source_and_write_allowance_are_specific(self):
        from phase11_5_r2_upload_plan import SOURCE as source, PHYSICAL as physical
        from phase11_5_device_management import authorize
        p=packet();p.update(source_revision=source,revision=source[:12],uf2_sha256=physical)
        validate(p)
        bad=copy.deepcopy(p);bad['uf2_sha256']='f'*64
        with self.assertRaises(ValueError):validate(bad)
        now=10**9
        state=dict(source_revision=source,pending=None,blocked=False,
            deadline_monotonic_ns=now+10**9,counts={'config':32,'wifi-off':0,'wifi-on':0,'heap-probe':6})
        with patch('phase11_5_device_management.time.monotonic_ns',return_value=now):
            authorize(state,'config','test')
            state['counts']['config']=33
            with self.assertRaises(ValueError):authorize(state,'config','test')
            authorize(state,'config','original')
            state['counts']['config']=34
            with self.assertRaises(ValueError):authorize(state,'config','original')
            state['source_revision']=SOURCE;state['counts']['config']=32
            with self.assertRaises(ValueError):authorize(state,'config','original')

    def test_usb_actor_single_endpoint_finite_sequence_and_renewal(self):
        p=packet();now=[10**9];calls=[];epoch=[0]
        class Peer:
            def request(self,op,body=None):
                calls.append((op,body))
                if op in ('CLAIM','RENEW'):return dict(expires_monotonic_ns=str(now[0]+60*10**9))
                if op=='GET_CLOCK':return dict(state='synchronized',leap='normal',uncertainty_ns='1',utc_now_ns=str(now[0]))
                if op=='ARM':return dict(start_utc_ns=body['start_utc_ns'])
                return {}
        with tempfile.TemporaryDirectory() as temp,patch('phase11_5_r2_usb_jobs.time.monotonic_ns',side_effect=lambda:now[0]):
            root=Path(temp);(root/'ready.json').write_text(json.dumps(dict(boot_id=p['boot_id'],start_monotonic_ns=0)))
            actor=USBJobs(p,root,Peer(),lambda *a:None,lambda:None)
            actor.info=lambda:dict(launch_epoch=str(epoch[0]),status=dict(state='complete',monotonic_now_ns=str(now[0])))
            for job in p['jobs']:
                actor.observe(dict(state='empty',owner_id=None,output_active=False))
                actor.observe(dict(state='loaded',job_id=job['job_id']))
                now[0]+=41*10**9
                actor.observe(dict(state='running',job_id=job['job_id']))
                epoch[0]+=1
                actor.observe(dict(state='complete',job_id=job['job_id'],output_active=False))
                actor.observe(dict(state='empty',owner_id=None,output_active=False))
            self.assertTrue(actor.complete)
            self.assertEqual([c[0] for c in calls],['CLAIM','LOAD','GET_CLOCK','ARM','RENEW','RELEASE']*3)
            before=len(calls);actor.observe({});self.assertEqual(before,len(calls))

    def test_failed_load_prevents_usb_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'ready.json').write_text('{}');(root/'load-failed.json').write_text('{}')
            actor=USBJobs(packet(),root,None,None,None)
            actor.observe({});self.assertTrue(actor.blocked);self.assertFalse(actor.complete)

    def test_per_mode_counter_epoch_and_cumulative_short_evidence(self):
        p=packet();rows=[];arms=[]
        base=dict(allocator_largest_successful_request_bytes=18364,launch_epoch='0',
            dma_irqs=0,alarm_irqs=0,tail_irqs=0,running_successor_links=0,
            refill_irq_pairs=0,running_tail_links=0,refill_short_predecessor=None)
        for n,job in enumerate(p['jobs']):
            start=(n+1)*10**12;arms.append(dict(job=job,monotonic_ns=start,start_utc_ns=str(start)))
            rows.append(dict(kind='info',monotonic_ns=start-1,value=dict(value=copy.deepcopy(base))))
            current=copy.deepcopy(base);samples=138000000*int(job['total_duration_ns'])//10**9
            blocks=(samples+524287)//524288
            for key,delta in dict(dma_irqs=blocks+1,alarm_irqs=1,tail_irqs=1,
                running_successor_links=blocks-1,refill_irq_pairs=blocks-1,running_tail_links=1).items():
                current[key]=base.get(key,0)+delta
            short=(samples%524288+31)//32
            # Retain the first job's worst fraction, as the actual instrumentation does.
            worst=base['refill_short_predecessor'] or dict(total_words=short,remaining_words=short//2,observations=0)
            current.update(launch_epoch=str(n+1),launch_target_ns=str(start),launch_observed_ns=str(start+12000),
                launch_delay_ns='12000',max_dma_irq_ns='100000',max_refill_irq_to_ready_ns='2000000',
                refill_short_predecessor=dict(worst,observations=n+1),
                refill_full_predecessor=dict(total_words=16384,remaining_words=8192),
                status=dict(state='running',utc_now_ns=str(start),monotonic_now_ns=str(start),uncertainty_ns='1000'))
            rows.append(dict(kind='info',monotonic_ns=start+1,value=dict(value=copy.deepcopy(current))))
            current['status']['state']='empty'
            rows.append(dict(kind='info',monotonic_ns=start+2,value=dict(value=copy.deepcopy(current))))
            base=current
        intact=timing(p,arms,rows);self.assertEqual(len(intact),3)
        self.assertNotEqual(intact[-1]['short_words'],intact[-1]['cumulative_worst_short']['total_words'])
        for key,bad in [('tail_irqs',0),('refill_irq_pairs',0),('launch_delay_ns','13'),
                        ('launch_epoch','1'),('max_refill_irq_to_ready_ns','2849392'),
                        ('allocator_largest_successful_request_bytes',18365)]:
            mutated=copy.deepcopy(rows);mutated[-1]['value']['value'][key]=bad
            with self.assertRaises(ValueError):timing(p,arms,mutated)
        self.assertEqual(timing(p,arms,rows),intact)

    def test_changed_or_missing_wire_cannot_pass(self):
        p=packet('production');j=p['jobs'][0];ex=[]
        for op,body in [('CLAIM',dict(owner_id=p['owner_id'],lease_ms=60000)),('LOAD',j),
            ('ARM',dict(job_id=j['job_id'],start_utc_ns='10000000000',max_start_uncertainty_ns='500000000')),
            ('RELEASE',{})]:
            ex.append(dict(request=dict(op=op,body=body),response=dict(body=dict(start_utc_ns='10000000000',
                clock=dict(state='synchronized',leap='normal'))),started_ns=1))
        events=[dict(event='JOB_STATE',body=dict(job_id=j['job_id'],state=s,output_active=s=='running'))
                for s in ('loaded','armed','running','complete')]
        self.assertEqual(len(transactions(p,ex,events)),1)
        for mutate in (lambda a:a.pop(),lambda a:a.append(a[-1]),lambda a:a[1]['request']['body'].update(total_duration_ns='1'),
                       lambda a:a[0]['request']['body'].update(owner_id='f'*32)):
            v=copy.deepcopy(ex);mutate(v)
            with self.assertRaises(ValueError):transactions(p,v,events)
        with self.assertRaises(ValueError):transactions(p,ex,events[:-1])
        with self.assertRaises(ValueError):timing(p,[],[])

if __name__=='__main__':unittest.main()
