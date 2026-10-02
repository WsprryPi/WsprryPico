#!/usr/bin/env python3
"""Bounded unattended B-only recovery campaign; default is offline plan validation."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
from phase12_candidate_manifest import read_json, verify
from phase12_recovery_device import resource_health, strict, sync_directory

SERIAL='CDDBF8767C506C07'
DEVICE='29f20b7342051ef947aa56cb9d4fab42'
RESERVED=0x3f3000
E10=0x3ff000
SIZE=4194304


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_pairs(items):
    out={}
    for key,value in items:
        require(key not in out,'duplicate JSON key');out[key]=value
    return out


def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def private_write(path,value):
    with Path(path).open('xb') as out:
        os.chmod(path,0o600);out.write(canonical(value)+b'\n');out.flush();os.fsync(out.fileno())
    fd=os.open(Path(path).parent,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


class Ledger:
    def __init__(self,path):
        self.path=Path(path);self.seq=0;self.previous='0'*64
        if self.path.exists():
            data=self.path.read_bytes();require(data.endswith(b'\n'),'truncated ledger')
            for line in data.splitlines():
                value=json.loads(line,object_pairs_hook=strict_pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)));checksum=value.pop('sha256')
                require(value['seq']==self.seq+1 and value['previous']==self.previous and hashlib.sha256(canonical(value)).hexdigest()==checksum,'corrupt ledger chain')
                self.seq=value['seq'];self.previous=checksum
    def record(self,kind,case=None,**payload):
        value=dict(seq=self.seq+1,previous=self.previous,kind=kind,case=case,utc_s=int(time.time()),payload=payload)
        checksum=hashlib.sha256(canonical(value)).hexdigest();value['sha256']=checksum
        with self.path.open('ab') as out:
            os.chmod(self.path,0o600);out.write(canonical(value)+b'\n');out.flush();os.fsync(out.fileno())
        sync_directory(self.path.parent)
        self.seq+=1;self.previous=checksum


def validate_plan(plan,manifest):
    require(re.fullmatch('[0-9a-f]{32}',plan['campaign_id']) is not None,'campaign ID')
    require(plan['schema'] in ('phase12-recovery-campaign/1','phase12-profile-continuation/1') and plan['authority']=='USER_AUTHORIZED_UNATTENDED_RECOVERY','campaign authority/scope')
    require(plan['serial']==SERIAL and plan['device_id']==DEVICE and plan['host']=='wspr5' and plan['interface']=='wlan2','exact B host/interface')
    require(plan['manifest_sha256']==hashlib.sha256(canonical(manifest)).hexdigest(),'manifest binding')
    require(plan['source_commit']==manifest['source_commit'],'source binding')
    require(plan['case_timeout_s']==300 and plan['max_resume_boots']==2 and plan['rf_jobs']==0,'finite inhibited bounds')
    cases=[dict(id=f'{level}-{stage}',kind='reset',level=level,stage=stage) for level in ('provisioning','full') for stage in range(1,8)]+[dict(id=f'profile-{stage}',kind='profile',stage=stage) for stage in range(8,11)]
    if plan['schema']=='phase12-profile-continuation/1':
        cases=cases[14:]
        for key in ('predecessor_ledger_sha256','predecessor_result_sha256','predecessor_baseline_sha256'):
            require(re.fullmatch('[0-9a-f]{64}',plan.get(key,'')),'continuation evidence binding')
    require(plan['cases']==cases,'exact bounded unique cases')
    return cases


def safe_info(info,revision=None,stage=None,consumed=None):
    require(info.get('device_id')==DEVICE,'wrong board identity')
    resource_health(info)
    s=info['status'];require(s['engine']=='inhibited-standalone-simulator' and s['output_active'] is False and s['enabled'] is False and s['state']=='empty' and not s.get('job_id') and not s.get('owner_id'),'inactive inhibited shared authority')
    require(s['storage_healthy'] is True and info['access_state'] in ('healthy','erased') and not info.get('bootstrap_reset_pending',False),'healthy stores')
    if revision is not None: require(info['revision']==revision,'revision mismatch')
    if stage is not None: require(int(info.get('phase12_fault_stage',0))==stage,'wrong fault stage')
    if consumed is not None: require(info.get('phase12_fault_consumed',False) is consumed,'one-shot consumption mismatch')
    return info


def observe_boot(boots,info,initial_boot,maximum):
    boots.add(info['status']['boot_id'])
    require(len(boots)-1<=1+maximum,'reboot budget exhausted')
    require(info['status']['boot_id']==initial_boot or
            info.get('phase12_fault_consumed') is True,'unexpected cold rearming')


def cleared_profile_journal():
    # Exact production Unprovisioned selection, with no retained inactive bank.
    import struct
    import zlib
    payload=struct.pack('<Q',0x324c455350435057)+bytes([2])+bytes(7)
    digest=hashlib.sha256(payload).digest()
    header=bytearray(b'\xff'*256)
    struct.pack_into('<QQII',header,0,0x3146525050435057,1,16,2)
    header[24:56]=digest
    struct.pack_into('<I',header,252,zlib.crc32(header[:252]))
    commit=bytearray(b'\xff'*256)
    struct.pack_into('<QQ',commit,0,0x31544d4d4f435057,1)
    commit[16:48]=digest
    struct.pack_into('<I',commit,252,zlib.crc32(commit[:252]))
    return bytes(header)+payload+b'\xff'*(8192-512-16)+bytes(commit)+b'\xff'*8192


def assess(case,before,after,before_bytes,after_bytes,prepared):
    require(before_bytes[E10:]==after_bytes[E10:],'E10 changed')
    require(after['access_loaded'] and after['access_state']==2 and after['profile_healthy'] and after['operational_healthy'],'journal load failure')
    if case['kind']=='profile':
        require(before_bytes[RESERVED:0x3f7000]==after_bytes[RESERVED:0x3f7000] and
                before_bytes[0x3fb000:E10]==after_bytes[0x3fb000:E10],
                'unrelated access/BLE/operational journal changed')
    if case['kind']=='reset':
        require(after['reset_level']==0 and after['reset_phase']==0 and after['epoch']==before['epoch']+1 and after['bond_count']==0 and after['default_password'],'reset did not complete once')
        old_keys=local_security_keys(before_bytes[0x3f5000:0x3f7000])
        new_keys=local_security_keys(after_bytes[0x3f5000:0x3f7000])
        require(new_keys is not None,'BLE physical bank contains peer/deleted/unknown secrets')
        if old_keys:
            require(all(new_keys.get(tag)!=key for tag,key in old_keys.items()),
                    'old local BLE security key retained after reset')
        require(after['profile_source']==2 and not after['profile_payload'],'profile not cleared')
        require(after_bytes[0x3f7000:0x3fb000]==cleared_profile_journal(),
                'profile banks retain stale secret bytes or unexpected journal')
        if case['level']=='full':
            require(after_bytes[0x3fb000:E10]==b'\xff'*16384 and after['config'] is None and after['watermark']==0,'full operational erase incomplete')
        else:
            require(after['effective_station']==before['effective_station'] and after['watermark']==before['watermark'],'effective station/watermark not preserved')
            old=before['config'];new=after['config']
            import copy
            expected=copy.deepcopy(old)
            if expected is None and before['effective_station']:
                expected=dict(version=1,enabled=False,station=before['effective_station'],
                              wifi={},schedules=[],expires_utc_s=0)
            if expected:
                expected['station']=before['effective_station']
                expected['wifi']=dict(ssid='',password='',ntp_ipv4='pool.ntp.org')
            require(new==expected,'operational configuration not preserved/cleared exactly')
    elif case['stage'] in (8,9):
        require(after['profile_sequence']==before['profile_sequence'] and after['profile_sha256']==before['profile_sha256'],'partial profile authority selected')
    else:
        require(after['profile_sequence']==before['profile_sequence']+1 and after['profile_source']==5,'committed profile not reconciled')
        p=json.loads(after['profile_payload']);old=json.loads(before['profile_payload'])
        require(p['request_sha256']==prepared['expected_digest'],'durable request digest mismatch')
        require(after['effective_station']==prepared['station'],'selected station mismatch')
        for key in ('network','tls','clients','device_id','version','tls_pending'):
            require(p.get(key)==old.get(key),'unrelated trust/network changed: '+key)
    return {'result':'PASS','physical_acceptance_scope':'named completed-phase/page watchdog interruption only'}


def local_security_keys(data):
    # Pinned SDK: alignment 1, 8-byte BTstack header and big-endian tag/length.
    # SMER/SMIR are freshly generated local keys, not BTD<n> peer credentials.
    # Reject any peer/deleted/unknown record, malformed tail or retained bank.
    if len(data)!=8192 or data[4096:]!=b'\xff'*4096: return None
    bank=data[:4096]
    if bank==b'\xff'*4096: return {}
    if bank[:8]!=b'BTstack\0': return None
    import struct
    keys={};at=8
    while at+8<=4096:
        tag,size=struct.unpack_from('>II',bank,at)
        if tag==0xffffffff:
            return keys if bank[at:]==b'\xff'*(4096-at) else None
        if tag not in (0x534d4552,0x534d4952) or size!=16 or tag in keys or at+24>4096:
            return None
        keys[tag]=bank[at+8:at+24];at+=24
    return None


def empty_bond_bank(data):
    return local_security_keys(data) is not None


def ap_ssid(suffix):
    require(isinstance(suffix,str) and re.fullmatch('[0-9a-f]{6}',suffix),
            'AP suffix identity')
    return 'WsprryPico-'+suffix


class Backend:
    def __init__(self,plan,manifest,artifact_root,campaign,inspector):
        self.plan=plan;self.manifest=manifest;self.artifact_root=Path(artifact_root);self.campaign=Path(campaign);self.inspector=str(Path(inspector).resolve())
        self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.connection='p12-recovery-'+plan['campaign_id']
        self.hardware_accessed=False
        self.helper=self.remote+'/phase12_recovery_device.py';self.roles={c['role']:c for c in manifest['candidates']}
    def call(self,action,**args):
        require(not hasattr(self,'guard') or self.guard.poll() is None,'board campaign lock lost')
        self.hardware_accessed=True
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','wspr5','python3',self.helper],input=canonical(dict(root=self.remote,action=action,**args)),capture_output=True,timeout=270)
        value=strict(p.stdout)
        if action=='info' and value.get('adapter_error') in ('TimeoutError','SerialException','FileNotFoundError'):
            raise TimeoutError('device observation unavailable: '+value['adapter_error'])
        require(p.returncode==0 and 'adapter_error' not in value,'adapter error: '+str(value.get('message','SSH/helper failure')))
        return value
    def acquire(self):
        # A live SSH-held lock excludes campaigns from any orchestrating host.
        guard_code="import os,fcntl,sys; f=os.open('/home/pi/.wsprrypico-recovery-"+SERIAL+".lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print('LOCKED',flush=True); sys.stdin.buffer.read()"
        import shlex
        self.guard=subprocess.Popen(['ssh','-o','BatchMode=yes','wspr5','python3 -c '+shlex.quote(guard_code)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        import select
        ready,_,_=select.select([self.guard.stdout],[],[],10)
        require(ready and self.guard.stdout.readline().strip()==b'LOCKED','board campaign already running')
    def setup(self):
        self.acquire()
        self.connection_created=False
        require(re.fullmatch('[0-9a-f]{32}',self.plan['campaign_id']),'campaign ID')
        subprocess.run(['ssh','-o','BatchMode=yes','wspr5','mkdir','-m','700',self.remote],check=True,timeout=10)
        for name in ('phase12_recovery_device.py','check_standalone_image.py'):
            src=Path(__file__).parent/name
            subprocess.run(['scp','-q',str(src),'wspr5:'+self.remote+'/'+name],check=True,timeout=20)
            actual=subprocess.check_output(['ssh','wspr5','sha256sum',self.remote+'/'+name],text=True,timeout=10).split()[0]
            require(actual==sha(src),'helper transfer hash')
        for role in ['restore']+[f'fault_{n}' for n in range(1,11)]:
            c=self.roles[role];subprocess.run(['scp','-q',str(self.artifact_root/c['uf2']['path']),'wspr5:'+self.remote+'/'+role+'.uf2'],check=True,timeout=20)
        info=self.call('info');safe_info(info)
        # The unused interface is static-only and never supplies a default route.
        require(info['access_default_password'] is True,'campaign requires retained default local-access password')
        ssid=ap_ssid(info['local_suffix'])
        p=subprocess.run(['ssh','wspr5','nmcli','-t','-f','GENERAL.STATE','device','show',self.plan['interface']],capture_output=True,text=True,timeout=10)
        require(p.returncode==0 and '30 (disconnected)' in p.stdout,'AP interface not unused')
        args=['sudo','-n','nmcli','connection','add','type','wifi','ifname',self.plan['interface'],'con-name',self.connection,'ssid',ssid,'connection.autoconnect','no','ipv4.method','manual','ipv4.addresses','192.168.4.2/24','ipv4.never-default','yes','ipv6.method','disabled']
        subprocess.run(['ssh','wspr5',*args],check=True,capture_output=True,timeout=20)
        self.connection_created=True
        return info
    def snapshot(self,name):
        result=self.call('snapshot',name=name)
        local=self.campaign/name
        require(not local.exists(),'local snapshot exists')
        subprocess.run(['scp','-q','wspr5:'+self.remote+'/'+name,str(local)],check=True,timeout=30)
        os.chmod(local,0o600)
        require(local.stat().st_size==SIZE and sha(local)==result['sha256'],'retained local backup barrier')
        with local.open('rb') as file: os.fsync(file.fileno())
        sync_directory(local.parent)
        result['inspection']=self.inspect(local)
        return result
    def inspect(self,path):
        p=subprocess.run([self.inspector,str(path)],capture_output=True,timeout=10,check=True)
        return strict(p.stdout)
    def deploy(self,role,backup,readback,restore=False):
        c=self.roles[role]
        return self.call('restore' if restore else 'deploy',image=role+'.uf2',image_sha256=c['uf2']['sha256'],backup=backup['path'],backup_sha256=backup['sha256'],readback=readback,revision=c['revision'],stage=c['fault_stage'])
    def prepare(self,case,station):
        self.call('open_ap')
        return self.call('prepare',kind=case['kind'],level=case.get('level'),stage=case['stage'],station=station,revision=self.manifest['source_commit'][:12],interface=self.plan['interface'],connection=self.connection,prepared=case['id']+'.request.json')
    def submit(self,prepared):
        return self.call('submit',prepared=prepared['prepared'],prepared_sha256=prepared['sha256'])
    def info(self): return self.call('info',allow_fault=True)
    def restore(self,baseline,name):
        result=self.deploy('restore',baseline,name,restore=True)
        safe_info(result['info'],self.manifest['source_commit'][:12],0,False)
        return result
    def stable_restore(self,baseline,name="final-stable-info.json"):
        original=baseline['inspection']
        old_profile=strict(original['profile_payload']) if original['profile_source']==5 else None
        end=time.monotonic()+180;stable=0;boot=None
        while time.monotonic()<end:
            info=safe_info(self.info(),self.manifest['source_commit'][:12],0,False)
            require(int(info['softap_session_inactivity_ms'])==900000 and
                    int(info['softap_session_absolute_ms'])==43200000 and
                    info['softap_retained_sessions']==0 and
                    not info['bootstrap_setup_pending'], 'ordinary restored session policy')
            require(int(info['access_generation'])==original['access_sequence'] and
                    int(info['provisioning_generation'])==original['profile_sequence'],
                    'restored journal generation changed')
            saved=info['saved_consumer_profile']
            require((saved['station'] if saved else info['status']['station'])==original['effective_station'],
                    'restored effective station changed')
            expected_time=old_profile['network']['time_server'] if old_profile else (original['config']['wifi']['ntp_ipv4'] if original['config'] else 'pool.ntp.org')
            require(info['network']['ntp_server']==expected_time,'restored time server changed')
            applicable=bool(old_profile and old_profile['network']['ssid']) or bool(original['config'] and original['config']['wifi']['ssid'])
            quiet=all(info[key]==0 for key in ('network_active_connections',
                      'network_pending_connections','network_buffered_rx_bytes',
                      'network_pending_tcp_bytes','bootstrap_pending_tcp_bytes',
                      'ble_active_connections','ble_inbound_bytes','ble_outbound_bytes')) and not info['ble_indication_pending'] and not info['bootstrap_connected']
            ready=quiet and (not applicable or (info['network']['link_status']==3 and
                  bool(info['network']['ipv4']) and info['status']['clock_state']=='synchronized'))
            if boot is None: boot=info['status']['boot_id']
            require(info['status']['boot_id']==boot,'unexpected final restoration reboot')
            stable=stable+1 if ready else 0
            if stable>=5:
                private_write(self.campaign/name,info)
                return dict(samples=stable,network_time_applicable=applicable,boot_id=boot)
            time.sleep(2)
        raise TimeoutError('restored network/time stability deadline')

    def cleanup(self):
        try:
            if getattr(self,'connection_created',False):
                existing=subprocess.run(['ssh','-o','BatchMode=yes','wspr5','nmcli','-t','-f','NAME','connection','show'],capture_output=True,text=True,timeout=20,check=True)
                if self.connection in existing.stdout.splitlines():
                    subprocess.run(['ssh','-o','BatchMode=yes','wspr5','sudo','-n','nmcli','connection','delete',self.connection],capture_output=True,timeout=20,check=True)
        finally:
            if hasattr(self,'guard'):
                self.guard.stdin.close();self.guard.wait(timeout=10)


def recover_existing(plan,manifest,root,backend):
    root=Path(root);receipt=read_json(root/'baseline-receipt.json')
    require(receipt['plan_sha256']==hashlib.sha256(canonical(plan)).hexdigest() and receipt['path']=='baseline.bin','recovery receipt binding')
    baseline=root/receipt['path']
    require(not baseline.is_symlink() and baseline.stat().st_size==SIZE and sha(baseline)==receipt['sha256'],'retained recovery backup lost/changed')
    name='recovery-'+uuid.uuid4().hex
    # A separate log preserves a corrupt/truncated campaign ledger intact.
    ledger=Ledger(root/(name+'.jsonl'));ledger.record('recovery_only_start',baseline_sha256=receipt['sha256'])
    backend.acquire();backend.connection_created=True
    try:
        remote_name=name+'.bin'
        subprocess.run(['scp','-q',str(baseline),'wspr5:'+backend.remote+'/'+remote_name],check=True,timeout=30)
        recovery_baseline=dict(path=remote_name,sha256=receipt['sha256'],inspection=backend.inspect(baseline))
        result=backend.restore(recovery_baseline,name+'.readback.bin')
        result['stability']=backend.stable_restore(recovery_baseline,name+'.stable-info.json')
        ledger.record('recovery_only_restored',readback=result['readback'])
        return {'status':'RESTORED_RECOVERY_ONLY','destructive_cases_resumed':0}
    finally: backend.cleanup()


def validate_completed_resets(plan,root,backend):
    require(root is not None,'continuation requires retained reset evidence')
    root=Path(root)
    for key,name in (('predecessor_ledger_sha256','ledger.jsonl'),
                     ('predecessor_result_sha256','result.json'),
                     ('predecessor_baseline_sha256','baseline.bin')):
        require(sha(root/name)==plan[key],'continuation evidence hash mismatch')
    Ledger(root/'ledger.jsonl')
    result=strict((root/'result.json').read_bytes())
    require(result['source_commit']==plan['source_commit'] and result['serial']==SERIAL and
            result['device_id']==DEVICE and result['hardware_accessed'] is True and
            result['rf_jobs']==0 and len(result['cases'])==14 and
            result['restoration'].get('stability',{}).get('samples')==5 and
            'error' not in result['restoration'],'incomplete restored reset predecessor')
    records=[strict(line) for line in (root/'ledger.jsonl').read_bytes().splitlines()]
    expected=[dict(id=f'{level}-{stage}',kind='reset',level=level,stage=stage)
              for level in ('provisioning','full') for stage in range(1,8)]
    require([row['case'] for row in result['cases']]==[c['id'] for c in expected],
            'reset predecessor cases')
    require([row['case'] for row in records if row['kind']=='mutation_attempt']==[c['id'] for c in expected],
            'predecessor repeated or extra submission')
    for case,row in zip(expected,result['cases']):
        before=root/(case['id']+'.before.bin');after=root/(case['id']+'.after.bin')
        require(sha(before)==row['before_sha256'] and sha(after)==row['after_sha256'],
                'predecessor snapshot hash')
        assess(case,backend.inspect(before),backend.inspect(after),
               before.read_bytes(),after.read_bytes(),{})
    return True


def campaign(plan,manifest,root,backend,clock=time.monotonic,sleeper=time.sleep,completed_reset_campaign=None):
    root=Path(root);ledger=Ledger(root/'ledger.jsonl');cases=validate_plan(plan,manifest)
    require(ledger.seq==0,'existing campaign cannot repeat operations; use recovery-only')
    if plan['schema']=='phase12-profile-continuation/1':
        validate_completed_resets(plan,completed_reset_campaign,backend)
    baseline=None;rows=[];primary=None;restoration=None
    ledger.record('campaign_start',plan_sha256=hashlib.sha256(canonical(plan)).hexdigest(),runner_sha256=sha(__file__))
    try:
        safe_info(backend.setup());ledger.record('preflight_pass')
        baseline=backend.snapshot('baseline.bin')
        require(baseline['inspection']['profile_healthy'] and baseline['inspection']['access_state']==2 and baseline['inspection']['operational_healthy'],'baseline journal health')
        private_write(root/'baseline-receipt.json',dict(plan_sha256=hashlib.sha256(canonical(plan)).hexdigest(),path=baseline['path'],sha256=baseline['sha256']))
        ledger.record('backup_retained',path=baseline['path'],sha256=baseline['sha256'])
        if plan['schema']=='phase12-profile-continuation/1':
            require((root/baseline['path']).read_bytes()[RESERVED:]==
                    (Path(completed_reset_campaign)/'baseline.bin').read_bytes()[RESERVED:],
                    'continuation baseline settings changed')
        backend.restore(baseline,'restoration-preflight.bin');ledger.record('restoration_preflight_pass')
        original=baseline['inspection'];require(not original['config'] or original['config']['enabled'] is False,'baseline scheduling enabled')
        require(original['effective_station'] is not None,'populated station required')
        if original['profile_source']==5: require(not json.loads(original['profile_payload']).get('tls_pending',False),'deferred boot TLS save not allowed')
        for case in cases:
            started=clock();cid=case['id'];ledger.record('case_start',cid)
            before=backend.snapshot(cid+'.before.bin');ledger.record('case_backup_retained',cid,sha256=before['sha256'])
            deployed=backend.deploy('fault_'+str(case['stage']),before,cid+'.deployment.bin')
            info=safe_info(deployed['info'],manifest['source_commit'][:12],case['stage'],False)
            initial_boot=info['status']['boot_id'];boots={initial_boot};station=dict(original['effective_station'])
            station['power_dbm']=30 if station['power_dbm']!=30 else 27
            prepared=backend.prepare(case,station);prepared['station']=station
            private_write(root/(cid+'.prepared.json'),prepared)
            require(clock()-started<plan['case_timeout_s'],'case deadline before mutation')
            ledger.record('mutation_attempt',cid,prepared_sha256=prepared['sha256'],request_id=prepared['request_id'],expected_digest=prepared['expected_digest'])
            outcome=backend.submit(prepared);ledger.record('mutation_delivery',cid,**outcome)
            while True:
                require(clock()-started<=plan['case_timeout_s'],'case deadline exhausted')
                try: info=backend.info()
                except (OSError,TimeoutError): sleeper(.5);continue
                require(info['device_id']==DEVICE and info['revision']==manifest['source_commit'][:12],'post-mutation identity drift')
                require(int(info.get('phase12_fault_stage',0))==case['stage'],'unexpected stage')
                observe_boot(boots,info,initial_boot,plan['max_resume_boots'])
                if info.get('phase12_fault_consumed') is True:
                    safe_info(info,manifest['source_commit'][:12],case['stage'],True);break
                sleeper(.5)
            require(info['status']['boot_id']!=initial_boot,'cut did not reboot')
            private_write(root/(cid+'.after-info.json'),info)
            after=backend.snapshot(cid+'.after.bin')
            require(clock()-started<=plan['case_timeout_s'],'case deadline after readback')
            row=assess(case,before['inspection'],after['inspection'],(root/before['path']).read_bytes(),(root/after['path']).read_bytes(),prepared)
            row.update(case=cid,seconds=clock()-started,observed_boots=len(boots),before_sha256=before['sha256'],after_sha256=after['sha256'])
            backend.restore(baseline,cid+'.restored.bin');ledger.record('case_restored',cid)
            rows.append(row);ledger.record('case_pass',cid,result=row)
    except BaseException as error:
        primary={'type':type(error).__name__,'message':str(error)};ledger.record('campaign_failed',error=primary)
    finally:
        if baseline:
            try:
                restoration=backend.restore(baseline,'final-restoration.bin')
                restoration['stability']=backend.stable_restore(baseline)
                ledger.record('final_restoration_pass',readback=restoration['readback'])
            except BaseException as error:
                restoration={'error':type(error).__name__,'message':str(error)};ledger.record('final_restoration_failed',**restoration)
        try: backend.cleanup()
        except Exception as error: ledger.record('host_cleanup_failed',error=type(error).__name__);primary=primary or {'type':'HostCleanupFailed','message':str(error)}
    complete=len(rows)==len(cases) and primary is None and restoration and 'error' not in restoration
    result=dict(schema='phase12-recovery-result/1',status='PASS_NAMED_SCOPE' if complete else 'STOPPED',source_commit=manifest['source_commit'],serial=SERIAL,device_id=DEVICE,hardware_accessed=getattr(backend,'hardware_accessed',False),rf_jobs=0,cases=rows,error=primary,restoration=restoration,physical_acceptance=bool(complete and getattr(backend,'hardware_accessed',False)))
    private_write(root/'result.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--artifact-root',type=Path,required=True);p.add_argument('--campaign',type=Path,required=True);p.add_argument('--inspector',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--recover-existing',action='store_true');p.add_argument('--completed-reset-campaign',type=Path)
    a=p.parse_args();plan=read_json(a.plan);manifest=read_json(a.manifest);validate_plan(plan,manifest);verify(manifest,a.artifact_root)
    if not a.run: print(json.dumps({'status':'VALIDATED_NO_HARDWARE','cases':len(plan['cases'])}));return
    os.umask(0o077)
    lock=os.open('/private/tmp/wsprrypico-recovery-'+SERIAL+'.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(lock,'w') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.recover_existing:
            require(a.campaign.is_dir() and not a.campaign.is_symlink(),'existing private campaign required')
            print(json.dumps(recover_existing(plan,manifest,a.campaign,Backend(plan,manifest,a.artifact_root,a.campaign,a.inspector))));return
        require(not a.campaign.exists(),'campaign directory exists')
        a.campaign.mkdir(mode=0o700,parents=True)
        sync_directory(a.campaign.parent)
        def interrupted(_signum,_frame): raise KeyboardInterrupt('campaign interrupted')
        signal.signal(signal.SIGTERM,interrupted)
        result=campaign(plan,manifest,a.campaign,Backend(plan,manifest,a.artifact_root,a.campaign,a.inspector),completed_reset_campaign=a.completed_reset_campaign)
        print(json.dumps({'status':result['status'],'passed_cases':len(result['cases']),'restored':result['restoration'] is not None and 'error' not in result['restoration']}))
        if result['status']!='PASS_NAMED_SCOPE': sys.exit(1)


if __name__=='__main__': main()
