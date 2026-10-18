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
