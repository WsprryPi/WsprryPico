#!/usr/bin/env python3
"""Finite retained maximum LOAD with the real native observer; no ARM or RF."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from phase11_5_device_management import digest, save
from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_load_reply_target import Journal, USB, inventory, healthy, request, wait_network
from phase11_5_pilot import SERIAL, DEVICE
from phase11_5_pilot_supervisor import configuration
from phase11_5_r3_v2_admission import maximum_job, candidate
from phase11_5_rf_reservation import Reservation, inactive

SOURCE = 'a9d5610d76f6cb349249b8def6eba65f21e7bfa9'
BOOT = '8d747e80fa4e2762ba2509b5bb5ecfae'


def validate(p):
    require(p['scope'] in ('phase115-completion-native-idle-v1', 'phase115-completion-native-idle-v2', 'phase115-completion-native-idle-v3', 'phase115-completion-native-idle-v4', 'phase115-completion-native-idle-v5', 'phase115-completion-native-idle-v6', 'phase115-completion-native-idle-v7', 'phase115-completion-native-idle-v8', 'phase115-completion-native-idle-v9') and
            (p['source_revision'],p['boot_id']) == (('150fe016bb61518fb259adcedf86d3ac9779d373','c3ea3e2ad15dafe5db2acec253e35c99') if p['scope'].endswith('-v9') else ('6b7a1b848e2b5192acaa0fa08fb778613457ad8b','1739cc4f28304080ec97e2b228ab2683') if p['scope'].endswith(('-v7','-v8')) else ('b0254c5e64abf858255ca6d426e864080f003891','4dad3b38c27aad73da01cefc9e857cdb') if p['scope'].endswith('-v6') else ('0001a3625832b16ad89236cd98cce9679353aba8','6213cc6b8d7694082fb804fdf5b121fc') if p['scope'].endswith('-v5') else ('d674dc6cbf8efd142527c1c54f283d6037bb1acf','d76d4e540ddafff6622513596125c58c') if p['scope'].endswith('-v4') else (SOURCE,BOOT)) and
            p['native_idle_policy'] == 'retained-load-native-90s-v1', 'Identified idle candidate')
    require(p.get('loaded_observation_policy') == ('two-published-loaded-samples-v1' if p['scope'].endswith(('-v8','-v9')) else None), 'Declared Loaded observation gate')
    count=3 if p['scope'].endswith(('-v4','-v5','-v6','-v7','-v8','-v9')) else 2 if p['scope'].endswith('-v1') else 1
    require(p['limits'] == dict(loads=count, fresh_id_replays=1, claims=count, aborts=count,
            releases=count, cleanup_aborts=1, cleanup_claims=1, cleanup_releases=1,
            rf_jobs=0, flashes=0, reboots=0, wifi_cycles=0, configuration_writes=0), 'Idle operation ceilings')
    require(p['runtime_seconds'] == 90 and p['contention']['maximum_https_requests'] == 0 and
            p['work_deadline_monotonic_ns']-p['start_monotonic_ns'] == 450_000_000_000 and
            p['cleanup_deadline_monotonic_ns']-p['work_deadline_monotonic_ns'] == 150_000_000_000 and
            p['cleanup_deadline_monotonic_ns'] < p['fixture_deadline_monotonic_ns'], 'Unextended finite deadlines')
    require(len(p['jobs']) == count and all(j == maximum_job(j['job_id'], duration=128_000_000_000)
            for j in p['jobs']) and len({j['job_id'] for j in p['jobs']}) == count, 'Distinct exact maximum jobs')
    ids = [p[k] for k in ('inventory_session', 'b_session', 'peer_session', 'cleanup_session', 'owner_id')]
    require(len(set(ids)) == len(ids) and all(len(s) == 32 and all(c in '0123456789abcdef' for c in s) for s in ids), 'Separate identities')
    if count==1:
        expected=['7ebc44a6c1ff42b0a6aaafef737af897']
        if p['scope'].endswith('-v3'):expected.insert(0,'681609784d9c46d882f1bd7df5aede7d')
        require(p['initial_terminal_jobs']==expected, 'Retained failed-packet seed identity')
    return p


class LoadedObservationGate:
    """Count distinct fresh native publications for the actual loaded job."""
    def __init__(self, packet_sha, boot, owner, job, began_ns):
        self.packet_sha,self.boot,self.owner,self.job,self.began_ns=packet_sha,boot,owner,job,began_ns
        self.first = None

    def observe(self, value, now_ns):
        require(value['packet_sha256']==self.packet_sha and
                0<=now_ns-value['observed_monotonic_ns']<=6_000_000_000, 'Fresh same-packet native publication')
        stamp=value['observed_monotonic_ns'];job=value.get('job')
        if stamp<self.began_ns or job is None:
            return False
        if not (job['boot_id']==self.boot and job['state']=='loaded' and
                job['job_id']==self.job and job['owner_id']==self.owner and job['output_active'] is False):
            return False
        if self.first is None:self.first=stamp
        return stamp-self.first>=1_000_000_000


def cleanup_identity(info, boot, source):
    # Acceptance failures must not prevent physical safety cleanup. This proves
    # the intended board/boot only; final inventory must still prove inactivity.
    require(info['device_id'] == DEVICE and info['revision'] == source[:12] and
            info['status']['boot_id'] == boot and info['status']['enabled'] is False,
            'Cleanup board/boot/scheduling identity')


def reconcile_authority(reservation, before, final, boot, source):
    identities = inactive(final)
    cleanup_identity(final['a']['info'], boot, source)
    require(all(configuration(before[b]) == configuration(final[b]) for b in before) and
            final['b']['wtp']['STATUS'] == before['b']['wtp']['STATUS'],
            'Final configuration/B preservation')
    reservation.release(final)
    return identities


def run(root, p, sha):
    boot=p['boot_id'];source=p['source_revision']
    require(os.geteuid() == 0 and str(root) == p['root'] and
            Path('/proc/sys/kernel/random/boot_id').read_text().strip() == p['host_boot_id'], 'Host identity')
    for n, h in p['stage_sha256'].items():
        require((root/n).resolve().is_relative_to(root) and digest(root/n) == h, 'Frozen input '+n)
    require(not (root/'run-result.json').exists(), 'Consumed packet')
    emit = Journal(root/'idle.jsonl'); emit('start', dict(packet_sha256=sha))
    result = dict(status='STARTED', loads=0, replays=0, claims=0, aborts=0, releases=0, rf_jobs=0)
    save(root/'run-result.json', result)
    reservation = Reservation(sha); held = False; net = None; observer = None
    stop = threading.Event(); info_ready = threading.Event(); errors = []; before = None
    def deadline(cleanup=False):
        require(p['start_monotonic_ns'] <= time.monotonic_ns() < p['cleanup_deadline_monotonic_ns' if cleanup else 'work_deadline_monotonic_ns'], 'Packet deadline')
    def active():
        deadline(); require(not errors, 'INFO observer failure')
        if net is not None:
            require(not (root/'contention-failed.json').exists(), 'Native observer failure')
            if net.poll() is not None:
                require((root/'contention-result.json').exists() and
                        json.loads((root/'contention-result.json').read_text())['status'] == 'CAPTURED_REQUIRES_AUDIT', 'Native exited unsuccessfully')
    def info_worker():
        try:
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
                next_at = time.monotonic()
                while not stop.is_set():
                    deadline(); began = time.monotonic_ns()
                    v = exchange(fd, b'INFO\n', time.monotonic()+5, lambda k,v:emit('console_'+k,v), False)
                    emit('info',dict(began_ns=began,value=v)); healthy(v,boot,source); info_ready.set()
                    next_at += 1; stop.wait(max(0,next_at-time.monotonic()))
        except BaseException as e:
            errors.append(str(e)); emit('failure',dict(worker='info',error=str(e)))
    hello = dict(versions=['WTP/1'], client_name='retained-native-idle', client_version='1')
    try:
        deadline(); before = {b:inventory(root,p,'before-'+b,b=='b') for b in ('a','b')}
        inactive(before); candidate(before['a'],p,boot=boot)
        records=before['a']['wtp']['STATUS']['terminal_records']
        expected=p.get('initial_terminal_jobs',[])
        require(before['a']['wtp']['STATUS']['state']=='empty' and
                [r['job_id'] for r in records]==expected and all(r['state']=='aborted' and r['output_active'] is False for r in records), 'Exact Empty/retained baseline')
        require(before['b']['wtp']['STATUS']['boot_id']==p['b_boot_id'], 'B boot')
        reservation.acquire(before); held = True
        save(root/'reservation-acquired.json',json.loads(reservation.path.read_text()))
        wait_network(root,boot,active,source)
        plan=p['contention'];pid=plan['client_pid']
        require(os.readlink(f'/proc/{pid}/ns/net')==plan['netns'] and
                os.readlink(f'/proc/{pid}/ns/mnt')==plan['mountns'], 'Original fixture process namespaces')
        with (root/'network.stdout').open('xb') as out, (root/'network.stderr').open('xb') as err:
            net=subprocess.Popen(['nsenter','-t',str(pid),'-m','-n','python3',str(root/'scripts/phase11_5_r3_v2_nominal_load.py'),
                '--root',str(root),'--packet-sha256',sha,'--run'],stdout=out,stderr=err)
        end=time.monotonic()+45
        while not (root/'contention-ready.json').exists():
            active(); require(time.monotonic()<end,'Native readiness deadline');time.sleep(.1)
        observer=threading.Thread(target=info_worker);observer.start()
        require(info_ready.wait(6),'INFO readiness');active()
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
            peer=USB(fd,boot,emit,active);serial=0
            def ask(op,body,label):
                nonlocal serial
                if op in ('CLAIM','LOAD'):
                    until=time.monotonic()+6
                    while True:
                        active();v=json.loads((root/'native-observation.json').read_text())
                        require(v['packet_sha256']==sha and 0<=time.monotonic_ns()-v['observed_monotonic_ns']<=6_000_000_000, 'Fresh native publication')
                        if v['job'] is not None:break
                        require(time.monotonic()<until,'No new stimulus without native status');time.sleep(.05)
                serial+=1;return peer.ask(request(op,body,f'{serial:032x}',p['peer_session']),label)
            ask('HELLO',hello,'hello')
            for index,job in enumerate(p['jobs']):
                active();require(net.poll() is None,'Native must overlap every LOAD')
                result['claims']+=1;save(root/'run-result.json',result)
                ask('CLAIM',dict(owner_id=p['owner_id'],lease_ms=60000),f'claim-{index}')
                result['loads']+=1;save(root/'run-result.json',result)
                reply=ask('LOAD',job,f'load-{index}')
                body=reply['body'];require(body['job_id']==job['job_id'] and body['state']=='loaded' and len(body['adjustments'])==512,'Full maximum reply')
                for n,a in enumerate(body['adjustments']):
                    require(a==dict(event_index=n,requested_frequency_nhz=str(135500000000000 if n%2==0 else 135495000000000),
                        realized_frequency_nhz=str(135500002652407 if n%2==0 else 135494990274310)), 'Exact adjustment')
                if index==len(p['jobs'])-1:
                    result['replays']+=1;save(root/'run-result.json',result)
                    again=ask('LOAD',job,'fresh-id-replay')
                    require(again['body']==body,'Fresh-ID replay equality')
                # Keep the original minimum dwell. A fixed three seconds can
                # miss a transient resolved status between one-Hz publications.
                began=time.monotonic_ns();until=time.monotonic()+3
                if p.get('loaded_observation_policy'):
                    gate=LoadedObservationGate(sha,boot,p['owner_id'],job['job_id'],began)
                    expires=began+6_000_000_000;observed=False
                    while time.monotonic()<until or not observed:
                        active();now=time.monotonic_ns()
                        require(now<expires, 'Loaded publication six-second deadline')
                        observed=gate.observe(json.loads((root/'native-observation.json').read_text()),now) or observed
                        time.sleep(.05)
                    emit('loaded_observation_gate',dict(job_id=job['job_id'],began_ns=began,
                        first_observed_ns=gate.first,ended_ns=time.monotonic_ns()))
                else:
                    while time.monotonic()<until:active();time.sleep(.1)
                result['aborts']+=1;save(root/'run-result.json',result)
                ask('ABORT',dict(job_id=job['job_id']),f'abort-{index}')
                result['releases']+=1;save(root/'run-result.json',result)
                ask('RELEASE',{},f'release-{index}')
                status=ask('STATUS',{},f'retained-{index}')['body']
                require(status['state']=='empty' and status['owner_id'] is None and status['output_active'] is False and
                    any(r['job_id']==job['job_id'] and r['state']=='aborted' for r in status['terminal_records']), 'Retained no-RF baseline')
            while net.poll() is None:active();time.sleep(.2)
            active();require(net.returncode==0,'Native completion')
        result['status']='CAPTURED_REQUIRES_AUDIT'
    except BaseException as e:
        result.update(status='FAILED',error=str(e));emit('failure',dict(worker='main',error=str(e)))
    finally:
        stop.set()
        if observer is not None:observer.join(7)
        if net is not None and net.poll() is None:
            net.terminate()
            try:net.wait(timeout=15)
            except subprocess.TimeoutExpired:net.kill();net.wait(timeout=5)
        if result['status']=='FAILED' and before is not None and held:
            try:
                deadline(True)
                with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
                    v=exchange(fd,b'INFO\n',time.monotonic()+5,lambda k,v:emit('cleanup_'+k,v),False)
                    cleanup_identity(v,boot,source)
                    ack=exchange(fd,b'ABORT\n',time.monotonic()+5,lambda k,v:emit('cleanup_'+k,v),False)
                    require(ack.get('ok') is True,'Cleanup ABORT acknowledgement')
                with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
                    peer=USB(fd,boot,emit,lambda:deadline(True))
                    for n,(op,body) in enumerate([('HELLO',hello),('CLAIM',dict(owner_id=p['owner_id'],lease_ms=5000)),('RELEASE',{})]):
                        peer.ask(request(op,body,f'{n+100:032x}',p['cleanup_session']),'cleanup-'+op)
            except BaseException as e:result['cleanup_error']=str(e)
        try:
            deadline(True);final={b:inventory(root,p,'final-'+b,b=='b') for b in ('a','b')}
            require(before is not None, 'Original inventories required')
            if held:
                result['final'] = reconcile_authority(reservation, before, final, boot, source)
                save(root/'reservation-released.json',json.loads(reservation.path.read_text()))
                try: candidate(final['a'],p,boot=boot)
                except ValueError as e: result.update(status='FAILED',acceptance_error=str(e))
            else:
                # Rejected admission grants no authority to abort or claim a
                # device. Record fresh observations without changing ownership.
                result['preflight_rejected'] = True
                result['final'] = inactive(final)
                require(result['final'] == inactive(before) and
                        all(configuration(before[b]) == configuration(final[b]) for b in before),
                        'Rejected preflight identity/configuration preservation')
        except BaseException as e:result.update(status='FAILED',reconciliation_error=str(e))
        reservation.close()
        if errors:result.update(status='FAILED',observer_errors=errors)
        save(root/'run-result.json',result);emit('finish',result)
        emit.file.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--packet-sha256',required=True);parser.add_argument('--run',action='store_true');a=parser.parse_args()
    if not a.run:print('Plan only; no device or network access.');return
    root=a.root.resolve(strict=True);require(digest(root/'packet.json')==a.packet_sha256,'Frozen packet digest')
    run(root,validate(json.loads((root/'packet.json').read_text())),a.packet_sha256)


if __name__=='__main__':main()
