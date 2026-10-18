#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline, identical-input source-statistics comparison using captured Pico originals."""
from pathlib import Path
import hashlib,json,subprocess,sys
if sys.flags.optimize:
 raise RuntimeError('Comparison requires assertions; run without -O')
root=Path(sys.argv[1]).resolve();capture=root/'live';engine=root/'host/microchrony_tests';oracle=root/'chrony49-stats'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
validated=json.loads((root/'live-analysis.json').read_text());previous=json.loads((root/'stats-comparison.json').read_text())
assert sha(engine)==previous['engine_sha256'] and sha(oracle)==previous['oracle_sha256']
for name,h in validated['inputs_sha256'].items():assert sha(capture/name)==h,name
report={'schema':'microchrony-chrony49-captured-source-comparison/1','engine_sha256':sha(engine),'oracle_sha256':sha(oracle),'script_sha256':sha(Path(__file__)),
 'scope':'Identical admitted real Pico measurements through Chrony4.9 SST and microchrony stats; no network, full packet admission, clock servo or RF comparison.',
 'truth':'No independent frequency or UTC truth in these captures; agreement is not accuracy.',
 'limitations':['Normalized scalar inputs, not identical full raw packet paths.', 'The existing host stats driver uses portable defaults, not the full Pico profile.', 'Kernel/hardware timestamping, source combination, servo feedback, persistence and RF are excluded.', 'Re-encoding in the microchrony stats driver retains its existing NTP quantization.'],
 'normalization':'Common arbitrary epoch 1800000000 plus64s and elapsed raw midpoint; offset is change in server midpoint UTC minus change in raw midpoint. Delay excludes server processing; positive remote root delay/2 is charged to dispersion in both harnesses.',
 'cohorts':[]}
for board in ('A','B'):
 assert validated['boards'][board]['accepted_original_visibility']['complete']
 cohorts={}
 for p in sorted(capture.glob(board+'-history-*.json')):
  v=json.loads(p.read_text())['response']
  if v.get('ok') is not True:continue
  key=(v['boot_id'],v['slot'],v['endpoint'],v['clock_epoch'])
  cohort=cohorts.setdefault(key,{})
  for r in v['records']:
   if r['id'] in cohort:assert cohort[r['id']]==r
   cohort[r['id']]=r
 for key,values in sorted(cohorts.items()):
  records=sorted(values.values(),key=lambda r:int(r['receive_raw_ns']));rows=[];timeline=[]
  first=records[0];raw0=(int(first['send_raw_ns'])+int(first['receive_raw_ns']))//2;utc0=(int(first['server_receive_ns'])+int(first['server_send_ns']))//2
  for r in records:
   send=int(r['send_raw_ns']);receive=int(r['receive_raw_ns']);server_recv=int(r['server_receive_ns']);server_send=int(r['server_send_ns'])
   raw=(send+receive)//2;utc=(server_recv+server_send)//2
   delay=max(1000,receive-send-(server_send-server_recv))/1e9
   rd=r['root_delay_16_16'];rd=rd if rd<2**31 else rd-2**32
   dispersion=r['root_dispersion_16_16']/65536+max(0,rd)/131072
   elapsed=(raw-raw0)/1e9;when=1800000064+elapsed
   offset=((utc-utc0)-(raw-raw0))/1e9
   rows.append(f'{when:.12f} {offset:.12f} {delay:.12f} {dispersion:.12f}')
   timeline.append(elapsed)
  payload='\n'.join(rows)+'\n'
  def run(args):
   result=subprocess.run(args,input=payload,text=True,capture_output=True,check=True,timeout=15)
   return [[float(x) for x in row.split()] for row in result.stdout.splitlines()]
  ref=run([str(oracle)]);mu=run([str(engine),'stats']);assert len(ref)==len(mu)==len(records)
  pairs=list(zip(ref[2:],mu[2:]));lastref,lastmu=ref[-1],mu[-1]
  report['cohorts'].append({'board':board,'slot':key[1],'endpoint':key[2],'boot_id':key[0],'clock_epoch':key[3],
   'originals':len(records),'elapsed_seconds':timeline,'input_sha256':hashlib.sha256(payload.encode()).hexdigest(),'input_rows':rows,
   'reference_rows':ref,'microchrony_rows':mu,
   'final_chrony_frequency_ppm':lastref[3]*1e6,'final_microchrony_frequency_ppm':lastmu[3]*1e6,
   'final_chrony_skew_ppm':lastref[5]*1e6,'final_microchrony_skew_ppm':lastmu[5]*1e6,
   'final_chrony_retained':int(lastref[1]),'final_microchrony_retained':int(lastmu[1]),
   'max_frequency_difference_ppm':max(abs(a[3]-b[3])*1e6 for a,b in pairs),
   'max_skew_difference_ppm':max(abs(a[5]-b[5])*1e6 for a,b in pairs)})
(root/'captured-source-comparison.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k not in ('input_rows','reference_rows','microchrony_rows','elapsed_seconds','input_sha256')} for r in report['cohorts']],indent=2))
