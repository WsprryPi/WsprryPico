"""Matrix boundaries and adversarial identity/capture checks; no hardware."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.plan import matrix,job,accepted_events,validate_capture,validate_physical,capture_elapsed_limit,load_workspace_bytes

class Tests(unittest.TestCase):
    def test_2m_pilot_uses_decode_and_resources_independently_of_segment_or_drift(self):
        from phase14.wspr_segment import pilot_decision
        rows=[dict(board=b,job_id=b+str(i),decode_passed=True,resources_passed=True,
            segment=dict(observed_relation='estimates_extend_outside_window',fitted_drift_hz_s_true_axes=[-10]))
            for b in ('A','B') for i in range(3)]
        self.assertTrue(pilot_decision(rows)['expand_full_qualification'])
        self.assertFalse(pilot_decision(rows[:-1])['expand_full_qualification'])
        for key in ('decode_passed','resources_passed'):
            invalid=copy.deepcopy(rows);invalid[0][key]=False
            self.assertFalse(pilot_decision(invalid)['expand_full_qualification'])
        invalid=copy.deepcopy(rows);invalid[-1]['job_id']=invalid[0]['job_id']
        with self.assertRaises(ValueError):pilot_decision(invalid)
        invalid=copy.deepcopy(rows);invalid[-1]['board']='A'
        with self.assertRaises(ValueError):pilot_decision(invalid)

    def test_2m_placement_bounds_are_annotations_and_missing_fits_are_not_failures(self):
        from phase14.wspr_segment import assess
        from campaign.plan import GOLDEN37
        reference=dict(schema='phase14-reference/1',band='2m',center_hz=144490500,
            scale_nominal_to_true_time=1,repeatability_bound_ppm=.01,
            reference_accuracy_assumption_ppb=1,traceable_calibration=False)
        measurement=dict(reference_hz=144450500,linear_drift_hz_per_s=0,
            measurements=[dict(index=i,tone=int(t),reference_compared_hz=144490500+int(t)*1.46484375,
                interval_s=[i*.6826667+.08,(i+1)*.6826667-.08],phase_residual_rms_rad=.01,amplitude_min_ratio=1,
                reference=dict(phase_residual_rms_rad=.01,amplitude_min_ratio=1,local_contrast_db=40)) for i,t in enumerate(GOLDEN37)])
        inside=assess(dict(measurement=measurement),[reference,reference])
        self.assertEqual(inside['observed_relation'],'estimates_inside_window')
        changed=copy.deepcopy(measurement)
        for fit in changed['measurements']:fit['reference_compared_hz']-=250
        outside=assess(dict(measurement=changed),[reference,reference])
        self.assertEqual(outside['observed_relation'],'estimates_extend_outside_window')
        self.assertLess(outside['minimum_edge_clearance_hz'],0)
        for annotation in (inside,outside,assess({},[])):
            self.assertIsNone(annotation['pass_fail_determination'])
            self.assertEqual(annotation['qualification_effect'],'informational_only_no_band_exclusion')
            self.assertNotIn('passed',annotation)
        changed['measurements'][0]['tone']=9
        with self.assertRaises(ValueError):assess(dict(measurement=changed),[reference,reference])

    def test_keyed_placement_removes_frequency_states_and_preserves_drift_information(self):
        from phase14.wspr_segment import describe
        value=job('DFCW','80m',138000000,'test')
        fits=[];refs=[]
        for index,event in enumerate(value['events']):
            if not event['rf_on']:continue
            left=int(event['offset_ns'])/1e9;right=left+int(event['duration_ns'])/1e9
            fits.append(dict(event_index=index,indicated_hz=int(event['frequency_nhz'])/1e9+40+(left+right)/2*.5))
            refs.append(dict(indicated_hz=3530100+40,interval_s=[left,right]))
        result=describe(dict(measurements=fits,reference_diagnostics=refs),value,'DFCW',3530100)
        self.assertAlmostEqual(result['fitted_offset_drift_hz_per_s'],.5)
        self.assertEqual(result['observed_relation'],'window_unspecified')
        self.assertIsNone(result['pass_fail_determination'])
        self.assertGreater(result['requested_offset_excursion_hz'],0)
        bounded=describe(dict(measurements=fits,reference_diagnostics=refs),value,'DFCW',3530100,(3570100,3570101))
        self.assertEqual(bounded['observed_relation'],'mean_frequencies_extend_outside_window')
        self.assertIsNone(bounded['pass_fail_determination'])

    def test_full_2m_gate_rehashes_actual_pilot_decode_files_and_rejects_substitution(self):
        from unittest.mock import patch
        from phase14.wspr_segment import verified_pilot,pilot_decision
        from phase14.harmonic import ROUTE
        from led_closeout.runner import sha256 as actual_sha
        source='a'*40;image='b'*64;line='2359 40 -0.0 144.490100 0 AA0NT EM18 37\n'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();directory=root/'build/pilot';directory.mkdir(parents=True);rows=[]
            for index in range(6):
                job_dir=directory/str(index);analysis_dir=job_dir/'analysis-wspr-pilot';analysis_dir.mkdir(parents=True)
                physical=dict(result='CONTROL_COMPLETE',board='A' if index<3 else 'B',band='2m',mode='WSPR',clock_hz=138000000,
                    source_revision=source[:12],firmware_sha256=image,output_route=ROUTE,job=dict(job_id=str(index)*32),
                    boot_id='c'*32,receiver_settings={})
                (job_dir/'physical.json').write_text(json.dumps(physical));(job_dir/'capture.json').write_text('{}');(job_dir/'capture.cf32').write_bytes(b'iq')
                wav=analysis_dir/'test.wav';wav.write_bytes(b'wave')
                receipt=dict(command=['/usr/bin/wsprd','-d','-H','-f','144.489',str(wav)],decoded=True,returncode=0,matches=[line.rstrip()])
                for name,value in (('decode.json',json.dumps(receipt)),('wsprd.stdout',line),('wsprd.stderr','')):(analysis_dir/name).write_text(value)
                analysis={key:physical[key] for key in ('board','boot_id','clock_hz','source_revision','firmware_sha256','band','mode','output_route')}
                analysis.update(job_id=physical['job']['job_id'],decoded=True,decode=receipt,wspr_decode_acceptance=dict(passed=True),
                    resources=dict(passed=True),decoder_sha256='d'*64,**{key:actual_sha(job_dir/name) for key,name in
                    (('capture_sha256','capture.cf32'),('metadata_sha256','capture.json'),('physical_sha256','physical.json'))})
                (analysis_dir/'result.json').write_text(json.dumps(analysis))
                rows.append(dict(board=physical['board'],job_id=analysis['job_id'],boot_id=physical['boot_id'],path=str(job_dir),
                    analysis_sha256=actual_sha(analysis_dir/'result.json'),decode_passed=True,resources_passed=True,
                    decoder_files_sha256={name:actual_sha(analysis_dir/name) for name in ('decode.json','wsprd.stdout','wsprd.stderr')},
                    wav=dict(path=str(wav),sha256=actual_sha(wav)),segment=dict(observed_relation='estimates_extend_outside_window')))
            value=dict(schema='phase14-wspr-pilot/1',result='CONTROL_ANALYSIS_COMPLETE',source_commit=source,firmware_sha256=image,
                output_route=ROUTE,jobs=rows,decision=pilot_decision(rows),reference_brackets=[])
            for name in ('reference-before.json','reference-after.json'):
                reference=directory/name;reference.write_text('{}');value['reference_brackets'].append(dict(path=str(reference),sha256=actual_sha(reference)))
            path=directory/'result.json';path.write_text(json.dumps(value))
            # Capture and physical validators have their own rejection coverage;
            # isolate this new gate's complete decoder/hash/identity binding.
            with patch('phase14.plan.validate_physical',side_effect=lambda p:p),patch('phase14.plan.validate_capture'), \
                 patch('led_closeout.runner.sha256',side_effect=lambda p:'d'*64 if str(p)=='/usr/bin/wsprd' else actual_sha(p)):
                self.assertTrue(verified_pilot(path,root,source,image)['decision']['expand_full_qualification'])
                for name in ('test.wav','wsprd.stdout','decode.json'):
                    target=directory/'0/analysis-wspr-pilot'/name;before=target.read_bytes();target.write_bytes(b'substituted')
                    with self.assertRaises((ValueError,json.JSONDecodeError)):verified_pilot(path,root,source,image)
                    target.write_bytes(before)
                for key,substitute in (('source_commit','f'*40),('firmware_sha256','e'*64),('result','PENDING')):
                    invalid=copy.deepcopy(value);invalid[key]=substitute;path.write_text(json.dumps(invalid))
                    with self.assertRaises(ValueError):verified_pilot(path,root,source,image)
                path.write_text(json.dumps(value));self.assertTrue(verified_pilot(path,root,source,image)['decision']['expand_full_qualification'])

    def test_harmonic_trial_scales_frequency_states_without_changing_time_or_symbols(self):
        from phase14.harmonic import trial_job,measurement_job,ROUTE
        from campaign.plan import make_job,GOLDEN37
        for clock in (132000000,138000000,150000000):
            for mode in ('TONE','WSPR','QRSS','FSKCW','DFCW'):
                direct=make_job(mode,48163500,sample_rate_hz=clock,keyed_dot_ns=3000000000)
                value=trial_job(mode,clock,'test')
                self.assertEqual(value['total_duration_ns'],direct['total_duration_ns'])
                self.assertEqual([(e['offset_ns'],e['duration_ns'],e['rf_on']) for e in value['events']],
                    [(e['offset_ns'],e['duration_ns'],e['rf_on']) for e in direct['events']])
                physical=dict(band='2m',mode=mode,clock_hz=clock,output_route=copy.deepcopy(ROUTE),job=value,
                    accepted_job=copy.deepcopy(value),load=dict(adjustments=[]),action='complete')
                received=measurement_job(physical)
                self.assertEqual(received['job_id'],value['job_id'])
                if mode=='WSPR':
                    self.assertEqual([int(e['frequency_nhz']) for e in received['events']],
                        [144490500000000000+int(s)*1464843750 for s in GOLDEN37])
                    self.assertEqual(value['total_duration_ns'],'110592000000')
                if mode in ('FSKCW','DFCW'):
                    frequencies={int(e['frequency_nhz']) for e in received['events'] if e['rf_on']}
                    self.assertEqual(max(frequencies)-min(frequencies),5000000001)
                changed=copy.deepcopy(physical);first=next(i for i,e in enumerate(value['events']) if e['rf_on'])
                before=value['events'][first]['frequency_nhz'];after=str(int(before)+20000000)
                changed['load']['adjustments']=[dict(event_index=first,requested_frequency_nhz=before,realized_frequency_nhz=after)]
                changed['accepted_job']=accepted_events(value,changed['load']['adjustments'])
                self.assertEqual(measurement_job(changed)['events'][first]['frequency_nhz'],str(3*int(after)))
                for case in ('route','band','waveform','accepted','compensation','native_flag'):
                    changed=copy.deepcopy(physical)
                    if case=='route':changed['output_route']['harmonic']=5
                    elif case=='band':changed['band']='6m'
                    elif case=='waveform':changed['job']['events'][first]['duration_ns']='1'
                    elif case=='accepted':changed['accepted_job']['events'][first]['frequency_nhz']='1'
                    elif case=='compensation':changed['requested_frequency_compensation_ppb']=1500
                    else:changed['output_route']['native_output_frequency_api']=0
                    with self.assertRaises(ValueError):measurement_job(changed)
    def test_direct_2m_rejection_never_arms_and_cleans_unexpected_load(self):
        from phase14_upper_band import reject_2m
        from unittest.mock import Mock,patch
        for admitted in (False,True):
            peer=Mock(fd=1,session='a'*32,received=bytearray(),schema={})
            peer.validator.errors.return_value=[]
            owner=[None];submitted=[None];operations=[]
            def request(op,body,**kwargs):
                operations.append(op)
                if op=='CLAIM':owner[0]=body['owner_id']
                if op=='STATUS':return dict(owner_id=owner[0],job_id=submitted[0] if admitted else 'b'*32,
                    state='loaded' if admitted else 'complete',output_active=False)
                return {}
            peer.request.side_effect=request
            def exchange(*args,**kwargs):
                value=kwargs['expected']['body'];submitted[0]=value['job_id']
                self.assertEqual(kwargs['expected']['op'],'LOAD')
                self.assertTrue(all(int(e['frequency_nhz'])>75000000*1000000000 for e in value['events'] if e['rf_on']))
                return dict(ok=admitted,error=dict(code='FREQUENCY_REJECTED'))
            with patch('phase11_5_inventory.exchange',side_effect=exchange):
                if admitted:
                    with self.assertRaises(ValueError):reject_2m(peer,Mock(),'WSPR',150000000)
                    self.assertIn('ABORT',operations)
                else:
                    result=reject_2m(peer,Mock(),'WSPR',150000000)
                    self.assertEqual(result['disposition'],'UNSUPPORTED_CONFIGURATION')
                    self.assertNotIn('ABORT',operations)
                self.assertNotIn('ARM',operations)
                self.assertEqual(operations[-1],'RELEASE')
    def test_wspr_external_decode_accepts_residual_diagnostics_but_rejects_wrong_message(self):
        from phase14.wspr_decode import assess
        line='2359 40 -0.0 3.570100 0 AA0NT EM18 37 '
        report=dict(decoded=True,passed=False,measurement=dict(max_symbol_residual_hz=1.68))
        receipt=dict(returncode=0,decoded=True,matches=[line])
        self.assertTrue(assess(report,receipt,line+'\n')['passed'])
        self.assertFalse(assess(report,receipt,line.replace('AA0NT','N0CALL'))['passed'])
        self.assertFalse(assess(report,dict(receipt,returncode=True),line)['passed'])
        self.assertFalse(assess(report,dict(receipt,returncode=1),line)['passed'])
        self.assertFalse(assess(dict(report,decoded=False),receipt,line)['passed'])
        self.assertFalse(assess(report,dict(receipt,matches=['invented']),line)['passed'])
        self.assertFalse(assess(dict(report,decode=dict(receipt,returncode=1)),receipt,line)['passed'])
    def test_browser_request_latency_does_not_reduce_one_hour_workload(self):
        from unittest.mock import patch
        from phase14.browser import activity
        class Clock:
            now=0
        clock=Clock()
        class SlowBrowser:
            def get(self,path):
                clock.now+=2400000000
                return dict(path=path,status=200)
        samples=[];last=-10000000000
        with patch('phase14.browser.time.monotonic_ns',side_effect=lambda:clock.now), \
             patch('phase14.browser.time.time_ns',side_effect=lambda:clock.now):
            while clock.now<3600000000000:
                if clock.now-last>=10000000000:
                    sample=activity(SlowBrowser(),'/api/v1/status')
                    samples.append(sample);last=sample['started_monotonic_ns']
                clock.now+=500000000
        self.assertGreaterEqual(len(samples),300)
        self.assertGreaterEqual(samples[-1]['utc_ns']-samples[0]['utc_ns'],3500000000000)
        self.assertTrue(all(s['completed_monotonic_ns']-s['started_monotonic_ns']==2400000000 for s in samples))
        # The prior completion-anchored interval produces only ~290 requests.
        self.assertLess(3600/(10+2.4),300)
    def test_browser_load_retains_original_request_count_rejection(self):
        from phase14_soak_analyze import browser_load
        origin=1791514876518283981
        original=[origin+i*12400000000 for i in range(291)]
        result=browser_load(original)
        self.assertFalse(result['passed'])
        self.assertEqual(result['issues'],['fewer than 300 successful browser requests'])
        repaired=[origin+i*10000000000 for i in range(360)]
        self.assertTrue(browser_load(repaired)['passed'])
        self.assertFalse(browser_load(repaired[:300])['passed'])
        self.assertFalse(browser_load([])['passed'])
        for invalid in ([True],[origin,origin],[origin,origin-1]):
            with self.assertRaises(ValueError):browser_load(invalid)
    def test_browser_repeat_compares_equivalent_mode_idle_windows(self):
        from phase14_browser_soak import idle_return
        windows=[[27124,27132,27124],[42068,42068,42068],
                 [27100,27100,27100],[42000,42008,42000]]
        result=idle_return(windows)
        self.assertTrue(result['passed'])
        self.assertEqual([p['median_growth_bytes'] for p in result['pairs']],[-24,-68])
        invalid=copy.deepcopy(windows);invalid[2]=[28149]*3
        self.assertFalse(idle_return(invalid)['passed'])
        invalid=copy.deepcopy(windows);invalid[3][1]+=2048
        self.assertFalse(idle_return(invalid)['passed'])
        for invalid in (windows[:3],[[True]*3]*4,[[-1]*3]*4):
            with self.assertRaises(ValueError):idle_return(invalid)
    def test_abort_assessment_rejects_extra_rf_and_full_duration(self):
        import numpy as np
        from phase14_abort import envelope
        power=np.zeros(12000);power[2000:4874]=1
        self.assertTrue(envelope(power,1000,10)['passed'])
        for case in ('complete','extra','tail','leading','missing'):
            invalid=power.copy()
            if case=='complete':invalid[2000:]=1
            elif case=='extra':invalid[7000:7500]=1
            elif case=='tail':invalid[8000:8002]=.2
            elif case=='leading':invalid[:3]=.2
            else:invalid[:]=0
            self.assertFalse(envelope(invalid,1000,10)['passed'],case)
        power[100]=float('nan')
        with self.assertRaises(ValueError):envelope(power,1000,10)
    def test_maximum_load_waits_for_existing_decoder_and_authority_reserves(self):
        value=job('FSKCW','80m',138000000,'test',128,'max-events')
        needed=load_workspace_bytes(value)
        # The failed 52,601-byte payload was legal, but its 107,488-byte
        # available heap could not hold input plus the existing decode reserve.
        self.assertEqual(needed,52601+16+32768+32768+4096)
        self.assertLess(107488,needed)
        # The independent unarmed diagnostic succeeded after cache expiry.
        self.assertGreaterEqual(131216,needed)
        self.assertGreaterEqual(125400,needed)
        self.assertEqual(value['total_duration_ns'],'128000000000')
        self.assertEqual(len(value['events']),512)
        with self.assertRaises(ValueError):load_workspace_bytes(dict(value,extra='x'*65536))
    def test_long_capture_finalization_has_a_separate_finite_budget(self):
        # Actual failed 650-second acquisition retained every sample, then
        # hashing/cleanup finished at 664.93 seconds, beyond the old 662 limit.
        count=162500000
        observed_complete_s=664.93271909200121
        self.assertGreater(observed_complete_s,650+12)
        self.assertGreater(capture_elapsed_limit(count,250000),observed_complete_s)
        self.assertLess(capture_elapsed_limit(count,250000),800)
        # A one-hour RF job still requests exactly one hour; only receiver
        # finalization scales with its ~7.29 GB complete CF32 file.
        hour_count=(3600+45)*250000
        self.assertGreater(capture_elapsed_limit(hour_count,250000),3645+hour_count*8/99000000+2)
        self.assertLess(capture_elapsed_limit(hour_count,250000),4000)
        self.assertEqual(job('TONE','80m',138000000,'test',3600)['total_duration_ns'],'3600000000000')
        for invalid in ((0,250000),(True,250000),(count,0),(count,True),(count,'250000')):
            with self.assertRaises(ValueError):capture_elapsed_limit(*invalid)
    def test_clock_boundaries_and_full_jobs(self):
        rows=matrix();self.assertEqual(len(rows),225)
        self.assertEqual(sum(r['disposition']=='UNSUPPORTED_CONFIGURATION' for r in rows),25)
        for clock in (132000000,138000000,150000000):
            with self.assertRaises(ValueError):job('TONE','2m',clock,'test')
        with self.assertRaises(ValueError):job('WSPR','4m',138000000,'test')
        self.assertEqual(len(job('WSPR','4m',150000000,'test')['events']),162)
        for mode in ('WSPR','QRSS','FSKCW','DFCW'):
            value=job(mode,'80m',138000000,'test')
            self.assertEqual(sum(int(e['duration_ns']) for e in value['events']),int(value['total_duration_ns']))
        maximum=job('FSKCW','80m',138000000,'test',3600,'max-events')
        self.assertEqual(len(maximum['events']),512)
        self.assertEqual(sum(int(e['duration_ns']) for e in maximum['events']),3600000000000)
        for mode in ('TONE','WSPR','QRSS','DFCW'):
            with self.assertRaises(ValueError):job(mode,'80m',138000000,'test',3600,'max-events')
        self.assertEqual(job('TONE','80m',138000000,'test',3600)['total_duration_ns'],'3600000000000')
        for value in (0,3601,True):
            with self.assertRaises(ValueError):job('TONE','80m',138000000,'test',value)
    def test_adjustments_cannot_bind_foreign_event(self):
        value=job('TONE','80m',138000000,'test')
        a=dict(event_index=0,requested_frequency_nhz=value['events'][0]['frequency_nhz'],realized_frequency_nhz='3570099990000000')
        self.assertEqual(accepted_events(value,[a])['events'][0]['frequency_nhz'],a['realized_frequency_nhz'])
        self.assertNotEqual(value['events'][0]['frequency_nhz'],a['realized_frequency_nhz'])
        for changes in ({'event_index':1},{'event_index':True},{'requested_frequency_nhz':'1'}):
            with self.assertRaises(ValueError):accepted_events(value,[dict(a,**changes)])
        with self.assertRaises(ValueError):accepted_events(value,[a,a])
    def test_corrupt_receiver_evidence_never_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'iq';path.write_bytes(b'\0'*80)
            settings=dict(format='CF32',sample_rate_hz=250000)
            metadata=dict(resolved_device=dict(driver='sdrplay',serial='2404058C60'),actual_settings=settings,
                          overflow_count=0,clipping=dict(sample_count=0),primary_outcome='success',
                          cleanup=dict(outcome='verified'),retained_sample_count=10,
                          requested_sample_count=10,
                          output=dict(complete=True,size_bytes=80,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            validate_capture(metadata,path,settings)
            for key,value in [('resolved_device',dict(driver='sdrplay',serial='foreign')),('overflow_count',1),
                              ('clipping',dict(sample_count=1)),('primary_outcome','failure'),
                              ('cleanup',dict(outcome='unknown')),('retained_sample_count',11),
                              ('requested_sample_count',11),('requested_sample_count',True),
                              ('output',dict(complete=True,size_bytes=80,sha256='0'*64))]:
                invalid=copy.deepcopy(metadata);invalid[key]=value
                with self.assertRaises(ValueError):validate_capture(invalid,path,settings)
            path.write_bytes(b'\1'*80)
            with self.assertRaises(ValueError):validate_capture(metadata,path,settings)
    def test_lifecycle_and_source_substitutions_are_rejected(self):
        value=job('TONE','80m',138000000,'test')
        idle=dict(device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',revision='144e8e83e598',
                  system_clock_hz=138000000,status=dict(boot_id='a'*32,engine='pio-dma-gp2',
                  owner_id=None,output_active=False,enabled=False,state='empty'))
        running=dict(boot_id='a'*32,job_id=value['job_id'],state='running',output_active=True)
        terminal=dict(running,state='complete',output_active=False)
        physical=dict(schema='phase14-physical/1',board='A',serial='0BF4B4AEC9FFB344',
                      device_id=idle['device_id'],source_revision=idle['revision'],
                      clock_hz=138000000,band='80m',mode='TONE',divider=1,rf_gp=2,engine='pio-dma-gp2',
                      result='CONTROL_COMPLETE',firmware_sha256='b'*64,boot_id='a'*32,job=value,
                      accepted_job=copy.deepcopy(value),load=dict(job_id=value['job_id'],adjustments=[]),
                      arm=dict(job_id=value['job_id']),action='complete',
                      status=[dict(status=running),dict(status=terminal)],terminal=terminal,before=idle,after=idle)
        validate_physical(physical)
        mutations=[lambda v:v.update(board='B'),lambda v:v.update(boot_id='c'*32),
                   lambda v:v.update(mode='DFCW'),
                   lambda v:v.update(firmware_sha256='bad'),
                   lambda v:v['accepted_job']['events'][0].update(duration_ns='1'),
                   lambda v:v['arm'].update(job_id='d'*32),
                   lambda v:v['status'][0]['status'].update(boot_id='d'*32),
                   lambda v:v['terminal'].update(output_active=True),
                   lambda v:v['after']['status'].update(enabled=True),
                   lambda v:v['after'].update(revision='0123456789ab')]
        for mutation in mutations:
            invalid=copy.deepcopy(physical);mutation(invalid)
            with self.assertRaises(ValueError):validate_physical(invalid)
        cancelled=copy.deepcopy(physical);cancelled['action']='cancel'
        cancelled['status'][0]['status'].update(state='armed',output_active=False)
        cancelled['status'][-1]['status']['state']='aborted';cancelled['terminal']=cancelled['status'][-1]['status']
        validate_physical(cancelled)
        cancelled['status'][0]['status'].update(state='running',output_active=True)
        with self.assertRaises(ValueError):validate_physical(cancelled)
    def test_spectral_capture_cannot_straddle_stop_or_restart(self):
        from phase14.plan import validate_spectral_window
        running=dict(state='running',output_active=True,boot_id='a'*32,job_id='b'*32)
        validate_spectral_window(running,copy.deepcopy(running),'a'*32,'b'*32)
        for change in ({'state':'complete','output_active':False},{'output_active':False},
                       {'boot_id':'c'*32},{'job_id':'d'*32}):
            for before,after in ((dict(running,**change),running),(running,dict(running,**change))):
                with self.assertRaises(ValueError):validate_spectral_window(before,after,'a'*32,'b'*32)
    def test_spectral_long_tail_preserves_owner_and_rejects_bad_terminals(self):
        from phase14.spectral_control import wait_complete
        class Peer:
            def __init__(self, change=None):
                self.time=0;self.expiry=60;self.change=change;self.renewals=0
            def request(self, operation, body):
                if self.time>=self.expiry:raise ValueError('lease expired')
                if operation=='RENEW':
                    self.expiry=self.time+body['lease_ms']/1000;self.renewals+=1
                    return {}
                result=dict(boot_id='a'*32,job_id='b'*32,state='running',output_active=True)
                if self.time>=120:
                    result.update(state='complete',output_active=False)
                    if self.change:result.update(self.change)
                return result
            def sleep(self, seconds):self.time+=30
        peer=Peer();statuses=[]
        terminal=wait_complete(peer,'owner','a'*32,'b'*32,150,statuses,
            now=lambda:peer.time,sleep=peer.sleep)
        self.assertEqual(terminal['state'],'complete')
        self.assertGreater(peer.renewals,2)
        self.assertLess(peer.time,peer.expiry)
        for change in ({'boot_id':'c'*32},{'job_id':'d'*32},
                       {'state':'failed'},{'output_active':True}):
            peer=Peer(change)
            with self.assertRaises(ValueError):
                wait_complete(peer,'owner','a'*32,'b'*32,150,[],
                    now=lambda:peer.time,sleep=peer.sleep)
        peer=Peer()
        with self.assertRaises(TimeoutError):
            wait_complete(peer,'owner','a'*32,'b'*32,90,[],
                now=lambda:peer.time,sleep=peer.sleep)
    def test_settings_journal_corruption_never_rolls_back(self):
        from phase14.profiles import engineering_record,profile
        value=dict(device_id='b'*32,version=1,wifi=dict(ssid='test',password='private'),tls={})
        raw=engineering_record(7,value)
        self.assertEqual(profile(raw),(7,1,value))
        for at in (0,8,16,24,252,260,7936,7944,7952,8188):
            broken=bytearray(raw);broken[at]^=1
            with self.assertRaises(ValueError):profile(broken)
        for sequence in (0,True,2**64):
            with self.assertRaises(ValueError):engineering_record(sequence,value)
        # A valid older slot must not hide a torn newer slot.
        broken=bytearray(engineering_record(8,value)[:8192]+raw[:8192]);broken[260]^=1
        with self.assertRaises(ValueError):profile(broken)
    def test_reboot_comparison_preserves_cursor_but_ignores_volatile_display(self):
        from phase14.profiles import durable_settings,restoration_payload,restoration_settings
        before=dict(device_id='a'*32,access_state='active',access_generation=2,
            access_default_password=False,provisioning_generation=3,provisioning_source='consumer_preclock',
            status=dict(configured=True,enabled=False,expires_utc_s=0,schedule_base_frequency_nhz='3570100000000000',
                schedules=[],station={},watermark_utc_ns='100',last_job='old-display'))
        after=copy.deepcopy(before);after['status']['last_job']=''
        self.assertEqual(durable_settings(before),durable_settings(after))
        after['status']['watermark_utc_ns']='200'
        self.assertNotEqual(durable_settings(before),durable_settings(after))
        self.assertEqual(restoration_settings(before,after)['config']['watermark_utc_ns'],'200')
        after['status']['watermark_utc_ns']='99'
        with self.assertRaises(ValueError):restoration_settings(before,after)
        original=b'p'*16384+b'c'*8192+b'w'*8192
        self.assertEqual(restoration_payload(original),b'p'*16384+b'c'*8192)
        with self.assertRaises(ValueError):restoration_payload(original[:-1])
    def test_refill_faults_and_growth_samples(self):
        from phase14.plan import resources
        fields=('allocator_failures','tls_allocation_failures','dma_errors','exhausted_successor_links',
                'refill_invalid_reserves','refill_irq_unpaired','core0_stack_fault_status','core1_stack_fault_status',
                'flash_read_failures','flash_erase_failures','flash_program_failures')
        info=dict.fromkeys(fields,0);info.update(system_clock_hz=138000000,status=dict(boot_id='a'*32),
            heap_available_bytes=100000,heap_allocated_bytes=30000,core0_stack_guard_valid=1,
            core1_stack_guard_valid=1,max_refill_irq_to_ready_ns=1500000)
        self.assertTrue(resources([info,copy.deepcopy(info)],138000000)['passed'])
        wire=copy.deepcopy(info);wire['max_refill_irq_to_ready_ns']='1500000'
        self.assertTrue(resources([info,wire],138000000)['passed'])
        for invalid in (True,'-1','01','NaN','18446744073709551616'):
            with self.assertRaises(ValueError):resources([dict(info,max_refill_irq_to_ready_ns=invalid)],138000000)
        for changes in ({'heap_available_bytes':32767},{'exhausted_successor_links':1},
                        {'max_refill_irq_to_ready_ns':4000000},{'core1_stack_guard_valid':0}):
            self.assertFalse(resources([info,dict(info,**changes)],138000000)['passed'])
        with self.assertRaises(ValueError):resources([info,dict(info,system_clock_hz=132000000)],138000000)
    def test_clock_loss_cannot_target_a_foreign_ntp_peer(self):
        from phase14.clock_loss import NtpBlock
        value=dict(provisioning_source='provisioned',network=dict(ntp_address='192.168.1.54',ipv4='192.168.1.53'))
        NtpBlock(value,None)
        for change in ('public','foreign','consumer'):
            invalid=copy.deepcopy(value)
            if change=='public':invalid['network']['ntp_address']='1.1.1.1'
            elif change=='foreign':invalid['network']['ipv4']='192.168.2.53'
            else:invalid['provisioning_source']='consumer_preclock'
            with self.assertRaises(ValueError):NtpBlock(invalid,None)
    def test_clock_loss_observation_failure_still_removes_owned_rule(self):
        from phase14.clock_loss import NtpBlock
        from unittest.mock import Mock,patch
        import subprocess
        block=NtpBlock(dict(provisioning_source='provisioned',network=dict(ntp_address='192.168.1.54',ipv4='192.168.1.53')),Mock())
        block.active=True
        with patch('phase14.clock_loss.subprocess.check_output',side_effect=subprocess.TimeoutExpired('nft',5)),patch('phase14.clock_loss.subprocess.run',return_value=Mock(returncode=1)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):block.close()
            self.assertEqual(run.call_args_list[0].args[0][1:4],['delete','table','inet'])
            self.assertFalse(block.active)
    def test_candidate_hash_and_reserved_region_substitutions_are_rejected(self):
        from phase14.candidate import candidate
        from standalone_image_tests import block
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);artifacts=root/'artifacts';artifacts.mkdir()
            path=artifacts/'candidate.uf2';path.write_bytes(block(0x10000000)+block(0x10FFFF00,True))
            manifest=dict(schema='phase14-candidates/1',source_commit='a'*40,board='pico2_w',engine='pio-dma-gp2',divider=1,rf_gp=2,
                gp14_enabled=False,fixtures_enabled=False,release_qualified=False,
                sdk_commit='079c6f39023649b154152db30f1d781e884879bc',picotool_commit='6f6458d792b93685a11423b244a585eaa99eafcf',
                images={'138000000':{'uf2':dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())}})
            def publish():(artifacts/'manifest.json').write_text(json.dumps(manifest))
            publish();self.assertEqual(candidate(root)[2],path)
            manifest['fixtures_enabled']=True;publish()
            with self.assertRaises(ValueError):candidate(root)
            manifest['fixtures_enabled']=False;publish();path.write_bytes(b'wrong firmware')
            with self.assertRaises(ValueError):candidate(root)
            path.write_bytes(block(0x103F8000))
            manifest['images']['138000000']['uf2']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();publish()
            with self.assertRaises(ValueError):candidate(root)
    def test_clock_probe_unexpected_admission_still_aborts_its_job(self):
        from phase14.clock_loss import reject_aged_arm
        from unittest.mock import Mock,patch
        value=job('TONE','80m',138000000,'clock-probe',5)
        for admitted in (False,True):
            peer=Mock(fd=1,session='a'*32,received=bytearray(),schema={})
            peer.validator.errors.return_value=[]
            owner=[None];operations=[]
            def request(op,body,**kwargs):
                operations.append(op)
                if op=='CLAIM':owner[0]=body['owner_id'];return dict(owner_id=owner[0])
                if op=='GET_CLOCK':return dict(state='unsynchronized',utc_now_ns='1000000000')
                if op=='STATUS':return dict(job_id=value['job_id'],owner_id=owner[0],output_active=False,state='armed' if admitted else 'loaded')
                return {}
            peer.request.side_effect=request
            response=dict(ok=admitted,error=dict(code='CLOCK_UNSYNCHRONIZED'))
            with patch('phase11_5_inventory.exchange',return_value=response):
                if admitted:
                    with self.assertRaises(ValueError):reject_aged_arm(peer,Mock(),value)
                else:reject_aged_arm(peer,Mock(),value)
            self.assertEqual(operations[-3:],['ABORT','STATUS','RELEASE'])
    def test_controller_relay_rejects_truncated_and_corrupt_frames(self):
        from phase14.relay import messages
        from validate_wtp_contract import frame
        schema=json.loads((ROOT/'docs/protocol/wtp-1.schema.json').read_text())
        value=dict(type='request',protocol='WTP/1',session_id='a'*32,request_id='b'*32,op='PING',body={})
        raw=frame(json.dumps(value,separators=(',',':')).encode())
        self.assertEqual(messages(raw,schema),[value])
        broken=bytearray(raw);broken[-1]^=1
        for invalid in (raw[:-1],raw[:8],bytes(broken),raw+b'extra'):
            with self.assertRaises(ValueError):messages(invalid,schema)
    def test_controller_terminal_requires_same_job_boot_and_post_arm_completion(self):
        from phase14.relay import terminal_proof
        from validate_wtp_contract import frame
        schema=json.loads((ROOT/'docs/protocol/wtp-1.schema.json').read_text())
        clock=dict(state='synchronized',utc_now_ns='0',monotonic_now_ns='0',uncertainty_ns='0',sync_age_ns='0',leap='normal')
        arm=dict(type='response',protocol='WTP/1',session_id='a'*32,request_id='b'*32,op='ARM',ok=True,
            body=dict(job_id='c'*32,state='armed',start_utc_ns='1000000000',start_monotonic_ns='1000000000',clock=clock))
        end=dict(type='event',protocol='WTP/1',session_id='a'*32,boot_id='d'*32,event_id='1',event='JOB_STATE',
            body=dict(job_id='c'*32,state='complete',output_active=False))
        def wire(values):return b''.join(frame(json.dumps(v,separators=(',',':')).encode()) for v in values)
        self.assertEqual(terminal_proof(wire([arm,end]),schema,arm,'d'*32,'c'*32)['terminal'],end['body'])
        cases=[[end,arm],[arm,dict(end,boot_id='e'*32)],
            [arm,dict(end,body=dict(end['body'],job_id='e'*32))],
            [arm,dict(end,body=dict(end['body'],state='aborted'))],
            [arm,dict(end,body=dict(end['body'],output_active=True))],
            [arm,end,dict(end,event_id='2',body=dict(end['body'],state='aborted'))]]
        for values in cases:
            with self.assertRaises(ValueError):terminal_proof(wire(values),schema,arm,'d'*32,'c'*32)
    def test_controller_relay_drains_fragmented_bytes_at_half_close(self):
        from phase14.relay import Relay
        import socket,threading
        source=b'complete local job'*8192;answer=b'complete response'*4096
        received=[]
        with tempfile.TemporaryDirectory() as directory,socket.socket() as server:
            server.bind(('127.0.0.1',0));server.listen(1)
            def endpoint():
                with server.accept()[0] as connection:
                    connection.settimeout(5);parts=[]
                    while data:=connection.recv(4096):parts.append(data)
                    received.append(b''.join(parts));connection.sendall(answer)
            worker=threading.Thread(target=endpoint);worker.start()
            relay=Relay(directory,'127.0.0.1',server.getsockname()[1],listen_port=0)
            try:
                with socket.create_connection(('127.0.0.1',relay.listen_port),timeout=5) as client:
                    for at in range(0,len(source),137):client.sendall(source[at:at+137])
                    client.shutdown(socket.SHUT_WR);parts=[]
                    while data:=client.recv(4096):parts.append(data)
                    self.assertEqual(b''.join(parts),answer)
            finally:relay.close();worker.join(timeout=5)
            self.assertFalse(worker.is_alive());self.assertEqual(received,[source])
            self.assertEqual((Path(directory)/'client-to-device.bin').read_bytes(),source)
            self.assertEqual((Path(directory)/'device-to-client.bin').read_bytes(),answer)
    def test_sampling_axis_correction_preserves_reference_anchor_and_original(self):
        from phase14.calibration import quantities
        reference=dict(schema='phase14-reference/1',scale_nominal_to_true_time=1.000002,repeatability_bound_ppm=.2,
            reference_accuracy_assumption_ppb=1,traceable_calibration=False)
        measurement=dict(reference_hz=3530100,observed_duration_s=110.592,tone_spacing_hz=1.46484375,
            measurements=[dict(index=0,reference_compared_hz=3570100.08)])
        original=copy.deepcopy(measurement);result=quantities(measurement,reference)
        self.assertEqual(measurement,original)
        self.assertAlmostEqual(result['reference_subtracted_frequencies'][0]['frequency_hz_true_axis'],3570100,places=6)
        self.assertGreater(result['observed_duration_s_true_axis'],measurement['observed_duration_s'])
        self.assertEqual(result['transmitter_frequency_correction_ppb'],0)
        for invalid in (True,0,float('nan'),1.1):
            with self.assertRaises(ValueError):quantities(measurement,dict(reference,scale_nominal_to_true_time=invalid))
    def test_usb_deauthorization_refuses_changed_port_identity(self):
        from phase14.usb import UsbUnavailable
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);device=root/'3-1.2';device.mkdir()
            (device/'serial').write_text('CDDBF8767C506C07');(device/'authorized').write_text('1')
            change=UsbUnavailable('B',Mock(),sysroot=root);change.start()
            self.assertEqual((device/'authorized').read_text().strip(),'0')
            (device/'serial').write_text('foreign')
            with self.assertRaises(ValueError):change.close()
            self.assertEqual((device/'authorized').read_text().strip(),'0')
            (device/'serial').write_text('CDDBF8767C506C07');change.close()
            self.assertEqual((device/'authorized').read_text().strip(),'1')
    def test_requested_compensation_changes_frequency_without_changing_time(self):
        from phase14.calibration import request_compensated
        value=job('WSPR','80m',138000000,'compensation')
        self.assertEqual(request_compensated(value,0),value)
        positive=request_compensated(value,1500);negative=request_compensated(value,-1500)
        self.assertLess(int(positive['events'][0]['frequency_nhz']),int(value['events'][0]['frequency_nhz']))
        self.assertGreater(int(negative['events'][0]['frequency_nhz']),int(value['events'][0]['frequency_nhz']))
        self.assertNotEqual(positive['job_id'],negative['job_id'])
        self.assertEqual(positive['total_duration_ns'],value['total_duration_ns'])
        self.assertEqual([(e['offset_ns'],e['duration_ns']) for e in positive['events']],[(e['offset_ns'],e['duration_ns']) for e in value['events']])
        for invalid in (True,100001,-100001,1.5):
            with self.assertRaises(ValueError):request_compensated(value,invalid)
    def test_public_index_does_not_mix_compensation_or_abort_with_baseline(self):
        from phase14_index import collect
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index,(action,compensation,source) in enumerate((('complete',0,'a'*12),('abort',0,'a'*12),('complete',1500,'a'*12),('complete',0,'b'*12))):
                folder=root/str(index);folder.mkdir();analysis=folder/'analysis';analysis.mkdir()
                value=dict(result='CONTROL_COMPLETE',board='A',band='80m',mode='TONE',clock_hz=138000000,
                    source_revision=source,firmware_sha256='f'*64,boot_id='c'*32,job=dict(job_id=str(index)*32),
                    action=action,workload='normal',requested_frequency_compensation_ppb=compensation,
                    private_secret='must never be exported')
                path=folder/'physical.json';path.write_text(json.dumps(value))
                report=dict(physical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),disposition='OPERATIONAL_SCREEN_PASS',
                    board='A',band='80m',mode='TONE',clock_hz=138000000,source_revision=source,
                    firmware_sha256='f'*64,boot_id='c'*32,job_id=str(index)*32,capture_sha256='d'*64,metadata_sha256='e'*64,limitations=[],tools={})
                (analysis/'result.json').write_text(json.dumps(report))
            value=collect(root,'a'*12)
            self.assertEqual(len(value['observations']),4)
            row=next(r for r in value['matrix'] if r['band']=='80m' and r['mode']=='TONE' and r['clock_hz']==138000000)
            self.assertEqual(row['observations'],[0]);self.assertFalse(value['release_qualified'])
            self.assertNotIn('must never be exported',json.dumps(value))
            physical=root/'0/physical.json';v=json.loads(physical.read_text());v['mode']='QRSS';physical.write_text(json.dumps(v))
            path=root/'0/analysis/result.json';report=json.loads(path.read_text());report['mode']='QRSS'
            report['physical_sha256']=hashlib.sha256(physical.read_bytes()).hexdigest()
            report['disposition']='OPERATIONAL_SCREEN_FAIL'
            report['human_copy']=dict(schema='phase14-human-copy/1',passed=True,overall_screen_passed=True,issues=[],
                private_secret='must never be exported',frequency_state_pairs=[dict(before_event_index=1,after_event_index=3,
                observed_jump_hz=5,private_secret='must never be exported')])
            path.write_text(json.dumps(report));value=collect(root,'a'*12)
            row=next(r for r in value['matrix'] if r['band']=='80m' and r['mode']=='QRSS' and r['clock_hz']==138000000)
            self.assertEqual(row['disposition'],'HUMAN_COPY_SCREEN_PASS_RELEASE_UNQUALIFIED')
            self.assertEqual(row['legacy_screen_disposition'],'SCREEN_FAIL')
            self.assertNotIn('must never be exported',json.dumps(value))
            from phase14.harmonic import ROUTE
            v['band']='2m';v['output_route']=copy.deepcopy(ROUTE);physical.write_text(json.dumps(v))
            report['band']='2m';report['output_route']=copy.deepcopy(ROUTE)
            report['physical_sha256']=hashlib.sha256(physical.read_bytes()).hexdigest();path.write_text(json.dumps(report))
            value=collect(root,'a'*12)
            row=next(r for r in value['matrix'] if r['band']=='2m' and r['mode']=='QRSS' and r['clock_hz']==138000000)
            self.assertEqual(row['observations'],[])
            self.assertEqual(row['disposition'],'UNSUPPORTED_CONFIGURATION')
            self.assertEqual(value['harmonic_output_observations'],[0])
            changed=copy.deepcopy(report);changed['output_route']['harmonic']=5;path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):collect(root,'a'*12)
            path.write_text(json.dumps(report))
            path=root/'0/analysis/result.json';report=json.loads(path.read_text());report['board']='B';path.write_text(json.dumps(report))
            with self.assertRaises(ValueError):collect(root,'a'*12)
    def test_soak_growth_rejects_leak_and_unstable_idle(self):
        from phase14_soak_analyze import idle_growth
        windows=[[10000,10032,10000] for _ in range(8)]
        self.assertTrue(idle_growth(windows)['passed'])
        windows[4]=[12048,12048,12048]
        self.assertFalse(idle_growth(windows)['passed'])
        windows[4]=[9000,10000,12000]
        self.assertFalse(idle_growth(windows)['passed'])
        with self.assertRaises(ValueError):idle_growth(windows[:7])
        windows[4]=[True,10000,10000]
        with self.assertRaises(ValueError):idle_growth(windows)
    def test_unresolved_human_capture_is_retained_without_promoting_or_rerunning(self):
        from phase14_human_repetitions import assess
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);physical=root/'physical.json'
            value=dict(capture_sha256='a'*64,metadata_sha256='b'*64)
            physical.write_text(json.dumps(value))
            with patch('phase14_human_repetitions.analyze',side_effect=ValueError('no acquired carrier')) as analyze:
                first=assess(root);second=assess(root)
                self.assertFalse(first['human_copy_passed']);self.assertEqual(first,second)
                self.assertEqual(first['disposition'],'ANALYSIS_UNRESOLVED');analyze.assert_called_once()
                physical.write_text(json.dumps(dict(value,capture_sha256='c'*64)))
                with self.assertRaises(ValueError):assess(root)
if __name__=='__main__':unittest.main()
