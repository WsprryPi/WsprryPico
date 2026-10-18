#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Causal NTP consistency and application-clock checks from bounded USB originals.

Usage: analyze_microchrony_capture.py capture_dir microchrony_tests output.json
Next NTP observations are proxies, never independent absolute UTC truth.
"""
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')
capture, engine, output = sys.argv[1:]
root = Path(capture)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def metrics(values):
    ordered = sorted(abs(v) for v in values)
    return {'count':len(values), 'median_abs_ns':statistics.median(ordered) if ordered else None,
            'max_abs_ns':max(ordered,default=None),
            'p95_abs_ns':ordered[min(len(ordered)-1,int(.95*len(ordered)))] if ordered else None,
            'mean_signed_ns':statistics.mean(values) if values else None}

def application_bindings(board, expected):
    """Verify recorded payloads independently of the observer's stored verdict."""
    points=[]
    for path in sorted(root.glob(board+'-binding-*.json')):
        record=json.loads(path.read_text())
        report['inputs_sha256'][path.name]=digest(path)
        info_path=root/path.name.replace('-binding-','-observe-')
        assert record['info']==json.loads(info_path.read_text()),'binding INFO differs'
        v=record['info']['response'];a,z=record['before']['body'],record['after']['body']
        assert json.loads(record['info']['raw_line'])==v,'raw INFO differs'
        la,li,lz=a['network']['ntp_learning'],v['network']['ntp_learning'],z['network']['ntp_learning']
        valid=(a['active_source']==z['active_source']=='sntp' and
               a['source_disagreement'] is False and z['source_disagreement'] is False and
               a['target']==z['target'] and a['target']['scope']=='member' and
               a['target']['device_id']==v['device_id']==expected['device_id'] and
               a['target']['boot_id']==v['status']['boot_id']==expected['status']['boot_id'] and
               a['firmware']==z['firmware']==v['firmware']==expected['firmware'] and
               a['source_revision']==z['source_revision']==v['revision']==expected['revision'] and
               a['clock_generation']==z['clock_generation'] and
               a['nominal_sample_hz']==z['nominal_sample_hz']==v['system_clock_hz']==138000000 and
               la['rf_candidate']['generation']==li['rf_candidate']['generation']==lz['rf_candidate']['generation'] and
               a['utc_rate_ppb']==z['utc_rate_ppb']==la['rate_ppb']==li['rate_ppb']==lz['rate_ppb'] and
               la['utc_frequency_ppb']==li['utc_frequency_ppb']==lz['utc_frequency_ppb'] and
               v['status']['clock_state']=='synchronized')
        assert not record['bound'] or valid,'stored authority verdict is unsupported'
        points.append({'file':path.name,'verified':valid,'info':v,
                       'clock_generation':a['clock_generation']})
    pairs=[];transitions=0
    for a,b in zip(points,points[1:]):
        if not a['verified'] or not b['verified']:continue
        va,vb=a['info'],b['info'];la,lb=va['network']['ntp_learning'],vb['network']['ntp_learning']
        if a['clock_generation']!=b['clock_generation']:continue
        if la['rf_candidate']['generation']!=lb['rf_candidate']['generation']:continue
        if la['rate_ppb']!=lb['rate_ppb'] or ((int(la['remaining_correction_ns'])==0)!=(int(lb['remaining_correction_ns'])==0)):
            transitions+=1
            continue
        raw_delta=int(vb['status']['monotonic_now_ns'])-int(va['status']['monotonic_now_ns'])
        utc_delta=int(vb['status']['utc_now_ns'])-int(va['status']['utc_now_ns'])
        assert raw_delta>0
        projected=raw_delta*(10**9+la['rate_ppb'])//10**9
        pairs.append({'from':a['file'],'to':b['file'],'raw_delta_ns':raw_delta,
                      'rate_ppb':la['rate_ppb'],'mapping_error_ns':utc_delta-projected})
    return {'source_and_application_binding':bool(points and any(p['verified'] for p in points)),
            'bracketed_points':len(points),'verified_points':sum(p['verified'] for p in points),
            'constant_segment_pairs':len(pairs),'nonzero_rate_pairs':sum(p['rate_ppb']!=0 for p in pairs),
            'max_abs_mapping_error_ns':max((abs(p['mapping_error_ns']) for p in pairs),default=None),
            'within_3us':bool(pairs and all(abs(p['mapping_error_ns'])<=3000 for p in pairs)),
            'finite_slew_transition_pairs':transitions,
            'transition_limit':'Exact slew endpoint is absent from INFO; transition pairs are not constant-rate accuracy claims.',
            'pairs':pairs}

report = {'schema':'microchrony-live-causal-analysis/1',
          'engine_sha256':digest(engine), 'analysis_sha256':digest(__file__),
          'independent_utc_or_rf_qualification':False,
          'method':'Each admitted original predicts the next original before ingesting it; single-source replay compares identical preceding inputs and common available holdouts.',
          'limits':['Accepted records only; this does not reconstruct rejected packets.',
                    'Counterfactual single-source replays do not recreate pool combination or target servo state.',
                    'Future NTP observations include network asymmetry and are not independent UTC truth.',
                    'Server processing is removed from path delay; remote root delay is charged to dispersion.'],
          'inputs_sha256':{}, 'boards':{}}
for board in ('A','B'):
    infos=[]; cohorts={}; snapshots={}; pages=[]
    expected_devices={'A':'fd6127d11d6aca42a9905fa3fb1bf1d5','B':'29f20b7342051ef947aa56cb9d4fab42'}
    for path in sorted(root.glob(board+'-observe-*.json')):
        wrapper=json.loads(path.read_text());v=wrapper['response'];infos.append(v)
        report['inputs_sha256'][path.name]=digest(path)
    assert infos,'missing INFO binding'
    expected=infos[0]
    for v in infos:
        assert v['device_id']==expected_devices[board]
        assert v['status']['owner_id'] is None and v['status']['output_active'] is False and v['status']['enabled'] is False
        for fault in ('allocator_failures','flash_read_failures','flash_erase_failures','flash_program_failures','core0_stack_fault_status','core1_stack_fault_status'):
            assert int(v[fault])==0,fault
        assert v['core0_stack_guard_valid']==v['core1_stack_guard_valid']==1
        assert v['status']['storage_healthy'] and v['ntp_retention']['healthy']
        assert (v['firmware'],v['revision'],v['status']['boot_id'])==(expected['firmware'],expected['revision'],expected['status']['boot_id'])
    for path in sorted(root.glob(board+'-history-*.json')):
        wrapper=json.loads(path.read_text());v=wrapper['response']
        report['inputs_sha256'][path.name]=digest(path)
        if v.get('ok') is not True:continue
        pages.append(wrapper)
        assert (v['device_id'],v['boot_id'],v['firmware'],v['revision'])==(expected_devices[board],expected['status']['boot_id'],expected['firmware'],expected['revision'])
        header_keys=('schema','device_id','boot_id','firmware','revision','slot','endpoint','clock_epoch','generation','count','frequency_ppb','skew_ppb','runs')
        identity={k:v[k] for k in header_keys}
        # The wire token hashes the open identity-object prefix, before page fields.
        prefix=json.dumps(identity,separators=(',',':'),ensure_ascii=False)[:-1]
        token=hashlib.sha256(prefix.encode()).hexdigest()
        assert token==v['token'],'history token does not reconstruct'
        assert 0<=v['slot']<4 and 0<=v['count']<=64 and 0<=v['cursor']<=v['next_cursor']<=v['count']
        assert v['next_cursor']==v['cursor']+len(v['records'])
        assert v['more']==(v['next_cursor']<v['count'])
        key=(v['boot_id'],v['slot'],v['endpoint'],v['clock_epoch'])
        cohort=cohorts.setdefault(key,{})
        snap=snapshots.setdefault((key,v['token']),{'count':v['count'],'records':{},'positions':{}})
        for position,record in enumerate(v['records'],v['cursor']):
            if position in snap['positions']:assert snap['positions'][position]==record
            snap['positions'][position]=record
            identifier=record['id']
            if identifier in cohort:assert cohort[identifier]==record,'original changed'
            cohort[identifier]=record;snap['records'][identifier]=record
    complete=sum(len(s['records'])==s['count'] and set(s['positions'])==set(range(s['count'])) for s in snapshots.values())
    board_report={'info_reads':len(infos),'complete_snapshots':complete,
                  'partial_snapshot_attempts':len(snapshots)-complete,
                  'cohorts':[],'unbound_clock_consistency':{},'final':{}}
    for key,by_id in cohorts.items():
        records=sorted(by_id.values(),key=lambda r:int(r['receive_raw_ns']))
        assert len({r['id'] for r in records})==len(records)
        parsed=[]
        for r in records:
            send=int(r['send_raw_ns']);receive=int(r['receive_raw_ns'])
            sr=int(r['server_receive_ns']);st=int(r['server_send_ns'])
            assert receive>=send and st>=sr
            raw=(send+receive)//2;utc=(sr+st)//2
            delay=max(1,receive-send-(st-sr))
            wire_delay=r['root_delay_16_16']
            signed_delay=wire_delay if wire_delay<2**31 else wire_delay-2**32
            dispersion=r['root_dispersion_16_16']/65536+max(0,signed_delay)/131072
            parsed.append((r,raw,utc,delay,dispersion))
        rows=[]
        for current,future in zip(parsed,parsed[1:]):
            r,raw,utc,delay,dispersion=current
            rows.append(f"{r['id']} 1 {raw} {utc} {delay} {dispersion:.15g} 1 {future[1]} {future[2]}")
        predictions={}
        if rows:
            result=subprocess.run([engine,'replay'],input='\n'.join(rows)+'\n',text=True,
                                  capture_output=True,check=True,timeout=15)
            for line in result.stdout.splitlines():
                mode,identifier,error,bound,age,usable,rate=map(int,line.split())
                predictions.setdefault(identifier,{})[mode]=(error,bound,age,usable,rate)
        common=[p for p in predictions.values() if all(p[m][3] for m in (0,1,2))]
        modes={name:metrics([p[m][0] for p in common]) for m,name in
               enumerate(('offset_only','phase_only','microchrony'))}
        board_report['cohorts'].append({'boot_id':key[0],'slot':key[1],'endpoint':key[2],
            'clock_epoch':key[3],'unique_originals':len(records),
            'span_ns':parsed[-1][1]-parsed[0][1] if parsed else 0,
            'rtt_median_ns':statistics.median(int(r['rtt_ns']) for r in records) if records else None,
            'holdouts':len(predictions),'common_available_holdouts':len(common),
            'modes_on_common_holdouts':modes,
            'rate_reduces_median_vs_phase_only':bool(common and modes['microchrony']['median_abs_ns']<modes['phase_only']['median_abs_ns']),
            'frequency_wins':sum(abs(p[2][0])<abs(p[1][0]) for p in common),
            'frequency_losses':sum(abs(p[2][0])>abs(p[1][0]) for p in common),
            'coverage_against_ntp_proxy':{name:sum(abs(p[m][0])<=p[m][1] for p in common)
                for m,name in enumerate(('offset_only','phase_only','microchrony'))}})
    bindings=[]
    for a,b in zip(infos,infos[1:]):
        sa,sb=a['status'],b['status'];la=a['network']['ntp_learning'];lb=b['network']['ntp_learning']
        if sa['clock_state']!='synchronized' or sb['clock_state']!='synchronized':continue
        if a['status']['boot_id']!=b['status']['boot_id']:continue
        if la['rf_candidate']['generation']!=lb['rf_candidate']['generation']:continue
        if la['rate_ppb']!=lb['rate_ppb']:continue
        # An unchanged rate and generation selects one constant-rate segment.
        if (int(la['remaining_correction_ns'])==0)!=(int(lb['remaining_correction_ns'])==0):continue
        raw_delta=int(sb['monotonic_now_ns'])-int(sa['monotonic_now_ns'])
        utc_delta=int(sb['utc_now_ns'])-int(sa['utc_now_ns'])
        expected_elapsed=raw_delta*(10**9+la['rate_ppb'])//10**9
        bindings.append({'raw_delta_ns':raw_delta,'expected_rate_ppb':la['rate_ppb'],
                         'mapping_error_ns':utc_delta-expected_elapsed})
    board_report['unbound_clock_consistency']={'source_and_application_binding':False,
        'constant_segment_pairs':len(bindings),
        'nonzero_rate_pairs':sum(p['expected_rate_ppb']!=0 for p in bindings),
        'max_abs_mapping_error_ns':max((abs(p['mapping_error_ns']) for p in bindings),default=None),
        'within_3us':bool(bindings and all(abs(p['mapping_error_ns'])<=3000 for p in bindings)),
        'pairs':bindings}
    board_report['verified_application_clock']=application_bindings(board,expected)
    if infos:
        first,last=infos[0],infos[-1]
        n=last['network'];s=last['status']
        board_report['final']={'firmware':last['firmware'],'boot_id':s['boot_id'],
            'clock_state':s['clock_state'],'owner_id':s['owner_id'],'output_active':s['output_active'],
            'enabled':s['enabled'],'learning':n['ntp_learning'],'pool':n['ntp_pool'],
            'retention':last['ntp_retention'],
            'max_core0_stack_used_bytes':max(i['core0_stack_used_bytes'] for i in infos),
            'max_core1_stack_used_bytes':max(i['core1_stack_used_bytes'] for i in infos),
            'min_heap_available_bytes':min(i['heap_available_bytes'] for i in infos),
            'max_process_us':max(p['max_process_us'] for i in infos for p in i['network']['ntp_pool']['peers']),
            'synchronized_reads':sum(i['status']['clock_state']=='synchronized' for i in infos),
            'launch_timing_gate_reads':sum(i['status']['clock_state']=='synchronized' and
                int(i['status']['uncertainty_ns'])<=500000000 and int(i['status']['sync_age_ns'])<=90000000000 for i in infos),
            'max_uncertainty_ns':max((int(i['status']['uncertainty_ns']) for i in infos if i['status']['clock_state']=='synchronized'),default=None),
            'total_queries':sum(p['queries'] for p in n['ntp_pool']['peers'])}
    total_originals=sum(len(c) for c in cohorts.values())
    if infos:
        accepted=sum(p['accepted'] for p in infos[-1]['network']['ntp_pool']['peers'])
        slots={}
        for peer in infos[-1]['network']['ntp_pool']['peers']:
            count=sum(len(c) for k,c in cohorts.items() if k[1]==peer['slot'])
            slots[str(peer['slot'])]={'unique_originals':count,'accepted_packets':peer['accepted'],'complete':count==peer['accepted']}
        board_report['accepted_original_visibility']={'unique_originals':total_originals,
             'final_accepted_packets':accepted,'complete':all(p['complete'] for p in slots.values()),'slots':slots}
        baseline_path=root/'capture-baseline.json'
        if baseline_path.exists():
            report['inputs_sha256'][baseline_path.name]=digest(baseline_path)
            baseline=json.loads(baseline_path.read_text())['boards'][board]
            frontiers=sorted(root.glob(board+'-baseline-frontier-*.json'));assert frontiers
            frontier=json.loads(frontiers[-1].read_text())
            report['inputs_sha256'][frontiers[-1].name]=digest(frontiers[-1])
            fv=frontier['response']
            assert (fv['device_id'],fv['status']['boot_id'],fv['firmware'],fv['revision'])==(
                expected['device_id'],expected['status']['boot_id'],expected['firmware'],expected['revision'])
            initial=set()
            for page in pages:
                if page['host_wall_ns']>=frontier['host_wall_start_ns']:continue
                v=page['response']
                for sample in v['records']:
                    initial.add((v['slot'],v['endpoint'],v['clock_epoch'],sample['id']))
            for slot,value in slots.items():
                base=baseline[slot];first=next(p for p in fv['network']['ntp_pool']['peers'] if str(p['slot'])==slot)
                count=sum(key[0]==int(slot) for key in initial)
                assert count==base['captured_originals'] and first['accepted']==base['accepted_packets']
                new_captured=value['unique_originals']-count
                new_accepted=value['accepted_packets']-first['accepted']
                assert new_captured==new_accepted,'missing newly accepted original'
                value.update(new_captured=new_captured,new_accepted=new_accepted,
                             pre_capture_missing=base['unseen_before_capture'],complete_since_baseline=True)
            board_report['accepted_original_visibility']['complete_since_baseline']=True
            board_report['accepted_original_visibility']['pre_capture_missing']=sum(v['pre_capture_missing'] for v in slots.values())
    report['boards'][board]=board_report
Path(output).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({b:{'info_reads':v['info_reads'],'unbound_clock_consistency':{k:x for k,x in v['unbound_clock_consistency'].items() if k!='pairs'},
      'cohorts':v['cohorts']} for b,v in report['boards'].items()},indent=2))
