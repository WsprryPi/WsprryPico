#!/usr/bin/env python3
"""Opt-in, hash-bound staging only. Does not run a fixture or open a device."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile


def require(value, message):
    if not value:
        raise ValueError(message)


def unpack(archive, packet_sha, root, own_sha):
    require(not root.exists(), 'New R3 root required; no overwrite or staging replay')
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tar:
        members = tar.getmembers()
        require(0 < len(members) <= 150 and sum(m.size for m in members) <= 30 * 1024 * 1024,
                'Staging archive bounds')
        require(len({m.name for m in members}) == len(members) and all(m.isfile() and
                not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts
                and str(PurePosixPath(m.name)) == m.name and m.name != '.'
                for m in members), 'Unsafe or duplicate archive member')
        data = {m.name: tar.extractfile(m).read() for m in members}
    require(hashlib.sha256(data['packet.json']).hexdigest() == packet_sha, 'Unapproved packet bytes')
    packet = json.loads(data['packet.json'])
    require(packet['root'] == str(root) and packet['r3_scope'] == 'phase11.5-r3-tls-a1-v1', 'R3 staging root/scope')
    require(set(data) == {'packet.json'} | set(packet['stage_sha256']), 'Archive manifest differs')
    require(packet['stage_sha256']['scripts/phase11_5_r3_tls_stage.py'] == own_sha,
            'Uploaded staging helper differs')
    for relative, sha in packet['stage_sha256'].items():
        require(hashlib.sha256(data[relative]).hexdigest() == sha, 'Archive content changed')
    # Resolve and hash every existing private input before creating the new root.
    for relative, spec in packet['remote_copy_inputs'].items():
        require(relative not in data and not PurePosixPath(relative).is_absolute()
                and '..' not in PurePosixPath(relative).parts, 'Private copy destination')
        path = Path(spec['path'])
        require(path.is_absolute() and not path.is_symlink(), 'Private source path')
        content = path.read_bytes()
        require(hashlib.sha256(content).hexdigest() == spec['sha256'], 'Existing private input changed')
        data[relative] = content
    root.mkdir(mode=0o700)
    for relative, content in data.items():
        path = root / relative
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o600)
    return dict(status='STAGED_ONLY', root=str(root), files=len(data), packet_sha256=packet_sha)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--packet-sha256', required=True)
    p.add_argument('--archive-sha256', required=True)
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    if not a.run:
        print('Plan only; no files copied or devices accessed.')
        return
    require(os.geteuid() == 0 and a.root.is_absolute(), 'Private wspr5 staging requires root')
    os.umask(0o077)
    raw = a.archive.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == a.archive_sha256, 'Unapproved archive bytes')
    value = unpack(raw, a.packet_sha256, a.root, hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    print(json.dumps(value))


if __name__ == '__main__':
    main()
