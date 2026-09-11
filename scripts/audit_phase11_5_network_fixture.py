#!/usr/bin/env python3
"""Read-only audit of N0 restoration and reconstructed final P0 wire records."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from phase11_5_inventory import require, validate_inventory
from phase11_5_pilot_supervisor import finished, idle
from phase11_5_network_fixture import HOST_BOOT, RADIOS, MANAGEMENT_PROFILE, INSTALLED_SHA
from validate_wtp_contract import crc32c, loads_strict, SchemaValidator


def payload(data):
    require(len(data)>=16, 'Truncated WTP frame')
    magic,version,encoding,flags,size,crc=struct.unpack('>4sBBHII',data[:16])
    require((magic,version,encoding,flags)==(b'WTPF',1,1,0) and 0<size<=65536 and
            len(data)==16+size and crc32c(data[16:])==crc,'WTP frame identity/length/CRC')
    return loads_strict(data[16:].decode())


def inventory(path, serial, device, revision, boot):
    final=finished(path,'READ_ONLY_INVENTORY')
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    pending=None;received=bytearray();info=None;responses={}
    schema=loads_strict((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema)
    for row in rows:
        require(row['serial']==serial,'Mixed inventory serial')
        kind,value=row['kind'],row['value']
        require(kind in ('start','tx','rx','info','response','finish'),'Unexpected inventory event')
        if kind=='tx':
            require(pending is None,'Overlapping inventory exchanges')
            pending=bytes.fromhex(value['hex']);received.clear()
        elif kind=='rx':
            require(pending is not None,'Unsolicited inventory bytes')
            received.extend(bytes.fromhex(value['hex']))
        elif kind=='info':
            require(pending==b'INFO\n' and bytes(received).endswith(b'\n') and
                    bytes(received).count(b'\n')==1 and info is None,'Console exchange framing')
            info=loads_strict(received.decode().strip());require(info==value,'Console summary differs')
            pending=None
        elif kind=='response':
            require(pending is not None,'Response without request')
            request,response=payload(pending),payload(bytes(received))
            require(not validator.errors(request,schema) and not validator.errors(response,schema),
                    'Wire schema differs from WTP/1')
            require(response==value and response.get('ok') is True and
                    all(request[key]==response[key] for key in ('session_id','request_id','op')),
                    'WTP response does not match wire request')
            require(request['op'] in ('HELLO','CAPS','GET_CLOCK','STATUS','PING') and
                    request['op'] not in responses,'Mutation or repeated inventory operation')
            responses[request['op']]=response['body'];pending=None
    require(pending is None and info==final['info'] and responses==final['wtp'],
            'Incomplete wire evidence or final summary differs')
    validate_inventory(info,responses,device);idle(final)
    require(info['revision']==revision and responses['STATUS']['boot_id']==boot and
            info['status']['engine']=='inhibited-standalone-simulator', 'Final board baseline changed')
    return {'serial':serial,'device_id':device,'revision':revision,'boot_id':boot,
            'state':'empty','output_active':False,'owner_id':None,'job_id':None}


def audit(root):
    root=root.resolve(strict=True)
    packet=json.loads((root/'packet.json').read_text())
    for relative,expected in packet['helper_sha256'].items():
        path=root/relative
        require(path.resolve().is_relative_to(root) and
                hashlib.sha256(path.read_bytes()).hexdigest()==expected,'Staged N0 helper changed')
    state=json.loads((root/'fixture-state.json').read_text())
    require(state.get('restored') is True and state['host_boot']==HOST_BOOT,'Restoration not recorded')
    data=(root/'fixture.jsonl').read_text();require(data.endswith('\n'),'Truncated fixture log')
    rows=[json.loads(line) for line in data.splitlines()]
    require(all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])),
            'Fixture time reversed')
    verified=[row for row in rows if row['kind']=='verified']
    cleanups=[row for row in rows if row['kind']=='cleanup']
    require(verified and cleanups and cleanups[-1]['value']['failures']==[],'Missing setup/restoration evidence')
    for row in verified:
        peer=row['value']['peer'];host=row['value']['host']
        require('Connected to '+RADIOS['wlan0'] in peer['link'] and
                '10.77.15.2/24' in peer['addresses'] and 'default' not in peer['routes'] and
                host['installed_pid']=='1957','N0 topology changed')
    host=json.loads((root/'final-host.json').read_text())
    require(host['host_boot']==HOST_BOOT and host['installed_pid']=='1957' and
            host['recovery_active']=='active' and host['recovery_enabled']=='enabled' and
            host['management_profile']==MANAGEMENT_PROFILE,'Host/service restoration changed')
    require('10.77.15.' not in host['interfaces']+host['routes'] and
            'phase115-closure-client' not in host['namespaces'] and
            'Access denied' in host['chrony_access'],'Host isolation resources remain')
    for name,mac in RADIOS.items():
        radio=host['radios'][name]
        require(radio['mac']==mac and radio['state'].startswith('30 ') and
                radio['power_save']=='Power save: '+state['radio'][mac]['power_save'],
                'Radio identity/state/power restoration')
    require(host['installed_sha256']['/usr/local/bin/wsprrypi']==INSTALLED_SHA and
            host['installed_sha256']['/usr/local/etc/wsprrypi.ini']==
            'e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8',
            'Installed binary/configuration changed')
    boards=[]
    for label,serial,device,revision,boot in (
        ('a','0BF4B4AEC9FFB344','fd6127d11d6aca42a9905fa3fb1bf1d5','802c91a7b86e-dirty',
         'e3634081a2c5844524ab64eb2afeab71'),
        ('b','CDDBF8767C506C07','29f20b7342051ef947aa56cb9d4fab42','dbf1d86f0885-dirty',
         '4e2fb851c08b278dd4b977104d2c2aaa')):
        boards.append(inventory(root/('phase115-n0-final-20260911-'+label+'.jsonl'),
                                serial,device,revision,boot))
    return {'result':'N0_RESTORED_AFTER_RECONCILIATION','setup_verifications':len(verified),
            'cleanup_attempts':len(cleanups),'retained_cleanup_failures':[
                row['value']['failures'] for row in cleanups if row['value']['failures']],
            'boards':boards,'phase11_5':'OPEN','accepted_configurations':[],
            'scope':'Host fixture and final inhibited USB state only; no A-G contention acceptance'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    print(json.dumps(audit(parser.parse_args().root),indent=2))
