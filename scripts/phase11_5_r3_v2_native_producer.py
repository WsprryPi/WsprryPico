#!/usr/bin/env python3
"""Opt-in one-job actual Pi producer; independent USB supervisor must already run.

This driver does not own USB. Charge before starting the real executable, bind
its first generated job while Waiting, and finish only on independent terminal
history. It is not a simulated WTP submission and does not install the binary.
"""
import argparse,configparser,hashlib,json,os,signal,subprocess,sys,time,urllib.request
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest,save
from phase11_5_r3_v2_native_plan import render_ini,validate_ini,validate_binding,validate_template,validate_initial,validate_host_scope,PI_SOURCE,PI_BINARY


def validate_exit(returncode,loss,reconciled):
    # scheduling_runtime.cpp latches transmission failure until wspr_loop exits.
    # Explicit WtpApplication::recover restores authority, not that history bit.
    require(type(loss) is bool and type(reconciled) is bool and
        reconciled is loss and returncode==(1 if loss else 0),
        'Native orderly exit failed')


def run(root,packet):
    mode=packet['native']['mode'];plan=packet['native'];packet_sha=digest(root/'packet.json')
    require(packet['standing_authority']=='R3-COMPLETE-20260913-v2' and packet['schema']=='phase11.5-r3-v2-native-v1' and
        packet['runtime_seconds']==600 and packet['restoration_seconds']==150 and packet['maximum_jobs']==1 and
        packet['configuration_writes']==packet['wifi_cycles']==packet['heap_probes']==packet['flashes']==0,'Native finite scope')
    require(plan['source_revision']==PI_SOURCE and plan['binary_sha256']==PI_BINARY and
        digest(Path(plan['binary']))==PI_BINARY and digest(Path(plan['observer']))==plan['observer_sha256'] and
        digest(root/'production-base.ini')==plan['base_ini_sha256'],'Actual native binary/input identity')
    require(os.readlink('/proc/self/ns/net')==plan['netns'] and os.readlink('/proc/self/ns/mnt')==plan['mountns'],'Native namespaces')
    loss=plan.get('transport_loss',False)
    require(type(loss) is bool and (not loss or mode=='dfcw'),'Native loss only on reviewed DFCW path')
    job=validate_template(plan['job_template'],mode,plan.get('template_policy','direct-compiler-v1'))
    # Validate routing, ports, GPIO and calibration before deriving the one-job
    # settings. Comparing a derivation with itself cannot validate its base.
    for name in ['phase115_production_load.py','phase115_tls_observer_test.py']:
        require(digest(root/'pi'/name)==packet['stage_sha256']['pi/'+name],
            'Reviewed native base-policy dependency')
    sys.path.insert(0,str(root/'pi'))
    from phase115_production_load import validate_ini as validate_inactive_base
    validate_inactive_base(root/'production-base.ini',False)
    baseline=(root/'production-base.ini').read_text()
    require(not (root/'native-result.json').exists(),'No native producer replay')
    end=time.monotonic()+packet['runtime_seconds'];sequence=0;process=None;binding=None
    result=dict(status='STARTING',rf_jobs_charged=0,rf_duration_ns_charged=0)
    stopping=[False]
    signal.signal(signal.SIGTERM,lambda *_:stopping.__setitem__(0,True))
    signal.signal(signal.SIGINT,lambda *_:stopping.__setitem__(0,True))
    log=(root/'native.jsonl').open('x');opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def emit(kind,value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence,kind=kind,value=value,monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns()))+'\n');log.flush();os.fsync(log.fileno());sequence+=1
    def check():
        require(not stopping[0] and time.monotonic()<end and not (root/'observer-failed.json').exists(),'Native finite deadline/observer guard')
    def sample(name,age,wait=True):
        deadline=time.monotonic()+7
        while True:
            check();s=json.loads((root/('observer-'+name+'.json')).read_text())
            elapsed=time.monotonic_ns()-s['monotonic_ns']
            require(s['packet_sha256']==packet_sha and elapsed>=0,'Native independent identity/time '+name)
            if elapsed<=age:return s['value']['value']
            if not wait:return None
            require(time.monotonic()<deadline,'Native fresh publication deadline '+name)
            time.sleep(.05)
    def host_status():
        began=time.monotonic_ns()
        with opener.open('http://127.0.0.1:31425/api/v1/status',timeout=3) as response:
            raw=response.read(131073);require(response.status==200 and len(raw)<=131072,'Native host API bounds')
        value=json.loads(raw);emit('native_status',dict(began_monotonic_ns=began,body_hex=raw.hex(),value=value));return value['host']
    emit('start',dict(packet_sha256=packet_sha,mode=mode,binary_sha256=PI_BINARY))
    try:
        s=sample('status',6_000_000_000);i=sample('info',2_000_000_000)
        validate_initial(s,packet)
        require(s['boot_id']==i['status']['boot_id']==packet['boot_id'] and s['state']==i['status']['state'] and
            s['owner_id'] is None and s['output_active'] is i['status']['output_active'] is False and
            i['status']['clock_state']=='synchronized','Native initial authority/clock')
        start=(time.time_ns()//10**9+90)*10**9
        text=render_ini(baseline,mode,start,root);validate_ini(text,baseline,mode,start,root)
        ini=root/'production-job.ini'
        with ini.open('x') as f:f.write(text);f.flush();os.fsync(f.fileno())
        # Charge conservatively before the executable could issue an ARM. No
        # second application instance or schedule is admitted in this packet.
        result.update(status='CHARGED_BEFORE_PROCESS_START',rf_jobs_charged=1,
            rf_duration_ns_charged=int(plan.get('duration_charge_ns',job['total_duration_ns'])))
        save(root/'native-result.json',result)
        execution=dict(start_utc_ns=start,ini_sha256=digest(ini),job_template=job)
        save(root/'native-execution.json',execution);emit('job_charge',dict(execution,rf_jobs=1))
        command=[plan['binary'],'--backend','wtp','-i',str(ini),'--socket-loopback-only','--socket-loopback-family','ipv4','--allow-unqualified-frequency','--allow-non-amateur-frequency']
        emit('process_starting',dict(argv=command))
        check()
        with (root/'production.log').open('xb') as output:
            process=subprocess.Popen(command,cwd=root,stdout=output,stderr=subprocess.STDOUT,
                env=dict(os.environ,TZ='UTC',LD_PRELOAD=plan['observer'],PHASE115_TLS_LOG=str(root/'production-tls.bin')))
        emit('process_started',dict(pid=process.pid,binary_sha256=digest(Path('/proc')/str(process.pid)/'exe')))
        ready_until=time.monotonic()+40
        while time.monotonic()<ready_until:
            check();require(process.poll() is None,'Native exited before binding')
            try:h=host_status()
            except OSError:time.sleep(.2);continue
            if h.get('phase')=='waiting':
                binding=validate_binding(h,packet,start,time.time_ns());break
            require(h.get('phase') in ['idle','connecting','preparing',None],'Native unexpected pre-binding state')
            time.sleep(.1)
        require(binding is not None,'Native did not bind before dispatch')
        save(root/'native-binding.json',dict(packet_sha256=packet_sha,**binding));emit('binding',binding)
        next_status=time.monotonic();completed=None;own_seen=False;dropped=None;host_completed=False
        while completed is None:
            check();require(process.poll() is None,'Native exited before independently confirmed completion')
            s=sample('status',6_000_000_000,False);i=sample('info',2_000_000_000,False)
            if s is not None and i is not None:
                require(s['owner_id'] in [None,binding['owner_id']] and s['job_id'] in
                    [None,binding['job_id'],*([plan['initial_authority']['job_id']] if not own_seen else [])],
                    'Native owner/job changed')
                own_seen=own_seen or s['job_id']==binding['job_id']
                records=[r for r in s['terminal_records'] if r['job_id']==binding['job_id']]
                if records:
                    require(len(records)==1 and records[0]['state']=='complete' and records[0]['output_active'] is False and
                        'error' not in records[0] and s['output_active'] is False,'Native failed or uncertain terminal')
                    completed=records[0];emit('independent_terminal',dict(status=s,record=completed));break
            if time.monotonic()>=next_status:
                h=host_status();host_completed=validate_host_scope(h,binding,packet,host_completed)
                if loss and dropped is None and s is not None and s['state'] in ['armed','running'] and s['job_id']==binding['job_id']:
                    from phase11_5_r3_v2_native_loss import acknowledged_arm_prefix,drop_native_socket
                    ack=acknowledged_arm_prefix((root/'production-tls.bin').read_bytes(),process.pid,binding,packet)
                    if ack is not None:
                        require(0<=time.monotonic_ns()-ack['ack_monotonic_ns']<=10_000_000_000,'Native acknowledged loss window')
                        emit('arm_ack_before_loss',ack)
                        result['transport_loss_attempts']=1;save(root/'native-result.json',result)
                        dropped=drop_native_socket(process.pid,emit,plan.get('loss_mechanism','ss-destroy-v1'))
                next_status+=1
                require(time.monotonic()-next_status<=1,'Native host observation cadence')
            time.sleep(.05)
        if loss:
            require(dropped is not None,'Native acknowledged transport loss never executed')
            h=host_status();require(h['phase']=='blocked' and h['session_id']==binding['session_id'] and
                h['job_id']==binding['job_id'] and h['identity']['boot_id']==packet['boot_id'],
                'Original native session must remain blocked before explicit reconciliation')
            body=b'{"operation":"reconcile"}'
            request=urllib.request.Request('http://127.0.0.1:31425/api/wtp/recover',data=body,
                headers={'Content-Type':'application/json'},method='POST')
            emit('reconciliation_pending',dict(url=request.full_url,body_hex=body.hex(),session_id=binding['session_id']))
            with opener.open(request,timeout=15) as response:
                raw=response.read(131073);require(response.status==200 and len(raw)<=131072,'Native explicit reconciliation response')
            reply=json.loads(raw);emit('reconciliation_response',dict(body_hex=raw.hex(),value=reply))
            require(reply['ok'] is True and reply['status']['phase']=='idle' and
                reply['status']['session_id']==binding['session_id'] and
                reply['status']['identity']['boot_id']==packet['boot_id'],'Native same-session reconciliation failed')
            result['same_session_reconciled']=True
        # Terminal proof precedes orderly shutdown; shutdown is not completion evidence.
        process.terminate();process.wait(timeout=15);emit('process_exit',dict(returncode=process.returncode))
        validate_exit(process.returncode,loss,result.get('same_session_reconciled',False))
        result.update(status='CAPTURED_REQUIRES_AUDIT',job_id=binding['job_id'],terminal=completed)
    except BaseException as error:
        result.update(status='FAILED',error=str(error));emit('failure',dict(type=type(error).__name__,error=str(error)))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            emit('failed_process_cleanup',dict(returncode=process.returncode))
        emit('finish',result);save(root/'native-result.json',result);log.close()
    require(result['status']=='CAPTURED_REQUIRES_AUDIT','Native attempt requires diagnosis')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no process, network or RF action.');return
    root=a.root.resolve(strict=True);require(digest(root/'packet.json')==a.packet_sha256,'Native packet identity')
    run(root,json.loads((root/'packet.json').read_text()))
if __name__=='__main__':main()
