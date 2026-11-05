// Shared ownership adapters; importing this module does not run a browser suite.
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {BrowserScope} from './browser_scope.mjs';
import {Cdp} from './browser_cdp.mjs';
import {Fixture} from './consumer_sessions.test.mjs';
import {launchChrome} from './chrome_startup.mjs';
import {qualifyNativeChildren} from './ui_fixture_inventory.mjs';
import {launchUiFixture} from './ui_fixture_process.mjs';
import {deadlinePromise,preserveCleanup} from './browser_deadline.mjs';
export {until} from './browser_deadline.mjs';

export class BrowserHarness extends BrowserScope {
  profiles=new Map();
  async profile(prefix='pico-browser-') {
    return this.own(mkdtemp(path.join(os.tmpdir(),prefix)),async value=>{
      // launchChrome.stop owns removal once a writer exists, including failure.
      if(!this.profiles.has(value))await rm(value,{recursive:true,force:true});
    },{priority:-20});
  }
  fixture(...args){return this.own(new Fixture(...args),value=>value.stop(),{priority:-10});}
  async review(driver,port,output,options){
    const server=await this.own(launchUiFixture(driver,port,output,{processGroup:process.platform!=='win32',...options}),value=>value.stop());
    const records=await server.ready;
    await qualifyNativeChildren(driver,server.process.pid,records);
    console.log(JSON.stringify({kind:'native-fixture-inventory/1',owner:server.process.pid,count:records.length,profiles:records.map(value=>value.name)}));
    return server;
  }
  async chrome(executable,args,profile) {
    if(this.profiles.has(profile))throw Error('Browser profile reuse refused; acquire a fresh private profile');
    const browser=launchChrome(executable,args,profile,{processGroup:process.platform!=='win32'});
    this.profiles.set(profile,browser);
    await this.own(browser,value=>value.stop());
    const pages=await browser.ready;return {browser,pages};
  }
  async connect(url,{dialogs=false}={}) {
    const cdp=await this.own(new Cdp(url),value=>value.stop());
    if(dialogs)cdp.on('Page.javascriptDialogOpening',(_params,session)=>cdp.send('Page.handleJavaScriptDialog',{accept:true},session));
    await cdp.open();return cdp;
  }
  async server(server,drain=()=>Promise.resolve()) {
    return this.own(server,async value=>{
      await preserveCleanup(null,[()=>value.closeAllConnections(),()=>deadlinePromise('fixture-http-close',(resolve,reject)=>{value.close(error=>error&&error.code!=='ERR_SERVER_NOT_RUNNING'?reject(error):resolve());},3000),()=>deadlinePromise('fixture-http-drain',(resolve,reject)=>{Promise.resolve().then(drain).then(resolve,reject);},20000)]);
    },{priority:-5});
  }
  listen(server) {
    return deadlinePromise('fixture-http-listen',(resolve,reject)=>{
      server.once('error',reject);server.listen(0,'127.0.0.1',resolve);
      return()=>server.removeListener('error',reject);
    });
  }
}
export async function fixtureJson(url,options={}) {
  return deadlinePromise('fixture-http-control',(resolve,reject)=>{
    const abort=new AbortController();
    const interrupted=()=>abort.abort(options.signal.reason);
    options.signal?.addEventListener('abort',interrupted,{once:true});
    if(options.signal?.aborted)interrupted();
    void(async()=>{
      const response=await fetch(url,{...options,signal:abort.signal});
      if(response.status!==200)throw Error('Fixture HTTP status '+response.status);
      const reader=response.body.getReader();let size=0,complete=false,primary;
      try{
        const chunks=[];while(true){const part=await reader.read();if(part.done){complete=true;break;}size+=part.value.length;if(size>65536)throw Error('Fixture JSON body exceeds bound');chunks.push(part.value);}
        return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Buffer.concat(chunks)));
      }catch(error){primary=error;throw error;}finally{await preserveCleanup(primary,[async()=>{if(!complete)await reader.cancel();},()=>reader.releaseLock()]);}
    })().then(resolve,reject);
    return()=>{options.signal?.removeEventListener('abort',interrupted);abort.abort();};
  },15000);
}

// Only these documented cross-document CDP states are retryable during navigation.
export function navigationTransient(error) {
  if(error.code===-32000&&['Cannot find context with specified id','Execution context was destroyed.'].includes(error.protocolMessage))return false;
  throw error;
}
