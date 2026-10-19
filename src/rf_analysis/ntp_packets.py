"""Bounded, transactional validation of USB offered-packet evidence pages.

No device IO. The caller retains the original reply before validation and must
enforce its finite time/disk budget. A first-page deficit is explicit; a later
gap cannot silently become complete input coverage.
"""
# SPDX-License-Identifier: MIT
import re


def decimal(value, maximum=(1 << 64)-1):
    if not isinstance(value, str) or not re.fullmatch(r'0|[1-9][0-9]*', value):
        raise ValueError('Noncanonical packet integer')
    result = int(value)
    if result > maximum:
        raise ValueError('Packet integer exceeds bound')
    return result


class PacketHistory:
    def __init__(self, device, boot, firmware, revision):
        self.identity = dict(device_id=device, boot_id=boot, firmware=firmware, revision=revision)
        self.cursor = 0
        self.first_gap = 0
        self.pages = 0
        self.accepted = self.rejected = 0
        self.last_receive = 0
        self.last_frontier = 0
        self.last_observed = 0

    def ingest(self, page, *, allow_initial_gap=False):
        if page.get('ok') is not True or page.get('schema') != 'microchrony-packet-page/1':
            raise ValueError('Packet page schema/refusal')
        if any(page.get(k) != v for k,v in self.identity.items()):
            raise ValueError('Packet identity changed')
        last,oldest,lost,overwritten,nxt = (decimal(page[k]) for k in
            ['last_id','oldest_id','lost_before','overwritten','next_cursor'])
        observed = decimal(page['observed_raw_ns'])
        if observed < self.last_observed:
            raise ValueError('Packet observation time regressed')
        if oldest != max(1,last-31) or overwritten != oldest-1 or last < self.last_frontier:
            raise ValueError('Packet ring frontier changed')
        first = max(self.cursor+1,oldest)
        if lost != first-self.cursor-1 or (lost and (self.pages or not allow_initial_gap)):
            raise ValueError('Packet history gap')
        records = page.get('records')
        if not isinstance(records,list) or len(records) != min(4,last-first+1):
            raise ValueError('Packet page count')
        previous = self.last_receive
        accepted = rejected = 0
        for expected,r in enumerate(records,first):
            if decimal(r['id']) != expected or type(r.get('slot')) is not int or not 0 <= r['slot'] < 4:
                raise ValueError('Packet sequence/slot')
            decimal(r['endpoint'],(1<<32)-1)
            decimal(r['clock_epoch'])
            send,receive = decimal(r['request_raw_ns']),decimal(r['receive_raw_ns'])
            decimal(r['request_token'])
            length = r['length']
            if type(length) is not int or not 0 <= length <= (1<<32)-1:
                raise ValueError('Packet length')
            prefix = r['prefix_hex']
            if not isinstance(prefix,str) or not re.fullmatch(r'[0-9a-f]*',prefix) or len(prefix) != 2*min(48,length):
                raise ValueError('Packet prefix')
            if type(r.get('truncated')) is not bool or r['truncated'] != (length > 48):
                raise ValueError('Packet truncation flag')
            if receive < max(send,previous) or receive > observed:
                raise ValueError('Packet raw time order')
            if type(r.get('accepted')) is not bool or not isinstance(r.get('reason'),str):
                raise ValueError('Packet verdict')
            if r['accepted'] and (r['reason'] != 'accepted' or length != 48 or r['truncated']):
                raise ValueError('Accepted packet verdict/length')
            if not r['accepted'] and r['reason'] == 'accepted':
                raise ValueError('Rejected packet lacks reason')
            previous = receive
            accepted += r['accepted']
            rejected += not r['accepted']
        expected_next = first+len(records)-1 if records else self.cursor
        if nxt != expected_next or type(page.get('more')) is not bool or page['more'] != (nxt < last):
            raise ValueError('Packet continuation')
        # Commit only after validating the entire page, including its tail.
        self.cursor = nxt
        self.first_gap += lost
        self.pages += 1
        self.accepted += accepted
        self.rejected += rejected
        self.last_receive = previous
        self.last_frontier = last
        self.last_observed = observed
        return records
