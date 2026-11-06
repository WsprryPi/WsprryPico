// Expected failures must reach the intended oracle and finish owned cleanup.
import assert from 'node:assert/strict';
import test from 'node:test';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {mkdtemp,rm,access,readdir} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {deadlinePromise,preserveCleanup} from './browser_deadline.mjs';
import {cleanupUiProcesses,ownedGroupAlive,recoverOwnedGroup} from './ui_process_cleanup.mjs';
const driver=process.argv[2];if(!driver)throw Error('Actual consumer_bootstrap_driver required');await access(driver);
for(const mode of ['expiry','draft','mutation',null])test(mode?'pilot detects isolated '+mode+' defect and closes all writers':'signal during observed pilot initialization closes every owned resource',{timeout:200000},async()=>{
  const output=await mkdtemp(path.join(os.tmpdir(),'pico-pilot-sensitivity-'));
  const child=spawn(process.execPath,[fileURLToPath(new URL('./session_timeout_browser.mjs',import.meta.url)),driver,output],{
    detached:process.platform!=='win32',stdio:['ignore','pipe','pipe','ipc'],
    env:{...process.env,SESSION_PILOT_SENSITIVITY:mode||undefined,SESSION_PILOT_HOLD_INIT:mode?undefined:'1',UI_REVIEW_NO_CAPTURE:'1'}
  });
  const resources=new Map();let stderr='',stdout='',protocolFailure,primary,holdObserved=false;
  child.stderr.on('data',bytes=>{stderr=(stderr+bytes.toString()).slice(-65536);});
  child.stdout.on('data',bytes=>{stdout=(stdout+bytes.toString()).slice(-65536);});
  child.on('message',value=>{
    if(value?.kind==='session-pilot-initialization-held/1'){
      if(mode||Object.keys(value).length!==1||resources.size!==1){protocolFailure=Error('Invalid initialization hold');return;}
      holdObserved=true;void ownedGroupAlive([...resources.keys()][0]).then(live=>{if(!live)protocolFailure=Error('Initialization hold lacks a live owned server');child.kill('SIGTERM');},error=>{protocolFailure=error;child.kill('SIGTERM');});return;
    }
    if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(',')!=='kind,pid,profile'||value.kind!=='browser-owned-process/1'||!Number.isSafeInteger(value.pid)||value.pid<=1||resources.has(value.pid)||!(value.profile===null||typeof value.profile==='string'&&path.dirname(value.profile)===os.tmpdir()&&path.basename(value.profile).startsWith(`pico-session-browser-${child.pid}-`))){protocolFailure=Error('Invalid owned-process receipt');return;}
    resources.set(value.pid,value);
  });
  try{
    // Includes the 60-second cold browser budget and independent cleanup; this
    // is a hang watchdog, never a functional latency assertion.
    const result=await deadlinePromise('session-sensitivity-worker',(resolve,reject)=>{
      const closed=(code,signal)=>resolve({code,signal});child.once('close',closed);child.once('error',reject);
      return()=>{child.removeListener('close',closed);child.removeListener('error',reject);};
    },180000);
    if(protocolFailure)throw protocolFailure;
    assert.equal(result.code,1,stderr);assert.equal(result.signal,null);
    if(mode){
      const receipts=stderr.split('\n').flatMap(line=>{try{const value=JSON.parse(line);return value?.kind==='session-pilot-sensitivity/1'?[value]:[];}catch{return [];}});
      assert.equal(receipts.length,1,stderr);
      assert.deepEqual(receipts[0],{kind:'session-pilot-sensitivity/1',mode,fault_entered:true,assertion_detected:true,cleanup_completed:true});
      assert.equal(resources.size,2,'must independently retain the actual fixture and browser process groups');
    }else{assert.equal(holdObserved,true);assert.equal(resources.size,1);}
    for(const resource of resources.values())assert.equal(await ownedGroupAlive(resource.pid),false,'worker must close each actual owned group before reporting completed cleanup');
    assert.deepEqual((await readdir(os.tmpdir())).filter(name=>name.startsWith(`pico-session-browser-${child.pid}-`)),[],'private profile must be removed after its writers stop');
    await assert.rejects(access(path.join(output,'results.json')),{code:'ENOENT'},'a deliberate defect cannot emit a successful pilot result');
  }catch(error){primary=error;throw error;}
  finally{
    await preserveCleanup(primary,[
      ()=>cleanupUiProcesses([child],undefined,{processGroup:process.platform!=='win32',remove:async()=>{}}),
      ...[...resources.values()].map(resource=>async()=>{
        await recoverOwnedGroup(resource.pid);
        if(resource.profile)await rm(resource.profile,{recursive:true,force:true});
      }),
      async()=>{if(!primary)await rm(output,{recursive:true,force:true});}
    ]);
  }
});
