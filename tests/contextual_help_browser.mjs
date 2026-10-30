// Called by both production-handler section carriers; popups use the fixture's
// deny-by-default proxy, so this check never reaches the public Internet.
import assert from 'node:assert/strict';
export async function checkContextualHelp({evaluate,send,key,section,helpWindows}) {
  assert.equal(await evaluate(`document.querySelectorAll('[data-operator-section]:not(:has(>summary>a.documentation-help))').length`),0,'every major disclosure has collapsed help');
  assert.equal(await evaluate(`!!document.querySelector('#local-access a.documentation-help') && !!document.querySelector('#login-recovery summary a.documentation-help')`),true,'modal and occupied-login help');
  for(const topic of ['LPF and band selector','UDP logging','USB logging','CW timing','Prepared job files','Recurring message schedule','Manual RF correction','NTP timeout and clock state'])
    assert.equal(await evaluate(`!!document.querySelector('[data-help="${topic}"]')`),true,topic);
  await section('radio-settings');
  await evaluate(`document.getElementById('radio-settings').open=false;document.getElementById('message-frequency').value='invalid raw draft';const helpTransfer=new DataTransfer();helpTransfer.items.add(new File(['draft'],'help-draft.json'));document.getElementById('job-file').files=helpTransfer.files;globalThis.helpFile=document.getElementById('job-file').files[0];globalThis.helpSnapshot=JSON.stringify({hash:location.hash,state:history.state,area:document.getElementById('station-area').hidden,open:[...document.querySelectorAll('details')].map(e=>e.open)});globalThis.helpRequests=[];globalThis.helpFetch=fetch;globalThis.fetch=(...args)=>{helpRequests.push(String(args[0]));return helpFetch(...args)};`);
  const selector='#radio-settings>summary>a.documentation-help';
  for(const activation of ['pointer','keyboard']) {
    const before=helpWindows.length;
    await evaluate(`document.querySelector('${selector}').scrollIntoView({block:'center'})`);
    if(activation==='pointer') {
      const point=await evaluate(`(()=>{const r=document.querySelector('${selector}').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
      await send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
      await send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
    } else {
      await evaluate(`document.querySelector('${selector}').focus()`);await key('Enter');
    }
    assert.equal(helpWindows.length,before+1,activation+' opens native popup');
    assert.equal(helpWindows.at(-1).url,'https://wsprrypico.readthedocs.io/en/devel/configure.html#wspr-configuration');
    const targets=await send('Target.getTargets');
    for(const target of targets.targetInfos) if(target.openerId)await send('Target.closeTarget',{targetId:target.targetId});
    assert.equal(await evaluate(`JSON.stringify({hash:location.hash,state:history.state,area:document.getElementById('station-area').hidden,open:[...document.querySelectorAll('details')].map(e=>e.open)})===helpSnapshot && document.getElementById('message-frequency').value==='invalid raw draft' && document.getElementById('job-file').files[0]===helpFile`),true,'native help preserves drafts, selected file, History and collapsed state');
  }
  assert.equal(await evaluate('helpRequests.length'),0,'help makes no application request');
  await evaluate('globalThis.fetch=helpFetch');
  // Native summary keyboard activation still toggles, independently of the link.
  await evaluate(`document.querySelector('#radio-settings>summary').focus()`);await key('Enter');
  assert.equal(await evaluate('document.getElementById("radio-settings").open'),true);
  await evaluate(`document.getElementById('radio-settings').open=false;document.getElementById('message-frequency').value='';document.getElementById('job-file').value=''`);
  await evaluate(`document.querySelector('#radio-settings [data-top]').click()`);
}
