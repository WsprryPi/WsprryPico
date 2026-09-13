"""Only explicitly selected packets may add early AP diagnostics."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_join_diagnostics import selected,select_journal,capture,POLICY

BOOT='220e53ca-ca95-4206-9581-dbe28aa1eeb8'

class JoinDiagnosticTests(unittest.TestCase):
    def entry(self,message='wlan0: EAPOL-4WAY-HS-COMPLETED 88:a2:9e:0a:60:df'):
        return dict(__MONOTONIC_TIMESTAMP='1000000',__REALTIME_TIMESTAMP='2000000',
                    _BOOT_ID=BOOT.replace('-',''),_SYSTEMD_UNIT='wpa_supplicant.service',
                    _COMM='wpa_supplicant',MESSAGE=message)

    def test_old_packets_unchanged_and_new_scope_is_explicit(self):
        self.assertFalse(selected({}))
        p=dict(network_join_diagnostics=POLICY,schema='phase11.5-r3-retained-fixture-v1',family='R3',configuration_writes=0)
        self.assertTrue(selected(p))
        for changed in (dict(network_join_diagnostics=True),dict(network_join_diagnostics='unknown'),
                        dict(family='R2'),dict(schema='other'),dict(configuration_writes=1)):
            with self.assertRaises(ValueError):selected(p|changed)

    def test_journal_retains_target_interface_and_host_identity(self):
        entry=self.entry();raw='\n'.join(json.dumps(r) for r in (entry,self.entry('wlan1: management event')))
        self.assertEqual(select_journal(raw,BOOT,0),[entry])
        self.assertEqual(select_journal(raw,BOOT,1000000001),[])
        for changed in (dict(_BOOT_ID='f'*32),dict(_SYSTEMD_UNIT='other.service')):
            with self.assertRaises(ValueError):select_journal(json.dumps(entry|changed),BOOT,0)

    def test_capture_records_live_phase_and_refuses_unknown_phase_or_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'fixture.jsonl').write_text(json.dumps(dict(utc_ns=2_000_000_000,monotonic_ns=0))+'\n')
            calls=[]
            def cmd(args,check=True):
                calls.append(args)
                return SimpleNamespace(stdout=json.dumps(self.entry()) if args[0]=='journalctl' else 'Station 88:a2:9e:0a:60:df\n',stderr='',returncode=0)
            fixture=SimpleNamespace(root=root,state=dict(host_boot=BOOT),cmd=cmd,note=lambda *a:None)
            with self.assertRaises(ValueError):capture(fixture,'after-cleanup')
            self.assertEqual(calls,[])
            value=capture(fixture,'before-recovery')
            self.assertEqual(value['entries'],[self.entry()]);self.assertEqual(value['station']['exit'],0)
            self.assertEqual(calls[1],['iw','dev','wlan0','station','get','88:a2:9e:0a:60:df'])
            with self.assertRaises(FileExistsError):capture(fixture,'before-recovery')

if __name__=='__main__':unittest.main()
