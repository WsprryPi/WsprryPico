#!/usr/bin/env python3
"""Campaign-owned .254 alias and finite B-peer-only SNTP responder."""
import fcntl,json,os,re,signal,socket,subprocess,sys,time
from pathlib import Path
from phase12_engineering_fixture import command,management,ntp_reply,private_write,strict
from phase12_fixture_roles import load_roles
from phase12_recovery_device import require

ADDRESS='192.168.84.254'
DURATION=300

def addresses(interface):
    rows=strict(command('ip','-j','address','show','dev',interface))
    require(len(rows)==1 and rows[0]['ifname']==interface,'exact alias interface')
    return rows[0]

def owns_alias(row,receipt):
    matches=[a for a in row.get('addr_info',[]) if a.get('family')=='inet' and a.get('local')==ADDRESS]
    return len(matches)==1 and matches[0].get('prefixlen')==24 and matches[0].get('label')==receipt['label'] and row['ifindex']==receipt['ifindex']

def process_bound(root,receipt,*,process_root=Path('/proc')):
    require(type(receipt['pid']) is int and receipt['pid']>1,'bounded owned alias PID')
    path=process_root/str(receipt['pid'])
    if not path.exists():return False
    args=(path/'cmdline').read_bytes().split(b'\0')
    require(str(Path(__file__).resolve()).encode() in args and b'--serve-alias' in args and
            str(root).encode() in args and receipt['startup_token'].encode() in args,'owned alias responder process identity')
    return True

def serve(root,token):
    require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink() and
            re.fullmatch('[0-9a-f]{32}',token),'alias server root/token')
    roles=load_roles(root);receipt=strict((root/'readiness-alias-owned.json').read_bytes())
    require(receipt['startup_token']==token and receipt['roles_sha256']==roles['sha256'],'alias startup binding')
    stop=False
    def stopped(*_):
        nonlocal stop;stop=True
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    started=time.monotonic();count=0;replies=0
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as stream:
        stream.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        stream.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,receipt['interface'].encode()+b'\0')
        stream.bind((ADDRESS,123));stream.settimeout(.5)
        private_write(root/'readiness-alias-ready.json',dict(pid=os.getpid(),startup_token=token,
            address=ADDRESS,roles_sha256=roles['sha256'],duration_s=DURATION))
        descriptor=os.open(root/'readiness-time-wire.jsonl',os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
        with os.fdopen(descriptor,'w') as wire:
            while not stop and time.monotonic()-started<DURATION and count<2000:
                try:query,peer=stream.recvfrom(512)
                except socket.timeout:continue
                selected=strict((root/'ntp-peer.json').read_bytes())
                if peer[0]!=selected['address']:continue
                count+=1
                if not (root/'readiness-alias-enabled.json').exists():continue
                monotonic_before=time.monotonic_ns();utc=time.time_ns()
                try:reply=ntp_reply(query,utc)
                except ValueError:continue
                stream.sendto(reply,peer);replies+=1
                row=dict(peer_address=peer[0],query_hex=query.hex(),reply_hex=reply.hex(),
                    monotonic_before_ns=monotonic_before,utc_ns=utc,monotonic_after_ns=time.monotonic_ns())
                wire.write(json.dumps(row,separators=(',',':'))+'\n');wire.flush();os.fsync(wire.fileno())
    private_write(root/'readiness-alias-stopped.json',dict(startup_token=token,requests=count,replies=replies))

def _action(request):
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','alias authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink(),'alias private root')
    roles=load_roles(root);require(request['roles_sha256']==roles['sha256'],'alias radio roles')
    operation=request['action'];path=root/'readiness-alias-owned.json'
    if operation=='start':
        require(not path.exists() and not path.is_symlink(),'never repeat alias creation')
        interface=roles['host_ap'];row=addresses(interface)
        name='p12-engineering-'+root.name.rsplit('-',1)[1]
        require(command('nmcli','-g','GENERAL.CONNECTION','device','show',interface).strip()==name,'only actual owned fixture AP')
        require(any(a.get('family')=='inet' and a.get('local')=='192.168.84.1' and a.get('prefixlen')==24 for a in row.get('addr_info',[])) and
                all(a.get('local')!=ADDRESS for a in row.get('addr_info',[])),'original .1 and unused .254 required')
        token=os.urandom(16).hex();receipt=dict(interface=interface,ifindex=row['ifindex'],label=interface+':p12'+token[:4],
            startup_token=token,roles_sha256=roles['sha256'],management_before=management(),daemon_spawn_attempted=False)
        private_write(path,receipt) # Fence uncertain address creation with exact-label ownership.
        command('sudo','-n','ip','address','add',ADDRESS+'/24','dev',interface,'label',receipt['label'])
        require(owns_alias(addresses(interface),receipt),'owned alias creation proof')
        # Create as the ordinary pi action user so private original wire evidence
        # remains retrievable after the sudo daemon appends to it.
        with (root/'readiness-time-wire.jsonl').open('x') as wire:os.chmod(wire.name,0o600)
        receipt['daemon_spawn_attempted']=True;private_write(path,receipt)
        with (root/'readiness-alias-server.log').open('x') as log:
            os.chmod(log.name,0o600)
            process=subprocess.Popen(['sudo','-n','python3',str(Path(__file__).resolve()),'--serve-alias',str(root),token],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        receipt['launch_pid']=process.pid
        try:private_write(path,receipt)
        except BaseException:
            process.terminate();process.wait(timeout=5);raise
        end=time.monotonic()+5
        while not (root/'readiness-alias-ready.json').exists() and time.monotonic()<end:time.sleep(.05)
        ready=strict((root/'readiness-alias-ready.json').read_bytes())
        require(process.poll() is None and ready['startup_token']==token and ready['roles_sha256']==roles['sha256'] and
                ready['address']==ADDRESS and ready['duration_s']==DURATION,'owned responder startup')
        receipt['pid']=ready['pid'];private_write(path,receipt)
        require(process_bound(root,receipt) and management()==receipt['management_before'],'alias responder/management proof')
        return dict(status='OWNED_ALIAS_STARTED_DISABLED',address=ADDRESS)
    require(operation in ('enable','stop'),'finite alias operation')
    if not path.exists():
        require(operation=='stop','alias not created');return dict(status='NO_OWNED_ALIAS')
    receipt=strict(path.read_bytes());require(receipt['roles_sha256']==roles['sha256'] and receipt['interface']==roles['host_ap'],'retained alias ownership')
    if operation=='enable':
        require(owns_alias(addresses(receipt['interface']),receipt) and process_bound(root,receipt),'owned live responder')
        peer=strict((root/'ntp-peer.json').read_bytes());require(re.fullmatch(r'192\.168\.84\.(?:[2-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-3])',peer['address']),'bound B isolated peer')
        require(not (root/'readiness-alias-enabled.json').exists(),'never repeat time enable')
        private_write(root/'readiness-alias-enabled.json',dict(enabled=True,startup_token=receipt['startup_token']))
        return dict(status='OWNED_ALIAS_TIME_ENABLED',address=ADDRESS)
    (root/'readiness-alias-enabled.json').unlink(missing_ok=True)
    ready_path=root/'readiness-alias-ready.json'
    if 'pid' not in receipt and ready_path.exists():
        ready=strict(ready_path.read_bytes());require(ready['startup_token']==receipt['startup_token'],'uncertain daemon startup ownership');receipt['pid']=ready['pid']
    if 'pid' not in receipt and 'launch_pid' in receipt:receipt['pid']=receipt['launch_pid']
    require('pid' in receipt or receipt['daemon_spawn_attempted'] is False,'uncertain responder startup; absence unproved')
    if 'pid' in receipt and process_bound(root,receipt):
        command('sudo','-n','kill','-TERM',str(receipt['pid']))
        end=time.monotonic()+5
        while process_bound(root,receipt) and time.monotonic()<end:time.sleep(.1)
        require(not process_bound(root,receipt),'alias responder absence required')
    row=addresses(receipt['interface'])
    if any(a.get('local')==ADDRESS for a in row.get('addr_info',[])):
        require(owns_alias(row,receipt),'foreign alias cannot be removed')
        command('sudo','-n','ip','address','del',ADDRESS+'/24','dev',receipt['interface'])
    require(all(a.get('local')!=ADDRESS for a in addresses(receipt['interface']).get('addr_info',[])) and
            management()==receipt['management_before'],'alias absence/management cleanup proof')
    private_write(root/'readiness-alias-cleanup.json',dict(status='OWNED_ALIAS_REMOVED',responder_absent=True,management_unchanged=True))
    return dict(status='OWNED_ALIAS_REMOVED')

def action(request):
    root=Path(request['root'])
    require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink(),'alias action root')
    lock=os.open(root/'readiness-alias-action.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _action(request)
    finally:os.close(lock)

def main():
    os.umask(0o077)
    if len(sys.argv)==4 and sys.argv[1]=='--serve-alias':serve(Path(sys.argv[2]),sys.argv[3]);return
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parent lost')))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('alias action deadline')));signal.alarm(35)
    print(json.dumps(action(strict(sys.stdin.buffer.readline(65537)))),flush=True)
if __name__=='__main__':main()
