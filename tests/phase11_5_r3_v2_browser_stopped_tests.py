import json,sys,shutil,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_browser_stopped import audit
BASE=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-browser-b3/evidence'
@unittest.skipUnless(BASE.is_dir(),'Private browser B3 evidence unavailable')
class StoppedBrowserTests(unittest.TestCase):
 def test_intact_and_adversarial_mutations(self):
  self.assertEqual(audit(BASE)['status'],'B3_STOPPED_COMPONENTS_VERIFIED')
  for kind in ['peak','raw_info','raw_wtp','charge','dom','asset','icon','accounting','packet','missing_response']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory(prefix='r3-browser-audit-') as d:
    root=Path(d)/'evidence';shutil.copytree(BASE,root)
    file='browser.jsonl'
    if kind in ['peak','raw_info','raw_wtp']:file='browser-observer.jsonl'
    if kind=='packet':
     with (root/'packet.json').open('a') as f:f.write(' ')
    elif kind=='accounting':
     p=root/'browser-result.json';v=json.loads(p.read_text());v['rf_jobs_charged']=2;p.write_text(json.dumps(v))
    elif kind=='dom':
     p=root/'case-0-terminal-dom.json';v=json.loads(p.read_text());v['job']['state']='running';p.write_text(json.dumps(v))
    else:
     p=root/file;rows=[json.loads(x) for x in p.read_text().splitlines()]
     if kind=='peak':next(x for x in rows if x['kind']=='info')['value']['value']['allocator_peak_bytes']=0
     elif kind=='raw_info':next(x for x in rows if x['kind']=='console_rx')['value']['hex']='7b7d0a'
     elif kind=='raw_wtp':next(x for x in rows if x['kind']=='wtp_rx')['value']['hex']='00'
     elif kind=='charge':next(x for x in rows if x['kind']=='arm_charge')['value']['duration_ns']='11000000000'
     elif kind=='asset':next(x for x in rows if x['kind']=='network_body' and x['value']['response']['url'].endswith(':18443/'))['value']['body']['body']+='x'
     elif kind=='icon':next(x for x in rows if x['kind']=='network_request' and x['value']['request']['url'].startswith('data:'))['value']['request']['url']+='x'
     else:rows=[x for x in rows if not (x['kind']=='network_body' and x['value']['request_id']=='100.10')]
     p.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    with self.assertRaises(Exception):audit(root)
  self.assertEqual(audit(BASE)['status'],'B3_STOPPED_COMPONENTS_VERIFIED')
if __name__=='__main__':unittest.main()
