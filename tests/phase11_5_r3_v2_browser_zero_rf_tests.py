import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_browser_observer import zero_rf_stop_admitted
class ZeroRfTests(unittest.TestCase):
    def values(self):
        s=dict(boot_id='boot',state='empty',output_active=False,owner_id=None,job_id=None)
        return [dict(status='FAILED',rf_jobs_charged=0,rf_duration_ns_charged='0',cases=[]),[dict(method='GET')],dict(status=copy.deepcopy(s)),s,'boot']
    def test_verified_setup_failure(self):self.assertTrue(zero_rf_stop_admitted(*self.values()))
    def test_any_mutation_or_uncertainty_keeps_readers(self):
        for kind in ['post','charged','duration','boot','active','loaded','owner','job','case']:
            a=self.values()
            if kind=='post':a[1].append(dict(method='POST'))
            elif kind=='charged':a[0]['rf_jobs_charged']=1
            elif kind=='duration':a[0]['rf_duration_ns_charged']='1'
            elif kind=='boot':a[3]['boot_id']='other'
            elif kind=='active':a[3]['output_active']=True
            elif kind=='loaded':a[3]['state']='loaded'
            elif kind=='owner':a[3]['owner_id']='owner'
            elif kind=='job':a[3]['job_id']='job'
            else:a[0]['cases']=[{}]
            with self.subTest(kind=kind):self.assertFalse(zero_rf_stop_admitted(*a))
if __name__=='__main__':unittest.main()
