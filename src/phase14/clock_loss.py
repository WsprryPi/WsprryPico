"""Pico-specific reversible NTP response suppression on the authorized wspr5 host."""
import ipaddress
import json
from pathlib import Path
import subprocess
import uuid

NFT='/usr/sbin/nft'


class NtpBlock:
    def __init__(self,info,evidence):
        self.e=evidence;self.active=False
        if info['provisioning_source']!='provisioned' or info['network']['ntp_address']!='192.168.1.54':
            raise ValueError('clock loss requires the temporary profile and verified local NTP peer')
        self.address=str(ipaddress.IPv4Address(info['network']['ipv4']))
        if ipaddress.IPv4Address(self.address) not in ipaddress.IPv4Network('192.168.1.0/24'):
            raise ValueError('selected Pico must be on the verified LAN')
        self.table='phase14_'+uuid.uuid4().hex

    def start(self):
        # One new table, one input chain, one selected source/destination/port rule.
        # An accept policy here never bypasses other tables; only this DROP is terminal.
        script=('add table inet '+self.table+'\nadd chain inet '+self.table+
                ' input { type filter hook input priority -100; policy accept; }\n'+
                'add rule inet '+self.table+' input ip saddr '+self.address+
                ' ip daddr 192.168.1.54 udp dport 123 counter drop\n')
        subprocess.run([NFT,'-f','-'],input=script,text=True,capture_output=True,check=True,timeout=5)
        self.active=True;self.e.event('ntp_block_started',dict(table=self.table,pico_ipv4=self.address,ntp_ipv4='192.168.1.54',port=123))

    def close(self):
        if self.active:
            try:
                observed=json.loads(subprocess.check_output([NFT,'-j','list','table','inet',self.table],text=True,timeout=5))
                self.e.event('ntp_block_observed',observed)
            finally:
                # Observation failure must not leave the experiment suppressing NTP.
                subprocess.run([NFT,'delete','table','inet',self.table],capture_output=True,check=True,timeout=5)
                absent=subprocess.run([NFT,'list','table','inet',self.table],capture_output=True,timeout=5)
                if absent.returncode!=1:raise ValueError('owned NTP rule removal not confirmed')
                self.active=False;self.e.event('ntp_block_removed',dict(table=self.table))
