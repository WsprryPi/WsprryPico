#!/usr/bin/env python3
"""Opt-in one-cycle idle A Wi-Fi recovery; no ARM, flash or CONFIG commands."""
import argparse,json,os,subprocess,time
from pathlib import Path
from phase11_5_inventory import require,exclusive_port,exchange
from phase11_5_pilot import SERIAL,DEVICE
from phase11_5_pilot_supervisor import finished,configuration
from phase11_5_device_management import digest,save
from phase11_5_r3_v2_rf import ASSET_SOURCE,ASSET_IMAGE,COMPLETION_SOURCE,COMPLETION_IMAGE,validate_info
from phase11_5_r3_v2_rf import MEMORY_SOURCE, MEMORY_IMAGE, MEMORY_BOOT

SCHEMA='phase11.5-r3-v2-wifi-recovery-v1'
P2_RECOVERY='restored-fixture-terminal-v1'
P2_HYPOTHESIS='A remained addressless with terminal link failure through 90 seconds after P2 fixture setup; one inactive OFF/ON restarts acquisition'
MEMORY_RECOVERY='post-flash-down-v1'
MEMORY_HYPOTHESIS='A remained addressless at link -1 through the 90-second post-flash readiness test while the isolated AP was up; one inactive OFF/ON restarts acquisition'
COMPLETION_RECOVERY={
    'retained-complete-addressless-v1':('associated-no-ipv4-v1',
        'A remained associated without IPv4 for at least 240 seconds after P1b fixture activation; one inactive OFF/ON restarts acquisition'),
    'retained-complete-terminal-v1':('terminal-failure-v1',
        'A reached terminal link failure after P1b fixture activation; one inactive OFF/ON restarts acquisition'),
    'retained-complete-link-recovery-v1':('no-ipv4-after-240-v1',
        'A has no IPv4 after at least 240 seconds of the verified fixture; one inactive OFF/ON restarts acquisition'),
}


def validate(p):
    p2=p.get('memory_recovery_policy')==P2_RECOVERY
    memory=p.get('memory_recovery_policy') in (MEMORY_RECOVERY,P2_RECOVERY)
    require(p.get('memory_recovery_policy') in (None,MEMORY_RECOVERY,P2_RECOVERY), 'Known memory recovery policy')
    require(p.get('completion_recovery_policy') is None or p.get('completion_recovery_policy') in COMPLETION_RECOVERY, 'Known completion recovery policy')
    completion=p.get('completion_recovery_policy') in COMPLETION_RECOVERY
    require(p['schema']==p['r3_scope']==SCHEMA and p['standing_authority']=='R3-COMPLETE-20260913-v2','Recovery scope')
    require(p['serial']==SERIAL and p['device_id']==DEVICE and
        (p['source_revision'],p['image_sha256'])==((MEMORY_SOURCE,MEMORY_IMAGE) if memory else (COMPLETION_SOURCE,COMPLETION_IMAGE) if completion else
            (ASSET_SOURCE,ASSET_IMAGE)),'Recovery image')
    require(p['runtime_seconds']==300 and p['restoration_seconds']==150 and p['maximum_wifi_cycles']==1 and
        p['rf_jobs']==p['flashes']==p['configuration_writes']==p['heap_probes']==0,'Recovery finite limits')
    if memory:
        require(not completion and p['boot_id']==MEMORY_BOOT and
                p['initial_link_policy']==('terminal-failure-v1' if p2 else 'cold-link-down-v1') and p['hypothesis']==(P2_HYPOTHESIS if p2 else MEMORY_HYPOTHESIS) and
                p['initial_job_id'] is None and type(p['not_before_monotonic_ns']) is int and
                p['not_before_monotonic_ns']>0, 'Exact post-flash recovery prerequisite')
        return p
    if completion:
        require((p['initial_link_policy'],p['hypothesis'])==COMPLETION_RECOVERY[p['completion_recovery_policy']] and
            p['initial_job_id']=='b88c7a3082eb4208a7e1f403bc13c9f8' and
            type(p['not_before_monotonic_ns']) is int and p['not_before_monotonic_ns']>0,
            'Completion recovery exact retained state and waited prerequisite')
        return p
    require((p.get('initial_link_policy','terminal-failure-v1'),p['hypothesis']) in [
        ('terminal-failure-v1','A stayed at terminal link failure after F1 AP expiry; one idle OFF/ON requests rejoin to verified F2'),
        ('terminal-failure-v1','A reached terminal link failure after F2 removal and F3 creation; one idle OFF/ON requests rejoin to verified F3'),
        ('associated-no-ipv4-v1','A associated to F3 but obtained no IPv4 lease after more than 240 seconds; one idle OFF/ON restarts network acquisition')],
        'Recovery hypothesis and admission policy')
    return p


def initial_link(network,p):
    policy=p.get('initial_link_policy','terminal-failure-v1')
    states={'terminal-failure-v1':(-3,-2),'associated-no-ipv4-v1':(1,),
            'no-ipv4-after-240-v1':(-3,-2,1),'cold-link-down-v1':(-1,)}.get(policy,())
    failed=network['link_status'] in states
    if policy!='terminal-failure-v1':failed=failed and network['mdns_state']=='waiting_address'
    require(network['enabled'] is True and not network['ipv4'] and failed,
        'Recovery requires exact failed/addressless link prerequisite')


def idle(v,baseline,p):
    validate_info(v['info'],baseline,p)
    s=v['wtp']['STATUS'];i=v['info']['status']
    terminal=p.get('completion_recovery_policy') in COMPLETION_RECOVERY
    require(s['boot_id']==p['boot_id'] and s['state']==i['state']==('complete' if terminal else 'empty') and
        s['output_active'] is i['output_active'] is False and s['owner_id'] is None and
        s['job_id']==(p['initial_job_id'] if terminal else None) and i['enabled'] is False,
        'Recovery inactive/unowned/schedule-disabled admission')
    require(configuration(v)==configuration(baseline),'Recovery configuration changed')


def run(root,p):
    end=time.monotonic()+p['runtime_seconds'];baseline=None;seq=0
    state=dict(status='STARTING',off=0,on=0,pending=None)
    path=root/'wifi-result.json';require(not path.exists(),'No recovery replay');save(path,state)
    def inventory(label):
        nonlocal seq
        require(time.monotonic()<end,'Recovery finite deadline')
        out=root/(label+'.stdout');err=root/(label+'.stderr')
        with out.open('xb') as o,err.open('xb') as e:
            r=subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),'--serial',SERIAL,
                '--device-id',DEVICE,'--session-id',p['inventory_session'],'--run'],stdout=o,stderr=e,timeout=min(65,end-time.monotonic()))
        require(r.returncode==0,'Recovery inventory failed');v=finished(out,'READ_ONLY_INVENTORY')
        if baseline is not None:idle(v,baseline,p)
        return v
    try:
        baseline=inventory('before-a');idle(baseline,baseline,p)
        n=baseline['info']['network']
        initial_link(n,p)
        for enabled,label in [(False,'off'),(True,'on')]:
            current=inventory(label+'-before')
            with (root/(label+'-exchange.jsonl')).open('x') as log:
                def emit(kind,value):
                    nonlocal seq
                    log.write(json.dumps(dict(sequence=seq,kind=kind,value=value,monotonic_ns=time.monotonic_ns()))+'\n')
                    log.flush();os.fsync(log.fileno());seq+=1
                with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
                    info=exchange(fd,b'INFO\n',min(end,time.monotonic()+5),emit,False)
                    idle(dict(current,info=info),baseline,p)
                    require(info['network']['enabled'] is not enabled,'Recovery transition changed')
                    state[label]=1;state['pending']=label;save(path,state)
                    ack=exchange(fd,b'WIFI ON\n' if enabled else b'WIFI OFF\n',min(end,time.monotonic()+5),emit,False)
                    require(ack==dict(ok=True),'Recovery command rejected')
            for index in range(11):
                v=inventory(label+'-after-'+str(index));n=v['info']['network']
                if n['enabled'] is enabled and not n['withdrawal_pending'] and n['requested_enabled'] is None:break
                require(index<10,'Recovery transition did not settle');time.sleep(.5)
            state['pending']=None;save(path,state)
        state['status']='CYCLE_ACKNOWLEDGED';save(path,state)
        for index in range(90):
            v=inventory('ready-'+str(index));n=v['info']['network']
            if n['link_status']==3 and n['ipv4']=='10.77.15.10' and v['wtp']['GET_CLOCK']['state']=='synchronized':
                state.update(status='RECOVERED_REQUIRES_AUDIT',final_inventory='ready-'+str(index)+'.stdout');break
            require(index<89 and time.monotonic()+2<end,'Recovery IP/clock readiness deadline');time.sleep(2)
    except BaseException as e:
        state.update(status='FAILED_REQUIRES_RECONCILIATION',error=str(e));raise
    finally:save(path,state)


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,required=True);a.add_argument('--packet-sha256',required=True);a.add_argument('--run',action='store_true');args=a.parse_args()
    if not args.run:print('Plan only; no device or network activity.');return
    root=args.root.resolve(strict=True);require(os.geteuid()==0 and digest(root/'packet.json')==args.packet_sha256,'Recovery root/packet')
    p=validate(json.loads((root/'packet.json').read_text()));require(p['root']==str(root),'Recovery root mismatch')
    if p.get('completion_recovery_policy') or p.get('memory_recovery_policy'):
        require(time.monotonic_ns()>=p['not_before_monotonic_ns'],'Recovery prerequisite wait not complete')
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['host_boot_id'],'Recovery host boot')
    timer=subprocess.check_output(['busctl','get-property','org.freedesktop.systemd1','/org/freedesktop/systemd1/unit/phase115_2dclosure_2dcleanup_2etimer','org.freedesktop.systemd1.Timer','NextElapseUSecMonotonic'],text=True).strip()
    require(timer=='t '+str(p['fixture_deadline_monotonic_ns']//1000) and
        time.monotonic_ns()+450_000_000_000<p['fixture_deadline_monotonic_ns'],'Recovery fixture deadline')
    for name,h in p['stage_sha256'].items():require(digest(root/name)==h,'Recovery helper identity')
    os.umask(0o077);run(root,p)

if __name__=='__main__':main()
