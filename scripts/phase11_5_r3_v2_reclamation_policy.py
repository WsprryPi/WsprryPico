"""Prospective repeated-cycle bounds; no hardware action is performed here."""
from phase11_5_inventory import require
from phase11_5_r3_v2_admission import maximum_job
from phase11_5_r3_v2_retention_plan import validate_plan

POLICY='native-wtp-and-retention-cycle-v1'


def validate(packet):
    require(packet['source_revision']=='c5f00b6109cc1c692b3f6bf258c1a77dadef6639' and
            packet['image_sha256']=='5f681b10d2c076309116cb9c20df1653d21e522ad19b6b33c1ee57efb3f54756' and
            packet['b_role']=='independent-zero-rf','Repaired A independent-cycle identity')
    require(type(packet['cycle_number']) is int and packet['cycle_number'] in (1,2,3) and
            packet['runtime_seconds']==6000 and packet['restoration_seconds']==150 and
            packet['contention']['policy']==POLICY and packet['contention']['maximum_https_requests']==301,
            'Finite equivalent cycle bounds')
    require(packet['reclamation']==dict(initial_quiet_seconds=360,terminal_ttl_ns=3600_000_000_000,
            post_cache_seconds=60,resource_return_tolerance_bytes=1024,
            idle_groups=['terminal-lru-touch','post-expiry-max-reuse']), 'Unchanged reclamation gates')
    require(len(packet['jobs'])==9,'Eight completed warmup terminals then one maximum job')
    for job in packet['jobs'][:8]:
        require(job==dict(job_id=job['job_id'],profile='rf-events/1',mode='tone',
            total_duration_ns='10000000000',allow_frequency_adjustment=True,
            events=[dict(offset_ns='0',duration_ns='10000000000',rf_on=True,frequency_nhz='135500000000000')]),
            'Matched finite terminal warmup')
    job=packet['jobs'][8]
    require(job==maximum_job(job['job_id'],512,1020_000_000_000), 'Matched maximum allocation RF job')
    validate_plan(packet['retention_http'],packet['owner_id'])
    # Includes normal launch/observation overhead, true terminal expiry and final
    # inactive maximum reallocation/release plus cache stabilization.
    require(360+8*50+1020+50+3660+120<6000,'Cycle full deadline arithmetic')
    return packet


def terminal_expired(status, info, jobs):
    require(status['output_active'] is False and status['state']=='empty' and status['owner_id'] is None,
            'Reclamation must be inactive and unowned')
    expected={job['job_id'] for job in jobs}
    require(not any(r['job_id'] not in expected for r in status['terminal_records']), 'Foreign terminal during cycle')
    return not status['terminal_records'] and info['status']['output_active'] is False
