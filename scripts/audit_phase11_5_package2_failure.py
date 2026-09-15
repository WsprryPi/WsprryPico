"""Raw audit of the frozen P2 LOAD allocation failure; never grants acceptance."""
from pathlib import Path
import sys,json,hashlib
from phase11_5_r3_preflight import audit_inventory
from phase11_5_rf_reservation import BOARDS,inactive
from phase11_5_pilot_supervisor import configuration
from phase11_5_inventory import loads_console
from audit_phase11_5_idle import frames


def audit(root):
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    packet='d5d9b1a813909e3f880084887cf7962bbe7a12b76944cf3d73d9367d88f46c9d'
    assert sha(root/'packet.json')==packet
    p=json.loads((root/'packet.json').read_text());assert p['source_revision']=='8dd6f0812292e9264c2a72745078a95ee606c191'
    for n,h in p['stage_sha256'].items():assert sha(root/n)==h
    values={}
    for phase in ('before','final'):
     values[phase]={}
     for b,(serial,device) in BOARDS.items():
      path=root/(phase+'-'+b+'.stdout');assert not path.with_suffix('.stderr').read_bytes()
      values[phase][b]=audit_inventory(path,dict(serial=serial,device_id=device),p['b_session' if b=='b' else 'inventory_session'],p['stage_sha256']['scripts/phase11_5_inventory.py'])
     inactive(values[phase])
    for b in BOARDS:
     old_config,new_config=configuration(values['before'][b]),configuration(values['final'][b])
     if b=='a':
      assert old_config[1]['station_mac']=='88:a2:9e:0a:60:df' and new_config[1]['station_mac']==''
      old_config[1].pop('station_mac');new_config[1].pop('station_mac')
     assert old_config==new_config
     if b=='b':assert values['before'][b]['wtp']['STATUS']['boot_id']==values['final'][b]['wtp']['STATUS']['boot_id']
    assert values['before']['b']['wtp']['STATUS']==values['final']['b']['wtp']['STATUS']
    assert values['before']['a']['wtp']['STATUS']['terminal_records']==p['initial_terminal_records']
    rows=[json.loads(x) for x in (root/'rf.jsonl').read_text().splitlines()]
    assert rows[0]['value']['packet_sha256']==packet
    requests=[];responses=[];rx=b'';console=b'';solicited=False;decoded=None;infos=[]
    for r in rows:
     v=r['value'];kind=r['kind']
     if kind in ('wtp_tx','capacity_tx'):
      messages,left=frames(bytes.fromhex(v['hex']));assert not left and messages==[v['request']]
      requests.append(v['request'])
     elif kind in ('wtp_rx','capacity_rx'):
      messages,rx=frames(rx+bytes.fromhex(v['hex']));responses+=messages
     elif kind=='console_tx':
      assert not solicited and not console and decoded is None and bytes.fromhex(v['hex'])==b'INFO\n'
      solicited=True
     elif kind=='console_rx':
      assert solicited;console+=bytes.fromhex(v['hex'])
      if console.endswith(b'\n'):
       assert console.count(b'\n')==1
       decoded=loads_console(console.decode().strip());console=b'';solicited=False
     elif kind=='info':
      assert decoded==v['value'];infos.append(decoded);decoded=None
    load,=[q for q in requests if q['op']=='LOAD'];job,=p['jobs'];assert load['body']==job
    assert len(bytes.fromhex(next(r['value']['hex'] for r in rows if r['kind']=='wtp_tx' and r['value']['request']['op']=='LOAD')))==52105
    assert not any(q['op']=='ARM' for q in requests)
    assert not any(v.get('request_id')==load['request_id'] for v in responses)
    assert not any(r['kind']=='capacity_tx' for r in rows)
    assert not any(json.loads(x)['kind']=='http_tx' for x in (root/'contention.jsonl').read_text().splitlines())
    final=values['final']['a']['wtp']['STATUS'];assert final['state']=='empty' and final['job_id'] is None
    i=values['final']['a']['info'];assert i['recovery_boot'] is True and i['fault_stage']==5 and i['fault_allocation_recorded'] is True and i['fault_allocation_request_bytes']==20480 and i['fault_allocation_returned_null'] is True
    assert final['boot_id']=='4768a88991247131bdc7c0fc421dbe8f'
    for phase,name,state in [('before','acquired','HELD'),('final','released','RELEASED')]:
     r=json.loads((root/('rf-reservation-'+name+'.json')).read_text());assert r['packet_sha256']==packet and r['state']==state and r['boards']==inactive(values[phase])
    result=json.loads((root/'rf-result.json').read_text());assert result['status']=='STOPPED_FINAL_STATE_UNVERIFIED' and result['rf_duration_ns_charged']==0 and result['armed_jobs']==[]
    load_result=json.loads((root/'contention-result.json').read_text());assert 'P2 finite deadline' in str(load_result)
    out=dict(status='LOAD_ALLOCATION_FAULT_AND_NEW_BOOT_INACTIVITY_VERIFIED',packet_sha256=packet,rf_seconds_charged=0,unplanned_watchdog_reboots=1,old_boot=p['boot_id'],new_boot=final['boot_id'],allocation_fault={k:v for k,v in i.items() if k.startswith('fault_')},load_wire_bytes=52105,load_response_received=False,prior_terminal_history_lost=True,accepted_components=[],capacity_attempted=False,http_attempted=False,persisted_configuration_fields_preserved=True,recovery_runtime_station_mac_empty=True,final_boards=inactive(values['final']),reservation_released=True,continuous_rf_timing_accepted=False,contention_result=load_result,evidence_sha256={n:sha(root/n) for n in ['packet.json','rf.jsonl','rf-result.json','contention.jsonl','contention-result.json','before-a.stdout','before-b.stdout','final-a.stdout','final-b.stdout','rf-reservation-acquired.json','rf-reservation-released.json']})
    return out


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.root)))
