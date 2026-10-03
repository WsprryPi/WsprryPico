#!/usr/bin/env python3
"""Narrow/broad scan schedule regression; no live operations."""
from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import phase12_engineering_fixture as f

class Tests(unittest.TestCase):
    def run_case(self,*,bad_cap=None,match=4,late=False):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);root=Path(directory.name);now=[0.0];scans=[];commands=[];ssid='p12-'+'a'*12
        capabilities='\n'.join(' * '+str(2407+channel*5)+'.0 MHz ['+str(channel)+'] (20.0 dBm)' for channel in range(1,12))+'\n'
        if bad_cap:capabilities=bad_cap(capabilities)
        beacon=('BSS e8:4e:06:ae:d7:09(on wlan0)\n freq: 2422.0\n SSID: '+ssid+'\n RSN: * Version: 1\n * Group cipher: CCMP\n * Pairwise ciphers: CCMP\n * Authentication suites: PSK\n').encode()
        def execute(argv,**kw):
            commands.append((argv,kw.get('timeout')))
            if 'GENERAL.STATE' in argv:raw=b'30 (disconnected)\n'
            elif argv[-1]=='link':raw=b'Not connected.\n'
            elif 'phy1' in argv:raw=capabilities.encode()
            elif argv[-1]=='info' and argv[-2]=='wlan0':raw=b'Interface wlan0\n wiphy 1\n type managed\n'
            elif argv[-1]=='info':raw=('Interface wlan2\n addr e8:4e:06:ae:d7:09\n ssid '+ssid+'\n type AP\n channel 3 (2422 MHz)\n').encode()
            else:
                scans.append((now[0],argv));raw=beacon if len(scans)==match else b''
                if late:now[0]=45
            return f.subprocess.CompletedProcess(argv,0,raw,b'')
        with patch.object(f,'management',return_value={}),patch.object(f.subprocess,'run',side_effect=execute):
            try:result=f.wait_owned_beacon(root,ssid,{},alternate_scans=True,clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay));error=None
            except (ValueError,TimeoutError) as failure:result=None;error=failure
        return result,error,scans,commands,json.loads((root/'owned-ap-beacon-readiness.json').read_text())

    def test_exact_alternation_schedule_legality_and_original_beacon(self):
        result,error,scans,commands,receipt=self.run_case()
        self.assertIsNone(error);self.assertEqual(result['status'],'INDEPENDENT_BEACON_READY');self.assertEqual([row[0] for row in scans],[0,10,20,30])
        broad=[str(freq) for freq in range(2412,2463,5)]
        self.assertEqual([argv[argv.index('freq')+1:] for _,argv in scans],[['2422'],broad,['2422'],broad])
        self.assertEqual(sum('phy1' in argv for argv,_ in commands),2)
        self.assertTrue(all(bound<=15 for _,bound in commands));self.assertFalse(any(word in ('up','down','join','add','set') for argv,_ in commands for word in argv))
        self.assertEqual(receipt['bssid'],'e8:4e:06:ae:d7:09');self.assertEqual(receipt['frequency_mhz'],2422)

    def test_illegal_fraction_duplicate_or_no_ir_stops_before_broad_scan(self):
        changes=(lambda raw:raw.replace('2412.0 MHz','2412.1 MHz'),lambda raw:raw+' * 2422 MHz [3] (20dBm)\n',lambda raw:raw.replace('[11] (20.0 dBm)','[11] (no IR)'),lambda raw:raw.replace('[1]','[bad]'))
        for change in changes:
            with self.subTest(change=change):
                result,error,scans,commands,receipt=self.run_case(bad_cap=change)
                self.assertIsNone(result);self.assertIsNotNone(error);self.assertEqual(len(scans),1);self.assertEqual(receipt['status'],'INDEPENDENT_BEACON_FAILED')

    def test_empty_scans_remain_four_and_late_scan_never_qualifies(self):
        result,error,scans,commands,receipt=self.run_case(match=99)
        self.assertIsNone(result);self.assertIsInstance(error,TimeoutError);self.assertEqual(len(scans),4)
        result,error,scans,commands,receipt=self.run_case(match=1,late=True)
        self.assertIsNone(result);self.assertIsNotNone(error);self.assertEqual(len(scans),1)

if __name__=='__main__':unittest.main()
