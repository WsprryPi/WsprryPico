import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {EventEmitter,once} from 'node:events';
import {access,mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
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

// Phase budgets and the JSON fixture run through the ordinary cleanup-test owner.
import {FixtureProcess} from './fixture_process.mjs';
import {createDeadlineTools,deadlinePromise,preserveCleanup} from './browser_deadline.mjs';
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
    const source=readFileSync(new URL('./progress_browser_integration.mjs',import.meta.url),'utf8');
    const code=source.slice(source.indexOf('class Cdp {'),source.indexOf('\nconst until='));
    class Socket extends EventTarget {
        readyState=1;sent=[];
        constructor(){super();Socket.last=this;}
        send(value){this.sent.push(JSON.parse(value));}
        reply(index,result){this.onmessage({data:JSON.stringify({id:this.sent[index].id,result})});}
    }
    const Cdp=new Function('deadlinePromise','WebSocket',code+';return Cdp;')(deadlinePromise,Socket);
    const cdp=new Cdp('owned-test');await cdp.open();
    const a=cdp.send('A'),b=cdp.send('B');Socket.last.reply(1,{value:'b'});Socket.last.reply(0,{value:'a'});
    assert.deepEqual(await Promise.all([a,b]),[{value:'a'},{value:'b'}]);
    const missing=cdp.send('lost');const refused=assert.rejects(missing,/socket/);Socket.last.dispatchEvent(new Event('close'));await refused;
    assert.equal(cdp.pending.size,0);
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
        patched=t.mock.method(process,'kill',(pid,signal)=>{
            if(pid===-f.process.pid&&signal!=='SIGKILL')throw Object.assign(Error('owned signal denied'),{code:'EPERM'});
            return realKill(pid,signal);
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
        await once(f.process.stdout,'end');
        await assert.rejects(f.command({op:'after-eof'}),/stdout closed|driver is closed/);
        assert.equal(f.stderr.includes(secret),false);
        assert.equal(String(f.failure).includes(secret),false);
    }finally{await f.stop();}
});
