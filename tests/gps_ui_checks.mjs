// SPDX-License-Identifier: MIT
// Native shipped editor -> real HTTP/crypto/handlers/journal; synthetic board.
import assert from 'node:assert/strict';
export async function checkGps({evaluate,section,click,idle,capture,telemetryFixture}) {
    await section('radio-pins');await idle();
    assert.equal(await evaluate(`document.querySelector('[data-gps="daylight"]').closest('[data-operator-section]').id`),'time-calibration');
    assert.equal(await evaluate(`document.querySelector('#gps-settings details').querySelectorAll('p,small').length`),0,'wiring explanations live in the manual');
    assert.match(await evaluate(`document.querySelector('[data-help="Validated UTC/PPS association"]').href`),/#validated-utc-pps-association$/);

    await evaluate(`globalThis.gpsWrites=[];globalThis.gpsApi=api;api=async(...a)=>{if(a[1]&&a[1]!=='GET')gpsWrites.push(structuredClone(a));return gpsApi(...a)};
      globalThis.gpsSet=(key,value)=>{const e=document.querySelector('[data-gps="'+key+'"]');e.value=String(value);e.dispatchEvent(new Event('change',{bubbles:true}))};`);
    assert.equal(await evaluate(`document.querySelector('[data-gps="enabled"]').disabled`),false);
    assert.equal(await evaluate(`document.querySelector('[data-gps="enabled"]').value`),'false');
    await section('time-calibration');await click('save-beacon-policy');await idle();
    assert.equal(await evaluate('gpsWrites.length'),0,'Saving the default on a Pico without GPS settings leaves the configuration unchanged');
    await evaluate(`globalThis.countedGpsApi=api;api=async(...args)=>{
      const result=await countedGpsApi(...args);
      return args[0]==='hardware' ? {...result,revision:'"another-settings-revision"'} : result;
    };`);
    await click('save-beacon-policy');await idle();
    assert.equal(await evaluate('gpsWrites.length'),0,'A stale default save sends no mutation');
    assert.equal(await evaluate('writeState'),'readback','A stale default save requires fresh readback');
    assert.doesNotMatch(await evaluate('document.getElementById("beacon-policy-status").textContent'),/already/);
    await evaluate('api=countedGpsApi');
    await evaluate("gpsSet('daylight','day_manual')");
    await click('read-saved');await idle();
    assert.match(await evaluate("document.getElementById('draft-comparison').textContent"),
      /Automatic beacon schedule.*Daylight only \(saved grid\).*24 hours/);
    await capture('beacon-conflict-comparison');
    await click('review-saved');await idle();
    await section('time-calibration');
    await evaluate("gpsSet('daylight','day_manual')");await click('save-beacon-policy');await idle();
    assert.equal(await evaluate('currentConfig.gps.daylight'),'day_manual');
    await evaluate("gpsSet('daylight','always')");await click('save-beacon-policy');await idle();
    assert.equal(await evaluate('gpsWrites.at(-1)[2].config.gps'),null,'24 hours clears a policy-only GPS object');
    assert.equal(await evaluate('currentConfig.gps == null'),true,'The cleared policy stays absent on readback');
    await evaluate('gpsWrites.length=0');
    await section('radio-pins');
    await capture('gps-settings');
    await evaluate(`gpsSet('location','gps')`);await click('save-pins');await idle();
    assert.equal(await evaluate('gpsWrites.length'),0);
    assert.equal(await evaluate('document.activeElement.dataset.gps'),'enabled');
    await evaluate(`gpsSet('enabled',true);gpsSet('location','manual')`);
    assert.equal(await evaluate(`document.querySelector('[data-gps="enabled"]').checkValidity()`),true,'Changing the cause clears dependent GPS custom validity');
    await evaluate(`document.querySelector('#gps-settings details').open=true;gpsSet('enabled',true);gpsSet('pps_gp',currentConfig.pins.rf_gp??currentConfig.pins.button_gp)`);
    await click('save-pins');await idle();
    assert.equal(await evaluate('gpsWrites.length'),0,'Allocation conflict refuses before writes');
    assert.equal(await evaluate('document.activeElement.dataset.gps'),'pps_gp');
    await evaluate(`gpsSet('pps_gp',3);gpsSet('minimum_message_delay_ms',900);gpsSet('maximum_message_delay_ms',800)`);
    await click('save-pins');await idle();
    assert.equal(await evaluate('gpsWrites.length'),0);
    assert.equal(await evaluate('document.activeElement.dataset.gps'),'maximum_message_delay_ms');
    await evaluate(`gpsSet('minimum_message_delay_ms',0)`);
    assert.equal(await evaluate(`document.querySelector('[data-gps="maximum_message_delay_ms"]').checkValidity()`),true,'Lowering the minimum clears the maximum-field dependency error');
    await evaluate(`gpsSet('minimum_message_delay_ms',0);gpsSet('maximum_message_delay_ms',1200)`);
    await click('save-pins');await idle();
    assert.equal(await evaluate('gpsWrites.length'),0,'An ambiguous-width delay window refuses before writes');
    assert.equal(await evaluate('document.activeElement.dataset.gps'),'maximum_message_delay_ms');
    await evaluate(`gpsSet('minimum_message_delay_ms',600)`);
    assert.equal(await evaluate(`document.querySelector('[data-gps="maximum_message_delay_ms"]').checkValidity()`),true);
    await evaluate(`gpsSet('receiver','e108');gpsSet('tx_gp',0);gpsSet('receiver','qlg3')`);
    await click('save-pins');await idle();
    assert.equal(await evaluate('gpsWrites.length'),0,'QLG3 cannot inherit a configuration-output draft');
    await evaluate(`gpsSet('tx_gp','');gpsSet('rx_gp',1);gpsSet('pps_gp',3)`);
    await evaluate(`gpsSet('daylight','day_manual')`);
    await capture('gps-details');
    await click('save-pins');await idle();
    assert.equal(await evaluate('gpsWrites.length'),1);
    assert.equal(await evaluate('gpsWrites[0][0]'),'config/update');
    assert.equal(await evaluate('currentConfig.gps.enabled'),true);
    assert.equal(await evaluate('currentConfig.gps.daylight'),'always','Pin save preserves the saved beacon policy');
    assert.equal(await evaluate(`document.querySelector('[data-gps="daylight"]').value`),'day_manual','Pin save preserves the pending beacon choice');
    assert.equal(await evaluate('currentConfig.gps.pairing_qualified'),false,'Saving pins cannot invent time qualification');
    assert.equal(await evaluate('currentConfig.gps.tx_gp'),null);
    assert.equal(await evaluate('currentConfig.gps.minimum_message_delay_ms'),600);
    assert.equal(await evaluate('currentConfig.gps.maximum_message_delay_ms'),1200);
    await section('time-calibration');await evaluate(`gpsSet('daylight','day')`);
    await click('save-beacon-policy');await idle();
    assert.equal(await evaluate('currentConfig.gps.daylight'),'day','relocated policy saves through production configuration path');
    assert.equal(await evaluate(`document.querySelector('[data-gps="daylight"]').value`),'day','confirmed policy readback stays in relocated control');
    await capture('time-calibration');
    await evaluate(`gpsEditor.enable(false)`);
    assert.equal(await evaluate(`document.querySelector('[data-gps="daylight"]').disabled`),true,'relocated input follows editor lock');
    await idle();await section('time-calibration');await evaluate(`gpsSet('daylight','night_manual')`);
    await click('save-beacon-policy');await idle();
    await section('radio-pins');

    assert.match(await evaluate('document.querySelector("[data-gps-status]").textContent'),/unavailable|not available|not been read/i);
    await evaluate(`gpsSet('enabled',false)`);await click('save-pins');await idle();
    assert.equal(await evaluate('currentConfig.gps.enabled'),false);
    assert.equal(await evaluate('currentConfig.gps.daylight'),'night_manual');
    await section('time-calibration');
    assert.equal(await evaluate(`document.querySelector('[data-gps="daylight"] option[value="always"]').textContent`),'24 hours');
    const savedPins = await evaluate('currentConfig.pins');
    const pinDraft = await evaluate(`(()=>{
      const field=document.querySelector('[name="button_gp"]');
      const original=field.value;
      field.value=[...field.options].find(option=>!option.disabled && option.value!==original).value;
      field.dispatchEvent(new Event('input',{bubbles:true}));
      return field.value;
    })()`);
    await evaluate(`gpsSet('receiver','e108');gpsSet('daylight','day_manual')`);
    await click('save-beacon-policy');await idle();
    assert.deepEqual(await evaluate('Object.keys(gpsWrites.at(-1)[2].config)'),['gps']);
    assert.deepEqual(await evaluate('currentConfig.pins'),savedPins);
    assert.equal(await evaluate('currentConfig.gps.daylight'),'day_manual');
    assert.equal(await evaluate('currentConfig.gps.enabled'),false);
    assert.equal(await evaluate('currentConfig.gps.receiver'),'qlg3');
    assert.equal(await evaluate(`document.querySelector('[name="button_gp"]').value`),pinDraft);
    assert.equal(await evaluate(`document.querySelector('[data-gps="receiver"]').value`),'e108');
    await capture('beacon-saved-grid');
    const before = await evaluate('gpsWrites.length');
    await evaluate(`gpsSet('daylight','night')`);await click('save-beacon-policy');await idle();
    assert.equal(await evaluate('gpsWrites.length'),before,'GPS schedule with GPS disabled refuses before a write');
    assert.equal(await evaluate('document.activeElement.dataset.gps'),'daylight');
    await evaluate(`gpsSet('daylight','always')`);await click('save-beacon-policy');await idle();
    assert.equal(await evaluate('currentConfig.gps.minimum_message_delay_ms'),600,'24 hours preserves nondefault GPS settings');
    await evaluate(`gpsSet('receiver','qlg3');document.querySelector('[name="button_gp"]').value=${JSON.stringify(String(savedPins.button_gp??''))};`);
    if(telemetryFixture) {
      // Presentation-only check using actual BrowserApi output from the SDK fixture.
      // This does not replace the production carrier and mutation assertions above.
      await evaluate(`gpsEditor.observation(${JSON.stringify(telemetryFixture)})`);
      assert.match(await evaluate('document.querySelector("[data-gps-status]").textContent'),/Capture IRQ latency .*timestamp bound .*rejected captures/);
      await capture('gps-telemetry');
      await evaluate('gpsEditor.observation(null)');
    }
    await evaluate('api=gpsApi');
}
