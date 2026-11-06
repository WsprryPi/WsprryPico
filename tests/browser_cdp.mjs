// Pure CDP transport for owned test browsers. Importing it launches no suite.
import {deadlinePromise,createDeadlineTools} from './browser_deadline.mjs';
const cleanupDeadline=createDeadlineTools().deadlinePromise;

export class Cdp {
  constructor(url,{WebSocketImpl=globalThis.WebSocket,deadline=deadlinePromise,cleanup=cleanupDeadline,timeoutMs=15000}={}) {
    if(!Number.isFinite(timeoutMs)||timeoutMs<=0)throw RangeError('Finite positive CDP watchdog required');
    const target=new URL(url);
    if(target.protocol!=='ws:'||target.hostname!=='127.0.0.1'||!target.port||!target.pathname.startsWith('/devtools/'))throw TypeError('Owned loopback DevTools socket required');
    this.deadline=deadline;this.cleanupDeadline=cleanup;this.timeoutMs=timeoutMs;this.sequence=0;this.pending=new Map();
    this.eventWork=new Set();this.eventHandlers=new Map();this.abandoned=new Set();this.failure=null;this.observedFailure=false;this.stopping=null;
    this.ws=new WebSocketImpl(url);
    this.fail=error=>{this.failure ||=error;for(const entry of this.pending.values())entry.reject(this.failure);this.pending.clear();};
    this.onClose=()=>{if(!this.stopping)this.fail(Error('stage=browser-socket; unexpected close'));};
    this.onError=()=>this.fail(Error('stage=browser-socket; transport error'));
    this.onMessage=event=>{
      try {
        const value=JSON.parse(event.data);
        if(!value||typeof value!=='object'||Array.isArray(value))throw Error('invalid envelope');
        if(value.id===undefined){if(typeof value.method!=='string'||!value.method||('params' in value&&(!value.params||typeof value.params!=='object'||Array.isArray(value.params))))throw Error('invalid event');for(const handler of this.eventHandlers.get(value.method)||[]){const work=Promise.resolve().then(()=>handler(value.params||{},value.sessionId)).catch(this.fail);this.eventWork.add(work);void work.finally(()=>this.eventWork.delete(work));}return;}
        if(!Number.isSafeInteger(value.id)||value.id<=0)throw Error('invalid correlation');
        const entry=this.pending.get(value.id);
        if(!entry){if(this.abandoned.delete(value.id))return;throw Error('unexpected response correlation');}
        if(value.sessionId!==entry.sessionId)throw Error('session correlation mismatch');
        if((Object.hasOwn(value,'result')?1:0)+(Object.hasOwn(value,'error')?1:0)!==1)throw Error('invalid response outcome');
        if(Object.hasOwn(value,'error')&&(!value.error||typeof value.error!=='object'||!Number.isSafeInteger(value.error.code)||typeof value.error.message!=='string'))throw Error('invalid protocol error');
        if(Object.hasOwn(value,'result')&&(!value.result||typeof value.result!=='object'||Array.isArray(value.result)))throw Error('invalid response result');
        this.pending.delete(value.id);
        value.error?entry.reject(Object.assign(Error(`stage=CDP ${entry.method}; ${value.error.message}`),{code:value.error.code,protocolMessage:value.error.message})):entry.resolve(value.result);
      }catch(error){this.fail(Error('stage=browser-socket; malformed or uncorrelated CDP response'));}
    };
    this.ws.addEventListener('close',this.onClose);this.ws.addEventListener('error',this.onError);
    this.ws.addEventListener('message',this.onMessage);
  }
  async observed(action) {
    try{return await action();}catch(error){if(error===this.failure)this.observedFailure=true;throw error;}
  }
  open() {return this.observed(async()=>{
    if(this.failure)throw this.failure;
    if(this.ws.readyState===1)return;
    await this.deadline('browser-socket-open',(resolve,reject)=>{
      const opened=()=>resolve(),failed=()=>reject(this.failure||Error('stage=browser-socket; closed before open'));
      this.ws.addEventListener('open',opened);this.ws.addEventListener('error',failed);this.ws.addEventListener('close',failed);
      if(this.ws.readyState===1)resolve();else if(this.ws.readyState>1)failed();
      return()=>{this.ws.removeEventListener('open',opened);this.ws.removeEventListener('error',failed);this.ws.removeEventListener('close',failed);};
    },this.timeoutMs);
  });}
  on(method,handler){if(typeof method!=='string'||typeof handler!=='function')throw TypeError('CDP event handler required');const set=this.eventHandlers.get(method)||new Set();set.add(handler);this.eventHandlers.set(method,set);return()=>{set.delete(handler);if(!set.size)this.eventHandlers.delete(method);};}
  send(method,params={},sessionId) {return this.observed(async()=>{
    if(this.failure)throw this.failure;
    if(this.stopping||this.ws.readyState!==1)throw Error('stage=browser-socket; request requires an open owned socket');
    if(typeof method!=='string'||!method||!params||typeof params!=='object'||Array.isArray(params))throw TypeError('Invalid CDP request');
    if(sessionId!==undefined&&(typeof sessionId!=='string'||!sessionId))throw TypeError('Explicit session identifier required');
    const id=++this.sequence;
    return this.deadline('CDP '+method,(resolve,reject)=>{
      this.pending.set(id,{resolve,reject,method,sessionId});
      try{this.ws.send(JSON.stringify({id,method,params,sessionId}));}catch(error){this.pending.delete(id);throw error;}
      return()=>{if(this.pending.delete(id)){this.abandoned.add(id);if(this.abandoned.size>1024)this.fail(Error('stage=browser-socket; cancelled request bound exceeded'));}};
    },this.timeoutMs);
  });}
  async evaluate(expression) {
    const result=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
    if(result.exceptionDetails)throw Error('stage=browser-evaluate; '+(result.exceptionDetails.exception?.description||result.exceptionDetails.text||'JavaScript exception'));
    if(!result.result||typeof result.result!=='object')throw Error('stage=browser-evaluate; missing remote result');
    return result.result.value;
  }
  stop() {
    if(this.stopping)return this.stopping;
    let resolveStop,rejectStop;
    this.stopping=new Promise((resolve,reject)=>{resolveStop=resolve;rejectStop=reject;});
    let primary=this.failure&&!this.observedFailure?this.failure:null;
    const cancelled=Error('stage=browser-socket; owner closed pending request');
    for(const entry of this.pending.values())entry.reject(cancelled);this.pending.clear();
    void (async()=>{
      let cleanup;
      try{if(this.eventWork.size)await this.cleanupDeadline('browser-event-drain',(resolve,reject)=>{Promise.all([...this.eventWork]).then(resolve,reject);},3000);}catch(error){cleanup=error;}
      primary ||= this.failure&&!this.observedFailure?this.failure:null;
      try{await this.cleanupDeadline('browser-socket-close',(resolve,reject)=>{
        const closed=()=>resolve();this.ws.addEventListener('close',closed);
        try{if(this.ws.readyState===3)resolve();else this.ws.close();}catch(error){reject(error);}
        return()=>this.ws.removeEventListener('close',closed);
      },3000);}catch(error){cleanup=cleanup?new AggregateError([cleanup,error],'event and socket cleanup failed'):error;}
      finally{this.ws.removeEventListener('close',this.onClose);this.ws.removeEventListener('error',this.onError);this.ws.removeEventListener('message',this.onMessage);this.abandoned.clear();this.eventHandlers.clear();}
      if(primary&&cleanup)throw new AggregateError([primary,cleanup],'browser operation and socket cleanup failed');
      if(primary||cleanup)throw primary||cleanup;
    })().then(resolveStop,rejectStop);
    return this.stopping;
  }
}
