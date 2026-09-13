"""Source-bound terminal retention checks using target clock brackets, not host age."""
from phase11_5_inventory import require


def retained_prior(records, caps, lower_ns, upper_ns):
    require(caps['terminal_record_entries']==8 and caps['terminal_record_ttl_seconds']==3600,
            'Unreviewed terminal capacity/expiry')
    require(type(lower_ns) is int and type(upper_ns) is int and 0<=lower_ns<=upper_ns,
            'Invalid target clock bracket')
    require(len(records)<=8 and len({r['job_id'] for r in records})==len(records), 'Invalid prior terminal cardinality')
    kept,expired=[],[]
    for record in records:
        ended=int(record['ended_monotonic_ns'])
        require(0<=ended<=lower_ns and record['state']=='complete' and record['output_active'] is False
                and 'error' not in record, 'Invalid prior terminal state/time')
        expires=ended+3_600_000_000_000
        if expires<=lower_ns: expired.append(record)
        elif expires>upper_ns: kept.append(record)
        else: raise ValueError('Terminal expiry falls inside the observation clock bracket; no definitive retention claim')
    return kept,expired
