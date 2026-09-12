"""Frozen remaining R2 jobs; reuse the accepted Tone gate and unchanged image."""
import hashlib
import json
import re
from phase11_5_inventory import require
from phase11_5_r2_amended_plan import SOURCE, PHYSICAL
from phase11_5_f1_plan import make_job

SCHEMA='phase11.5-r2-modes-v1'
COUNTS={'config':30,'wifi-off':0,'wifi-on':0,'heap-probe':6}


def jobs(nonce, path):
    require(re.fullmatch('[0-9a-f]{32}',nonce) is not None, 'Mode nonce')
    require(path in ('usb','production'), 'Mode submission path')
    modes=('FSKCW','DFCW','WSPR') if path=='usb' else ('QRSS',)
    result=[]
    for mode in modes:
        job=make_job(mode,135500,sample_rate_hz=138000000,keyed_dot_ns=3000000000)
        if path=='production':
            # Native execution_plan_compiler.cpp emits ETE without diagnostic padding.
            job['events']=job['events'][1:-1]
            for event in job['events']:event['offset_ns']=str(int(event['offset_ns'])-10**9)
            job['total_duration_ns']='33000000000'
        job['job_id']=hashlib.sha256(f'R2-modes:{nonce}:{mode}'.encode()).hexdigest()[:32]
        result.append(job)
    return result


def validate(packet):
    from phase11_5_r2_upload_plan import SOURCE as upload_source, PHYSICAL as upload_physical
    source = packet['source_revision']
    require(source in (SOURCE,upload_source), 'Unreviewed mode firmware')
    physical = upload_physical if source == upload_source else PHYSICAL
    if source == upload_source:
        require(packet['submission_path']=='usb', 'Upload repair only remaining USB modes')
    require(packet['schema']==SCHEMA and packet['revision']==source[:12] and packet['uf2_sha256']==physical and
            type(packet['system_clock_hz']) is int and packet['system_clock_hz']==138000000 and
            packet['pio_divider']==1 and packet['listener_enabled'] is True and
            packet['rf_render_in_ram'] is True, 'Remaining-mode image/configuration')
    require(packet['serial']=='0BF4B4AEC9FFB344' and
            packet['device_id']=='fd6127d11d6aca42a9905fa3fb1bf1d5', 'Mode DUT identity')
    for key in ('nonce','boot_id','owner_id'):
        require(isinstance(packet[key],str) and re.fullmatch('[0-9a-f]{32}',packet[key]) and
                packet[key]!='0'*32, 'Mode nonzero identity')
    expected=jobs(packet['nonce'],packet['submission_path'])
    if packet['submission_path']=='production':
        binding=packet['production_binding']
        require(binding['phase']=='waiting' and binding['owner_id']==packet['owner_id'] and
                binding['identity']['boot_id']==packet['boot_id'] and
                binding['identity']['device_id']==packet['device_id'] and
                re.fullmatch('[0-9a-f]{16}0000000000000001',binding['job_id']),
                'Production identity must be bound while Waiting before first dispatch')
        expected[0]['job_id']=binding['job_id']
    require(json.dumps(packet['jobs'],sort_keys=True)==json.dumps(expected,sort_keys=True) and packet['nominal_seconds']==300 and
            packet['browser_profile']=='N', 'Exact remaining jobs and workload')
    require(type(packet['maximum_renewals']) is int and packet['maximum_renewals']==12,
            'Renewal limit')
    return packet
