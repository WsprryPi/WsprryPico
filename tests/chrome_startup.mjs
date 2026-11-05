// Bounded startup for the isolated Chrome process used by browser fixtures.
import {spawn} from 'node:child_process';
import {open} from 'node:fs/promises';
import {constants} from 'node:fs';
import {deadlinePromise,remaining,preserveCleanup} from './browser_deadline.mjs';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';
import path from 'node:path';

async function discovery(profile) {
  let handle,primary;
  try{
    handle=await open(path.join(profile,'DevToolsActivePort'),constants.O_RDONLY|constants.O_NONBLOCK|(constants.O_NOFOLLOW||0));
    const stat=await handle.stat();
    if(!stat.isFile()||stat.size>4096)throw Error('Invalid Chrome discovery file type/size');
    const buffer=Buffer.alloc(4097),{bytesRead}=await handle.read(buffer,0,buffer.length,0);
    if(bytesRead>4096)throw Error('Oversized Chrome discovery record');
    const lines=new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,bytesRead)).split('\n');
    const valid=lines.length>=2&&/^[1-9][0-9]{0,4}$/.test(lines[0])&&lines[1].startsWith('/devtools/browser/');
    const port=valid?Number(lines[0]):null;
    return {port:port<=65535?port:null,incomplete:!port||port>65535,bytes:bytesRead};
  }catch(error){if(error.code==='ENOENT')return {port:null,incomplete:false};primary=error;throw error;}
  finally{await preserveCleanup(primary,[async()=>{await handle?.close();}]);}
}
class DiscoveryProtocolError extends Error {}
async function devtoolsPages(response) {
  if(!response.body)throw new DiscoveryProtocolError('DevTools discovery body is absent');
  // Startup precedes navigation in maintained callers; bounded initial page
  // metadata is distinct from screenshots and other potentially large CDP data.
  const reader=response.body.getReader(),chunks=[];let bytes=0,complete=false,primary;
  try{
    while(true){const part=await reader.read();if(part.done){complete=true;break;}bytes+=part.value.length;if(bytes>65536)throw new DiscoveryProtocolError('DevTools discovery metadata exceeds byte bound');chunks.push(part.value);}
    let value;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Buffer.concat(chunks)));}catch(error){throw new DiscoveryProtocolError('Malformed DevTools discovery JSON',{cause:error});}
    if(!Array.isArray(value)||value.some(item=>!item||typeof item!=='object'||Array.isArray(item)))throw new DiscoveryProtocolError('Malformed DevTools page inventory');
    return value;
  }catch(error){primary=error;throw error;}
  finally{await preserveCleanup(primary,[async()=>{if(!complete)await reader.cancel();},()=>reader.releaseLock()]);}
}
function bounded(label,action,budget) {
  return deadlinePromise(label,(resolve,reject)=>{
    const abort=new AbortController();Promise.resolve().then(()=>action(abort.signal)).then(resolve,reject);
    return()=>abort.abort();
  },budget);
}

// Match the other cold-start browser fixtures. Hosted runners can spend most
// of 20 seconds starting Chrome before its DevTools endpoint is available.
export function launchChrome(executable,args,profile,{timeoutMs=60000,processGroup=false,now=()=>performance.now()}={}) {
  if(!Number.isFinite(timeoutMs)||timeoutMs<=0)throw new RangeError("Chrome startup budget must be finite and positive");
  const enclosing=remaining(Infinity);timeoutMs=Math.min(timeoutMs,enclosing);
  const started=performance.now(),clockStarted=now();
  const timing={budgetMs:timeoutMs,watchdogMs:Math.min(Math.max(60000,timeoutMs),enclosing),firstStderrMs:null,endpointMs:null,probes:0,incompleteDiscoveryReads:0,lastDiscoveryBytes:null};
  const diagnostic=()=>JSON.stringify({...timing,elapsedMs:Math.round(performance.now()-started),deadlineElapsedMs:Math.round(now()-clockStarted)});
  const child=spawn(executable,args,{stdio:['ignore','ignore','pipe'],detached:processGroup});
  let stderr='',advertisedPort,spawnError,stopping,asynchronousFailure;
  const exited=(code,signal)=>{if(!stopping||(code!==null&&code!==0))asynchronousFailure ||=failure('Chrome exited unexpectedly');};
  child.on('exit',exited);
  child.stderr?.on('data',bytes=>{
    timing.firstStderrMs ??= Math.round(performance.now()-started);
    stderr=(stderr+bytes.toString()).slice(-8192);
    const match=stderr.match(/DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)\//);
    if(match)advertisedPort=Number(match[1]);
  });
  child.on('error',error=>{spawnError=error;});
  function failure(reason,probe) {
    const detail=probe instanceof Error?probe.message:probe;
    return Error(`${reason}; executable=${executable}; exit=${child.exitCode}; signal=${child.signalCode}; startup=${diagnostic()}`+
      (detail?`; last probe: ${detail}`:'')+(stderr?`\nChrome stderr (last 8192 characters):\n${stderr}`:''),probe instanceof Error?{cause:probe}:undefined);
  }
  const ready=(async()=>{
    // An injected logical clock lets fault tests expire only after establishing
    // the intended blocked state. A separate real watchdog always remains finite.
    const deadline=clockStarted+timeoutMs,watchdog=started+timing.watchdogMs;
    let probe;
    while(now()<deadline && performance.now()<watchdog) {
      if(spawnError)throw failure(`Chrome launch failed: ${spawnError.message}`);
      if(child.exitCode!==null || child.signalCode!==null)throw failure('Chrome exited before DevTools became ready',probe);
      let port=advertisedPort;
      if(!port) {
        try {
          const record=await bounded('Chrome discovery read',()=>discovery(profile),Math.min(1000,deadline-now(),watchdog-performance.now()));
          port=record.port;timing.lastDiscoveryBytes=record.bytes??null;if(record.incomplete)timing.incompleteDiscoveryReads++;
        }catch(error){throw failure('Chrome discovery failed',error);}

      }
      if(Number.isInteger(port) && port>0 && port<=65535) {
        timing.endpointMs ??= Math.round(performance.now()-started);
        timing.probes++;
        try {
          const pages=await bounded('Chrome DevTools discovery',async signal=>{
            const response=await fetch(`http://127.0.0.1:${port}/json`,{signal});
            if(!response.ok)throw Error(`DevTools returned HTTP ${response.status}`);
            return devtoolsPages(response);
          },Math.max(1,Math.min(1000,deadline-now(),watchdog-performance.now())));
          if(now()>=deadline||performance.now()>=watchdog)break;
          if(child.exitCode!==null||child.signalCode!==null)throw failure('Chrome exited before DevTools became ready');
          const eligible=Array.isArray(pages)?pages.filter(page=>page&&typeof page==='object'&&page.type==='page'&&
            typeof page.webSocketDebuggerUrl==='string'&&page.webSocketDebuggerUrl.startsWith(`ws://127.0.0.1:${port}/devtools/page/`)):[];
          if(!eligible.length)throw Error('DevTools has no ready page target');
          return eligible;

        } catch(error) {if(error instanceof DiscoveryProtocolError)throw failure('Invalid Chrome DevTools discovery',error);probe=error;}
      }
      const pause=Math.min(40,deadline-now(),watchdog-performance.now());
      if(pause>0){
        try{await deadlinePromise('Chrome discovery pacing',resolve=>{const timer=setTimeout(resolve,pause);return()=>clearTimeout(timer);},watchdog-performance.now());}
        catch(error){throw failure('Timed out: Chrome startup',error);}
      }
    }
    throw failure('Timed out: Chrome startup',probe);
  })();
  function stop(){
    if(stopping)return stopping;
    stopping=(async()=>{
      let cleanup;
      try{await cleanupUiProcesses([child],profile,{processGroup});}catch(error){cleanup=error;}
      finally{child.removeListener('exit',exited);}
      if(asynchronousFailure&&cleanup)throw new AggregateError([asynchronousFailure,cleanup],'Chrome operation and cleanup failed');
      if(asynchronousFailure||cleanup)throw asynchronousFailure||cleanup;
    })();return stopping;
  }
  return {process:child,ready,diagnostic,stop,profile};
}
