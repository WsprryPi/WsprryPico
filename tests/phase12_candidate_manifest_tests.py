#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase12_candidate_manifest as manifest

COMMIT = '1' * 40
SDK = '079c6f39023649b154152db30f1d781e884879bc'

class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inspect = {}
        self.data = {'schema': manifest.SCHEMA, 'source_commit': COMMIT, 'sdk_commit': SDK,
                     'toolchain': 'GNU Arm 15.3.1', 'authority': 'NONE_PREPARATION_ONLY', 'candidates': []}
        for role in sorted(manifest.ROLES):
            stage = int(role[6:]) if role.startswith('fault_') else 0
            c = {'role': role, 'firmware': '0.0.0-devel', 'revision': COMMIT[:12],
                 'target': 'WsprryPico-StandaloneRF' if role == 'rf_ap' else 'WsprryPico',
                 'gp14': role in ('consumer', 'rf_ap'), 'lan_mode': 'tls' if role == 'engineering' else 'plain',
                 'fault_stage': stage, 'session_deadline_fixture': role == 'session_deadline'}
            payload = b'0.0.0-devel\0' + COMMIT[:12].encode() + b'\0'
            elf = bytearray(84 + len(payload))
            elf[:7] = b'\x7fELF\x01\x01\x01'
            struct.pack_into('<H', elf, 18, 40)
            struct.pack_into('<I', elf, 28, 52)
            struct.pack_into('<HH', elf, 42, 32, 1)
            struct.pack_into('<8I', elf, 52, 1, 84, 0x10000000, 0x10000000, len(payload), len(payload), 5, 4)
            elf[84:] = payload
            uf2 = bytearray(512)
            struct.pack_into('<8I', uf2, 0, 0x0a324655, 0x9e5d5157, 0x2000, 0x10000000, 256, 0, 1, 0xe48bff59)
            uf2[32:32+len(payload)] = payload
            struct.pack_into('<I', uf2, 508, 0x0ab16f30)
            symbols = 'wsprrypico::rf::start_worker(\n' if role == 'rf_ap' else 'DryRunEngine\n'
            if c['gp14']: symbols += 'PicoGp14Capture\n'
            assembly = ''
            if stage:
                symbols += 'phase12_fault_stage()\nphase12_profile_programmed(\nphase12_reset_checkpoint(\n'
                assembly = ('10000000 <wsprrypico::provisioning::phase12_fault_stage()>:\n'
                            f'10000000: 2000 movs r0, #{stage}\n10000002: 4770 bx lr\n'
                            '\n10000004 <wsprrypico::standalone::PicoProfileMedia::program(unsigned int)>:\n'
                            '10000004: f000 bl 10000008 <wsprrypico::provisioning::phase12_profile_programmed(unsigned int)>\n')
            identity = '\n'.join(f'inline constexpr char {k}[] = "{v}";' for k,v in
                [('kFirmwareVersion', c['firmware']), ('kBuildRevision', c['revision']), ('kBoard', 'pico2_w'),
                 ('kProcessor', 'RP2350'), ('kPicoSdkVersion', '2.3.1'), ('kPicoSdkCommit', SDK), ('kArmToolchainVersion', '15.3.1')])
            defines = {'WSPRRY_PICO_CONSUMER_LAN_MODE': '2' if c['lan_mode']=='tls' else '1'}
            for key, value in [('WSPRRY_PICO_GP14_RUNTIME_BUTTON', c['gp14']),
                ('WSPRRY_PICO_PHASE12_FAULT_FIXTURE', bool(stage)),
                ('WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE', c['session_deadline_fixture']),
                ('WSPRRY_PICO_GP14_RF_ACCEPTANCE', role=='rf_ap'),
                ('WSPRRY_PICO_STANDALONE_RF', role=='rf_ap'), ('WSPRRY_PICO_RF_OUTPUT_DISABLED', role!='rf_ap')]:
                if value: defines[key]='1'
            argv = ['cc', *['-D'+k+'='+v for k,v in defines.items()], '-o', f'CMakeFiles/{c["target"]}.dir/main.o']
            records = [{'file':'/repo/src/standalone/pico/main.cpp', 'arguments':argv}]
            if stage:
                records.append({'file':'/repo/src/provisioning/pico/phase12_fault_fixture.cpp',
                    'arguments':['cc', '-DWSPRRY_PICO_PHASE12_FAULT_STAGE='+str(stage), '-o',f'CMakeFiles/{c["target"]}.dir/fixture.o']})
            e10 = bytearray(512)
            struct.pack_into('<8I', e10, 0, 0x0a324655, 0x9e5d5157, 0xa000, 0x10ffff00, 256, 0, 2, 0xe48bff57)
            e10[32:288] = bytes([0xef])*256
            struct.pack_into('<I', e10, 288, 0x9957e304)
            struct.pack_into('<I', e10, 508, 0x0ab16f30)
            for name, content in [('elf',bytes(elf)), ('uf2',bytes(e10)+bytes(uf2)), ('map',b'FLASH 0x10000000 0x003f3000 xr\n'),
                ('symbols', symbols.encode()), ('build_identity', identity.encode()), ('compile_commands', json.dumps(records).encode())]:
                c[name] = self.put(role+'.'+name, content)
            self.inspect[c['elf']['path']] = (symbols, assembly)
            self.data['candidates'].append(c)

    def put(self, name, content):
        (self.root/name).write_bytes(content)
        return {'path':name, 'sha256':hashlib.sha256(content).hexdigest(), 'bytes':len(content)}

    def run_verify(self):
        return manifest.verify(self.data, self.root, lambda p:self.inspect[p.name])

    def test_complete_set(self):
        self.assertEqual(self.run_verify()['candidates'], 15)

    def test_dirty_identity_rejected(self):
        self.data['candidates'][0]['revision'] += '-dirty'
        with self.assertRaises(ValueError): self.run_verify()

    def test_forged_symbols_rejected(self):
        c=self.data['candidates'][0]
        c['symbols']=self.put('forged', b'DryRunEngine\nfalse\n')
        with self.assertRaises(ValueError): self.run_verify()

    def test_wrong_compiled_stage_rejected(self):
        c=next(c for c in self.data['candidates'] if c['role']=='fault_8')
        records=manifest.read_json(self.root/c['compile_commands']['path'])
        records[1]['arguments'][1]='-DWSPRRY_PICO_PHASE12_FAULT_STAGE=9'
        c['compile_commands']=self.put('wrongcommands', json.dumps(records).encode())
        with self.assertRaises(ValueError): self.run_verify()

    def test_wrong_linked_stage_rejected(self):
        c=next(c for c in self.data['candidates'] if c['role']=='fault_8')
        syms,asm=self.inspect[c['elf']['path']]
        self.inspect[c['elf']['path']]=(syms,asm.replace('#8','#9'))
        with self.assertRaises(ValueError): self.run_verify()

    def test_mismatched_uf2_rejected_even_rehashed(self):
        c=self.data['candidates'][0]
        raw=bytearray((self.root/c['uf2']['path']).read_bytes());raw[544]^=1
        c['uf2']=self.put('wronguf2',bytes(raw))
        with self.assertRaises(ValueError): self.run_verify()

    def test_missing_role_rejected(self):
        self.data['candidates'].pop()
        with self.assertRaises(ValueError): self.run_verify()

    def test_real_rf_macro_on_inhibited_rejected(self):
        c=self.data['candidates'][0]
        records=manifest.read_json(self.root/c['compile_commands']['path'])
        records[0]['arguments'].insert(1,'-DWSPRRY_PICO_STANDALONE_RF=1')
        c['compile_commands']=self.put('unsafecommands',json.dumps(records).encode())
        with self.assertRaises(ValueError): self.run_verify()

    def test_duplicate_json_and_traversal_rejected(self):
        path=self.root/'duplicate';path.write_text('{"x":1,"x":2}')
        with self.assertRaises(ValueError): manifest.read_json(path)
        c=self.data['candidates'][0];c['elf']['path']='../escape'
        with self.assertRaises(ValueError): self.run_verify()

if __name__=='__main__': unittest.main()
