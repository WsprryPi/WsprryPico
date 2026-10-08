#!/usr/bin/env python3
"""Independent sampled RF fixtures challenge operational false passes."""

import sys
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from campaign.plan import make_job
from campaign.analysis import keyed, spectrum


def synth(job, *, extra=False, wrong_shift=False, dropout=False):
    rate = 12000
    duration = int(job["total_duration_ns"]) / 1e9 + 4
    count = round(duration * rate)
    rng = np.random.default_rng(71)
    iq = 0.0001 * (rng.normal(size=count) + 1j * rng.normal(size=count))
    phase = 0.0
    for event in job["events"]:
        if not event["rf_on"]:
            continue
        a = round((2 + int(event["offset_ns"]) / 1e9) * rate)
        b = a + round(int(event["duration_ns"]) / 1e9 * rate)
        frequency = int(event["frequency_nhz"]) / 1e9 - 3570100
        if wrong_shift:
            frequency = 0
        angle = phase + 2 * np.pi * (2000 + frequency) * np.arange(b - a) / rate
        iq[a:b] += 0.2 * np.exp(1j * angle)
        phase = angle[-1] + 2 * np.pi * (2000 + frequency) / rate
    if extra:
        a = round(0.8 * rate)
        iq[a : a + 1200] += 0.2 * np.exp(2j * np.pi * 2000 * np.arange(1200) / rate)
    if dropout:
        a = round(3.2 * rate)
        iq[a : a + 100] = 0.0001
    return iq, rate


class AnalysisTests(unittest.TestCase):
    def test_closein_peak_ratio_and_incomplete_window_rejection(self):
        from phase14.closein import compare
        rate=12000;time=np.arange(12*rate)/rate
        rng=np.random.default_rng(95)
        iq=1e-5*(rng.normal(size=len(time))+1j*rng.normal(size=len(time)))
        on=(time>=2)&(time<7)
        iq[on]+=.2*np.exp(2j*np.pi*2000*time[on])+.01*np.exp(2j*np.pi*1880*time[on])+.0063245553*np.exp(2j*np.pi*2120*time[on])
        result=compare(iq,rate,3568100,3570100,[2,7],24000)
        self.assertAlmostEqual(result['lower_120']['peak_dbc'],-26.0206,places=2)
        self.assertAlmostEqual(result['upper_120']['peak_dbc'],-30,places=2)
        self.assertGreater(result['carrier_on_minus_off_db'],60)
        # The retained Pi benchmark searches within 5 Hz of +/-120 Hz. A
        # displaced stronger feature must not hide outside a narrower search.
        iq[on]+=.02*np.exp(2j*np.pi*1876*time[on])
        result=compare(iq,rate,3568100,3570100,[2,7],24000)
        self.assertAlmostEqual(result['lower_120']['offset_hz'],-124,places=2)
        self.assertAlmostEqual(result['lower_120']['peak_dbc'],-20,places=2)
        for interval in ([2,3],[2,11],[7,2]):
            with self.assertRaises(ValueError):compare(iq,rate,3568100,3570100,interval,24000)
    def test_human_copy_preserves_slow_drift_but_rejects_missing_or_collapsed_marks(self):
        from phase14.human_copy import assess
        for mode in ('QRSS','FSKCW','DFCW'):
            job=make_job(mode,3570100,keyed_dot_ns=3000000000);iq,rate=synth(job)
            t=np.arange(len(iq))/rate;iq*=np.exp(.03j*np.pi*t*t)
            report=keyed(iq,rate,3568100,3570100,job)
            self.assertFalse(report['passed'],mode)
            human=assess(report,job);self.assertTrue(human['passed'],(mode,human))
            self.assertFalse(human['legacy_screen_passed'])
            for fault in ('extra','dropout'):
                bad,rate=synth(job,**{fault:True})
                self.assertFalse(assess(keyed(bad,rate,3568100,3570100,job),job)['passed'],(mode,fault))
            if mode!='QRSS':
                bad,rate=synth(job,wrong_shift=True)
                self.assertFalse(assess(keyed(bad,rate,3568100,3570100,job),job)['passed'])
                forged=copy.deepcopy(report);forged['human_frequency_state_pairs'][0]['expected_jump_hz']=.01
                self.assertFalse(assess(forged,job)['passed'])

    def test_long_capture_scan_rejects_nonfinite_after_chunk_boundary(self):
        from analyze_rf_bench import load_capture
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'capture.cf32';metadata=root/'capture.json'
            iq=np.ones(1048577,dtype='<c8');iq.tofile(path)
            value=dict(primary_outcome='success',cleanup=dict(outcome='verified'),
                output=dict(size_bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),complete=True),
                retained_sample_count=len(iq),actual_settings=dict(sample_rate_hz=250000,center_frequency_hz=3545100),
                wire_format=dict(sample_format='CF32',component_type='IEEE754_binary32',interleave='real_imaginary',
                    byte_order='little_endian',bytes_per_complex_sample=8))
            metadata.write_text(json.dumps(value));loaded,_,_=load_capture(path,metadata)
            self.assertEqual(len(loaded),len(iq));del loaded
            iq[-1]=complex(float('nan'),0);iq.tofile(path)
            value['output']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();metadata.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'Non-finite'):load_capture(path,metadata)

    def test_qrss_filter_rejects_distant_carrier_and_retains_slow_drift(self):
        from phase14_qrss_diagnostic import narrow_fir,polynomial
        rate=12000;t=np.arange(36000)/rate
        filtered=narrow_fir(1+.5*np.exp(2j*np.pi*2000*t),rate,25)
        self.assertLess(float(np.max(np.abs(filtered[4000:-4000]-1))),.0001)
        t=np.arange(9000)/1000
        report=polynomial(np.exp(2j*np.pi*t-.01j*np.pi*(t-4.5)**2),1000)
        self.assertGreater(report['linear_phase_rms_rad'],.15)
        self.assertLess(report['quadratic_phase_rms_rad'],1e-10)
        self.assertAlmostEqual(report['fitted_frequency_drift_hz_per_s'],-.01,places=10)

    def test_reference_pair_removes_common_phase_without_removing_source_drift(self):
        from phase14_qrss_diagnostic import polynomial
        t=np.arange(9000)/1000
        reference=np.exp(.6j*np.sin(2*np.pi*.4*t))
        source=reference*np.exp(-.01j*np.pi*(t-4.5)**2)
        corrected=source*np.conj(reference)/np.abs(reference)
        report=polynomial(corrected,1000)
        self.assertGreater(report['linear_phase_rms_rad'],.15)
        self.assertAlmostEqual(report['fitted_frequency_drift_hz_per_s'],-.01,places=10)
        self.assertLess(polynomial(reference*np.conj(reference)/np.abs(reference),1000)['linear_phase_rms_rad'],1e-12)
    def test_short_terminal_off_still_requires_independent_quiet(self):
        job=make_job('FSKCW',3570100)
        job['events'][-1]['duration_ns']='1000'
        job['total_duration_ns']=str(int(job['events'][-1]['offset_ns'])+1000)
        iq,rate=synth(job)
        result=keyed(iq,rate,3568100,3570100,job)
        self.assertTrue(result['passed'],result['issues'])
        end=round((2+int(job['total_duration_ns'])/1e9)*rate)
        truncated=keyed(iq[:end+round(.2*rate)],rate,3568100,3570100,job)
        self.assertFalse(truncated['passed']);self.assertIn('missing final silence',truncated['issues'])
        iq[end+rate:end+2*rate]+=.2*np.exp(2j*np.pi*2000*np.arange(rate)/rate)
        extra=keyed(iq,rate,3568100,3570100,job)
        self.assertFalse(extra['passed'])
    def test_keyed_modes_and_faults(self):
        for mode in ("QRSS", "FSKCW", "DFCW"):
            job = make_job(mode, 3570100)
            iq, rate = synth(job)
            good = keyed(iq, rate, 3568100, 3570100, job)
            self.assertTrue(good["passed"], (mode, good))
            for fault in ("extra", "dropout"):
                iq, rate = synth(job, **{fault: True})
                self.assertFalse(keyed(iq, rate, 3568100, 3570100, job)["passed"])
            if mode != "QRSS":
                iq, rate = synth(job, wrong_shift=True)
                self.assertFalse(keyed(iq, rate, 3568100, 3570100, job)["passed"])

    def test_keyed_transition_with_large_common_frequency_offset(self):
        job = make_job("FSKCW", 3570100)
        iq, rate = synth(job)
        iq *= np.exp(2j * np.pi * 45 * np.arange(len(iq)) / rate)
        report = keyed(iq, rate, 3568100, 3570100, job)
        self.assertTrue(report["passed"], report["issues"])

    def test_frequency_noise_is_not_reported_as_timing_failure(self):
        job = make_job("FSKCW", 3570100)
        iq, rate = synth(job)
        iq *= np.exp(1j * 0.03 * np.sin(2 * np.pi * 25 * np.arange(len(iq)) / rate))
        report = keyed(iq, rate, 3568100, 3570100, job)
        self.assertFalse(report["passed"])
        self.assertEqual(
            set(report["issues"]),
            {"keyed frequency transition fit residual exceeds 0.15 Hz"},
        )
        self.assertLess(max(abs(t["error_s"]) for t in report["transitions"]), 0.02)
        self.assertGreater(max(t["fit_rms_hz"] for t in report["transitions"]), 0.15)

    def test_spectrum_measures_known_spur(self):
        rate = 12000
        t = np.arange(12000) / rate
        iq = np.exp(2j * np.pi * 2000 * t) + 0.1 * np.exp(2j * np.pi * 3500 * t)
        report = spectrum(iq, rate, 0, [2000], [[0, 1]])
        self.assertTrue(report["available"])
        self.assertAlmostEqual(
            report["strongest_other_bin_hz"], 3500, delta=rate / report["fft_samples"]
        )
        self.assertAlmostEqual(report["strongest_other_bin_dbc"], -20, delta=1)
        self.assertFalse(spectrum(iq[:10], rate, 0, [2000], [[0, 0.001]])["available"])

    def test_spectrum_excludes_measured_reference_with_receiver_offset(self):
        rate=12000;t=np.arange(24000)/rate
        iq=np.exp(2j*np.pi*2000*t)+10*np.exp(2j*np.pi*1040*t)+.1*np.exp(2j*np.pi*3500*t)
        nominal=spectrum(iq,rate,0,[2000],[[0,2]],excluded_frequencies=[1000])
        self.assertAlmostEqual(nominal['strongest_other_bin_hz'],1040,delta=rate/nominal['fft_samples'])
        measured=spectrum(iq,rate,0,[2000],[[0,2]],excluded_frequencies=[1000,1040])
        self.assertAlmostEqual(measured['strongest_other_bin_hz'],3500,delta=rate/measured['fft_samples'])
        self.assertAlmostEqual(measured['strongest_other_bin_dbc'],-20,delta=1)

    def test_fsk_timing_cannot_hide_in_continuous_carrier(self):
        expected = make_job("FSKCW", 3570100)
        changed = copy.deepcopy(expected)
        changed["events"][1]["duration_ns"] = str(
            int(changed["events"][1]["duration_ns"]) + 50000000
        )
        changed["events"][2]["offset_ns"] = str(
            int(changed["events"][2]["offset_ns"]) + 50000000
        )
        changed["events"][2]["duration_ns"] = str(
            int(changed["events"][2]["duration_ns"]) - 50000000
        )
        iq, rate = synth(changed)
        report = keyed(iq, rate, 3568100, 3570100, expected)
        self.assertFalse(report["passed"])
        self.assertIn("keyed frequency transition timing failed", report["issues"])


if __name__ == "__main__":
    unittest.main()
