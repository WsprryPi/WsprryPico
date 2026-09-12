#!/usr/bin/env python3
"""Opt-in R1 only: inhibited regression and matched physical idle resource baseline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import struct
import sys
import time

from phase11_5_inventory import require
from phase11_5_device_fixture import DeviceFixture
from phase11_5_device_management import R1_SOURCE, digest
from phase11_5_network_fixture import Fixture
from audit_phase11_5_idle import audit as audit_idle
from audit_phase11_5_load import audit as audit_load

R1_HELPERS={'scripts/'+name+'.py' for name in ('phase11_5_r1','audit_phase11_5_r1',
    'phase11_5_a2_load','phase11_5_idle_observer','audit_phase11_5_idle','audit_phase11_5_load')}


def validate_fixture_dns(value):
    query=bytes.fromhex(value['query_hex']);reply=bytes.fromhex(value['reply_hex'])
    question=b'\x05clock\x08phase115\x04test\x00\x00\x01\x00\x01'
    require(len(query)==12+len(question) and query[2:]==struct.pack('!HHHHH',256,1,0,0,0)+question,
            'DNS admission query differs')
    require(len(reply)==len(query)+16 and reply[:2]==query[:2], 'DNS admission transaction/length')
    flags,qd,an,ns,ar=struct.unpack('!HHHHH',reply[2:12])
    require(flags&0x800f==0x8000 and (qd,an,ns,ar)==(1,1,0,0) and
            reply[12:len(query)]==question and reply[len(query):len(query)+6]==b'\xc0\x0c\x00\x01\x00\x01' and
            reply[-6:]==b'\x00\x04\x0a\x4d\x0f\x01' and
            value['local_address']=='10.77.15.2' and value['peer']==['10.77.15.1',53] and
            0<=value['elapsed_ns']<=3_000_000_000, 'DNS admission answer/address/deadline')


def fixture_dns(fixture, root):
    """One recorded native-client positive control before any board mutation; no retry."""
    program="""import socket,struct,secrets,time,json
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(3)
q=struct.pack('!HHHHHH',secrets.randbits(16),256,1,0,0,0)+b'\\x05clock\\x08phase115\\x04test\\x00\\x00\\x01\\x00\\x01'
s.connect(('10.77.15.1',53));start=time.monotonic_ns();s.send(q);data=s.recv(512)
print(json.dumps(dict(query_hex=q.hex(),reply_hex=data.hex(),peer=list(s.getpeername()),local_address=s.getsockname()[0],elapsed_ns=time.monotonic_ns()-start)))
"""
    response=fixture.in_client(['python3','-c',program])
    value=json.loads(response.stdout)
    with (root/'fixture-dns-admission.json').open('x') as stream:json.dump(value,stream,indent=2)
    validate_fixture_dns(value)


def resources(path):
    """Call only after raw audit. Costs overlap; report separately, never sum maxima."""
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    samples=[r for r in rows if r['kind']=='info'];infos=[r['value']['value'] for r in samples]
    statuses=[r['value']['value'] for r in rows if r['kind']=='status']
    require(statuses and all(s['terminal_records']==[] for s in statuses),
            'R1 requires independently observed empty terminal history')
    first,last=infos[0],infos[-1]
    seconds=(int(last['heap_sample_observed_us'])-int(first['heap_sample_observed_us']))/1e6
    cost=int(last['allocator_sample_time_us'])-int(first['allocator_sample_time_us'])
    require(seconds>0 and cost>=0, 'Resource clock/counter regression')
    maxima=('allocator_peak_bytes','allocator_largest_successful_request_bytes',
        'allocator_max_sample_us','allocator_max_entry_us','core0_stack_used_bytes',
        'core0_stack_scan_us','heap_sample_cost_us')
    result={key:max(int(i[key]) for i in infos) for key in maxima}
    if first['status']['engine']=='pio-dma-gp2':
        result.update({key:max(int(i[key]) for i in infos) for key in
            ('core1_stack_used_bytes','rf_max_probe_ns')})
    result.update(boot=first['status']['boot_id'],clock_hz=first['system_clock_hz'],
        heap_capacity_bytes=first['heap_capacity_bytes'],allocator_sample_delta_us=cost,
        sampled_interval_seconds=seconds,allocator_sampling_fraction=cost/(seconds*1e6),
        max_info_roundtrip_seconds=max((r['monotonic_ns']-r['value']['began_monotonic_ns'])/1e9 for r in samples),
        last={key:last[key] for key in ('heap_allocated_bytes','heap_arena_bytes',
            'heap_arena_free_bytes','heap_free_chunks','heap_top_releasable_bytes',
            'allocator_failures','tls_allocation_failures')},
        network=last['network'],terminal_records=statuses[-1]['terminal_records'])
    return result


def matched_quiet(before, after):
    require(before['boot']==after['boot'] and before['clock_hz']==after['clock_hz'] and
            before['terminal_records']==after['terminal_records']==[], 'Quiet identity/history differs')
    for key in ('ipv4','ntp_address','stable_hostname','mdns_state','control_listening'):
        require(before['network'][key]==after['network'][key], 'Quiet network state differs: '+key)
    for key in ('allocator_failures','tls_allocation_failures'):
        require(before['last'][key]==after['last'][key], 'Unexpected quiet allocation failure')
    delta=after['last']['heap_allocated_bytes']-before['last']['heap_allocated_bytes']
    require(abs(delta)<=1024, 'Unexplained matched quiet retained heap')
    return delta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--packet-sha256',required=True)
    p.add_argument('--run',action='store_true');args=p.parse_args()
    if not args.run:print('Plan only: R1; no host, device or network accessed.');return
    require(sys.platform=='linux' and os.geteuid()==0,'wspr5 root required')
    os.umask(0o077);root=args.root.resolve(strict=True)
    require(digest(root/'packet.json')==args.packet_sha256,'Frozen R1 packet changed')
    packet=json.loads((root/'packet.json').read_text())
    require(packet['family']=='R1' and packet['source_revision']==R1_SOURCE and packet['rf_jobs']==[] and
            packet['runtime_seconds'] in (2400,2700) and type(packet['network_runtime_seconds']) is int and 0 < packet['network_runtime_seconds'] <= 4200,
            'Frozen R1 scope/bounds')
    require(set(packet['case_helper_sha256'])==R1_HELPERS, 'Incomplete R1 helper identity set')
    for path,expected in packet['case_helper_sha256'].items():
        require((root/path).resolve().is_relative_to(root) and digest(root/path)==expected,'R1 helper changed')
    result_path=root/'r1-result.json';require(not result_path.exists(),'No R1 rerun')
    f=Fixture(Path(packet['network_root']))
    result=dict(family='R1',source=R1_SOURCE,status='RUNNING',intervals={},rf_jobs=[])
    def save():result_path.write_text(json.dumps(result,indent=2)+'\n')
    def run(label,argv,timeout):
        result['current_stage']=label;save()
        if (root/'device-state.json').exists() and label not in ('r1-device-restore','r1-host-cleanup'):
            state=json.loads((root/'device-state.json').read_text())
            require(time.monotonic_ns()+(timeout+180)*10**9 < state['deadline_monotonic_ns'],
                    'R1 interval would consume restoration reserve')
        with (root/(label+'.log')).open('x') as out:
            r=subprocess.run(argv,stdout=out,stderr=subprocess.STDOUT,timeout=timeout)
        require(r.returncode==0,label+' failed; stop dependent tests')
    def device(action):
        run('r1-device-'+action,['python3',str(root/'scripts/phase11_5_device_fixture.py'),action,
                                '--root',str(root),'--run'],180)
    def ready(kind):
        d=DeviceFixture(root)
        for index in range(13):
            current=d.check_current('r1-'+kind+'-ready-'+str(index))
            if current['wtp']['GET_CLOCK']['state']=='synchronized' and \
                current['info']['network']['ipv4']=='10.77.15.10' and \
                current['info']['network']['ntp_address']=='10.77.15.1':return d
            require(index<12,'R1 network/time readiness deadline');time.sleep(5)
    session=secrets.token_hex(16)
    def time_admission(label):
        if packet.get('time_server_mdns'):
            from phase11_5_time_local import fixture_admission
            require(packet.get('time_server_dns') is False and
                    packet.get('time_server_dns_name') == 'time.local' and
                    packet.get('time_server_address') == '10.77.15.1', 'R1 mDNS packet identity')
            fixture_admission(f, root, label)
        else:
            fixture_dns(f, root)
    def load(d,label,seconds,browser):
        kind=d.state['kind'];name='a2-'+kind+'-'+label
        case=dict(case=name,boot=d.state['boot'],source=R1_SOURCE,
            clock_hz=138000000 if kind=='physical' else 150000000,
            observer_session_id=session,observer_sha256=digest(root/'scripts/phase11_5_idle_observer.py'),
            intervals=[['nominal' if browser else 'controller',seconds]],rf_jobs=[],browser_profile='N')
        with (root/(name+'-packet.json')).open('x') as out:json.dump(case,out,indent=2)
        run(label,['python3',str(root/'scripts/phase11_5_a2_load.py'),'--root',str(root),
            '--kind',kind,'--attempt',label,'--seconds',str(seconds),*(['--browser'] if browser else []),
            '--workload-manifest',str(root/'workload.json'),'--run'],seconds+100)
        target=root/(name+('-nominal' if browser else '-controller'))
        usb=audit_idle(target/'usb-health.jsonl',root/(target.name+'-admission.stdout'))
        value=dict(usb=usb,load=audit_load(target,root/'pi/phase115_tls_observer_test.py'),
                   resources=resources(target/'usb-health.jsonl'))
        result['intervals'][label]=value;save();return value
    def quiet(d,label):
        baseline=label+'-admission';d.check_current(baseline)
        path=root/(label+'.jsonl')
        run(label,['python3',str(root/'scripts/phase11_5_idle_observer.py'),'--baseline',str(root/(baseline+'.stdout')),
            '--output',str(path),'--session-id',session,'--seconds','360','--run'],375)
        value=dict(usb=audit_idle(path,root/(baseline+'.stdout')),resources=resources(path))
        result['intervals'][label]=value;save();return value
    try:
        if packet.get('time_server_mdns'):
            DeviceFixture(root).verify_helpers()
            for path, expected in packet['production_helper_sha256'].items():
                require(digest(root/path) == expected, 'Production helper changed before fixture')
            for path_key, hash_key in (('production_binary','production_binary_sha256'),
                    ('production_observer','production_observer_sha256')):
                require(digest(Path(packet[path_key])) == packet[hash_key], 'Production artifact changed')
            require(digest(root/'production.ini') == packet['production_ini_sha256'], 'Production INI changed')
            require(packet['network_root'] == str(root), 'Fresh R1 mDNS fixture must share the new root')
            run('r1-host-setup', ['python3', str(root/'scripts/phase11_5_network_fixture.py'),
                'setup', '--root', str(root), '--run'], 330)
            f = Fixture(root)
        f.verify()
        result['current_stage']='fixture-time-admission';save();time_admission('fixture-time-inhibited')
        device('start');d=ready('inhibited');load(d,'r1-inhibited',180,True)
        if packet.get('time_server_mdns'): time_admission('fixture-time-physical')
        device('switch');d=ready('physical');warm=load(d,'r1-warm',180,True)
        current=d.check_current('r1-before-probes');initial=int(current['info']['allocator_failures'])
        needed=max(warm['resources']['allocator_largest_successful_request_bytes'],
                   current['info']['allocator_largest_successful_request_bytes'])
        require(initial==0 and needed>0,'Unexpected pre-probe failure or missing necessary allocation')
        result['probes']=[]
        d.management_baseline()
        for index,(size,expected) in enumerate(((needed,True),(current['info']['heap_capacity_bytes']+1,False),(needed,True))):
            run('r1-probe-'+str(index),['python3',str(root/'scripts/phase11_5_device_management.py'),'heap-probe',
                '--root',str(root),'--baseline',str(root/d.state['baseline']),'--bytes',str(size),'--run'],90)
            management=json.loads((root/'management-state.json').read_text())
            require(management['last_result']['reply']['allocated'] is expected,'Unexpected probe outcome')
            result['probes'].append(dict(bytes=size,allocated=expected,
                management_result=management['last_result']));save()
        current=d.check_current('r1-after-probes')
        require(int(current['info']['allocator_failures'])==initial+1 and
                current['info']['tls_allocation_failures']==0,'Unexpected probe failure count')
        before=quiet(d,'r1-quiet-before')
        load(d,'r1-controller',180,False)
        normal=load(d,'r1-normal',300,True)
        after=quiet(d,'r1-quiet-after')
        require(normal['resources']['allocator_largest_successful_request_bytes']<=needed,
                'Normal workload needs an allocation larger than the successful probe')
        result['quiet_delta_bytes']=matched_quiet(before['resources'],after['resources'])
        result['status']='CAPTURED_REQUIRES_FINAL_REVIEW'
    except BaseException as error:
        result['status']='FAILED';result['error']=type(error).__name__+': '+str(error);result['failed_stage']=result.get('current_stage')
    finally:
        if (root/'device-state.json').exists():
            try:device('restore');result['device_restored']=True
            except BaseException as error:result['restore_error']=type(error).__name__+': '+str(error)
        if packet.get('time_server_mdns') and (root/'fixture-state.json').exists():
            try:
                run('r1-host-cleanup', ['python3', str(root/'scripts/phase11_5_network_fixture.py'),
                    'cleanup', '--root', str(root), '--run'], 600)
                shutil.copyfile(root/'fixture-state.json', root/'host-fixture-state.json')
                result['host_restored'] = True
            except BaseException as error:
                result['host_restore_error'] = type(error).__name__+': '+str(error)
        save()
    require(result['status']=='CAPTURED_REQUIRES_FINAL_REVIEW' and result.get('device_restored') and
            (not packet.get('time_server_mdns') or result.get('host_restored')),
            'R1 incomplete; preserve evidence')


if __name__=='__main__':main()
