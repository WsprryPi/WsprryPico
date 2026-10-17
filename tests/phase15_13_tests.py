"""Hardware-free planning boundaries; no message-generation acceptance work."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from phase15_13.plan import plan, validate, FREQUENCIES, CLOCK, repair_plan, fskcw_repair_plan
from campaign.plan import BANDS
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import importlib.util
spec=importlib.util.spec_from_file_location('p1513_cli',Path(__file__).resolve().parents[1]/'scripts/phase15_13.py')
cli=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class PlanTests(unittest.TestCase):
    def test_physical_selectors_cannot_combine_plans(self):
        import subprocess
        result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/phase15_13.py'),
            'execute','--output','/unused','--cold-focused','--final-five-metre'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('not allowed with argument',result.stderr)

    def test_fskcw_retest_preserves_one_complete_short_job(self):
        focused=fskcw_repair_plan();self.assertEqual(focused['diagnostic_rf_windows'],1)
        original=next(w for w in plan()['windows'] if w['band']=='5m' and w['mode']=='FSKCW')
        revised=focused['windows'][0]
        self.assertEqual(revised['job']['events'],original['job']['events'])
        self.assertEqual(int(revised['job']['total_duration_ns']),35000000000)
        self.assertLess(35+8+5,60)
        self.assertNotEqual(revised['job']['job_id'],original['job']['job_id'])

    def test_focused_retest_is_waveform_equivalent_and_finite(self):
        repair=repair_plan();self.assertEqual(repair['diagnostic_rf_windows'],3)
        original=[w for w in plan()['windows'] if w['band']=='5m' and w['mode']=='WSPR']
        for before,after in zip(original,repair['windows']):
            self.assertNotEqual(before['job']['job_id'],after['job']['job_id'])
            self.assertFalse(after['job']['allow_frequency_adjustment'])
            self.assertLess(len(after['job']['events']),162)
            for event in before['job']['events']:
                offset=int(event['offset_ns'])
                selected=next(e for e in after['job']['events'] if int(e['offset_ns'])<=offset<int(e['offset_ns'])+int(e['duration_ns']))
                divisor=CLOCK*1000000000
                increment=(int(event['frequency_nhz'])*(1<<32)+divisor//2)//divisor
                realized=(CLOCK*increment*1000000000+(1<<31))//(1<<32)
                self.assertEqual(int(selected['frequency_nhz']),realized)
            self.assertEqual(before['job']['total_duration_ns'],after['job']['total_duration_ns'])
            from phase14.wspr_segment import describe
            report=dict(measurements=[dict(index=i,indicated_hz=int(event['frequency_nhz'])/1e9)
                for i,event in enumerate(before['job']['events'])])
            annotation=describe(report,after['job'],'WSPR')
            self.assertEqual(len(annotation['observations']),162)

    def test_rejected_load_releases_claim_without_needing_an_accepted_job(self):
        from phase15_13.live import cleanup_owned
        from unittest.mock import Mock
        rig=Mock();state=dict(owner_id='owner',job_id=None,state='empty',output_active=False)
        rig.info.return_value={'status':state}
        rig.device.console.side_effect=lambda *args:state.update(owner_id=None)
        cleanup_owned(rig,'owner','submitted-but-rejected')
        rig.device.console.assert_called_once_with('A','ABORT')
        rig.device.peer.assert_not_called()
        rig.device.peer.reset_mock();state['owner_id']='foreign'
        cleanup_owned(rig,'owner','submitted-but-rejected')
        rig.device.peer.assert_not_called()

    def test_consecutive_utc_slots_retain_local_clock_reprojection(self):
        from phase15_13.live import consecutive_frames
        observed=[[9.970,120.562],[129.911,240.503],[249.928,360.520]]
        records=[dict(arm=dict(start_utc_ns=str(1000000000+i*120000000000),
                              start_monotonic_ns=str(v))) for i,v in
                 enumerate((174105743000,294048492000,414067174000))]
        proof=consecutive_frames(observed,records)
        self.assertLess(max(abs(x) for x in proof['interframe_projection_error_s']),.002)
        changed=copy.deepcopy(records);changed[1]['arm']['start_utc_ns']='122000000000'
        with self.assertRaises(ValueError):consecutive_frames(observed,changed)
        changed=copy.deepcopy(observed);changed[1][1]-=1
        with self.assertRaises(ValueError):consecutive_frames(changed,records)

    def test_valid_tone_keeps_frequency_diagnostic_and_rejects_interruption(self):
        import hashlib,json,tempfile
        import numpy as np
        from measure_rf_bench import measure
        from phase15_13.assessment import assess
        from phase14.live import save
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'analysis').mkdir()
            window=plan()['windows'][0];job=window['job'];rate=250000
            center=window['frequency_hz']-25000
            t=np.arange(8*rate)/rate
            envelope=(t>=1)&(t<6)
            iq=(envelope*np.exp(2j*np.pi*25125*t)+.1*np.exp(-2j*np.pi*14956*t)).astype('<c8')
            iq.tofile(root/'capture.cf32')
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            settings=dict(format='CF32',sample_rate_hz=rate,center_frequency_hz=center)
            meta=dict(resolved_device=dict(driver='sdrplay',serial='2404058C60'),actual_settings=settings,
                overflow_count=0,clipping=dict(sample_count=0),primary_outcome='success',cleanup=dict(outcome='verified'),
                retained_sample_count=len(iq),requested_sample_count=len(iq),
                output=dict(complete=True,size_bytes=iq.nbytes,sha256=sha(root/'capture.cf32')))
            save(root/'capture.json',meta)
            idle=dict(device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',revision='c'*12,system_clock_hz=CLOCK,
                status=dict(boot_id='a'*32,engine='pio-dma-gp2',owner_id=None,output_active=False,enabled=False,state='empty'))
            running=dict(boot_id='a'*32,job_id=job['job_id'],state='running',output_active=True)
            terminal=dict(running,state='complete',output_active=False)
            physical=dict(schema='phase14-physical/1',window_id=window['id'],board='A',serial='0BF4B4AEC9FFB344',
                device_id=idle['device_id'],source_revision=idle['revision'],clock_hz=CLOCK,band='8m',mode='TONE',
                divider=1,rf_gp=2,engine='pio-dma-gp2',result='CONTROL_COMPLETE',firmware_sha256='b'*64,boot_id='a'*32,
                job=job,accepted_job=job,load=dict(job_id=job['job_id'],adjustments=[]),arm=dict(job_id=job['job_id']),
                action='complete',status=[dict(status=running),dict(status=terminal)],terminal=terminal,before=idle,after=idle,
                receiver_settings=settings)
            save(root/'physical.json',physical)
            measured=measure(iq,rate,center,duration_s=5,base_hz=window['frequency_hz'],
                             reference_hz=window['frequency_hz']-40000)
            self.assertFalse(measured['relative_checks_passed'])
            result=dict(physical_sha256=sha(root/'physical.json'),capture_sha256=sha(root/'capture.cf32'),
                metadata_sha256=sha(root/'capture.json'),resources=dict(passed=True),measurement=measured,passed=False)
            save(root/'analysis/result.json',result)
            accepted=assess(root)
            self.assertTrue(accepted['passed'])
            self.assertAlmostEqual(accepted['details']['reference_compared_offset_mean_hz'],81,places=1)
            self.assertFalse(accepted['legacy_screen_passed'])
            result['measurement']['intervals_s']=[[1,3],[3.1,6]]
            save(root/'analysis/result.json',result)
            self.assertFalse(assess(root)['passed'])
            iq[rate+10000]=complex(float('nan'),0)
            iq.tofile(root/'capture.cf32')
            with self.assertRaises(ValueError):assess(root)

    def test_legacy_default_and_custom_pin_authority(self):
        self.assertEqual(cli.boot_pins({})['rf_gp'],2)
        self.assertEqual(cli.boot_pins({})['button_gp'],14)
        custom=cli.boot_pins({});custom['rf_gp']=3
        self.assertEqual(cli.boot_pins({'pins':custom}),custom)

    def test_configuration_refuses_torn_newest_record(self):
        import struct,zlib,json
        raw=bytearray(b'\xff'*32768)
        payload=json.dumps({'version':1,'enabled':False}).encode()
        for index in range(2):
            record=bytearray(b'\xff'*2048)
            struct.pack_into('<QQI',record,0,0x32524f5453505757,index+1,len(payload))
            record[32:32+len(payload)]=payload
            struct.pack_into('<I',record,2044,zlib.crc32(record[:-4]))
            raw[16384+index*2048:16384+(index+1)*2048]=record
        self.assertFalse(cli.configuration(bytes(raw))['enabled'])
        raw[16384+2048+40]^=1
        with self.assertRaises(ValueError):cli.configuration(bytes(raw))

    def test_exact_budget_and_legacy_scope(self):
        p = validate(plan())
        self.assertEqual(p['nominal_rf_windows'], 14)
        self.assertEqual(len({w['job']['job_id'] for w in p['windows']}), 14)
        self.assertEqual(p['diagnostic_rf_windows'], 0)
        self.assertNotIn('8m', BANDS)
        self.assertNotIn('5m', BANDS)
        self.assertEqual(len(p['groups']), 10)

    def test_complete_capture_and_frequency_states(self):
        p = plan()
        for group in p['groups']:
            for window in group['windows']:
                job = window['job']
                total = sum(int(e['duration_ns']) for e in job['events'])
                self.assertEqual(total, int(job['total_duration_ns']))
                for event in job['events']:
                    if event['rf_on']:
                        hz = int(event['frequency_nhz'])/1e9
                        self.assertGreaterEqual(hz, FREQUENCIES[window['band']]-5)
                        self.assertLessEqual(hz, FREQUENCIES[window['band']]+5)
                        self.assertLess(hz, CLOCK/2-1)
            required = 8 + (240 if group['mode']=='WSPR' else 0) + total/1e9 + 5
            self.assertGreater(group['capture_seconds'], required)
        self.assertEqual(p['capture_bytes'], sum(g['capture_bytes'] for g in p['groups']))

    def test_no_unbounded_or_substituted_plan(self):
        for mutate in (lambda p: p['windows'].pop(),
                       lambda p: p.update(clock_hz=150000000),
                       lambda p: p['groups'][1]['windows'].append(copy.deepcopy(p['windows'][0])),
                       lambda p: p.update(diagnostic_rf_windows=1)):
            p = plan()
            mutate(p)
            with self.assertRaises(ValueError):
                validate(p)


if __name__ == '__main__':
    unittest.main()
