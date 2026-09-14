"""Pure, finite native Pi submission policy. No process, transport or RF access."""
import configparser
import copy
import hashlib
import io
import json
import time
from phase11_5_inventory import require

DURATIONS={'qrss':143250000000,'fskcw':143250000000,'dfcw':155750000000}
PI_SOURCE='bba4024ec310589b9f4813e9c6fb3082836e726f'
PI_BINARY='b184cfba8b72a2cb73def207ab01792c5eaaae033607a926593dbad1e91cf124'


def parse_ini(text):
    c=configparser.ConfigParser(interpolation=None,strict=True);c.optionxform=str;c.read_string(text)
    require(not c.defaults(),'Explicit INI settings required')
    return c


def render_ini(base_text,mode,start_utc_ns,root):
    require(mode in DURATIONS and type(start_utc_ns) is int and start_utc_ns%10**9==0,'Native mode/whole-second start')
    c=parse_ini(base_text)
    require(c['Operation']['Transmit']=='false' and c['Operation']['Enable on Boot']=='Never' and
        c['Operation']['Transmit Backend']=='wtp' and all(c['Operation'][k]=='false' for k in
        ['Use LED','Use Amp','Use Shutdown']),'Reviewed inactive base required')
    utc=time.gmtime(start_utc_ns//10**9)
    c['Operation'].update({'Mode':mode.upper(),'Transmit':'true','Enable on Boot':'Follow'})
    c['CW'].update({'Message':'?'*32,'Base Frequency':'135495' if mode=='fskcw' else '135500',
        'Shift Hz':'5','Dot Seconds':'0.35' if mode=='dfcw' else '0.25',
        'Intra Element Gap':'1','Inter Character Gap':'3','Inter Word Gap':'7',
        'DFCW Intra Element Gap':'1','DFCW Inter Character Gap':'3','DFCW Inter Word Gap':'7',
        'Fade Shape':'none','Fade In Ms':'0','Fade Out Ms':'0','Repeat Minutes':'60',
        'Start Minute':str(utc.tm_min),'Start Second':str(utc.tm_sec)})
    for key,file in [('TLS CA File','client-ca.crt'),('TLS Client Certificate','client.crt'),('TLS Client Key','client.key')]:
        c['WTP'][key]=str(root/'credentials/controller'/file)
    out=io.StringIO();c.write(out);return out.getvalue()


def validate_ini(actual,base,mode,start_utc_ns,root):
    # Reject every unreviewed setting, including ancillary GPIO and calibration.
    expected=render_ini(base,mode,start_utc_ns,root)
    require(actual==expected,'Native INI differs from the frozen complete derivation')


def configuration_template(job):
    """Exact frozen bba4024 DFCW config-builder conversion, independently exported.

    duration_cast truncates binary64 (0.35 * 3) seconds to 1049999999 ns.
    Direct chrono 350ms templates bypassed that production input conversion.
    This corrects an evidence expectation, not the native application's timing.
    """
    result=copy.deepcopy(job)
    if job['mode']=='dfcw':
        cursor=0;changed=0
        for e in result['events']:
            if not e['rf_on'] and e['duration_ns']=='1050000000':
                e['duration_ns']='1049999999';changed+=1
            e['offset_ns']=str(cursor);cursor+=int(e['duration_ns'])
        require(changed==31,'Frozen DFCW configuration gap count')
        result['total_duration_ns']=str(cursor)
    validate_template(result,job['mode'],'production-config-builder-v1')
    return result


def validate_template(job,mode,policy='direct-compiler-v1'):
    require(policy in ['direct-compiler-v1','production-config-builder-v1'],'Native compiler input policy')
    duration=DURATIONS.get(mode,0)-(31 if mode=='dfcw' and policy=='production-config-builder-v1' else 0)
    require(mode in DURATIONS and job['mode']==mode and job['profile']=='rf-events/1' and
        job['total_duration_ns']==str(duration) and job['allow_frequency_adjustment'] is True and
        len(job['events'])==383,'Actual native compiler shape/duration')
    cursor=0;frequencies=set()
    for event in job['events']:
        require(int(event['offset_ns'])==cursor and int(event['duration_ns'])>0 and type(event['rf_on']) is bool,'Native timeline')
        cursor+=int(event['duration_ns'])
        if event['rf_on']:
            require('frequency_nhz' in event,'Missing native RF frequency');frequencies.add(int(event['frequency_nhz']))
        else:require('frequency_nhz' not in event,'Off event frequency')
    expected={135500000000000} if mode=='qrss' else {135500000000000,135495000000000 if mode=='fskcw' else 135505000000000}
    require(cursor==duration and frequencies==expected,'Native duration/frequency bounds')
    if policy=='production-config-builder-v1':
        expected_sha={'qrss':'66e569e356ee07673f6ac9eb5018110355096f6baad13841f83bb422e127366d',
            'fskcw':'2bbc23703cf1fe7df32b0eabef1a8c8f8421364122207ba12d484a87d7f259a1',
            'dfcw':'f1f274704c67c1ff4869714ba70a225f327fa2f52057424093bec95320426709'}[mode]
        raw=json.dumps(dict(job,job_id='a'*32),sort_keys=True,separators=(',',':')).encode()
        require(hashlib.sha256(raw).hexdigest()==expected_sha,'Exact production config-builder export')
    return job


def validate_binding(binding,packet,start_utc_ns,now_utc_ns):
    require(binding['phase']=='waiting' and binding['identity']['device_id']==packet['device_id'] and
        binding['identity']['boot_id']==packet['boot_id'] and binding['network']['resolved_address']=='10.77.15.10' and
        binding['network']['authenticated_identity']=='wsprrypico-0a60df.local','Native identity before dispatch')
    require(int(binding['start_utc_ns'])==start_utc_ns and now_utc_ns+30_000_000_000<int(binding['dispatch_utc_ns']) and
        int(binding['dispatch_utc_ns'])<=start_utc_ns,'Native binding dispatch reserve')
    for key in ['session_id','owner_id','job_id']:
        value=binding[key];require(isinstance(value,str) and len(value)==32 and all(c in '0123456789abcdef' for c in value),'Native binding identifier')
    require(binding['job_id'].endswith('0000000000000001'),'Exactly the first native job')
    return binding


def validate_initial(status,packet):
    initial=packet['native']['initial_authority']
    require(set(initial)=={'state','job_id'} and initial['state'] in ['empty','complete','aborted'],
        'Native frozen initial lifecycle')
    require(status['boot_id']==packet['boot_id'] and status['owner_id'] is None and
        status['output_active'] is False and all(status[k]==v for k,v in initial.items()),
        'Native initial authority differs from reviewed boundary')
    if initial['state']=='empty':require(initial['job_id'] is None,'Native Empty job')
    else:
        require(any(t['job_id']==initial['job_id'] and t['state']==initial['state'] and
            t['output_active'] is False and 'error' not in t for t in status['terminal_records']),
            'Native initial terminal history')


def validate_host_scope(host,binding,packet,completed_seen):
    require(host['identity']['boot_id']==packet['boot_id'] and host['identity']['device_id']==packet['device_id'] and
        host['session_id']==binding['session_id'],'Native application identity drift')
    job=host.get('job')
    report=host.get('last_report')
    if report and report.get('job_id')==binding['job_id'] and report.get('outcome')=='complete':
        require(report['execution']['ok'] is True and report['execution']['faulted'] is False and
            report['execution']['stopped'] is False,'Native completed report execution')
        job=report['job']
    if job and job.get('job_id')==binding['job_id'] and job.get('state')=='complete':
        require(job.get('authoritative') is True and job.get('output_active') is False and
            job.get('device_output_active') is False and job['boot_id']==packet['boot_id'],
            'Native host completion authority')
        completed_seen=True
    if host.get('job_id') not in [None,binding['job_id']]:
        require(completed_seen and host['phase']=='waiting' and
            host['job_id']==binding['job_id'][:-16]+'0000000000000002' and
            int(host['start_utc_ns'])==int(binding['start_utc_ns'])+3600_000_000_000 and
            int(host['dispatch_utc_ns'])>int(binding['start_utc_ns'])+packet['runtime_seconds']*10**9,
            'Native unexpected subsequent dispatch')
    return completed_seen
