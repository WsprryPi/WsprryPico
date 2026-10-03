#!/usr/bin/env python3
"""Finite B populated source5 saves over an independently bound open AP observer."""
import hashlib,json,os,re,secrets,signal,socket,subprocess,sys,threading,time
from pathlib import Path
from phase12_consumer_negative_dispatch import HTTP as ConsumerHTTP
from phase12_consumer_negative import keys,seal,b64,unb64
from phase12_engineering_network_dispatch import cleanup_action,management,parse_interfaces,scan_link
from phase12_engineering_fixture import command,management as management_identity,action as fixture_action
from phase12_engineering_setup import private_bytes
from phase12_consumer_composition import Evidence,canonical
from phase12_serial_observer import Observer
from phase12_recovery_device import DEVICE,strict,require,resource_health
from phase12_composition_audit import counter
from check_standalone_image import validate_uf2

from phase12_fixture_roles import load_roles

class HTTP(ConsumerHTTP):
    interface='wlan0'
    def wire(self,method,path,body):
        routes={'/api/owner/v1/public-status','/api/owner/v1/claim/status','/api/bootstrap/v1/status'}
        posts={'/api/owner/v1/claim/start','/api/owner/v1/claim/submit','/api/bootstrap/v1/start','/api/bootstrap/v1/submit'}
        require((method=='GET' and path in routes and body is None) or
                (method=='POST' and path in posts and isinstance(body,dict)),'populated exact route scope')
        payload=b'' if body is None else canonical(body);require(len(payload)<=1024,'request bound')
        marker='Owner' if path.startswith('/api/owner/') else 'Bootstrap'
        head=method+' '+path+' HTTP/1.1\r\nHost: 192.168.4.1\r\nConnection: close\r\n'
        if body is not None:head+='Origin: http://192.168.4.1\r\nContent-Type: application/json\r\nX-WsprryPico-'+marker+': 1\r\nContent-Length: '+str(len(payload))+'\r\n'
        return head.encode()+b'\r\n'+payload
    def connect(self,deadline):
        require(time.monotonic()<deadline,'HTTP connect deadline');stream=socket.socket()
        try:
            stream.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,self.interface.encode()+b'\0')
            stream.bind(('192.168.4.3',0));stream.settimeout(min(5,deadline-time.monotonic()))
            stream.connect(('192.168.4.1',80));require(stream.getsockname()[0]=='192.168.4.3','actual observer source');return stream
        except BaseException:stream.close();raise

    def delivered_unobserved(self,path,body,deadline):
        """Drain TCP delivery, retain bytes privately, discard application meaning.

        Closing before the queued response is delivered cancels production's
        trial. This is application response loss, not physical packet loss.
        """
        self.attempts+=1;require(self.attempts<=100,'finite HTTP requests')
        wire=self.wire('POST',path,body);raw=bytearray()
        with self.connect(deadline) as stream:
            require(time.monotonic()<deadline,'discarded-response send deadline')
            stream.settimeout(min(5,deadline-time.monotonic()));stream.sendall(wire)
            while True:
                require(time.monotonic()<deadline,'discarded-response drain deadline')
                stream.settimeout(min(5,deadline-time.monotonic()));chunk=stream.recv(4096)
                if not chunk:break
                raw.extend(chunk);require(len(raw)<=32768,'discarded response bound')
        require(b'\r\n\r\n' in raw,'discarded response header missing')
        head,payload=bytes(raw).split(b'\r\n\r\n',1);require(len(head)<=8192,'discarded header bound')
        lines=head.split(b'\r\n');require(re.fullmatch(rb'HTTP/1\.1 [0-9]{3} .*',lines[0]),'discarded status framing')
        headers={}
        for line in lines[1:]:
            key,value=line.split(b':',1);key=key.lower();require(key not in headers,'discarded duplicate header');headers[key]=value.strip()
        require(b'transfer-encoding' not in headers and
            re.fullmatch(rb'0|[1-9][0-9]*',headers.get(b'content-length',b'')) and
            int(headers[b'content-length'])==len(payload),'discarded exact body length')
        # No JSON parse, status-code acceptance, state/digest inspection or retry.
        require(time.monotonic()<=deadline,'late discarded response');return wire,bytes(raw)


def wait_saved_boot(observe,read_slot,kind,generation,oldboot,expected,deadline,
                    *,clock=time.monotonic,sleeper=time.sleep):
    fresh_http_boot=None
    while True:
        require(clock()<deadline,'single save reboot deadline')
        try:observed=observe()
        except (OSError,TimeoutError):sleeper(.5);continue
        require(clock()<deadline,'late single save INFO')
        current=counter(observed['provisioning_generation'],'generation')
        require(current in (generation,generation+1),'save selected more than once')
        if observed['status']['boot_id']!=oldboot and current==generation+1:
            require(fresh_http_boot is None or observed['status']['boot_id']==fresh_http_boot,'HTTP/USB fresh boot disagrees')
            return observed
        if kind=='station':
            try:slot=read_slot()
            except (OSError,TimeoutError):sleeper(min(2,max(0,deadline-clock())));continue
            require(clock()<deadline,'late single save slot')
            require(slot['device_id']==DEVICE,'same-device slot observation')
            selected=counter(slot['generation'],'slot generation')
            if slot['boot_id']!=oldboot:
                require(isinstance(slot['boot_id'],str) and re.fullmatch('[0-9a-f]{32}',slot['boot_id']) is not None and
                    selected==generation+1 and slot['request_id_digest']==expected,'unbound fresh HTTP boot')
                require(fresh_http_boot is None or fresh_http_boot==slot['boot_id'],'multiple unexpected HTTP boots')
                fresh_http_boot=slot['boot_id']
                sleeper(min(2,max(0,deadline-clock())));continue
            require(selected in (generation,generation+1),'unexpected slot generation')
            if selected==generation+1:
                require(slot['request_id_digest']==expected,'foreign committed request')
            elif slot['request_id_digest']==expected:
                # Trial exposes this attempt's digest with the OLD durable
                # generation. It does not establish a committed tuple.
                require(slot['slot_state'] in ('trial','reconcile','terminal'),'unexpected attempt state')
        sleeper(min(2 if kind=='station' else .5,max(0,deadline-clock())))


def restart_trial_carrier(root,authority,kind,evidence,*,invoke=None):
    require(kind in ('station','network'),'finite trial carrier case')
    invoke=fixture_action if invoke is None else invoke
    restarted=invoke(dict(root=str(root),authority=authority,action='restart_ap_offline',preserve_disabled_ntp=True))
    require(restarted['status']=='OWNED_AP_RESTARTED_NO_SNTP' and restarted['ntp_started'] is False,
            'owned trial carrier without SNTP')
    evidence.record('owned_ap_restarted_after_start',case=kind,ntp_started=False)
    return restarted


def wait_fallback(observe, associate, deadline, *, clock=time.monotonic, sleeper=time.sleep):
    """Use actual carrier association after controlled station loss, never USB mutation."""
    while True:
        require(clock() < deadline, 'consumer station-loss fallback deadline')
        value = observe()
        if value['network']['link_status'] != 3:
            associate()
            require(clock()<deadline,'consumer station-loss fallback deadline')
            return value
        sleeper(.5)


def exact_channel_three(raw):
    fields=re.findall(rb'(?m)^[ \t]*freq:([^\r\n]*)$',raw)
    return len(fields)==1 and raw.count(b'freq:')==1 and re.fullmatch(rb'[ \t]*2422(?:\.0+)?[ \t]*',fields[0]) is not None


def associate_observer(name,ssid,deadline,evidence,interface='wlan0',*,single_channel=False,before_activation=None,clock=time.monotonic,runner=subprocess.run,sleeper=time.sleep):
    """Complete active scan before owned join; retain every command outcome."""
    def invoke(argv,limit):
        require(clock()<deadline,'observer association deadline')
        try:
            result=runner(argv,capture_output=True,timeout=min(limit,deadline-clock()))
        except subprocess.TimeoutExpired as error:
            stdout=error.stdout or b'';stderr=error.stderr or b''
            evidence.record('observer_command_timeout',argv=argv,stdout_hex=stdout[:262144].hex(),stderr_hex=stderr[:16384].hex(),
                            output_overflow=len(stdout)>262144 or len(stderr)>16384)
            require(len(stdout)<=262144 and len(stderr)<=16384,'observer timeout output bound')
            raise
        require(len(result.stdout)<=262144 and len(result.stderr)<=16384,'observer output bound')
        evidence.record('observer_command',argv=argv,returncode=result.returncode,
                        stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex())
        require(clock()<deadline,'late observer command')
        if result.returncode:raise subprocess.CalledProcessError(result.returncode,argv,result.stdout,result.stderr)
        return result.stdout
    while True:
        try:scan=invoke(['sudo','-n','/usr/sbin/iw','dev',interface,'scan']+(['freq','2422'] if single_channel else []),20)
        except subprocess.TimeoutExpired:
            if clock()>=deadline:raise
            sleeper(min(.5,deadline-clock()));continue
        except subprocess.CalledProcessError as error:
            # iw exposes Linux EBUSY/EAGAIN/ENOBUFS as numeric errno in stderr.
            # Retry only the read-only scan; no NM activation has been issued.
            if not re.search(rb'\(-(11|16|105)\)',error.stderr or b''):raise
            require(clock()<deadline,'exact observer AP scan deadline')
            sleeper(min(.5,deadline-clock()));continue
        matches=[]
        for block in re.split(rb'(?m)^BSS ',scan)[1:]:
            bssid=re.match(rb'([0-9a-f:]{17})',block)
            names=re.findall(rb'(?m)^\s*SSID: (.*)$',block)
            if bssid and names==[ssid.encode()]:
                if single_channel:require(exact_channel_three(block),'concurrent scan exact channel3')
                matches.append(bssid[1].decode())
        if matches:break
        require(clock()<deadline,'exact observer AP scan deadline');sleeper(min(.5,deadline-clock()))
    if before_activation is not None:
        evidence.record('exact_beacon_before_station_return',scan_raw_hex=scan.hex(),bssids=matches)
        before_activation(deadline)
        require(clock()<deadline,'station return before activation deadline')
    remaining=deadline-clock();require(remaining>1,'observer join remaining budget')
    wait=max(1,min(30,int(remaining-1)))
    invoke(['sudo','-n','nmcli','--wait',str(wait),'connection','up',name],wait+1)
    link=invoke(['/usr/sbin/iw','dev',interface,'link'],5)
    associated=re.search(rb'Connected to ([0-9a-f:]{17})',link)
    actual=re.search(rb'(?m)^\s*SSID: (.*)$',link)
    require(associated and actual and actual[1]==ssid.encode() and associated[1].decode() in matches,'exact scanned B AP association')
    if single_channel:require(exact_channel_three(link),'concurrent B AP association must remain channel3')
    evidence.record('actual_ap_carrier',interface=interface,scan_raw_hex=scan.hex(),link_raw_hex=link.hex(),bssid=associated[1].decode())


def seal_network(start,body,private,network):
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    require(start['device_id']==DEVICE,'network device binding')
    request=secrets.token_hex(16);nonce=secrets.token_bytes(12)
    aad=(b'WsprryPico/WiFi-Bootstrap/1\0'+bytes.fromhex(DEVICE)+bytes.fromhex(start['boot_id'])+
         bytes.fromhex(start['slot_id'])+unb64(body['browser_public_key'])+unb64(start['pico_public_key'])+
         bytes.fromhex(body['request_nonce'])+bytes.fromhex(request))
    shared=private.exchange(X25519PublicKey.from_public_bytes(unb64(start['pico_public_key'])))
    key=HKDF(algorithm=hashes.SHA256(),length=32,salt=hashlib.sha256(aad).digest(),info=b'WsprryPico network-only AEAD v1').derive(shared)
    parts=[network[k].encode() for k in ('ssid','password','time_server')]
    require(1<=len(parts[0])<=32 and 8<=len(parts[1])<=63 and 1<=len(parts[2])<=253,'network fields')
    plain=b''.join(bytes([len(p)])+p for p in parts);box=ChaCha20Poly1305(key).encrypt(nonce,plain,aad)
    return dict(version=1,device_id=DEVICE,boot_id=start['boot_id'],slot_id=start['slot_id'],request_id=request,
                aead_nonce=b64(nonce),ciphertext=b64(box[:-16]),tag=b64(box[-16:]))


def run(request):
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink(),'private root')
    if request.get('action')=='cleanup':
        receipt=root/'populated-observer-owned.json'
        if not receipt.exists():return dict(status='NO_OWNED_OBSERVER')
        owned=strict(private_bytes(receipt,2048));require(owned['name']=='p12-observer-'+root.name.rsplit('-',1)[1],'ownedobserverbinding')
        return cleanup_action(root)
    manifest_raw=private_bytes(root/'manifest.json',262144);require(hashlib.sha256(manifest_raw).hexdigest()==request['manifest_sha256'],'manifest hash')
    manifest=strict(manifest_raw);require(manifest['source_commit']==request['source_commit'],'source')
    image=private_bytes(root/'restore.uf2',4*1024*1024);validate_uf2(image)
    require(hashlib.sha256(image).hexdigest()==next(c for c in manifest['candidates'] if c['role']=='restore')['uf2']['sha256'],'ordinary image')
    network_raw=private_bytes(root/'populated-network.json',4096);require(hashlib.sha256(network_raw).hexdigest()==request['network_sha256'],'network hash')
    network=strict(network_raw);require(network['time_server']=='192.168.84.1','initial isolated time target')
    roles=load_roles(root);require(request.get('roles_sha256',roles['sha256'] if roles['selection']=='engineering' else None)==roles['sha256'],'radio roles binding');interface=roles['observer']
    before_management=management();management_bound=management_identity();rows=parse_interfaces(before_management[0]);require(rows.get(interface,{}).get('state')=='disconnected','unused independent observer')
    name='p12-observer-'+root.name.rsplit('-',1)[1]
    ssid='WsprryPico-'+request['suffix'];require(re.fullmatch('WsprryPico-[0-9a-f]{6}',ssid),'BAPname')
    require(name not in command('nmcli','-t','-f','NAME','connection','show').splitlines(),'observer name unused')
    require(request['case'] in ('station','network'),'finite case');prefix='populated-'+request['case']
    evidence=Evidence(root/(prefix+'-wire.jsonl'));observer=Observer();http=HTTP();http.interface=interface;deadline=time.monotonic()+300
    boot=request['boot_id'];generation=request['generation'];rows_out=[];created=False;trial_ap=False
    evidence.record('fixture_radio_roles',roles=roles)
    evidence.record('management_identity_before',value=management_bound)
    def info(fresh=False):
        require(time.monotonic()<deadline,'finite populated deadline');value,raw=observer();require(strict(raw)==value,'actual INFOwire');resource_health(value)
        s=value['status'];require(value['device_id']==DEVICE and value['revision']==request['source_commit'][:12] and
            value['provisioning_source']=='consumer_preclock' and value['access_state']=='healthy' and
            s['engine']=='inhibited-standalone-simulator' and s['enabled'] is False and s['output_active'] is False and
            s['state']=='empty' and not s.get('job_id') and not s.get('owner_id') and s['storage_healthy'] is True,'exact idleB')
        require(s['clock_state']=='unsynchronized' and value['saved_consumer_profile']['tls_pending'] is False,'noSNTP preserving existingtrust')
        evidence.record('actual_info',raw_hex=raw.hex());return value
    def restart_trial_ap(kind):
        nonlocal trial_ap
        trial_ap=True # Fence cleanup even if the one restart has uncertain completion.
        return restart_trial_carrier(root,request['authority'],kind,evidence)
    def exchange(method,path,body=None):
        code,value,wire,raw=http(method,path,body,min(deadline,time.monotonic()+10))
        evidence.record('http_request',raw_hex=wire.hex());evidence.record('http_response',raw_hex=raw.hex())
        require(code==200,'exact successful HTTPcode');return value
    fallback_deadline=min(deadline,time.monotonic()+110)
    def associate():
        associate_observer(name,ssid,fallback_deadline,evidence,interface=interface,single_channel=roles['selection']=='concurrent')
        require(management()[1]==before_management[1] and management_identity()==management_bound,'management identities/default routes unchanged')
    try:
        first=info();require(first['status']['boot_id']==boot and counter(first['provisioning_generation'],'generation')==generation,'seedboundary')
        receipt=root/'populated-observer-owned.json'
        if not receipt.exists():
            with receipt.open('xb') as output:os.chmod(receipt,0o600);output.write(canonical(dict(name=name)))
        created=True
        command('sudo','-n','nmcli','connection','add','type','wifi','ifname',interface,'con-name',name,'ssid',ssid,
            'connection.autoconnect','no','ipv4.method','manual','ipv4.addresses','192.168.4.3/24','ipv4.never-default','yes','ipv6.method','disabled',*(['802-11-wireless.band','bg','802-11-wireless.channel','3'] if roles['selection']=='concurrent' else []))
        fallback = wait_fallback(info, associate, fallback_deadline)
        evidence.record('actual_station_loss_fallback',link_status=fallback['network']['link_status'],
                        usb_mutation=False)
        for kind in (request['case'],):
            before=info();require(before['status']['boot_id']==boot and counter(before['provisioning_generation'],'generation')==generation,'before save exactboundary')
            public=exchange('GET','/api/owner/v1/public-status');require(public['device_id']==DEVICE and public['boot_id']==boot and
                counter(public['generation'],'generation')==generation and public['clock_ready'] is False and public['tls_ready'] is False and
                public['readiness']=='pending_trustworthy_time_or_tls','actual offline public status')
            if kind=='station':
                body,private=keys(generation);start=exchange('POST','/api/owner/v1/claim/start',body)
                require(start['boot_id']==boot and counter(start['generation'],'startgen')==generation,'owner STARTbinding')
                restart_trial_ap(kind)
                submitted=seal(start,body,private,request['station']);path='/api/owner/v1/claim/submit'
                result=exchange('POST',path,submitted);require(result['state'] in ('checking','accepted'),'owner accepted transport')
            else:
                from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
                from cryptography.hazmat.primitives import serialization
                private=X25519PrivateKey.generate();body=dict(version=1,device_id=DEVICE,
                    browser_public_key=b64(private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)),request_nonce=secrets.token_hex(16))
                start=exchange('POST','/api/bootstrap/v1/start',body);require(start['boot_id']==boot,'network STARTbinding')
                restart_trial_ap(kind)
                network['time_server']='192.168.84.254';submitted=seal_network(start,body,private,network);path='/api/bootstrap/v1/submit'
                wire,raw=http.delivered_unobserved(path,submitted,min(deadline,time.monotonic()+10))
                evidence.record('one_application_response_discarded',request_raw_hex=wire.hex(),response_raw_hex=raw.hex(),
                    semantic_response_observed=False,physical_packet_loss=False)
            expected=hashlib.sha256(bytes.fromhex(submitted['request_id'])).hexdigest();oldboot=boot;end=min(deadline,time.monotonic()+125)
            observed=wait_saved_boot(info,lambda:exchange('GET','/api/owner/v1/claim/status'),
                kind,generation,oldboot,expected,end)
            if trial_ap:
                if (root/'fixture-ap-proof.json').exists():
                    # Post-reboot receive proof has its own original join budget, within the case cap.
                    end=min(deadline,time.monotonic()+160)
                    selected_boot=observed['status']['boot_id']
                    while observed['network']['link_status']!=3:
                        require(time.monotonic()<end,'original network trial association deadline');time.sleep(.5);observed=info()
                        require(observed['status']['boot_id']==selected_boot and counter(observed['provisioning_generation'],'network trial generation')==generation+1,'same new network trial boot/generation')
                    proof=fixture_action(dict(root=str(root),authority=request['authority'],action='prove_target',phase=kind,source_commit=request['source_commit'],boot_id=selected_boot,generation=generation+1,remaining_s=min(160,end-time.monotonic())))
                    require(time.monotonic()<end and proof['status']=='TARGET_ASSOCIATION_VERIFIED','actual target network join before acceptance')
                    evidence.record('target_trial_association_proof',case=kind,proof=proof)
                fixture_action(dict(root=str(root),authority=request['authority'],action='stop',preserve_disabled_ntp=True));trial_ap=False
                evidence.record('owned_ap_stopped_after_durable_save',ntp_started=False)
            boot=observed['status']['boot_id'];generation+=1
            rows_out.append(dict(case=kind,request_digest=expected,generation=generation,boot_id=boot,submit_attempts=1,application_response_discarded=kind=='network'))
        result=dict(status='POPULATED_SAVES_REVIEW_REQUIRED',cases=rows_out,rf_jobs=0,physical_acceptance=False)
        path=root/(prefix+'-result.json');path.write_bytes(canonical(result)+b'\n');os.chmod(path,0o600);return result
    finally:
        evidence.close()
        try:
            if created:cleanup_action(root)
        finally:
            if trial_ap:fixture_action(dict(root=str(root),authority=request['authority'],action='stop',preserve_disabled_ntp=True))
        require(management_identity()==management_bound,'management identity after cleanup changed')


def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parentlost')))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('populated case deadline')))
    signal.alarm(320)
    if request.get('action')!='cleanup':
        def watch():
            if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
        threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)
if __name__=='__main__':main()
