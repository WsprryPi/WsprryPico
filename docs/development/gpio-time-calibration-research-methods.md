# Retained GPIO/NTP research methods

Recorded: 2026-10-09. Documentation of the exact local calculations used in the
[research report](gpio-time-calibration-research.md) and
[review closure](gpio-time-calibration-review-closure.md). These methods target
one frozen intake; they are not application code, a general NTP implementation,
or an RF calibration algorithm.

## Input and output boundaries

Use Python 3 and its standard library locally. Supply the original 25 byte-exact
files under `inputs/`, following the relative paths in the
[sanitized intake manifest](gpio-time-calibration-intake-manifest.json).
The JSON manifest is research metadata, not application configuration. Its
`stable_during_read` flags report the original file-copy checks; executing these
methods does not independently re-observe the remote source metadata. The full
private transfer manifest additionally retains inode/mtime records, and its
hash is included in the public manifest.

Raw inputs, `analysis.json`, `observations.jsonl` and complete method output
remain private/ignored. Generated analysis contains network diagnostics; do
not publish it wholesale. The intake and full original transfer manifest are
retained locally; no raw records, IQ or credentials are part of this document.
Without the exact private input files, a fresh checkout cannot rerun the data
analysis. This appendix preserves the method and input binding, not those files.

The methods have no network, device or hardware-control imports/calls. They
read JSON evidence and write local calculated results. The independent validator
checks input hashes, identities, repeated idle records, rates, percentiles and
conditional endpoint ranges. It does not qualify absolute UTC, hardware timing
or carrier error, and it cannot fill missing per-observation source labels.
The frozen methods use assertions for validation. Run the given isolated
Python commands without `-O`; optimization must not disable these checks.

## Recover the methods

From the repository root, extract the two source blocks below into an ignored
local directory. The UTF-8/LF source bytes must match the recorded hashes.
For a fresh intake directory only, copy the public manifest as `manifest.json`
and supply the 25 original files below `inputs/`. Preserve an existing original
transfer manifest; do not overwrite it with the sanitized publication.

```python
from pathlib import Path
import re, hashlib, sys
if sys.flags.optimize:
    raise RuntimeError("Run recovery and validation without Python optimization")
repo = Path.cwd()
out = repo / "build/gpio-time-review-closure-20261009"
out.mkdir(mode=0o700, parents=True, exist_ok=True)
doc = (repo / "docs/development/gpio-time-calibration-research-methods.md").read_text(encoding="utf-8")
expected = {
    "analyze": "5ad0812cdcf599a9332fccb7ed1f8752ad03ab38489319500f849b2d10ff937d",
    "validate": "da62e9876f288085e79b3303ea07c217f23b8c5eb0d964146c9dbb9ea9b3186e",
}
blocks = re.findall(r"## (analyze|validate)\.py\n\n```python\n(.*?)```", doc, re.S)
assert len(blocks) == 2 and {name for name, _ in blocks} == set(expected)
for name, source in blocks:
    data = source.encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == expected[name], name
    target = out / (name + ".py")
    target.write_bytes(data)
    target.chmod(0o600)
    print(target.name, hashlib.sha256(target.read_bytes()).hexdigest())
```

Run against the existing local intake (or your separate restored byte-exact
intake). Preserve the original raw files. The primary method writes calculated
outputs under the supplied root; save its full stdout only in private storage.

```sh
set -e
python3 -I build/gpio-time-review-closure-20261009/analyze.py build/gpio-time-research-20261009 > build/gpio-time-review-closure-20261009/analysis.stdout
python3 -I build/gpio-time-review-closure-20261009/validate.py build/gpio-time-research-20261009 > build/gpio-time-review-closure-20261009/validation.stdout
```

Stop on any extraction or calculation failure; do not validate stale result
files from an earlier successful execution. The closure check executes each
child with an enforced successful exit and parses its newly produced stdout.

The validated summary remains the original 365,335 events, 2,563 target INFO
rows and 249/234 distinct A/B anchors. Apparent OLS rates and timing-derived
endpoint ranges remain diagnostics with the report's stated assumptions.

## Exact method hashes

| Method | SHA-256 |
| --- | --- |
| `analyze.py` | `5ad0812cdcf599a9332fccb7ed1f8752ad03ab38489319500f849b2d10ff937d` |
| `validate.py` | `da62e9876f288085e79b3303ea07c217f23b8c5eb0d964146c9dbb9ea9b3186e` |

## analyze.py

```python
from pathlib import Path
from collections import Counter,defaultdict
from fractions import Fraction
from datetime import datetime,timezone
import json,hashlib,math,statistics,sys

ROOT=Path(sys.argv[1]).resolve()
summary=json.loads((ROOT/'inputs/result.json').read_text())
manifest=json.loads((ROOT/'manifest.json').read_text())
def quant(values,p):
    a=sorted(values)
    if not a:return None
    x=(len(a)-1)*p;i=int(x);f=x-i
    return a[i] if i==len(a)-1 else a[i]*(1-f)+a[i+1]*f
def stats(a,scale=1):
    return {'n':len(a),'min':min(a)/scale,'median':quant(a,.5)/scale,'p95':quant(a,.95)/scale,'max':max(a)/scale} if a else {'n':0}
def iso(n):return datetime.fromtimestamp(n/1e9,timezone.utc).isoformat()
def anchors(rows):
    seen={};conflicts=0
    for r in rows:
        if r['state'] not in ('synchronized','holdover'):continue
        key=r['anchor_m']
        if key in seen:
            if seen[key]['anchor_u']!=r['anchor_u']:conflicts+=1
        else:seen[key]=r
    return sorted(seen.values(),key=lambda r:r['anchor_m']),conflicts
def fit(a):
    if len(a)<3:return {'n':len(a)}
    m0=a[0]['anchor_m'];b0=a[0]['offset']
    x=[(r['anchor_m']-m0)/1e9 for r in a];y=[(r['offset']-b0)/1e9 for r in a]
    xm=statistics.mean(x);ym=statistics.mean(y)
    s=sum((t-xm)*(v-ym) for t,v in zip(x,y))/sum((t-xm)**2 for t in x)
    residual=[v-(ym+s*(t-xm)) for t,v in zip(x,y)]
    dm=a[-1]['anchor_m']-m0;db=a[-1]['offset']-b0;du=dm+db
    ppm=float(Fraction(-db*1_000_000,du))
    bound=float(Fraction((a[0]['base_unc']+a[-1]['base_unc'])*1_000_000,du))
    return {'n':len(a),'span_s':dm/1e9,'endpoint_ppm':ppm,'ols_ppm':-s/(1+s)*1e6,'residual_ms':stats([abs(v)*1000 for v in residual]),'endpoint_uncertainty_equivalent_ppm':bound,'offset_span_ms':(max(r['offset'] for r in a)-min(r['offset'] for r in a))/1e6,'first_base_unc_ms':a[0]['base_unc']/1e6,'last_base_unc_ms':a[-1]['base_unc']/1e6}

cohorts=defaultdict(list);jobs=[];quality=Counter();allkinds=Counter();schemas=Counter();sourcefields=Counter();raw_count=0
boots={j['board']:j['boot_id'] for j in summary['jobs']}
ids={'A':'fd6127d11d6aca42a9905fa3fb1bf1d5','B':None}
physical_by_index={}
for idx,j in enumerate(summary['jobs']):
    rel=Path(j['path']).relative_to(Path(manifest['remote_root']))
    p=ROOT/'inputs'/rel/'physical.json';v=json.loads(p.read_text());physical_by_index[idx]=v
    assert v['schema']=='phase14-physical/1' and v['result']=='CONTROL_COMPLETE'
    assert v['board']==j['board'] and v['boot_id']==j['boot_id'] and v['job']['job_id']==j['job_id']
    assert v['source_revision']==summary['source_commit'][:12] and v['firmware_sha256']==summary['firmware_sha256'] and v['clock_hz']==138000000
    assert v['capture_sha256']==j['capture_sha256'] and v['metadata_sha256']==j['metadata_sha256']
    assert int(v['accepted_job']['total_duration_ns'])==3600_000_000_000 and v['terminal']['state']=='complete' and not v['terminal']['output_active']
    assert v['engine_frequency_correction_ppb']==v['requested_frequency_compensation_ppb']==0
    ids[v['board']]=v['device_id']
    browser=[r['utc_ns'] for r in v['browser_activity']]
    jobs.append({'index':idx,'board':v['board'],'mode':v['mode'],'job_id':v['job']['job_id'],'boot_id':v['boot_id'],'physical_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status_rows':len(v['status']),'status_clock_rows':sum('clock' in r['status'] for r in v['status']),'browser_requests':len(browser),'browser_span_s':(browser[-1]-browser[0])/1e9 if browser else None,'browser_original_count_pass':len(browser)>=300 if browser else None,'arm_unc_ms':int(v['arm']['clock']['uncertainty_ns'])/1e6})

for idx,j in enumerate(summary['jobs']):
    last_host=0;last_event_m=0
    with (ROOT/'inputs'/str(idx)/'events.jsonl').open() as stream:
        for line_number,line in enumerate(stream,1):
            try:e=json.loads(line)
            except ValueError:quality['invalid_json_lines']+=1;continue
            allkinds[e['kind']]+=1;raw_count+=1
            if e['utc_ns']<last_host:quality['host_utc_backward']+=1
            if e['monotonic_ns']<last_event_m:quality['host_monotonic_backward']+=1
            last_host=e['utc_ns'];last_event_m=e['monotonic_ns']
            if e['kind']!='info':continue
            schemas[','.join(sorted(e))]+=1
            d=e.get('value',e.get('data'));b=d['board'];v=d['info'];s=v['status'];n=v['network']
            assert v['device_id']==ids[b] and s['boot_id']==boots[b] and v['revision']==summary['source_commit'][:12] and v['system_clock_hz']==138000000
            for k in ('time_source','time_disagreement'):sourcefields[k]+=int(k in v or k in s)
            try:m=int(s['monotonic_now_ns']);u=int(s['utc_now_ns']);age=int(s['sync_age_ns']);unc=int(s['uncertainty_ns'])
            except (ValueError,KeyError):quality['invalid_clock_fields']+=1;continue
            if s['clock_state'] not in ('synchronized','holdover') or u<1_735_689_600_000_000_000 or age>m:
                quality['invalid_or_unsynchronized_clock']+=1;continue
            growth=(age*50_000+999_999_999)//1_000_000_000
            r={'index':idx,'target':b==j['board'],'board':b,'boot':s['boot_id'],'host_utc':e['utc_ns'],'host_m':e['monotonic_ns'],'line':line_number,'m':m,'u':u,'age':age,'unc':unc,'anchor_m':m-age,'anchor_u':u-age,'offset':u-m,'base_unc':unc-growth,'state':s['clock_state'],'job_state':s['state'],'job':s['job_id'],'peer':n['ntp_address'],'server':n['ntp_server'],'accepted':n['accepted'],'rejected':n['rejected'],'queries':n['queries'],'rtt':n['last_rtt_ns'],'sample_unc':n['last_sample_uncertainty_ns'],'base_matches_latest':unc-growth==n['last_sample_uncertainty_ns'],'launch_delay_ns':v.get('launch_delay_ns')}
            if r['base_unc']<0:quality['negative_base_uncertainty']+=1
            cohorts[b].append(r)

report={'schema':'gpio-ntp-research/1','scope':'closed original eight-hour soak only','source_commit':summary['source_commit'],'firmware_sha256':summary['firmware_sha256'],'tool_snapshot':'dbf1f3e','start_utc':iso(summary['started_utc_ns']),'end_utc':iso(summary['ended_utc_ns']),'collection_start_utc':iso(manifest['started_utc_ns']),'collection_end_utc':iso(manifest['ended_utc_ns']),'source_bytes':manifest['source_bytes'],'raw_events':raw_count,'event_kinds':allkinds,'event_schemas':schemas,'quality':quality,'source_field_counts':sourcefields,'jobs':jobs,'boards':{},'calibration_validated':False}
for b,rows in cohorts.items():
    rows.sort(key=lambda r:r['m']);target=[r for r in rows if r['target']]
    a,conflicts=anchors(target);da=[a[i]['offset']-a[i-1]['offset'] for i in range(1,len(a))]
    running=[r for r in target if r['job_state']=='running'];idle=[r for r in target if r['job_state'] not in ('armed','running')]
    transitions=[];deltas=[];cad=[];perjob=[]
    for idx,j in enumerate(jobs):
        if j['board']!=b:continue
        rr=[r for r in target if r['index']==idx];aa,cc=anchors(rr)
        cadence=[rr[i]['host_m']-rr[i-1]['host_m'] for i in range(1,len(rr)) if rr[i]['job_state']==rr[i-1]['job_state']=='running']
        cad+=cadence
        counts={k:rr[-1][k]-rr[0][k] for k in ('accepted','rejected','queries')}
        if any(v<0 for v in counts.values()):quality['counter_reset']+=1
        deltas.append(counts)
        for prev,cur in zip(rr,rr[1:]):
            ac=cur['accepted']-prev['accepted'];rc=cur['rejected']-prev['rejected'];new=cur['anchor_m']!=prev['anchor_m']
            if ac<0 or rc<0:quality['counter_reset']+=1
            transitions.append({'accept_delta':ac,'reject_delta':rc,'new_anchor':new,'base_matches_latest':cur['base_matches_latest']})
        perjob.append({'index':idx,'info_rows':len(rr),'anchors':len(aa),'counter_delta':counts,'cadence_s':stats(cadence,1e9),'fit':fit(aa),'max_age_s':max(r['age'] for r in rr)/1e9,'peer_changes':sum(l['peer']!=r['peer'] for l,r in zip(rr,rr[1:]))})
    count_trans=Counter()
    for t in transitions:
        if t['accept_delta']>1:count_trans['multi_accept_gaps']+=1
        if t['new_anchor'] and t['accept_delta']==0:count_trans['anchor_change_without_accept']+=1
        if t['accept_delta']>0 and not t['new_anchor']:count_trans['accept_without_anchor_change']+=1
        if t['accept_delta']==1 and t['reject_delta']==0 and t['new_anchor'] and t['base_matches_latest']:count_trans['single_accept_consistent']+=1
    report['boards'][b]={'all_info_rows':len(rows),'target_info_rows':len(target),'running_rows':len(running),'idle_rows':len(idle),'distinct_anchors':len(a),'anchor_conflicts':conflicts,'clock_states':Counter(r['state'] for r in target),'uncertainty_ms':stats([r['unc'] for r in target],1e6),'age_s':stats([r['age'] for r in target],1e9),'latest_rtt_ms':stats([r['rtt'] for r in target],1e6),'offset_update_ms':stats([abs(n) for n in da],1e6),'counter_deltas_within_jobs':{k:sum(x[k] for x in deltas) for k in ('accepted','rejected','queries')},'counter_delta_across_all_target':{k:target[-1][k]-target[0][k] for k in ('accepted','rejected','queries')},'transitions':count_trans,'base_matches_latest_rows':sum(r['base_matches_latest'] for r in target),'distinct_peers':len(set(r['peer'] for r in target)),'servers':sorted(set(r['server'] for r in target)),'cadence_s':stats(cad,1e9),'fit':fit(a),'jobs':perjob,'max_uncertainty_exceeds_500ms':any(r['unc']>500_000_000 for r in target),'max_age_exceeds_90s':any(r['age']>90_000_000_000 for r in target)}
out=ROOT/'analysis.json';out.write_text(json.dumps(report,indent=2)+'\n')
with (ROOT/'observations.jsonl').open('w') as f:
    for b in sorted(cohorts):
        for r in cohorts[b]:f.write(json.dumps(r)+'\n')
print(json.dumps(report,indent=2))
```

## validate.py

```python
from pathlib import Path
from fractions import Fraction
from collections import Counter
import hashlib,json,sys

root=Path(sys.argv[1]).resolve()
manifest=json.loads((root/'manifest.json').read_text())
primary=json.loads((root/'analysis.json').read_text())
assert len(manifest['files'])==25
for f in manifest['files']:
    data=(root/'inputs'/f['relative']).read_bytes()
    assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest()==f['sha256']
    assert f['stable_during_read']
assert sum(f['bytes'] for f in manifest['files'])==187925869

summary=json.loads((root/'inputs/result.json').read_text())
raw=Counter();rows={'A':[],'B':[]};by_job={};idle_duplicates=0
for i,job in enumerate(summary['jobs']):
    infos=[]
    for line in (root/'inputs'/str(i)/'events.jsonl').read_text().splitlines():
        e=json.loads(line);raw[e['kind']]+=1
        if e['kind']!='info':continue
        info=e['value']['info'];b=e['value']['board']
        if b!=job['board']:continue
        infos.append(info);s=info['status'];n=info['network']
        m,u,age=map(int,(s['monotonic_now_ns'],s['utc_now_ns'],s['sync_age_ns']))
        assert s['clock_state']=='synchronized' and age<=90_000_000_000
        assert int(s['uncertainty_ns'])<=500_000_000 and m%1000==0
        rows[b].append(dict(index=i,m=m-age,u=u-age,offset=u-m,
                            uncertainty=int(s['uncertainty_ns']),age=age,info=info))
    by_job[i]=infos
    idle=json.loads((root/'inputs'/str(i)/'idle-window.json').read_text())
    assert len(idle)==3
    for v in idle:
        assert v in infos
        idle_duplicates+=1
    physical=json.loads((root/'inputs'/Path(job['path']).relative_to(manifest['remote_root'])/'physical.json').read_text())
    assert physical['engine']=='pio-dma-gp2' and physical['rf_gp']==2 and physical['divider']==1
    assert physical['clock_hz']==138000000
    assert int(physical['accepted_job']['total_duration_ns'])==3_600_000_000_000
    assert len(physical['accepted_job']['events'])==(1 if job['mode']=='TONE' else 512)
    assert len(physical['browser_activity'])==job['browser_requests']
    assert physical['terminal']['state']=='complete' and not physical['terminal']['output_active']

def exact_rate(points):
    unique={}
    for r in points:
        if r['m'] in unique:assert unique[r['m']]['u']==r['u']
        unique[r['m']]=r
    a=sorted(unique.values(),key=lambda r:r['m']);first=a[0];last=a[-1]
    # Independent direct UTC-on-monotonic regression, all integer moments.
    x=[r['m']-first['m'] for r in a];y=[r['u']-first['u'] for r in a];n=len(a)
    rate=Fraction(n*sum(t*v for t,v in zip(x,y))-sum(x)*sum(y),n*sum(t*t for t in x)-sum(x)**2)
    ppm=(1/rate-1)*1_000_000
    endpoint=(Fraction(last['m']-first['m'],last['u']-first['u'])-1)*1_000_000
    return a,float(ppm),float(endpoint)

def exact_quantile(values,p):
    ordered=sorted(values);at=(len(ordered)-1)*p;lo=at.numerator//at.denominator
    if lo==len(ordered)-1:return Fraction(ordered[lo])
    return ordered[lo]+(ordered[lo+1]-ordered[lo])*(at-lo)

out={'input_hashes_verified':25,'input_bytes':sum(f['bytes'] for f in manifest['files']),
     'raw_events':sum(raw.values()),'event_kinds':dict(raw),'idle_exact_duplicates':idle_duplicates,'boards':{}}
assert dict(raw)==primary['event_kinds'] and sum(raw.values())==365335
for b,rr in rows.items():
    a,ols,endpoint=exact_rate(rr);p=primary['boards'][b]
    assert len(rr)==p['target_info_rows'] and len(a)==p['distinct_anchors']
    assert abs(ols-p['fit']['ols_ppm'])<1e-9 and abs(endpoint-p['fit']['endpoint_ppm'])<1e-12
    assert max(r['uncertainty'] for r in rr)/1e6==p['uncertainty_ms']['max']
    assert max(r['age'] for r in rr)/1e9==p['age_s']['max']
    for field,metric,scale in [('uncertainty','uncertainty_ms',1000000),('age','age_s',1000000000)]:
        for label,fraction in [('median',Fraction(1,2)),('p95',Fraction(95,100))]:
            expected=float(exact_quantile([r[field] for r in rr],fraction)/scale)
            assert abs(expected-p[metric][label])<1e-9
    rtts=[r['info']['network']['last_rtt_ns'] for r in rr]
    for label,fraction in [('median',Fraction(1,2)),('p95',Fraction(95,100))]:
        assert abs(float(exact_quantile(rtts,fraction)/1000000)-p['latest_rtt_ms'][label])<1e-9
    assert max(rtts)/1000000==p['latest_rtt_ms']['max']
    x=[r['m']-a[0]['m'] for r in a];y=[r['u']-a[0]['u'] for r in a];n=len(a)
    rate=Fraction(n*sum(t*v for t,v in zip(x,y))-sum(x)*sum(y),n*sum(t*t for t in x)-sum(x)**2)
    intercept=(sum(y)-rate*sum(x))/n
    residual=[abs(v-rate*t-intercept) for t,v in zip(x,y)]
    assert abs(float(max(residual)/1000000)-p['fit']['residual_ms']['max'])<1e-8
    assert abs(float(exact_quantile(residual,Fraction(95,100))/1000000)-p['fit']['residual_ms']['p95'])<1e-8
    compatible=[];deltas=Counter();perjob=[]
    for i,infos in by_job.items():
        if summary['jobs'][i]['board']!=b:continue
        q=[r for r in rr if r['index']==i]
        anchors,j_ols,j_endpoint=exact_rate(q)
        original=next(j for j in p['jobs'] if j['index']==i)
        assert abs(j_ols-original['fit']['ols_ppm'])<1e-9
        for k in ['accepted','rejected','queries']:
            d=infos[-1]['network'][k]-infos[0]['network'][k]
            assert d==original['counter_delta'][k];deltas[k]+=d
        for old,new in zip(q,q[1:]):
            on=old['info']['network'];nn=new['info']['network']
            # Source acquisition collects network before the UTC snapshot.
            growth=(new['age']*50000+999999999)//1000000000
            if nn['accepted']-on['accepted']==1 and nn['rejected']==on['rejected'] and new['m']!=old['m'] and new['uncertainty']-growth==nn['last_sample_uncertainty_ns']:
                compatible.append(abs(new['offset']-old['offset']))
        perjob.append({'index':i,'ols_ppm':j_ols,'endpoint_ppm':j_endpoint})
    assert dict(deltas)==p['counter_deltas_within_jobs']
    base=lambda r:r['uncertainty']-(r['age']*50000+999999999)//1000000000
    proxy=float(Fraction((base(a[0])+base(a[-1]))*1000000,a[-1]['u']-a[0]['u']))
    assert abs(proxy-p['fit']['endpoint_uncertainty_equivalent_ppm'])<1e-12
    dm=a[-1]['m']-a[0]['m'];du=a[-1]['u']-a[0]['u'];error=base(a[0])+base(a[-1])
    model_interval=[float((Fraction(dm,du+error)-1)*1000000),float((Fraction(dm,du-error)-1)*1000000)]
    out['boards'][b]={'info_rows':len(rr),'anchors':len(a),'ols_ppm':ols,'endpoint_ppm':endpoint,
                      'consistent_single_accept_updates':len(compatible),'max_consistent_update_ms':max(compatible)/1e6,
                      'median_consistent_update_ms':float(exact_quantile(compatible,Fraction(1,2))/1000000),
                      'p95_consistent_update_ms':float(exact_quantile(compatible,Fraction(95,100))/1000000),
                      'endpoint_uncertainty_equivalent_ppm':proxy,'conditional_endpoint_interval_ppm':model_interval,'per_job':perjob}
(root/'independent-validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
```
