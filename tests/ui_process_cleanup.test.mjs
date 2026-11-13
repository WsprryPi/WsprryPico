import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {EventEmitter,once} from 'node:events';
import {access,mkdtemp,rm,writeFile,readFile,chmod} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import test from 'node:test';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

class Child extends EventEmitter {
    exitCode=null;
    signalCode=null;
    signals=[];
    constructor(onSignal) {super();this.onSignal=onSignal;}
    kill(signal) {this.signals.push(signal);this.onSignal?.(signal,this);return true;}
    finish(signal) {this.signalCode=signal;this.emit('exit',null,signal);}
}

test('cleanup confirms forced termination before removing a live browser profile',async()=>{
    const child=new Child((signal,child)=>{
        if(signal==='SIGKILL')queueMicrotask(()=>child.finish(signal));
    });
    let removed=false;
    await cleanupUiProcesses([child],'/unused/profile',{timeoutMs:2,remove:async()=>{
        assert.equal(child.signalCode,'SIGKILL','profile must outlive its writer');removed=true;
    }});
    assert.deepEqual(child.signals,['SIGTERM','SIGKILL']);
    assert.equal(removed,true);
    assert.equal(child.listenerCount('exit'),0);
});

test('an already signalled child needs no new signal or exit event',async()=>{
    const child=new Child();child.signalCode='SIGTERM';
    await cleanupUiProcesses([undefined,child],'/unused/profile',{timeoutMs:2,remove:async()=>{}});
    assert.deepEqual(child.signals,[]);
    assert.equal(child.listenerCount('exit'),0);
});

test('shutdown failure still cleans the other fixture and preserves the profile',async()=>{
    const error=Object.assign(Error('signal denied'),{code:'EPERM'});
    const browser=new Child(()=>{throw error;});
    const fixture=new Child((signal,child)=>child.finish(signal));
    let removed=false;
    await assert.rejects(cleanupUiProcesses([browser,fixture],'/unused/profile',{
        timeoutMs:2,remove:async()=>{removed=true;}
    }),error);
    assert.equal(fixture.signalCode,'SIGTERM');
    assert.equal(removed,false);
    assert.equal(browser.listenerCount('exit'),0);
});

test('unconfirmed forced termination fails without deleting a live profile',async()=>{
    const child=new Child();let removed=false;
    await assert.rejects(cleanupUiProcesses([child],'/unused/profile',{
        timeoutMs:2,remove:async()=>{removed=true;}
    }),/did not exit/);
    assert.deepEqual(child.signals,['SIGTERM','SIGKILL']);
    assert.equal(removed,false);
    assert.equal(child.listenerCount('exit'),0);
});

test('persistent profile removal errors remain visible',async()=>{
    const child=new Child();child.exitCode=0;
    const error=Object.assign(Error('profile still busy'),{code:'ENOTEMPTY'});
    await assert.rejects(cleanupUiProcesses([child],'/unused/profile',{
        remove:async()=>{throw error;}
    }),error);
});

test('owned profile writer descendants stop after their parent exits',{
    skip:process.platform==='win32',timeout:5000
},async t=>{
    const profile=await mkdtemp(path.join(os.tmpdir(),'wsprrypico-cleanup-test-'));
    const writer=`
        const fs=require('node:fs'),path=require('node:path');
        const directory=path.join(process.argv[1],'Default');
        function write(){fs.mkdirSync(directory,{recursive:true});fs.writeFileSync(path.join(directory,'state'),'busy');}
        process.on('SIGTERM',()=>{});write();setInterval(write,5);process.send('ready');
    `;
    const parent=`
        const {spawn}=require('node:child_process');
        process.on('SIGTERM',()=>process.exit(0));
        const writer=spawn(process.execPath,['-e',${JSON.stringify(writer)},process.argv[1]],
            {stdio:['ignore','inherit','inherit','ipc']});
        writer.once('message',()=>process.send('ready'));
    `;
    const child=spawn(process.execPath,['-e',parent,profile],{
        stdio:['ignore','pipe','pipe','ipc'],detached:true
    });
    t.after(async()=>{
        try {process.kill(-child.pid,'SIGKILL');}catch(error){if(error.code!=='ESRCH')throw error;}
        await rm(profile,{recursive:true,force:true,maxRetries:10,retryDelay:100});
    });
    const closed=once(child,'close');
    await once(child,'message');
    await cleanupUiProcesses([child],profile,{processGroup:true,timeoutMs:100});
    await closed; // The descendant inherited stdio, so parent exit alone cannot close it.
    assert.equal(child.exitCode,0,'parent finished its graceful shutdown');
    await assert.rejects(access(profile),{code:'ENOENT'});
});

test('an exited owned group with an EPERM probe does not block profile removal',{
    skip:process.platform==='win32',timeout:5000
},async t=>{
    const child=spawn(process.execPath,['-e',''],{detached:true,stdio:'ignore'});
    await once(child,'exit');
    const kill=process.kill.bind(process),signals=[];
    t.mock.method(process,'kill',(pid,signal)=>{
        if(pid!==-child.pid)return kill(pid,signal);
        signals.push(signal);
        throw Object.assign(Error('exiting group'),{code:'EPERM'});
    });
    let removed=false;
    await cleanupUiProcesses([child],'/unused/profile',{
        processGroup:true,remove:async()=>{removed=true;}
    });
    assert.equal(removed,true);
    assert.ok(signals.length>0);
    assert.ok(signals.every(signal=>signal===0),'no kill is needed after all group members exit');
});

test('a denied group kill preserves the profile while an owned writer is live',{
    skip:process.platform==='win32',timeout:10000
},async t=>{
    const child=spawn(process.execPath,['-e',"process.send('ready');setInterval(()=>{},1000)"],{
        detached:true,stdio:['ignore','ignore','ignore','ipc']
    });
    const kill=process.kill.bind(process);
    let patched,removed=false,denied=false;
    try{
        await once(child,'message');
        patched=t.mock.method(process,'kill',(pid,signal)=>{
            if(pid===-child.pid&&signal==='SIGKILL'){
                denied=true;throw Object.assign(Error('live group denied'),{code:'EPERM'});
            }
            return kill(pid,signal);
        });
        // Model a browser parent that has exited while its owned group still
        // contains this writer; only group cleanup may stop the remaining process.
        await assert.rejects(cleanupUiProcesses([{pid:child.pid,exitCode:0,signalCode:null}],'/unused/profile',{
            processGroup:true,remove:async()=>{removed=true;}
        }),/live group denied/);
        assert.equal(denied,true);
        assert.equal(removed,false);
        kill(child.pid,0);
    }finally{
        patched?.mock.restore();
        const exited=once(child,'exit');kill(child.pid,'SIGKILL');await exited;
    }
});

test('a group exiting between probe and kill permits removal after fresh observation',{
    skip:process.platform==='win32',timeout:5000
},async t=>{
    const child=spawn(process.execPath,['-e',"process.send('ready');setInterval(()=>{},1000)"],{
        detached:true,stdio:['ignore','ignore','ignore','ipc']
    });
    const kill=process.kill.bind(process),signals=[];
    let patched,removed=false;
    const exited=once(child,'exit');
    try{
        await once(child,'message');
        patched=t.mock.method(process,'kill',(pid,signal)=>{
            if(pid!==-child.pid)return kill(pid,signal);
            signals.push(signal);
            if(signal==='SIGKILL'){
                kill(child.pid,'SIGKILL');
                throw Object.assign(Error('group exited during signal'),{code:'EPERM'});
            }
            return kill(pid,signal);
        });
        await cleanupUiProcesses([{pid:child.pid,exitCode:0,signalCode:null}],'/unused/profile',{
            processGroup:true,remove:async()=>{removed=true;}
        });
        assert.equal(removed,true);
        assert.deepEqual(signals.slice(0,3),[0,'SIGKILL',0],'denial requires a fresh group observation');
    }finally{
        patched?.mock.restore();
        if(child.exitCode===null&&child.signalCode===null)kill(child.pid,'SIGKILL');
        await exited;
    }
});

// Phase budgets and the JSON fixture run through the ordinary cleanup-test owner.
import {FixtureProcess} from './fixture_process.mjs';
import {createDeadlineTools,deadlinePromise,preserveCleanup,until} from './browser_deadline.mjs';
import {readFileSync} from 'node:fs';
function fixtureObservation(child,text) {
    return deadlinePromise('fixture-observation',(resolve,reject)=>{
        let seen='';const data=bytes=>{seen+=bytes;if(seen.includes(text))resolve();};
        child.stderr.on('data',data);return()=>child.stderr.removeListener('data',data);
    },5000);
}

test('actual fixture accepts a gated fragmented response and serializes later commands',{timeout:10000},async()=>{
    const code=`let input='',held;process.stdin.setEncoding('utf8');process.stdin.on('data',bytes=>{input+=bytes;let end;while((end=input.indexOf('\\n'))>=0){const line=input.slice(0,end);input=input.slice(end+1);if(line==='RELEASE'){process.stdout.write(held);continue;}const value=JSON.parse(line);const answer=JSON.stringify(value)+'\\n';if(value.op==='fragment'){process.stdout.write(answer.slice(0,5));held=answer.slice(5);process.stderr.write('FRAGMENT_HELD\\n');}else process.stdout.write(answer);}});`;
    const f=new FixtureProcess(process.execPath,['-e',code]);
    try {
        const entered=fixtureObservation(f.process,'FRAGMENT_HELD');
        const first=f.command({op:'fragment',value:'λ'}),second=f.command({op:'next',value:2});
        await entered;assert.equal(f.queue.length,1);
        f.process.stdin.write('RELEASE\n');
        assert.deepEqual(await first,{op:'fragment',value:'λ'});
        assert.deepEqual(await second,{op:'next',value:2});
    }finally{await f.stop();}
});

test('an acknowledged held command times out and ignored EOF cannot prevent owned teardown',{timeout:12000},async()=>{
    let now=0;const timers=new Set();
    const tools=createDeadlineTools({clock:()=>now,setTimer:fn=>{timers.add(fn);return fn;},clearTimer:fn=>timers.delete(fn)});
    const code=`process.on('SIGTERM',()=>process.stderr.write('TERM_IGNORED\\n'));process.stdin.on('data',()=>process.stderr.write('COMMAND_HELD\\n'));process.stdin.on('end',()=>process.stderr.write('EOF_IGNORED\\n'));setInterval(()=>{},1000);`;
    const f=new FixtureProcess(process.execPath,['-e',code],{deadline:tools.deadlinePromise,cleanupMs:1000});
    try {
        const entered=fixtureObservation(f.process,'COMMAND_HELD');const command=f.command({op:'hold'});
        const rejected=assert.rejects(command,/stage=fixture-command/);
        await entered;const eof=fixtureObservation(f.process,'EOF_IGNORED');now=20001;
        for(const timer of [...timers])timer();await rejected;await eof;await f.stop();
        assert.notEqual(f.process.signalCode,null);assert.equal(f.queue.length,0);
        assert.throws(()=>process.kill(f.process.pid,0),{code:'ESRCH'});
    }finally{await f.stop();}
});

test('fixture spawn failure, malformed JSON and stdout EOF refuse instead of waiting',{timeout:10000},async()=>{
    for(const [executable,args,expected] of [
        ['/no/such/fixture',[],/fixture-spawn/],
        [process.execPath,['-e',`process.stdin.once('data',()=>process.stdout.write('not-json\\n'));`],/malformed JSON/],
        [process.execPath,['-e',`process.stdin.once('data',()=>process.stdout.end());`],/stdout closed|fixture-exit/]
    ]) {
        const f=new FixtureProcess(executable,args);
        try{await assert.rejects(f.command({op:'probe'}),expected);}finally{await f.stop();}
    }
});

test('monotonic stage refuses late inner success and propagates its remaining command budget',async()=>{
    let now=0;const tools=createDeadlineTools({clock:()=>now});
    let enter,release;const entered=new Promise(resolve=>enter=resolve),gate=new Promise(resolve=>release=resolve);
    const result=tools.until(async()=>{enter();return gate;},'held-readiness',1000);
    await entered;now=1001;release(true);await assert.rejects(result,/stage=held-readiness/);
    now=0;const budgets=[];
    await tools.until(()=>{now=400;return tools.deadlinePromise('inner',resolve=>{budgets.push(tools.remaining());resolve(true);});},'parent',1000);
    assert.deepEqual(budgets,[600]);
});

test('actual progress CDP dispatch preserves reordered replies and refuses socket loss',async()=>{
    const {Cdp}=await import('./browser_cdp.mjs');
    class Socket extends EventTarget {
        readyState=1;sent=[];
        constructor(){super();Socket.last=this;}
        send(value){this.sent.push(JSON.parse(value));}
        reply(index,result){this.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({id:this.sent[index].id,result})}));}
        close(){this.readyState=3;this.dispatchEvent(new Event('close'));}
    }
    const cdp=new Cdp('ws://127.0.0.1:12345/devtools/page/owned-test',{WebSocketImpl:Socket});await cdp.open();
    const a=cdp.send('A'),b=cdp.send('B');Socket.last.reply(1,{value:'b'});Socket.last.reply(0,{value:'a'});
    assert.deepEqual(await Promise.all([a,b]),[{value:'a'},{value:'b'}]);
    const missing=cdp.send('lost');const refused=assert.rejects(missing,/socket/);Socket.last.dispatchEvent(new Event('close'));await refused;
    assert.equal(cdp.pending.size,0);await cdp.stop();
});

test('cleanup retains the original failure and attempts every remaining finalizer',async()=>{
    const primary=Error('original operation failed'),cleanup=Error('owned cleanup failed');let last=false;
    await assert.rejects(preserveCleanup(primary,[async()=>{throw cleanup;},async()=>{last=true;}]),error=>{
        assert.deepEqual(error.errors,[primary,cleanup]);return true;
    });
    assert.equal(last,true);
});

test('owned fixture timeout and denied cleanup remain visible together',{skip:process.platform==='win32',timeout:12000},async t=>{
    let now=0;const timers=new Set();
    const tools=createDeadlineTools({clock:()=>now,setTimer:fn=>{timers.add(fn);return fn;},clearTimer:fn=>timers.delete(fn)});
    const code=`process.stdin.on('data',()=>process.stderr.write('COMMAND_HELD\\n'));process.stdin.on('end',()=>process.stderr.write('EOF_IGNORED\\n'));setInterval(()=>{},1000);`;
    const f=new FixtureProcess(process.execPath,['-e',code],{deadline:tools.deadlinePromise,cleanupMs:1000});
    const realKill=process.kill.bind(process);let patched;
    try {
        const entered=fixtureObservation(f.process,'COMMAND_HELD');const refused=assert.rejects(f.command({op:'hold'}),/fixture-command/);await entered;
        const childKill=f.process.kill.bind(f.process);
        patched=t.mock.method(f.process,'kill',signal=>{
            if(signal==='SIGTERM')throw Object.assign(Error('owned signal denied'),{code:'EPERM'});
            return childKill(signal);
        });
        now=20001;for(const timer of [...timers])timer();await refused;
        await assert.rejects(f.stop(),error=>{
            assert.match(String(error.errors?.[0]),/fixture-command/);assert.match(String(error.errors?.[1]),/owned signal denied/);return true;
        });
    }finally{
        patched?.mock.restore();
        if(f.process.exitCode===null&&f.process.signalCode===null){
            const closed=deadlinePromise('probe-owned-reap',resolve=>{f.process.once('exit',resolve);return()=>f.process.removeListener('exit',resolve);},5000);
            realKill(-f.process.pid,'SIGKILL');await closed;
        }
    }
});

test('synchronous completion cannot hide a subsequently acquired disposer failure',async()=>{
    const primary=Error('synchronous rejection'),cleanup=Error('dispose denied');
    await assert.rejects(deadlinePromise('empty rejection',(_resolve,reject)=>reject()),/rejected without diagnostic/);
    await assert.rejects(deadlinePromise('synchronous success',resolve=>{resolve(true);return()=>{throw cleanup;};}),error=>{
        assert.deepEqual(error.errors,[cleanup]);return true;
    });
    await assert.rejects(deadlinePromise('synchronous failure',(_resolve,reject)=>{reject(primary);return()=>{throw cleanup;};}),error=>{
        assert.deepEqual(error.errors,[primary,cleanup]);return true;
    });
});

test('idle stdout EOF refuses new commands and diagnostics retain no stderr secrets',{timeout:10000},async()=>{
    const secret='credential-PHASE7-SECRET';
    const code=`process.stderr.write(${JSON.stringify(secret)});process.stdout.end();process.stdin.resume();`;
    const f=new FixtureProcess(process.execPath,['-e',code]);
    try {
        await deadlinePromise('fixture-idle-eof',resolve=>{
            if(f.stdoutClosed||f.process.stdout.readableEnded){resolve();return;}
            f.process.stdout.once('end',resolve);return()=>f.process.stdout.removeListener('end',resolve);
        },5000);
        await assert.rejects(f.command({op:'after-eof'}),/stdout closed|driver is closed/);
        assert.equal(f.stderr.includes(secret),false);
        assert.equal(String(f.failure).includes(secret),false);
    }finally{await f.stop();}
});

test('last successful reply cannot hide a subsequent nonzero fixture exit',{timeout:10000},async()=>{
    const f=new FixtureProcess(process.execPath,['-e',`process.stdin.once('data',()=>process.stdout.write('{}\\n',()=>process.exit(17)));`]);
    const exited=once(f.process,'exit');
    assert.deepEqual(await f.command({op:'last'}),{});await exited;
    let failure;
    await assert.rejects(f.stop(),error=>{
        failure=error;
        const errors=error instanceof AggregateError?error.errors:[error];
        assert.ok(errors.some(item=>/child_exit=17/.test(String(item))));return true;
    });
    await assert.rejects(f.stop(),error=>error===failure,'idempotent finalization retains its failed outcome');
});

test('nonzero exit caused by orderly EOF cannot qualify fixture shutdown',{timeout:10000},async()=>{
    const f=new FixtureProcess(process.execPath,['-e',`process.stdin.on('data',()=>process.stdout.write('{}\\n'));process.stdin.on('end',()=>process.exit(19));`]);
    assert.deepEqual(await f.command({op:'ready'}),{});
    await assert.rejects(f.stop(),/child_exit=19/);
});

test('invalid UTF-8 and oversized JSON lines cannot become valid fixture responses',{timeout:10000},async()=>{
    for(const answer of [`Buffer.from([123,34,120,34,58,34,255,34,125,10])`,`Buffer.alloc(2*1024*1024+4097,32)`]){
        const f=new FixtureProcess(process.execPath,['-e',`process.stdin.once('data',()=>process.stdout.write(${answer}));`]);
        try{await assert.rejects(f.command({op:'probe'}),/malformed JSON\/UTF-8|byte bound/);}finally{await f.stop();}
    }
});


function observedDriver(body) {
    return `#!/usr/bin/env node\nconst fs=require('node:fs');const destination=process.env.FIXTURE_OWNER_OBSERVATION;const report=stage=>{fs.writeFileSync(destination+'.tmp',JSON.stringify({pid:process.pid,stage}));fs.renameSync(destination+'.tmp',destination);};${body}\n`;
}

const reviewFixture=fileURLToPath(new URL('./ui_review_fixture.mjs',import.meta.url));
async function observeInitialization(fixture,observation,label){
    let stderr='',closed,spawnError;
    const diagnostic=bytes=>{stderr=(stderr+bytes.toString()).slice(-8192);};
    const close=(code,signal)=>{closed={code,signal};};
    const error=value=>{spawnError=value;};
    fixture.stderr.on('data',diagnostic);fixture.once('close',close);fixture.once('error',error);
    const check=()=>{
        if(spawnError||closed)throw Error(`stage=${label}; fixture exited before initialization; child_exit=${closed?.code}; child_signal=${closed?.signal}; ${spawnError?.message||''}; stderr=${stderr}`);
    };
    try{return await until(async()=>{
        check();let value;
        try{value=JSON.parse(await readFile(observation,'utf8'));}
        catch(error){if(error.code!=='ENOENT')throw error;}
        check();return value||false;
    },label,5000);}
    finally{fixture.stderr.removeListener('data',diagnostic);fixture.removeListener('close',close);fixture.removeListener('error',error);}
}

test('initialization observation reports an actual missing worker instead of a readiness timeout',{timeout:10000},async()=>{
    const directory=await mkdtemp(path.join(os.tmpdir(),'pico-init-exit-'));
    const missing=path.join(directory,'missing-worker.mjs');
    const fixture=spawn(process.execPath,[missing],{stdio:['ignore','pipe','pipe'],detached:process.platform!=='win32'});
    try{
        await assert.rejects(observeInitialization(fixture,path.join(directory,'never-created.json'),'missing-worker'),error=>{
            assert.match(error.message,/fixture exited before initialization; child_exit=1/);
            assert.ok(error.message.includes('Cannot find module')&&error.message.includes(missing));
            assert.ok(!error.message.includes('last_transition=pending'));return true;
        });
    }finally{await cleanupUiProcesses([fixture],directory,{processGroup:process.platform!=='win32'});}
});

test('review fixture interruption during initialization reaps its registered driver',{timeout:15000},async()=>{
    const directory=await mkdtemp(path.join(os.tmpdir(),'pico-initialization-owner-'));
    const driver=path.join(directory,'driver.cjs'),observation=path.join(directory,'observed.json');
    await writeFile(driver,observedDriver("process.stdin.on('data',()=>report('held'));process.stdin.on('end',()=>process.exit(0));"));
    await chmod(driver,0o755);
    let fixture,driverPid;
    try{
        fixture=spawn(process.execPath,[reviewFixture,driver,'19189',directory],{
            stdio:['ignore','pipe','pipe'],detached:process.platform!=='win32',
            env:{...process.env,FIXTURE_OWNER_OBSERVATION:observation}
        });
        const exited=once(fixture,'exit');
        const observed=await observeInitialization(fixture,observation,'observed initialization command');
        assert.equal(observed.stage,'held');driverPid=observed.pid;process.kill(driverPid,0);
        assert.equal(fixture.kill('SIGTERM'),true,'fault requires a live initialization owner');
        const [code]=await deadlinePromise('interrupted fixture exit',(resolve,reject)=>{exited.then(resolve,reject);},7000);
        assert.notEqual(code,0,'interrupted initialization cannot qualify a ready fixture');
        assert.throws(()=>process.kill(driverPid,0),{code:'ESRCH'},'registered driver must be reaped before owner exits');
    }finally{
        if(fixture)await cleanupUiProcesses([fixture],undefined,{processGroup:process.platform!=='win32',remove:async()=>{}});
        if(driverPid){try{process.kill(-driverPid,'SIGKILL');}catch(error){if(error.code!=='ESRCH')throw error;}}
        await rm(directory,{recursive:true,force:true});
    }
});


test('a failing fixture stream finalizer cannot skip the remaining stream finalizers',async()=>{
    const finished=[];
    const f=Object.create(FixtureProcess.prototype);
    f.process={exitCode:0,signalCode:null};f.stopping=null;
    for(const name of ['stdin','stdout','stderr'])f.process[name]={destroy(){
        finished.push(name);if(name==='stdin')throw Error('owned stream disposer failed');
    }};
    await assert.rejects(f.stop(),error=>{
        assert.ok(error instanceof AggregateError);
        assert.ok(error.errors.some(item=>/owned stream disposer failed/.test(String(item))));return true;
    });
    assert.deepEqual(finished,['stdin','stdout','stderr']);
});


test('abrupt review-server exit cannot strand its initialized native driver group',{skip:process.platform==='win32',timeout:15000},async()=>{
    const directory=await mkdtemp(path.join(os.tmpdir(),'pico-group-owner-'));
    const driver=path.join(directory,'driver.cjs'),observation=path.join(directory,'observed.json');
    await writeFile(driver,observedDriver("process.on('SIGTERM',()=>{});process.stdin.on('data',()=>report('held'));process.stdin.on('end',()=>report('eof-held'));setInterval(()=>{},1000);"));
    await chmod(driver,0o755);
    let fixture,driverPid,removed=false;
    const dead=async()=>{
        if(process.platform==='linux'){
            try{return (await readFile(`/proc/${driverPid}/stat`,'utf8')).split(/\) (?=[A-Za-z] )/).at(-1).split(' ')[0]==='Z';}
            catch(error){if(error.code==='ENOENT')return true;throw error;}
        }
        try{return execFileSync('ps',['-o','stat=','-p',String(driverPid)],{encoding:'utf8'}).trim().startsWith('Z');}
        catch(error){if(error.status===1)return true;throw error;}
    };
    try{
        fixture=spawn(process.execPath,[reviewFixture,driver,'19189',directory],{
            stdio:['ignore','pipe','pipe'],detached:true,env:{...process.env,FIXTURE_OWNER_OBSERVATION:observation}
        });
        const observed=await observeInitialization(fixture,observation,'observed held initialization');
        driverPid=observed.pid;
        const group=Number(execFileSync('ps',['-o','pgid=','-p',String(driverPid)],{encoding:'utf8'}).trim());
        assert.equal(group,fixture.pid,'native driver must remain inside the browser-owned server group');
        assert.equal(fixture.kill('SIGTERM'),true,'fault requires a live initialization owner');
        await until(async()=>JSON.parse(await readFile(observation,'utf8')).stage==='eof-held','observed ignored driver EOF',5000);
        const exited=once(fixture,'exit');assert.equal(fixture.kill('SIGKILL'),true);
        const [code,signal]=await exited;assert.equal(code,null);assert.equal(signal,'SIGKILL');
        assert.equal(await dead(),false,'the fault must leave a live driver before group recovery');
        await cleanupUiProcesses([fixture],directory,{processGroup:true,remove:async(profile,options)=>{
            assert.equal(await dead(),true,'profile removal requires observed descendant death');
            removed=true;await rm(profile,options);
        }});
        assert.equal(removed,true);
    }finally{
        if(fixture)await cleanupUiProcesses([fixture],directory,{processGroup:true});
        if(driverPid&&!await dead())process.kill(driverPid,'SIGKILL');
    }
});
