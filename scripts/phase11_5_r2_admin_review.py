#!/usr/bin/env python3
"""Offline R2 administrative amendment review; no hardware or service operations.

Usage: python3 scripts/phase11_5_r2_admin_review.py EVIDENCE_ROOT REVIEW_REPO
Writes separate usb/amended-audit.json and amended-adversarial-review.json.
Original frozen helpers, packets, raw captures and failed results remain intact.
"""
import copy,json,shutil,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1]).resolve();repo=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(repo/'scripts'))
from audit_phase11_5_r2_modes import audit as strict_audit
def audit(root, decoder):
 return strict_audit(root, decoder, cadence_policy="single-flight-admin-v1")
from phase11_5_device_management import save
results={}
for name in ('usb',):
 original=root/name
 try:strict_audit(original,root/'pi/phase115_tls_observer_test.py')
 except ValueError as e:
  assert str(e).startswith('Nominal production STATUS rate absent/reduced:')
  strict_failure=str(e)
 else:raise AssertionError('Original strict failure disappeared')
 intact=audit(original,root/'pi/phase115_tls_observer_test.py')
 with tempfile.TemporaryDirectory(prefix='r2-mode-evidence-') as temporary:
  dest=Path(temporary)/name;shutil.copytree(original,dest)
  assert audit(dest,root/'pi/phase115_tls_observer_test.py')==intact
  cases=[('jobs.json',lambda v:v.update(nominal_seconds=299)),
         ('jobs.json',lambda v:v.update(source_revision='0'*40)),
         ('jobs.json',lambda v:v['jobs'][0].update(total_duration_ns='1')),
         ('jobs.json',lambda v:v.update(extra_unbound_field=True)),
         ('result.json',lambda v:v.update(load_exit=1))]
  rejected=[]
  for file,mutation in cases:
   p=dest/file;before=p.read_bytes();value=json.loads(before);mutation(value);save(p,value)
   try:
    try:audit(dest,root/'pi/phase115_tls_observer_test.py')
    except (ValueError,KeyError,AssertionError):rejected.append(file)
    else:raise AssertionError('Mutated evidence accepted: '+file)
   finally:p.write_bytes(before)
  p=dest/'usb-health.jsonl';before=p.read_bytes();rows=[json.loads(s) for s in before.splitlines()]
  for field,value in [('tail_irqs',0),('launch_delay_ns','1'),('allocator_failures',999),('core1_stack_guard_valid',0)]:
   modified=copy.deepcopy(rows)
   for row in modified:
    if row['kind']=='info':row['value']['value'][field]=value
   p.write_text(''.join(json.dumps(row)+'\n' for row in modified))
   try:
    try:audit(dest,root/'pi/phase115_tls_observer_test.py')
    except (ValueError,KeyError,AssertionError):rejected.append(field)
    else:raise AssertionError('Mutated raw observation accepted: '+field)
   finally:p.write_bytes(before)
  assert audit(dest,root/'pi/phase115_tls_observer_test.py')==intact
  results[name]=dict(intact_passed=True,rejected=len(rejected),rejected_mutations=rejected,intact_after_mutations_passed=True,original_strict_failure=strict_failure)
 save(root/'usb/amended-audit.json',intact)
 assert audit(original,root/'pi/phase115_tls_observer_test.py')==intact
save(root/'usb/amended-adversarial-review.json',results)
print(json.dumps(results))
