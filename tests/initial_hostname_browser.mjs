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
  const server=http.createServer((req,res)=>{queue=queue.then(async()=>{
    try {
      const url=new URL(req.url.startsWith('http:')?req.url:'http://192.168.4.1'+req.url);
      if(url.hostname!=='192.168.4.1'){res.writeHead(403);res.end();return;}
      const chunks=[];for await(const chunk of req)chunks.push(chunk);
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
  for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name==='mobile'});
    await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false);
    const capture=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
    await writeFile(path.join(output,`initial-${view.name}-${theme}.png`),Buffer.from(capture.data,'base64'));
  }
  async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
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
  await cdp.evaluate(`document.getElementById('wifi-form').requestSubmit()`);
  await until(()=>cdp.evaluate(`document.getElementById('notice').textContent==='Wi-Fi saved and connected.'`),'network and hostname saved');
  assert.equal(submits,1);
  assert.equal(await cdp.evaluate(`document.getElementById('setup-hostname').textContent`),'picoc.local');
  await f.command({op:'reboot'});await f.time(f.now+1000);
  const client=f.client('192.168.4.1',true);await f.login(client);
  const hostname=await(await client.request('hostname')).json();
  assert.equal(hostname.active,'picoc.local');assert.equal(hostname.saved,'picoc.local');
  console.log('PASS initial hostname field, mobile/desktop light/dark, invalid refusal, canonical save, and reboot readback');
});
