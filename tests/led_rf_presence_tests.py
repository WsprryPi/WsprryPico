"""Synthetic signal/noise behavioral validation of the receiver presence check."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from led_closeout.rf_check import check_capture


class PresenceTests(unittest.TestCase):
    def test_burst_vs_idle_and_opposite_expectations(self):
        rate=250000
        rng=np.random.default_rng(137)
        noise=(rng.normal(size=rate*8)+1j*rng.normal(size=rate*8)).astype('<c8')*.01
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'signal.cf32';noise.tofile(path)
            self.assertFalse(check_capture(path,False)['detected'])
            self.assertFalse(check_capture(path,True)['passed'])
            t=np.arange(rate)/rate
            noise[rate*3:rate*4]+=np.exp(2j*np.pi*20100*t).astype('<c8')*.1
            noise.tofile(path)
            self.assertTrue(check_capture(path,True)['detected'])
            self.assertFalse(check_capture(path,False)['passed'])
            noise+=np.exp(2j*np.pi*20100*np.arange(rate*8)/rate).astype('<c8')*.1
            noise.tofile(path)
            steady=check_capture(path,False)
            self.assertTrue(steady['detected'])
            self.assertFalse(steady['inactive_tail'])
            self.assertFalse(steady['passed'])

    def test_invalid_or_short_data_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'invalid.cf32'
            for samples in (np.zeros(250000*8,dtype='<c8'),
                            np.full(250000*8,np.nan,dtype='<c8'),
                            np.ones(8192,dtype='<c8')):
                samples.tofile(path)
                with self.assertRaises(ValueError):check_capture(path,False)


if __name__=='__main__':unittest.main()
