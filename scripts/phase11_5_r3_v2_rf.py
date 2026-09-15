#!/usr/bin/env python3
"""Bounded v2 USB finite RF with independent Console/host observers; opt-in only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from phase11_5_inventory import require,exclusive_port,exchange
from phase11_5_pilot import Peer,SERIAL,DEVICE,check_rf_observation
from phase11_5_pilot_supervisor import finished,configuration,B_SERIAL,B_DEVICE
from phase11_5_device_management import digest,save
from phase11_5_r3_capacity_plan import identity
from phase11_5_r3_v2_observer_policy import SINGLE_FLIGHT,next_offer

SCHEMA='phase11.5-r3-v2-usb-rf-v1'
REPAIRED_SOURCE='c5f00b6109cc1c692b3f6bf258c1a77dadef6639'
REPAIRED_IMAGE='5f681b10d2c076309116cb9c20df1653d21e522ad19b6b33c1ee57efb3f54756'
PAGED_SOURCE='8921a70081839f168edef5926e92445f251d8e1d'
PAGED_IMAGE='3899b498d05ca5b39e23a45e455c44b2784bcf2aca35f62a8ef4db644cc7241b'
INFO_SOURCE='f5502cff9fa6b56747b2e1b1036a77fc0e270f6f'
INFO_IMAGE='a71447e8fe00c023a106ac682f4b11cf8e9e7d93cabb7b5868da10025e2cd5a2'
ASSET_SOURCE='a740dbb8e7319beb20c4807b35f6672bf9fdfd27'
ASSET_IMAGE='454e03e5165143463d6b5f965ea8f1f3704138f08bfc7057704e3fef8f10ebe4'
DIAGNOSTIC_SOURCE='4da36726ac6809bdf4e73d281fe13b2393dd3b31'
DIAGNOSTIC_IMAGE='0153107c517b673bfad7850957c8387a7dbfb12ddb0a3b1e90edb94b804b9a9f'
DIAGNOSTIC_POLICY='single-maximum-failure-capture-v1'
CLOSURE_POLICY='group2-bounded-acceptance-v1'
REPAIR_POLICY='group2-paged-input-retest-v1'
REPAIR_SOURCE='4dad112c8a4c0ce4e5be77ecba5c3c460496472c'
REPAIR_IMAGE='4b4ddd6c9108d20cb7718756da047e4ddd0d4948e6c432d3aa1329d55150d08a'
COMPLETION_POLICY='phase115-completion-capacity-v1'
COMPLETION_SOURCE='98f5797d77fb2bc4c11a4e80f6ff35d7ad16a5b5'
COMPLETION_IMAGE='b6d5ab7610a0e19e9de91ce78dde4eb7c63b9192343dd86af4f7bcb857838733'
B_PARALLEL_AUTHORIZATION='37ae5f5658ffc7c4436547061e4a81e577ea9102a086ec1e74d09031699caaab'


def comparator_required(packet):
    role=packet.get('b_role','unchanged-comparator')
    require(role in ('unchanged-comparator','independent-zero-rf'), 'Explicit B role')
    if role=='independent-zero-rf':
        require(packet['source_revision'] in (REPAIRED_SOURCE,PAGED_SOURCE,INFO_SOURCE,ASSET_SOURCE,DIAGNOSTIC_SOURCE) and
                packet.get('b_parallel_authorization_sha256')==B_PARALLEL_AUTHORIZATION,
                'Independent B requires repaired A and accepted parallel scope')
    return role=='unchanged-comparator'



def native_running(record, packet, packet_sha256, now):
    """Wait for a fresh independent native observation before USB capacity input."""
    require(record['packet_sha256']==packet_sha256,'Native observation packet')
    age=now-record['observed_monotonic_ns']
    require(0<=age<=3_000_000_000,'Fresh native observation required')
    job=record.get('job') or {}
    return (job.get('boot_id')==packet['boot_id'] and job.get('job_id')==packet['jobs'][0]['job_id'] and
            job.get('owner_id')==packet['owner_id'] and job.get('state')=='running' and
            job.get('output_active') is True)


def fresh_sample(samples, lock, name, maximum_age_ns, monotonic_ns=time.monotonic_ns, *, identity=None,inflight=None):
    """Read publication and age atomically with the journal's publisher."""
    with lock:
        stamp, value = samples[name]
        if identity is not None:
            from phase11_5_browser_jobs import admit_snapshot
            admit_snapshot(dict(identity,monotonic_ns=stamp),monotonic_ns(),maximum_age_ns,
                identity['packet_sha256'],inflight.get(name) if inflight is not None else None,
                'INFO' if name=='info' else 'STATUS')
            return value
        age = monotonic_ns() - stamp
        require(0 <= age <= maximum_age_ns,
                f'Fresh {name.upper()} required: age_ns={age}, limit_ns={maximum_age_ns}')
        return value


def guarded_action(action, value, faults, report):
    """A failed mutation guard stops mutations, while its reader continues."""
    if faults:
        return
    try:
        action(value)
    except BaseException as error:
        faults.append('wtp action: ' + str(error))
        report('failure', dict(worker='wtp action', error=str(error), type=type(error).__name__))


def validate(packet):
    diagnostic=packet.get('diagnostic_policy')==DIAGNOSTIC_POLICY
    completion=packet.get('closure_policy')==COMPLETION_POLICY
    repair=packet.get('closure_policy')==REPAIR_POLICY
    closure=packet.get('closure_policy') in (CLOSURE_POLICY,REPAIR_POLICY,COMPLETION_POLICY)
    require('closure_policy' not in packet or closure,'Unknown closure policy')
    require(packet['source_revision']!=REPAIR_SOURCE or repair,'Repair image requires exact retest policy')
    if closure:
        require('diagnostic_policy' not in packet and packet['source_revision']==(COMPLETION_SOURCE if completion else REPAIR_SOURCE if repair else DIAGNOSTIC_SOURCE) and
                packet['observer_policy']==SINGLE_FLIGHT and len(packet['jobs'])==1 and
                packet['runtime_seconds']==300 and packet['maximum_renewals']==8 and
                packet['jobs'][0]['mode']=='fskcw' and len(packet['jobs'][0]['events'])==512 and
                packet['jobs'][0]['total_duration_ns']=='128000000000' and
                all(e==dict(offset_ns=str(n*250000000),duration_ns='250000000',rf_on=True,
                    frequency_nhz=str(135500000000000 if n%2==0 else 135495000000000))
                    for n,e in enumerate(packet['jobs'][0]['events'])) and
                'wtp_capacity' in packet and 'http_capacity' in packet and
                packet['contention']['policy']=='native-wtp-and-https-status-20s-v1' and
                packet['contention']['maximum_https_requests']==16 and
                not packet.get('allocator_failure_baseline'), 'Exact Group 2 capacity tranche')
    if completion:
        require(packet.get('shared_rf_reservation')=='durable-both-picos-v1' and
                packet.get('b_role')=='unchanged-comparator' and
                type(packet.get('maximum_initial_terminal_records')) is int and
                packet['maximum_initial_terminal_records']==1, 'Completion requires both-board RF reservation and bounded initial retention')
    require(packet['source_revision']!=COMPLETION_SOURCE or completion, 'Completion image requires reviewed policy')
    require('diagnostic_policy' not in packet or diagnostic,'Unknown diagnostic policy')
    if diagnostic:
        require(packet['source_revision']==DIAGNOSTIC_SOURCE and
                packet['observer_policy']==SINGLE_FLIGHT,'Diagnostic source/observer scope')
    require(packet['schema']==packet['r3_scope']==SCHEMA and
            packet['standing_authority']=='R3-COMPLETE-20260913-v2' and
            packet['serial']==SERIAL and packet['device_id']==DEVICE and
            (packet['source_revision'],packet['image_sha256']) in [
                ('7d183978d08d77d5de668911be041bb188c851f5',
                 '38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1'),
                (REPAIRED_SOURCE,REPAIRED_IMAGE),(PAGED_SOURCE,PAGED_IMAGE),(INFO_SOURCE,INFO_IMAGE),(ASSET_SOURCE,ASSET_IMAGE),(DIAGNOSTIC_SOURCE,DIAGNOSTIC_IMAGE),(REPAIR_SOURCE,REPAIR_IMAGE),(COMPLETION_SOURCE,COMPLETION_IMAGE)],
            'Reviewed physical source/image/scope')
    if completion:
        require(type(packet.get('not_before_host_monotonic_ns')) is int and
                packet['not_before_host_monotonic_ns']>0, 'Frozen capacity start boundary')
    comparator_required(packet)
    if packet['source_revision']==DIAGNOSTIC_SOURCE and not closure:
        require(len(packet['jobs'])==1 and packet['jobs'][0]['mode']=='tone' and
                packet['jobs'][0]['total_duration_ns']=='90000000000' and
                packet['runtime_seconds']==(240 if diagnostic else 180) and packet['maximum_renewals']==5 and
                'wtp_capacity' in packet and 'contention' not in packet and
                'http_capacity' not in packet and not packet.get('allocator_failure_baseline'),
                'Diagnostic image permits only the reviewed 90-second maximum-input comparison')
    for key in ['owner_id','peer_session','inventory_session','boot_id']:identity(packet[key])
    if 'wtp_capacity' in packet:
        cap=packet['wtp_capacity']
        keys={'maximum_request_id'} if diagnostic else {'maximum_request_id','oversized_request_id','recovery_request_id'}
        require(set(cap)==keys and len({identity(value) for value in cap.values()})==len(keys) and len(packet['jobs'])==1,
            'Exact bounded WTP capacity exchanges')
    if 'http_capacity' in packet:
        from phase11_5_r3_capacity_plan import http_capacity_cases
        cap=packet['http_capacity']
        require(set(cap)=={'seed','cases'} and cap['cases']==http_capacity_cases(cap['seed']) and
            len(packet['jobs'])==1 and 'contention' in packet,'Exact A HTTP boundary stimuli')
    if comparator_required(packet):
        for key in ['b_session','b_boot_id']:identity(packet[key])
    require(type(packet['runtime_seconds']) is int and 1<=packet['runtime_seconds']<=28800 and
            packet['configuration_writes']==packet['wifi_cycles']==packet['heap_probes']==packet['flashes']==0,
            'Finite runtime and no management mutations')
    require(type(packet['maximum_renewals']) is int and 0<=packet['maximum_renewals']<=512 and
            packet['restoration_seconds']==150,'Renewal and restoration bounds')
    if 'contention' in packet:
        require(packet['contention']['policy'] in ['native-wtp-and-https-status-20s-v1','native-wtp-and-bounded-pressure-v1'] and
                packet['runtime_seconds']<=4000 and
                packet['contention']['maximum_https_requests']<=201,'Declared nominal contention')
    jobs=packet['jobs'];require(1<=len(jobs)<=16 and len({j['job_id'] for j in jobs})==len(jobs),'Finite job count')
    total=0
    for j in jobs:
        identity(j['job_id']);duration=int(j['total_duration_ns']);total+=duration
        require(j['profile']=='rf-events/1' and j['mode'] in ['tone','qrss','fskcw','dfcw','wspr'] and
                j['allow_frequency_adjustment'] is True and 0<duration<=3600_000_000_000 and
                0<len(j['events'])<=512,'Finite job bounds')
        offset=0
        for e in j['events']:
            require(int(e['offset_ns'])==offset and int(e['duration_ns'])>0 and type(e['rf_on']) is bool,
                    'Contiguous finite events')
            require(('frequency_nhz' in e)==e['rf_on'] and
                    (not e['rf_on'] or 135490_000_000_000<=int(e['frequency_nhz'])<=135510_000_000_000),
                    'Fixed conducted frequency bounds')
            offset+=int(e['duration_ns'])
        require(offset==duration,'Complete finite duration')
    require(total<=14400_000_000_000 and total+len(jobs)*40_000_000_000<packet['runtime_seconds']*10**9,
            'Total finite budget and observation reserve')
    return packet


def validate_info(info,baseline,packet, *, allow_missed=False):
    old=baseline['info']
    failures=packet.get('allocator_failure_baseline',0)
    if failures:
        require(type(failures) is int and failures in (1,2) and packet['source_revision']==ASSET_SOURCE and
            packet['boot_id']=='2b4583bd3d79a38f030a08c82ed96939' and
            packet.get('allocator_failure_evidence_sha256')=={
                1:'1dfe9f50261824323df93b969370ca8c4bc6d4d7e1b293d3cdeaa8d11dd4f64a',
                2:'551e6985c56a3a088cbdc4b1d6d3a750d3695536f0914eafc54c277f38af26d6'}[failures],
            'Historical C2/C3 failure baseline requires exact retained evidence; no new failures allowed')
    require(info['device_id']==DEVICE and info['revision']==packet['source_revision'][:12] and
            info['status']['boot_id']==packet['boot_id']==old['status']['boot_id'] and
            info['system_clock_hz']==138000000 and info['rf_render_in_ram'] is True and
            info['status']['engine']=='pio-dma-gp2','Physical identity')
    require(info['recovery_boot'] is False and not info['engine_diagnostic'] and
            all(info[k]==0 for k in ['fault_stage','fault_hash','fault_pc','fault_status']) and
            info['status']['storage_healthy'] is True and info['status']['enabled'] is False and
            info['status']['last_error'] is None and
            info['status']['watermark_utc_ns']==old['status']['watermark_utc_ns'],'Fault/configuration')
    for core in [0,1]:
        p=f'core{core}_stack_'
        require(type(info[p+'guard_valid']) is int and info[p+'guard_valid']==1 and info[p+'fault_status']==0 and
                info[p+'guard_bottom']==old[p+'guard_bottom'] and
                info[p+'guard_limit']==old[p+'guard_limit']==info[p+'guard_bottom']+4096,'Stack guard/reserve')
    require(info['heap_capacity_bytes']==old['heap_capacity_bytes'] and
            info['heap_capacity_bytes']-info['allocator_peak_bytes']>=32768 and
            info['allocator_failures']==old['allocator_failures']==str(failures) and
            info['tls_allocation_failures']==old['tls_allocation_failures'],'Allocator reserve/failures')
    require(type(info['status']['output_active']) is bool and
            info['status']['state'] in (['empty','loaded','armed','running','complete','aborted']+(['missed'] if allow_missed else [])) and
            (info['status']['state']=='running' or info['status']['output_active'] is False),'INFO authority')
    check_rf_observation(info)


def diagnostic_identity(info,packet):
    require(info['device_id']==DEVICE and info['revision']==packet['source_revision'][:12] and
            info['status']['boot_id']==packet['boot_id'] and
            type(info['status']['output_active']) is bool,'Diagnostic identity/output authority')


def capture_diagnostic_info(info,baseline,packet,faults,emit):
    """Keep same-identity read-only evidence after failure; acceptance stays strict."""
    diagnostic_identity(info,packet)
    try:
        validate_info(info,baseline,packet)
    except (ValueError,KeyError) as error:
        reason='console diagnostic: '+str(error)
        if reason not in faults:
            faults.append(reason)
            emit('failure',dict(worker='console diagnostic',error=str(error),type=type(error).__name__))
    return info


def recent_clock(info, clock=None):
    """Offer LOAD shortly after accepted SNTP; ARM ten seconds ahead before its
    ordinary 64-second successor. Network resets can still invalidate launch.
    No device clock, polling or guard policy is changed.
    """
    s=info['status']
    ready=(info['network']['accepted']>0 and info['network']['link_status']==3 and
        s['clock_state']=='synchronized' and 0<=int(s['sync_age_ns'])<=5_000_000_000)
    if clock is None:return ready
    return (info['network']['link_status']==3 and info['network']['accepted']>0 and
        s['clock_state']=='synchronized' and clock['state']=='synchronized' and clock['leap']=='normal' and
        0<=int(clock['sync_age_ns'])<=15_000_000_000 and
        0<=int(clock['monotonic_now_ns'])-int(s['monotonic_now_ns'])<=2_000_000_000 and
        int(clock['utc_now_ns'])-int(clock['monotonic_now_ns'])==int(s['utc_now_ns'])-int(s['monotonic_now_ns']) and
        int(clock['uncertainty_ns'])<=500_000_000)


def run(root,packet):
    diagnostic=packet.get('diagnostic_policy')==DIAGNOSTIC_POLICY
    capture_failures=diagnostic or packet.get('closure_policy') in (CLOSURE_POLICY,REPAIR_POLICY,COMPLETION_POLICY)
    os.umask(0o077);end=time.monotonic()+packet['runtime_seconds'];lock=threading.Lock();done=threading.Event()
    faults=[];samples={};inflight={};seq=0;result=dict(status='RUNNING',armed_jobs=[],completed_jobs=[],renewals=0,rf_duration_ns_charged=0)
    log=(root/'rf.jsonl').open('x')
    observer_pid=os.getpid();observer_start=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
    observer_identity=dict(packet_sha256=digest(root/'packet.json'),pid=observer_pid,pid_start_ticks=observer_start)
    def emit(kind,value):
        nonlocal seq
        with lock:
            stamp=time.monotonic_ns()
            log.write(json.dumps(dict(sequence=seq,kind=kind,value=value,monotonic_ns=stamp,utc_ns=time.time_ns()))+'\n')
            log.flush();os.fsync(log.fileno());seq+=1
            if kind in ['info','status','health']:samples[kind]=(stamp,value['value'])
            if kind=='console_tx':inflight['info']=dict(observer_identity,monotonic_ns=stamp,value=value)
            if 'pressure_family' in packet or ('http_capacity' in packet and kind in ['info','status','console_tx','failure']):
                save(root/('observer-'+kind+'.json'),dict(packet_sha256=digest(root/'packet.json'),
                    pid=observer_pid,pid_start_ticks=observer_start,monotonic_ns=stamp,value=value))
                if kind=='failure':save(root/'observer-failure.json',dict(value=value))
    def checkpoint():require(time.monotonic()<end and not faults,'Finite deadline or observer failure')
    def inventory(label,b=False):
        require(not b or comparator_required(packet),'Independent B endpoint is not owned by A')
        with (root/(label+'.stdout')).open('xb') as out,(root/(label+'.stderr')).open('xb') as err:
            code=subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),'--serial',B_SERIAL if b else SERIAL,
                '--device-id',B_DEVICE if b else DEVICE,'--session-id',packet['b_session'] if b else packet['inventory_session'],
                '--run'],stdout=out,stderr=err,timeout=65).returncode
        require(code==0,'Inventory failed: '+label);return finished(root/(label+'.stdout'),'READ_ONLY_INVENTORY')
    def empty(value,b=False):
        i,s=value['info'],value['wtp']['STATUS']
        require(s['boot_id']==(packet['b_boot_id'] if b else packet['boot_id']) and
                s['state']==i['status']['state']=='empty' and s['output_active'] is i['status']['output_active'] is False and
                s['owner_id'] is s['job_id'] is None and i['status']['enabled'] is False,'Inactive/unowned admission')
    before=before_b=None;load_process=None
    reservation=None;final_values={}
    def periodic(name,interval,read,act=None):
        next_at=time.monotonic();last=None;count=0
        singleflight=name=='info' and packet.get('observer_policy')==SINGLE_FLIGHT
        while time.monotonic()<end and not done.is_set():
            began=time.monotonic()
            require(began-next_at<=1 and (singleflight or last is None or began-last<=interval+1),name+' cadence')
            value=read();require(time.monotonic()-began<=5,name+' roundtrip')
            emit(name,dict(began_monotonic_ns=int(began*1e9),value=value));last=began;count+=1
            if act is not None:guarded_action(act,value,faults,emit)
            next_at=next_offer(began,time.monotonic(),interval) if singleflight else next_at+interval
            done.wait(max(0,min(next_at,end)-time.monotonic()))
        emit(name+'_finish',dict(samples=count))
    def console():
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
            def read():
                info=exchange(fd,b'INFO\n',time.monotonic()+5,lambda k,v:emit('console_'+k,v),False)
                if capture_failures:return capture_diagnostic_info(info,before,packet,faults,emit)
                validate_info(info,before,packet);return info
            periodic('info',1,read)
    def health():
        def read():
            boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            throttle=subprocess.check_output(['vcgencmd','get_throttled'],text=True,timeout=2).strip()
            require(boot==packet['host_boot_id'] and throttle=='throttled=0x0','Host health')
            return dict(boot=boot,throttled=throttle,loadavg=Path('/proc/loadavg').read_text().strip(),
                        temperature=Path('/sys/class/thermal/thermal_zone0/temp').read_text().strip())
        periodic('health',5,read)
    def wtp():
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
            peer=Peer(fd,emit,lambda:require(time.monotonic()<end,'WTP observer deadline'),packet['boot_id'])
            peer.session=packet['peer_session'];hello=peer.request('HELLO',dict(versions=['WTP/1'],client_name='R3-v2-RF',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==packet['boot_id'],'Peer identity')
            state=dict(index=0,phase='idle',lease=None,done_at=None)
            def read():
                s=peer.request('STATUS');require(s['boot_id']==packet['boot_id'] and type(s['output_active']) is bool,
                                               'STATUS identity/authority')
                require(s['state'] in ['empty','loaded','armed','running','complete'] and
                        (s['state']=='running' or s['output_active'] is False),'Unexpected RF state')
                require(s['owner_id'] in [None,packet['owner_id']] and
                        (s['job_id'] is None or s['job_id'] in [j['job_id'] for j in packet['jobs']]),'Foreign owner/job')
                return s
            def act(status):
                checkpoint()
                if load_process is not None:
                    require(load_process.poll() is None and not (root/'contention-failed.json').exists(),
                            'Nominal contention worker failed')
                    ready=root/'contention-ready.json'
                    if not ready.exists():
                        require(time.monotonic_ns()-load_started<45_000_000_000,'Contention readiness deadline')
                        return
                    require(json.loads(ready.read_text())['packet_sha256']==digest(root/'packet.json'),
                            'Contention readiness packet')
                if 'info' not in samples or 'health' not in samples:return
                info=fresh_sample(samples,lock,'info',2_000_000_000,
                    identity=observer_identity if packet.get('observer_policy')==SINGLE_FLIGHT else None,inflight=inflight)
                if state['done_at'] is not None:
                    if time.monotonic()-state['done_at']>=10:done.set()
                    return
                job=packet['jobs'][state['index']]
                if state['phase']=='idle':
                    require(status['state']=='empty' and status['owner_id'] is None and not status['output_active'],
                            'Next job idle admission')
                    if capture_failures and not recent_clock(info):return
                    require(time.monotonic()+int(job['total_duration_ns'])/1e9+40<end,'Remaining finite observation budget')
                    checkpoint()
                    state['epoch']=int(info['launch_epoch']);state['lease']=peer.request('CLAIM',dict(owner_id=packet['owner_id'],lease_ms=60000))
                    checkpoint();peer.request('LOAD',job);state['phase']='loaded'
                elif state['phase']=='loaded':
                    require(status['state']=='loaded' and status['job_id']==job['job_id'],'Loaded observation')
                    clock=peer.request('GET_CLOCK')
                    require(clock['state']=='synchronized' and clock['leap']=='normal' and int(clock['uncertainty_ns'])<=500_000_000,
                            'ARM synchronized clock')
                    if capture_failures:require(recent_clock(info,clock),'ARM recent accepted SNTP and matching clock mapping')
                    target=((int(clock['utc_now_ns'])+10_000_000_000+999)//1000)*1000
                    checkpoint()
                    result['armed_jobs'].append(job['job_id']);result['rf_duration_ns_charged']+=int(job['total_duration_ns'])
                    save(root/'rf-result.json',result);emit('arm_pending',dict(job=job,start_utc_ns=str(target)))
                    arm=peer.request('ARM',dict(job_id=job['job_id'],start_utc_ns=str(target),max_start_uncertainty_ns='500000000'))
                    require(arm['start_utc_ns']==str(target),'ARM changed start');emit('arm_acknowledged',arm)
                    state['phase']='executing'
                elif state['phase']=='executing':
                    require(status['job_id']==job['job_id'] and status['owner_id']==packet['owner_id'] and
                            status['state'] in ['armed','running','complete'],'Finite lifecycle')
                    if status['state']=='running' and 'wtp_capacity' in packet and not state.get('capacity_exchanged',False):
                        if capture_failures and not (info['status']['state']=='running' and info['status']['output_active'] is True):return
                        from phase11_5_r3_capacity_probe import exchange_capacity
                        from phase11_5_r3_capacity_plan import wtp_capacity_frame
                        from validate_wtp_contract import frame
                        if packet.get('closure_policy') in (REPAIR_POLICY,COMPLETION_POLICY):
                            published=root/'native-observation.json'
                            if not published.exists() or not native_running(json.loads(published.read_text()),packet,digest(root/'packet.json'),time.monotonic_ns()):return
                        cap=packet['wtp_capacity'];state['capacity_exchanged']=True
                        raw=wtp_capacity_frame(peer.session,cap['maximum_request_id'])
                        checkpoint()
                        observer_checkpoint=peer.checkpoint
                        if capture_failures:peer.checkpoint=checkpoint
                        try:observed=exchange_capacity(peer,raw,json.loads(raw[16:]),emit)
                        finally:peer.checkpoint=observer_checkpoint
                        require(observed['boot_id']==packet['boot_id'] and observed['job_id']==job['job_id'] and
                            observed['owner_id']==packet['owner_id'] and observed['state']=='running' and
                            observed['output_active'] is True,'Maximum WTP under owned Running RF')
                        if not diagnostic:
                            recovery=dict(type='request',protocol='WTP/1',session_id=peer.session,
                                request_id=cap['recovery_request_id'],op='PING',body={'token':'after-capacity'})
                            raw=wtp_capacity_frame(peer.session,cap['oversized_request_id'],True)+frame(json.dumps(recovery,separators=(',',':')).encode())
                            checkpoint();observer_checkpoint=peer.checkpoint
                            if capture_failures:peer.checkpoint=checkpoint
                            try:
                                require(exchange_capacity(peer,raw,recovery,emit,invalid_frames=1)==recovery['body'],
                                        'Same-connection oversized WTP recovery')
                            finally:peer.checkpoint=observer_checkpoint
                    if status['state']=='complete':
                        if info['status']['state']!='complete' or int(info['launch_epoch'])<=state['epoch']:return
                        emit('job_complete',dict(job_id=job['job_id'],status=status,info=info))
                        result['completed_jobs'].append(job['job_id']);save(root/'rf-result.json',result)
                        checkpoint();peer.request('RELEASE');state['phase']='released'
                    elif int(state['lease']['expires_monotonic_ns'])-int(info['status']['monotonic_now_ns'])<=20_000_000_000:
                        require(result['renewals']<packet['maximum_renewals'],'Renewal bound')
                        checkpoint()
                        state['lease']=peer.request('RENEW',dict(owner_id=packet['owner_id'],lease_ms=60000));result['renewals']+=1
                else:
                    require(status['state']=='empty' and status['owner_id'] is None and not status['output_active'],'Released authority')
                    state['index']+=1;state['phase']='idle'
                    if state['index']==len(packet['jobs']):state['done_at']=time.monotonic()
            periodic('status',5,read,act)
    def worker(name,fn):
        try:fn()
        except BaseException as error:
            faults.append(name+': '+str(error));emit('failure',dict(worker=name,error=str(error),type=type(error).__name__))
            # Keep independent readers alive to the original finite deadline.
    try:
        if packet.get('closure_policy')==COMPLETION_POLICY:
            from phase11_5_rf_reservation import Reservation
            reservation=Reservation(digest(root/'packet.json'))
        if comparator_required(packet):
            before_b=inventory('before-b',True);empty(before_b,True)
        before=inventory('before-a');empty(before);validate_info(before['info'],before,packet)
        caps=before['wtp']['CAPS'];require(caps['max_events']==512 and caps['max_job_duration_ns']=='3600000000000','Extended CAPS')
        if reservation is not None:
            require(len(before['wtp']['STATUS']['terminal_records'])<=packet['maximum_initial_terminal_records'],
                    'Initial retained state exceeds the frozen individual-capacity workload')
            reservation.acquire({'a':before,'b':before_b})
            save(root/'rf-reservation-acquired.json',json.loads(reservation.path.read_text()))
        clock=before['wtp']['GET_CLOCK'];require(clock['state']=='synchronized' and clock['leap']=='normal','Initial clock')
        emit('start',dict(packet_sha256=digest(root/'packet.json'),baseline_sha256=digest(root/'before-a.stdout'),
                         boot_id=packet['boot_id'],seconds=packet['runtime_seconds']))
        if 'contention' in packet:
            plan=packet['contention'];load_started=time.monotonic_ns()
            command=['nsenter','-t',str(plan['client_pid']),'-m','-n','python3',
                str(root/'scripts/phase11_5_r3_v2_nominal_load.py'),'--root',str(root),
                '--packet-sha256',digest(root/'packet.json'),'--run']
            emit('contention_starting',dict(argv=command))
            with (root/'contention.stdout').open('xb') as out,(root/'contention.stderr').open('xb') as err:
                load_process=subprocess.Popen(command,stdout=out,stderr=err)
        threads=[threading.Thread(target=worker,args=(name,fn)) for name,fn in [('console',console),('health',health),('wtp',wtp)]]
        for t in threads:t.start()
        for t in threads:t.join()
        if load_process is not None:
            save(root/'rf-observation-done.json',dict(packet_sha256=digest(root/'packet.json')))
            load_process.wait(timeout=25)
            require(load_process.returncode==0 and
                    json.loads((root/'contention-result.json').read_text())['status']=='CAPTURED_REQUIRES_AUDIT',
                    'Nominal contention completion')
        result['status']='CAPTURED_REQUIRES_AUDIT' if not faults and len(result['completed_jobs'])==len(packet['jobs']) else 'STOPPED_REQUIRES_DIAGNOSIS'
    except BaseException as error:faults.append('supervisor: '+str(error));result['status']='STOPPED_REQUIRES_DIAGNOSIS'
    finally:
        if load_process is not None and load_process.poll() is None:
            load_process.terminate()
            try:load_process.wait(timeout=25)
            except subprocess.TimeoutExpired:load_process.kill();load_process.wait(timeout=5)
        for label,b in ([('final-a',False),('final-b',True)] if comparator_required(packet) else [('final-a',False)]):
            try:
                v=inventory(label,b)
                final_values['b' if b else 'a']=v
                if capture_failures and not b:
                    diagnostic_identity(v['info'],packet)
                    require(v['wtp']['STATUS']['boot_id']==packet['boot_id'] and
                            v['wtp']['STATUS']['output_active'] is v['info']['status']['output_active'] is False and
                            v['wtp']['STATUS']['owner_id'] is None,'Diagnostic final inactive/unowned authority')
                    require(configuration(v)==configuration(before),'Diagnostic configuration changed')
                    result[label]=v['wtp']['STATUS']
                    continue
                empty(v,b)
                if b:require(before_b is not None and configuration(v)==configuration(before_b) and
                             v['info']['revision']==before_b['info']['revision'],'B configuration/source')
                else:require(before is not None and configuration(v)==configuration(before),'A configuration');validate_info(v['info'],before,packet)
                result[label]=v['wtp']['STATUS']
            except BaseException as error:result[label+'-error']=str(error);result['status']='STOPPED_FINAL_STATE_UNVERIFIED'
        if reservation is not None:
            try:
                if reservation.held:
                    reservation.release(final_values)
                    save(root/'rf-reservation-released.json',json.loads(reservation.path.read_text()))
            except BaseException as error:
                faults.append('RF reservation remains held: '+str(error))
                result['status']='STOPPED_FINAL_STATE_UNVERIFIED'
            finally:reservation.close()
        result['faults']=faults;emit('finish',result);save(root/'rf-result.json',result);log.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no device or host changes.');return
    root=a.root.resolve(strict=True);require(os.geteuid()==0 and digest(root/'packet.json')==a.packet_sha256,'Root/hash')
    packet=validate(json.loads((root/'packet.json').read_text()));require(packet['root']==str(root),'Packet root')
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==packet['host_boot_id'],'Host boot')
    if packet.get('closure_policy')==COMPLETION_POLICY:
        require(time.monotonic_ns()>=packet['not_before_host_monotonic_ns'], 'Individual-capacity preparation window not complete')
    timer=subprocess.check_output(['busctl','get-property','org.freedesktop.systemd1',
        '/org/freedesktop/systemd1/unit/phase115_2dclosure_2dcleanup_2etimer',
        'org.freedesktop.systemd1.Timer','NextElapseUSecMonotonic'],text=True,timeout=5).strip()
    require(timer=='t '+str(packet['fixture_deadline_monotonic_ns']//1000) and
            time.monotonic_ns()+(packet['runtime_seconds']+packet['restoration_seconds'])*10**9 <
            packet['fixture_deadline_monotonic_ns'],'Fixture observation/restoration reserve')
    for n,sha in packet['stage_sha256'].items():
        require((root/n).resolve().is_relative_to(root) and digest(root/n)==sha,'Staged input changed')
    with (root/'rf-result.json').open('x') as f:json.dump(dict(status='STARTING'),f)
    run(root,packet)

if __name__=='__main__':main()
