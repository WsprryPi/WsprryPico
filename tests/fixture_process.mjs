// Owned JSON-line host fixture with bounded operations and shutdown.
import {spawn} from 'node:child_process';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';
import {deadlinePromise} from './browser_deadline.mjs';
export class FixtureProcess {
  constructor(executable,args=[],{timeoutMs=20000,cleanupMs=3000,deadline=deadlinePromise,processGroup=process.platform!=='win32'}={}) {
    this.deadline=deadline;this.timeoutMs=timeoutMs;this.cleanupMs=cleanupMs;this.queue=[];this.stderr='';this.stderrBytes=0;this.stdoutClosed=false;
    this.pending=Promise.resolve();this.failure=null;this.failureObserved=false;this.exitFailure=null;this.stopping=null;
    if(typeof processGroup!=='boolean')throw TypeError('Explicit fixture process-group policy required');
    this.processGroup=processGroup&&process.platform!=='win32';
    this.process=spawn(executable,args,{stdio:['pipe','pipe','pipe'],detached:this.processGroup});
    this.buffer=Buffer.alloc(0);
    this.process.stderr.on('data',bytes=>{this.stderrBytes+=bytes.length;this.stderr=`[fixture stderr withheld; bytes=${this.stderrBytes}]`;});
    const fail=error=>{this.failure ||= error;for(const next of this.queue.splice(0))next.reject(error);};
    this.fail=fail;
    this.process.stdout.on('data',bytes=>{
      this.buffer=Buffer.concat([this.buffer,bytes]);
      if(this.buffer.length>1024*1024){fail(Error('stage=fixture-reply; response exceeds byte bound'));void this.stop().catch(()=>{});return;}
      let end;
      while((end=this.buffer.indexOf(10))>=0){
        const raw=this.buffer.subarray(0,end);this.buffer=this.buffer.subarray(end+1);
        const next=this.queue.shift();
        if(!next){fail(Error('stage=fixture-reply; unexpected response without request'));void this.stop().catch(()=>{});return;}
        try{next.resolve(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw)));}catch(error){const failure=Error('stage=fixture-reply; malformed JSON/UTF-8 response; response_bytes='+raw.length);fail(failure);next.reject(failure);void this.stop().catch(()=>{});return;}
      }
    });
    this.process.stdout.on('end',()=>{this.stdoutClosed=true;if(!this.stopping||this.queue.length)fail(Error('stage=fixture-reply; stdout closed before response'));});
    this.process.once('error',error=>fail(Error('stage=fixture-spawn; '+error.message,{cause:error})));
    this.process.on('exit',(code,signal)=>{
      const error=Error(`stage=fixture-exit; child_exit=${code}; child_signal=${signal}; stderr_bytes=${this.stderrBytes}`);
      if(signal===null&&code!==0)this.exitFailure=error;
      if(!this.stopping||this.queue.length||this.exitFailure)fail(error);
    });
    this.process.stdin.on('error',error=>{if(!this.stopping||this.queue.length)fail(Error('stage=fixture-input; '+error.message,{cause:error}));});
  }
  command(value) {
    // Start the budget when enqueued, so serialization cannot hide an unbounded backlog.
    const operation=this.deadline('fixture-command',(resolve,reject)=>{
      let active=true,entry;
      const result=this.pending.then(()=>{
        if(!active)return;
        if(this.failure)throw this.failure;
        if(this.stdoutClosed||this.stopping||this.process.exitCode!==null||this.process.signalCode!==null)throw Error('stage=fixture-command; driver is closed');
        return new Promise((reply,fail)=>{entry={resolve:reply,reject:fail};this.queue.push(entry);this.process.stdin.write(JSON.stringify(value)+'\n');});
      });
      this.pending=result.catch(()=>{});
      result.then(resolve,reject);
      return()=>{active=false;if(entry){const index=this.queue.indexOf(entry);if(index>=0){this.queue.splice(index,1);const error=Error('stage=fixture-command; response deadline or cancellation');entry.reject(error);this.fail(error);void this.stop().catch(()=>{});}}};
    },this.timeoutMs);
    return operation.catch(error=>{this.fail(error);this.failureObserved=true;void this.stop().catch(()=>{});throw error;});
  }
  stop() {
    if(this.stopping)return this.stopping;
    this.stopping=(async()=>{
      let primary;const cleanupFailures=[];
      try {
        if(this.process.pid&&this.process.exitCode===null&&this.process.signalCode===null) {
          await new Promise(resolve=>{
            let done=false;
            const finish=()=>{if(done)return;done=true;clearTimeout(timer);this.process.removeListener('exit',finish);resolve();};
            const timer=setTimeout(finish,this.cleanupMs);
            this.process.once('exit',finish);
            try{this.process.stdin.end();}catch(error){primary=error;finish();}
            if(this.process.exitCode!==null||this.process.signalCode!==null)finish();
          });
        }
        if(this.process.pid)await cleanupUiProcesses([this.process],undefined,{timeoutMs:this.cleanupMs,processGroup:this.processGroup,remove:async()=>{}});
      }catch(error){cleanupFailures.push(error);}
      finally{
        for(const stream of [this.process.stdin,this.process.stdout,this.process.stderr]){
          try{stream.destroy();}catch(error){cleanupFailures.push(error);}
        }
      }
      if(cleanupFailures.length)throw new AggregateError([
        ...new Set([primary,this.failure,this.exitFailure].filter(Boolean)),...cleanupFailures
      ],'fixture operation and cleanup failed');
      if(primary)throw primary;
      // A command rejection has already propagated its primary failure. An idle
      // crash after the final successful reply has no such observer and must
      // fail finalization, including a nonzero exit during orderly EOF shutdown.
      if(this.exitFailure)throw this.failure&&this.failure!==this.exitFailure
        ?new AggregateError([this.failure,this.exitFailure],'fixture response and exit failed'):this.exitFailure;
      if(this.failure&&!this.failureObserved)throw this.failure;
    })();return this.stopping;
  }
}
