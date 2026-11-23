// Shipped page -> Chrome -> actual production HTTP/AEAD, synthetic board/time.
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {BrowserHarness,until,navigationTransient} from './browser_harness.mjs';
const driver=process.argv[2]&&path.resolve(process.argv[2]),output=path.resolve(process.argv[3]||'build/native-retirement-ui');
if(!driver)throw Error('Expected hardware-inhibited HTTP fixture');
const h=new BrowserHarness();
await h.run(async()=>{
 await mkdir(output,{recursive:true});
 const port=19249,profile=await h.profile('pico-native-retirement-');
 await h.review(driver,port,output,{profiles:['consumer-lan'],messages:true});
 const started=await h.chrome(process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
  '--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
  '--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:'+port,'--proxy-bypass-list=<-loopback>','about:blank'],profile);
 const cdp=await h.connect(started.pages[0].webSocketDebuggerUrl,{dialogs:true});
 const send=(...args)=>cdp.send(...args),evaluate=value=>cdp.evaluate(value);
 const pageErrors=[];cdp.on('Runtime.exceptionThrown',event=>pageErrors.push(event.exceptionDetails?.exception?.description||event.exceptionDetails?.text));
 await send('Runtime.enable');
 await send('Page.enable');await send('Page.navigate',{url:'http://192.168.1.53/'});
 await until(()=>evaluate('typeof accessCarrier!=="undefined" && !!localIdentity && !busy').catch(navigationTransient),'actual admitted page');
 assert.deepEqual(pageErrors,[],'Shipped page initializes without uncaught errors');
 assert.equal(await evaluate('typeof lastBrowserTimeRefresh'), 'number','All retained settings controls finish initialization');
 assert.equal(await evaluate('document.getElementById("native-stop").disabled'),true);
 assert.equal(await evaluate('!!document.querySelector("#job-file,#send-once,#release,#abort")'),false);
 const capture=async state=>{
  for(const theme of ['light','dark'])for(const viewport of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
   await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
   await send('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.name==='mobile'});
   await evaluate('scrollTo(0,0)');assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'no horizontal overflow');
   const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
   await writeFile(path.join(output,`${state}-${theme}-${viewport.name}.png`),Buffer.from(shot.data,'base64'));
  }
 };
 await capture('locked');
 await evaluate('document.getElementById("access-toggle").click()');
 assert.equal(await evaluate('document.activeElement.id'),'local-password');
 await evaluate('document.getElementById("local-password").value="test-password"');
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',windowsVirtualKeyCode:13});
 await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 await until(()=>evaluate('!busy && !document.getElementById("native-stop").disabled'),'authenticated native stop');
 await evaluate(`document.getElementById('message-text').value='CQ RETAINED DRAFT';document.getElementById('message-text').dispatchEvent(new Event('input',{bubbles:true}));
  globalThis.retirementCalls=[];globalThis.retirementApi=api;api=async(...args)=>{retirementCalls.push([args[0],args[1]||'GET']);const result=await retirementApi(...args);if(globalThis.loseNativeStop&&args[0]==='schedules/stop'&&args[1]==='POST'){loseNativeStop=false;throw Object.assign(Error('Fixture lost stop reply'),{unconfirmed:true});}return result;};`);
 await evaluate('document.getElementById("native-stop").focus()');
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',windowsVirtualKeyCode:13});
 await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 await until(()=>evaluate('!busy && document.getElementById("native-stop-status").textContent.includes("confirmed inactive")'),'confirmed native stop');
 assert.equal(await evaluate('document.getElementById("message-text").value'),'CQ RETAINED DRAFT');
 assert.equal(await evaluate('retirementCalls.filter(([r,m])=>r==="schedules/stop"&&m==="POST").length'),1);
 await capture('confirmed-stop');
 await until(()=>evaluate('!document.getElementById("native-stop").disabled'),'fresh stop observation');
 await evaluate('globalThis.loseNativeStop=true;document.getElementById("native-stop").click()');
 await until(()=>evaluate('!busy && nativeStopUnknown && !document.getElementById("native-stop-read").hidden'),'unknown outcome hold');
 assert.deepEqual(pageErrors,[],'Shipped page initializes without uncaught errors');
 assert.equal(await evaluate('typeof lastBrowserTimeRefresh'), 'number','All retained settings controls finish initialization');
 assert.equal(await evaluate('document.getElementById("native-stop").disabled'),true);
 assert.equal(await evaluate('document.getElementById("restart").disabled'),true,'Unknown stop cannot reset into an unreconciled schedule');
 assert.equal(await evaluate('document.getElementById("settings").disabled'),true,'Unknown stop holds schedule edits');
 await evaluate(`globalThis.heldWrites=[];const heldRequest=radio.request.bind(radio);radio.request=(...args)=>{if(args[1]&&args[1]!=='GET')heldWrites.push(args[0]);return heldRequest(...args);};`);
 assert.equal(await evaluate(`api('restart','POST',{}).then(()=>false,error=>error.message.includes('Read stop status'))`),true);
 assert.equal(await evaluate('heldWrites.length'),0,'Hold refuses a new mutation before encrypted transport');
 await evaluate('refresh()');
 assert.match(await evaluate('document.getElementById("output").textContent'),/Unknown.*stop unconfirmed/);
 assert.equal(await evaluate('retirementCalls.filter(([r,m])=>r==="schedules/stop"&&m==="POST").length'),2);
 assert.equal(await evaluate('document.getElementById("message-text").value'),'CQ RETAINED DRAFT');
 assert.match(await evaluate('document.getElementById("console-warning").textContent'),/Read stop status/);
 await capture('unknown-stop');
 await evaluate('document.getElementById("native-stop-read").focus()');
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',windowsVirtualKeyCode:13});
 await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 await until(()=>evaluate('!busy && !nativeStopUnknown'),'explicit native stop readback');
 assert.equal(await evaluate('retirementCalls.filter(([r,m])=>r==="schedules/stop"&&m==="POST").length'),2,'readback never replays stop');
 assert.equal(await evaluate('retirementCalls.some(([r])=>r==="jobs"||r.startsWith("jobs/"))'),false);
 assert.equal(await evaluate('document.getElementById("message-text").value'),'CQ RETAINED DRAFT');
 await capture('readback');
 assert.deepEqual(pageErrors,[],'No uncaught errors during stop/readback');
 await writeFile(path.join(output,'checks.json'),JSON.stringify({actualHttpAead:true,keyboard:true,draftsPreserved:true,stopPosts:2,unknownReadbackNoReplay:true,themes:['light','dark'],widths:[1280,390]},null,2)+'\n');
 console.log('PASS actual shipped native stop, keyboard, retained draft, lost-reply readback without replay, and desktop/mobile layout under both OS color preferences');
});
