#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rule-level differential tests against separate, unmodified Chrony 4.9 objects."""
import hashlib,json,math,subprocess,sys
from pathlib import Path
if sys.flags.optimize:
 raise RuntimeError('Validation requires assertions; run without -O')
engine,control,selection,output=sys.argv[1:]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(path,args=(),payload=''):
 p=subprocess.run([path,*args],input=payload,text=True,capture_output=True,timeout=15,check=True)
 return p.stdout.splitlines()
def close(a,b,absolute=1e-12,relative=1e-8):
 assert math.isfinite(a) and math.isfinite(b)
 assert abs(a-b)<=absolute+relative*max(abs(a),abs(b)),(a,b)
# The reference scheduler receives actual in-process IO events at each virtual
# time. Timeout callbacks alone do not advance SCH_GetLastEventTime.
rows=[];when=1800000000;last=None;expected=[]
for interval in (2,16,64,128):
 for sd in (.000001,.0001,.001,.01):
  for offset in (.00001,.0002,.002,.02,1,-.00001,-.0002,-.002,-.02,-1):
   when+=interval
   rows.append(f'{when} {offset} {sd} 0 .000001 .0000035')
   expected.append((offset,sd,0 if last is None else interval))
   last=when
reference=run(control,payload='\n'.join(rows)+'\n')
actual=run(engine,('slew',),'\n'.join(' '.join(map(str,p)) for p in expected)+'\n')
assert len(reference)==len(actual)==160
max_rate_delta=0
for r,a,p in zip(reference,actual,expected):
 r=list(map(float,r.split()));a=list(map(float,a.split()))
 close(r[3],a[0])
 # Query the actual unmodified generic clock driver as well as REF_SetReference.
 driver=float(run(control,('slew',str(p[0]),str(r[3])))[0])
 delta=abs(a[1]*1e6+driver);max_rate_delta=max(max_rate_delta,delta)
 close(-driver*1e-6,a[1],absolute=5e-10)
# Score updates and qualitative selection are tested with identical source data.
def trace(name):
 rows=[]
 count=3 if name=='majority' else 2
 for i in range(1,21):
  for slot in range(count):
   offset=0;delay=.006 if slot==0 else .008;stratum=1;received=1;leap=0
   if name=='hysteresis' and i>=8:delay=.006 if slot==0 else .002
   if name=='majority':
    delay=.002+slot*.0002
    offset=.25 if slot==2 else slot*.0001
   if name=='disagreement':offset=.25*slot
   if name=='stratum':
    delay=.002 if slot==0 else .004
    stratum=4 if slot==0 else 1
   if name=='withdrawal' and i>=10 and slot==0:received=0
   rows.append((slot,1800000000+i*64+slot,offset,delay,0,stratum,leap,received))
 return rows
def decode(lines,width):
 out=[]
 for line in lines:
  parts=line.split();assert len(parts)==1+4*width
  out.append([(parts[1+i*width],float(parts[2+i*width])) for i in range(4)])
 return out
cases={}
for name in ('hysteresis','majority','disagreement','stratum','withdrawal'):
 payload='\n'.join(' '.join(map(str,row)) for row in trace(name))+'\n'
 ref=decode(run(selection,payload=payload),4)
 got=decode(run(engine,('selection',),payload),2)
 chosen=lambda row:[i for i,(state,_) in enumerate(row) if state=='*']
 assert chosen(ref[-1])==chosen(got[-1]),(name,ref[-1],got[-1])
 if name=='hysteresis':
  ref_switch=next(i+1 for i,r in enumerate(ref) if chosen(r)==[1])
  mu_switch=next(i+1 for i,r in enumerate(got) if chosen(r)==[1])
  assert ref_switch==mu_switch,(ref_switch,mu_switch)
  assert chosen(got[15])==[0] and got[15][1][1]>1
  assert chosen(got[16])==[0] and got[16][1][1]<10
  close(ref[15][1][1],got[15][1][1],relative=.01)
  close(ref[16][1][1],got[16][1][1],relative=.01)
 if name=='majority':
  assert chosen(got[-1]) in ([0],[1])
  assert got[-1][2][0]=='x' and ref[-1][2][0]=='x'
 if name=='disagreement':assert not chosen(got[-1])
 cases[name]={'rows':len(got),'reference':ref,'microchrony':got,
  'selected_choice_mismatch_rows':[i+1 for i,(r,g) in enumerate(zip(ref,got)) if chosen(r)!=chosen(g)],
  'final_selected_choice_matches':chosen(ref[-1])==chosen(got[-1])}
report={'schema':'microchrony-chrony49-rule-differential/1','control_cases':160,
 'max_slew_difference_ppm':max_rate_delta,'source_cases':cases,
 'binaries_sha256':{p:sha(p) for p in (engine,control,selection)},
 'scope':'REF correction rate, actual generic-driver clipping, final SRC source choices and the tested hysteresis switch; startup row differences reported and conservative extra bounds retained',
 'full_unix_daemon_equivalence_claimed':False}
Path(output).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print('Chrony 4.9 differential rules passed:',len(expected),'steering cases and',len(cases),'source traces; max slew difference ppm',max_rate_delta)
