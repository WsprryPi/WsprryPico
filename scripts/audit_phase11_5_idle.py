#!/usr/bin/env python3
"""Offline A2 observer audit: reconstruct wire bytes before checking reported samples."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from phase11_5_inventory import require, loads_console
from validate_wtp_contract import crc32c, loads_strict, SchemaValidator
from phase11_5_network_fixture import HOST_BOOT
from phase11_5_pilot_supervisor import finished


def frames(buffer):
    result=[]
    while len(buffer)>=16:
        magic,version,encoding,flags,length,crc=struct.unpack('>4sBBHII',buffer[:16])
        require((magic,version,encoding,flags)==(b'WTPF',1,1,0) and 0<length<=65536,
                'Bad wire header')
        if len(buffer)<16+length:break
        payload=buffer[16:16+length]
        require(crc32c(payload)==crc,'Bad wire CRC')
        result.append(loads_strict(payload.decode()));buffer=buffer[16+length:]
    return result,buffer


def audit(path, baseline_path, rf_packet=None):
    text=path.read_text();require(text.endswith('\n'),'Truncated envelope')
    rows=[json.loads(line) for line in text.splitlines()]
    require(rows and rows[0]['kind']=='start' and rows[-1]['kind']=='finish' and
            rows[-1]['value']=={'result':'CAPTURED_REQUIRES_AUDIT','faults':[]},'Missing clean finish')
    require([r['sequence'] for r in rows]==list(range(len(rows))) and
            all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])),'Envelope ordering')
    seconds=rows[0]['value']['seconds'];boot=rows[0]['value']['boot'];session=rows[0]['value']['session_id']
    baseline=finished(baseline_path,'READ_ONLY_INVENTORY')['info']
    if rf_packet is not None:
        from phase11_5_rf_observer import validate_info as rf_info, validate_status as rf_status
        from phase11_5_f1_plan import validate_rf_packet,SCHEMA as F1_SCHEMA
        validate_rf_packet(rf_packet)
        require(baseline['revision']==rf_packet['revision'] and
                baseline['system_clock_hz']==rf_packet['system_clock_hz'] and
                baseline['device_id']==rf_packet['device_id'], 'RF packet/baseline identity mismatch')
    require(hashlib.sha256(baseline_path.read_bytes()).hexdigest()==rows[0]['value']['baseline_sha256']
            and baseline['status']['boot_id']==boot,'Baseline hash/boot binding')
    require(rows[-1]['monotonic_ns']-rows[0]['monotonic_ns']>=seconds*1e9,'Interval truncated')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema)
    modes=rf_packet is not None and rf_packet.get('schema')=='phase11.5-r2-modes-v1'
    usb_actor=modes and rf_packet['submission_path']=='usb'
    wire=b'';console=b'';console_pending=False;console_value=None;messages=[];requests={};samples={}
    latest_status=None;event_id=-1;seen_request_ids=set()
    for row in rows:
        kind,value=row['kind'],row['value']
        require(kind in ('start','finish','console_tx','console_rx','wtp_tx','wtp_rx','wtp_message',
                         'info','status','health','info_finish','status_finish','health_finish') +
                         (('armed_job',) if usb_actor else ()),
                'Unexpected event or failure')
        if kind=='console_tx':
            require(not console_pending and not console and console_value is None and
                    bytes.fromhex(value['hex'])==b'INFO\n','Unexpected Console command')
            console_pending=True
        elif kind=='console_rx':
            require(console_pending,'Unsolicited Console bytes');console+=bytes.fromhex(value['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n')==1,'Console suffix')
                console_value=loads_console(console.decode().strip());console=b'';console_pending=False
        elif kind=='wtp_tx':
            decoded,left=frames(bytes.fromhex(value['hex']))
            require(not left and decoded==[value['request']],'Reported request differs from wire')
            request=decoded[0];require(not validator.errors(request,schema),'Request schema')
            require(request['session_id']==session and request['op'] in (('HELLO','STATUS','GET_CLOCK','CLAIM','LOAD','ARM','RENEW','RELEASE') if usb_actor else ('HELLO','STATUS')) and
                    request['request_id'] not in seen_request_ids,'Unexpected request/session/replay')
            seen_request_ids.add(request['request_id'])
            requests[request['request_id']]=request
        elif kind=='wtp_rx':
            decoded,wire=frames(wire+bytes.fromhex(value['hex']));messages.extend(decoded)
        elif kind=='wtp_message':
            require(messages and messages.pop(0)==value,'Reported message differs from wire')
            require(not validator.errors(value,schema),'Response schema')
            if value['type']=='event' and rf_packet is not None:
                from phase11_5_rf_observer import validate_event
                validate_event(value,boot,rf_packet)
                require(value['session_id']==session and int(value['event_id'])==event_id+1,'RF event identity/gap')
                event_id=int(value['event_id']);continue
            require(value['type']=='response' and value['ok'] is True,'Unexpected event/rejection')
            request=requests.pop(value['request_id'],None)
            require(request and request['op']==value['op'] and value['session_id']==session,'Response binding')
            if value['op']=='STATUS':latest_status=value['body']
            elif value['op']=='HELLO':require(value['body']['boot_id']==boot,'HELLO boot changed')
        elif kind in ('info','status','health'):
            samples.setdefault(kind,[]).append(row)
            if kind=='info':
                info=value['value'];require(console_value==info,'INFO differs from raw Console');console_value=None
                if rf_packet is not None:rf_info(info,{'info':baseline})
                require(info['status']['boot_id']==boot and
                        (rf_packet is not None or (info['status']['state']=='empty' and
                        info['status']['output_active'] is False)) and info['fault_stage']==0 and
                        info['fault_status']==0 and info['core0_stack_guard_valid']==1 and
                        info['core0_stack_fault_status']==0,'INFO identity/fault')
                if info['status']['engine']=='pio-dma-gp2':
                    require(info['core1_stack_guard_valid']==1 and info['core1_stack_fault_status']==0,
                            'Core 1 guard fault')
                require(info['heap_capacity_bytes']-info['allocator_peak_bytes']>=32768,'Heap reserve')
                require(all(info[k]==baseline[k] for k in ('device_id','revision','system_clock_hz',
                        'fault_hash','fault_pc','allocator_failures','tls_allocation_failures')) and
                        info['status']['engine']==baseline['status']['engine'],'Identity/allocation fault')
                for core in range(2 if info['status']['engine']=='pio-dma-gp2' else 1):
                    prefix=f'core{core}_stack_'
                    require(type(info[prefix+'guard_valid']) is int and
                            info[prefix+'guard_bottom']==baseline[prefix+'guard_bottom'] and
                            info[prefix+'guard_limit']==baseline[prefix+'guard_limit']==
                            info[prefix+'guard_bottom']+4096,'Stack reserve identity')
            elif kind=='status':
                status=value['value'];require(latest_status==status,'STATUS differs from raw WTP')
                latest_status=None
                if rf_packet is not None:rf_status(status,boot,rf_packet)
                else:
                    require(status['boot_id']==boot and status['state']=='empty' and
                            status['output_active'] is False and status['owner_id'] is None and
                            status['job_id'] is None,'STATUS authority')
            else:
                require(value['value']['boot']==HOST_BOOT and
                        value['value']['throttled']=='throttled=0x0','Host health')
    require(not wire and not console and not console_pending and console_value is None and
            not messages and not requests and latest_status is None,'Incomplete raw exchange')
    result={}
    for kind,period in [('info',1),('status',5),('health',5)]:
        values=samples.get(kind,[]);require(values,'Missing '+kind)
        times=[r['value']['began_monotonic_ns'] for r in values]
        gaps=[(b-a)/1e9 for a,b in zip(times,times[1:])]
        require(len(times)>=(seconds-1)//period and (not gaps or max(gaps)<=period+1) and
                times[-1]-times[0]>=(seconds-period-1)*1e9,'Insufficient '+kind+' coverage')
        endings=[r for r in rows if r['kind']==kind+'_finish']
        require(len(endings)==1 and endings[0]['value']==dict(samples=len(times),completed=True),
                'Missing '+kind+' finish')
        result[kind]=dict(samples=len(times),max_gap_seconds=max(gaps,default=0))
    infos=[r['value']['value'] for r in samples['info']]
    result.update(boot=boot,seconds=seconds,raw_wire_verified=True,
        max_allocator_peak_bytes=max(i['allocator_peak_bytes'] for i in infos),
        last_heap_allocated_bytes=infos[-1]['heap_allocated_bytes'])
    if rf_packet is not None:
        coverage={j['job_id']:dict(states=set(),active=False) for j in rf_packet['jobs']}
        for row in samples['status']:
            status=row['value']['value']
            if status['job_id'] in coverage:
                v=coverage[status['job_id']];v['states'].add(status['state'])
                v['active'] |= status['state']=='running' and status['output_active']
        for v in coverage.values():
            require((({'armed','running'}<=v['states']) if modes and rf_packet['submission_path']=='production' else {'loaded','armed','running','complete'}<=v['states']) and v['active'],
                    'Missing independent RF state/output coverage')
            v['states']=sorted(v['states'])
        require(samples['status'][-1]['value']['value']['state']=='empty' and
                samples['status'][-1]['value']['value']['owner_id'] is None,'Final RF job not released')
        terminal=samples['status'][-1]['value']['value']['terminal_records']
        expected_jobs=(rf_packet.get('prior_terminal_records',[])+rf_packet['jobs'])[-8:]
        require(len(terminal)==len(expected_jobs) and
                {r['job_id'] for r in terminal}=={j['job_id'] for j in expected_jobs} and
                all(r['state']=='complete' and r['output_active'] is False and 'error' not in r
                    for r in terminal),'Finite terminal history differs')
        for prior in rf_packet.get('prior_terminal_records',[]):
            retained=next((r for r in terminal if r['job_id']==prior['job_id']),None)
            require(retained is None or retained==prior,'Preserved terminal record changed')
        result['job_coverage']=coverage
        result['max_rf_service_gap_ns']=max(int(i['rf_max_service_gap_ns']) for i in infos)
        result['rf_last_observation']=infos[-1]
        result['terminal_records']=terminal
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path)
    parser.add_argument('--baseline',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(audit(args.log,args.baseline),indent=2))
