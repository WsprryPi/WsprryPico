// Shipped initial form, browser crypto, production bootstrap handlers, and journals.
import assert from 'node:assert/strict';
import http from 'node:http';
import path from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
import {BrowserHarness,until} from './browser_harness.mjs';
import {fixtureHttpBody} from './fixture_http_body.mjs';
const h=new BrowserHarness();
await h.run(async()=>{
  const output=path.resolve(process.argv[3] || 'build/initial-hostname-browser');
  await mkdir(output,{recursive:true});
  const f=await h.fixture(process.argv[2],['1'.repeat(32),'--blank']);await f.time(1000);
  let queue=Promise.resolve(),submitted=false,submits=0;
  const mutations=[];
  const server=http.createServer((req,res)=>{queue=queue.then(async()=>{
    try {
      const url=new URL(req.url.startsWith('http:')?req.url:'http://192.168.4.1'+req.url);
      if(url.hostname!=='192.168.4.1'){res.writeHead(403);res.end();return;}
      const chunks=[];for await(const chunk of req)chunks.push(chunk);
      if(req.method==='POST' && !url.pathname.endsWith('/time'))mutations.push(url.pathname);
      if(submitted&&url.pathname==='/api/bootstrap/v1/status')await f.time(f.now+2000);
      const response=await f.fetch(url.hostname,true,url.pathname,{method:req.method,body:Buffer.concat(chunks),
        headers:{'Content-Type':req.headers['content-type']||'application/json'},marker:'Bootstrap'});
      const bytes=await fixtureHttpBody(f,response);
      if(url.pathname==='/api/bootstrap/v1/submit'){submitted=true;++submits;}
      res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
    }catch(error){res.writeHead(500);res.end(error.message);}
  });});
  await h.server(server,()=>queue);await h.listen(server);
  const profile=await h.profile('initial-hostname-');
  const started=await h.chrome(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
    '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
    '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${server.address().port}`,
    '--proxy-bypass-list=<-loopback>','about:blank'],profile);
  const cdp=await h.connect(started.pages[0].webSocketDebuggerUrl,{dialogs:true});await cdp.send('Page.enable');
  await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
  await until(()=>cdp.evaluate(`!!document.getElementById('hostname') && !document.getElementById('submit').disabled`),'initial form ready');
  const presentation=await(await f.fetch('192.168.4.1',true,'/api/presentation/v1')).json();
  assert.equal(await cdp.evaluate(`document.getElementById('hostname').disabled`),false);
  assert.equal(await cdp.evaluate(`document.getElementById('hostname').value`),presentation.hostname.slice(0,-6));
  assert.equal(await cdp.evaluate(`document.getElementById('hostname').hasAttribute('placeholder')`),false);
  assert.equal(await cdp.evaluate(`document.querySelector('label[for="hostname"]').textContent`),'Hostname');
  await cdp.evaluate(`globalThis.nativeCopyEvents=0;document.addEventListener('copy',()=>++nativeCopyEvents)`);
  async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
  async function copy() {
    await cdp.evaluate(`document.getElementById('copy-setup-link').focus()`);
    await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',windowsVirtualKeyCode:13});
    await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
  }
  await until(()=>cdp.evaluate(`!document.getElementById('copy-setup-link').disabled`),'copy ready');
  assert.equal(await cdp.evaluate('isSecureContext'),false,'test the actual HTTP AP origin');
  assert.equal(await cdp.evaluate(`document.getElementById('setup-url').value`),'http://'+presentation.hostname+'/');
  await copy();
  await until(()=>cdp.evaluate(`document.getElementById('setup-copy-status').textContent==='Link copied'`),'native HTTP copy');
  // A browser edit command pastes through the system clipboard without granting
  // this insecure page Clipboard API privileges or replacing its native copy.
  await cdp.evaluate(`{const e=document.createElement('textarea');e.id='clipboard-paste-probe';document.body.append(e);e.focus();}`);
  await cdp.send('Input.dispatchKeyEvent',{type:'rawKeyDown',key:'v',code:'KeyV',commands:['Paste']});
  await until(()=>cdp.evaluate(`document.getElementById('clipboard-paste-probe').value===${JSON.stringify('http://'+presentation.hostname+'/')}`),'exact native clipboard contents');
  await cdp.evaluate(`document.getElementById('clipboard-paste-probe').remove()`);
  assert.deepEqual(mutations,[],'copy is not a setup mutation or form submission');
  await field('hostname','x'.repeat(63));
  async function capture(state) {
    for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
      await cdp.send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name==='mobile'});
      await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
      assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false);
      const capture=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(path.join(output,`${state}-${view.name}-${theme}.png`),Buffer.from(capture.data,'base64'));
    }
  }
  await capture('initial');
  await cdp.evaluate(`globalThis.nativeCopy=document.execCommand;document.execCommand=()=>false`);
  await copy();
  assert.match(await cdp.evaluate(`document.getElementById('setup-copy-status').textContent`),/Could not copy/);
  assert.equal(await cdp.evaluate(`document.activeElement.id`),'setup-url');
  assert.equal(await cdp.evaluate(`document.getElementById('setup-url').selectionEnd`),77);
  await cdp.evaluate(`document.execCommand=nativeCopy`);
  await field('ssid','Home Wi-Fi');await field('password','test-password');await field('hostname','bad_name.local');
  await cdp.evaluate(`document.getElementById('wifi-form').requestSubmit()`);
  await until(()=>cdp.evaluate(`document.getElementById('hostname').getAttribute('aria-invalid')==='true'`),'hostname error');
  assert.equal(submits,0);
  for(const invalid of ['picoc.local','picoc.','.picoc','a.b','K','x'.repeat(64),'-bad']){
    await field('hostname',invalid);
    await cdp.evaluate(`document.getElementById('wifi-form').dispatchEvent(new Event('submit',{cancelable:true}))`);
    await until(()=>cdp.evaluate(`document.getElementById('hostname').getAttribute('aria-invalid')==='true'`),'invalid hostname refused');
    assert.equal(submits,0);
  }
  await field('hostname','PicoC');
  assert.equal(await cdp.evaluate(`document.getElementById('setup-url').value`),'http://picoc.local/');
  // Hold only browser delivery after the actual ACK request/response. All
  // handlers and journal effects remain production; no server queue is held.
  await cdp.evaluate(`globalThis.actualFetch=fetch.bind(globalThis);globalThis.releaseAck=undefined;fetch=async(...args)=>{const response=await actualFetch(...args);if(String(args[0]).endsWith('/api/bootstrap/v1/ack'))await new Promise(resolve=>globalThis.releaseAck=resolve);return response;}`);
  await cdp.evaluate(`document.getElementById('wifi-form').requestSubmit()`);
  await until(()=>cdp.evaluate(`document.getElementById('notice').textContent==='Wi-Fi saved and connected.'`),'network and hostname saved');
  assert.equal(submits,1);
  assert.equal(await cdp.evaluate(`document.getElementById('setup-hostname').textContent`),'picoc.local');
  assert.match(await cdp.evaluate(`document.getElementById('setup-link-state').textContent`),/^Saved/);
  await until(()=>cdp.evaluate(`typeof releaseAck==='function'`),'background ACK response');
  await until(()=>cdp.evaluate(`!document.getElementById('submission-busy')?.open`),'setup modal released');
  const beforeBackgroundCopy=mutations.length;
  const backgroundCopies=await cdp.evaluate('nativeCopyEvents');
  await copy();
  assert.equal(await cdp.evaluate('nativeCopyEvents'),backgroundCopies+1,'background ACK cannot block local copy');
  assert.equal(await cdp.evaluate(`document.getElementById('setup-copy-status').textContent`),'Link copied');
  assert.equal(mutations.length,beforeBackgroundCopy);
  await cdp.evaluate(`releaseAck();fetch=actualFetch`);
  await capture('saved');
  // Rendering and copying need no network after the verified result is present.
  await cdp.send('Network.enable');await cdp.send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:-1,uploadThroughput:-1});
  const beforeOffline=mutations.length;
  const offlineCopies=await cdp.evaluate('nativeCopyEvents');
  await copy();
  assert.equal(await cdp.evaluate('nativeCopyEvents'),offlineCopies+1,'offline copy executes rather than retaining prior feedback');
  await until(()=>cdp.evaluate(`document.getElementById('setup-copy-status').textContent==='Link copied'`),'offline result copy');
  assert.equal(mutations.length,beforeOffline);
  await cdp.evaluate(`document.getElementById('change-connected').click()`);
  await field('hostname','');
  assert.equal(await cdp.evaluate(`document.getElementById('setup-url').value`),'http://picoc.local/','returning to edit retains the verified saved hostname');
  assert.equal(mutations.length,beforeOffline,'returning to edit and clearing a draft do not save');
  await f.command({op:'reboot'});await f.time(f.now+1000);
  const client=f.client('192.168.4.1',true);await f.login(client);
  const hostname=await(await client.request('hostname')).json();
  assert.equal(hostname.active,'picoc.local');assert.equal(hostname.saved,'picoc.local');
  console.log('PASS HTTP AP native keyboard copy and exact pasted URL, manual fallback, offline result copy, mobile/desktop light/dark maximum name, invalid refusal, canonical save, and reboot readback');
});
