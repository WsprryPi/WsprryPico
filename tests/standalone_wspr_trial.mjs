// Shipped browser controls -> production API/scheduler -> inhibited engine.
// Synthetic time and RAM journals; never evidence of physical RF performance.
import assert from 'node:assert/strict';

export async function firstWsprTransmission({cdp,click,field,login,until,control,capture}) {
  await until(()=>cdp.evaluate('!busy'),'frequency save and settings readback settled');
  assert.equal(await cdp.evaluate(`document.getElementById('save-config').disabled`),false,'confirmed dial save leaves schedule Save usable');
  assert.equal(await cdp.evaluate('writeState'),'ready');
  await click('standalone-frequency-read');await until(()=>cdp.evaluate('!busy'),'saved frequency verified');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
  assert.equal(await cdp.evaluate(`document.getElementById('save-config').disabled`),false,'frequency read retains the confirmed schedule continuation');
  await cdp.evaluate(`{const e=document.getElementById('config').elements.schedules;e.value='240 / 0';e.dispatchEvent(new Event('input',{bubbles:true}));}`);
  await cdp.evaluate(`document.getElementById('config').requestSubmit()`);
  await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.schedules?.[0]?.period_s===240`),'disabled schedule draft saved');
  await click('apply-progress');await until(()=>cdp.evaluate(`!busy && writeState==='ready'`),'disabled schedule applied');
  await click('refresh');await until(()=>cdp.evaluate('!busy'),'pre-enable status');
  if(await cdp.evaluate('snapshot.standalone.reboot_required')) {
    await cdp.evaluate(`document.getElementById('wifi-host-link').click()`);
    await click('restart');await until(()=>cdp.evaluate('restartSent && !busy'),'explicit restart requested');
    await control({op:'reboot'});
    await control({op:'message_review'}); // Model boot-applied saved configuration and active-job service.
    await cdp.evaluate('refresh()');
    await login();
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'restart login');
    await cdp.evaluate(`document.getElementById('station-link').click()`);
    await click('read-saved');await until(()=>cdp.evaluate(`!busy && writeState==='review'`),'restart settings read');
    await click('review-saved');await until(()=>cdp.evaluate(`!busy && writeState==='ready'`),'restart settings reviewed');
  }
  assert.equal(await cdp.evaluate('snapshot.standalone.reboot_required'),false);
  await cdp.evaluate(`document.getElementById('config').elements.enabled.click()`);
  await cdp.evaluate(`document.getElementById('config').requestSubmit()`);
  await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.enabled===true`),'enabled draft saved');
  assert.equal((await control({op:'frequency_state'})).enabled,false,'saving enable draft never applies it');
  assert.equal(await cdp.evaluate(`document.getElementById('apply-progress').disabled`),false);
  await click('apply-progress');
  await until(()=>cdp.evaluate(`!busy && writeState==='ready'`),'confirmed schedule application');
  assert.equal((await control({op:'frequency_state'})).enabled,true);
  assert.equal(await cdp.evaluate(`document.getElementById('progress-error-settings-enabled').textContent`),'Saved value applied.');
  assert.equal(await cdp.evaluate(`document.getElementById('save-config').disabled`),false,'confirmed Apply leaves later edits usable');
  await click('refresh');await until(()=>cdp.evaluate('!busy'),'enabled status');
  assert.match(await cdp.evaluate(`document.getElementById('standalone-status').textContent`),/enabled and waiting/);
  assert.equal(await cdp.evaluate('snapshot.job.state'),'empty');
  const initial=await control({op:'schedule_tick',delta_ns:'0'});
  const now=BigInt(initial.utc_now_ns),period=240000000000n;
  let start=now/period*period+1000000000n;if(start-now<10000000000n)start+=period;
  assert.equal((await control({op:'schedule_tick',delta_ns:String(start-now-5000000000n)})).state,'armed');
  await click('refresh');await until(()=>cdp.evaluate('!busy'),'armed status');
  assert.match(await cdp.evaluate(`document.getElementById('standalone-status').textContent`),/job is armed/);
  const job=await control({op:'accepted_job',surface:'consumer'});
  assert.equal(job.mode,'wspr');assert.equal(job.events.length,162);
  assert.equal(job.total_duration_ns,'110592000000');
  const tones=new Set(['14097097802734375','14097099267578125','14097100732421875','14097102197265625']);
  assert.ok(job.events.every(e=>tones.has(e.frequency_nhz)),'WSPR tones use the saved dial +1500 Hz center');
  assert.equal((await control({op:'schedule_tick',delta_ns:'5000000000'})).state,'running');
  await click('refresh');await until(()=>cdp.evaluate('!busy'),'running status');
  assert.equal(await cdp.evaluate('snapshot.job.state'),'running');
  assert.equal((await control({op:'schedule_tick',delta_ns:'110592000000'})).state,'complete');
  await click('refresh');await until(()=>cdp.evaluate('!busy'),'complete status');
  assert.equal(await cdp.evaluate('snapshot.job.state'),'complete');
  assert.equal(await cdp.evaluate('snapshot.job.output_active'),false,'dry-run output remains inhibited');
  await cdp.evaluate(`document.getElementById('config').elements.enabled.click()`);
  await cdp.evaluate(`document.getElementById('config').requestSubmit()`);
  await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.enabled===false`),'disabled draft saved');
  assert.equal((await control({op:'frequency_state'})).enabled,true,'disable also needs explicit application');
  await click('apply-progress');await until(()=>cdp.evaluate(`!busy && writeState==='ready'`),'disabled schedule applied');
  assert.equal((await control({op:'frequency_state'})).enabled,false);
  await click('refresh');await until(()=>cdp.evaluate('!busy'),'disabled status');
  assert.match(await cdp.evaluate(`document.getElementById('standalone-status').textContent`),/is disabled/);
  await control({op:'schedule_tick',delta_ns:'240000000000'});
  assert.deepEqual(await control({op:'accepted_job',surface:'consumer'}),job,'disabled schedule submits no subsequent job');
  await capture('first-wspr-complete-and-disabled');
  console.log('PASS complete shipped first-use: station application, dial save, enabled draft, explicit apply, WSPR armed/running/complete, explicit disable; no hardware/RF');
}
