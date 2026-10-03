#!/usr/bin/env python3
"""Bounded, injected ordinary CONFIG/STATUS serialization measurement.

No connection, flash or job operation happens on import. The caller owns peer
setup, native journal preconditioning, complete readback and restoration.
"""
import copy
import json
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from validate_wtp_contract import crc32c, loads_strict
from phase12_engineering_composition import guard
from phase12_recovery_orchestrator import DEVICE, require
from phase12_composition_audit import counter

CARRIERS = ('usb', 'ble', 'tls')


def decode(wire):
    require(type(wire) is bytes and len(wire) >= 16, 'actual complete WTP wire required')
    magic, size, checksum = struct.unpack('>8sII', wire[:16])
    require(magic == b'WTPF\x01\x01\x00\x00' and 0 < size <= 65536 and
            len(wire) == size+16 and crc32c(wire[16:]) == checksum, 'WTP frame CRC/length')
    return loads_strict(wire[16:])


def station_config(config):
    require(config['enabled'] is False and config['version'] == 1, 'disabled saved CONFIG required')
    result = copy.deepcopy(config)
    old = result['station']['power_dbm']
    require(type(old) is int, 'station metadata power')
    result['station']['power_dbm'] = 30 if old == 27 else 27
    return result


def canonical_config(config):
    result={key:config[key] for key in ('version','enabled')}
    result['station']={key:config['station'][key] for key in ('callsign','locator','power_dbm')}
    result['wifi']={key:config['wifi'][key] for key in ('ssid','password','ntp_ipv4') if key in config['wifi']}
    result['schedules']=[{key:item[key] for key in ('period_s','phase_s')} for item in config['schedules']]
    if 'expires_utc_s' in config:result['expires_utc_s']=config['expires_utc_s']
    require(result==config,'unknown CONFIG fields must not be dropped')
    return result


def assess(records, before, after):
    """Validate independently emitted target critical-section pairs."""
    open_spans = {}; seen_spans=set(); spans = []; previous = before; seq = 0
    for record in records:
        require(counter(record['seq'], 'sequence') == seq+1, 'trace sequence continuity')
        seq += 1
        stamp = counter(record['monotonic_ns'], 'trace time')
        require(previous <= stamp <= after, 'trace clock/bookend mismatch')
        previous = stamp
        span = counter(record['span'], 'span')
        if record['phase'] == 'begin':
            require(span==seq and span not in seen_spans and record['outcome'] == 'pending', 'trace begin')
            seen_spans.add(span)
            open_spans[span] = record
        else:
            require(record['phase'] == 'end' and span in open_spans and
                    record['outcome'] == 'complete', 'missing/failed trace pair')
            begin = open_spans.pop(span)
            require(begin['kind'] == record['kind'], 'trace pair kind')
            spans.append((record['kind'], counter(begin['monotonic_ns'], 'begin'), stamp,
                          counter(begin['seq'],'begin sequence'),counter(record['seq'],'end sequence')))
    require(not open_spans, 'open trace spans')
    statuses = [s for s in spans if s[0] == 'status']
    flash = [s for s in spans if s[0] in ('standalone_erase', 'standalone_program')]
    require(len(statuses) == 60 and len(statuses)+len(flash) == len(spans), 'trace scope/count')
    require(sum(s[0] == 'standalone_erase' for s in flash)==1 and
            sum(s[0] == 'standalone_program' for s in flash)==8, 'exact one erase/eight programs required')
    require(all((b <= c or d <= a) and (ae < cb or ce < ab) for _, a, b, ab, ae in statuses for _, c, d, cb, ce in flash),
            'STATUS handling overlaps flash critical section')
    require(any(b <= min(s[1] for s in flash) for _, a, b, _, _ in statuses) and
            any(a >= max(s[2] for s in flash) for _, a, b, _, _ in statuses), 'before/after flash STATUS')
    return spans


def run(plan, config, observe_info, console, exchanges, *, clock=time.monotonic):
    """exchanges[carrier](op, body, deadline) returns exact request/response bytes.

    console(command, deadline) returns decoded JSON and its actual JSON bytes.
    Each carrier must already be authenticated to the exact same selected boot.
    Callbacks must enforce the absolute deadline, including all socket/BLE waits.
    CONFIG is attempted once, and uncertainty propagates to caller restoration.
    """
    require(set(exchanges) == set(CARRIERS), 'three prepared independent peers')
    start = clock(); deadline = start+120; evidence = []; lock = threading.Lock()
    sessions = {}; requests = set(); began = False
    def check():
        require(clock() < deadline, '120 second measurement deadline')
    def command(text):
        check(); reply, raw = console(text, deadline)
        require(type(raw) is bytes and loads_strict(raw) == reply and reply.get('ok') is True,
                'actual successful console response')
        evidence.append({'console': text, 'response_hex': raw.hex()})
        return reply
    def identity(reply):
        require(reply['schema'] == 'wsprrypico-activity-trace/1' and
                reply['device_id'] == DEVICE and reply['boot_id'] == plan['boot_id'] and
                reply['revision'] == plan['source_commit'][:12], 'trace identity')
    def exchange(carrier, op):
        check(); begin = clock()
        reqwire, respwire = exchanges[carrier](op, {}, deadline)
        end = clock(); check(); request = decode(reqwire); response = decode(respwire)
        require(request['protocol'] == response['protocol'] == 'WTP/1' and
                request['type'] == 'request' and response['type'] == 'response' and
                request['op'] == response['op'] == op and response['ok'] is True,
                'actual correlated successful WTP operation')
        for key in ('session_id', 'request_id'):
            require(request[key] == response[key], 'WTP correlation')
        with lock:
            require(request['request_id'] not in requests, 'duplicate request ID')
            requests.add(request['request_id'])
            sessions.setdefault(carrier, request['session_id'])
            require(sessions[carrier] == request['session_id'], 'carrier session changed')
            evidence.append({'carrier':carrier, 'operation':op, 'start_s':begin-start,
                             'end_s':end-start, 'request_hex':reqwire.hex(), 'response_hex':respwire.hex()})
        body = response['body']
        if op == 'STATUS':
            require(body['boot_id'] == plan['boot_id'] and body['state'] == 'empty' and
                    body['owner_id'] is None and body['job_id'] is None and
                    body['output_active'] is False, 'empty unowned inactive STATUS')
        return body
    info, raw = observe_info(); require(loads_strict(raw) == info, 'actual INFO bytes')
    guard(info, plan, empty=True)
    new_config = station_config(config)
    try:
        begin = command('ACTIVITYTRACE BEGIN '+DEVICE); identity(begin)
        require(begin['enabled'] is True, 'trace enabled'); began = True
        epoch = begin['capture_epoch']
        pre = [exchange(c, 'GET_CLOCK') for c in CARRIERS]
        for c in CARRIERS: exchange(c, 'STATUS')
        gate = threading.Event(); stop = threading.Event()
        def worker(c):
            gate.wait(timeout=max(0, deadline-clock()))
            for _ in range(18):
                if stop.is_set(): return
                exchange(c, 'STATUS')
                time.sleep(min(.02,max(0,deadline-clock())))
        pool = ThreadPoolExecutor(max_workers=3)
        tasks = [pool.submit(worker,c) for c in CARRIERS]
        gate.set(); config_start = clock()-start
        try:
            saved = command('CONFIG '+json.dumps(canonical_config(new_config),separators=(',',':')))
            require(saved.get('enabled') is False, 'CONFIG remains disabled')
            config_end = clock()-start
            for task in tasks: task.result(timeout=max(0,deadline-clock()))
        finally:
            stop.set()
            # No peer may keep emitting STATUS after END or caller restoration.
            try:
                for task in tasks:
                    try:
                        task.result(timeout=max(0,deadline-clock()))
                    except Exception:
                        pass # Original failure propagates after every worker is joined.
            finally:
                pool.shutdown(wait=True,cancel_futures=True)
        for c in CARRIERS: exchange(c, 'STATUS')
        post = [exchange(c, 'GET_CLOCK') for c in CARRIERS]
        ended = command('ACTIVITYTRACE END '+DEVICE); identity(ended)
        require(ended['enabled'] is False and ended['capture_epoch'] == epoch, 'trace end binding')
        began = False
        records = []; cursor = 0
        for _ in range(8):
            page = command('ACTIVITYTRACE READ '+str(cursor)); identity(page)
            require(page['capture_epoch'] == epoch and page['enabled'] is False and
                    page['overflow'] is False and page['clock_regressed'] is False and
                    counter(page['dropped_spans'],'dropped') == 0 and
                    counter(page['open_spans'],'open') == 0, 'complete unoverflowed capture')
            records.extend(page['records']); next_cursor = counter(page['next_cursor'],'cursor')
            require(next_cursor >= cursor and (not page['more'] or next_cursor > cursor), 'cursor progress')
            cursor = next_cursor
            if not page['more']:
                require(cursor == counter(page['record_count'],'count') == len(records), 'trace complete')
                break
        else: raise RuntimeError('bounded trace pagination exhausted')
        spans = assess(records, max(counter(p['monotonic_now_ns'],'preclock') for p in pre),
                       min(counter(p['monotonic_now_ns'],'postclock') for p in post))
        statuses = [e for e in evidence if e.get('operation') == 'STATUS']
        require(all(any(e['carrier'] == c and e['start_s'] <= config_end and
                        config_start <= e['end_s'] for e in statuses) for c in CARRIERS),
                'each carrier must actually attempt STATUS around CONFIG')
        info, raw = observe_info(); require(loads_strict(raw) == info, 'post INFO wire'); guard(info,plan,empty=True)
        return {'schema':'phase12-engineering-flash-status/1', 'review_required':True,
                'scope':'source1 saved station metadata; no profile activation or RF timing qualification',
                'elapsed_s':clock()-start, 'config':new_config, 'exchanges':evidence,
                'trace':records, 'spans':spans, 'status_samples':60,
                'sample_max_round_trip_s':max(e['end_s']-e['start_s'] for e in statuses)}
    finally:
        if began:
            command('ACTIVITYTRACE END '+DEVICE)


def dispatch(plan, config, peers, observe_info, console):
    """Actual dispatcher seam: peers supply captured actual wire, never rebuilt frames.

    Existing USB/BLE/TLS peer setup must be done by the authorized parent. A
    decoded-only peer is rejected: wire_exchange must retain actual transport
    writes and CRC-valid correlated received bytes, with the absolute deadline.
    """
    require(all(callable(getattr(peers[c], 'wire_exchange', None)) for c in CARRIERS),
            'actual wire capture adapters required')
    return run(plan, config, observe_info, console,
               {c: peers[c].wire_exchange for c in CARRIERS})
