'use strict';
// Pure guards for the actual Chromium producer. No browser, socket or RF access.
const assert = require('node:assert/strict');
const ORIGIN = 'https://wsprrypico-0a60df.local:18443';
function same(actual,expected) { assert.deepEqual(actual,expected); }
function sameAuthority(actual,expected) {
  return ['boot_id','state','job_id','owner_id','output_active'].every(key=>
    Object.hasOwn(actual,key)&&Object.hasOwn(expected,key)&&actual[key]===expected[key]);
}
function readyForJob(ui, expected, cancellation=false) {
  return ui.online===true && ui.busy===false && ui.job &&
    ['boot_id','state','job_id','owner_id','output_active'].every(key=>
      Object.hasOwn(ui.job,key)&&Object.hasOwn(expected,key)&&ui.job[key]===expected[key]) &&
    (!cancellation || ui.abortDisabled===false);
}
function guardRequest(request, context) {
  const url = new URL(request.url);
  assert.equal(url.origin,ORIGIN,'Unexpected browser origin');
  if (request.method === 'GET') {
    assert(['/', '/style.css', '/app.js', '/favicon.ico', '/api/v1/status', '/api/v1/capabilities', '/api/v1/config'].includes(url.pathname),'Unexpected read');
    return null;
  }
  assert.equal(request.method,'POST'); assert.equal(url.pathname,'/api/v1/jobs');
  const q=JSON.parse(request.postData);const step=context.operations[context.index];
  assert(step,'Unexpected extra mutation');assert.equal(q.operation,step);
  assert.equal(q.session_id,context.session);assert.match(q.request_id,/^[0-9a-f]{32}$/);
  assert(!context.requestIds.has(q.request_id),'Mutation retry');
  if(step==='HELLO') same(q.body,{versions:['WTP/1'],client_name:'WsprryPico browser',client_version:'1'});
  if(step==='CLAIM') same(q.body,{owner_id:context.session,lease_ms:30000});
  if(step==='LOAD') same(q.body,context.case.job);
  if(step==='LOAD_MESSAGE') {
    assert.match(q.body.job_id,/^[0-9a-f]{32}$/);
    const {job_id,...body}=q.body;same(body,context.case.message);
  }
  if(step==='ARM') {
    assert.equal(q.body.job_id,context.jobId); assert.equal(q.body.max_start_uncertainty_ns,'500000000');
    const start=BigInt(q.body.start_utc_ns),now=BigInt(context.utcNowNs);
    assert(start-now>=5000000000n && start-now<=60000000000n,'ARM lead outside finite allowance');
    assert(context.chargedJobs<4 && context.chargedNs+BigInt(context.case.duration_ns)<=600000000000n,'RF charge bound');
  }
  if(step==='ABORT') same(q.body,{job_id:context.jobId});
  if(step==='RELEASE') same(q.body,{});
  return q;
}
module.exports={guardRequest,ORIGIN,sameAuthority,readyForJob};
