"""C0 target panic attribution and independent USB cleanup failures."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase11_5_inventory as inventory
from audit_phase11_5_r3_c0_failure import audit


class CleanupTests(unittest.TestCase):
    def test_failed_lock_never_changes_another_owners_control_lines(self):
        with patch.object(inventory.subprocess,'run',return_value=Mock(returncode=1,stdout=b'',stderr=b'')), \
             patch.object(inventory.os,'open',return_value=91),patch.object(inventory.os,'close') as close, \
             patch.object(inventory.fcntl,'flock',side_effect=BlockingIOError('owner raced admission')), \
             patch.object(inventory.fcntl,'ioctl') as ioctl:
            with self.assertRaises(BlockingIOError):
                with inventory.exclusive_port(Path('/unused')):self.fail('lock was not acquired')
            ioctl.assert_not_called();close.assert_called_once_with(91)

    def test_primary_failure_survives_both_ioctl_cleanup_errors(self):
        primary=TimeoutError('original transfer deadline')
        def ioctl(fd, op, *args):
            if op in (inventory.termios.TIOCMBIC,inventory.termios.TIOCNXCL):
                raise OSError('disconnected cleanup')
        with patch.object(inventory.subprocess,'run',return_value=Mock(returncode=1,stdout=b'',stderr=b'')), \
             patch.object(inventory.os,'open',return_value=91),patch.object(inventory.os,'close') as close, \
             patch.object(inventory.fcntl,'flock'),patch.object(inventory.fcntl,'ioctl',side_effect=ioctl), \
             patch.object(inventory,'configure_raw'):
            with self.assertRaises(TimeoutError) as caught:
                with inventory.exclusive_port(Path('/unused')):raise primary
            self.assertIs(caught.exception,primary)
            self.assertEqual(len(primary.__notes__),2)
            close.assert_called_once_with(91)

    def test_cleanup_failure_after_success_still_fails(self):
        def ioctl(fd,op,*args):
            if op==inventory.termios.TIOCMBIC:raise OSError('DTR failed')
        with patch.object(inventory.subprocess,'run',return_value=Mock(returncode=1,stdout=b'',stderr=b'')), \
             patch.object(inventory.os,'open',return_value=91),patch.object(inventory.os,'close') as close, \
             patch.object(inventory.fcntl,'flock'),patch.object(inventory.fcntl,'ioctl',side_effect=ioctl), \
             patch.object(inventory,'configure_raw'):
            with self.assertRaisesRegex(OSError,'DTR failed'):
                with inventory.exclusive_port(Path('/unused')):pass
            close.assert_called_once_with(91)


@unittest.skipUnless(os.environ.get('PHASE115_R3_C0_BASE'),'Private C0 evidence not provided')
class C0Tests(unittest.TestCase):
    def test_preserved_failure_and_adversarial_mutations(self):
        original=Path(os.environ['PHASE115_R3_C0_BASE']);expected=audit(original)
        self.assertEqual(expected['fault_domain'],'FIRMWARE_ALLOCATION_PANIC')
        self.assertFalse(expected['complete_host_write_proven'])
        for mutation in ('wire-crc','wire-length','extra-arm','panic-hash','same-boot',
                         'active-output','host-reset-before-send','helper-change'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                shutil.copytree(original/'evidence',root/'evidence')
                for name in ('reconcile-a.stdout','reconcile-a.stderr','reconcile-b.stdout','reconcile-b.stderr','host-diagnostics.json'):
                    shutil.copyfile(original/name,root/name)
                if mutation.startswith('wire-') or mutation=='extra-arm':
                    path=root/'evidence/capacity.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()]
                    if mutation=='extra-arm':rows[-1]['value']['request']['op']='ARM'
                    else:
                        raw=bytearray.fromhex(rows[-1]['value']['hex']);raw[12 if mutation=='wire-crc' else 11]^=1
                        rows[-1]['value']['hex']=raw.hex()
                    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                elif mutation in ('panic-hash','same-boot','active-output'):
                    path=root/'reconcile-a.stdout';text=path.read_text()
                    text=text.replace('3833354787','0') if mutation=='panic-hash' else \
                         text.replace('bccea7c09794539c4f64bc22b0e76c56','9c5aec394269e0b57ca16d73ad3d12b6') if mutation=='same-boot' else \
                         text.replace('"output_active": false','"output_active": true')
                    path.write_text(text)
                elif mutation=='helper-change':
                    path=root/'evidence/scripts/phase11_5_r3_capacity_probe.py';path.write_text(path.read_text()+'\n')
                else:
                    path=root/'host-diagnostics.json';v=json.loads(path.read_text());rows=[json.loads(s) for s in v['kernel'].splitlines()]
                    next(r for r in rows if 'USB disconnect' in r['MESSAGE'])['__MONOTONIC_TIMESTAMP']='1'
                    v['kernel']='\n'.join(json.dumps(r) for r in rows);path.write_text(json.dumps(v))
                with self.assertRaises((ValueError,KeyError,StopIteration)):
                    audit(root)
        self.assertEqual(audit(original),expected)


if __name__=='__main__':unittest.main()
