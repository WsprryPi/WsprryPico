// Cleanup for the isolated browser and RAM-backed UI fixture processes.
import {rm} from 'node:fs/promises';

function hasExited(child) {return child.exitCode!==null || child.signalCode!==null;}

function signalOwned(child,signal,processGroup) {
    try {
        if(processGroup && child.pid)process.kill(-child.pid,signal);
        else child.kill(signal);
    } catch(error) {
        if(error.code!=='ESRCH')throw error;
    }
}

function signalAndWait(child,signal,timeoutMs,processGroup) {
    if(hasExited(child))return Promise.resolve(true);
    return new Promise((resolve,reject)=>{
        let timer,settled=false;
        function finish(exited,error) {
            if(settled)return;settled=true;
            clearTimeout(timer);child.removeListener('exit',onExit);
            if(error)reject(error);else resolve(exited);
        }
        function onExit() {finish(true);}
        // Subscribe before signalling, including an immediately exiting child.
        child.once('exit',onExit);
        timer=setTimeout(()=>finish(false),timeoutMs);
        try {
            signalOwned(child,signal,processGroup);
            if(hasExited(child))finish(true);
        } catch(error) {finish(false,error);}
    });
}

async function stopChild(child,timeoutMs,processGroup) {
    if(!child)return;
    if(!await signalAndWait(child,'SIGTERM',timeoutMs,processGroup) &&
       !await signalAndWait(child,'SIGKILL',timeoutMs,processGroup)) {
        throw Error('UI fixture process did not exit after SIGKILL');
    }
    // A browser can exit before its profile-writing descendants. These groups
    // belong only to detached processes started by this integration check.
    if(processGroup && child.pid)signalOwned(child,'SIGKILL',true);
}

export async function cleanupUiProcesses(children,profile,{timeoutMs=3000,processGroup=false,remove=rm}={}) {
    const results=await Promise.allSettled(children.map(child=>stopChild(child,timeoutMs,processGroup)));
    const errors=results.filter(result=>result.status==='rejected').map(result=>result.reason);
    if(errors.length===1)throw errors[0];
    if(errors.length)throw new AggregateError(errors,'UI fixture shutdown failed');
    await remove(profile,{recursive:true,force:true,maxRetries:10,retryDelay:100});
}
