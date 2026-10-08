"""Pico-specific reversible NTP response suppression on the authorized wspr5 host."""
import ipaddress
import json
from pathlib import Path
import subprocess
import uuid
import time

NFT='/usr/sbin/nft'


def reject_aged_arm(peer,evidence,value):
    """One new finite LOAD after completion; prove aged clock cannot admit ARM."""
    from phase11_5_inventory import exchange,require
    from validate_wtp_contract import frame
    owner=uuid.uuid4().hex;claimed=False
    try:
        peer.request('CLAIM',dict(owner_id=owner,lease_ms=60000));claimed=True
        peer.request('LOAD',value,timeout=30)
        clock=peer.request('GET_CLOCK',{})
        require(clock['state']=='unsynchronized','clock must have aged beyond holdover')
        request=dict(type='request',protocol='WTP/1',session_id=peer.session,request_id=uuid.uuid4().hex,
            op='ARM',body=dict(job_id=value['job_id'],start_utc_ns=str((int(clock['utc_now_ns'])//1000000000+4)*1000000000),max_start_uncertainty_ns='500000000'))
        response=exchange(peer.fd,frame(json.dumps(request,separators=(',',':')).encode()),
            time.monotonic()+3,peer.emit,True,expected=request,receive_buffer=peer.received)
        evidence.event('aged_arm_observation',dict(clock=clock,request=request,response=response))
        require(not peer.validator.errors(response,peer.schema) and response.get('ok') is False and
            response.get('error',{}).get('code')=='CLOCK_UNSYNCHRONIZED','aged clock did not refuse ARM')
        evidence.event('aged_arm_refused',dict(clock=clock,request=request,response=response))
        return dict(clock=clock,request=request,response=response)
    finally:
        if claimed:
            status=peer.request('STATUS',{})
            require(status['job_id']==value['job_id'] and status['owner_id']==owner,'clock probe authority changed')
            if status['state'] in ('loaded','armed','running'):peer.request('ABORT',dict(job_id=value['job_id']))
            require(peer.request('STATUS',{})['output_active'] is False,'clock probe output uncertain')
            peer.request('RELEASE',{})


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
