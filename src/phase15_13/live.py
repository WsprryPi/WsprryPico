"""Finite Linux runner using the existing identity-bound WTP/receiver adapters."""
import copy
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import uuid

from led_closeout.runner import require, sha256
from phase14.live import CAPTURE, Rig, save
from phase14.plan import BOARDS, accepted_events, validate_capture, capture_elapsed_limit, load_workspace_bytes
from phase15_13.plan import CLOCK, RATE, FREQUENCIES, plan, validate


def consecutive_frames(observed,records):
    require(len(observed)==len(records)==3,'three complete WSPR frame records required')
    starts=[int(r['arm']['start_utc_ns']) for r in records]
    local=[int(r['arm']['start_monotonic_ns']) for r in records]
    require(all(starts[i+1]-starts[i]==120000000000 for i in range(2)),
            'WSPR requested UTC starts must be consecutive 120-second slots')
    require(all(abs(right-left-110.592)<.02 for left,right in observed),
            'complete 110.592-second WSPR envelopes required')
    # SNTP observations reproject each new complete job onto the monotonic
    # timer. Consecutive UTC slots therefore need not be exactly 120 s apart
    # on the uncalibrated receiver axis. Retain both axes. WTP permits launch
    # within the requested UTC second, rather than imposing a new 50 ms gate.
    errors=[observed[i+1][0]-observed[i][0]-(local[i+1]-local[i])/1e9 for i in range(2)]
    require(all(abs(error)<1.02 for error in errors) and
            all(observed[i+1][0]-observed[i][1]>.5 for i in range(2)),
            'consecutive frame timing differs from local ARM projections')
    return dict(requested_start_utc_ns=[str(v) for v in starts],
                projected_start_monotonic_ns=[str(v) for v in local],observed_intervals_s=observed,
                interframe_projection_error_s=errors,
                timing_scope='Consecutive requested UTC slots; observed local projection, full envelopes and quiet gaps. No calibrated absolute UTC assertion.')


def cleanup_owned(rig,owner,job_id):
    current=rig.info('A')['status']
    if current['owner_id']==owner:
        if current['state'] in ('loaded','armed','running'):
            require(current['job_id']==job_id,'unexpected successor job; preserve authority')
        # An unsuccessful LOAD can leave an empty claim and a reset TCP
        # connection. The existing identity-bound local ABORT clears that
        # claim without attempting RELEASE on a broken transport.
        if current['state']!='failed':
            rig.device.console('A','ABORT')
            require(rig.info('A')['status']['owner_id'] is None,'local cleanup retained owner')
        rig.device.close_peer('A')
    require(rig.info('A')['status']['output_active'] is False,'failure cleanup output uncertain')


def split_wspr(directory, records, frequency):
    """Lossless capture slices; retain the full parent and exact sample ranges."""
    import numpy as np
    from measure_rf_bench import measure
    metadata = json.loads((directory/'capture.json').read_text())
    iq = np.memmap(directory/'capture.cf32', dtype='<c8', mode='r')
    observed = measure(iq, RATE, FREQUENCIES[records[0]['band']]-25000,
                       base_hz=frequency)['intervals_s']
    sequence=consecutive_frames(observed,records)
    save(directory/'frame-sequence.json',sequence)
    edges = [0] + [round((observed[i][1]+observed[i+1][0])/2*RATE) for i in range(2)] + [len(iq)]
    for i, record in enumerate(records):
        child = directory.parent/record['window_id']
        child.mkdir(mode=0o700)
        np.asarray(iq[edges[i]:edges[i+1]]).tofile(child/'capture.cf32')
        meta = copy.deepcopy(metadata)
        meta['evidence_type']='derived_capture_slice'
        meta['capture_id']=record['window_id']
        meta['requested_sample_count'] = meta['retained_sample_count'] = edges[i+1]-edges[i]
        meta['output'].update(path=str(child/'capture.cf32'),sha256=sha256(child/'capture.cf32'),
                              size_bytes=(edges[i+1]-edges[i])*8)
        meta['derivation'] = dict(parent_capture_sha256=metadata['output']['sha256'],
                                  parent_metadata_sha256=sha256(directory/'capture.json'),
                                  parent_path=str(directory), sample_range=edges[i:i+2],
                                  operation='unchanged contiguous CF32 sample slice',
                                  timestamps_describe='full parent receiver acquisition',
                                  frame_sequence_sha256=sha256(directory/'frame-sequence.json'))
        save(child/'capture.json', meta)
        record.update(capture_sha256=meta['output']['sha256'],
                      metadata_sha256=sha256(child/'capture.json'), parent=meta['derivation'])
        save(child/'physical.json', record)
        validate_capture(meta, child/'capture.cf32', record['receiver_settings'])
    return [directory.parent/r['window_id'] for r in records]


def group(rig, selected, image_hash, source_revision):
    band, mode = selected['band'], selected['mode']
    directory = rig.e.root/(band+'-'+mode)
    directory.mkdir(mode=0o700)
    before = rig.idle('A')
    rig.idle('B')
    # Use the existing preparation/authority reserve estimate before capture,
    # CLAIM or LOAD. Closed sessions/replies retain bounded cache lifetimes;
    # waiting is quiet and never retries an uncertain or rejected mutation.
    rig.device.close_peer('A')
    needed=max(load_workspace_bytes(w['job']) for w in selected['windows'])
    deadline=time.monotonic()+360
    samples=[]
    while True:
        before=rig.idle('A')
        samples.append(dict(utc_ns=time.time_ns(),available_bytes=before['heap_available_bytes']))
        if before['heap_available_bytes']>=needed:break
        require(time.monotonic()<deadline,'bounded LOAD workspace recovery unavailable')
        time.sleep(2)
    save(directory/'load-preflight.json',dict(required_available_bytes=needed,wait_limit_s=360,samples=samples))
    require(before['revision']==source_revision[:12] and before['system_clock_hz']==CLOCK,
            'source/clock changed before acquisition')
    require(before['status']['engine']=='pio-dma-gp2' and rig.verified_pins['rf_gp']==2 and
            before['status']['reboot_required'] is False,
            'engine/active GPIO mismatch')
    settings = dict(format='CF32', sample_rate_hz=RATE, bandwidth_hz=200000,
                    center_frequency_hz=FREQUENCIES[band]-25000, gain_db=20,
                    channel=0, agc=False, bias_tee=False)
    from phase14_reference import gps
    reference = gps(FREQUENCIES[band]-40000)
    require(reference['out1'] and not reference['pps1'], 'reference output readiness')
    samples = selected['capture_seconds']*RATE
    limit = capture_elapsed_limit(samples, RATE)
    argv = [CAPTURE, '--enable-physical-sdr', 'sdrplay', '2404058C60',
            str(settings['center_frequency_hz']), str(samples), '20', str(RATE), '200000',
            '0', 'false', 'false', '100000', str(limit), str(directory/'capture.cf32'),
            str(directory/'capture.json'), directory.name]
    require(shutil.disk_usage(directory).free > samples*8 + plan()['storage_reserve_bytes'],
            'capture storage reserve')
    records = []
    process = None
    active_job = None
    owner = None
    first_start = None
    with (directory/'receiver.log').open('x') as log:
        try:
            process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic()+8
            pending = directory/'capture.cf32.incomplete'
            while not pending.exists() or pending.stat().st_size < 65536:
                require(process.poll() is None and time.monotonic()<deadline, 'receiver readiness')
                time.sleep(.05)
            time.sleep(1)
            for index, window in enumerate(selected['windows']):
                before = rig.idle('A')
                peer = rig.device.peer('A')
                owner = uuid.uuid4().hex
                require(peer.request('CLAIM', dict(owner_id=owner, lease_ms=60000))['owner_id']==owner,
                        'exclusive owner')
                value = window['job']
                active_job = value['job_id']
                record = dict(schema='phase14-physical/1', window_id=window['id'], board='A',
                    serial=BOARDS['A'][0], device_id=BOARDS['A'][1], source_revision=before['revision'],
                    boot_id=peer.boot, firmware_sha256=image_hash, clock_hz=CLOCK, divider=1,
                    engine='pio-dma-gp2', rf_gp=2, boot_pins=rig.verified_pins, session_id=peer.session,
                    engine_frequency_correction_ppb=0, requested_frequency_compensation_ppb=0,
                    band=band, mode=mode, workload='normal', job=value, reference=reference,
                    receiver_command=argv, receiver_helper_sha256=sha256(CAPTURE),
                    receiver_settings=settings, action='complete', result='PENDING', status=[], before=before,
                    path='GP2 -20 dB -> combiner -> -40 dB -> RSP1B; no antenna; no LPF')
                records.append(record)
                save(directory/'records.json', records)
                record['load'] = peer.request('LOAD', value, timeout=30)
                record['accepted_job'] = accepted_events(value, record['load']['adjustments'])
                clock = peer.request('GET_CLOCK', {})
                require(clock['state']=='synchronized' and int(clock['uncertainty_ns'])<=500000000,
                        'admissible synchronized device clock')
                if first_start is None:
                    first_start = (int(clock['utc_now_ns'])//1000000000+8)*1000000000
                start = first_start+index*120000000000
                require(start > int(clock['utc_now_ns'])+100000000, 'finite frame preparation margin')
                record['arm'] = peer.request('ARM', dict(job_id=value['job_id'], start_utc_ns=str(start),
                                                        max_start_uncertainty_ns='500000000'))
                rig.e.event('planned_window_armed', dict(id=window['id'], start_utc_ns=str(start)))
                end = time.monotonic()+max(0,(start-int(clock['utc_now_ns']))/1e9)+int(value['total_duration_ns'])/1e9+8
                renewed = sampled = time.monotonic()
                while True:
                    require(process.poll() is None and time.monotonic()<end, 'capture/job deadline')
                    status = peer.request('STATUS', {})
                    require(status['boot_id']==record['boot_id'] and status['job_id']==active_job,
                            'job/boot changed')
                    record['status'].append(dict(utc_ns=time.time_ns(),monotonic_ns=time.monotonic_ns(),status=status))
                    if time.monotonic()-sampled>=10:
                        rig.info('A'); sampled=time.monotonic()
                    if int(value['total_duration_ns'])>45000000000 and time.monotonic()-renewed>=25:
                        peer.request('RENEW', dict(owner_id=owner, lease_ms=60000)); renewed=time.monotonic()
                    if status['state'] in ('complete','aborted','missed','failed'):
                        break
                    time.sleep(.5)
                record['terminal'] = status
                require(status['output_active'] is False, 'terminal output uncertain')
                require(status['state']=='complete', 'job failed: '+status['state'])
                require(status['owner_id'] in (None,owner),'unexpected terminal successor owner')
                if status['owner_id']==owner:
                    peer.request('RELEASE', {})
                owner=None; active_job=None
                record['after'] = rig.idle('A')
                rig.device.close_peer('A')
                record['result']='CONTROL_COMPLETE'
                save(directory/'records.json', records)
                print(json.dumps(dict(window=window['id'], control='complete')), flush=True)
            require(process.wait(timeout=max(1, limit-selected['capture_seconds']+25))==0, 'complete receiver capture')
            meta = json.loads((directory/'capture.json').read_text())
            validate_capture(meta, directory/'capture.cf32', settings)
            if mode=='WSPR':
                return split_wspr(directory, records, FREQUENCIES[band])
            record = records[0]
            record.update(capture_sha256=meta['output']['sha256'],metadata_sha256=sha256(directory/'capture.json'))
            save(directory/'physical.json',record)
            return [directory]
        except BaseException as error:
            save(directory/'failure.json', dict(error=repr(error), records=records))
            if active_job:
                cleanup_owned(rig,owner,active_job)
            raise
        finally:
            if process and process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
