// Shipped AP page and production HTTP/AEAD; synthetic board and delayed transport.
import assert from 'node:assert/strict';
import path from 'node:path';
import {writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {BrowserHarness,until,fixtureJson} from './browser_harness.mjs';

export async function checkApUnlock(driver,output) {
if(!driver) throw Error('Usage: node tests/ap_unlock_browser.mjs DRIVER [OUTPUT]');
const h=new BrowserHarness();
await h.run(async()=>{
  await h.review(driver,19249,output,{profiles:['consumer-ap']});
  const profile=await h.profile('pico-ap-unlock-');
  const chrome=await h.chrome(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
    '--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
    '--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:19253',
    '--proxy-bypass-list=<-loopback>','about:blank'],profile);
  const cdp=await h.connect(chrome.pages[0].webSocketDebuggerUrl);
  const evaluate=value=>cdp.evaluate(value);
  await cdp.send('Page.enable');
  await fixtureJson('http://127.0.0.1:19253/.fixture-control',{method:'POST',body:JSON.stringify({op:'field_clock'})});
  await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
  await until(()=>evaluate('typeof busy!=="undefined" && !!localIdentity && !busy'),'AP landing ready');
  assert.equal(await evaluate('location.pathname'),'/wifi-host');
  assert.equal(await evaluate('radio.authenticated'),false);
  // Delay the first encrypted time reply after the server has accepted it.
  // Respect the production AbortSignal, reproducing sequence uncertainty on
  // expiry instead of returning a canned application response or retrying it.
  await evaluate(`(()=>{
    const request=radio.request.bind(radio),fetcher=radio.fetcher;
    let timeRead=false;
    globalThis.delayedFieldTime=false;
    globalThis.fieldTimeReads=0;
    radio.request=async (path,...args)=>{
      timeRead=path==='consumer/time';
      if(timeRead) ++globalThis.fieldTimeReads;
      try { return await request(path,...args); }
      finally { timeRead=false; }
    };
    radio.fetcher=async (path,options)=>{
      const response=await fetcher(path,options);
      if(timeRead && !globalThis.delayedFieldTime) {
        globalThis.delayedFieldTime=true;
        await new Promise((resolve,reject)=>{
          const abort=()=>{clearTimeout(timer);reject(new DOMException('Fetch aborted','AbortError'));};
          const timer=setTimeout(()=>{options.signal.removeEventListener('abort',abort);resolve();},5000);
          if(options.signal.aborted) abort();
          else options.signal.addEventListener('abort',abort,{once:true});
        });
      }
      return response;
    };
    document.getElementById('access-toggle').click();
  })()`);
  await until(()=>evaluate(`!busy && !submissions.pending && !accessLoginPending &&
    !document.getElementById('login-submit').matches(':disabled') &&
    (document.getElementById('local-password').value='test-password',
    document.getElementById('local-login').requestSubmit(),true)`),'single explicit password submission');
  await until(()=>evaluate('!busy && !accessLoginPending'),'post-login reads finished');
  assert.equal(await evaluate('delayedFieldTime'),true,'exercise a real post-login time read');
  assert.equal(await evaluate('localAuthenticated && radio.authenticated'),true,'slow AP time read preserves the confirmed login');
  assert.equal(await evaluate('fieldTimeReads'),1,'no automatic replay of the delayed encrypted request');
  assert.equal(await evaluate('document.getElementById("local-access").open'),false);
  assert.match(await evaluate('document.getElementById("browser-time-status").textContent'),/Using browser time/);
  assert.equal(await evaluate('document.getElementById("local-password").value'),'');
  assert.equal(await evaluate('document.activeElement===document.getElementById("access-toggle")'),false,'successful login does not retain button focus');
  assert.equal(await evaluate('getComputedStyle(document.getElementById("access-toggle")).borderTopWidth'),'4px','unlocked border is stronger');
  assert.equal(await evaluate('getComputedStyle(document.getElementById("access-toggle")).outlineStyle'),'none','no post-login focus ring');
  await evaluate('document.getElementById("wifi-host-link").focus()');
  await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
  await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
  assert.equal(await evaluate('document.activeElement.id'),'access-toggle','lock remains reachable by keyboard');
  assert.equal(await evaluate('document.activeElement.matches(":focus-visible")'),true,'keyboard focus remains visible');
  await evaluate('document.activeElement.blur()');
  if(process.env.PICO_BROWSER_NO_CAPTURE!=='1') {
    const shot=await cdp.send('Page.captureScreenshot',{format:'png'});
    await writeFile(path.join(output,'unlocked-desktop.png'),Buffer.from(shot.data,'base64'));
  }
  await cdp.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  if(process.env.PICO_BROWSER_NO_CAPTURE!=='1') {
    const shot=await cdp.send('Page.captureScreenshot',{format:'png'});
    await writeFile(path.join(output,'unlocked-mobile.png'),Buffer.from(shot.data,'base64'));
  }
  console.log('PASS AP root, password unlock and browser UTC survive a five-second reply without replay; mobile layout remains bounded');
});
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href)
  await checkApUnlock(process.argv[2],path.resolve(process.argv[3] || 'build/ap-unlock-browser'));
