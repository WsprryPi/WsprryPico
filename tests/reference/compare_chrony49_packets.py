#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offer identical packets to unmodified Chrony NCR and the production Engine.

Only deterministic time, request scheduling, entropy, IO and clock-output sinks
are adapted. Chrony's wire parsing/auth/correlation/delay admission executes
before accepted observations reach SST. No sockets or host clock writes occur.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys

SECOND = 10**9
EPOCH = 1_800_000_000 * SECOND


def stamp(value):
    return (((value // SECOND + 2_208_988_800) << 32) |
            ((value % SECOND) << 32) // SECOND) & ((1 << 64) - 1)


def reply(server, processing=0):
    packet = bytearray(48)
    packet[0:4] = bytes([0x24, 1, 6, 0xec])
    for start,value in [(16,server-SECOND),(32,server),(40,server+processing)]:
        packet[start:start+8] = stamp(value).to_bytes(8,'big')
    return packet


def fixture(name):
    rng = random.Random(20261019)
    rows = []
    count = 96 if name.startswith('queue_') or name == 'changing_jitter' else 32
    previous = None
    for i in range(1,count+1):
        send = i*64*SECOND
        delay,offset,processing,mask = 2_000_000,0,0,0
        if name.startswith('queue_'):
            queue = (i*7%11)*2_000_000
            delay += queue
            offset = round(rng.uniform(-1,1)*1_000_000) + round(i*64*-.8*1000)
            offset += round(queue * {'queue_forward':.5,'queue_reverse':-.5,'queue_weak':.2}[name])
        if name == 'changing_jitter':
            queue = (i*7%11)*2_000_000
            delay += queue
            offset = round(.2*queue + rng.uniform(-1,1)*(1000 if i<=48 else 5_000_000))
        if name == 'startup_queue' and i == 4:
            delay,offset = 202_000_000,100_000_000
        if i == 25:
            if name == 'within_stability_allowance': delay,offset = 8_000_000,3_000_000
            if name == 'excess_queue': delay,offset = 202_000_000,100_000_000
            if name == 'phase_step_with_queue': delay,offset = 22_000_000,200_000_000
            if name == 'processing': processing=500_000; delay+=processing
        server = EPOCH+send+(delay-processing)//2+offset
        if name == 'era_rollover':
            server += (2_085_978_496 - 1_800_000_000 - 25*64)*SECOND
        packet=reply(server,processing)
        if i == 25:
            if name == 'correlation': mask=1
            if name == 'short': packet=packet[:24]
            if name == 'one_byte_short': packet=packet[:47]
            if name == 'one_byte_long': packet+=bytes(1)
            if name == 'extension': packet+=bytes(4)
            if name == 'wrong_mode': packet[0]=0x23
            if name == 'wrong_version': packet[0]=0x14
            if name == 'leap_alarm': packet[0]=0xe4
            if name == 'bad_stratum': packet[1]=16
            if name == 'zero_receive': packet[32:40]=bytes(8)
            if name == 'zero_transmit': packet[40:48]=bytes(8)
            if name == 'future_reference': packet[16:24]=stamp(server+2*SECOND).to_bytes(8,'big')
            if name == 'reverse_processing': packet[40:48]=stamp(server-1_000_000).to_bytes(8,'big')
            if name == 'max_delay': delay=4*SECOND
            if name == 'root_distance': packet[8:12]=struct.pack('!I',4*65536)
            if name == 'zero_reference': packet[16:24]=bytes(8)
            if name == 'stale_server':
                packet[16:24]=previous[16:24]
                packet[32:48]=previous[32:48]
        previous = packet[:]
        rows.append(f'{send} {send+delay} {mask:x} {"-" if name == "loss" and i == 25 else packet.hex()}\n')
        if name == 'duplicate' and i == 25:
            rows.append(f'{send} {send+delay+1_000_000} 0 {packet.hex()}\n')
    return ''.join(rows)


def compare(reference, engine, names):
    cases = {}
    for name in names:
        payload=fixture(name)
        ref=subprocess.run([str(reference.resolve())],input=payload,text=True,capture_output=True,
                           timeout=30,check=True)
        # Repeating the external adapter must recreate the same offered wire bytes.
        repeated=subprocess.run([str(reference.resolve())],input=payload,text=True,capture_output=True,
                                timeout=30,check=True)
        assert ref.stdout == repeated.stdout, 'Reference entropy or scheduling is not deterministic'
        mu=subprocess.run([str(engine.resolve()),'packet'],input=ref.stdout,text=True,
                          capture_output=True,timeout=30,check=True)
        expected=[line.split() for line in ref.stdout.splitlines()]
        actual=[line.split() for line in mu.stdout.splitlines()]
        assert len(expected)==len(actual)==len(payload.splitlines())
        differing=[]
        for r,m in zip(expected,actual):
            assert r[0]==m[0]
            if int(r[7]) != int(m[1]):
                differing.append({'row':int(r[0]),'chrony_valid':int(r[6]),
                                  'chrony_accepted':int(r[7]),'chrony_tests':int(r[8]),
                                  'microchrony_accepted':int(m[1]),'microchrony_reason':m[2]})
        cases[name]={'input_sha256':hashlib.sha256(payload.encode()).hexdigest(),
                     'offered_wire_sha256':hashlib.sha256(ref.stdout.encode()).hexdigest(),
                     'offered':len(expected),'chrony_accepted':sum(int(r[7]) for r in expected),
                     'microchrony_accepted':sum(int(m[1]) for m in actual),
                     'differences':differing,'reference_rows':expected,'microchrony_rows':actual}
        print(name, len(differing), 'differences',flush=True)
    return cases


def main():
    if sys.flags.optimize: raise RuntimeError('Run without -O')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',type=Path);parser.add_argument('engine',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    names=['steady','startup_queue','correlation','short','one_byte_short','one_byte_long','extension','wrong_mode','wrong_version','leap_alarm','bad_stratum',
           'zero_receive','zero_transmit','future_reference','reverse_processing','max_delay',
           'root_distance','processing','within_stability_allowance','excess_queue',
           'phase_step_with_queue','queue_forward','queue_reverse','queue_weak',
           'zero_reference','stale_server','era_rollover','duplicate','loss','changing_jitter']
    cases = compare(args.reference,args.engine,names)
    profiles = {'wrong_version':'Bounded client supports NTPv3/v4; Chrony also admits v2.',
                'future_reference':'Pico requires reference <= server transmit.',
                'reverse_processing':'Pico requires receive <= transmit.',
                'root_distance':'Pico applies its existing 3-second distance gate before fitting.',
                'zero_reference':'Zero reference is outside the Pico era/coherence profile.'}
    for name, case in cases.items():
        differences = case['differences']
        if name in profiles:
            assert len(differences) == 1 and differences[0]['row'] == 25
            assert differences[0]['chrony_accepted'] == 1 and differences[0]['microchrony_accepted'] == 0
        else:
            assert not differences, (name, differences)
    for name in ['correlation','short','one_byte_short','one_byte_long','extension','wrong_mode','leap_alarm','bad_stratum',
                 'zero_receive','zero_transmit','max_delay','excess_queue','stale_server','loss']:
        assert cases[name]['chrony_accepted'] == cases[name]['microchrony_accepted'] == 31, name
    for name in ['steady','startup_queue','within_stability_allowance','phase_step_with_queue','era_rollover']:
        assert cases[name]['chrony_accepted'] == cases[name]['microchrony_accepted'] == 32, name
    assert cases['duplicate']['microchrony_accepted'] == 32
    report={'schema':'microchrony-chrony49-packet-admission/1','cases':cases,
            'deliberate_stricter_profile_differences':profiles,
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'reference_sha256':hashlib.sha256(args.reference.read_bytes()).hexdigest(),
            'engine_sha256':hashlib.sha256(args.engine.read_bytes()).hexdigest(),
            'scope':'Single basic NTP association; common fixed raw clock, offered wire packets and externally supplied requests; output discipline frozen; UDP sockets/autonomous scheduling and receive-timeout policy excluded. Loss means an omitted reply between supplied requests.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main()
