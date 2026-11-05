// Explicit resource ownership for standalone browser test entry points.
import {createDeadlineTools,preserveCleanup} from './browser_deadline.mjs';
const cleanupDeadline=createDeadlineTools().deadlinePromise;
export class BrowserScope {
  constructor({processImpl=process,cleanup=cleanupDeadline}={}) {
    this.process=processImpl;this.cleanup=cleanup;this.resources=[];this.closing=null;
    this.interruption=null;this.abort=new AbortController();this.signal=this.abort.signal;
    this.handlers=new Map(['SIGTERM','SIGINT'].map(name=>[name,()=>{
      this.interruption ||=Error('browser scope interrupted by '+name);
      this.abort.abort(this.interruption);
      void this.close(this.interruption).catch(()=>{this.process.exitCode=1;});
    }]));
    try{for(const [name,handler] of this.handlers)this.process.on(name,handler);}
    catch(primary){const errors=[];for(const [name,handler] of this.handlers)try{this.process.removeListener(name,handler);}catch(error){errors.push(error);}if(errors.length)throw new AggregateError([primary,...errors],'scope acquisition and rollback failed');throw primary;}
  }
  async own(resource,dispose) {
    if(typeof dispose!=='function')throw TypeError('Owned resource finalizer required');
    const record={value:Promise.resolve(resource),dispose,stopping:null};
    const finish=()=>{record.stopping ||= (async()=>{let value;try{value=await record.value;}catch{return;}await dispose(value);})();return record.stopping;};
    record.finish=finish;
    if(this.closing){
      const primary=this.interruption||Error('browser scope already closing');let value;
      try{value=await record.value;}catch(error){throw new AggregateError([primary,error],'late resource acquisition failed');}
      await preserveCleanup(primary,[()=>this.cleanup('late-browser-resource',(resolve,reject)=>{finish().then(resolve,reject);},20000)]);
      throw primary;
    }
    this.resources.push(record); // Includes pending acquisition, before first await.
    const value=await record.value;
    if(typeof this.process.send==='function'&&Number.isSafeInteger(value?.process?.pid)){
      await new Promise((resolve,reject)=>this.process.send({kind:'browser-owned-process/1',pid:value.process.pid,profile:typeof value.profile==='string'?value.profile:null},error=>error?reject(error):resolve()));
    }
    if(this.closing){await this.close(this.interruption);throw this.interruption||Error('browser scope already closing');}
    return value;
  }
  close(primary=this.interruption) {
    if(this.closing)return this.closing;
    const actions=this.resources.splice(0).reverse().map(record=>()=>
      this.cleanup('browser-resource-cleanup',(resolve,reject)=>{record.finish().then(resolve,reject);},20000));
    this.closing=(async()=>{await preserveCleanup(primary,actions);if(primary)throw primary;})();return this.closing;
  }
  async run(action) {
    let primary;
    try{const result=await action();if(this.interruption)throw this.interruption;return result;}
    catch(error){primary=error;throw error;}
    finally{
      await preserveCleanup(primary,[()=>this.close(),...[...this.handlers].map(([name,handler])=>()=>this.process.removeListener(name,handler))]);
    }
  }
}
