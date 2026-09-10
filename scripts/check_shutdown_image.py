#!/usr/bin/env python3
"""Read-only linked-image check for the standard inhibited shutdown breadcrumbs."""
import argparse
import json
import re
import subprocess

CALLS = {
    'cyw43_arch_disable_sta_mode': ['cyw43_cb_tcpip_deinit', 'cyw43_wifi_leave'],
    'cyw43_cb_tcpip_deinit': ['dhcp_stop', 'netif_remove'],
    'netif_remove': ['igmp_stop'],
    'cyw43_netif_update_igmp_mac_filter': ['cyw43_wifi_update_multicast_filter'],
}

def validate(text):
    for caller, operations in CALLS.items():
        found = re.search(r'^\w+ <' + caller + r'>:\n(.*?)(?=^\w+ <|\Z)', text, re.M | re.S)
        if not found:
            raise ValueError('missing linked caller: ' + caller)
        for op in operations:
            if not re.search(r'\b(?:bl|blx|b\.w)\s+[^\n]*<__wrap_' + op + r'>', found[1]):
                raise ValueError('missing interception: ' + caller + ' -> ' + op)
    return CALLS

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf')
    parser.add_argument('--objdump', default='arm-none-eabi-objdump')
    args = parser.parse_args()
    text = subprocess.check_output([args.objdump, '-d', args.elf], text=True)
    print(json.dumps({'intercepted_calls': validate(text)}, indent=2))
