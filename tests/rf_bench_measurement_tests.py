#!/usr/bin/env python3
"""Offline adversarial checks for relative tone/frame interpretation."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / part) for part in ('src', 'scripts')]
from decode_rf_wspr import audio_from_iq, decode_window
from measure_rf_bench import BASE, SPACING, SYMBOL, measure, phase_fit

RATE = 10000
CENTER = BASE - 2000

def capture(frame=False, gap=False, wrong=False, duration=2, delayed_boundary=False, symbols=None):
    length = 162 * SYMBOL if frame else duration
    n = round(length * RATE)
    rng = np.random.default_rng(9)
    iq = (rng.normal(size=n + 2 * RATE) + 1j * rng.normal(size=n + 2 * RATE)) * 1e-5
    tones = (np.floor(np.arange(n) / RATE / SYMBOL).astype(int) % 4) if frame else np.zeros(n)
    if symbols is not None:
        tones = np.array(symbols)[np.minimum(161, np.floor(np.arange(n) / RATE / SYMBOL).astype(int))]
    if delayed_boundary:
        tones[round(SYMBOL*RATE):round((SYMBOL+.02)*RATE)] = 0
    if wrong:
        tones = 3 - tones
    frequency = BASE - CENTER + 7.25 + tones * SPACING
    iq[RATE:RATE+n] += .1 * np.exp(2j * np.pi * np.cumsum(frequency) / RATE)
    if gap:
        iq[RATE + n//2:RATE + n//2 + RATE//20] = 1e-5
    return iq

class Tests(unittest.TestCase):
    def test_simultaneous_reference_contrast_follows_observed_receiver_peak(self):
        iq=capture()
        iq*=np.exp(2j*np.pi*158.7*np.arange(len(iq))/RATE)
        reference_hz=BASE-3000
        iq+=.01*np.exp(2j*np.pi*(reference_hz-CENTER+158.7)*np.arange(len(iq))/RATE)
        result=measure(iq,RATE,CENTER,duration_s=2,reference_hz=reference_hz)
        self.assertTrue(result['measurements'])
        for fit in result['measurements']:
            self.assertGreater(fit['reference']['local_contrast_db'],30)
            self.assertAlmostEqual(fit['reference']['indicated_hz'],reference_hz+158.7,delta=.02)
            self.assertAlmostEqual(fit['reference_compared_hz'],BASE+7.25,delta=.02)
        # The old frequency diagnostic remains separate from reference SNR.
        self.assertFalse(result['relative_checks_passed'])

    def test_reference_acquisition_handles_receiver_tuning_offset_and_rejects_noise(self):
        import numpy as np
        from rf_analysis.reference import reference_observation
        from measure_rf_bench import local_contrast
        rate=250000;center=144490500;frequency=center-20000
        t=np.arange(7*rate)/rate
        rng=np.random.default_rng(19)
        noise=.001*(rng.normal(size=len(t))+1j*rng.normal(size=len(t)))
        iq=.1*np.exp(2j*np.pi*(frequency-center+158.7)*t)+noise
        self.assertLess(local_contrast(iq[rate:2*rate],rate,center,frequency),30)
        result=reference_observation(iq,rate,center,frequency)
        self.assertTrue(result['acquisition_passed'])
        self.assertAlmostEqual(result['mean_indicated_hz'],frequency+158.7,places=2)
        self.assertFalse(reference_observation(noise,rate,center,frequency)['acquisition_passed'])

    def test_independent_receiver_axis_correction_cannot_hide_wrong_rf(self):
        from rf_analysis.reference import reference_observation
        rate=12000;carrier=144490500;center=carrier-2500;reference=carrier-5000
        time=np.arange(7*rate)/rate
        receiver_phase=2*np.pi*(157*time+.005*time*time)
        rng=np.random.default_rng(937)
        noise=.0001*(rng.normal(size=len(time))+1j*rng.normal(size=len(time)))
        marker=.2*np.exp(2j*np.pi*(reference-center)*time+1j*receiver_phase)
        active=(time>=1)&(time<6)
        for actual_error in (-16,300):
            iq=noise+marker
            iq[active]+=.1*np.exp(2j*np.pi*(carrier-center+actual_error)*time[active]+1j*receiver_phase[active])
            observed=reference_observation(iq,rate,center,reference)
            self.assertTrue(observed['acquisition_passed'])
            offset=observed['mean_indicated_hz']-reference
            report=measure(iq,rate,center-offset,duration_s=5,base_hz=carrier)
            self.assertEqual(report['relative_checks_passed'],actual_error==-16,report['issues'])
            self.assertAlmostEqual(report['tone_frequency_summary']['nominal_offset_hz'],actual_error,delta=.05)

    def test_decode_audio_preserves_frequency_and_time(self):
        audio = audio_from_iq(capture(), RATE, CENTER)
        self.assertEqual(len(audio), 120 * 12000)
        segment = audio[14400:33600].astype(float)
        # The capture's +7.25 Hz remains in audio; no reference subtraction.
        spectrum = np.abs(np.fft.rfft(segment * np.hanning(len(segment))))
        frequency = np.fft.rfftfreq(len(segment), 1/12000)[np.argmax(spectrum)]
        self.assertAlmostEqual(frequency, 1507.25, delta=0.4)
        self.assertLess(np.max(np.abs(audio[:6000])), 100)
        self.assertEqual(np.max(np.abs(audio[60000:])), 0)
        with self.assertRaises(ValueError):
            audio_from_iq(np.zeros(20000, complex), RATE, CENTER)

        iq = np.zeros(150 * RATE, complex)
        selected, first, last = decode_window(iq, RATE, 20.0)
        assert (first, last, len(selected)) == (20 * RATE, 140 * RATE, 120 * RATE)
        for bad in (-1, float('nan'), 50):
            try:
                decode_window(iq, RATE, bad)
            except ValueError:
                pass
            else:
                raise AssertionError('invalid decode window accepted')

    def test_tone_frequency(self):
        result = measure(capture(), RATE, CENTER, duration_s=2)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertAlmostEqual(result['measurements'][0]['indicated_hz'], BASE + 7.25, places=3)
        self.assertFalse(result['qualification'])
    def test_translated_carrier(self):
        iq = capture()
        iq *= np.exp(2j*np.pi*300*np.arange(len(iq))/RATE)
        self.assertFalse(measure(iq, RATE, CENTER, duration_s=2)['relative_checks_passed'])
        result = measure(iq, RATE, CENTER, duration_s=2, base_hz=BASE+300)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertAlmostEqual(result['tone_frequency_summary']['mean_hz'], BASE+307.25, places=3)
        with self.assertRaises(ValueError):
            measure(iq, RATE, CENTER, base_hz=float('nan'))

    def test_frame(self):
        result = measure(capture(frame=True), RATE, CENTER, frame=True)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertEqual(len(result['measurements']), 162)
        self.assertAlmostEqual(result['tone_spacing_hz'], SPACING, places=3)
    def test_frame_with_large_common_frequency_offset(self):
        iq = capture(frame=True)
        iq *= np.exp(2j * np.pi * 40 * np.arange(len(iq)) / RATE)
        result = measure(iq, RATE, CENTER, frame=True)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertAlmostEqual(result['tone_spacing_hz'], SPACING, places=3)

    def test_frequency_noise_is_not_reported_as_missing_transition(self):
        iq = capture(frame=True)
        iq *= np.exp(1j * .03 * np.sin(2 * np.pi * 25 * np.arange(len(iq)) / RATE))
        result = measure(iq, RATE, CENTER, frame=True)
        self.assertFalse(result['relative_checks_passed'])
        self.assertTrue(result['issues'])
        self.assertTrue(all(issue.startswith('Transition fit residual exceeds 0.15 Hz')
                            for issue in result['issues']))
        self.assertLess(result['max_transition_error_s'], .01)
        self.assertGreater(max(t['fit_rms_hz'] for t in result['transitions']), .15)

    def test_encoded_repeated_symbols(self):
        symbols = np.random.default_rng(14).integers(0, 4, 162).tolist()
        result = measure(capture(frame=True, symbols=symbols), RATE, CENTER, frame=True, symbols=symbols)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertEqual(len(result['transitions']), sum(a != b for a, b in zip(symbols, symbols[1:])))
        self.assertAlmostEqual(result['tone_spacing_hz'], SPACING, places=3)
        with self.assertRaises(ValueError):
            measure(capture(), RATE, CENTER, frame=True, symbols=[0]*161)

    def test_delayed_symbol_boundary(self):
        result = measure(capture(frame=True, delayed_boundary=True), RATE, CENTER, frame=True)
        self.assertFalse(result['relative_checks_passed'])
        self.assertGreater(result['max_transition_error_s'], .015)
    def test_gap(self):
        result = measure(capture(gap=True), RATE, CENTER, duration_s=2)
        self.assertFalse(result['relative_checks_passed'])
    def test_wrong_duration(self):
        self.assertFalse(measure(capture(), RATE, CENTER, duration_s=3)['relative_checks_passed'])
    def test_reversed_frame(self):
        self.assertFalse(measure(capture(frame=True, wrong=True), RATE, CENTER, frame=True)['relative_checks_passed'])
    def test_simultaneous_reference(self):
        iq = capture()
        reference = BASE - 4000
        # Both sources have the same +7.25 Hz receiver error.
        iq += .07 * np.exp(2j * np.pi * (reference - CENTER + 7.25) * np.arange(len(iq)) / RATE)
        result = measure(iq, RATE, CENTER, duration_s=2, reference_hz=reference)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertAlmostEqual(result['tone_frequency_summary']['mean_hz'], BASE, places=3)
    def test_absent_reference_rejected(self):
        with self.assertRaises(ValueError):
            phase_fit(np.zeros(100, dtype=complex), 1000)
        result = measure(capture(), RATE, CENTER, duration_s=2, reference_hz=BASE-4000)
        self.assertFalse(result['relative_checks_passed'])
    def test_self_reference_rejected(self):
        with self.assertRaises(ValueError):
            measure(capture(), RATE, CENTER, duration_s=2, reference_hz=BASE)
    def test_noise(self):
        rng = np.random.default_rng(7)
        iq = rng.normal(size=40000) + 1j*rng.normal(size=40000)
        self.assertFalse(measure(iq, RATE, CENTER, duration_s=2)['relative_checks_passed'])


class LowFrequencyTests(unittest.TestCase):
    @staticmethod
    def sampled(*, duration=5, frequency_error=.7, gap=False, extra=False, frame=False, delayed=False, seed=22):
        rate=20000; carrier=137500; center=carrier-2000
        start=1.234; length=162*SYMBOL if frame else duration
        count=round((length+4)*rate); rng=np.random.default_rng(seed)
        amplitude=.01; noise=amplitude*3*np.sqrt(rate/100000)
        iq=noise*(rng.normal(size=count)+1j*rng.normal(size=count))
        n=round(length*rate); times=np.arange(n)/rate
        tones=np.minimum(161,np.floor(times/SYMBOL).astype(int))%4 if frame else np.zeros(n)
        if delayed:
            tones[round(SYMBOL*rate):round((SYMBOL+.03)*rate)]=0
        offsets=carrier-center+frequency_error+tones*SPACING
        wave=amplitude*np.exp(2j*np.pi*np.cumsum(offsets)/rate)
        a=round(start*rate);iq[a:a+n]+=wave
        if gap:iq[a+round(2*rate):a+round(2.05*rate)]=noise*(rng.normal(size=round(.05*rate))+1j*rng.normal(size=round(.05*rate)))
        if extra:
            a=round((length+2)*rate);n=round(.1*rate)
            iq[a:a+n]+=amplitude*np.exp(2j*np.pi*(carrier-center+frequency_error)*np.arange(n)/rate)
        return iq,rate,center,carrier,start

    def test_weak_lf_carrier_has_independent_resolved_edges(self):
        for seed in range(3):
            iq,rate,center,carrier,start=self.sampled(seed=seed)
            r=measure(iq,rate,center,base_hz=carrier,duration_s=5)
            self.assertTrue(r['relative_checks_passed'],r)
            self.assertAlmostEqual(r['intervals_s'][0][0],start,delta=.01)
            self.assertAlmostEqual(r['observed_duration_s'],5,delta=.02)
            self.assertGreaterEqual(r['acquisition']['acquisition_snr_db'],20)
            self.assertTrue(all(e['uncertainty_s']<=.01 for e in r['edge_measurements']))
            self.assertAlmostEqual(r['measurements'][0]['indicated_hz'],carrier+.7,delta=.05)

    def test_lf_acquisition_uses_dominant_added_power_and_rejects_wrong_dominant_carrier(self):
        rate=12000;carrier=137500;center=carrier-2000;time=np.arange(9*rate)/rate
        rng=np.random.default_rng(1207)
        noise=1e-7*(rng.normal(size=len(time))+1j*rng.normal(size=len(time)))
        main=np.exp(2j*np.pi*(carrier-center+.7)*time)
        spur=np.exp(2j*np.pi*(carrier-center-350)*time)
        active=(time>=1.234)&(time<6.234)
        for spur_amplitude in (.002,.2):
            iq=noise+.008*main
            iq[active]+=.1*main[active]+spur_amplitude*spur[active]
            report=measure(iq,rate,center,base_hz=carrier,duration_s=5)
            self.assertEqual(report['relative_checks_passed'],spur_amplitude==.002,report)
            if spur_amplitude==.002:
                self.assertAlmostEqual(report['measurements'][0]['indicated_hz'],carrier+.7,delta=.02)
                self.assertAlmostEqual(report['observed_duration_s'],5,delta=.02)

    def test_lf_rejects_persistent_drifting_peak_but_not_a_new_wrong_carrier(self):
        rate=12000;carrier=137500;center=carrier-2000;time=np.arange(9*rate)/rate
        rng=np.random.default_rng(382)
        noise=.001*(rng.normal(size=len(time))+1j*rng.normal(size=len(time)))
        persistent=.4*np.exp(2j*np.pi*((carrier-center-500)*time+.1*time*time))
        active=(time>=1.234)&(time<6.234)
        for wrong in (False,True):
            iq=noise+persistent
            iq[active]+=.01*np.exp(2j*np.pi*(carrier-center+.7)*time[active])
            if wrong:iq[active]+=.02*np.exp(2j*np.pi*(carrier-center+250)*time[active])
            from measure_rf_bench import acquired_baseband
            _,_,acquired,acquisition,narrow,narrow_rate=acquired_baseband(iq,rate,center,carrier)
            self.assertTrue(acquisition['passed'])
            self.assertTrue(any(not c['passed'] for c in acquisition['candidates']))
            self.assertAlmostEqual(acquired,carrier+(250 if wrong else .7),delta=4)
            fit=phase_fit(narrow[round(2*narrow_rate):round(5*narrow_rate)],narrow_rate,acquired)
            self.assertAlmostEqual(fit['indicated_hz'],carrier+(250 if wrong else .7),delta=.02)
            # Acquisition does not waive the independent edge-resolution gate:
            # this deliberately overpowering interferer masks 1 ms edge samples.
            report=measure(iq,rate,center,base_hz=carrier,duration_s=5)
            self.assertFalse(report['relative_checks_passed'])

    def test_lf_gap_extra_carrier_wrong_duration_and_frequency_fail(self):
        for change in [dict(gap=True),dict(extra=True),dict(duration=4.95),dict(frequency_error=150)]:
            iq,rate,center,carrier,_=self.sampled(**change)
            r=measure(iq,rate,center,base_hz=carrier,duration_s=5)
            self.assertFalse(r['relative_checks_passed'],(change,r))

    def test_lf_frame_boundaries_and_delayed_transition(self):
        iq,rate,center,carrier,_=self.sampled(frame=True)
        r=measure(iq,rate,center,base_hz=carrier,frame=True)
        self.assertTrue(r['relative_checks_passed'],r['issues'])
        self.assertTrue(all(t['confidence']==.99 for t in r['transitions']))
        iq,rate,center,carrier,_=self.sampled(frame=True,delayed=True)
        r=measure(iq,rate,center,base_hz=carrier,frame=True)
        self.assertFalse(r['relative_checks_passed'])

if __name__ == '__main__':
    unittest.main()
