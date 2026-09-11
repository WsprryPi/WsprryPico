#!/usr/bin/env python3
"""Opt-in offline evidence mutation checks; no device/network operations."""
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_phase11_4_controlled_soak as a
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
a.R=args.evidence_root.resolve()
output=args.output.resolve()
a.need(not output.exists(),'output already exists; preserve earlier assessment')
a.need(not output.is_relative_to(a.R),'output must be outside raw evidence')
original=a.rows
cases=[]
def mutate(name,fn):
 cache={n:copy.deepcopy(original(n)) for n in ('usb.jsonl','network.jsonl','host.jsonl','supervisor.jsonl','before-a.jsonl','before-b.jsonl','final-a.jsonl','final-b.jsonl')}
 fn(cache)
 a.rows=lambda n:cache[n]
 try:a.analyze()
 except (ValueError,KeyError,IndexError) as e:cases.append({'case':name,'result':'REJECTED','reason':str(e)})
 else:raise AssertionError('Fault accepted: '+name)
 finally:a.rows=original

def payload(cache,file,key,alter):
 row=next(r for r in cache[file] if r['kind']=='sample')
 vals=[json.loads(x) for x in row['value']['stdout'].splitlines()]
 target=next(x for x in vals if key in x);alter(target)
 row['value']['stdout']='\n'.join(json.dumps(x) for x in vals)+'\n'
mutate('boot change',lambda c:payload(c,'usb.jsonl','info',lambda x:x['info']['status'].update(boot_id='different')))
mutate('allocator error',lambda c:payload(c,'usb.jsonl','info',lambda x:x['info'].update(tls_allocation_failures=1)))
mutate('output enabled',lambda c:payload(c,'usb.jsonl','info',lambda x:x['info']['status'].update(output_active=True)))
mutate('saved-state drift',lambda c:payload(c,'usb.jsonl','info',lambda x:x['info']['status'].update(watermark_utc_ns='0')))
mutate('DNS failure masked by HTTPS',lambda c:payload(c,'network.jsonl','dns',lambda x:x.update(dns_ok=False)))
mutate('wrong HTTPS boot',lambda c:payload(c,'network.jsonl','https',lambda x:x['https']['body']['job'].update(boot_id='different')))
mutate('wrong TLS identity',lambda c:payload(c,'network.jsonl','https',lambda x:x['https'].update(server_sha256='wrong')))
mutate('USB record removed',lambda c:c['usb.jsonl'].pop(100))
mutate('interval marker absent',lambda c:c['network.jsonl'].pop())
mutate('observer died',lambda c:next(r for r in c['supervisor.jsonl'] if r['kind']=='observer_health')['value'].update(peer=1))
mutate('child unclean exit',lambda c:next(r for r in c['supervisor.jsonl'] if r['kind']=='child_closed')['value'].update(exit=1))
mutate('Pico B reboot',lambda c:c['final-b.jsonl'][0]['value']['status'].update(boot_id='different'))
mutate('Pico A restoration drift',lambda c:c['final-a.jsonl'][0]['value']['status'].update(enabled=True))
mutate('false WTP aggregate',lambda c:payload(c,'usb.jsonl','wtp',lambda x:x.update(identity_output_ok=False)))
# A repeated clean evaluation confirms instrumentation did not mutate original evidence.
a.analyze();a.analyze()
out={'semantic_faults_rejected':len(cases),'cases':cases,'final_clean_reassessments':2}
with output.open('x') as stream:stream.write(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
