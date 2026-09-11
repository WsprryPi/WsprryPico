#!/usr/bin/env python3
"""Pure, bounded F1 job construction and exact-packet validation; no hardware I/O."""
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from campaign.plan import make_job
from phase11_5_inventory import require
from phase11_5_network_fixture import HOST_BOOT

SOURCE='8fb3894253ef45adc3aad28f25a684168487490f'
IMAGE='75b26e3fa2fc74e517fbfe9cdbe8ee7b9c0e6eabfc13708827d48d978ea0ba9f'
SCHEMA='phase11.5-f1-v1'
MODES=('TONE','QRSS','FSKCW','DFCW','WSPR')
MAX_RENEWALS=60
NOMINAL_SECONDS=1500


def validate_rf_packet(packet):
    if packet.get('schema')==SCHEMA:
        validate(packet)
    else:
        from phase11_5_pilot import validate_packet
        validate_packet(packet)
    prior=packet.get('prior_terminal_records',[])
    require(isinstance(prior,list) and len(prior)<=8 and
            len({r['job_id'] for r in prior})==len(prior) and
            not {r['job_id'] for r in prior}&{j['job_id'] for j in packet['jobs']} and
            all(r['state']=='complete' and r['output_active'] is False and 'error' not in r
                for r in prior),'Invalid preserved terminal history')
    return packet


def admit_caps(packet,caps):
    validate_rf_packet(packet)
    for job in packet['jobs']:
        require(job['mode'] in caps['modes'] and job['profile'] in caps['profiles'] and
                len(job['events'])<=caps['max_events'] and
                int(job['total_duration_ns'])<=int(caps['max_job_duration_ns']),
                'Finite job exceeds actual CAPS')
        for event in job['events']:
            if event['rf_on']:
                frequency=int(event['frequency_nhz'])
                require(any(int(r['minimum_nhz'])<=frequency<=int(r['maximum_nhz'])
                            for r in caps['frequency_ranges']),'Finite frequency outside actual CAPS')


def jobs(nonce):
    require(isinstance(nonce,str) and re.fullmatch('[0-9a-f]{32}',nonce),'F1 nonce')
    result=[]
    for mode in MODES:
        for repeat in range(3):
            job=make_job(mode,135500,sample_rate_hz=138000000,keyed_dot_ns=3000000000)
            if mode=='TONE':
                # Keep the ten-second Tone used by A3 so the independent
                # five-second STATUS observer can see its Running interval.
                job['total_duration_ns']=job['events'][0]['duration_ns']='10000000000'
            job['job_id']=hashlib.sha256(f'Phase11.5-F1:{nonce}:{mode}:{repeat}'.encode()).hexdigest()[:32]
            result.append(job)
    return result


def totals(sequence):
    return dict(jobs=len(sequence),duration_ns=sum(int(j['total_duration_ns']) for j in sequence),
        rf_on_ns=sum(int(e['duration_ns']) for j in sequence for e in j['events'] if e['rf_on']))


def validate(packet):
    require(packet['host_boot_id']==HOST_BOOT,'F1 exact host boot')
    require(packet['maximum_renewals']==MAX_RENEWALS,'F1 bounded lease renewals')
    require(packet['nominal_seconds']==NOMINAL_SECONDS,'F1 frozen nominal interval')
    require(packet['schema']==SCHEMA and packet['source_revision']==SOURCE and
            packet['revision']==SOURCE[:12] and packet['uf2_sha256']==IMAGE and
            packet['system_clock_hz']==138000000 and packet['rf_render_in_ram'] is True,
            'F1 exact physical firmware/clock')
    require(packet['serial']=='0BF4B4AEC9FFB344' and
            packet['device_id']=='fd6127d11d6aca42a9905fa3fb1bf1d5', 'F1 DUT')
    for key in ('boot_id','owner_id','browser_session_id','nonce'):
        require(isinstance(packet[key],str) and re.fullmatch('[0-9a-f]{32}',packet[key]) and
                packet[key]!='0'*32,'F1 nonzero identity')
    require(packet['jobs']==jobs(packet['nonce']),'F1 jobs differ from exact finite plan')
    require(packet['totals']==totals(packet['jobs']),'F1 totals differ')
    require(packet['totals']==dict(jobs=15,duration_ns=622776000000,rf_on_ns=532776000000),
            'Unexpected F1 duration or RF-on budget')
    return packet


if __name__=='__main__':
    # Deterministic preview only. Execution requires a separately frozen nonce,
    # actual boot, owner/session identities and reviewed prerequisite hashes.
    sequence=jobs('1'*32)
    print(json.dumps(dict(status='PREVIEW_NOT_AUTHORIZATION',jobs=sequence,totals=totals(sequence)),indent=2))
