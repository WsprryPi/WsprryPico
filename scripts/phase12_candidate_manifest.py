#!/usr/bin/env python3
"""Offline, content-bound Phase12 firmware candidate verification. Never flashes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import struct
from check_standalone_image import validate_uf2

SCHEMA = 'phase12-candidates/1'
ROLES = {'restore', 'consumer', 'engineering', 'rf_ap', 'session_deadline',
         *('fault_%d' % n for n in range(1, 11))}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path, limit=1024 * 1024):
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, 'duplicate JSON member')
            out[k] = v
        return out
    require(Path(path).stat().st_size <= limit, 'manifest too large')
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def sha(path):
    require(path.stat().st_size <= 32 * 1024 * 1024, 'artifact too large')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(root, a):
    require(set(a) == {'path', 'sha256', 'bytes'}, 'artifact fields')
    require(isinstance(a['path'], str) and a['path'] and
            not Path(a['path']).is_absolute() and '..' not in Path(a['path']).parts,
            'relative artifact path required')
    p = root / a['path']
    require(not p.is_symlink() and p.resolve().is_relative_to(root), 'artifact escapes root')
    require(type(a['bytes']) is int and a['bytes'] > 0 and
            p.stat().st_size == a['bytes'], 'artifact size mismatch')
    require(isinstance(a['sha256'], str) and
            re.fullmatch('[0-9a-f]{64}', a['sha256']) and sha(p) == a['sha256'],
            'artifact hash mismatch')
    return p


def verify_payload(elf, uf2):
    require(len(elf) >= 52 and elf[:7] == b'\x7fELF\x01\x01\x01' and
            struct.unpack_from('<H', elf, 18)[0] == 40, 'ARM little-endian ELF32 required')
    offset = struct.unpack_from('<I', elf, 28)[0]
    stride, count = struct.unpack_from('<HH', elf, 42)
    require(stride == 32 and 0 < count <= 64 and offset + stride*count <= len(elf),
            'bounded ELF program headers')
    pages = {}
    e10_blocks = 0
    for i in range(0, len(uf2), 512):
        flags, address, size = struct.unpack_from('<III', uf2, i+8)
        if address == 0x10ffff00:
            e10_blocks += 1
            require(e10_blocks <= 1, 'duplicate E10 block')
            continue # exact E10 contents already checked by validate_uf2
        number, total, family = struct.unpack_from('<III', uf2, i+20)
        require(flags == 0x2000 and family == 0xe48bff59 and number == len(pages) and
                total == (len(uf2)//512)-1 and size == 256 and address % 256 == 0,
                'ordinary UF2 flash page required')
        require(address not in pages, 'duplicate UF2 page')
        pages[address] = uf2[i+32:i+32+size]
    covered = set()
    for i in range(count):
        kind, file_offset, _, address, size, _, _, _ = struct.unpack_from('<8I', elf, offset+i*stride)
        if kind != 1 or size == 0:
            continue
        require(0x10000000 <= address < address+size <= 0x103f3000 and
                file_offset+size <= len(elf), 'ELF load segment outside application')
        for n in range(size):
            page = (address+n) & ~255
            require(page in pages and pages[page][(address+n) & 255] == elf[file_offset+n],
                    'UF2 payload differs from ELF')
            covered.add(address+n)
    require(e10_blocks == 1 and covered, 'E10 or ELF load payload absent')
    for address, payload in pages.items():
        require(all(address+i in covered or b in (0, 255) for i,b in enumerate(payload)),
                'unexpected UF2 payload outside ELF segments')


def inspect_binary(elf):
    # Derive symbols/disassembly from the hashed ELF; sidecar text cannot forge
    # a linked feature claim. These read-only tools never execute the image.
    def run(tool, args):
        result = subprocess.run([tool, *args, str(elf)], capture_output=True,
                                text=True, timeout=30, check=True)
        require(len(result.stdout) <= 16 * 1024 * 1024, 'tool output too large')
        return result.stdout
    return run('arm-none-eabi-nm', ['-C']), run('arm-none-eabi-objdump', ['-d', '-C'])


def definitions(entry):
    argv = entry.get('arguments')
    if argv is None:
        argv = shlex.split(entry['command'])
    require(isinstance(argv, list) and all(isinstance(x, str) for x in argv), 'compile argv')
    out = {}
    for arg in argv:
        if arg.startswith('-D'):
            name, sep, value = arg[2:].partition('=')
            require(name not in out or out[name] == (value if sep else '1'), 'conflicting macro')
            out[name] = value if sep else '1'
    return out


def verify_compile(c, records):
    require(isinstance(records, list), 'compile database list')
    selected = [r for r in records if ('CMakeFiles/' + c['target'] + '.dir/') in
                (' '.join(r.get('arguments', [])) or r.get('command', ''))]
    mains = [r for r in selected if r['file'].endswith('/src/standalone/pico/main.cpp')]
    require(len(mains) == 1, 'exact target main compile record')
    d = definitions(mains[0])
    def flag(name, expected):
        require(d.get(name) == expected, 'compiled option mismatch: ' + name)
    flag('WSPRRY_PICO_CONSUMER_LAN_MODE', '2' if c['lan_mode'] == 'tls' else '1')
    flag('WSPRRY_PICO_GP14_RUNTIME_BUTTON', '1' if c['gp14'] else None)
    flag('WSPRRY_PICO_PHASE12_FAULT_FIXTURE', '1' if c['fault_stage'] else None)
    flag('WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE',
         '1' if c['session_deadline_fixture'] else None)
    flag('WSPRRY_PICO_GP14_RF_ACCEPTANCE', '1' if c['role'] == 'rf_ap' else None)
    flag('WSPRRY_PICO_STANDALONE_RF', '1' if c['role'] == 'rf_ap' else None)
    flag('WSPRRY_PICO_RF_OUTPUT_DISABLED', None if c['role'] == 'rf_ap' else '1')
    for diagnostic in ('WSPRRY_PICO_GP14_FLASH_PROBE', 'WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC'):
        flag(diagnostic, None)
    fixtures = [r for r in selected if r['file'].endswith('/phase12_fault_fixture.cpp')]
    require(len(fixtures) == (1 if c['fault_stage'] else 0), 'fixture compile separation')
    if fixtures:
        require(definitions(fixtures[0]).get('WSPRRY_PICO_PHASE12_FAULT_STAGE') ==
                str(c['fault_stage']), 'exact compiled fault stage')


def verify(m, root, inspector=inspect_binary):
    root = Path(root).resolve()
    require(set(m) == {'schema', 'source_commit', 'sdk_commit', 'toolchain',
                       'authority', 'candidates'}, 'manifest fields')
    require(m['schema'] == SCHEMA and m['authority'] == 'NONE_PREPARATION_ONLY', 'schema/authority')
    require(isinstance(m['source_commit'], str) and re.fullmatch('[0-9a-f]{40}', m['source_commit']),
            'exact source commit')
    require(m['sdk_commit'] == '079c6f39023649b154152db30f1d781e884879bc' and
            m['toolchain'] == 'GNU Arm 15.3.1', 'pinned build inputs')
    require(isinstance(m['candidates'], list) and len(m['candidates']) == len(ROLES),
            'complete finite candidate set')
    seen = set()
    for c in m['candidates']:
        require(set(c) == {'role', 'firmware', 'revision', 'target', 'gp14', 'lan_mode', 'fault_stage',
                           'session_deadline_fixture', 'elf', 'uf2', 'map', 'symbols',
                           'build_identity', 'compile_commands'}, 'candidate fields')
        role = c['role']
        require(role in ROLES and role not in seen, 'unknown/duplicate role')
        seen.add(role)
        require(c['firmware'] == '0.0.0-devel' and c['revision'] == m['source_commit'][:12],
                'separate clean firmware/revision identity')
        require(type(c['gp14']) is bool and type(c['session_deadline_fixture']) is bool and
                type(c['fault_stage']) is int, 'typed options')
        expected_stage = int(role[6:]) if role.startswith('fault_') else 0
        require(c['fault_stage'] == expected_stage and
                c['session_deadline_fixture'] == (role == 'session_deadline'), 'fixture role')
        require(c['target'] == ('WsprryPico-StandaloneRF' if role == 'rf_ap' else 'WsprryPico'),
                'target/engine role')
        require(c['gp14'] == (role in {'consumer', 'rf_ap'}) and
                c['lan_mode'] == ('tls' if role == 'engineering' else 'plain'), 'build options')
        elf = artifact(root, c['elf'])
        uf2 = artifact(root, c['uf2'])
        map_file = artifact(root, c['map'])
        symbols_path = artifact(root, c['symbols'])
        symbols, assembly = inspector(elf)
        require(symbols_path.read_text() == symbols, 'symbols differ from hashed ELF')
        verify_compile(c, read_json(artifact(root, c['compile_commands']), 16 * 1024 * 1024))
        identity = artifact(root, c['build_identity']).read_text()
        require(elf.read_bytes().startswith(b'\x7fELF'), 'ELF magic')
        validate_uf2(uf2.read_bytes())
        verify_payload(elf.read_bytes(), uf2.read_bytes())
        require(re.search(r'^FLASH\s+0x10000000\s+0x003f3000\s+xr$', map_file.read_text(), re.M),
                'reserved flash layout')
        for key, value in [('kFirmwareVersion', c['firmware']), ('kBuildRevision', c['revision']),
                           ('kBoard', 'pico2_w'), ('kProcessor', 'RP2350'),
                           ('kPicoSdkVersion', '2.3.1'), ('kPicoSdkCommit', m['sdk_commit']),
                           ('kArmToolchainVersion', '15.3.1')]:
            require(re.search(r'char ' + key + r'\[\] = "' + re.escape(value) + r'";', identity),
                    'build identity header: ' + key)
        binary = elf.read_bytes()
        require((c['revision'] + '\0').encode() in binary and
                (c['firmware'] + '\0').encode() in binary, 'identity absent from ELF')
        require(('wsprrypico::rf::start_worker(' in symbols) == (role == 'rf_ap'), 'RF worker separation')
        require(('DryRunEngine' in symbols) == (role != 'rf_ap'), 'inhibited engine separation')
        require(('PicoGp14Capture' in symbols) == c['gp14'], 'GP14 separation')
        require(('phase12_fault_stage()' in symbols) == bool(expected_stage), 'fault symbol separation')
        if expected_stage:
            require('phase12_profile_programmed(' in symbols and
                    'phase12_reset_checkpoint(' in symbols, 'fixture linkage')
            body = re.search(r'<wsprrypico::provisioning::phase12_fault_stage\(\)>:\n'
                             r'([^\n]*\n[^\n]*)', assembly)
            require(body and re.search(r'\bmovs?\s+r0, #'+str(expected_stage)+r'\b', body[1]) and
                    re.search(r'\bbx\s+lr\b', body[1]), 'linked stage getter mismatch')
            adapter = re.search(r'<wsprrypico::standalone::PicoProfileMedia::program\([^\n]*>:\n'
                                r'([\s\S]*?)(?=\n\n|\Z)', assembly)
            require(adapter and re.search(
                r'\bbl\s+[^\n]*<wsprrypico::provisioning::phase12_profile_programmed\(', adapter[1]),
                'profile adapter has no linked hook call')
        require('bootsel_read' not in symbols.lower(), 'runtime BOOTSEL absent')
    require(seen == ROLES, 'missing candidates')
    return {'status': 'VERIFIED_PREPARATION_ONLY', 'source_commit': m['source_commit'],
            'candidates': len(seen), 'hardware_accessed': False, 'physical_acceptance': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('--artifact-root', type=Path, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(verify(read_json(a.manifest), a.artifact_root), sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        p.exit(1, 'REFUSED: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
