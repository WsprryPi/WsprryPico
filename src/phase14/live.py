"""Linux physical adapter reusing existing identity-bound control and receiver tools."""
import contextlib
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from led_closeout.device import Device, Peer
from phase14.profiles import durable_settings
from led_closeout.runner import require, sha256
from phase14.plan import BOARDS, BANDS, job, accepted_events, validate_capture

CAPTURE='/home/pi/wsprrypi-qualification-runs/complete-test-deployment-284c7e04a3fdd079c46e782b/wspq-capture-soapy'
PICOTOOL='/home/pi/phase11-4-e1/picotool-build/picotool'


def save(path,value):
    temporary=Path(str(path)+'.pending')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


class Evidence:
    def __init__(self,root):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=False,mode=0o700)
        self.events=(self.root/'events.jsonl').open('x',buffering=1)
    def event(self,kind,value):
        self.events.write(json.dumps(dict(kind=kind,utc_ns=time.time_ns(),monotonic_ns=time.monotonic_ns(),value=value))+'\n')


class Rig:
    def __init__(self,root,source,*,board=None,receiver=True,reference=False):
        self.e=Evidence(root)
        self.device=Device({'picotool':dict(path=PICOTOOL),'evidence_mode':'gpio-readback','wtp_request_timeout':5},self.e,source)
        self.lock=None
        self.reference_before=None
        try:
            self.device.lock_boards(board or 'A',None if board else 'B')
            if receiver:
                self.lock=open('/tmp/wsprrypico-phase14-receiver.lock','a')
                fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if reference:
                require(receiver,'reference requires receiver ownership')
                from phase14_reference import gps
                self.reference_before=gps()
                require(self.reference_before['out1'] and not self.reference_before['pps1'],'GPSDO output 1 RF readiness')
        except BaseException:
            self.close()
            raise
    def info(self,board):
        value=self.device.info(board)
        require(value['device_id']==BOARDS[board][1], 'named device mismatch')
        self.e.event('info',dict(board=board,info=value))
        return value
    def idle(self,board):
        value=self.info(board);s=value['status']
        require(not s['enabled'] and not s['output_active'] and s['owner_id'] is None and
                s['state'] not in ('armed','running','loaded','failed'), 'board not available for finite test')
        return value
    def deploy(self,board,image,commit):
        before=self.idle(board)
        require(sha256(image)==self.image_hash, 'firmware artifact hash')
        self.device.rom(board)
        self.device.pt(board,['load','-v',str(image)])
        self.device.pt(board,['reboot'])
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            try:
                value=self.device.console(board,'INFO')
                ready=(value.get('lan_wtp_ready') if value.get('provisioning_source')=='consumer_preclock' else
                       value.get('provisioning_source')=='provisioned' and value.get('network',{}).get('control_listening'))
                if ready:
                    break
            except (FileNotFoundError,ValueError,TimeoutError):
                pass
            time.sleep(.5)
        else:
            raise TimeoutError('candidate boot/LAN readiness')
        value=self.idle(board)
        require(value['revision']==commit[:12] and value['status']['engine']=='pio-dma-gp2', 'candidate source/engine')
        require(durable_settings(before)==durable_settings(value), 'firmware load changed durable settings')
        self.e.event('deployment_verified',dict(board=board,uf2=str(image),sha256=self.image_hash,info=value))
    def inventory(self,boards=BOARDS):
        values={}
        for board in boards:
            value=self.idle(board)
            peer=self.device.peer(board)
            responses={op:peer.request(op,{}) for op in ('CAPS','GET_CLOCK','STATUS','PING')}
            values[board]=dict(info=value,responses=responses)
        save(self.e.root/'inventory.json',values)
        return {b:dict(revision=v['info']['revision'],clock=v['info']['system_clock_hz'],
                       engine=v['info']['status']['engine'],state=v['responses']['STATUS']['state'])
                for b,v in values.items()}
    def execute(self,board,clock,band,mode,sequence,*,duration=None,action='complete',image_hash=None,workload='normal',browser_credentials=None,clock_loss=False,request_compensation_ppb=0):
        root=self.e.root/(str(sequence)+'-'+board+'-'+str(clock)+'-'+band+'-'+mode)
        root.mkdir(mode=0o700)
        before=self.idle(board);peer=self.device.peer(board)
        require(before['system_clock_hz']==clock and before['status']['engine']=='pio-dma-gp2','RF clock/engine mismatch')
        reference=None
        if self.reference_before:
            from phase14_reference import gps
            reference=gps(BANDS[band]-40000)
            require(all(reference[k]==self.reference_before[k] for k in ('out1','out2','pps1','f2','out1low','out2low')),
                    'unrelated reference settings changed')
        # Every capture has one attributable Pico and an inactive peer board.
        other='B' if board=='A' else 'A';self.idle(other)
        browser=None
        if browser_credentials:
            require(before['provisioning_source']=='provisioned','browser workload requires engineering profile')
            from phase14.browser import Browser
            browser=Browser(browser_credentials,before)
        value=job(mode,band,clock,uuid.uuid4().hex,duration,workload)
        from phase14.calibration import request_compensated
        value=request_compensated(value,request_compensation_ppb)
        settings=dict(format='CF32',sample_rate_hz=250000,bandwidth_hz=200000,
                      center_frequency_hz=BANDS[band]-25000,gain_db=20,channel=0,agc=False,bias_tee=False)
        seconds=math.ceil(int(value['total_duration_ns'])/1e9)+45
        count=seconds*250000
        argv=[CAPTURE,'--enable-physical-sdr','sdrplay','2404058C60',str(settings['center_frequency_hz']),
              str(count),'20','250000','200000','0','false','false','100000',str(seconds+12),
              str(root/'capture.cf32'),str(root/'capture.json'),root.name]
        require(__import__('shutil').disk_usage(root).free>count*8+256*1024*1024,'capture storage')
        record=dict(schema='phase14-physical/1',board=board,serial=BOARDS[board][0],
            device_id=BOARDS[board][1],source_revision=before['revision'],boot_id=peer.boot,
            firmware_sha256=image_hash,clock_hz=clock,divider=1,engine='pio-dma-gp2',rf_gp=2,
            session_id=peer.session,browser_activity=[],
            engine_frequency_correction_ppb=0,requested_frequency_compensation_ppb=request_compensation_ppb,
            band=band,mode=mode,workload=workload,job=value,reference=reference,receiver_command=argv,receiver_helper_sha256=sha256(CAPTURE),
            receiver_settings=settings,action=action,result='PENDING',status=[],before=before,
            path='each source -20 dB -> combiner -> -40 dB -> RSP1B; no antenna; no LPF; operator-owned filtering')
        save(root/'physical.json',record)
        block=None
        if clock_loss:
            require(board=='B' and mode=='TONE' and duration is not None and 220<=duration<=3600 and action=='complete',
                    'finite B Tone clock-loss workload')
            from phase14.clock_loss import NtpBlock
            block=NtpBlock(before,self.e)
        process=None;claimed=False;owner=uuid.uuid4().hex;terminal=None
        with (root/'receiver.log').open('x') as log:
            try:
                process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                capture_deadline=time.monotonic()+seconds+12
                deadline=time.monotonic()+8
                while not (root/'capture.cf32.incomplete').exists() or (root/'capture.cf32.incomplete').stat().st_size<65536:
                    require(process.poll() is None and time.monotonic()<deadline,'capture readiness')
                    time.sleep(.05)
                # Retain quiet before any RF and give network framing a generous finite arm margin.
                time.sleep(1)
                response=peer.request('CLAIM',dict(owner_id=owner,lease_ms=60000));claimed=True
                require(response['owner_id']==owner,'CLAIM owner')
                # Initial low-band waveform preparation can exceed a short control
                # round trip. Bound the single mutation; never retry an uncertain LOAD.
                response=peer.request('LOAD',value,timeout=30)
                record['load']=response;record['accepted_job']=accepted_events(value,response['adjustments'])
                clock_value=peer.request('GET_CLOCK',{})
                require(clock_value['state']=='synchronized' and int(clock_value['uncertainty_ns'])<=500000000,'WTP clock not admissible')
                start=(int(clock_value['utc_now_ns'])//1000000000+4)*1000000000
                record['arm']=peer.request('ARM',dict(job_id=value['job_id'],start_utc_ns=str(start),max_start_uncertainty_ns='500000000'))
                if action=='cancel':
                    pending=peer.request('STATUS',{})
                    require(pending['boot_id']==record['boot_id'] and pending['job_id']==value['job_id'] and
                        pending['state']=='armed' and pending['output_active'] is False,'pending cancellation reached RF')
                    record['status'].append(dict(utc_ns=time.time_ns(),monotonic_ns=time.monotonic_ns(),status=pending))
                    record['cancel_requested_utc_ns']=time.time_ns()
                    record['cancel_reply']=peer.request('ABORT',dict(job_id=value['job_id']))
                save(root/'physical.json',record)
                end=time.monotonic()+int(value['total_duration_ns'])/1e9+10
                action_done=False;disconnected=False;running_since=None;last_info=0;last_renew=time.monotonic();last_browser=0;browser_index=0
                while time.monotonic()<end:
                    require(process.poll() is None,'capture ended before terminal RF')
                    if disconnected:
                        status=self.info(board)['status']
                    else:
                        status=peer.request('STATUS',{})
                    require(status['boot_id']==record['boot_id'] and status['job_id']==value['job_id'],'job/boot observation mismatch')
                    record['status'].append(dict(utc_ns=time.time_ns(),monotonic_ns=time.monotonic_ns(),status=status))
                    if status['state']=='running' and running_since is None:running_since=time.monotonic()
                    if block and not block.active and status['state']=='running' and status['output_active']:
                        # Suppress observations after RF actually starts. Blocking
                        # during the four-second arm lead can age a nearly-stale
                        # clock before launch, testing a different assertion.
                        block.start();record['ntp_block_table']=block.table
                    if running_since and not action_done and time.monotonic()-running_since>=2:
                        if action=='abort':peer.request('ABORT',dict(job_id=value['job_id']))
                        elif action=='disconnect':
                            self.device.close_peer(board);disconnected=True
                        action_done=True
                    if not disconnected and time.monotonic()-last_renew>=25:
                        peer.request('RENEW',dict(owner_id=owner,lease_ms=60000))
                        last_renew=time.monotonic()
                    if browser and time.monotonic()-last_browser>=10:
                        paths=('/','/api/v1/status','/api/v1/capabilities','/api/v1/jobs')
                        activity=browser.get(paths[browser_index%4]);browser_index+=1
                        record['browser_activity'].append(dict(utc_ns=time.time_ns(),response=activity))
                        self.e.event('browser_activity',activity);last_browser=time.monotonic()
                    if time.monotonic()-last_info>=10:
                        self.info(board);last_info=time.monotonic()
                    if status['state'] in ('complete','aborted','missed','failed'):
                        terminal=status;break
                    time.sleep(.5)
                require(terminal is not None and terminal['output_active'] is False,'no authoritative terminal inactivity')
                record['terminal']=terminal
                if disconnected:
                    require(terminal['owner_id'] in (None,owner),'foreign successor owner')
                    if terminal['owner_id']==owner:
                        self.device.close_peer(board)
                        # Same logical session is permitted to reconnect; expiry does not abort RF.
                        if before['provisioning_source']=='consumer_preclock':
                            address=before['network']['ipv4']
                            connection=__import__('socket').create_connection((address,before['lan_wtp_port']),timeout=5)
                            connection.setblocking(False)
                            context=contextlib.closing(connection);context.__enter__();fd=connection.fileno()
                        else:
                            from phase11_5_inventory import exclusive_port
                            context=exclusive_port(Path(self.device.base(board)+'-if02'));fd=context.__enter__()
                        self.device.peer_contexts[board]=context
                        peer=Peer(fd,self.e,self.device.root,timeout=5);peer.session=record['session_id']
                        peer.request('HELLO',dict(versions=['WTP/1'],client_name='Phase14',client_version='1'))
                        self.device.peers[board]=peer
                    else:
                        peer=self.device.peer(board);claimed=False
                if terminal['owner_id'] is None:
                    claimed=False
                if claimed:
                    peer.request('RELEASE',{});claimed=False
                after=self.idle(board)
                record['after']=after
                # No owned job remains. Offline IQ analysis may exceed the listener's
                # idle timeout, so release this transport and negotiate afresh next job.
                self.device.close_peer(board)
                # Finish the planned receiver capture with its trailing quiet.
                require(process.wait(timeout=max(1,capture_deadline-time.monotonic()))==0,'capture failed')
                metadata=json.loads((root/'capture.json').read_text())
                validate_capture(metadata,root/'capture.cf32',settings)
                require(metadata['retained_sample_count']==count,'capture planned count')
                if block:
                    from phase14.clock_loss import reject_aged_arm
                    probe=job('TONE',band,clock,uuid.uuid4().hex,5)
                    record['aged_arm_probe']=reject_aged_arm(self.device.peer(board),self.e,probe)
                    record['after']=self.idle(board)
                    self.device.close_peer(board)
                record.update(result='CONTROL_COMPLETE' if terminal['state']==('aborted' if action in ('abort','cancel') else 'complete') else 'CONTROL_FAILED',
                              capture_sha256=metadata['output']['sha256'],metadata_sha256=sha256(root/'capture.json'))
            except BaseException as error:
                record.update(result='FAILED',error=repr(error))
                try:
                    current=self.device.info(board)['status']
                    if current.get('job_id')==value['job_id'] and current['state'] in ('loaded','armed','running'):
                        self.device.console(board,'ABORT')
                    current=self.device.info(board)['status']
                    require(current['output_active'] is False,'cleanup output uncertain')
                    record['cleanup']=current
                    if current.get('owner_id')==owner:
                        peer.request('RELEASE',{});claimed=False
                    record['cleanup']=self.device.info(board)['status']
                except BaseException as cleanup:
                    record['cleanup_error']=repr(cleanup)
                raise
            finally:
                try:
                    if block:block.close()
                finally:
                    try:
                        if process and process.poll() is None:
                            os.killpg(process.pid,signal.SIGTERM)
                            try:process.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
                    finally:
                        record['session_id']=peer.session
                        save(root/'physical.json',record)
        print(json.dumps(dict(path=str(root),result=record['result'],board=board,clock=clock,band=band,mode=mode)),flush=True)
        return root
    def close(self):
        try:
            if self.reference_before:
                from phase14_reference import gps
                restored=gps(self.reference_before['f1'])
                require(restored==self.reference_before,'GPSDO settings restoration')
                self.e.event('reference_restored',restored)
                self.reference_before=None
        finally:
            self.device.close()
            if self.lock:self.lock.close()
            self.e.events.close()
