// SPDX-License-Identifier: MIT
import assert from 'node:assert/strict';
export async function checkGrayLine({evaluate,section,idle,capture}) {
  await section('time-calibration');
  await evaluate('grayLineEditor.read()');await idle();
  const query=`document.querySelector('#gray-line-controls [data-gray="morning.enabled"]')`;
  assert.equal(await evaluate(`${query}.matches(':disabled')`),false);
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-gray="morning.lower_mdeg"]').value`),'-6');
  await evaluate(`${query}.checked=true;${query}.dispatchEvent(new Event('input',{bubbles:true}));`);
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-action="save"]').disabled`),false);
  await evaluate(`document.querySelector('#gray-line-controls [data-action="save"]').click()`);await idle();
  const saved=await evaluate(`api('gray-line').then(r=>r.data.saved)`);assert.equal(saved.morning.enabled,true);
  await evaluate(`(()=>{const input=document.querySelector('#gray-line-controls [data-gray="morning.lower_mdeg"]');input.value='6';input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  assert.equal(await evaluate(`document.querySelector('#gray-line-controls [data-action="save"]').disabled`),true);
  assert.match(await evaluate(`document.querySelector('#gray-line-controls [role="status"]').textContent`),/lower elevation/);
  await capture('gray-line-validation');
  await evaluate(`document.querySelector('#gray-line-controls [data-action="discard"]').click();${query}.checked=false;${query}.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#gray-line-controls [data-action="save"]').click();`);await idle();
  const restored=await evaluate(`api('gray-line').then(r=>r.data.saved)`);assert.equal(restored.morning.enabled,false);
  await capture('gray-line');
}
