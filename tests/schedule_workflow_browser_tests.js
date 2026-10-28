'use strict';
// Real editor and application state machine with deterministic DOM/API doubles.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {fixture} = require('./network_browser_tests.js');
const {create} = require('../src/network/web/standalone-frequency.js');
const target = {scope:'member',device_id:'1'.repeat(32),boot_id:'a'.repeat(32)};
const station = {callsign:'AA0NT',locator:'EM18',power_dbm:37};
const element = value => ({value,disabled:false,hidden:false,textContent:'',setAttribute(){}});

async function saveDial(f, revision = '"original-revision"') {
    const ui = {input:element(''),read:element(),save:element(),discard:element(),adopt:element(),status:element()};
    let dial = null, writes = 0;
    const editor = create({...ui,afterSave:async result=>{
        f.context.ack = result;
        await vm.runInContext("reconcileConfirmedSettings(ack,ack.data.target,'Confirmed frequency; schedule settings are ready.')",f.context);
        vm.runInContext('controls(online)',f.context);
    },exchange:async(method,body,match,resource)=>{
        if (resource === 'station/2') return {revision,data:{schema:'transmitter-station/2',target,station,storage_healthy:true}};
        if (resource === 'progress') return {revision,data:{schema:'transmitter-progress/1',target,applied_station:station,station_complete:true}};
        if (method === 'PUT') {dial=body.frequency_hz;++writes;}
        return {revision,data:{schema:'transmitter-standalone-frequency/1',target,frequency_hz:dial,allowed:dial!==null,storage_healthy:true}};
    }});
    editor.setAvailability(true);await ui.read.onclick();
    ui.input.value='14095600';ui.input.oninput();await ui.save.onclick();
    assert.equal(writes,1);assert.equal(dial,14095600);
    return ui;
}

(async()=>{
    const f=await fixture();
    f.form.enabled.checked=true;f.form.schedules.value='600 / 120';
    f.elements.config.oninput();
    await saveDial(f);
    assert.equal(vm.runInContext('writeState',f.context),'ready');
    assert.equal(f.elements['save-config'].disabled,false);
    assert.equal(f.form.enabled.checked,true);assert.equal(f.form.schedules.value,'600 / 120','confirmed save preserves all browser edits');
    assert.match(f.elements['schedule-save-help'].textContent,/stores your edits as a draft/);
    assert.equal(f.calls.filter(c=>c.options.method && c.options.method!=='GET').length,0,'readback never applies or saves the schedule');
    for (const checked of [false,true]) {
        f.form.enabled.checked=checked;f.elements.config.oninput();
        assert.equal(f.elements['save-config'].disabled,false,'checkbox stays saveable after confirmed frequency save');
    }
    const concurrent=await fixture();concurrent.form.enabled.checked=true;
    await saveDial(concurrent,'"earlier-revision"');
    assert.equal(vm.runInContext('writeState',concurrent.context),'review');
    assert.equal(concurrent.elements['save-config'].disabled,true);
    assert.match(concurrent.elements['schedule-save-help'].textContent,/I reviewed saved settings/);
    assert.equal(concurrent.form.enabled.checked,true);
    assert.match(concurrent.elements['save-reconcile-status'].textContent,/changed afterward/);
    await concurrent.elements['review-saved'].onclick();
    assert.equal(concurrent.elements['save-config'].disabled,false);
    const interrupted=await fixture();interrupted.configSaveMode='lost';
    interrupted.form.schedules.value='240 / 0';interrupted.elements.config.oninput();
    await interrupted.elements.config.onsubmit({preventDefault(){}});
    assert.equal(vm.runInContext('writeState',interrupted.context),'readback');
    await saveDial(interrupted);
    assert.equal(vm.runInContext('writeState',interrupted.context),'review','a later confirmed frequency save must not clear an earlier ambiguous settings save');
    assert.equal(interrupted.elements['save-config'].disabled,true);
    assert.match(interrupted.elements['save-reconcile-status'].textContent,/earlier settings save still needs review/);
    await interrupted.elements['review-saved'].onclick();
    assert.equal(interrupted.elements['save-config'].disabled,false);
    const rebooted=await fixture();rebooted.state.job.boot_id='b'.repeat(32);
    await saveDial(rebooted);
    assert.equal(vm.runInContext('writeState',rebooted.context),'review','changed boot needs deliberate review');
    const unavailable=await fixture();unavailable.offline=true;
    const ui=await saveDial(unavailable);
    assert.match(ui.status.textContent,/Saved WSPR dial/,'successful save remains confirmed if subsequent settings read fails');
    assert.match(unavailable.elements['save-reconcile-status'].textContent,/save succeeded.*could not be read back/);
    assert.equal(vm.runInContext('writeState',unavailable.context),'readback');
    assert.equal(unavailable.elements['save-config'].disabled,true);
    unavailable.offline=false;
    await unavailable.elements.refresh.onclick();
    await unavailable.elements['read-saved'].onclick();await unavailable.elements['review-saved'].onclick();
    assert.equal(unavailable.elements['save-config'].disabled,false);
    const html=require('node:fs').readFileSync(require.resolve('../src/network/web/index.html'),'utf8');
    assert.doesNotMatch(html,/id="standalone-status"/,'schedule observations belong to the contextual status console');
    console.log('PASS schedule workflow: confirmed-save continuation, preserved checkbox/draft, concurrent revision and boot review, failed readback recovery, unified status surface');
})().catch(error=>{console.error(error);process.exitCode=1;});
