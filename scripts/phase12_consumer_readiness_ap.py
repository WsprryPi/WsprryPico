#!/usr/bin/env python3
"""One canonical owned AP/beacon before consumer cold boot; time stays disabled."""
import hashlib,json,os,re,signal,sys,time,threading,subprocess
from pathlib import Path
from phase12_engineering_fixture import action as fixture_action,wait_owned_beacon,management,owned_ap_configuration,verify_disabled_ntp
from phase12_fixture_roles import load_roles
from phase12_engineering_setup import private_bytes
from phase12_recovery_device import strict,require
from phase12_consumer_readiness import bound_info

def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,value):
 with Path(path).open('x') as out:os.chmod(path,0o600);json.dump(value,out,sort_keys=True);out.write('\n')
def inputs(root,request):
 require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12' and re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink(),'exact owned readiness root/authority')
 roles=load_roles(root);require(roles['selection']=='engineering' and roles['host_ap']=='wlan2' and roles['observer']=='wlan0' and request['roles_sha256']==roles['sha256'],'canonical consumer proof radio roles')
 for name,digest in request['inputs'].items():
  require(Path(name).name==name and sha(private_bytes(root/name,8388608))==digest,'actual staged source/private input digest')
 network_raw=private_bytes(root/'readiness-network.json',2048)
 require(network_raw==private_bytes(root/'populated-network.json',2048) and sha(network_raw)==request['network_sha256']==request['populated_network_sha256'],'same saved AP/network original bytes')
 network=strict(network_raw);require(network['time_server']==request['time_server'],'saved time source binding')
 return roles,network

def prepare(request,*,clock=time.monotonic,action=fixture_action,beacon=wait_owned_beacon,managed=management,ap_config=owned_ap_configuration,disabled=verify_disabled_ntp):
 root=Path(request['root']);roles,network=inputs(root,request);started=clock();end=started+300
 require(not (root/'readiness-ap-ready-before-boot.json').exists() and not (root/'readiness-ap-activation-attempt.json').exists(),'single AP preparation never replayed')
 before=managed();require(before==request.get('management_before',before),'same actual supplied management original')
 write(root/'readiness-ap-activation-attempt.json',dict(activation_attempts=1,started_monotonic_s=started,prior_boot_id=request['prior_boot_id'],case=request['case']))
 result=action(dict(root=str(root),authority=request['authority'],action='start_ap',interface='wlan2',proof_mode='target',ssid=network['ssid'],password=network['password'],time_server='192.168.84.1'))
 require(clock()<end and result['status']=='TARGET_PROOF_PENDING' and result['roles_sha256']==roles['sha256'],'one original AP activation result')
 observed=beacon(root,network['ssid'],before)
 require(clock()<end and observed['status']=='INDEPENDENT_BEACON_READY' and observed['ap_interface']=='wlan2' and observed['observer_interface']=='wlan0' and observed['bssid']==result['bssid'] and observed['frequency_mhz']==2422,'fresh exact owned beacon before boot')
 ap=ap_config(root,roles,__import__('phase12_engineering_fixture').command);responder=disabled(root,roles)
 require(managed()==before and clock()<end,'disabled time/management after preboot AP observation')
 receipt=dict(schema='phase12-readiness-ap-before-boot/1',status='AP_READY_SNTP_DISABLED_BEFORE_BOOT',root=str(root),case=request['case'],roles_sha256=roles['sha256'],source_commit=request['source_commit'],generation=request['generation'],checkpoint_sha256=request['checkpoint_sha256'],prior_boot_id=request['prior_boot_id'],inputs=request['inputs'],network_sha256=request['network_sha256'],activation_attempts=1,beacon_sha256=sha(private_bytes(root/'owned-ap-beacon-readiness.json',2097152)),beacon=observed,ap=ap,ntp_identity=responder,started_monotonic_s=started,ready_monotonic_s=clock(),deadline_monotonic_s=end,management_before=before)
 write(root/'readiness-ap-ready-before-boot.json',receipt)
 require(clock()<end,'late original readiness AP final receipt')
 return dict(status=receipt['status'],receipt=receipt,receipt_sha256=sha(private_bytes(root/'readiness-ap-ready-before-boot.json',2097152)))

def reuse(request,*,clock=time.monotonic,managed=management,ap_config=owned_ap_configuration,disabled=verify_disabled_ntp):
 root=Path(request['root']);roles,network=inputs(root,request);raw=private_bytes(root/'readiness-ap-ready-before-boot.json',2097152)
 require(sha(raw)==request['ap_ready_sha256'],'original preboot AP receipt hash')
 value=strict(raw)
 for key in ('root','case','roles_sha256','source_commit','generation','checkpoint_sha256','prior_boot_id','inputs','network_sha256'):
  require(value[key]==request[key],'same preboot receipt/request '+key)
 require(value['schema']=='phase12-readiness-ap-before-boot/1' and value['status']=='AP_READY_SNTP_DISABLED_BEFORE_BOOT' and value['activation_attempts']==1 and request['boot_id']!=value['prior_boot_id'] and 0<=value['started_monotonic_s']<value['ready_monotonic_s']<value['deadline_monotonic_s']==value['started_monotonic_s']+300 and clock()<value['deadline_monotonic_s'],'one fresh checkpoint boot after preactivated AP within same300')
 require(sha(private_bytes(root/'owned-ap-beacon-readiness.json',2097152))==value['beacon_sha256'] and strict(private_bytes(root/'owned-ap-beacon-readiness.json',2097152))==value['beacon'],'retained original exact beacon')
 require(ap_config(root,roles,__import__('phase12_engineering_fixture').command)==value['ap'] and disabled(root,roles)==value['ntp_identity'] and managed()==value['management_before'],'same preactivated AP/responder/management; no activation')
 require(clock()<value['deadline_monotonic_s'],'late preactivated original validation')
 return value

def station_cycle(request,operation,evidence,deadline,*,clock=time.monotonic,runner=subprocess.run,
                  managed=management,ap_config=owned_ap_configuration,disabled=verify_disabled_ntp):
 """One owned UUID down/up, keeping the original responder disabled and alive."""
 require(operation in ('down','up') and clock()<deadline,'named finite offline station cycle')
 root=Path(request['root']);roles,_=inputs(root,request)
 original_raw=private_bytes(root/'readiness-ap-ready-before-boot.json',2097152)
 require(sha(original_raw)==request['ap_ready_sha256'],'original AP receipt for station cycle')
 original=strict(original_raw);name='p12-engineering-'+root.name.rsplit('-',1)[1]
 require(original['ap']['connection']==name and roles['host_ap']=='wlan2' and
         original['root']==str(root) and original['case']==request['case'] and
         original['generation']==request['generation'] and original['inputs']==request['inputs'] and
         original['activation_attempts']==1 and clock()<original['deadline_monotonic_s'],
         'same original owned offline AP')
 marker=root/('readiness-station-'+operation+'-attempt.json')
 require(not marker.exists() and not marker.is_symlink(),'station cycle submission never replayed')
 def read(*argv):
  require(clock()<deadline,'station cycle command deadline')
  try:row=runner(list(argv),capture_output=True,timeout=min(10 if 'up' in argv or 'down' in argv else 5,deadline-clock()))
  except subprocess.TimeoutExpired as error:
   try:evidence.record('station_cycle_command_timeout',operation=operation,argv=list(argv),stdout_hex=(error.stdout or b'')[:262144].hex(),stderr_hex=(error.stderr or b'')[:16384].hex())
   except BaseException:pass
   raise
  error=None
  try:
   require(len(row.stdout)<=262144 and len(row.stderr)<=16384,'station cycle original output bound')
   if row.returncode:raise subprocess.CalledProcessError(row.returncode,list(argv),row.stdout,row.stderr)
   require(clock()<deadline,'late station cycle command')
  except BaseException as failure:error=failure
  try:evidence.record('station_cycle_command',operation=operation,argv=list(argv),returncode=row.returncode,stdout_hex=row.stdout[:262144].hex(),stderr_hex=row.stderr[:16384].hex())
  except BaseException:
   if error is None:raise
  if error is not None:raise error
  require(clock()<deadline,'station cycle command evidence deadline')
  return row.stdout.decode('utf-8')
 before=managed(read)
 require(before==original['management_before'] and disabled(root,roles)==original['ntp_identity'],
         'same original management and disabled responder before cycle')
 uuid=read('nmcli','-g','connection.uuid','connection','show',name).strip()
 require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',uuid) is not None,'actual owned UUID')
 if operation=='down':
  reuse(request,clock=clock,managed=lambda:managed(read),ap_config=lambda a,b,_:ap_config(a,b,read),disabled=disabled)
 else:
  down=strict(private_bytes(root/'readiness-station-down.json',65536))
  require(down['status']=='OWNED_AP_DOWN_SNTP_DISABLED' and down['connection_uuid']==uuid and
          down['ap_ready_sha256']==request['ap_ready_sha256'] and down['boot_id']==request['boot_id'] and
          down['generation']==request['generation'],'same single completed offline down')
  require(read('nmcli','-g','GENERAL.STATE','device','show','wlan2').strip()=='30 (disconnected)',
          'owned AP remains down before same UUID up')
 write(marker,dict(operation=operation,attempts=1,connection_uuid=uuid,boot_id=request['boot_id'],
                   generation=request['generation'],ap_ready_sha256=request['ap_ready_sha256']))
 remaining=deadline-clock();require(remaining>1,'owned cycle remaining original budget')
 read('sudo','-n','nmcli','--wait',str(max(1,min(9,int(remaining-1)))),'connection',operation,'uuid',uuid)
 require(read('nmcli','-g','connection.uuid','connection','show',name).strip()==uuid,'original profile UUID retained')
 if operation=='down':
  require(read('nmcli','-g','GENERAL.STATE','device','show','wlan2').strip()=='30 (disconnected)',
          'actual owned AP down')
 else:
  reuse(request,clock=clock,managed=lambda:managed(read),ap_config=lambda a,b,_:ap_config(a,b,read),disabled=disabled)
 require(managed(read)==before and disabled(root,roles)==original['ntp_identity'] and clock()<deadline,
         'same management and disabled original responder after cycle')
 result=dict(status='OWNED_AP_DOWN_SNTP_DISABLED' if operation=='down' else 'OWNED_AP_UP_SNTP_DISABLED',
             connection_uuid=uuid,boot_id=request['boot_id'],generation=request['generation'],
             ap_ready_sha256=request['ap_ready_sha256'],down_attempts=1,up_attempts=int(operation=='up'),
             initial_activation_attempts=1,total_activation_attempts=1+int(operation=='up'),ntp_enabled=False)
 write(root/('readiness-station-'+operation+'.json'),result)
 evidence.record('owned_offline_station_cycle',operation=operation,receipt=result)
 require(clock()<deadline,'station cycle final receipt deadline')
 return result

def offline_info(request,observe,deadline,*,clock=time.monotonic):
    require(clock()<deadline,'offline INFO original phase deadline')
    value=bound_info(observe(),request)
    require(clock()<deadline and value['status']['boot_id']==request['boot_id'] and
            str(value['provisioning_generation'])==str(request['generation']) and
            value['status']['clock_state']=='unsynchronized' and str(value['network']['accepted'])=='0' and
            value['saved_consumer_profile']['tls_pending'] is (request['case']=='pending-tls') and
            value['lan_wtp_ready'] is False,'same offline boot/generation/time boundary')
    return value

def controlled_loss(request,observe,evidence,deadline,*,clock=time.monotonic,sleeper=time.sleep):
    """Observe actual station loss, then hold it for the production 60 s fallback."""
    end=min(deadline,clock()+60)
    for _ in range(121):
        value=offline_info(request,observe,end,clock=clock)
        if value['network']['link_status']!=3:break
        sleeper(min(.5,max(0,end-clock())))
    else:raise TimeoutError('bounded observed station loss')
    started=clock();until=started+60
    require(until<deadline,'60 s fallback within original110 association')
    evidence.record('actual_station_loss',boot_id=request['boot_id'],generation=request['generation'],
                    link_status=value['network']['link_status'],loss_started_monotonic_s=started)
    while clock()<until:sleeper(min(2,until-clock()))
    value=offline_info(request,observe,deadline,clock=clock)
    require(value['network']['link_status']!=3,'station remained unavailable through actual fallback hold')
    evidence.record('controlled_station_loss_held',boot_id=request['boot_id'],generation=request['generation'],
                    held_seconds=clock()-started,ntp_accepted=0)
    require(clock()<deadline,'controlled loss evidence original deadline')
    return value

def main():
 os.umask(0o077);require(sys.argv[1:]==['--prepare-ap'],'explicit preboot action required')
 request=strict(sys.stdin.buffer.readline(65537))
 signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parent lost')))
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('preboot AP preparation deadline')));signal.alarm(110)
 def watch():
  if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
 threading.Thread(target=watch,daemon=True).start()
 print(json.dumps(prepare(request)),flush=True)
if __name__=='__main__':main()
