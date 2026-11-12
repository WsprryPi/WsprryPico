// Cleanup for the isolated browser and RAM-backed UI fixture processes.
import {rm,readdir,readFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {performance} from 'node:perf_hooks';
import {createDeadlineTools} from './browser_deadline.mjs';
const cleanupDeadlines=createDeadlineTools(); // Cleanup survives an expired operation budget.
const executeFile=promisify(execFile);

async function groupAlive(pid,budget) {
    try{process.kill(-pid,0);}catch(error){if(error.code==='ESRCH')return false;if(error.code!=='EPERM')throw error;}
    if(process.platform==='linux') {
        for(const entry of await readdir('/proc')) {
            if(!/^\d+$/.test(entry))continue;
            try {
                const fields=(await readFile(`/proc/${entry}/stat`,'utf8')).split(/\) (?=[A-Za-z] )/).at(-1).split(' ');
                // Dead zombies cannot write a profile; their parent/init owns reaping.
                if(Number(fields[2])===pid&&fields[0]!=='Z')return true;
            }catch(error){if(error.code!=='ENOENT'&&error.code!=='ESRCH')throw error;}
        }
        return false;
    }
    const {stdout}=await executeFile('ps',['-axo','pgid=,stat='],{timeout:Math.ceil(budget)});
    return stdout.trim().split('\n').some(line=>{const [group,state]=line.trim().split(/\s+/);return Number(group)===pid&&!state.startsWith('Z');});
}

// Recovery is limited to groups retained from this run's ownership records.
export async function ownedGroupAlive(pid,timeoutMs=3000) {
    if(!Number.isSafeInteger(pid)||pid<=1)throw TypeError('Retained owned group required');
    return cleanupDeadlines.deadlinePromise('owned-group-probe',(resolve,reject,budget)=>{
        groupAlive(pid,budget).then(resolve,reject);
    },timeoutMs);
}
export async function recoverOwnedGroup(pid,timeoutMs=3000) {
    await killOwnedGroup(pid,timeoutMs);
    await cleanupDeadlines.until(async()=>!await ownedGroupAlive(pid,timeoutMs),'owned-group-recovery',timeoutMs);
}

async function killOwnedGroup(pid,timeoutMs) {
    if(!await ownedGroupAlive(pid,timeoutMs))return;
    try{process.kill(-pid,'SIGKILL');}
    catch(error){
        if(error.code==='ESRCH')return;
        // macOS can refuse a group signal while its last members exit. Only
        // an independent observation of no live members permits profile removal.
        if(error.code==='EPERM'&&!await ownedGroupAlive(pid,timeoutMs))return;
        throw error;
    }
}

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
    const end=performance.now()+2*timeoutMs;
    // Let an orchestrator close its owned channels before signalling drivers.
    // Forced recovery still targets the complete retained group.
    if(!await signalAndWait(child,'SIGTERM',timeoutMs,false) &&
       !await signalAndWait(child,'SIGKILL',Math.max(0,end-performance.now()),processGroup)) {
        throw Error('UI fixture process did not exit after SIGKILL');
    }
    // A browser can exit before its profile-writing descendants. These groups
    // belong only to detached processes started by this integration check.
    if(processGroup && child.pid) {
        await killOwnedGroup(child.pid,Math.max(1,end-performance.now()));
        await cleanupDeadlines.until(()=>cleanupDeadlines.deadlinePromise('owned-group-observation',
            (resolve,reject,budget)=>{groupAlive(child.pid,budget).then(live=>resolve(!live),reject);}),
            'owned-process-group-exit',Math.max(0,end-performance.now()));
    }
}

export async function cleanupUiProcesses(children,profile,{timeoutMs=3000,processGroup=false,remove=rm}={}) {
    const results=await Promise.allSettled(children.map(child=>stopChild(child,timeoutMs,processGroup)));
    const errors=results.filter(result=>result.status==='rejected').map(result=>result.reason);
    if(errors.length===1)throw errors[0];
    if(errors.length)throw new AggregateError(errors,'UI fixture shutdown failed');
    await remove(profile,{recursive:true,force:true,maxRetries:10,retryDelay:100});
}
