// Actual shipped UI -> production HTTP/crypto/config journal. No hardware.
import assert from 'node:assert/strict';
import {checkSi5351} from './si5351_ui_checks.mjs';
import {checkGps} from './gps_ui_checks.mjs';
export async function checkHardwareSaveIsolation({evaluate,section,click,idle,capture}) {
  await idle();
  const before=await evaluate(`(async()=>({application:(await api('application')).data,hardware:(await api('hardware')).data,config:(await api('config')).data.config}))()`);
  assert.equal(before.application.recurrence.enabled,true);
  assert.equal(before.application.recurrence.suspended,true);
  assert.equal(before.application.recurrence.schedule_dial_frequency_nhz,'0');
  await evaluate(`(()=>{const f=document.getElementById('config').elements;
    f.schedules.value='invalid WSPR draft';f.expiry.value='invalid expiry';
    for(const field of [f.schedules,f.expiry])field.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  async function preserved() {
    const observed=await evaluate(`(async()=>({application:(await api('application')).data,hardware:(await api('hardware')).data,config:(await api('config')).data.config,draft:[document.getElementById('config').elements.schedules.value,document.getElementById('config').elements.expiry.value]}))()`);
    assert.deepEqual(observed.application.recurrence,before.application.recurrence);
    assert.deepEqual(observed.hardware.active,before.hardware.active);
    assert.equal(observed.hardware.pending_restart,true);
    assert.deepEqual(observed.draft,['invalid WSPR draft','invalid expiry']);
    const ordinary=config=>Object.fromEntries(Object.entries(config).filter(([key])=>!['pins','si5351','gps'].includes(key)));
    assert.deepEqual(ordinary(observed.config),ordinary(before.config));
    assert.equal(await evaluate('snapshot.job.output_active'),false);
    assert.equal(await evaluate('snapshot.job.owner_id'),null);
  }
  await section('radio-pins');
  await evaluate(`(()=>{const f=document.getElementById('config').elements;
    f.button_gp.value='15';f.button_gp.dispatchEvent(new Event('change',{bubbles:true}));
    f.indicator.value='external';f.indicator.dispatchEvent(new Event('change',{bubbles:true}));
    f.indicator_gp.value='6';f.indicator_gp.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await click('save-pins');await idle();
  assert.equal(await evaluate('currentConfig.pins.button_gp'),15);
  assert.equal(await evaluate('currentConfig.pins.indicator_gp'),6);
  await preserved();
  await checkSi5351({evaluate,section,click,idle,capture});await preserved();
  await checkGps({evaluate,section,click,idle,capture});await preserved();
  await section('radio-pins');await capture('suspended-hardware-saved');
}
