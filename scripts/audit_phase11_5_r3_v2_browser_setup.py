"""Audit the original browser trust failure and corrected GET-only trust probe."""
import base64,hashlib,json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_preflight import audit_inventory
from phase11_5_pilot_supervisor import configuration
from audit_phase11_5_r3_v2_browser import body_bytes,ORIGIN,PEER
from validate_wtp_contract import unique_object,reject_constant
PACKETS={'b2':'21569af32117cd0ea8bb1117446e3cdf55584325429b5a88abc6b55a3723db5e',
'b6':'2f1d5f744042fa65923d21e8d26e0f25d1ce614c52cfdb39b0a7cb3adc8adc91',
'p0':'dcdbdb5dbba70ac47ab3c9f691926940d8b484c0f5752106224205e39b13be4c'}

def audit(root,kind):
 require(kind in PACKETS and digest(root/'packet.json')==PACKETS[kind],'Frozen setup packet')
 p=json.loads((root/'packet.json').read_text());raw=(root/'browser.jsonl').read_text()
 require(raw.endswith('\n'),'Truncated browser trace')
 rows=[json.loads(x,object_pairs_hook=unique_object,parse_constant=reject_constant) for x in raw.splitlines()]
 require([r['sequence'] for r in rows]==list(range(len(rows))) and
  all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])) and
  rows[0]['kind']=='start' and rows[-1]['kind']=='finish' and
  rows[0]['value']==dict(packet_sha256=PACKETS[kind],netns=p['netns']),'Browser provenance/chronology')
 result=json.loads((root/'browser-result.json').read_text());require(rows[-1]['value']==result and
  result['rf_jobs_charged']==0 and result['rf_duration_ns_charged']=='0' and result['cases']==[],'Zero-RF accounting')
 requests=[r for r in rows if r['kind']=='network_request'];guards=[r for r in rows if r['kind']=='request_guard']
 require(all(r['value']['request']['method']=='GET' for r in requests+guards) and
  not any(r['kind']=='arm_charge' for r in rows),'No mutation attempted')
 guard_requests={r['value']['network_id']:r['value']['request'] for r in guards}
 target_requests={r['value']['requestId']:r['value']['request'] for r in requests
  if not r['value']['request']['url'].startswith('data:')}
 require(len(guard_requests)==len(guards) and set(guard_requests)==set(target_requests) and
  all(all(guard_requests[k].get(field)==q.get(field) for field in ['url','method','postData'])
   for k,q in target_requests.items()),'Guard/actual setup request mismatch')
 if kind=='b6':
  from audit_phase11_5_r3_v2_browser_observer import audit as audit_observer
  observed=audit_observer(root,p)
  require(result['status']=='FAILED' and result['error']=='UI/observer condition deadline' and
   result['request_count']==len(requests)==len(guards)==2,'Exact zero-RF B6 initialization failure')
  require(all(r['kind'] in ['start','finish','browser_version','network_request','request_guard',
   'network_response','network_body','failure'] for r in rows),'B6 unexpected activity')
  responses={r['value']['requestId']:r['value']['response'] for r in rows if r['kind']=='network_response'}
  bodies={r['value']['request_id']:r['value'] for r in rows if r['kind']=='network_body'}
  guard_map={r['value']['network_id']:r['value']['request'] for r in guards}
  keys={r['value']['requestId'] for r in requests}
  require(len(responses)==len(bodies)==len(guard_map)==2 and keys==set(responses)==set(bodies)==set(guard_map),'Complete B6 network evidence')
  require([r['value']['request']['url'] for r in requests]==[ORIGIN+'/',ORIGIN+'/favicon.ico'],'Exact B6 GET scope')
  for row,status,code in zip(requests,[503,404],['resource_exhausted','not_found']):
   key=row['value']['requestId'];q=row['value']['request'];r=responses[key];b=bodies[key];raw=body_bytes(b['body'])
   require(guard_map[key]['url']==q['url'] and guard_map[key]['method']=='GET' and r==b['response'] and
    r['url']==q['url'] and r['status']==status and r['securityState']=='secure' and
    r['securityDetails']['protocol']=='TLS 1.3' and not r.get('fromDiskCache',False) and
    not r.get('fromServiceWorker',False) and int(r['headers']['Content-Length'])==len(raw) and
    json.loads(raw)==dict(error=dict(code=code)),'Actual B6 authenticated HTTP rejection')
  before=observed['inventories']['before-a'];final=observed['inventories']['final-a']
  require(before['wtp']['STATUS']==final['wtp']['STATUS'] and all(before['info'][k]==final['info'][k] for k in
   ['launch_epoch','dma_irqs','alarm_irqs','tail_irqs']),'B6 unchanged job/RF authority')
  return dict(status='B6_ZERO_RF_STATIC_PAGE_REFUSAL_VERIFIED',packet_sha256=PACKETS[kind],rf_jobs=0,
   classification='FIRMWARE_STATIC_ASSET_ADMISSION_REFUSAL',original_harness_error=result['error'],
   boot_id=p['boot_id'],source_revision=p['source_revision'],image_sha256=p['image_sha256'],
   final_authority=final['wtp']['STATUS'],cadence=observed['cadence'],certificate_pin_observation='NOT_REACHED',family_closed=False)
 if kind=='b2':
  require(result['status']=='FAILED' and 'ERR_CERT_AUTHORITY_INVALID' in result['error'] and len(requests)==len(guards)==1 and
   requests[0]['value']['request']['url']==guards[0]['value']['request']['url']==ORIGIN+'/' and
   not any(r['kind']=='network_body' for r in rows),'Certificate failure before application response')
  recovery=json.loads((root/'zero-rf-recovery.json').read_text());values=[]
  for name,session in [('before-a',p['inventory_session']),('recovery-final-a2',recovery['inventory_session'])]:
   require(not (root/(name+'.stderr')).read_bytes(),'Inventory stderr')
   v=audit_inventory(root/(name+'.stdout'),dict(serial=p['serial'],device_id=p['device_id']),session,
    p['stage_sha256']['scripts/phase11_5_inventory.py']);values.append(v)
   s=v['wtp']['STATUS'];require(s['boot_id']==p['boot_id'] and s['state']=='empty' and
    s['owner_id'] is s['job_id'] is None and s['output_active'] is False,'Reconciled authority')
  require(configuration(values[0])==configuration(values[1]) and values[0]['wtp']['STATUS']==values[1]['wtp']['STATUS'],
   'Preserved authority/configuration')
  return dict(status='B2_ZERO_RF_TRUST_FAILURE_VERIFIED',packet_sha256=PACKETS[kind],rf_jobs=0,
   classification='BROWSER_TRUST_SETUP_FAILURE_BEFORE_JOB_REQUEST',final_authority=values[1]['wtp']['STATUS'],family_closed=False)
 require(result['status']=='BROWSER_TRUST_READ_ONLY_VERIFIED' and result['request_count']==4 and len(guards)==4 and
  [r['value'] for r in rows if r['kind']=='peer_certificate']==[dict(sha256=PEER)],'Trust probe completion/pin')
 bodies={r['value']['request_id']:r['value'] for r in rows if r['kind']=='network_body'}
 require(len(bodies)==len(requests),'Complete probe bodies')
 seen=set();snapshot=None
 for r in requests:
  q=r['value']['request'];key=r['value']['requestId'];b=bodies[key];response=b['response'];raw=body_bytes(b['body'])
  if q['url'].startswith('data:'):
   require(hashlib.sha256(q['url'].encode()).hexdigest()=='04e449d20d0365d881a54ed24af7ed00fe79dd9f9e601248f4fd7793003924f2' and
    raw==base64.b64decode(q['url'].split(',',1)[1],validate=True),'Browser-local icon');continue
  require(q['url'].startswith(ORIGIN+'/') and response['url']==q['url'] and response['status']==200 and
   response['securityState']=='secure' and response['securityDetails']['protocol']=='TLS 1.3' and
   not response.get('fromDiskCache',False) and not response.get('fromServiceWorker',False) and
   int(response['headers']['Content-Length'])==len(raw),'Actual authenticated probe response')
  path=q['url'][len(ORIGIN):];seen.add(path)
  if path=='/':require(hashlib.sha256(raw).hexdigest()=='c2e866fdc8e26efbafeb87a94452d20db8ba83d3cdef4bfe6a70db330771f9b9','Identified target document')
  if path=='/api/v1/status':snapshot=json.loads(raw)
 require(seen=={'/','/api/v1/status','/api/v1/capabilities','/api/v1/config'},'Exact GET scope')
 dom=json.loads((root/'initial-dom.json').read_text());require(snapshot and dom['job']==snapshot['job'] and
  dom['job']['boot_id']==p['boot_id'] and dom['job']['state']=='empty' and dom['job']['output_active'] is False and
  dom['job']['owner_id'] is None and dom['online'] is True and dom['busy'] is False,'Actual UI backend snapshot')
 return dict(status='P0_AUTHENTICATED_GET_ONLY_BROWSER_VERIFIED',packet_sha256=PACKETS[kind],rf_jobs=0,
  authenticated_gets=4,document_sha256='c2e866fdc8e26efbafeb87a94452d20db8ba83d3cdef4bfe6a70db330771f9b9',
  boot_id=p['boot_id'],family_closed=False)
