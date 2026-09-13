"""Distinguish C0's retained target allocation panic from transport symptoms."""
import json
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_r3_capacity_probe import BOOT, SOURCE, SERIAL, DEVICE, B_SERIAL, B_DEVICE, HOST_BOOT
from phase11_5_r3_capacity_plan import wtp_capacity_frame
from phase11_5_pilot import Decoder
from phase11_5_pilot_supervisor import idle, configuration
from audit_phase11_5_r3_capacity_probe import rows

PACKET='e5b9d24bea51101d3344e4c86c56a4128c03c8d317fca47914da8834dc41493c'
RECOVERY_BOOT='bccea7c09794539c4f64bc22b0e76c56'
SESSIONS={'a':'53869c401f4a44b4b0836ccd6dec1ded','b':'cb6884bbee184f79b670f7950f9d81ea'}


def audit(base):
    root=base/'evidence'
    require(digest(root/'packet.json')==PACKET,'Different C0 packet')
    packet=json.loads((root/'packet.json').read_text())
    for name,sha in packet['stage_sha256'].items():require(digest(root/name)==sha,'C0 executed helper changed')
    values={}
    for label in ('before-a','before-b','reconcile-a','reconcile-b'):
        b=label.endswith('-b');reconcile=label.startswith('reconcile')
        path=(base if reconcile else root)/(label+'.stdout')
        session=SESSIONS['b' if b else 'a'] if reconcile else packet['b_inventory_session_id' if b else 'inventory_session_id']
        value=audit_inventory(path,dict(serial=B_SERIAL if b else SERIAL,device_id=B_DEVICE if b else DEVICE),
                              session,packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not path.with_suffix('.stderr').read_bytes(),'C0 reconciliation stderr')
        values[label]=value
        if label!='reconcile-a':idle(value)
        require(value['info']['revision']==('dbf1d86f0885-dirty' if b else SOURCE[:12]),'C0 source')
    before,after=values['before-a'],values['reconcile-a']
    require(before['wtp']['STATUS']['boot_id']==BOOT and after['wtp']['STATUS']==dict(
        boot_id=RECOVERY_BOOT,state='empty',output_active=False,owner_id=None,job_id=None,terminal_records=[]),
        'C0 changed boot and current authority')
    require(after['info']['recovery_boot'] is True and after['info']['fault_stage']==5 and
            after['info']['fault_hash']==3833354787 and after['info']['fault_pc']==after['info']['fault_status']==0 and
            after['info']['status']['state']=='empty' and after['info']['status']['output_active'] is False,
            'C0 allocation panic not proved')
    old_config,old_network=configuration(before)
    new_config,new_network=configuration(after)
    require(old_config==new_config and old_network['station_mac']=='88:a2:9e:0a:60:df' and
            new_network==dict(old_network,station_mac='') and after['info']['network']['initialized'] is False,
            'C0 saved fields or expected recovery-network state changed')
    require(configuration(values['before-b'])==configuration(values['reconcile-b']),'C0 B configuration')
    require(values['before-b']['wtp']['STATUS']==values['reconcile-b']['wtp']['STATUS'] and
            values['before-b']['info']['status']['boot_id']=='feffcd075ab6cb0b74e7e0c2fde6c87f','C0 B changed')
    trace=rows(root/'capacity.jsonl')
    require([r['kind'] for r in trace]==['start','wtp_tx','wtp_rx','wtp_rx','wtp_rx','wtp_message','capacity_tx'] and
            trace[0]['value']=={'packet_sha256':PACKET},'C0 failure point differs')
    hello=decode_frame(bytes.fromhex(trace[1]['value']['hex']))
    require(hello==trace[1]['value']['request'] and hello['op']=='HELLO' and
            hello['session_id']==packet['peer_session_id'],'C0 HELLO wire')
    decoder=Decoder();replies=[]
    for row in trace[2:5]:replies.extend(decoder.feed(bytes.fromhex(row['value']['hex'])))
    require(not decoder.buffer and replies==[trace[5]['value']] and replies[0]['ok'] is True and
            replies[0]['request_id']==hello['request_id'] and replies[0]['session_id']==hello['session_id'] and
            replies[0]['body']['boot_id']==BOOT and replies[0]['body']['device_id']==DEVICE,'C0 initial endpoint identity')
    maximum=trace[6]['value'];wire=bytes.fromhex(maximum['hex'])
    require(wire==wtp_capacity_frame(packet['peer_session_id'],packet['maximum_request_id']) and
            decode_frame(wire)==maximum['request'] and maximum['expected_invalid_frames']==0,'C0 attempted maximum bytes')
    require(json.loads((root/'capacity-result.json').read_text())==dict(status='FAILED',rf_jobs=0,
            configuration_writes=0,wifi_cycles=0,flashes=0,error='BrokenPipeError: [Errno 32] Broken pipe',
            final_inventory_error='ValueError: C0 inventory failed: after-a'),'C0 failed result changed')
    require(not (root/'after-b.stdout').exists(),'Unexpected original C0 final B inventory')
    failed=rows(root/'after-a.stdout')
    require(failed[-1]['kind']=='failure' and 'USB EOF' in (root/'after-a.stderr').read_text(), 'C0 lost final transport')
    host=json.loads((base/'host-diagnostics.json').read_text())
    require(host['host_boot_id']==HOST_BOOT,'C0 host changed')
    kernel=[json.loads(s) for s in host['kernel'].splitlines()]
    require(kernel and all(r['_BOOT_ID']==HOST_BOOT.replace('-','') for r in kernel),'C0 foreign kernel log')
    disconnect=next(r for r in kernel if r['MESSAGE']=='usb 1-1.4: USB disconnect, device number 28')
    identity=next(r for r in kernel if r['MESSAGE']=='usb 1-1.4: SerialNumber: '+SERIAL)
    reset_ns=int(disconnect['__MONOTONIC_TIMESTAMP'])*1000
    require(trace[-1]['monotonic_ns']<reset_ns<int(identity['__MONOTONIC_TIMESTAMP'])*1000 <
            rows(base/'reconcile-a.stdout')[0]['monotonic_ns'], 'C0 reset chronology')
    return dict(status='FAILED_CONFIRMED_TARGET_ALLOCATION_PANIC',family_closed=False,packet_sha256=PACKET,
        fault_domain='FIRMWARE_ALLOCATION_PANIC',panic_format='Out of memory',panic_hash=3833354787,
        fault_stage=5,original_boot=BOOT,recovery_boot=RECOVERY_BOOT,
        attempted_payload_bytes=65536,complete_host_write_proven=False,exact_failed_allocation_known=False,
        firmware_remediation_verified=False,rf_jobs=0,rf_seconds=0,configuration_writes=0,wifi_cycles=0,flashes=0,
        final_status=after['wtp']['STATUS'],b_unchanged=True,test_configuration_retained=True,
        evidence_archive_sha256='7fea4b144454fc7c4ffe909dc61450f1078f2753f564ad4916229047602cd06d',
        evidence_archive_bytes=1085440,evidence_archive_files=84,
        diagnostic_sha256={n:digest(base/n) for n in ('reconcile-a.stdout','reconcile-a.stderr',
            'reconcile-b.stdout','reconcile-b.stderr','host-diagnostics.json')},
        harness_findings=['Original transfer did not record partial-write progress',
                          'USB cleanup could mask the primary exception',
                          'Original final inventory stopped before B when A failed'],
        limitation='Valid maximum-request attempt reached a target allocation panic; the exact allocation and full delivery are not established. No oversized request or RF was sent.')
