#!/usr/bin/env python3
"""One B-only repair flash after independently confirmed BF2 fragmented reply refusal."""
import argparse,json,os,re,subprocess
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_v2_parallel_b_deploy import run,validate_stage,B_SERIAL,B_DEVICE,AUTHORIZATION

SCHEMA='phase11.5-r3-v2-parallel-b-paged-repair-v1'
SOURCE='8921a70081839f168edef5926e92445f251d8e1d'
IMAGE='67c27f20da8212097d60cd6b58fbbb4e774286df728ed7ea3e2746b5c6a59f58'
FAULT_AUDIT='c64ee7a5db10c43d0c8cd03e8f3bbae7a12c1243f1109166b7121a957fabbcaa'
PRIOR_BOOT='f4f3670094e95d3d143e4d4b20aefc24'

def validate(packet):
    require(packet['schema']==packet['r3_scope']==SCHEMA and packet['serial']==B_SERIAL and
        packet['device_id']==B_DEVICE and packet['source_revision']==SOURCE and packet['image_sha256']==IMAGE and
        packet['authorization_sha256']==AUTHORIZATION,'Identified B repair only')
    for k,v in dict(runtime_seconds=300,cleanup_seconds=150,flashes=1,bootsel_commands=1,
            rf_jobs=0,arm_commands=0,loads=0,configuration_writes=0,wifi_cycles=0).items():
        require(type(packet[k]) is int and packet[k]==v,'Exact repair budget: '+k)
    require(packet['prior_revision']=='48ef82c7dedf' and packet['prior_boot']==PRIOR_BOOT and
        packet['fault_audit_sha256']==FAULT_AUDIT and
        packet['fault_audit_file']=='/home/pi/phase11-5-r3-v2-parallel-b-functional-bf2-20260913/independent-audit.json',
        'BF2 confirmed failure prerequisite')
    require(re.fullmatch('[0-9a-f]{32}',packet['inventory_session']) and packet['inventory_session']!='0'*32 and
        packet['image_file']=='candidate.uf2' and packet['root'].startswith('/home/pi/phase11-5-r3-v2-parallel-b-deploy-') and
        '..' not in Path(packet['root']).parts and str(Path(packet['root']))==packet['root'],'Private repair scope')
    return packet

def prerequisite(packet):
    path=Path(packet['fault_audit_file']);require(digest(path)==FAULT_AUDIT,'BF2 audit absent or changed')
    value=json.loads(path.read_text());require(value['status']=='STOPPED_B_COMPONENTS_VERIFIED' and
        value['classification']=='FIRMWARE_OUTPUT_ALLOCATION_REJECTED_WITHOUT_RESET' and
        value['allocator_failures']==1 and value['panic_protection_verified'] is True and
        value['maximum_load_reply_pass'] is False and value['boot_id']==PRIOR_BOOT and value['final_state']['output_active'] is False and
        value['final_state']['state']=='empty' and value['final_state']['owner_id'] is None,'Demonstrated inactive BF2 fault')
    state=subprocess.check_output(['systemctl','show','phase115-r3-v2-bf2.service','-p','MainPID','-p','ActiveState'],text=True,timeout=5)
    require('MainPID=0' in state.splitlines() and 'ActiveState=inactive' in state.splitlines(),'BF2 still active')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no device or filesystem changes.');return
    require(os.geteuid()==0,'wspr5 root required');os.umask(0o077);root=a.root.resolve(strict=True)
    require(digest(root/'packet.json')==a.packet_sha256,'Changed repair packet')
    packet=validate(json.loads((root/'packet.json').read_text()));require(packet['root']==str(root),'Changed root')
    validate_stage(root,packet)
    require('scripts/phase11_5_r3_v2_parallel_b_paged_repair.py' in packet['stage_sha256'],'Missing repair runner manifest')
    prerequisite(packet)
    with (root/'deployment-result.json').open('x') as f:json.dump(dict(status='STARTING'),f)
    run(root,packet)

if __name__=='__main__':main()
