#!/usr/bin/env python3
"""Opt-in eight-hour wspr5 soak on the qualified onboard AP/USB peer fixture.

The existing diagnostic sampler is copied unchanged into the private deployment.
This controller supplies exact current identity, independent bounded workers,
full AP/peer captures, and a separate automatic restoration service.
"""
import argparse
import contextlib
import datetime
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import phase11_4_hotspot as h
import phase11_4_soak as old
import phase11_4_loop_common as common
from phase11_4_radio_diagnostic import ethernet_check

REVISION = '802c91a7b86e-dirty'
ADDRESS = '10.77.14.10'
SAVED = ('station', 'schedules', 'watermark_utc_ns', 'expires_utc_s', 'enabled', 'suspended')
ROOT = None
BASE_CONSOLE, BASE_HOST, BASE_UNIT = h.console, h.host_check, h.system_unit


def console(command='INFO'):
    value = BASE_CONSOLE()
    common.validate_info(value, value['status']['boot_id'], REVISION)
    if command != 'INFO':
        if (ROOT / 'hotspot-baseline.json').exists():
            baseline = json.loads((ROOT / 'hotspot-baseline.json').read_text())
            if value['status']['boot_id'] != baseline['status']['boot_id']:
                raise ValueError('Unexpected boot: preserve evidence; automatic device mutation blocked')
        return BASE_CONSOLE(command)
    return value


def host():
    result = BASE_HOST()
    ethernet_check()
    return result


def setup():
    h.setup(cleanup_entrypoint=ROOT / 'scripts/phase11_4_controlled_soak.py',
            cleanup_unit='phase11-soak-cleanup', cleanup_after='9h')
    (ROOT / 'target-changed').touch()
    console('CONFIG ' + json.dumps(json.loads((ROOT / 'test-config.json').read_text())))
    console('REBOOT')
    time.sleep(3)
    value = h.ready(ADDRESS)
    h.save('hotspot-baseline.json', value)
    h.usb_check()
    peer = h.in_client(['python3', ROOT / 'scripts/phase11_4_hotspot.py', 'probe', ADDRESS,
        value['status']['boot_id'], '--root', ROOT, '--run'], timeout=40)
    h.save('preflight-peer.json', {'exit': peer.returncode, 'stdout': peer.stdout})
    print('SOAK FIXTURE READY', flush=True)


def cleanup():
    if not (ROOT / 'setup-started').exists():
        return
    h.cmd(['systemctl', 'stop', 'phase11-controlled-soak.service'], check=False)
    h.cleanup()
    h.cmd(['systemctl', 'stop', 'phase11-soak-cleanup.timer'], check=False)
    h.save('soak-restored.json', {'epoch_ns': time.time_ns(), 'result': 'PASS', 'host': host()})
    print('SOAK RESTORATION PASS', flush=True)


def configure_sampler():
    baseline = json.loads((ROOT / 'hotspot-baseline.json').read_text())
    old.BOOT = baseline['status']['boot_id']
    old.REVISION = REVISION
    old.ADDRESS = common.ADDRESS = ADDRESS
    return baseline


def sample(kind):
    baseline = configure_sampler()
    if kind in ('usb', 'wtp'):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            old.usb_sample(kind == 'wtp')
        for line in output.getvalue().splitlines():
            row = json.loads(line)
            if 'info' in row:
                v = row['info']
                for field in SAVED:
                    if v['status'][field] != baseline['status'][field]:
                        row['anomalies'].append('Saved state changed: ' + field)
                if v['network']['ipv4'] != ADDRESS or v['network']['mdns_state'] != 'active':
                    row['anomalies'].append('Discovery/address changed')
            old.emit(row)
    elif kind == 'network':
        old.network_sample(ROOT / 'client-compat', 'linux')
    else:
        old.emit({'host': host(), 'peer': {
            'link': h.in_client(['iw', 'dev', 'wlan2', 'link']).stdout,
            'routes': h.in_client(['ip', '-4', 'route']).stdout,
            'netns': h.in_client(['readlink', '/proc/self/ns/net']).stdout,
            'mountns': h.in_client(['readlink', '/proc/self/ns/mnt']).stdout}})


def note(stream, kind, value):
    stream.write(json.dumps({'epoch_ns': time.time_ns(), 'monotonic_ns': time.monotonic_ns(),
                            'kind': kind, 'value': value}) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def worker(kind):
    plan = json.loads((ROOT / 'run.json').read_text())
    start, end = plan['start_epoch'], plan['end_epoch']
    deadline = time.monotonic() + max(0, end - time.time())
    interval = {'usb': 5, 'network': 30, 'host': 300}[kind]
    count = 0
    with (ROOT / (kind + '.jsonl')).open('x') as log:
        note(log, 'started', {'worker': kind, 'plan': plan})
        while time.time() < end and time.monotonic() < deadline:
            epoch = time.time()
            quiet = old.quiet_window(epoch, start, end)
            if epoch >= start and not (kind == 'network' and quiet):
                mode = 'wtp' if kind == 'usb' and count % 12 == 0 else kind
                args = ['python3', ROOT / 'scripts/phase11_4_controlled_soak.py', 'sample',
                        '--sample', mode, '--root', ROOT, '--run']
                began = time.monotonic()
                try:
                    p = (h.in_client(args, timeout=24, check=False) if kind == 'network'
                         else h.cmd(args, timeout=24, check=False))
                    note(log, 'sample', {'sample': mode, 'quiet_scheduled': quiet,
                        'started_epoch': epoch, 'duration': time.monotonic()-began,
                        'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
                except Exception as error:
                    note(log, 'sample_failure', {'sample': mode, 'started_epoch': epoch,
                         'type': type(error).__name__, 'message': str(error)})
                count += 1
            time.sleep(max(0, min(interval, deadline-time.monotonic(), end-time.time())))
        note(log, 'interval_finished', {'samples': count, 'review_required': True})


def run():
    if (ROOT / 'run.json').exists():
        raise ValueError('Fresh deployment required; never overwrite a soak')
    baseline = configure_sampler()
    value = console()
    common.validate_info(value, baseline['status']['boot_id'], REVISION)
    host()
    start = time.time() + 10
    end = start + 28800
    h.save('run.json', {'start_epoch': start, 'end_epoch': end,
        'start_utc': datetime.datetime.fromtimestamp(start, datetime.timezone.utc).isoformat(),
        'end_utc': datetime.datetime.fromtimestamp(end, datetime.timezone.utc).isoformat(),
        'boot': baseline['status']['boot_id'], 'revision': REVISION,
        'host_boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'address': ADDRESS, 'duration_seconds': 28800, 'status': 'RUNNING; review required'})
    deadline = time.monotonic() + end-time.time()
    children, streams = {}, []
    with (ROOT / 'supervisor.jsonl').open('x') as log:
        try:
            for label, interface, ns in [('ap','wlan0',None),('peer','wlan2',h.NETNS)]:
                stream = (ROOT / (label + '-capture.log')).open('x');streams.append(stream)
                args = ['/usr/bin/tcpdump','-n','-U','-i',interface,'-s','0','-w',str(ROOT/(label+'.pcap')),
                        'ether host 88:a2:9e:0a:60:df or host ' + ADDRESS]
                if ns: args = ['ip','netns','exec',ns,*args]
                children[label] = subprocess.Popen(args,stdout=stream,stderr=stream)
            time.sleep(1)
            if any(p.poll() is not None for p in children.values()) or any(
                    not (ROOT/(n+'.pcap')).exists() or (ROOT/(n+'.pcap')).stat().st_size < 24 for n in ('ap','peer')):
                raise RuntimeError('Capture startup failed')
            for kind in ('usb','network','host'):
                stream=(ROOT/(kind+'.stderr')).open('x');streams.append(stream)
                children[kind]=subprocess.Popen(['python3',str(ROOT/'scripts/phase11_4_controlled_soak.py'),
                     'worker','--worker',kind,'--root',str(ROOT),'--run'],stdout=stream,stderr=stream)
            note(log,'observers_ready',json.loads((ROOT/'run.json').read_text()))
            print('EIGHT HOUR SOAK RUNNING '+str(ROOT),flush=True)
            while time.time()<end and time.monotonic()<deadline:
                note(log,'observer_health',{key:p.poll() for key,p in children.items()})
                time.sleep(max(0,min(30,deadline-time.monotonic(),end-time.time())))
            note(log,'interval_finished',{'review_required':True})
        finally:
            for key,p in children.items():
                if key in ('usb','network','host') and time.time() >= end:
                    try:p.wait(timeout=26)
                    except subprocess.TimeoutExpired:pass
                note(log,'child_closed',{'name':key,**common.stop_process(p)})
            for stream in streams:stream.close()
            note(log,'closed',{'review_required':True})
            # A separate service can stop the controller without stopping itself.
            h.system_unit('phase11-soak-finish',['python3',ROOT/'scripts/phase11_4_controlled_soak.py',
                'cleanup','--root',ROOT,'--run'],seconds=480)


def main():
    global ROOT
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['setup','run','cleanup','worker','sample'])
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--worker',choices=['usb','network','host'])
    p.add_argument('--sample',choices=['usb','wtp','network','host'])
    p.add_argument('--run',action='store_true')
    a=p.parse_args()
    if not a.run:
        print('Plan only; --run is required.');return
    if not __debug__ or sys.platform!='linux' or os.geteuid()!=0:
        raise RuntimeError('Linux root and enabled assertions required')
    os.umask(0o077);os.environ['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
    ROOT=a.root.resolve()
    if not ROOT.is_dir() or ROOT.stat().st_mode & 0o077:raise ValueError('Private root required')
    h.ROOT=ROOT;h.AP_IF='wlan0';h.CLIENT_IF='wlan2'
    h.console=console;h.host_check=host
    h.system_unit=lambda name,args,seconds=33000:BASE_UNIT(name,args,seconds)
    def interrupted(signum,frame):raise InterruptedError('Bounded service interrupted')
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    if a.command=='worker':
        if not a.worker:p.error('--worker required')
        worker(a.worker)
    elif a.command=='sample':
        if not a.sample:p.error('--sample required')
        sample(a.sample)
    else:globals()[a.command]()


if __name__=='__main__':main()
