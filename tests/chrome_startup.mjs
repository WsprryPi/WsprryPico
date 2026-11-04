// Bounded startup for the isolated Chrome process used by browser fixtures.
import {spawn} from 'node:child_process';
import {readFile} from 'node:fs/promises';
import path from 'node:path';

// Match the other cold-start browser fixtures. Hosted runners can spend most
// of 20 seconds starting Chrome before its DevTools endpoint is available.
export function launchChrome(executable,args,profile,{timeoutMs=60000,processGroup=false}={}) {
  const started=performance.now();
  const timing={budgetMs:timeoutMs,firstStderrMs:null,endpointMs:null,probes:0};
  const diagnostic=()=>JSON.stringify({...timing,elapsedMs:Math.round(performance.now()-started)});
  const child=spawn(executable,args,{stdio:['ignore','ignore','pipe'],detached:processGroup});
  let stderr='',advertisedPort,spawnError;
  child.stderr?.on('data',bytes=>{
    timing.firstStderrMs ??= Math.round(performance.now()-started);
    stderr=(stderr+bytes.toString()).slice(-8192);
    const match=stderr.match(/DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)\//);
    if(match)advertisedPort=Number(match[1]);
  });
  child.on('error',error=>{spawnError=error;});
  function failure(reason,probe) {
    return Error(`${reason}; executable=${executable}; exit=${child.exitCode}; signal=${child.signalCode}; startup=${diagnostic()}`+
      (probe?`; last probe: ${probe}`:'')+(stderr?`\nChrome stderr (last 8192 characters):\n${stderr}`:''));
  }
  const ready=(async()=>{
    const deadline=Date.now()+timeoutMs;
    let probe;
    while(Date.now()<deadline) {
      if(spawnError)throw failure(`Chrome launch failed: ${spawnError.message}`);
      if(child.exitCode!==null || child.signalCode!==null)throw failure('Chrome exited before DevTools became ready',probe);
      let port=advertisedPort;
      if(!port) {
        try {port=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);}
        catch(error) {if(error.code!=='ENOENT')probe=error.message;}
      }
      if(Number.isInteger(port) && port>0 && port<=65535) {
        timing.endpointMs ??= Math.round(performance.now()-started);
        timing.probes++;
        try {
          const response=await fetch(`http://127.0.0.1:${port}/json`,{
            signal:AbortSignal.timeout(Math.max(1,Math.min(1000,deadline-Date.now())))
          });
          if(!response.ok)throw Error(`DevTools returned HTTP ${response.status}`);
          const pages=await response.json();
          if(!Array.isArray(pages) || !pages.some(page=>page.type==='page' &&
             typeof page.webSocketDebuggerUrl==='string' &&
             page.webSocketDebuggerUrl.startsWith(`ws://127.0.0.1:${port}/devtools/page/`)))
            throw Error('DevTools has no ready page target');
          return pages;
        } catch(error) {probe=error.message;}
      }
      await new Promise(resolve=>setTimeout(resolve,40));
    }
    throw failure('Timed out: Chrome startup',probe);
  })();
  return {process:child,ready,diagnostic};
}
