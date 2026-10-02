#!/usr/bin/env python3
"""Link-audit failures for missing routing and direct SDK bypass."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_btstack_pool_hooks import POOLS, validate


def fixture():
    lines = []
    for pool in POOLS:
        for operation in ('get', 'free'):
            real = f'btstack_memory_{pool}_{operation}'
            wrapper = '__wrap_' + real
            lines += [f'00000010 <{wrapper}>:', f'  10: f000 f800\tbl\t20 <{real}>',
                      f'00000020 <{real}>:']
            if pool == 'hci_connection':
                lines += [f'00000030 <sdk_{operation}>:', f'  30: f000 f800\tbl\t10 <{wrapper}>']
    return '\n'.join(lines)


def rejected(text):
    try:
        validate(text)
    except ValueError:
        return
    raise AssertionError('unsafe routing accepted')


def main():
    valid = fixture()
    result = validate(valid)
    if len(result) != 10 or result['__wrap_btstack_memory_l2cap_channel_get'] != []:
        raise AssertionError('unreachable configured hooks misreported')
    rejected(valid + '\n00000040 <bypass>:\n  40: f000 f800\tbl\t20 <btstack_memory_hci_connection_get>')
    rejected(valid.replace('00000010 <__wrap_btstack_memory_sm_lookup_entry_get>:',
                           '00000010 <missing>:', 1))
    rejected(valid.replace('00000030 <sdk_get>:\n  30: f000 f800\tbl\t10 <__wrap_btstack_memory_hci_connection_get>', ''))


if __name__ == '__main__':
    main()
