"""Pure launch mapping rejects wrong targets without treating later UTC as ARM time."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_arm_mapping import validate_mapping,waveform_samples

class MappingTests(unittest.TestCase):
    def test_absolute_samples_and_off_tail(self):
        def job(duration,on=True):
            return dict(total_duration_ns=str(duration),events=[dict(offset_ns='0',duration_ns=str(duration),rf_on=on)])
        self.assertEqual(waveform_samples(job(155749999969)),21493499996)
        self.assertEqual(waveform_samples(job(1001)),138)
        self.assertEqual(waveform_samples(job(1001,False)),139)
        self.assertEqual(waveform_samples(job(3600_000_000_000)),496800000000)
        with self.assertRaises(ValueError):waveform_samples(job(1))
        with self.assertRaises(ValueError):waveform_samples(job(3600_000_000_001))
    def test_mapping_quantization_and_mutations(self):
        request=dict(job_id='1'*32,start_utc_ns='20000000000',max_start_uncertainty_ns='500000000')
        ack=dict(job_id='1'*32,state='armed',start_utc_ns='20000000000',start_monotonic_ns='10000000123',
            clock=dict(state='synchronized',leap='normal',utc_now_ns='15000000000',monotonic_now_ns='5000000123',uncertainty_ns='1000000'))
        self.assertEqual(validate_mapping(request,ack,10000001000)['quantization_ns'],877)
        for target in [10000000123,10000000000,10000002000]:
            with self.assertRaises(ValueError):validate_mapping(request,ack,target)
        for key,value in [('job_id','2'*32),('start_monotonic_ns','10000000124'),('start_utc_ns','20000000001'),('state','running')]:
            changed=copy.deepcopy(ack);changed[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):validate_mapping(request,changed,10000001000)
        for key,value in [('utc_now_ns','15040000000'),('uncertainty_ns','500000000'),('state','unsynchronized'),('leap','unknown')]:
            changed=copy.deepcopy(ack);changed['clock'][key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):validate_mapping(request,changed,10000001000)
if __name__=='__main__':unittest.main()
