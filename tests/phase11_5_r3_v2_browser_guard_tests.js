'use strict';
const assert=require('node:assert/strict');
const {guardRequest,ORIGIN}=require('../scripts/phase11_5_r3_v2_browser_guard');
const context={operations:['ARM'],index:0,session:'a'.repeat(32),requestIds:new Set(),jobId:'b'.repeat(32),
  utcNowNs:'100000000000',chargedJobs:0,chargedNs:0n,case:{duration_ns:'150000000000'}};
const q={session_id:context.session,request_id:'c'.repeat(32),operation:'ARM',body:{job_id:context.jobId,start_utc_ns:'120000000000',max_start_uncertainty_ns:'500000000'}};
const req=body=>({url:ORIGIN+'/api/v1/jobs',method:'POST',postData:JSON.stringify(body)});
assert.equal(guardRequest(req(q),context).operation,'ARM');
for(const mutate of [r=>r.url='https://other.invalid/api/v1/jobs',r=>r.method='PUT',r=>r.url=ORIGIN+'/api/v1/config',
 r=>r.postData=r.postData.replace('120000000000','104999999999'),r=>r.postData=r.postData.replace('120000000000','160000000001'),
 r=>r.postData=r.postData.replace('b'.repeat(32),'d'.repeat(32)),r=>r.postData=r.postData.replace('500000000','1000000000')]) {
 const r=req(q);mutate(r);assert.throws(()=>guardRequest(r,context));
}
assert.throws(()=>guardRequest(req(q),{...context,chargedJobs:4}));
assert.throws(()=>guardRequest(req(q),{...context,chargedNs:500000000000n}));
assert.throws(()=>guardRequest(req(q),{...context,requestIds:new Set([q.request_id])}));
assert.equal(guardRequest({url:ORIGIN+'/api/v1/status',method:'GET'},context),null);
console.log('Actual-browser mutation guards: scope, timing, identity, replay and cumulative budget passed');
