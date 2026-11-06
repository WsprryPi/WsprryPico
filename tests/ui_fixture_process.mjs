// Owned review-server startup with complete-line readiness, not a startup delay.
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {deadlinePromise} from './browser_deadline.mjs';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';
import {parseProfileSelection} from './ui_fixture_profiles.mjs';

export function launchUiFixture(executable,port,output,{profiles,messages=false,processGroup=process.platform!=='win32',timeoutMs=20000,spawnImpl=spawn,deadline=deadlinePromise}={}) {
  if(typeof executable!=='string'||!executable||executable.includes('\0')||typeof output!=='string'||output.includes('\0')||typeof processGroup!=='boolean'||!Number.isFinite(timeoutMs)||timeoutMs<=0||typeof spawnImpl!=='function'||typeof deadline!=='function')throw TypeError('Valid fixture paths, ownership, and finite watchdog required');
  if(profiles!==undefined&&(!Array.isArray(profiles)||!profiles.length||!profiles.every(name=>typeof name==='string'&&!name.includes(','))))throw TypeError('Explicit nonempty named profile list required');
  const flags=[...(messages?['messages']:[]),...(profiles===undefined?[]:['--profiles='+profiles.join(',')])];
  const {selected}=parseProfileSelection(flags,port);
  const expected=new Map(selected.map(value=>[value.name,value]));

  let child;const records=new Map();let buffer=Buffer.alloc(0),stderrBytes=0,failure,stopping,stopRequested=false,started=false,resolveStartup,rejectStartup;
  const fail=error=>{failure ||=error;rejectStartup?.(failure);};
  const data=bytes=>{
    if(failure)return;
    try{
      buffer=Buffer.concat([buffer,bytes]);if(buffer.length>65536)throw Error('startup output exceeds byte bound');
      let end;
      while((end=buffer.indexOf(10))>=0){
        const line=new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,end));buffer=buffer.subarray(end+1);
        if(started)throw Error('unexpected output after readiness');
        if(line.startsWith('READY;')){
          if(records.size!==expected.size||new Set([...records.values()].map(value=>value.driver_pid)).size!==expected.size)throw Error('incomplete or duplicate driver inventory');
          started=true;resolveStartup?.([...records.values()]);continue;
        }
        const value=JSON.parse(line),definition=value&&typeof value==='object'&&!Array.isArray(value)?expected.get(value.name):null;
        const authority=definition?.ap?'192.168.4.1':'192.168.1.53';
        const allowed=new Set(['name','url','proxy','pid','driver_pid','authority','synthetic_password']);
        if(!definition||Object.keys(value).some(key=>!allowed.has(key))||('synthetic_password' in value&&typeof value.synthetic_password!=='string')||records.has(value.name)||value.pid!==child.pid||!Number.isSafeInteger(value.driver_pid)||value.driver_pid<=0||value.driver_pid===child.pid||value.authority!==authority||value.url!==`http://${authority}/`||value.proxy!==`http://127.0.0.1:${port+definition.index}`)throw Error('fixture identity, authority, driver, or port mismatch');
        records.set(value.name,value);
      }
    }catch(error){fail(Error(`stage=fixture-startup; invalid readiness; records=${records.size}; pending_bytes=${buffer.length}; stderr_bytes=${stderrBytes}`));}
  };
  const stderr=bytes=>{stderrBytes+=bytes.length;};
  const exited=(code,signal)=>{if(!stopRequested||code!==0||signal!==null)fail(Error(`stage=fixture-exit; child_exit=${code}; child_signal=${signal}; stderr_bytes=${stderrBytes}`));};
  const errored=error=>fail(Error('stage=fixture-spawn; '+error.message));
  const ended=()=>{if(!stopRequested)fail(Error(`stage=fixture-startup; stdout EOF; records=${records.size}; pending_bytes=${buffer.length}`));};
  const ready=deadline('fixture-startup',(resolve,reject)=>{resolveStartup=resolve;rejectStartup=reject;if(failure)reject(failure);return()=>{resolveStartup=null;rejectStartup=null;};},timeoutMs).catch(error=>{failure ||=error;throw error;});
  void ready.catch(()=>{}); // The owning caller still awaits the original rejecting promise.
  try{child=spawnImpl(process.execPath,[fileURLToPath(new URL('./ui_review_fixture.mjs',import.meta.url)),executable,String(port),output,...flags],{stdio:['ignore','pipe','pipe'],detached:processGroup});}catch(error){fail(error);throw error;}
  child.stdout.on('data',data);child.stderr.on('data',stderr);child.stdout.on('end',ended);child.on('exit',exited);child.on('error',errored);

  function stop(){
    if(stopping)return stopping;
    if(!started)fail(Error('stage=fixture-startup; cancelled by owner'));
    stopRequested=true;
    stopping=(async()=>{
      let cleanup;
      try{await cleanupUiProcesses([child],undefined,{processGroup,remove:async()=>{}});}catch(error){cleanup=error;}
      finally{child.stdout.removeListener('data',data);child.stdout.removeListener('end',ended);child.stderr.removeListener('data',stderr);child.removeListener('exit',exited);child.removeListener('error',errored);
        const failures=[];for(const stream of [child.stdout,child.stderr])try{stream.destroy();}catch(error){failures.push(error);}
        if(failures.length)cleanup=new AggregateError([...(cleanup?[cleanup]:[]),...failures],'fixture pipe cleanup failed');
      }
      if(failure&&cleanup)throw new AggregateError([failure,cleanup],'fixture operation and cleanup failed');
      if(failure||cleanup)throw failure||cleanup;
    })();return stopping;
  }
  return {process:child,ready,stop,records};
}
