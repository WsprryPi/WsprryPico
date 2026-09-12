#!/usr/bin/env python3
"""Exact R2 first packet: three browser-owned finite Tone jobs under N300.

This packet does not close R2 modes or production/USB submission coverage.
"""
import hashlib
import json
import re
from phase11_5_inventory import require

SCHEMA = 'phase11.5-r2-tone-v1'
SOURCE = 'e20ae8bea2d5237af017dbd5f73bfe9332ce144e'
IMAGE = '7a7306b8ad9dab694903434b86aec18e249c79dad0443645cd04ca857e9d4a04'
SECONDS = 300
from phase11_5_r2_amended_plan import SOURCE as AMENDED_SOURCE, PHYSICAL as AMENDED_IMAGE
AMENDED_SCHEMA='phase11.5-r2-tone-v2'


def jobs(nonce):
    require(isinstance(nonce, str) and re.fullmatch('[0-9a-f]{32}', nonce), 'R2 nonce')
    return [dict(job_id=hashlib.sha256(f'R2:{nonce}:tone:{i}'.encode()).hexdigest()[:32],
        profile='rf-events/1', mode='tone', total_duration_ns='10000000000',
        allow_frequency_adjustment=True, events=[dict(offset_ns='0', duration_ns='10000000000',
            rf_on=True, frequency_nhz='135500000000000')]) for i in range(3)]


def validate(packet):
    source,image=(AMENDED_SOURCE,AMENDED_IMAGE) if packet['schema']==AMENDED_SCHEMA else (SOURCE,IMAGE)
    require(packet['schema'] in (SCHEMA,AMENDED_SCHEMA) and packet['source_revision'] == source and
            packet['revision'] == source[:12] and packet['uf2_sha256'] == image and
            type(packet['system_clock_hz']) is int and packet['system_clock_hz'] == 138000000 and
            packet['rf_render_in_ram'] is True and type(packet['pio_divider']) is int and packet['pio_divider'] == 1 and
            packet['listener_enabled'] is True, 'R2 firmware/clock/renderer/listener')
    require(packet['serial'] == '0BF4B4AEC9FFB344' and
            packet['device_id'] == 'fd6127d11d6aca42a9905fa3fb1bf1d5', 'R2 device')
    for key in ('nonce', 'boot_id', 'owner_id', 'browser_session_id'):
        require(isinstance(packet[key], str) and re.fullmatch('[0-9a-f]{32}', packet[key]) and
                packet[key] != '0'*32, 'R2 nonzero identity')
    require(json.dumps(packet['jobs'],sort_keys=True) == json.dumps(jobs(packet['nonce']),sort_keys=True) and packet['nominal_seconds'] == SECONDS and
            packet['browser_profile'] == 'N' and packet['submission_path'] == 'browser',
            'R2 exact jobs/profile/path')
    require(packet.get('prior_terminal_records') == [], 'R2 first packet requires empty history')
    return packet
