"""Shared conducted-path reservation; process exit never clears RF uncertainty."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import require

PATH = Path('/home/pi/phase11-5-shared-rf-reservation.json')
BOARDS = {
    'a': ('0BF4B4AEC9FFB344', 'fd6127d11d6aca42a9905fa3fb1bf1d5'),
    'b': ('CDDBF8767C506C07', '29f20b7342051ef947aa56cb9d4fab42'),
}


def inactive(values):
    require(set(values) == set(BOARDS), 'Both named boards require reconciliation')
    identities = {}
    for name, value in values.items():
        info, status = value['info'], value['wtp']['STATUS']
        require(info['device_id'] == BOARDS[name][1] == value['wtp']['HELLO']['device_id'],
                'Reservation device identity')
        require(info['status']['boot_id'] == status['boot_id'] == value['wtp']['HELLO']['boot_id'],
                'Reservation boot identity')
        require(status['state'] == info['status']['state'] and
                status['state'] in ('empty', 'complete', 'aborted', 'missed') and
                status['output_active'] is info['status']['output_active'] is False and
                status['owner_id'] is None and info['status']['enabled'] is False,
                'Reservation requires inactive, unarmed, unowned and schedules disabled')
        identities[name] = dict(device_id=info['device_id'], boot_id=status['boot_id'],
                                revision=info['revision'], state=status['state'])
    return identities


class Reservation:
    def __init__(self, packet_hash, path=PATH, *, reconciliation=None,
                 authorized_boot_changes=None, authorized_revision_changes=None):
        self.path = path
        self.packet_hash = packet_hash
        self.held = False
        self.fd = os.open(str(path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(not path.is_symlink(), 'Reservation symlink refused')
            previous = json.loads(path.read_text()) if path.exists() else None
            if reconciliation is None:
                require(authorized_boot_changes is None and authorized_revision_changes is None,
                        'Boot/revision changes require reconciliation evidence')
                require(previous is None or previous['state'] == 'RELEASED',
                        'Prior RF reservation unresolved; reconcile before any new RF')
            else:
                values, observed_ns = reconciliation
                identities = inactive(values)
                allowed = authorized_boot_changes or {}
                revisions = authorized_revision_changes or {}
                require(set(allowed).issubset(BOARDS) and set(revisions).issubset(BOARDS) and all(
                    isinstance(pair, (tuple, list)) and len(pair) == 2 and pair[0] != pair[1]
                    for pair in (*allowed.values(), *revisions.values())),
                    'Invalid authorized boot/revision transition')
                require(previous is not None and previous['state'] == 'HELD' and
                        previous['packet_sha256'] == packet_hash and
                        previous['host_boot'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                        'Reconciliation requires the original held reservation')
                changed = {board for board in BOARDS
                           if identities[board]['boot_id'] != previous['boards'][board]['boot_id']}
                changed_revisions = {board for board in BOARDS if
                    identities[board]['revision'] != previous['boards'][board]['revision']}
                require(0 <= time.monotonic_ns() - observed_ns <= 5_000_000_000 and
                        changed == set(allowed) and changed_revisions == set(revisions) and all(
                            identities[b]['device_id'] == previous['boards'][b]['device_id'] and
                            (b not in allowed or tuple(allowed[b]) == (
                                previous['boards'][b]['boot_id'], identities[b]['boot_id'])) and
                            (b not in revisions or tuple(revisions[b]) == (
                                previous['boards'][b]['revision'], identities[b]['revision']))
                            for b in BOARDS),
                        'Reconciliation requires fresh inactive proof and exact authorized '
                        'boot/revision transitions')
                self.held = True
        except BaseException:
            os.close(self.fd)
            raise

    def write(self, state, identities):
        value = dict(state=state, packet_sha256=self.packet_hash, boards=identities,
                     host_boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                     monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())
        raw = (json.dumps(value, sort_keys=True) + '\n').encode()
        temporary = self.path.with_suffix('.tmp')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary.exists():
                temporary.unlink()
        return hashlib.sha256(raw).hexdigest()

    def acquire(self, values):
        require(not self.held, 'Reservation already held')
        identities = inactive(values)
        self.write('HELD', identities)
        self.held = True

    def release(self, values):
        require(self.held, 'No RF reservation to release')
        self.write('RELEASED', inactive(values))
        self.held = False

    def close(self):
        # A crash, exception or unlock leaves HELD on disk until reconciliation.
        os.close(self.fd)
