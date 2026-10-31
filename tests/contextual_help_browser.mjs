// Called by both production-handler section carriers; popups use the fixture's
// deny-by-default proxy, so this check never reaches the public Internet.
import assert from 'node:assert/strict';
export async function checkContextualHelp({evaluate,send,key,section,helpWindows}) {
  assert.equal(await evaluate(`document.querySelectorAll('[data-operator-section]:not(:has(>summary a.documentation-help))').length`),0,'every major disclosure has collapsed help');
  assert.equal(await evaluate(`document.querySelectorAll('details>summary:not(:has(a.documentation-help))').length`),0,'every disclosure, including generated UDP controls, has contextual help');
  assert.equal(await evaluate(`document.querySelectorAll('section:not(:has(a.documentation-help))').length`),0,'every operator section has contextual help');
  assert.equal(await evaluate(`!!document.querySelector('#local-access a.documentation-help') && !!document.querySelector('#login-recovery summary a.documentation-help')`),true,'modal and occupied-login help');
  for(const topic of ['LPF and band selector','UDP logging','USB logging','CW timing','Prepared job files','Recurring message schedule','Manual RF correction','NTP timeout and clock state'])
    assert.equal(await evaluate(`!!document.querySelector('[data-help="${topic}"]')`),true,topic);
  assert.equal(await evaluate(`[...document.querySelectorAll('a.documentation-help')].every(a=>a.getAttribute('aria-label') && a.title && a.querySelector('svg[aria-hidden="true"][focusable="false"]') && !a.textContent.trim())`),true,'every contextual link is a named decorative inline icon');
  for(const width of [1280,390,320,740]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<800});
    assert.equal(await evaluate(`(()=>{const h=document.getElementById('status-heading').getBoundingClientRect(),a=document.querySelector('[data-help="Transmitter status"]'),r=a.getBoundingClientRect(),s=a.querySelector('svg').getBoundingClientRect();return r.x>=h.right && r.x-h.right<=4 && Math.abs(r.y+r.height/2-h.y-h.height/2)<2 && r.width>=44 && r.height>=44 && s.width===16 && s.height===16 && document.documentElement.scrollWidth<=innerWidth})()`),true,'status help stays beside its heading at '+width+'px');
    assert.equal(await evaluate(`(()=>{const a=document.getElementById('header-help'),r=a.getBoundingClientRect(),nav=document.getElementById('area-nav').getBoundingClientRect(),m=document.querySelector('main').getBoundingClientRect(),pad=parseFloat(getComputedStyle(document.querySelector('main')).paddingRight);return Math.abs(r.right-(m.right-pad))<1 && nav.right<=r.left && r.width>=44 && r.height>=44 && getComputedStyle(a).color==='rgb(219, 229, 237)'})()`),true,'manual icon follows navigation at the content edge at '+width+'px');
    if(width===1280) {
      // Reserve layout space as a traditional scrollbar does on Linux.
      await evaluate(`document.body.style.width='calc(100% - 17px)'`);
      assert.equal(await evaluate(`(()=>{const a=document.getElementById('header-help'),r=a.getBoundingClientRect(),nav=document.getElementById('area-nav').getBoundingClientRect(),m=document.querySelector('main').getBoundingClientRect(),pad=parseFloat(getComputedStyle(document.querySelector('main')).paddingRight);return Math.abs(r.right-(m.right-pad))<1 && nav.right<=r.left && r.width>=44 && r.height>=44 && getComputedStyle(a).color==='rgb(219, 229, 237)'})()`),true,'header alignment uses available layout width, including reserved scrollbar space');
      await evaluate(`document.body.style.width=''`);
    }
    assert.equal(await evaluate(`[...document.querySelectorAll('[data-operator-section]>summary .help-heading')].every(g=>{const label=g.firstElementChild.getBoundingClientRect(),link=g.querySelector('a').getBoundingClientRect();return link.x>=label.right && link.x-label.right<=4 && Math.abs(link.y+link.height/2-label.y-label.height/2)<2})`),true,'long collapsed titles retain their adjacent icon');
  }
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await section('radio-settings');
  await evaluate(`document.getElementById('radio-settings').open=false;document.getElementById('message-frequency').value='invalid raw draft';const helpTransfer=new DataTransfer();helpTransfer.items.add(new File(['draft'],'help-draft.json'));document.getElementById('job-file').files=helpTransfer.files;globalThis.helpFile=document.getElementById('job-file').files[0];globalThis.helpSnapshot=JSON.stringify({hash:location.hash,state:history.state,area:document.getElementById('station-area').hidden,open:[...document.querySelectorAll('details')].map(e=>e.open)});globalThis.helpRequests=[];globalThis.helpFetch=fetch;globalThis.fetch=(...args)=>{helpRequests.push(String(args[0]));return helpFetch(...args)};`);
  for(const selector of ['#radio-settings>summary a.documentation-help','#header-help']) {
    for(const activation of ['pointer','keyboard']) {
      const before=helpWindows.length;
      await evaluate(`document.querySelector('${selector}').scrollIntoView({block:'center'})`);
      if(activation==='pointer') {
        const point=await evaluate(`(()=>{const r=document.querySelector('${selector}').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
        await send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
        await send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
      } else {
        await evaluate(selector==='#header-help' ? `document.getElementById('wifi-host-link').focus()` : `document.querySelector('#radio-settings>summary').focus()`);await key('Tab');
        assert.equal(await evaluate(`document.activeElement===document.querySelector('${selector}')`),true,'native Tab reaches help in locked fieldset');
        await key('Enter');
      }
      assert.equal(helpWindows.length,before+1,activation+' opens native popup');
      if(selector==='#header-help')assert.match(helpWindows.at(-1).url,/^https:\/\/wsprrypico\.readthedocs\.io\/en\/(main|devel)\/index\.html$/);
      else assert.match(helpWindows.at(-1).url,/^https:\/\/wsprrypico\.readthedocs\.io\/en\/(main|devel)\/configure\.html#wspr-configuration$/);
      const version=new URL(helpWindows.at(-1).url).pathname.split('/')[2];
      assert.equal(await evaluate(`[...document.querySelectorAll('a.documentation-help')].every(a=>new URL(a.href).pathname.startsWith('/en/${version}/'))`),true,'one maintained manual version across the shipped page');
      const targets=await send('Target.getTargets');
      for(const target of targets.targetInfos) if(target.openerId)await send('Target.closeTarget',{targetId:target.targetId});
      assert.equal(await evaluate(`JSON.stringify({hash:location.hash,state:history.state,area:document.getElementById('station-area').hidden,open:[...document.querySelectorAll('details')].map(e=>e.open)})===helpSnapshot && document.getElementById('message-frequency').value==='invalid raw draft' && document.getElementById('job-file').files[0]===helpFile`),true,'native help preserves drafts, selected file, History and collapsed state');
    }
  }
  assert.equal(await evaluate('helpRequests.length'),0,'help makes no application request');
  await evaluate('globalThis.fetch=helpFetch');
  // Native summary keyboard activation still toggles, independently of the link.
  await evaluate(`document.querySelector('#radio-settings>summary').focus()`);await key('Enter');
  assert.equal(await evaluate('document.getElementById("radio-settings").open'),true);
  await evaluate(`document.getElementById('radio-settings').open=false;document.getElementById('message-frequency').value='';document.getElementById('job-file').value=''`);
  await evaluate(`document.querySelector('#radio-settings [data-top]').click()`);
}
