// Shipped page/bundle -> real browser -> production HTTP/crypto/commissioning.
// Only TCP/board/time boundaries use the existing deterministic fixture.
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {Fixture} from './consumer_sessions.test.mjs';

if (!globalThis.WebSocket) throw new Error('Use Node with built-in WebSocket; Node 20 needs --experimental-websocket');
const output=path.resolve(process.argv[3] || 'build/progress-browser-reproduction');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'p158-chrome-'));
let f=new Fixture(process.argv[2]);await f.time(1000);
let old=false, chrome, cdp; const requests=[];
const proxy=http.createServer(async(req,res)=>{
    try {
        const u=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
        if(!['192.168.1.53','192.168.4.1'].includes(u.hostname)){res.writeHead(403);res.end();return;}
        if(old && ['/api/v1/application/2','/api/owner/v1/wspr-support'].includes(u.pathname)){
            res.writeHead(404,{'Content-Type':'application/json'});res.end('{"error":{"code":"not_found"}}');return;
        }
        const chunks=[];for await(const b of req)chunks.push(b);
        if(u.pathname.endsWith('/start'))await f.time(f.now+1000);
        const response=await f.fetch(u.hostname,u.hostname==='192.168.4.1',u.pathname,
            {method:req.method,body:Buffer.concat(chunks),headers:{'Content-Type':req.headers['content-type']||'application/json'},
                marker:u.pathname.startsWith('/api/owner/')?'Owner':u.pathname.startsWith('/api/bootstrap/')?'Bootstrap':'Radio'});
        const socket=f.socket;
        let bytes=Buffer.from(await response.arrayBuffer());
        const expected=Number(response.headers.get('content-length'));
        // Explicit TCP-ACK pumping of the existing bounded 100-step fixture, without
        // increasing a production/test deadline or accepting an incomplete response.
        for(let pump=0;bytes.length<expected && pump<4;++pump){
            await f.command({op:'complete',socket});
            const snapshot=await f.command({op:'wire',socket});
            const wire=Buffer.from(snapshot.wire,'hex');bytes=wire.subarray(wire.indexOf('\r\n\r\n')+4);
        }
        assert.equal(bytes.length,expected,'complete production HTTP response');
        requests.push({path:u.pathname,status:response.status,bytes:bytes.length});
        if(u.pathname === "/") await writeFile(path.join(output,"root.html"),bytes);
        res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
    }catch(error){res.writeHead(500,{'Content-Type':'text/plain'});res.end(error.message);}
});
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const port=proxy.address().port;
class Cdp {
    constructor(url){this.ws=new WebSocket(url);this.sequence=0;this.pending=new Map();this.ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&this.pending.has(m.id)){const p=this.pending.get(m.id);this.pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}};}
    async open(){if(this.ws.readyState===1)return;await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
    send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{this.pending.set(id,{resolve,reject});this.ws.send(JSON.stringify({id,method,params}));});}
    async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=10000){const end=Date.now()+ms;let last;while(Date.now()<end){try{const r=await fn();if(r)return r;}catch(e){last=e;}await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+label+(last?' '+last.message:''));}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
async function click(id){await cdp.evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);}
async function capture(name){
    for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
        await cdp.evaluate(`document.getElementById(${JSON.stringify(name.startsWith('old-')?'notice':'consumer-station-form')}).scrollIntoView({block:'start'})`);
        assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
        const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        await writeFile(path.join(output,`${name}-${view.name}-${theme}.png`),Buffer.from(image.data,'base64'));
    }
}
try {
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
            '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','http://192.168.1.53/'],{stdio:'ignore'});
    const debugPort=await until(async()=>Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome startup',60000);
    const page=await until(async()=>(await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(p=>p.type==='page'),'page');
    cdp=new Cdp(page.webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
    await until(()=>cdp.evaluate(`typeof radio !== 'undefined' && !!document.getElementById('local-password')`),'shipped radio page');
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate(`localAuthenticated && !busy`),'actual browser login');
    await click('read-saved');
    await until(()=>cdp.evaluate(`applicationVersion===2 && writeState==='review' && !busy`),'versioned saved-state readback');
    await click('review-saved');
    await until(()=>cdp.evaluate(`writeState==='ready' && !busy && !document.getElementById('consumer-station-settings').disabled`),'review enables editing');
    await field('consumer-callsign','AA0NT/12');
    await field('consumer-locator','');
    await field('message-text','');
    const before=await f.command({op:'stats'});
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-locator').validity.valueMissing`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-station-form').checkValidity()`),false);
    const after=await f.command({op:'stats'});
    assert.equal(after.profile_programs,before.profile_programs);
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'');
    await capture('callsign-only-blocked');
    console.log(JSON.stringify({native_locator_required:true,blank_qrss:true,separate_forms:true,profile_mutations:after.profile_programs-before.profile_programs}));
} finally {
    cdp?.ws.close();chrome?.kill();proxy.close();await f.stop();
}
