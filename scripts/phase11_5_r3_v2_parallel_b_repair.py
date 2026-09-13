#!/usr/bin/env python3
"""One B-only repair flash after independently confirmed BF1 allocation panic."""
import argparse,json,os,re,subprocess
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_v2_parallel_b_deploy import run,validate_stage,B_SERIAL,B_DEVICE,AUTHORIZATION

SCHEMA='phase11.5-r3-v2-parallel-b-repair-v1'
SOURCE='48ef82c7dedfa5b073c486dd0620afde33f71ab6'
IMAGE='10c3ae9445d5f508604ae732dda15eb00cd28fcf964167cd96f75e7f50fd9929'
FAULT_AUDIT='0203df0e3c64a8f092d0cac6b20dbf84f6f201ea863c376019e22efe2dd2a3dc'
PRIOR_BOOT='de3aa3fcb1e87d5db95985509cd10110'

def validate(packet):
    require(packet['schema']==packet['r3_scope']==SCHEMA and packet['serial']==B_SERIAL and
        packet['device_id']==B_DEVICE and packet['source_revision']==SOURCE and packet['image_sha256']==IMAGE and
        packet['authorization_sha256']==AUTHORIZATION,'Identified B repair only')
    for k,v in dict(runtime_seconds=300,cleanup_seconds=150,flashes=1,bootsel_commands=1,
            rf_jobs=0,arm_commands=0,loads=0,configuration_writes=0,wifi_cycles=0).items():
        require(type(packet[k]) is int and packet[k]==v,'Exact repair budget: '+k)
    require(packet['prior_revision']=='c5f00b6109cc' and packet['prior_boot']==PRIOR_BOOT and
        packet['fault_audit_sha256']==FAULT_AUDIT and
        packet['fault_audit_file']=='/home/pi/phase11-5-r3-v2-parallel-b-functional-bf1-20260913/independent-audit.json',
        'BF1 confirmed failure prerequisite')
    require(re.fullmatch('[0-9a-f]{32}',packet['inventory_session']) and packet['inventory_session']!='0'*32 and
        packet['image_file']=='candidate.uf2' and packet['root'].startswith('/home/pi/phase11-5-r3-v2-parallel-b-deploy-') and
        '..' not in Path(packet['root']).parts and str(Path(packet['root']))==packet['root'],'Private repair scope')
    return packet

def prerequisite(packet):
    path=Path(packet['fault_audit_file']);require(digest(path)==FAULT_AUDIT,'BF1 audit absent or changed')
    value=json.loads(path.read_text());require(value['status']=='STOPPED_B_COMPONENTS_VERIFIED' and
        value['classification']=='FIRMWARE_ALLOCATION_PANIC' and value['failed_allocation_bytes']==54917 and
        value['diagnostic_boot_id']==PRIOR_BOOT and value['final_state']['output_active'] is False and
        value['final_state']['state']=='empty' and value['final_state']['owner_id'] is None,'Demonstrated inactive BF1 fault')
    state=subprocess.check_output(['systemctl','show','phase115-r3-v2-bf1.service','-p','MainPID','-p','ActiveState'],text=True,timeout=5)
    require('MainPID=0' in state.splitlines() and 'ActiveState=inactive' in state.splitlines(),'BF1 still active')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no device or filesystem changes.');return
    require(os.geteuid()==0,'wspr5 root required');os.umask(0o077);root=a.root.resolve(strict=True)
    require(digest(root/'packet.json')==a.packet_sha256,'Changed repair packet')
    packet=validate(json.loads((root/'packet.json').read_text()));require(packet['root']==str(root),'Changed root')
    validate_stage(root,packet)
    require('scripts/phase11_5_r3_v2_parallel_b_repair.py' in packet['stage_sha256'],'Missing repair runner manifest')
    prerequisite(packet)
    with (root/'deployment-result.json').open('x') as f:json.dump(dict(status='STARTING'),f)
    run(root,packet)

if __name__=='__main__':main()
