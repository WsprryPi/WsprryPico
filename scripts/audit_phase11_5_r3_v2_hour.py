"""Independent frozen physical hours plus native WTP/HTTPS raw-evidence audit."""
import importlib.util
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_pilot import DEVICE
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_rf import audit as audit_rf
from validate_wtp_contract import SchemaValidator

PACKET = "065cb07e6ace4261caf4ba24cb7d6e1417186d1d7c1445bae25d102b256df3b5"
PACKETS = {
    "addf150f2832d418c7f198e25edbf29bebaf21a62202fd1a9f072447c0db0da1": ("H2B", "dfcw"),
    PACKET: ("H0", "qrss"),
    "c408f5db396a50a6413334f05b7cc1eda22dab0040023454f28c435241931d41": ("H1", "fskcw"),
    "4eeb2113a40dc386f7839ae40a2e1f1d13b2da23dc86d04eb7ae0131dcfe2304": ("H2", "dfcw"),
    "c5ecb3dcf84eb61b788ede7c2481d10054831cee6c630c5ca4d9c715bc8a8c8c": ("H1A", "fskcw"),
    "dd834b829b6745d64385a4b831e96018be51edcf09dcfbc544cc6dc4d4eb82ed": ("H2A", "dfcw"),
}
PEER = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"
NAME = "wsprrypico-0a60df.local"


def journal(path):
    raw = path.read_bytes()
    require(raw.endswith(b"\n"), "Truncated journal")
    rows = [json.loads(line) for line in raw.splitlines()]
    require(rows and rows[0]["kind"] == "start" and rows[-1]["kind"] == "finish" and
            [r["sequence"] for r in rows] == list(range(len(rows))) and
            all(a["monotonic_ns"] <= b["monotonic_ns"] for a,b in zip(rows, rows[1:])),
            "Journal envelope/sequence/time")
    return rows


def native_wire(root, packet, decoder):
    require(digest(decoder) == packet["stage_sha256"]["pi/phase115_tls_observer_test.py"], "Native decoder identity")
    spec = importlib.util.spec_from_file_location("h0_native_decoder", decoder)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rows = module.decode((root / "production-tls.bin").read_bytes())
    require(all(r["version"] == "P115TLS2" for r in rows), "Native write-entry evidence")
    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/protocol/wtp-1.schema.json").read_text())
    validator = SchemaValidator(schema)
    buffers = {}; starts = {}; writes = {}; pending = {}; seen = set(); statuses = []; counts = {}; connections = set()
    for row in rows:
        kind, cid, stamp = row["kind"], row["connection_id"], row["monotonic_ns"]
        if kind == 2:
            require(row["payload"].hex() == PEER, "Native TLS actual certificate")
            connections.add(cid)
        if kind == 7: writes[cid] = stamp
        if kind == 8: writes.pop(cid, None)
        if kind == 5:
            require(not any(key[0] == cid for key in pending), "Native connection lost with request outstanding")
        if kind not in (3,4): continue
        key = (cid,kind)
        if kind == 3: starts.setdefault(key, writes.pop(cid))
        messages, buffers[key] = frames(buffers.get(key,b"") + row["payload"])
        for message in messages:
            require(not validator.errors(message,schema), "Native frame schema")
            token = (cid,message["session_id"],message.get("request_id"))
            if kind == 3:
                require(message["type"] == "request" and message["op"] in ["HELLO","CAPS","STATUS","GET_CLOCK","PING"] and
                        token not in seen and not any(k[0] == cid for k in pending), "Native mutation/retry/pipelining")
                seen.add(token); pending[token] = (message,starts[key])
                counts[message["op"]] = counts.get(message["op"],0) + 1
            elif message["type"] == "event":
                require(message["boot_id"] == packet["boot_id"] and message["event"] in ["JOB_STATE","OWNER_RELEASED"],
                        "Native foreign/fault event")
            else:
                require(message["type"] == "response" and message["ok"] is True and token in pending,
                        "Native rejected/unmatched response")
                request, began = pending.pop(token)
                require(request["op"] == message["op"] and 0 <= stamp-began <= 5_000_000_000, "Native request deadline")
                body = message["body"]
                if message["op"] in ["HELLO","STATUS"]: require(body["boot_id"] == packet["boot_id"], "Native boot")
                if message["op"] == "HELLO": require(body["device_id"] == DEVICE, "Native device")
                if message["op"] == "STATUS": statuses.append(dict(began=began,ended=stamp,value=body))
        if not buffers[key]: starts.pop(key,None)
    require(connections and statuses and not pending and not writes and not any(buffers.values()), "Incomplete native wire")
    return statuses, dict(connections=len(connections),operations=counts)


def audit(root, decoder, *, report_cadence_findings=False):
    packet_digest = digest(root/"packet.json")
    require(packet_digest in PACKETS, "Unreviewed physical hour packet")
    label, mode = PACKETS[packet_digest]
    base = audit_rf(root, packet_digest=packet_digest)
    packet = json.loads((root/"packet.json").read_text()); plan = packet["contention"]
    rf = journal(root/"rf.jsonl"); load = journal(root/"contention.jsonl")
    require(load[0]["value"] == dict(packet_sha256=packet_digest,policy=plan["policy"],binary_sha256=plan["binary_sha256"]) and
            all(r["kind"] in ["start","finish","native_status","https_status"] for r in load), "Contention provenance/failure")
    result = json.loads((root/"contention-result.json").read_text())
    require(result == load[-1]["value"] and result["status"] == "CAPTURED_REQUIRES_AUDIT" and result["native_exit"] == 0 and
            not (root/"contention-failed.json").exists(), "Contention completion")
    ready = json.loads((root/"contention-ready.json").read_text())
    require(ready["packet_sha256"] == packet_digest and ready["boot_id"] == packet["boot_id"] and
            ready["observed_monotonic_ns"] < next(r["monotonic_ns"] for r in rf if r["kind"] == "arm_pending"),
            "Native readiness before RF")
    require(len(base["jobs"]) == 1 and base["jobs"][0]["mode"] == mode and
            base["jobs"][0]["duration_ns"] == 3600_000_000_000, "Exact physical mode hour")
    job = packet["jobs"][0]; arm = next(r["monotonic_ns"] for r in rf if r["kind"] == "arm_acknowledged")
    derivation = packet['message_derivation']
    require(derivation['message']=='?'*32 and derivation['morse']=='..--..' and
            derivation['tail_ns']=='1000', 'Worst supported message derivation')
    expected=[];offset=0
    def append(duration,on,frequency):
        nonlocal offset
        event=dict(offset_ns=str(offset),duration_ns=str(duration),rf_on=on)
        if on:event['frequency_nhz']=str(frequency)
        expected.append(event);offset+=duration
    for character in range(32):
        for element,mark in enumerate('..--..'):
            append(int(derivation['dot_ns'] if mode=='dfcw' or mark=='.' else derivation['dash_ns']),
                   True,135495000000000 if mode=='dfcw' and mark=='-' else 135500000000000)
            if element<5:append(int(derivation['intra_gap_ns']),mode=='fskcw',135495000000000)
        if character<31:append(int(derivation['character_gap_ns']),mode=='fskcw',135495000000000)
    append(1000,False,0)
    require(expected==job['events'] and offset==3600000000000 and len(expected)==384,
            'Physical hour is not the declared full worst-case message')
    end = next(r["monotonic_ns"] for r in rf if r["kind"] == "job_complete")
    native, native_metrics = native_wire(root,packet,decoder)
    families = {"native_wire": (native,6_000_000_000)}
    host = []; https = []
    request = f"GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n".encode()
    for row in load:
        kind,v,stamp = row["kind"],row["value"],row["monotonic_ns"]
        if kind not in ["native_status","https_status"]: continue
        body = json.loads(bytes.fromhex(v["body_hex"]))
        require(0 <= stamp-v["began_monotonic_ns"] <= (3 if kind == "native_status" else 15)*10**9,
                "HTTP observation deadline")
        if kind == "native_status":
            require(body == v["value"], "Native HTTP body/summary")
            identity = body.get("host",{}).get("identity")
            if stamp >= ready["observed_monotonic_ns"]:
                require(identity and identity["device_id"] == DEVICE and identity["boot_id"] == packet["boot_id"],
                        "Native HTTP identity")
                host.append(dict(began=v["began_monotonic_ns"],ended=stamp,value=body["job"]))
        else:
            require(bytes.fromhex(v["request_hex"]) == request and v["status"] == 200 and v["peer_sha256"] == PEER,
                    "HTTPS request/authentication/status")
            headers = {k.lower():value for k,value in v["headers"]}
            require(int(headers["content-length"]) == len(bytes.fromhex(v["body_hex"])) and
                    body["transport"]["active"] == 2 and body["transport"]["pending"] == 0,
                    "HTTPS complete body/supported concurrency")
            https.append(dict(began=v["began_monotonic_ns"],ended=stamp,value=body["job"]))
    require(len(https) == result["https_requests"] <= plan["maximum_https_requests"], "HTTPS accounting")
    families.update(native_http=(host,6_000_000_000),https=(https,21_000_000_000))
    usb_running=[r for r in rf if r['kind']=='status' and r['value']['value']['state']=='running']
    require(usb_running,'Missing independent Running interval')
    interior_begin=usb_running[0]['monotonic_ns']+6_000_000_000
    interior_end=usb_running[-1]['monotonic_ns']-6_000_000_000
    coverage = {};cadence_findings=[]
    for name,(samples,bound) in families.items():
        selected = [s for s in samples if arm-bound <= s["began"] <= end+bound]
        # A periodic producer need not add an unscheduled request after RF ends.
        # Its last request must still be within the declared cadence of that end.
        valid_cadence=bool(selected and selected[0]["began"] <= arm and end-selected[-1]["began"] <= bound and
                all(0 < b["began"]-a["began"] <= bound for a,b in zip(selected,selected[1:])))
        active = [s for s in selected if s["value"]["state"] == "running"]
        valid_running=bool(active and active[-1]["ended"]-active[0]["began"] >= 3600_000_000_000-2*bound)
        if not valid_cadence or not valid_running:
            finding=dict(family=name,coverage_and_cadence_pass=valid_cadence,running_span_pass=valid_running,
                maximum_start_gap_ns=max((b['began']-a['began'] for a,b in zip(selected,selected[1:])),default=0),
                required_maximum_start_gap_ns=bound)
            cadence_findings.append(finding)
            require(report_cadence_findings,name+' full-hour coverage/cadence')
        for s in selected:
            value = s["value"]
            require(value["boot_id"] == packet["boot_id"] and
                    value["job_id"] in [None,job["job_id"]] and value["owner_id"] in [None,packet["owner_id"]] and
                    value["state"] in ["empty","loaded","armed","running","complete"] and
                    value["output_active"] is (value["state"] == "running"), name+" authority")
            if interior_begin<=s['began'] and s['ended']<=interior_end:
                require(value['state']=='running' and value['output_active'] is True and
                        value['job_id']==job['job_id'] and value['owner_id']==packet['owner_id'],
                        name+' disagrees with independent Running interval')
        coverage[name] = dict(status='PASS' if valid_cadence and valid_running else 'FAILED',samples=len(selected),
            max_start_gap_ns=max((b["began"]-a["began"] for a,b in zip(selected,selected[1:])),default=0))
    base.update(status=label+"_"+mode.upper()+('_PHYSICAL_HOUR_WITH_SEPARATE_CADENCE_FINDINGS' if cadence_findings else
                    "_PHYSICAL_HOUR_WITH_NOMINAL_CONTENTION_VERIFIED"),
                physical_hour_or_saturation_verified=True,physical_hour_verified=True,saturation_verified=False,
                all_contention_cadence_passed=not cadence_findings,cadence_findings=cadence_findings,
                native=native_metrics,contention_coverage=coverage,https_requests=len(https),
                message_characters=32,message_events=384,prior_terminal_expiry=terminal_expiry(root,rf))
    return base


def terminal_expiry(root, rows):
    """Bracket actual terminal TTL against independent device-monotonic INFO reads."""
    from phase11_5_pilot_supervisor import finished
    before=finished(root/'before-a.stdout','READ_ONLY_INVENTORY')
    prior=before['wtp']['STATUS']['terminal_records']
    infos=[r for r in rows if r['kind']=='info'];statuses=[r for r in rows if r['kind']=='status']
    checks=[]
    for record in prior:
        expires=int(record['ended_monotonic_ns'])+3600000000000
        present=[];absent=[];ambiguous=0
        for s in statuses:
            lower=[i for i in infos if i['monotonic_ns']<=s['value']['began_monotonic_ns']]
            upper=[i for i in infos if i['value']['began_monotonic_ns']>=s['monotonic_ns']]
            if not lower or not upper:continue
            lo=int(lower[-1]['value']['value']['status']['monotonic_now_ns'])
            hi=int(upper[0]['value']['value']['status']['monotonic_now_ns'])
            matches=[v for v in s['value']['value']['terminal_records'] if v['job_id']==record['job_id']]
            if hi<expires:
                require(matches==[record],'Prior terminal lost or changed before actual TTL')
                present.append(dict(lower_ns=lo,upper_ns=hi))
            elif lo>=expires:
                require(not matches,'Prior terminal retained beyond actual TTL')
                absent.append(dict(lower_ns=lo,upper_ns=hi))
            else:ambiguous+=1
        checks.append(dict(job_id=record['job_id'],expires_monotonic_ns=expires,
            observed_before_expiry=bool(present),observed_after_expiry=bool(absent),
            last_present_bracket=present[-1] if present else None,first_absent_bracket=absent[0] if absent else None,
            ambiguous_boundary_samples=ambiguous,scope='Existing terminal TTL only; not capacity/LRU/replay/reclamation'))
    return checks


def audit_capacity(root, decoder, packet_digest):
    """Existing RF/native audits plus three bounded HTTP body boundary exchanges."""
    from phase11_5_r3_capacity_plan import http_capacity_cases
    from phase11_5_browser_jobs import admit_snapshot
    base=audit_rf(root,packet_digest=packet_digest)
    packet=json.loads((root/'packet.json').read_text());cases=http_capacity_cases(packet['http_capacity']['seed'])
    require(packet['http_capacity']['cases']==cases,'Frozen capacity HTTP cases')
    rf=journal(root/'rf.jsonl');load=journal(root/'contention.jsonl');plan=packet['contention'];job,=packet['jobs']
    native,metrics=native_wire(root,packet,decoder)
    require(metrics['connections']==1,'One persistent native TLS/WTP connection')
    ready=json.loads((root/'contention-ready.json').read_text())
    require(ready['packet_sha256']==packet_digest and ready['boot_id']==packet['boot_id'] and
        ready['observed_monotonic_ns']<next(r['monotonic_ns'] for r in rf if r['kind']=='arm_pending') and
        not (root/'contention-failed.json').exists(),'Native readiness and no contention failure')
    for exchange in base['wtp_capacity']:
        before=[s for s in native if s['ended']<=exchange['began_ns']]
        after=[s for s in native if s['began']>=exchange['ended_ns']]
        require(before and after,'Native observations bracket USB capacity')
        for s in [before[-1],after[0]]:
            v=s['value']
            require(v['boot_id']==packet['boot_id'] and v['state']=='running' and v['output_active'] is True and
                v['owner_id']==packet['owner_id'] and v['job_id']==job['job_id'],
                'Independent native owned Running around USB capacity')
    arm=next(r['monotonic_ns'] for r in rf if r['kind']=='arm_acknowledged')
    end=next(r['monotonic_ns'] for r in rf if r['kind']=='job_complete')
    require(native[0]['began']<arm and native[-1]['ended']>=end-6_000_000_000 and
        all(0<b['began']-a['began']<=6_000_000_000 for a,b in zip(native,native[1:])),'Native authority coverage')
    for s in native:
        v=s['value'];require(v['boot_id']==packet['boot_id'] and v['job_id'] in [None,job['job_id']] and
            v['owner_id'] in [None,packet['owner_id']] and v['output_active'] is (v['state']=='running'),'Native authority')
    require(load[0]['value']==dict(packet_sha256=packet_digest,policy=plan['policy'],binary_sha256=plan['binary_sha256']) and
        all(r['kind'] in ['start','finish','native_status','https_status','http_capacity_admission','http_tx',
            'http_write_complete','http_response'] for r in load),'Finite HTTP capture without failures')
    selected=[r for r in load if r['kind'].startswith('http_')]
    require([r['kind'] for r in selected]==['http_capacity_admission','http_tx','http_write_complete','http_response']*3,
        'Exactly three HTTP capacity exchanges')
    observations={}
    for r in rf:
        if r['kind'] in ['status','info','console_tx']:observations[(r['kind'],r['monotonic_ns'])]=r['value']
    out=[]
    for case,offset in zip(cases,range(0,12,4)):
        admission,tx,write,reply=selected[offset:offset+4];snap=admission['value']
        require(snap['case']==case['label'] and tx['value']==case and
            write['value']==dict(label=case['label'],bytes=len(bytes.fromhex(case['wire_hex']))),'Exact complete HTTP write')
        require(0<=admission['monotonic_ns']-snap['guarded_at_ns']<=100_000_000,'HTTP admission publication delay')
        pending=snap['pending_info']
        require(observations[('console_tx',pending['monotonic_ns'])]==pending['value'],'Raw in-flight INFO request')
        for kind,maxage in [('status',6_000_000_000),('info',2_000_000_000)]:
            record=snap[kind]
            require(observations[(kind,record['monotonic_ns'])]==record['value'] and
                record['packet_sha256']==packet_digest,'Independent HTTP admission evidence')
            admit_snapshot(record,snap['guarded_at_ns'],maxage,packet_digest,pending if kind=='info' else None,
                'INFO' if kind=='info' else 'STATUS')
        status=snap['status']['value']['value'];info=snap['info']['value']['value']
        require(status['boot_id']==info['status']['boot_id']==packet['boot_id'] and status['state']=='running' and
            status['output_active'] is True and status['owner_id']==packet['owner_id'] and status['job_id']==job['job_id'],
            'HTTP boundary during authoritative Running RF')
        v=reply['value'];raw=bytes.fromhex(v['body_hex']);body=json.loads(raw)
        headers={k.lower():val for k,val in v['headers']}
        require(v['label']==case['label'] and v['peer_sha256']==PEER and v['status']==case['expected_status'] and
            len(raw)<=131072 and int(headers['content-length'])==len(raw) and
            0<=reply['monotonic_ns']-v['began_monotonic_ns']<=15_000_000_000,'HTTP identity/body/deadline')
        if case['error_code']:
            require(body['error']['code']==case['error_code'],'HTTP-layer rejection')
        else:
            request=json.loads(bytes.fromhex(case['wire_hex']).split(b'\r\n\r\n',1)[1])
            require(body['ok'] is True and body['request_id']==request['request_id'] and
                body['result']['device_id']==DEVICE and body['result']['boot_id']==packet['boot_id'],
                'Supported HELLO, exact request and recovery identity')
        following=next(r for r in rf if r['kind']=='status' and r['value']['began_monotonic_ns']>reply['monotonic_ns'])
        require(following['value']['value']['state']=='running' and following['value']['value']['owner_id']==packet['owner_id'],
            'RF and owner survive HTTP boundary exchange')
        out.append(dict(label=case['label'],declared_bytes=case['declared_body_bytes'],offered_bytes=case['offered_body_bytes'],
            response_status=v['status'],began_ns=v['began_monotonic_ns'],ended_ns=reply['monotonic_ns']))
    ordinary=[r for r in load if r['kind']=='https_status']
    for r in ordinary:
        v=r['value'];body=json.loads(bytes.fromhex(v['body_hex']))
        require(v['status']==200 and v['peer_sha256']==PEER and body['job']['boot_id']==packet['boot_id'] and
            body['transport']['active']==2 and body['transport']['pending']==0,'Ordinary native plus HTTPS concurrency')
    result=json.loads((root/'contention-result.json').read_text())
    require(result==load[-1]['value']==dict(status='CAPTURED_REQUIRES_AUDIT',https_requests=len(ordinary)+3,native_exit=0) and
        result['https_requests']<=plan['maximum_https_requests'],'Finite contention accounting')
    base.update(status='RF_WTP_HTTP_CAPACITY_COMPONENTS_VERIFIED',http_capacity=out,native=metrics,
        limitations=['No USB unread-output pressure or retention/reclamation credit'])
    return base
