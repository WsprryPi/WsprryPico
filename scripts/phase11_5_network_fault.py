#!/usr/bin/env python3
"""One bounded DHCP change and one 15-second external AP loss on owned N0.

Separate disruption authorization is required. No USB or Pico management is
used. Before AP loss, an independent owned timer arms an idempotent AP return.
The ordinary LAN, management radio, installed transmitter and forwarding stay
outside this helper's scope. Workload/device outcomes require separate audit.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import time

from phase11_5_inventory import require
from phase11_5_network_fixture import Fixture, PROFILE, PREFIX, DUT_MAC, RADIOS
from phase11_5_device_management import save, digest


def admit_fault(state, action):
    require(action in ('lease','link'), 'Unknown fault')
    require(not state.get('pending') and action not in state.get('attempted',[]),
            'Fault already attempted or unresolved; no automatic retry')


class Fault:
    def __init__(self, root):
        self.host=Fixture(root)
        self.path=root/'network-fault-state.json'
        self.state=json.loads(self.path.read_text()) if self.path.exists() else {}

    def persist(self): save(self.path,self.state)

    def restore_link(self):
        with (self.host.root/'link-return.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            self.state=json.loads(self.path.read_text())
            if self.state.get('link_restored'): return
            self.host.deadline=time.monotonic()+40
            self._restore_link()

    def _restore_link(self):
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.host.state['host_boot'],
                'Host boot changed')
        require(time.monotonic_ns()<self.state['return_deadline_monotonic_ns'], 'AP return deadline expired')
        require(self.state.get('profile_uuid') and not self.host.state.get('restored'),
                'No owned AP return remains')
        require(self.host.value('nmcli','-g','connection.uuid','connection','show',PROFILE)==
                self.state['profile_uuid'],'AP profile identity changed')
        require(Path('/sys/class/net/wlan0/address').read_text().strip()==RADIOS['wlan0'],
                'AP radio identity changed')
        self.host.cmd(['nmcli','--wait','25','connection','up',PROFILE],timeout=30)
        self.host.cmd(['iw','dev','wlan0','set','power_save','off'],timeout=5)
        self.host.note('external_link_restored',{'profile_uuid':self.state['profile_uuid']})
        self.state['link_restored']=True;self.state['pending']=None;self.persist()

    def run(self, action):
        self.host.verify();admit_fault(self.state,action)
        self.state.setdefault('attempted',[]).append(action)
        self.state['pending']=action;self.persist()
        if action=='lease':
            path=self.host.root/'dhcp-hosts'
            require(path.read_text()==DUT_MAC+',10.77.15.10,60s\n','Unexpected DHCP binding')
            unit=PREFIX+'-dhcp.service'
            require(self.host.value('systemctl','show',unit,'-p','Description','--value')==
                    self.host.state['token'],'DHCP unit ownership changed')
            with path.open('w') as stream:
                stream.write(DUT_MAC+',10.77.15.20,60s\n');stream.flush();os.fsync(stream.fileno())
            self.host.cmd(['systemctl','kill','-s','HUP',unit])
            self.host.note('dhcp_binding_changed',{'old':'10.77.15.10','new':'10.77.15.20',
                                                  'device_outcome':'not yet observed'})
            self.state['pending']=None;self.persist();return
        self.state['profile_uuid']=self.host.value('nmcli','-g','connection.uuid','connection','show',PROFILE)
        self.state['return_deadline_monotonic_ns']=time.monotonic_ns()+120_000_000_000
        self.persist()
        unit=PREFIX+'-linkrestore'
        for suffix in ('.timer','.service'):
            require(self.host.value('systemctl','show',unit+suffix,'-p','LoadState','--value')=='not-found',
                    'Link-restoration unit already exists')
        # N0's owned cleanup also knows about these two transient resources.
        self.host.state['units'].extend([unit+'.timer',unit+'.service']);self.host.save()
        self.host.cmd(['systemd-run','--quiet','--unit='+unit,'--description='+self.host.state['token'],
            '--on-active=20s','--property=UMask=0077','--property=RuntimeMaxSec=100',
            '/usr/bin/python3',str(Path(__file__).resolve()),'restore-link',
            '--root',str(self.host.root),'--run'])
        try:
            self.host.cmd(['nmcli','--wait','10','connection','down',PROFILE],timeout=15)
            self.host.note('external_link_down',{'planned_seconds':15})
            time.sleep(15)
        finally:
            self.restore_link()
        self.host.stop_owned(unit+'.timer')
        self.host.note('external_link_case_finished',{'device_outcome':'requires independent USB/network audit'})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('lease','link','restore-link'))
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if not args.run:
        print('Plan only; separate N1 disruption authorization is required.');return
    require(sys.platform=='linux' and os.geteuid()==0,'wspr5 root required')
    os.umask(0o077);root=args.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077==0,'Private fixture root required')
    require(Path(__file__).resolve()==root/'scripts/phase11_5_network_fault.py','Run the staged helper')
    packet=json.loads((root/'packet.json').read_text())
    for relative,expected in packet['helper_sha256'].items():
        path=root/relative
        require(path.resolve().is_relative_to(root) and digest(path)==expected,'Staged helper changed')
    require('scripts/phase11_5_network_fault.py' in packet['helper_sha256'],'Missing fault-helper identity')
    def interrupted(signum,frame): raise InterruptedError('External link action interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if args.action=='restore-link':
        # Do not wait behind the actor whose interrupted sleep this timer must
        # recover. N0 stops this owned unit before removing the AP profile.
        Fault(root).restore_link()
        return
    # Ordinary fault operations serialize with N0 setup/cleanup. AP return has
    # its own lock, and re-reads its durable result to avoid duplicate activation.
    with Path('/run/lock/phase115-closure.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        fault=Fault(root)
        fault.run(args.action)


if __name__=='__main__':main()
