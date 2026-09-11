#!/usr/bin/env python3
"""Offline audit of the September 2026 controlled soak; never accesses hardware.

Requires private evidence in --evidence-root and its parent current.json manifest.
Outputs measured results; final memory interpretation remains a reviewed judgment.
"""
import argparse,json,hashlib,struct,statistics,datetime,re
from pathlib import Path
R = None
import phase11_4_loop_common as c
from phase11_4_soak import quiet_window
c.ADDRESS='10.77.14.10'
SAVED=('station','schedules','watermark_utc_ns','expires_utc_s','enabled','suspended')
def need(x,m):
 if not x:raise ValueError(m)
def read(n):return json.loads((R/n).read_text())
def rows(n):
 b=(R/n).read_bytes();need(b.endswith(b'\n'),'incomplete JSONL '+n)
 return [json.loads(v) for v in b.splitlines()]
def stamp(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()
def capture(name):
 b=(R/(name+'.pcap')).read_bytes();need(b[:4]==bytes.fromhex('d4c3b2a1'),'pcap format')
 _,major,minor,zone,sig,snap,link=struct.unpack('<IHHIIII',b[:24]);need((major,minor,link)==(2,4,1),'pcap header')
 offset=24;times=[];truncated=0
 while offset<len(b):
  need(len(b)-offset>=16,'truncated record header');sec,usec,inc,orig=struct.unpack('<IIII',b[offset:offset+16]);offset+=16
  need(0<inc<=orig and inc<=snap and usec<1000000 and offset+inc<=len(b),'bad packet record')
  truncated+=inc<orig;times.append(sec+usec/1e6);offset+=inc
 log=(R/(name+'-capture.log')).read_text();count=int(re.search(r'(\d+) packets captured',log)[1]);drops=int(re.search(r'(\d+) packets dropped by kernel',log)[1])
 need(count==len(times) and drops==0 and truncated==0,'capture loss/count/truncation')
 return dict(packets=count,drops=drops,truncated=truncated,first=stamp(min(times)),last=stamp(max(times)),size=len(b),sha256=hashlib.sha256(b).hexdigest())
def analyze():
 plan=read('run.json');base=read('hotspot-baseline.json');boot=plan['boot'];start=plan['start_epoch'];end=plan['end_epoch']
 need(end-start==28800 and plan['duration_seconds']==28800,'eight hour plan')
 pointer=json.loads((R.parent/'current.json').read_text());need(plan==pointer['run'],'wrong run')
 for n,digest in pointer['source_sha256'].items():need(hashlib.sha256((R/n).read_bytes()).hexdigest()==digest,'source mismatch '+n)
 for n,digest in read('final-sha256.json').items():need(hashlib.sha256((R/n).read_bytes()).hexdigest()==digest,'evidence hash '+n)
 logs={k:rows(k+'.jsonl') for k in ('usb','network','host','supervisor')};metrics={};infos=[];wtps=0;network=[]
 for k,rs in logs.items():
  need(all(b['monotonic_ns']>a['monotonic_ns'] and b['epoch_ns']>a['epoch_ns'] for a,b in zip(rs,rs[1:])),'timestamp order '+k)
  drift=[(b['epoch_ns']-a['epoch_ns']-b['monotonic_ns']+a['monotonic_ns'])/1e9 for a,b in zip(rs,rs[1:])]
  need(max(map(abs,drift),default=0)<.1,'host clock discontinuity')
  finished=[v for v in rs if v['kind']=='interval_finished'];need(len(finished)==1 and finished[0]['epoch_ns']/1e9>=end,'interval incomplete '+k)
  need(not any(v['kind']=='sample_failure' for v in rs),'observer failure '+k)
  samples=[r for r in rs if r['kind']=='sample'];ts=[r['value']['started_epoch'] for r in samples]
  metrics[k]={'samples':len(samples),'finished_utc':stamp(finished[0]['epoch_ns']/1e9),'max_clock_step_seconds':max(map(abs,drift),default=0)}
  if ts:metrics[k].update(first_utc=stamp(ts[0]),last_utc=stamp(ts[-1]),first_offset=ts[0]-start,final_gap=end-ts[-1],max_gap=max(b-a for a,b in zip(ts,ts[1:])),max_duration=max(r['value']['duration'] for r in samples))
  for row in samples:
   v=row['value'];t=v['started_epoch'];need(start<=t<end and v['exit']==0 and not v['stderr'],'sample failed/outside interval '+k)
   values=[json.loads(x) for x in v['stdout'].splitlines()];need(values,'empty sample')
   if k=='usb':
    inf=[x for x in values if 'info' in x];need(len(inf)==1 and inf[0]['anomalies']==[],'USB anomalies');i=inf[0]['info'];c.validate_info(i,boot,plan['revision'])
    need(all(not i[f] for f in ('fault_stage','fault_hash','fault_pc','fault_status','tls_allocation_failures')),'fault/allocation error')
    need(all(i['status'][f]==base['status'][f] for f in SAVED),'saved state drift')
    n=i['network'];need(n['ipv4']==c.ADDRESS and n['mdns_state']=='active' and n['stable_hostname']==c.NAME and n['station_mac']==base['network']['station_mac'],'network identity drift')
    need(n['ntp_server']==n['ntp_address']=='10.77.14.1' and i['status']['clock_state']=='synchronized','clock drift')
    need(all(m['errors']==0 for m in n['memory'].values()),'lwip allocator error')
    infos.append((t,v['sample'],i))
    if v['sample']=='wtp':
     agg=[x for x in values if 'wtp' in x];need(len(agg)==1 and agg[0]['identity_output_ok'] is True,'missing/failed WTP aggregate');w=agg[0]['wtp']
     need(w['hello']['device_id']==c.DEVICE and w['hello']['boot_id']==w['status']['boot_id']==boot,'WTP identity');need(w['status']['output_active'] is False and w['status']['state']=='empty' and w['status']['owner_id'] is None and w['status']['job_id'] is None,'WTP authority');wtps+=1
   elif k=='network':
    need(len(values)==1,'network shape');x=values[0];need(x['dns_ok'] is True and x['https_ok'] is True,'network failed')
    need(x['dns']['exit']==0 and {v[4][0] for v in json.loads(x['dns']['stdout'])}=={c.ADDRESS},'native DNS result');c.validate_https(x['https'],boot)
    need(all(x['https']['body']['standalone'][f]==base['status'][f] for f in SAVED),'HTTPS saved drift')
    need(not quiet_window(t,start,end),'probe in scheduled quiet window');network.append(t)
   elif k=='host':
    need(len(values)==1,'host shape');x=values[0];need('SSID: Bohica-IoT' in x['host']['management'] and 'eth0' in x['host']['interfaces'],'management changed')
    need('SSID: WsprryPico-Test' in x['peer']['link'] and '10.77.14.2' in x['peer']['routes'],'client changed')
  if k!='supervisor':
   need(rs[0]['kind']=='started' and rs[0]['value']['plan']==plan and rs[-1]['kind']=='interval_finished','worker lifecycle')
   need(finished[0]['value']['samples']==len(samples),'worker count mismatch')
 sup=logs['supervisor'];need(sup[0]['kind']=='observers_ready' and sup[-1]['kind']=='closed','supervisor lifecycle')
 for row in sup:
  if row['kind']=='observer_health':need(set(row['value'])=={'ap','peer','usb','network','host'} and all(v is None for v in row['value'].values()),'observer died')
 closed=[r['value'] for r in sup if r['kind']=='child_closed'];need(len(closed)==5 and all(v['exit']==0 for v in closed),'unclean child exits')
 monos=[int(i['status']['monotonic_now_ns']) for _,_,i in infos];need(all(b>a for a,b in zip(monos,monos[1:])),'Pico uptime discontinuity')
 quiet={}
 for t,mode,i in infos:
  elapsed=t-start;window=int(elapsed//600)
  # Last minute of scheduled pauses allows transport teardown; require measured empty pools.
  selected=(60<=elapsed%600<120) or t>=end-60
  mem=i['network']['memory']
  if selected and all(mem[n]['used']==0 for n in ('tcp_pcbs','tcp_segments','packet_pool')):
   key='final' if t>=end-60 else str(window)
   quiet.setdefault(key,[]).append({'app':i['heap_allocated_bytes'],'tls':i['tls_allocated_bytes'],'lwip':mem['heap']['used'],'mode':mode})
 q={k:{'count':len(v),**{n:{'min':min(x[n] for x in v),'median':statistics.median(x[n] for x in v),'max':max(x[n] for x in v)} for n in ('app','tls','lwip')}} for k,v in quiet.items()}
 need(set(q)=={str(i) for i in range(48)}|{'final'},'missing comparable quiet window')
 metrics['memory']={'quiet_by_sampler':{mode:{key:{n:statistics.median(x[n] for x in vals if x['mode']==mode) for n in ('app','tls','lwip')} for key,vals in quiet.items() if any(x['mode']==mode for x in vals)} for mode in ('usb','wtp')},'quiet_windows':q,'quiet_samples':sum(len(v) for v in quiet.values()),'wtp_checks':wtps,'pico_uptime_observed_seconds':(monos[-1]-monos[0])/1e9,'final_peaks':{k:infos[-1][2][k] for k in ('heap_sampled_peak_bytes','tls_peak_bytes','core0_stack_used_bytes')},'allocator_errors':0}
 need(read('cleanup-result.json')['failures']==[] and read('soak-restored.json')['result']=='PASS','restoration failed')
 restored=read('pico-restored.json');need(restored['network']['ipv4'].startswith('192.168.1.') and restored['status']['boot_id']!=boot,'restore identity');need(all(restored['status'][f]==base['status'][f] for f in SAVED),'restore state drift')
 # Independent restored device evidence must agree with saved identity and ownership.
 for target in ('a','b'):
  before=rows('before-'+target+'.jsonl')[0]['value'];rr=rows('final-'+target+'.jsonl');after=rr[0]['value'];wt=rr[1]['value']
  need(after['device_id']==before['device_id'] and after['revision']==before['revision'] and after['deployment_identity_matches'] is True and after['recovery_boot'] is False,'final identity '+target)
  need(all(after['status'][f]==before['status'][f] for f in SAVED),'final saved state '+target)
  need(after['status']['output_active'] is False and after['status']['storage_healthy'] is True and after['network']['mdns_state']=='active','final output/storage/discovery '+target)
  need(after['network']['ipv4']==before['network']['ipv4'] and after['network']['stable_hostname']==before['network']['stable_hostname'],'final address/name '+target)
  need(after['status']['boot_id']==(restored['status']['boot_id'] if target=='a' else before['status']['boot_id']),'final boot '+target)
  need(wt['exit']==0,'final USB WTP exit')
  replies=[json.loads(line) for line in wt['stdout'].splitlines() if line.startswith('{')]
  statuses=[x['body'] for x in replies if x.get('op')=='STATUS'];need(statuses,'missing final WTP status')
  need(all(x['boot_id']==after['status']['boot_id'] and x['state']=='empty' and x['output_active'] is False and x['owner_id'] is None and x['job_id'] is None for x in statuses),'final WTP authority')
 finalhost=read('final-host.json');need(finalhost[0]['stdout'].strip()==plan['host_boot'],'host boot changed')
 need(finalhost[3]['stdout']=='' and 'phase11' not in finalhost[4]['stdout'] and '10.77.14.' not in finalhost[2]['stdout'],'fixture remains')
 need('Bohica-IoT' in finalhost[5]['stdout'] and finalhost[6]['stdout']=='active\nactive\n' and finalhost[7]['stdout']=='inactive\n'*5,'final services/association')
 need([x['stdout'].strip() for x in finalhost[8:]]==['Power save: on','Power save: off','Power save: on'],'radio power restore')
 need((R/'wifi-ssh.txt').read_text().split()[2]=='192.168.1.117','Wi-Fi SSH endpoint')
 # Bounds follow the deployed interval + subprocess deadline, with a one-second scheduling allowance.
 for kind,limit in [('usb',30),('network',175),('host',325)]:
  need(metrics[kind]['max_gap']<limit and metrics[kind]['first_offset']<limit and metrics[kind]['final_gap']<limit,'observation gap '+kind)
 metrics['captures']={n:capture(n) for n in ('ap','peer')};metrics['restore_utc']=stamp(read('soak-restored.json')['epoch_ns']/1e9);metrics['restored_boot']=restored['status']['boot_id']
 metrics['result']='COMPLETE: observations validated; memory trend and independent restoration review required'
 return metrics
def main():
 global R
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--evidence-root',type=Path,required=True)
 parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args()
 R=args.evidence_root.resolve()
 output=args.output.resolve()
 need(not output.exists(),'output already exists; preserve earlier analysis')
 need(not output.is_relative_to(R),'output must be outside raw evidence')
 result=analyze()
 with output.open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
 print('Offline soak audit complete; review the measured memory results.')


if __name__=='__main__':main()
