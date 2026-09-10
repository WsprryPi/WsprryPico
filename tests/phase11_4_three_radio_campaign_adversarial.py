#!/usr/bin/env python3
"""Offline adversarial campaign checks; requires a completed private evidence directory."""
import argparse,json,shutil,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_4_three_radio_campaign_audit import assess
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('root',type=Path)
root=parser.parse_args().root.resolve()
original=assess(root); results=[]
def mutate_json(path, edit, lines=False):
 value=[json.loads(s) for s in path.read_text().splitlines()] if lines else json.loads(path.read_text())
 edit(value);path.unlink()
 path.write_text(('\n'.join(json.dumps(v) for v in value) if lines else json.dumps(value))+'\n')
def trial(label,edit):
 with tempfile.TemporaryDirectory(prefix='campaign-review-') as name:
  d=Path(name)/'series';d.mkdir()
  (d.parent/'events.jsonl').symlink_to(root.parent/'events.jsonl')
  for p in root.rglob('*'):
   q=d/p.relative_to(root)
   if p.is_dir():q.mkdir(exist_ok=True)
   else:q.symlink_to(p)
  edit(d)
  try:assess(d)
  except ValueError as e:results.append({'case':label,'rejected':True,'reason':str(e)})
  else:raise RuntimeError('Admitted: '+label)
trial('seven cases cannot close campaign',lambda d:shutil.rmtree(d/'case-08'))
trial('extra numbered case refused',lambda d:(d/'case-09').mkdir())
trial('incomplete campaign refused',lambda d:mutate_json(d/'campaign.json',lambda v:v.__setitem__('complete',False)))
def change_sessions(d):
 for p in (d/'case-02').glob('peer2-*/events.jsonl'):
  def edit(rows):
   for r in rows:
    if r['kind'] in ('client_request','client_received'):r['value']['session_id']='0'*31+'2'
  mutate_json(p,edit,True)
trial('session churn between cases refused',change_sessions)
def repeat_request(d):
 first=[json.loads(s) for s in (d/'case-01/peer1-before/events.jsonl').read_text().splitlines()]
 rid=next(r['value']['request_id'] for r in first if r['kind']=='client_request' and r['value']['op']=='HELLO')
 def edit(rows):
  for r in rows:
   if r['kind'] in ('client_request','client_received') and r['value']['op']=='HELLO':r['value']['request_id']=rid
 mutate_json(d/'case-02/peer1-before/events.jsonl',edit,True)
trial('request replay between cases refused',repeat_request)
def remove_ack(d):
 records=[json.loads(s) for s in (d/'case-01/events.jsonl').read_text().splitlines()]
 on=next(r['epoch_ns'] for r in records if r['kind']=='on_begin')
 def edit(rows):
  rows.remove(next(r for r in rows if r['kind']=='WIFI ON' and r['epoch_ns']>on))
 mutate_json(d.parent/'events.jsonl',edit,True)
trial('missing device control acknowledgement refused',remove_ack)
assert assess(root)==original
print(json.dumps({'checks':results,'final_reassessment':'PASS','new_actionable_findings':0},indent=2))
