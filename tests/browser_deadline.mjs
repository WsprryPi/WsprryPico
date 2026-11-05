// Test-only monotonic stage budgets; no firmware or operator policy controls.
import {AsyncLocalStorage} from 'node:async_hooks';
import {performance} from 'node:perf_hooks';
export function createDeadlineTools({clock=()=>performance.now(),setTimer=setTimeout,clearTimer=clearTimeout}={}) {
  const current=new AsyncLocalStorage();
  function remaining(limit=20000) {
    const parent=current.getStore();
    if(parent?.error)throw parent.error;
    const value=Math.min(limit,parent?parent.expires-clock():limit);
    if(value<=0)throw Error(`stage=${parent?.label||'operation'}; expected=completion before stage deadline`);
    return value;
  }
  function deadlinePromise(label,executor,limit=20000) {
    const budget=remaining(limit),started=clock();
    return new Promise((resolve,reject)=>{
      let done=false,dispose,acquired=false,pending;
      const finish=(error,value)=>{
        if(done)return;
        if(!acquired){pending ||= [error,value];return;}
        done=true;
        if(!error&&clock()-started>=budget)error=Error(`stage=${label}; expected=completion before stage deadline; elapsed=${clock()-started}ms; hang_guard=${budget}ms`);
        const failures=[];
        try{clearTimer(timer);}catch(cleanup){failures.push(cleanup);}
        try{if(typeof dispose==='function')dispose();}catch(cleanup){failures.push(cleanup);}
        if(failures.length)error=new AggregateError(error?[error,...failures]:failures,'operation and cleanup failed');
        error?reject(error):resolve(value);
      };
      const timer=setTimer(()=>finish(Error(`stage=${label}; expected=completion; last_transition=pending; elapsed=${clock()-started}ms; hang_guard=${budget}ms`)),budget);
      try{dispose=executor(value=>finish(null,value),error=>finish(error||Error(`stage=${label}; operation rejected without diagnostic`)),budget);}
      catch(error){error ||= Error(`stage=${label}; operation rejected without diagnostic`);pending=[pending?.[0]?new AggregateError([pending[0],error],'operation and acquisition failed'):error];}
      acquired=true;if(pending)finish(...pending);

    });
  }
  async function stage(action,label,limit) {
    const context={label,expires:clock()+remaining(limit)};
    return current.run(context,async()=>{
      try{return await deadlinePromise(label,(resolve,reject)=>{Promise.resolve().then(action).then(resolve,reject);},limit);}
      catch(error){context.error=error;throw error;}
    });
  }
  async function until(fn,label,limit=20000,{retryErrors=false}={}) {
    let last;
    try{return await stage(async()=>{
      while(true){
        let value;
        try{value=await fn();}catch(error){if(!retryErrors)throw error;last=error;}
        remaining(); // A late successful inner operation cannot qualify this stage.
        if(value)return value;
        await deadlinePromise(label,resolve=>{const timer=setTimeout(resolve,Math.min(40,remaining()));return()=>clearTimer(timer);});
      }
    },label,limit);}catch(error){if(last)error.message+=`; last_error=${last.message}`;throw error;}
  }
  return {remaining,deadlinePromise,until};
}
export const {remaining,deadlinePromise,until}=createDeadlineTools();
export async function preserveCleanup(primary,actions) {
  const failures=[];
  for(const action of actions)try{await action();}catch(error){failures.push(error);}
  if(failures.length)throw new AggregateError(primary?[primary,...failures]:failures,'fixture operation and cleanup failed');
}
