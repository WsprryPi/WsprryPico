#!/usr/bin/env python3
"""Opt-in finite real-Chromium supervisor with independent USB/host observations."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from phase11_5_inventory import require,exclusive_port,exchange
from phase11_5_pilot import Peer,SERIAL,DEVICE
from phase11_5_pilot_supervisor import finished,configuration,B_SERIAL,B_DEVICE
from phase11_5_device_management import digest,save
from phase11_5_r3_v2_rf import validate_info,comparator_required,REPAIRED_SOURCE,REPAIRED_IMAGE,PAGED_SOURCE,PAGED_IMAGE,INFO_SOURCE,INFO_IMAGE,ASSET_SOURCE,ASSET_IMAGE
from phase11_5_r3_v2_observer_policy import STRICT,SINGLE_FLIGHT,next_offer

SCHEMA='phase11.5-r3-v2-chromium-v1'


def validate(packet):
    require(packet['schema']==packet['r3_scope']==SCHEMA and packet['standing_authority']=='R3-COMPLETE-20260913-v2',
            'Browser scope/authority')
    comparator_required(packet)
    require(packet.get('observer_policy',STRICT) in (STRICT,SINGLE_FLIGHT),'Unknown observer policy')
    require((packet['source_revision'],packet['image_sha256']) in [
                ('7d183978d08d77d5de668911be041bb188c851f5',
                 '38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1'),
                (REPAIRED_SOURCE,REPAIRED_IMAGE),(PAGED_SOURCE,PAGED_IMAGE),(INFO_SOURCE,INFO_IMAGE),(ASSET_SOURCE,ASSET_IMAGE)] and
            packet['serial']==SERIAL and packet['device_id']==DEVICE,'Browser physical identity')
    require(packet['runtime_seconds']==900 and packet['restoration_seconds']==150 and
            packet['configuration_writes']==packet['wifi_cycles']==packet['heap_probes']==packet['flashes']==0,
            'Browser finite scope/no management changes')
    cases=packet['cases']
    require(len(cases)==4 and [c['kind'] for c in cases]==['file-complete','message-complete','armed-abort','running-abort'] and
            [int(c['duration_ns']) for c in cases]==[10000000000,143250001000,143250001000,155750001000] and
            sum(int(c['duration_ns']) for c in cases)<=600000000000,'Frozen browser job budget')
    indices=packet.get('case_indices',[0,1,2,3])
    require(indices in ([0,1,2,3],[1,2,3],[2,3],[3]), 'Reviewed remaining browser cases')
    if indices in ([1,2,3],[2,3],[3]):
        require(packet['source_revision'] in (INFO_SOURCE,ASSET_SOURCE) and packet.get('reused_browser_audit_sha256')==
            '7ddd6632414f01a230e149630ef81e4978bae8579cab1689e32c47f105a94b65', 'Preserved B3 component evidence')
    if indices==[2,3]:
        require(packet.get('reused_completed_fskcw_audit_sha256')==
            'bc0f02e259df7d146b5d2d624866461fede040e473fa9a8138592f019b0277de' and
            packet.get('between_case_quiet_seconds')==360, 'Preserved FSKCW and actual replay quiet interval')
    else:
        require(packet.get('between_case_quiet_seconds',0)==0, 'Unexpected quiet interval')
    if indices==[3]:
        require(packet.get('reused_completed_fskcw_audit_sha256')==
            'bc0f02e259df7d146b5d2d624866461fede040e473fa9a8138592f019b0277de' and
            packet.get('reused_armed_cancel_audit_sha256')==
            'a08bdeb570d273b216b5193e96f27d9f3abdb97eebe7e5164b684cbd0cb3983e', 'Preserved completed and Armed-cancel components')
    require(packet['maximum_jobs']==len(indices) and packet['maximum_request_count']==250 and
            packet['running_abort_after_ns']==120000000000,'Producer request/abort bounds')
    job=cases[0]['job']
    require(job['profile']=='rf-events/1' and job['mode']=='tone' and job['allow_frequency_adjustment'] is True and
            job['total_duration_ns']=='10000000000' and job['events']==[
                dict(offset_ns='0',duration_ns='10000000000',rf_on=True,frequency_nhz='135500000000000')],
            'Exact finite browser file job')
    for case,mode,dot in zip(cases[1:],['fskcw','qrss','dfcw'],[250000000,250000000,350000000]):
        require(case['message']==dict(mode=mode,message='?'*32,frequency_nhz='135500000000000',
            space_frequency_nhz='0' if mode=='qrss' else '135495000000000',
            timing=dict(dot_ns=str(dot),dash_ns=str(dot*3),intra_gap_ns=str(dot),
                character_gap_ns=str(dot*3),word_gap_ns=str(dot*7)),repeat_count=1,repeat_gap_ns='1000000000',
            allow_frequency_adjustment=True),'Exact finite browser message/frequencies')
        require(case['dot_seconds']==('0.35' if mode=='dfcw' else '0.25'),'UI timing input')
    return packet


def zero_rf_stop_admitted(result,requests,info,status,boot):
    return (result.get('status')=='FAILED' and result.get('rf_jobs_charged')==0 and
        result.get('rf_duration_ns_charged')=='0' and result.get('cases')==[] and
        all(r.get('method')=='GET' for r in requests) and
        info.get('status',{}).get('boot_id')==status.get('boot_id')==boot and
        info.get('status',{}).get('state')==status.get('state')=='empty' and
        info.get('status',{}).get('output_active') is status.get('output_active') is False and
        status.get('owner_id') is status.get('job_id') is None)


def run(root,packet):
    end=time.monotonic()+packet['runtime_seconds'];done=threading.Event();lock=threading.Lock();seq=0
    faults=[];samples={};child=None;baseline={};result=dict(status='RUNNING')
    log=(root/'browser-observer.jsonl').open('x')
    def emit(kind,value):
        nonlocal seq
        entered=time.monotonic_ns()
        with lock:
            row=dict(sequence=seq,kind=kind,value=value,monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns());seq+=1
            if packet.get('observer_policy')==SINGLE_FLIGHT:
                row['event_observed_monotonic_ns']=entered
                row['journal_lock_wait_ns']=row['monotonic_ns']-entered
            log.write(json.dumps(row)+'\n');log.flush();os.fsync(log.fileno())
            if kind in ['info','status','health']:
                samples[kind]=row
                save(root/('observer-'+kind+'.json'),dict(row,packet_sha256=digest(root/'packet.json')))
    def fail(name,error):
        faults.append(name+': '+str(error));emit('failure',dict(worker=name,error=str(error),type=type(error).__name__))
        save(root/'observer-failed.json',dict(faults=faults))
    def inventory(label,b=False):
        require(not b or comparator_required(packet),'Independent B endpoint is not owned by A')
        with (root/(label+'.stdout')).open('xb') as out,(root/(label+'.stderr')).open('xb') as err:
            code=subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),'--serial',B_SERIAL if b else SERIAL,
                '--device-id',B_DEVICE if b else DEVICE,'--session-id',packet['b_session'] if b else packet['inventory_session'],
                '--run'],stdout=out,stderr=err,timeout=65).returncode
        require(code==0,'Inventory '+label)
        return finished(root/(label+'.stdout'),'READ_ONLY_INVENTORY')
    def inactive(v,b=False):
        s=v['wtp']['STATUS'];i=v['info']
        require(s['boot_id']==(packet['b_boot_id'] if b else packet['boot_id']) and
                s['state'] in ['empty','complete','aborted'] and s['output_active'] is i['status']['output_active'] is False and
                s['owner_id'] is None and i['status']['enabled'] is False,'Inactive/unowned boundary')
    def periodic(name,period,read):
        next_at=time.monotonic();last=None;count=0
        single=name=='info' and packet.get('observer_policy')==SINGLE_FLIGHT
        while time.monotonic()<end and not done.is_set():
            now=time.monotonic();require(now-next_at<=1 and (single or last is None or now-last<=period+1),name+' cadence')
            value=read();require(time.monotonic()-now<=5,name+' reply deadline')
            emit(name,dict(began_monotonic_ns=int(now*1e9),value=value));last=now;count+=1
            published=time.monotonic()
            require(published-now<=5,name+' publication deadline')
            if single:next_at=next_offer(now,published,period)
            else:next_at+=period
            done.wait(max(0,min(next_at,end)-time.monotonic()))
        emit(name+'_finish',dict(samples=count))
    def console():
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
            def read():
                value=exchange(fd,b'INFO\n',time.monotonic()+5,lambda k,v:emit('console_'+k,v),False)
                validate_info(value,baseline['a'],packet);return value
            periodic('info',1,read)
    def status():
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
            peer=Peer(fd,emit,lambda:require(time.monotonic()<end,'Finite observer deadline'),packet['boot_id'])
            peer.session=packet['peer_session']
            hello=peer.request('HELLO',dict(versions=['WTP/1'],client_name='R3-v2-browser-observer',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==packet['boot_id'],'Observer HELLO identity')
            def read():
                s=peer.request('STATUS');require(s['boot_id']==packet['boot_id'] and
                    s['state'] in ['empty','loaded','armed','running','complete','aborted'] and
                    s['output_active'] is (s['state']=='running'),'Browser observer authority')
                binding=root/'browser-binding.json'
                if binding.exists():
                    b=json.loads(binding.read_text());require(b['packet_sha256']==digest(root/'packet.json') and
                        s['owner_id'] in [None,b['session']] and
                        s['job_id'] in [None,*b['job_ids'],baseline['a']['wtp']['STATUS']['job_id']],
                        'Foreign browser job/owner')
                else:require(s['owner_id'] is None and not s['output_active'],'Unexpected pre-browser authority')
                return s
            periodic('status',5,read)
    def health():
        def read():
            b=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            t=subprocess.check_output(['vcgencmd','get_throttled'],text=True,timeout=2).strip()
            require(b==packet['host_boot_id'] and t=='throttled=0x0','Host health')
            return dict(boot=b,throttled=t,temperature=Path('/sys/class/thermal/thermal_zone0/temp').read_text().strip())
        periodic('health',5,read)
    def worker(name,fn):
        try:fn()
        except BaseException as error:fail(name,error)
    threads=[]
    try:
        if comparator_required(packet):
            baseline['b']=inventory('before-b',True);inactive(baseline['b'],True)
        baseline['a']=inventory('before-a');inactive(baseline['a']);validate_info(baseline['a']['info'],baseline['a'],packet)
        require(baseline['a']['wtp']['STATUS']['state']=='empty','Browser starts Empty')
        emit('start',dict(packet_sha256=digest(root/'packet.json'),baseline_sha256=digest(root/'before-a.stdout'),boot_id=packet['boot_id']))
        for name,fn in [('info',console),('status',status),('health',health)]:
            t=threading.Thread(target=worker,args=(name,fn));threads.append(t);t.start()
        deadline=time.monotonic()+8
        while len(samples)<3:
            require(not faults and time.monotonic()<deadline,'Independent observer readiness');time.sleep(.05)
        command=['nsenter','-t',str(packet['client_pid']),'-m','-n','bwrap','--ro-bind','/','/',
            '--bind',str(root),str(root),'--bind',str(root/'browser-home'),'/root','--setenv','HOME','/root',
            '--ro-bind',str(root/'chromium-etc'),'/etc/chromium','--tmpfs','/tmp','--dev','/dev','--proc','/proc',
            '--unshare-pid','--die-with-parent','node',str(root/'scripts/phase11_5_r3_v2_browser.js'),
            '--root',str(root),'--packet-sha256',digest(root/'packet.json'),'--run']
        emit('browser_starting',dict(argv=command))
        with (root/'browser.stdout').open('xb') as out,(root/'browser.stderr').open('xb') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err)
        while time.monotonic()<end:
            if child.poll() is not None:
                require(child.returncode==0 and not faults,'Browser process/observation failure')
                r=json.loads((root/'browser-result.json').read_text())
                require(r['status']=='CAPTURED_REQUIRES_AUDIT','Browser result failed')
                # One observer period after the producer exits, preserving terminal evidence.
                time.sleep(6);done.set();break
            if faults:
                raise ValueError('Browser stopped after independent observer failure')
            time.sleep(.1)
        if child.poll() is None:raise ValueError('Browser did not finish within finite runtime')
        result['status']='CAPTURED_REQUIRES_AUDIT'
    except BaseException as error:
        fail('supervisor',error);result['status']='STOPPED_REQUIRES_DIAGNOSIS'
        save(root/'browser-observer-result.json',dict(result,faults=faults,
            observation_state='Remaining readers continue to the original deadline'))
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
        # A verified GET-only setup failure has no pending job lifecycle to observe.
        # Otherwise preserve the original deadline and all independent readers.
        if faults and child is not None and child.poll() is not None:
            try:
                r=json.loads((root/'browser-result.json').read_text())
                trace=[json.loads(line) for line in (root/'browser.jsonl').read_text().splitlines()]
                requests=[row['value']['request'] for row in trace if row['kind'] in ('network_request','request_guard')]
                with lock:
                    now=time.monotonic_ns();i=samples['info'];s=samples['status']
                    fresh=0<=now-i['monotonic_ns']<=2_000_000_000 and 0<=now-s['monotonic_ns']<=6_000_000_000
                    safe=fresh and zero_rf_stop_admitted(r,requests,i['value']['value'],s['value']['value'],packet['boot_id'])
                if safe:
                    emit('zero_rf_failure_observation_complete',dict(reason='GET-only producer failure; fresh Empty/inactive/unowned authority'))
                    done.set()
            except (OSError,ValueError,KeyError,TypeError):pass
        for t in threads:t.join()
        for label,b in ([('final-a',False),('final-b',True)] if comparator_required(packet) else [('final-a',False)]):
            try:
                v=inventory(label,b);inactive(v,b);old=baseline['b' if b else 'a']
                require(configuration(v)==configuration(old) and v['info']['revision']==old['info']['revision'],'Preserved configuration/source')
                if not b:validate_info(v['info'],old,packet)
                result[label]=v['wtp']['STATUS']
            except BaseException as error:result[label+'-error']=str(error);result['status']='STOPPED_FINAL_STATE_UNVERIFIED'
        result['faults']=faults;emit('finish',result);save(root/'browser-observer-result.json',result);log.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no browser, USB or network activity.');return
    root=a.root.resolve(strict=True);require(os.geteuid()==0 and digest(root/'packet.json')==a.packet_sha256,'Root/packet')
    packet=validate(json.loads((root/'packet.json').read_text()));require(packet['root']==str(root),'Packet root')
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==packet['host_boot_id'],'Host boot')
    timer=subprocess.check_output(['busctl','get-property','org.freedesktop.systemd1',
        '/org/freedesktop/systemd1/unit/phase115_2dclosure_2dcleanup_2etimer','org.freedesktop.systemd1.Timer',
        'NextElapseUSecMonotonic'],text=True,timeout=5).strip()
    require(timer=='t '+str(packet['fixture_deadline_monotonic_ns']//1000) and
        time.monotonic_ns()+(packet['runtime_seconds']+packet['restoration_seconds'])*10**9<packet['fixture_deadline_monotonic_ns'],
        'Fixture deadline and restoration reserve')
    for name,sha in packet['stage_sha256'].items():require(digest(root/name)==sha,'Staged input changed')
    for name,spec in packet['remote_copy_inputs'].items():require(digest(root/name)==spec['sha256'],'Private input changed')
    with (root/'browser-observer-result.json').open('x') as f:json.dump(dict(status='STARTING'),f)
    run(root,packet)

if __name__=='__main__':main()
