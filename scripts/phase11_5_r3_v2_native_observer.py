#!/usr/bin/env python3
"""Opt-in finite native submission supervisor with independent USB/host authority."""
import argparse,json,os,subprocess,threading,time
from pathlib import Path
from phase11_5_inventory import require,exclusive_port,exchange
from phase11_5_pilot import Peer,SERIAL,DEVICE
from phase11_5_pilot_supervisor import finished,configuration,B_SERIAL,B_DEVICE
from phase11_5_device_management import digest,save
from phase11_5_r3_v2_rf import validate_info,comparator_required,ASSET_SOURCE,ASSET_IMAGE
from phase11_5_r3_v2_native_plan import validate_template,validate_initial,PI_SOURCE,PI_BINARY
from phase11_5_r3_v2_native_plan import DURATIONS
from phase11_5_r3_v2_observer_policy import SINGLE_FLIGHT,next_offer
SCHEMA='phase11.5-r3-v2-native-v1'

def validate(packet):
    require(packet['schema']==packet['r3_scope']==SCHEMA and packet['standing_authority']=='R3-COMPLETE-20260913-v2','Native authority/scope')
    require((packet['source_revision'],packet['image_sha256'])==(ASSET_SOURCE,ASSET_IMAGE) and
        packet['serial']==SERIAL and packet['device_id']==DEVICE and not comparator_required(packet),'Native A identity/B scope')
    require(packet['runtime_seconds']==600 and packet['restoration_seconds']==150 and packet['maximum_jobs']==1 and
        packet['configuration_writes']==packet['wifi_cycles']==packet['heap_probes']==packet['flashes']==0,'Native finite scope')
    require(packet.get('observer_policy')==SINGLE_FLIGHT and packet.get('timing_mapping_policy')==
        'acknowledged-monotonic-launch-v1','Prospective native observation/mapping policy')
    n=packet['native'];require(n['source_revision']==PI_SOURCE and n['binary_sha256']==PI_BINARY and
        type(n.get('transport_loss',False)) is bool and
        (not n.get('transport_loss',False) or n['mode']=='dfcw'),'Native identified finite path')
    require(n.get('loss_mechanism','ss-destroy-v1') in ['ss-destroy-v1','pidfd-duplicate-shutdown-v1'] and
        ('loss_mechanism' not in n or n.get('transport_loss') is True),'Native reviewed loss mechanism')
    validate_template(n['job_template'],n['mode'],n.get('template_policy','direct-compiler-v1'))
    require(n.get('duration_charge_ns',n['job_template']['total_duration_ns'])==str(DURATIONS[n['mode']]),
        'Conservative native duration charge')
    if n.get('template_policy')=='production-config-builder-v1':
        require(packet.get('sample_mapping_policy')=='waveform-absolute-nearest-v1','Native absolute sample policy')
    return packet

def run(root,packet):
    end=time.monotonic()+packet['runtime_seconds'];done=threading.Event();lock=threading.Lock();seq=0
    faults=[];samples={};child=None;baseline={};result=dict(status='RUNNING')
    log=(root/'native-observer.jsonl').open('x')
    def emit(kind,value):
        nonlocal seq
        with lock:
            row=dict(sequence=seq,kind=kind,value=value,monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns());seq+=1
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
            hello=peer.request('HELLO',dict(versions=['WTP/1'],client_name='R3-v2-native-observer',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==packet['boot_id'],'Observer HELLO identity')
            def read():
                s=peer.request('STATUS');require(s['boot_id']==packet['boot_id'] and
                    s['state'] in ['empty','loaded','armed','running','complete','aborted'] and
                    s['output_active'] is (s['state']=='running'),'Native observer authority')
                binding=root/'native-binding.json'
                if binding.exists():
                    b=json.loads(binding.read_text());require(b['packet_sha256']==digest(root/'packet.json') and
                        s['owner_id'] in [None,b['owner_id']] and
                        s['job_id'] in [None,b['job_id'],baseline['a']['wtp']['STATUS']['job_id']],
                        'Foreign native job/owner')
                else:require(s['owner_id'] is None and not s['output_active'],'Unexpected pre-native authority')
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
        validate_initial(baseline['a']['wtp']['STATUS'],packet)
        emit('start',dict(packet_sha256=digest(root/'packet.json'),baseline_sha256=digest(root/'before-a.stdout'),boot_id=packet['boot_id']))
        for name,fn in [('info',console),('status',status),('health',health)]:
            t=threading.Thread(target=worker,args=(name,fn));threads.append(t);t.start()
        deadline=time.monotonic()+8
        while len(samples)<3:
            require(not faults and time.monotonic()<deadline,'Independent observer readiness');time.sleep(.05)
        command=['nsenter','-t',str(packet['client_pid']),'-m','-n','python3',
            str(root/'scripts/phase11_5_r3_v2_native_producer.py'),'--root',str(root),
            '--packet-sha256',digest(root/'packet.json'),'--run']
        emit('native_starting',dict(argv=command))
        with (root/'native.stdout').open('xb') as out,(root/'native.stderr').open('xb') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err)
        while time.monotonic()<end:
            if child.poll() is not None:
                require(child.returncode==0 and not faults,'Native process/observation failure')
                r=json.loads((root/'native-result.json').read_text())
                require(r['status']=='CAPTURED_REQUIRES_AUDIT','Native result failed')
                # One observer period after the producer exits, preserving terminal evidence.
                time.sleep(6);done.set();break
            if faults:
                raise ValueError('Native stopped after independent observer failure')
            time.sleep(.1)
        if child.poll() is None:raise ValueError('Native did not finish within finite runtime')
        result['status']='CAPTURED_REQUIRES_AUDIT'
    except BaseException as error:
        fail('supervisor',error);result['status']='STOPPED_REQUIRES_DIAGNOSIS'
        save(root/'native-observer-result.json',dict(result,faults=faults,
            observation_state='Remaining readers continue to the original deadline'))
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
        for t in threads:t.join()
        for label,b in ([('final-a',False),('final-b',True)] if comparator_required(packet) else [('final-a',False)]):
            try:
                v=inventory(label,b);inactive(v,b);old=baseline['b' if b else 'a']
                require(configuration(v)==configuration(old) and v['info']['revision']==old['info']['revision'],'Preserved configuration/source')
                if not b:validate_info(v['info'],old,packet)
                result[label]=v['wtp']['STATUS']
            except BaseException as error:result[label+'-error']=str(error);result['status']='STOPPED_FINAL_STATE_UNVERIFIED'
        result['faults']=faults;emit('finish',result);save(root/'native-observer-result.json',result);log.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no native, USB or network activity.');return
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
    with (root/'native-observer-result.json').open('x') as f:json.dump(dict(status='STARTING'),f)
    run(root,packet)

if __name__=='__main__':main()
