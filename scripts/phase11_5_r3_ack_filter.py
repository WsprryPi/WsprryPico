"""Prospective zero-payload ACK filter; never infer payload length from PSH."""
import ipaddress
import json
from phase11_5_inventory import require


def rules(table, port, source='10.77.15.2', destination='10.77.15.10'):
    require(table.startswith('r3b2_') and table[5:].isalnum()
            and type(port) is int and 1 <= port <= 65535, 'B2 filter identity')
    source, destination = str(ipaddress.IPv4Address(source)), str(ipaddress.IPv4Address(destination))
    text = (f'create table ip {table}\n'
            f'add chain ip {table} output {{ type filter hook output priority 0; policy accept; }}\n')
    for words in range(5, 16):
        # IPv4 IHL=5 and paired TCP data-offset/IP-length equality prove zero
        # payload for every possible TCP option length. ACK-with-data passes,
        # even if it lacks PSH. SYN, FIN and RST always pass.
        text += (f'add rule ip {table} output ip saddr {source} ip daddr {destination} '
                 f'tcp sport {port} tcp dport 18443 ip hdrlength 5 tcp doff {words} '
                 f'ip length {20 + words * 4} tcp flags & (syn | fin | rst | ack) == ack counter drop\n')
    return text


def audit_rules(raw, table, port):
    """Check actual nft JSON, not just the runner's intended command text."""
    items = json.loads(raw)['nftables']
    require([next(iter(v)) for v in items] == ['metainfo', 'table', 'chain'] + ['rule'] * 11
            and all(len(v) == 1 for v in items), 'Unexpected nft objects')
    actual_table, chain = items[1]['table'], items[2]['chain']
    require({k: v for k, v in actual_table.items() if k != 'handle'} == dict(family='ip', name=table)
            and {k: v for k, v in chain.items() if k != 'handle'} == dict(family='ip', table=table,
                name='output', type='filter', hook='output', prio=0, policy='accept'), 'Actual nft table/chain differs')
    total = 0
    for words, item in zip(range(5, 16), items[3:]):
        rule = item['rule']
        expected = []
        for protocol, field, value in (('ip', 'saddr', '10.77.15.2'), ('ip', 'daddr', '10.77.15.10'),
                ('tcp', 'sport', port), ('tcp', 'dport', 18443), ('ip', 'hdrlength', 5),
                ('tcp', 'doff', words), ('ip', 'length', 20 + words * 4)):
            expected.append(dict(match=dict(op='==', left=dict(payload=dict(protocol=protocol, field=field)), right=value)))
        expected.append({'match': {'op': '==', 'left': {'&': [
            {'payload': {'protocol': 'tcp', 'field': 'flags'}}, {'|': ['fin', 'syn', 'rst', 'ack']}]}, 'right': 'ack'}})
        require({k: v for k, v in rule.items() if k not in ('handle', 'expr')} ==
                dict(family='ip', table=table, chain='output') and len(rule['expr']) == 10
                and rule['expr'][:8] == expected and rule['expr'][-1] == {'drop': None},
                'Actual nft predicate differs from the zero-payload tuple scope')
        counter = rule['expr'][8]['counter']
        require(set(counter) == {'packets', 'bytes'} and type(counter['packets']) is int
                and type(counter['bytes']) is int and 0 <= counter['packets'] <= 100
                and counter['bytes'] == counter['packets'] * (20 + words * 4), 'Dropped packets were not empty ACKs')
        total += counter['packets']
    require(total > 0, 'No actual empty ACK dropped')
    return total
