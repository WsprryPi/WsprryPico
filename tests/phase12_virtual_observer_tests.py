#!/usr/bin/env python3
"""Private prototype tests: finite topology, one create, exact cleanup ownership."""
import json
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import phase12_fixture_roles as roles
import phase12_virtual_observer as v
import phase12_engineering_fixture as fixture
import phase12_populated_dispatch as dispatch
import subprocess

RAW='''valid interface combinations:
         * #{ managed, P2P-client } <= 2, #{ P2P-GO } <= 1, #{ P2P-device } <= 1,
           total <= 3, #channels <= 2
         * #{ managed, P2P-client } <= 2, #{ AP } <= 1, #{ P2P-device } <= 1,
           total <= 3, #channels <= 1
        HT Capability overrides:
'''

class Tests(unittest.TestCase):
    def setUp(self):self.map=roles.role_map('concurrent','a'*32)
    def write(self,path,value):path.write_text(json.dumps(value))
    def test_map_unique_finite_and_hash_bound(self):
        self.assertLessEqual(len(self.map['observer']),15);self.assertEqual(self.map['host_ap'],'wlan2');self.assertEqual(self.map['beacon_observer'],'wlan0')
        self.assertNotEqual(self.map['observer'],roles.role_map('concurrent','b'*32)['observer'])
        with self.assertRaises(ValueError):roles.role_map('concurrent')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture-roles.json';p.write_text(json.dumps(self.map));self.assertEqual(roles.load_roles(d),self.map)
            data=dict(self.map,observer='wlan1');p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):roles.load_roles(d)
    def test_actual_combo_continuations_and_incompatible_alternatives(self):
        v.combinations(RAW)
        for bad in (RAW.replace('#{ AP } <= 1','#{ P2P-GO } <= 1'),RAW.replace('#channels <= 1','#channels <= 2'),RAW.replace('total <= 3','total <= 1'),RAW.replace('managed','monitor')):
            with self.assertRaises(ValueError):v.combinations(bad)
    def test_shared_mode_budget_and_overlapping_groups_refuse(self):
        for body in ('#{ managed, AP } <= 1, total <= 2, #channels <= 1',
                     '#{ managed, AP } <= 2, #{ AP } <= 1, total <= 3, #channels <= 1'):
            with self.assertRaises(ValueError):v.combinations('valid interface combinations:\n * '+body+'\n')
        v.combinations('valid interface combinations:\n * #{ managed, AP } <= 2, total <= 2, #channels <= 1\n')

    def test_topology_collision_and_unowned_sibling_refuse_before_creation(self):
        for inventory in ('phy#2\n Interface wlan2\n Interface '+self.map['observer']+'\n','phy#2\n Interface wlan2\n Interface foreign\n'):
            with self.assertRaises(ValueError):v.topology(self.map,lambda *argv:inventory if argv[-1]=='dev' else RAW)
        proof=v.topology(self.map,lambda *argv:'phy#2\n Interface wlan2\n' if argv[-1]=='dev' else RAW)
        self.assertTrue(proof['name_absent'])
    def test_full_lifecycle_survives_ap_stop_and_checks_wdev_before_delete(self):
        with tempfile.TemporaryDirectory() as d:
            active=[False];calls=[];name=self.map['observer'];wdev=['0x9']
            def read(*argv):
                if argv[-1]=='dev':return 'phy#2\n Interface wlan2\n'+(' Interface '+name+'\n' if active[0] else '')
                if argv[-1]=='info':return 'Interface '+name+'\n wiphy 2\n wdev '+wdev[0]+'\n type managed\n'
                if argv[-1]=='link':return 'Not connected.\n'
                if 'GENERAL.STATE' in argv:return '30 (disconnected)\n'
                raise AssertionError(argv)
            def mutate(*argv):calls.append(argv);active[0]=argv[-1]!='del'
            proof=dict(phy='2',name_absent=True,roles_sha256=self.map['sha256'])
            v.create(d,self.map,proof,read,mutate,self.write)
            self.assertTrue(active[0]);self.assertEqual(len(calls),1)
            # AP stop/restart never invokes virtual lifecycle. Exact receipt stays.
            old=(Path(d)/'virtual-observer-owned.json').read_bytes();self.assertEqual(old,(Path(d)/'virtual-observer-owned.json').read_bytes())
            wdev[0]='0x10'
            with self.assertRaisesRegex(ValueError,'identity changed'):v.remove(d,self.map,read,mutate,self.write)
            self.assertEqual(len(calls),1);wdev[0]='0x9'
            result=v.remove(d,self.map,read,mutate,self.write);self.assertEqual(result['status'],'OWNED_VIRTUAL_OBSERVER_REMOVED');self.assertFalse(active[0]);self.assertEqual(len(calls),2)
            with self.assertRaisesRegex(ValueError,'already attempted'):v.create(d,self.map,proof,read,mutate,self.write)
    def test_creation_uncertain_reconciles_one_attempt_and_can_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            name=self.map['observer'];active=[False];calls=[]
            def read(*argv):
                if argv[-1]=='info':return 'Interface '+name+'\n wiphy 2\n wdev 0x9\n type managed\n'
                if argv[-1]=='link':return 'Not connected.\n'
                if 'GENERAL.STATE' in argv:return '30 (disconnected)\n'
                return 'phy#2\n Interface wlan2\n'+(' Interface '+name+'\n' if active[0] else '')
            def mutate(*argv):
                calls.append(argv);active[0]=argv[-1]!='del'
                if argv[-1]!='del':raise TimeoutError('ambiguous create')
            with self.assertRaises(TimeoutError):v.create(d,self.map,dict(phy='2',name_absent=True,roles_sha256=self.map['sha256']),read,mutate,self.write)
            self.assertEqual(len(calls),1);v.remove(d,self.map,read,mutate,self.write);self.assertEqual(len(calls),2)
    def availability_case(self,states,*,deadline=90,late=False):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);root=Path(directory.name)
        now=[0.0];calls=[];mutations=[];name=self.map['observer']
        def read(*argv):
            calls.append(argv)
            if argv[-1]=='info':return 'Interface '+name+'\n wiphy 2\n wdev 0x9\n type managed\n'
            raw=states.pop(0) if len(states)>1 else states[0]
            if late:now[0]=6
            return raw
        try:
            result=v.create(root,self.map,dict(phy='2',name_absent=True,roles_sha256=self.map['sha256']),read,lambda *argv:mutations.append(argv),self.write,deadline=deadline,clock=lambda:now[0],sleeper=lambda seconds:now.__setitem__(0,now[0]+seconds))
            error=None
        except ValueError as failure:result=None;error=failure
        receipt=json.loads((root/'virtual-observer-owned.json').read_text())
        self.assertEqual(len(mutations),1);self.assertEqual(mutations[0][-4:],('add',name,'type','managed'))
        self.assertFalse(any('up' in argv or 'set' in argv for argv in mutations))
        return result,error,receipt,calls,now[0]

    def test_actual_transient_nm_availability_is_read_only_and_retained(self):
        result,error,receipt,calls,elapsed=self.availability_case(['20 (unavailable)\n','30 (disconnected)\n'])
        self.assertIsNone(error);self.assertEqual(result['state'],'AVAILABLE');self.assertEqual(elapsed,.1)
        self.assertEqual([row['raw'] for row in receipt['nm_states']],['20 (unavailable)\n','30 (disconnected)\n'])
        self.assertEqual(receipt['nm_states'][1]['monotonic_start_s'],.1)
        self.assertTrue(all(argv[:4]==('nmcli','-g','GENERAL.STATE','device') for argv in calls[1:]))

    def test_persistent_unavailable_original_deadline_and_late_success_refuse(self):
        for states,deadline,late in [(['20 (unavailable)\n'],.25,False),(['30 (disconnected)\n'],90,True),(['100 (connected)\n'],90,False)]:
            with self.subTest(states=states):
                result,error,receipt,calls,elapsed=self.availability_case(states,deadline=deadline,late=late)
                self.assertIsNone(result);self.assertIsNotNone(error);self.assertEqual(receipt['state'],'AVAILABILITY_FAILED')
                self.assertGreaterEqual(len(receipt['nm_states']),1)
                if deadline==.25:self.assertLessEqual(elapsed,.25)
                if late:self.assertEqual(receipt['nm_states'][0]['raw'],'30 (disconnected)\n')

    def test_intermediate_stop_keeps_virtual_and_final_cleanup_orders_connection_first(self):
        root='/home/pi/phase12-recovery-'+'a'*32
        name='p12-observer-'+'a'*32
        for action in ('stop','finish'):
            calls=[]
            def command(*argv):
                if argv[-2:]==('connection','show'):return name+'\n'
                calls.append(argv);return ''
            with patch.object(fixture,'load_roles',return_value=self.map),patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'exists',return_value=False),patch.object(fixture,'stop_ntp'),patch.object(fixture,'command',side_effect=command),patch.object(fixture,'management',side_effect=lambda:calls.append(('management-after',)) or {}),patch.object(fixture,'private_write',side_effect=lambda path,value:calls.append(('final-record',path.name))) as saved,patch.object(v,'remove',side_effect=lambda *args:calls.append(('virtual-remove',))) as remove:
                fixture.action(dict(root=root,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action=action))
            self.assertTrue(any(row[-2:]==('delete',name) for row in calls))
            if action=='stop':
                remove.assert_not_called();saved.assert_not_called()
            else:
                remove.assert_called_once();saved.assert_called_once()
                self.assertLess(calls.index(('virtual-remove',)),calls.index(('management-after',)))
                self.assertEqual(calls[-1],('final-record','fixture-management-after.json'))

    def test_concurrent_association_scan_and_single_join_stay_on_channel_three(self):
        class Evidence:
            def record(self,*args,**kwargs):pass
        calls=[];name=self.map['observer']
        def run(argv,**kwargs):
            calls.append(argv)
            if 'scan' in argv:return subprocess.CompletedProcess(argv,0,b'BSS 88:a2:9e:0a:9d:89(on observer)\n freq: 2422\n SSID: WsprryPico-0a9d89\n',b'')
            if argv[-1]=='link':return subprocess.CompletedProcess(argv,0,b'Connected to 88:a2:9e:0a:9d:89\n SSID: WsprryPico-0a9d89\n freq: 2422\n',b'')
            return subprocess.CompletedProcess(argv,0,b'',b'')
        dispatch.associate_observer('owned','WsprryPico-0a9d89',10,Evidence(),interface=name,single_channel=True,clock=lambda:0,runner=run)
        self.assertEqual(calls[0][-3:],['scan','freq','2422'])
        self.assertEqual(sum('up' in row for row in calls),1)
        def wrong(argv,**kwargs):
            row=run(argv,**kwargs);row.stdout=row.stdout.replace(b'2422',b'2412');return row
        calls.clear()
        with self.assertRaisesRegex(ValueError,'exact channel3'):
            dispatch.associate_observer('owned','WsprryPico-0a9d89',10,Evidence(),interface=name,single_channel=True,clock=lambda:0,runner=wrong)
        self.assertFalse(any('up' in row for row in calls))

    def test_actual_channel_frequency_decimals_and_all_fields(self):
        for raw in (b' freq: 2422\n',b'\tfreq: 2422.0\n',b' freq: 2422.000\n'):
            self.assertTrue(dispatch.exact_channel_three(raw))
        for raw in (b'freq: 2422.1\n',b'freq: malformed\n',b'freq: 2422\nfreq: bad\n',b'freq: 2422 freq: 2422\n',b'freq:2422.0\nfreq:2422.0\n'):
            self.assertFalse(dispatch.exact_channel_three(raw))

    def test_wrong_binding_or_active_connection_refuses_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            name=self.map['observer'];found=dict(interface=name,phy='2',wdev='0x9',mode='managed')
            self.write(Path(d)/'virtual-observer-owned.json',dict(interface=name,roles_sha256=self.map['sha256'],identity=found))
            def read(*argv):
                if argv[-1]=='dev':return 'phy#2\n Interface '+name+'\n'
                if argv[-1]=='link':return 'Connected to 11:22:33:44:55:66'
                return 'Interface '+name+'\n wiphy 2\n wdev 0x9\n type managed\n'
            mutations=[]
            with self.assertRaises(ValueError):v.remove(d,self.map,read,lambda *args:mutations.append(args),self.write)
            self.assertEqual(mutations,[])

if __name__=='__main__':unittest.main()
