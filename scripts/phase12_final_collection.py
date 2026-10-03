"""Preserve early evidence, then retrieve finalized teardown records once."""
import os,re
from phase12_recovery_device import strict
from pathlib import Path

def collect_final(remote,names,required=()):
    root=Path(remote.root)
    names=tuple(names)
    if len(set(names))!=len(names):raise ValueError('duplicate final evidence basename')
    for name in names:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',name) or name in ('.','..'):
            raise ValueError('regular final evidence basename required')
        target=root/name;early=root/('before-final-'+name)
        if target.is_symlink() or (target.exists() and not target.is_file()):raise ValueError('final evidence source must be regular')
        if early.exists() or early.is_symlink():raise ValueError('early evidence collision')
    required=set(required)
    if not required.issubset(names):raise ValueError('required final evidence name absent')
    server_existed=(root/'ntp-ready.json').exists() or (root/'ntp-pid.json').exists()
    if server_existed:
        required.update(name for name in ('ntp-stopped.json','ntp-server.log') if name in names)
    for name in names:
        target=root/name;early=root/('before-final-'+name)
        if target.exists():
            required.add(name)
            # Exclusive link preserves bytes before opening the final basename.
            os.link(target,early,follow_symlinks=False);target.unlink()
    remote.collect(names)
    for name in names:
        target=root/name
        if name in required and not target.exists():raise ValueError('previously observed final evidence missing')
        if target.is_symlink() or (target.exists() and not target.is_file()):raise ValueError('collected final evidence must be regular')
    if server_existed and 'ntp-stopped.json' in names:
        stopped=strict((root/'ntp-stopped.json').read_bytes())
        if not (type(stopped.get('requests')) is int and type(stopped.get('replies')) is int and
                0<=stopped['replies']<=stopped['requests']<=2000):
            raise ValueError('actual bounded final responder counters required')
        # A zero-reply responder never creates per-response metrics. Its
        # original stopped counters are the complete final evidence.
        if stopped['replies']>0 and 'ntp-metrics.json' in names and not (root/'ntp-metrics.json').is_file():
            raise ValueError('positive responder replies require final metrics')
