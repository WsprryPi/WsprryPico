#!/usr/bin/env python3
"""Immutable, campaign-local radio roles for isolated Phase 12 fixtures."""
import hashlib
import json
from pathlib import Path
import re

PAIRS={'engineering':('wlan2','wlan0'),'swapped':('wlan0','wlan2')}


def role_map(selection='engineering',campaign_id=None):
    if selection=='concurrent':
        if not isinstance(campaign_id,str) or not re.fullmatch('[0-9a-f]{32}',campaign_id):raise ValueError('concurrent campaign identity required')
        body=dict(schema='phase12-fixture-roles/1',selection=selection,host_ap='wlan2',observer='p12o'+campaign_id[:10],beacon_observer='wlan0',campaign_id=campaign_id)
        body['sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return body
    if selection not in PAIRS:raise ValueError('unsupported fixture radio roles')
    ap,observer=PAIRS[selection]
    body=dict(schema='phase12-fixture-roles/1',selection=selection,host_ap=ap,observer=observer)
    body['sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return body


def load_roles(root):
    path=Path(root)/'fixture-roles.json'
    if path.is_symlink():raise ValueError('private radio roles symlink')
    if not path.exists():
        if (Path(root)/'fixture-roles-bound.json').exists() or (Path(root)/'fixture-roles-bound.json').is_symlink():raise ValueError('bound radio roles missing')
        return role_map()
    if path.is_symlink() or not path.is_file():raise ValueError('private radio roles file')
    raw=path.read_bytes()
    if len(raw)>2048:raise ValueError('radio roles bound')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate radio role member')
            result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    if not isinstance(value,dict) or value!=role_map(value.get('selection'),value.get('campaign_id')):raise ValueError('immutable radio roles hash/schema')
    bound=Path(root)/'fixture-roles-bound.json'
    if bound.exists() or bound.is_symlink():
        if bound.is_symlink() or len(bound.read_bytes())>2048 or json.loads(bound.read_bytes())!=value:raise ValueError('radio roles changed after fixture binding')
    return value


def preflight(roles,read):
    """Read actual capabilities and identities before a swapped fixture starts."""
    phys={};commands=[]
    def actual(*argv):
        raw=read(*argv);commands.append(dict(argv=list(argv),stdout=raw));return raw
    for interface in ('wlan0','wlan2','wlan1'):
        raw=actual('sudo','-n','/usr/sbin/iw','dev',interface,'info')
        phy=re.findall(r'(?m)^\s*wiphy (\d+)\s*$',raw)
        if len(phy)!=1:raise ValueError('actual interface PHY identity')
        phys[interface]=phy[0]
        if interface!='wlan1':
            state=actual('nmcli','-g','GENERAL.STATE','device','show',interface)
            if '30 (disconnected)' not in state:raise ValueError('fixture radio must be unused')
            if 'Not connected.' not in actual('sudo','-n','/usr/sbin/iw','dev',interface,'link'):raise ValueError('fixture radio associated')
            addresses=json.loads(actual('ip','-j','address','show','dev',interface))
            if any(a.get('family') in ('inet','inet6') and a.get('scope')!='link' for row in addresses for a in row.get('addr_info',[])):
                raise ValueError('fixture radio has existing routable address')
    if len(set(phys.values()))!=3:raise ValueError('fixture and management require distinct PHYs')
    for interface,mode in ((roles['host_ap'],'AP'),(roles['host_ap'] if roles['selection']=='concurrent' else roles['observer'],'managed')):
        raw=actual('sudo','-n','/usr/sbin/iw','phy','phy'+phys[interface],'info')
        section=re.search(r'Supported interface modes:\n((?:[ \t]*\*[^\n]*\n)+)',raw)
        if not section or not re.search(r'(?m)^\s*\* '+mode+r'\s*$',section[1]):raise ValueError('actual required radio mode unavailable')
        # Count every channel-3 field before validating its frequency; an invalid
        # or duplicate entry must not disappear through a selective regex.
        channel=[line for line in raw.splitlines() if '[3]' in line]
        exact=re.fullmatch(r'\s*\*\s+2422(?:\.0+)?\s+MHz\s+\[3\](.*)',channel[0]) if len(channel)==1 and raw.count('[3]')==1 else None
        if not exact or any(token in exact[1].lower() for token in ('disabled','no ir','no-ir','radar')):raise ValueError('legal active channel 3 unavailable')
        if interface==roles['host_ap'] and not re.search(r'CCMP.*00-0f-ac:4|00-0f-ac:4.*CCMP',raw):raise ValueError('actual CCMP capability unavailable')
    if roles['selection']=='concurrent':
        from phase12_virtual_observer import topology
        if phys['wlan2']!='2':raise ValueError('concurrent campaign requires actual phy2 wlan2')
        virtual=topology(roles,actual)
    else:virtual=None
    return dict(virtual=virtual,schema='phase12-radio-preflight/1',roles_sha256=roles['sha256'],phys=phys,commands=commands,status='READ_ONLY_CAPABILITIES_READY')
