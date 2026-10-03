#!/usr/bin/env python3
"""Exact campaign-owned concurrent managed interface for the opt-in fixture."""
import json
import re
import time
from pathlib import Path


def require(ok,message):
    if not ok:raise ValueError(message)


def identity(raw):
    def field(pattern):
        values=re.findall(pattern,raw,re.M);require(len(values)==1,'virtual interface identity field');return values[0]
    return dict(interface=field(r'^\s*Interface (\S+)\s*$'),phy=field(r'^\s*wiphy (\d+)\s*$'),
                wdev=field(r'^\s*wdev (0x[0-9a-f]+)\s*$'),mode=field(r'^\s*type (\S+)\s*$'))


def combinations(raw):
    section=re.search(r'valid interface combinations:\n(.*?)(?=\n\s*[A-Za-z][^\n:]*:|\Z)',raw,re.S)
    # iw wraps each combination over continuation lines; never combine budgets
    # from two alternatives. Require an explicit AP+managed same-channel entry.
    require(section is not None,'actual concurrent interface combinations required')
    for part in re.split(r'(?m)^\s*\* ',section[1]):
        if not part.strip():continue
        groups=re.findall(r'#\{ ([^}]+) \} <= (\d+)',part)
        covered=set();supported=True
        for modes,limit in groups:
            names=set(modes.split(', '))
            if covered & names:supported=False
            covered.update(names)
            # A group limit is shared by all named modes. We require one AP
            # and one managed interface simultaneously, never separate maxima.
            if len(names & {'managed','AP'})>int(limit):supported=False
        total=re.findall(r'total <= (\d+)',part);channels=re.findall(r'#channels <= (\d+)',part)
        if supported and {'managed','AP'}<=covered and len(total)==len(channels)==1 and int(total[0])>=2 and int(channels[0])==1:return
    raise ValueError('unsupported AP plus managed single-channel combination')


def topology(roles,read):
    inventory=read('sudo','-n','/usr/sbin/iw','dev')
    require(roles['observer'] not in re.findall(r'(?m)^\s*Interface (\S+)\s*$',inventory),'virtual observer name collision')
    sections=re.split(r'(?m)^phy#(\d+)\s*$',inventory)
    devices={}
    for index in range(1,len(sections),2):devices[sections[index]]=re.findall(r'(?m)^\s*Interface (\S+)\s*$',sections[index+1])
    require(devices.get('2')==['wlan2'],'actual phy2 must contain only unused wlan2')
    combinations(read('sudo','-n','/usr/sbin/iw','phy','phy2','info'))
    return dict(inventory=inventory,phy='2',name_absent=True,roles_sha256=roles['sha256'])


def create(root,roles,proof,read,mutate,write,*,deadline=None,clock=time.monotonic,sleeper=time.sleep):
    root=Path(root);path=root/'virtual-observer-owned.json'
    require(not path.exists() and not path.is_symlink(),'virtual observer already attempted; no retries')
    require(proof['roles_sha256']==roles['sha256'] and proof['name_absent'] and proof['phy']=='2','actual precreation topology proof')
    receipt=dict(schema='phase12-owned-virtual-observer/1',roles_sha256=roles['sha256'],interface=roles['observer'],before=proof,state='CREATE_INTENT',identity=None)
    write(path,receipt)
    failure=None
    try:mutate('sudo','-n','/usr/sbin/iw','phy','phy2','interface','add',roles['observer'],'type','managed')
    except BaseException as error:failure=error;receipt['create_error_type']=type(error).__name__
    try:
        found=identity(read('sudo','-n','/usr/sbin/iw','dev',roles['observer'],'info'))
        require(found['phy']=='2' and found['interface']==roles['observer'] and found['mode']=='managed','created virtual identity mismatch')
        receipt['identity']=found;receipt['state']='CREATED';write(path,receipt)
    except BaseException as error:
        receipt['state']='CREATE_UNCERTAIN';receipt['readback_error_type']=type(error).__name__;write(path,receipt);raise
    if failure is not None:raise failure
    # NetworkManager discovers a new kernel interface asynchronously. Observe
    # only this owned interface; never change UP/managed flags or NM settings.
    until=min(clock()+5,deadline if deadline is not None else float('inf'))
    receipt['nm_states']=[];write(path,receipt)
    try:
        for _ in range(51):
            started=clock();require(started<until,'new observer availability deadline')
            raw=read('nmcli','-g','GENERAL.STATE','device','show',roles['observer'])
            ended=clock()
            receipt['nm_states'].append(dict(monotonic_start_s=started,monotonic_end_s=ended,raw=raw[:8192],output_overflow=len(raw)>8192));write(path,receipt)
            require(len(raw)<=8192,'NM state output bound')
            require(ended<until,'late observer availability result')
            state=re.fullmatch(r'\s*(\d+) \(([^\r\n()]*)\)\s*',raw)
            require(state is not None,'actual NM state format')
            if state[1]=='30' and state[2]=='disconnected':
                receipt['state']='AVAILABLE';write(path,receipt);return receipt
            require(state[1] in ('10','20'),'new observer must remain unused while becoming available')
            sleeper(max(0,min(.1,until-clock())))
        raise ValueError('bounded observer availability samples exhausted')
    except BaseException as error:
        receipt['state']='AVAILABILITY_FAILED';receipt['availability_error_type']=type(error).__name__;write(path,receipt);raise


def remove(root,roles,read,mutate,write):
    path=Path(root)/'virtual-observer-owned.json'
    if not path.exists():return dict(status='NO_OWNED_VIRTUAL_OBSERVER')
    require(not path.is_symlink() and len(path.read_bytes())<=262144,'private virtual receipt')
    receipt=json.loads(path.read_bytes());require(receipt['roles_sha256']==roles['sha256'] and receipt['interface']==roles['observer'],'virtual cleanup source binding')
    inventory=read('sudo','-n','/usr/sbin/iw','dev')
    if roles['observer'] not in re.findall(r'(?m)^\s*Interface (\S+)\s*$',inventory):
        receipt['state']='ABSENT';write(path,receipt);return dict(status='VIRTUAL_OBSERVER_ABSENT')
    current=identity(read('sudo','-n','/usr/sbin/iw','dev',roles['observer'],'info'))
    require(receipt['identity'] is not None and current==receipt['identity'],'virtual cleanup identity changed or uncertain')
    require('Not connected.' in read('sudo','-n','/usr/sbin/iw','dev',roles['observer'],'link'),'virtual observer connection must be removed first')
    mutate('sudo','-n','/usr/sbin/iw','dev',roles['observer'],'del')
    require(roles['observer'] not in re.findall(r'(?m)^\s*Interface (\S+)\s*$',read('sudo','-n','/usr/sbin/iw','dev')),'virtual observer deletion not verified')
    receipt['state']='REMOVED';write(path,receipt);return dict(status='OWNED_VIRTUAL_OBSERVER_REMOVED')
