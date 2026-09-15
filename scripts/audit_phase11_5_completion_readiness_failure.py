"""Audit the immutable readiness-publication failure; no capacity acceptance."""
import json
import importlib.util

from phase11_5_device_management import digest

from audit_phase11_5_completion_p1_failure import inputs
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_hour import journal, native_wire
from audit_phase11_5_r3_v2_rf import timing
from phase11_5_inventory import require, loads_console
from phase11_5_r3_v2_rf import validate_info
from phase11_5_rf_reservation import BOARDS, inactive
from validate_wtp_contract import SchemaValidator

PACKET = '26e58c73da189aa1d9aecae6b410e392ca2957499632e38caa3b05f14c3d8104'


FOLLOWUP = 'e14d253bca421dd9f49824333ae1907d30fa4a3e1716474efef2ddad5eeedaf4'


def failed_native(root, packet):
    path=root/'pi/phase115_tls_observer_test.py'
    require(digest(path)==packet['stage_sha256']['pi/phase115_tls_observer_test.py'], 'Native decoder identity')
    spec=importlib.util.spec_from_file_location('failed_native_decoder',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=module.decode((root/'production-tls.bin').read_bytes())
    schema=json.loads((root/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    buffers={3:b'',4:b''};pending=None;replies=[];closed=[];certificates=[]
    for row in rows:
        require(row['version']=='P115TLS2','Native capture version')
        kind=row['kind']
        if kind==2:
            certificates.append(row['payload'].hex())
        elif kind==5:
            closed.append(row)
            require(pending is not None and pending['op']=='STATUS','Closure with STATUS outstanding')
        elif kind in (3,4):
            require(not closed,'No traffic after captured native closure')
            messages,buffers[kind]=frames(buffers[kind]+row['payload'])
            for message in messages:
                require(not validator.errors(message,schema),'Native complete message schema/CRC')
                if kind==3:
                    require(pending is None and message['op'] in ('HELLO','CAPS','STATUS'), 'Native read-only serialized requests')
                    pending=message
                else:
                    require(pending is not None and message['type']=='response' and message['ok'] is True and
                            all(message[k]==pending[k] for k in ('op','request_id','session_id')), 'Native matched successful prefix')
                    if message['op'] in ('HELLO','STATUS'):
                        require(message['body']['boot_id']==packet['boot_id'],'Native boot')
                    replies.append(message);pending=None
    require(certificates==['06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'] and
            len(closed)==1 and len(replies)==8 and pending['request_id']=='00000000000000000000000000000009' and
            not buffers[3] and buffers[4].hex()=='5754504601010000000000ff8c4e21fa',
            'Exact outstanding STATUS and incomplete 255-byte frame; no payload/CRC acceptance')
    snapshots=[r['value']['value'] for r in journal(root/'contention.jsonl') if r['kind']=='native_status']
    require(any(v['host']['ready'] is False and v['host']['session_phase']=='disconnected' and
                v['host']['identity']['boot_id']==packet['boot_id'] and v['job'] is None for v in snapshots),
            'Cached identity survives failed authoritative session')
    return dict(status='FAILED_INCOMPLETE_FRAME',complete_successful_responses=8,
                outstanding_request_id=pending['request_id'],declared_payload_bytes=255,received_payload_bytes=0,
                connection_closed_monotonic_ns=closed[0]['monotonic_ns'],full_native_coverage=False)


def audit(root):
    sha=digest(root/'packet.json'); require(sha in (PACKET,FOLLOWUP), 'Exact reviewed failure')
    followup=sha==FOLLOWUP
    packet, values = inputs(root, sha)
    rows = journal(root/'rf.jsonl')
    require(rows[0]['value']['packet_sha256'] == sha, 'Exact failed trace')
    schema = json.loads((root/'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    pending = None; wire = b''; replies = []; exchanges = []
    console_pending = None; console = b''; decoded = None; info = []
    for row in rows:
        kind, value, stamp = row['kind'], row['value'], row['monotonic_ns']
        if kind == 'console_tx':
            require(console_pending is None and not console and decoded is None and
                    bytes.fromhex(value['hex']) == b'INFO\n', 'Single read-only Console request')
            console_pending = stamp
        elif kind == 'console_rx':
            require(console_pending is not None, 'Solicited Console response')
            console += bytes.fromhex(value['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n') == 1 and
                        stamp-console_pending <= 5_000_000_000, 'Console framing/deadline')
                decoded = loads_console(console.decode().strip()); console = b''; console_pending = None
        elif kind == 'info':
            require(decoded == value['value'], 'Raw INFO agrees with summary')
            validate_info(decoded, values['before-a'], packet); info.append(row); decoded = None
        elif kind == 'wtp_tx':
            messages, left = frames(bytes.fromhex(value['hex']))
            require(pending is None and not left and messages == [value['request']] and
                    not validator.errors(messages[0], schema), 'USB request framing/schema')
            pending = (messages[0], stamp)
        elif kind == 'wtp_rx':
            messages, wire = frames(wire + bytes.fromhex(value['hex']))
            for message in messages:
                require(not validator.errors(message, schema) and
                        message['session_id'] == packet['peer_session'], 'USB response schema/session')
                if message['type'] == 'event':
                    require(message['boot_id'] == packet['boot_id'] and
                            message['event'] in ('JOB_STATE','OWNER_RELEASED'), 'No fault event')
                else:
                    require(pending is not None and message['ok'] is True and
                            all(message[k] == pending[0][k] for k in ('op','request_id','session_id')) and
                            stamp-pending[1] <= 5_000_000_000, 'USB matched response/deadline')
                    exchanges.append(dict(request=pending[0], response=message,
                                          started_ns=pending[1], finished_ns=stamp)); pending = None
                replies.append(message)
    require(not wire and pending is None and not console and console_pending is None and decoded is None and
            replies == [r['value'] for r in rows if r['kind'] == 'wtp_message'], 'Complete raw observations')
    mutations = [e for e in exchanges if e['request']['op'] not in ('HELLO','STATUS','GET_CLOCK','RENEW')]
    require([e['request']['op'] for e in mutations] == (['CLAIM','LOAD','ARM','RELEASE'] if followup else ['CLAIM','LOAD','ARM']), 'One finite launch, no retry')
    load, arm = mutations[1:3]
    job, = packet['jobs']
    require(load['request']['body'] == job and arm['request']['body']['job_id'] == job['job_id'], 'Exact maximum job')
    adjustments = load['response']['body']['adjustments']
    require(len(adjustments) == 512 and all(a == dict(event_index=n,
        requested_frequency_nhz=str(135500000000000 if n%2 == 0 else 135495000000000),
        realized_frequency_nhz=str(135500002652407 if n%2 == 0 else 135494990274310))
        for n,a in enumerate(adjustments)), 'All exact maximum LOAD adjustments')
    require(not any(r['kind'].startswith('capacity_') for r in rows) and
            (followup or not (root/'native-observation.json').exists()), 'Zero WTP capacity offers')
    gaps = [b['value']['began_monotonic_ns']-a['value']['began_monotonic_ns'] for a,b in zip(info,info[1:])]
    require((128 <= len(info) <= 300 if followup else len(info) == 300) and all(0 < gap <= 2_000_000_000 for gap in gaps), 'Complete independent Console cadence')
    metrics = timing(packet, [dict(job=job, start_utc_ns=arm['request']['body']['start_utc_ns'],
        monotonic_ns=arm['started_ns'], request=arm['request']['body'], acknowledgment=arm['response']['body'])], rows)
    if followup:
        native_metrics = failed_native(root, packet)
    else:
        native, native_metrics = native_wire(root, packet, root/'pi/phase115_tls_observer_test.py')
        require({'loaded','armed','running','complete'} <= {s['value']['state'] for s in native}, 'Native lifecycle coverage')
    contention = journal(root/'contention.jsonl')
    require(not any(r['kind'] in ('http_tx','https_status') for r in contention), 'Zero HTTP probe/status offers')
    final = values['final-a']['wtp']['STATUS']
    require(final['state'] == ('empty' if followup else 'complete') and final['job_id'] == (None if followup else job['job_id']) and
            any(r['job_id']==job['job_id'] and r['state']=='complete' and r['output_active'] is False for r in final['terminal_records']) and
            final['output_active'] is False and final['owner_id'] is None, 'Authoritative completion')
    for phase, name, state in [('before','acquired','HELD'),('final','released','RELEASED')]:
        r = json.loads((root/('rf-reservation-'+name+'.json')).read_text())
        require(r['packet_sha256'] == sha and r['state'] == state and
                r['boards'] == inactive({b:values[phase+'-'+b] for b in BOARDS}), 'Shared reservation reconciliation')
    result = json.loads((root/'rf-result.json').read_text())
    require(result == rows[-1]['value'] and result['status'] == 'STOPPED_REQUIRES_DIAGNOSIS' and
            result['armed_jobs'] == [job['job_id']] and result['completed_jobs'] == ([job['job_id']] if followup else []) and
            result['renewals'] == (3 if followup else 0) and result['rf_duration_ns_charged'] == 128_000_000_000,
            'Preserved failed result and full RF charge')
    return dict(status='NATIVE_CONNECTION_FAILURE_AND_FINITE_COMPLETION_CONFIRMED' if followup else 'READINESS_FAILURE_AND_FINITE_COMPLETION_CONFIRMED', packet_sha256=sha,
        capacity_acceptance=False, family_closed=False, rf_jobs_charged=1, rf_seconds_charged=128,
        console_samples=len(info), maximum_console_start_gap_ns=max(gaps), native=native_metrics,
        jobs=metrics, final_a=final, final_b=values['final-b']['wtp']['STATUS'],
        configurations_preserved=True, schedules_disabled=True, reservation_released=True,
        failures=result['faults'], maximum_allocator_peak_bytes=max(r['value']['value']['allocator_peak_bytes'] for r in info))
