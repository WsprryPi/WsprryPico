"""Pure remaining HTTP/slot/alert scope; independent of consumed A1 packets."""
from phase11_5_inventory import require
from phase11_5_r3_tls_plan import jobs, validate as validate_a1, CASES as A1_CASES, SCHEMA as A1_SCHEMA

SCHEMA='phase11.5-r3-transport-b1-v1'
SCHEMA_B2='phase11.5-r3-transport-b2-v1'
CASES=(('positive','partial-header','recover-header','partial-body','recover-body','pending-expiry','recover-pending'),
       ('positive','stalled-http-reader','recover-reader','failed-alert-ack','recover-alert-ack','failed-alert-wait','recover-alert-wait'))
MAX_CONNECTIONS=15
RECOVERY = dict(scope='r3-b1-idle-rejoin-v1', maximum_off=1, maximum_on=1,
                prior_packet_sha256='474e315dee1d7ba7527105a8c34b572508536224be010d9133ec2aaf8998b0d3',
                prior_evidence_sha256='6c6c34d81048bdd07a970899dfbff845711d3c52f924d373ae00756785fe63f3')
RECOVERY_B2 = dict(scope='r3-b2-idle-rejoin-v1', maximum_off=1, maximum_on=1,
                   prior_packet_sha256='b5359002368fbe2ff4db1dc4b101734f40145887f03ac767e9a01d6634ce7b0b',
                   prior_evidence_sha256='412c493b11eddfc8a5e51c7870f1917986ae0977eca40751f5565dbb78b507b2')
ACK_POLICY_B2 = 'zero-payload-after-server-flight-v1'


def validate(packet):
    require(packet.get('schema') in (SCHEMA, SCHEMA_B2) and packet.get('pressure_cases')==[list(c) for c in CASES]
            and packet.get('maximum_tcp_connections')==MAX_CONNECTIONS
            and packet.get('observer_bracket_policy')=='request-cadence-and-roundtrip-v1', 'B1 exact scope')
    require(packet.get('ack_filter_policy') == (ACK_POLICY_B2 if packet['schema'] == SCHEMA_B2 else None),
            'Transport ACK filter policy')
    validate_a1(dict(packet,schema=A1_SCHEMA,pressure_cases=[list(c) for c in A1_CASES]))
    return packet


def validate_retained(packet):
    b2 = packet.get('r3_scope') == SCHEMA_B2
    require(packet.get('r3_scope') in (SCHEMA, SCHEMA_B2) and packet['maximum_tcp_connections']==MAX_CONNECTIONS
            and packet['pressure_cases']==[list(c) for c in CASES]
            and packet.get('ack_filter_scope') == (ACK_POLICY_B2 if b2 else 'isolated-tuple-pure-ack-v1')
            and packet.get('fixture_authorized') is True and packet.get('current_wiring_confirmed') is True
            and packet.get('wifi_recovery') == (RECOVERY_B2 if b2 else RECOVERY), 'B1/B2 retained scope')
    from phase11_5_r3_retained import validate as old_validate
    old_validate(dict(packet,r3_scope=A1_SCHEMA,maximum_tcp_connections=12,
                      pressure_cases=[list(c) for c in A1_CASES], wifi_recovery=None))
    return packet
