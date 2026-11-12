// SPDX-License-Identifier: MIT
import assert from 'node:assert/strict';
export async function checkUnsetSettings({evaluate,section,click,idle,capture}) {
  const empty=await evaluate(`Promise.all(['gray-line','rf-calibration'].map(p=>api(p).then(r=>({saved:r.data.saved,healthy:r.data.storage_healthy}))))`);
  assert.deepEqual(empty,[{saved:null,healthy:true},{saved:null,healthy:true}],'production handlers report healthy unset settings');
  for(const id of ['gray-line-1-status','rf-calibration-status']) {
    const text=await evaluate(`document.getElementById('${id}').textContent`);
    assert.match(text,/No standalone station configuration is applied/);
    assert.doesNotMatch(text,/unavailable|unsupported|another Pico/);
  }
  assert.equal(await evaluate('document.getElementById("radio-result-reveal").hidden'),true);
  assert.equal(await evaluate('document.querySelector("#gray-line-controls fieldset").disabled'),true);
  assert.equal(await evaluate('document.getElementById("rf-manual-ppm").disabled'),true);
  await evaluate(`globalThis.emptyApi=api;globalThis.emptyWrites=[];api=async(...args)=>{if(args[1]&&args[1]!=='GET')emptyWrites.push(args[0]);return emptyApi(...args)};`);
  for(const id of ['gray-line-1-save','rf-calibration-save']) {
    assert.equal(await evaluate(`document.getElementById('${id}').disabled`),true);
    await click(id);await idle();
  }
  assert.deepEqual(await evaluate('emptyWrites'),[],'unset settings never enable a mutation');
  await section('advanced-scheduling');await capture('gray-line-unset');
  await section('time-calibration');await capture('time-calibration');
  await evaluate('api=emptyApi');
}

export async function checkUnsetGrayDraft({evaluate,section,idle}) {
  await section('advanced-scheduling');await idle();
  await evaluate(`globalThis.grayDraftApi=api;const field=document.querySelector('[data-gray="morning.upper_mdeg"]');field.value='7';field.dispatchEvent(new Event('input',{bubbles:true}));
    api=async(...args)=>{const r=await grayDraftApi(...args);return args[0]==='gray-line'&&(!args[1]||args[1]==='GET')?{...r,data:{...r.data,saved:null}}:r};`);
  await evaluate('grayLineEditor.load()');
  assert.equal(await evaluate(`document.querySelector('[data-gray="morning.upper_mdeg"]').value`),'7');
  assert.match(await evaluate('document.getElementById("gray-line-1-status").textContent'),/entries are preserved/);
  assert.equal(await evaluate('document.getElementById("gray-line-1-save").disabled'),true);
  await evaluate('api=grayDraftApi');await evaluate('grayLineEditor.load()');
  assert.equal(await evaluate(`document.querySelector('[data-gray="morning.upper_mdeg"]').value`),'7');
  assert.equal(await evaluate('document.getElementById("gray-line-1-save").disabled'),false);
  await evaluate('document.getElementById("gray-line-1-discard").click()');
}

export async function checkGrayLine({evaluate,section,idle,capture}) {
  await section('advanced-scheduling');
  await evaluate('grayLineEditor.read()');await idle();
  const query=`document.querySelector('#gray-line-controls [data-gray="morning.enabled"]')`;
  assert.equal(await evaluate(`${query}.matches(':disabled')`),false);
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-gray="morning.lower_mdeg"]').value`),'-6');
  await evaluate(`${query}.checked=true;${query}.dispatchEvent(new Event('input',{bubbles:true}));`);
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-action="save"]').disabled`),false);
  await evaluate(`document.querySelector('#gray-line-controls [data-action="save"]').click()`);await idle();
  const saved=await evaluate(`api('gray-line').then(r=>r.data.saved)`);assert.equal(saved.morning.enabled,true);
  await evaluate(`(()=>{const input=document.querySelector('#gray-line-controls [data-gray="morning.wspr_dial_frequency_hz"]');input.value='1234567';input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#gray-line-controls [data-action="save"]').click();})()`);await idle();
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-gray="morning.wspr_dial_frequency_hz"]').value`),'1234567');
  assert.match(await evaluate(`document.querySelector('#gray-line-controls [role="status"]').textContent`),/Read saved settings before another save/);
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-action="save"]').disabled`),true);
  assert.deepEqual(await evaluate(`api('gray-line').then(r=>r.data.saved)`),saved);
  await evaluate(`document.querySelector('#gray-line-controls [data-action="read"]').click()`);await idle();
  await evaluate(`document.querySelector('#gray-line-controls [data-action="discard"]').click()`);
  await evaluate(`(()=>{const input=document.querySelector('#gray-line-controls [data-gray="morning.lower_mdeg"]');input.value='6';input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-action="save"]').disabled`),true);
  assert.match(await evaluate(`document.querySelector('#gray-line-controls [role="status"]').textContent`),/lower elevation/);
  await capture('gray-line-validation');
  await evaluate(`document.querySelector('#gray-line-controls [data-action="discard"]').click();${query}.checked=false;${query}.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#gray-line-controls [data-action="save"]').click();`);await idle();
  const restored=await evaluate(`api('gray-line').then(r=>r.data.saved)`);assert.equal(restored.morning.enabled,false);
  await capture('gray-line');
}
