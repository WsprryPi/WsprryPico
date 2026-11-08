// Opt-in focused geometry runner; production dispatcher and browser, no board.
import {BrowserHarness,until} from './browser_harness.mjs';
import {checkControlAlignment} from './control_alignment_checks.mjs';
const h=new BrowserHarness();
await h.run(async()=>{
  const [driver,output,mode='verify']=process.argv.slice(2);
  if(!driver||!output||!['baseline','verify'].includes(mode))throw Error('Usage: control_alignment_browser.mjs ABS_DRIVER OUTPUT [baseline|verify]');
  await (await h.review(driver,19149,output,{profiles:['consumer-lan']})).ready;
  const profile=await h.profile('pico-alignment-');
  const started=await h.chrome(process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:19149','--proxy-bypass-list=<-loopback>','about:blank'],profile);
  const cdp=await h.connect(started.pages[0].webSocketDebuggerUrl,{dialogs:true});const send=(...args)=>cdp.send(...args),evaluate=x=>cdp.evaluate(x);
  await send('Page.enable');await send('Page.bringToFront');await send('Page.navigate',{url:'http://192.168.1.53/'});
  await until(()=>evaluate('typeof busy!=="undefined" && !busy && !!settingsLoadedBoot'),'current served page');
  await evaluate('document.getElementById("access-toggle").click()');
  await until(()=>evaluate('!busy && !document.getElementById("login-submit").disabled && (document.getElementById("local-password").value="test-password",document.getElementById("local-login").requestSubmit(),true)'),'login admission');
  await until(()=>evaluate('!busy && localAuthenticated && !!currentConfig'),'authenticated state');
  const section=async id=>evaluate(`WsprryPicoSections.reveal(document.getElementById('${id}'));document.getElementById('${id}').scrollIntoView({block:'start'})`);
  await checkControlAlignment({evaluate,send,section,output,baseline:mode==='baseline'});
});
