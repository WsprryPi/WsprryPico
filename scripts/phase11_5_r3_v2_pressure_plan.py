"""Pure prospective v2 pressure scope; frozen historical packet validators stay strict."""
from phase11_5_inventory import require
from phase11_5_r3_tls_plan import CASES as TLS_CASES,BRACKET_POLICY
from phase11_5_r3_transport_plan import CASES as TRANSPORT_CASES,ACK_POLICY_B2


def validate(packet):
    from phase11_5_r3_v2_rf import validate as validate_rf
    validate_rf(packet)
    return validate_profile(packet)


def validate_profile(packet):
    family=packet['pressure_family'];require(family in ['tls','transport'],'V2 pressure family')
    require(packet['runtime_seconds']==(330 if family=='tls' else 450) and len(packet['jobs'])==2 and
            packet['maximum_tcp_connections']==(12 if family=='tls' else 15) and
            packet['pressure_cases']==[list(c) for c in (TLS_CASES if family=='tls' else TRANSPORT_CASES)] and
            packet['observer_bracket_policy']==BRACKET_POLICY and packet['maximum_renewals']==12,
            'V2 exact finite pressure budget')
    require(packet.get('ack_filter_policy')==(ACK_POLICY_B2 if family=='transport' else None),
            'V2 prospective payload-free ACK policy')
    for job in packet['jobs']:
        require(job['mode']=='tone' and job['total_duration_ns']==('100000000000' if family=='tls' else '150000000000') and job['events']==[
            dict(offset_ns='0',duration_ns='100000000000' if family=='tls' else '150000000000',rf_on=True,frequency_nhz='135500000000000')],
            'V2 pressure finite Tones with whole-case deadline reserve')
    require(packet['contention']['policy']=='native-wtp-and-bounded-pressure-v1','V2 controller-only nominal load')
    return packet
