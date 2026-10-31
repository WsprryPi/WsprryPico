'use strict';
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {fixture} = require('./network_browser_tests.js');
(async () => {
  for (const shipped of [false,true]) {
    process.env.WSPRRY_PICO_BROWSER_SHIPPED = shipped ? '1' : '';
    const f = await fixture(), e = f.elements;
    const run = code => vm.runInContext(code, f.context);
    assert.equal(e['message-delivery'].value, 'recurring');
    assert.equal(e['message-interval'].value, '10');
    assert.equal(e['message-frequency'].value, '');
    assert.equal(e['message-text'].value, '73 DE AA0NT');
    assert.equal(Date.parse(e['message-start'].value+'Z') % 600000, 0);
    assert.equal(run('hasUnsavedDraft()'), false);
    run("currentConfig.station.callsign='K1ABC'; defaultMessageDraft()");
    assert.equal(e['message-text'].value,'73 DE K1ABC');
    e['message-text'].value='MY MESSAGE';
    e['message-form'].oninput({target:e['message-text']});
    run("currentConfig.station.callsign='W1AW'; defaultMessageDraft()");
    assert.equal(e['message-text'].value,'MY MESSAGE');
    assert.equal(run('hasUnsavedDraft()'),true);
    assert.equal(run("stationEntry({station:{callsign:null},fields:{},applied_station:null},'callsign')"),'N0CALL');
    assert.equal(run("stationEntry({station:{callsign:null},fields:{callsign:null},applied_station:null},'callsign')"),'');
    f.prepareMessage('qrss','73 DE N0CALL');
    assert.throws(()=>run('messagePlan()'),/Replace the N0CALL/);
    // A received saved schedule wins over generated text, timing and recurrence.
    run("messageScheduleReadback={data:{saved:{enabled:false,first_start_utc_ns:'1800000000000000000',period_s:1200,expires_utc_s:0,message:{message:'SAVED',mode:'qrss',frequency_nhz:'14096900000000000',space_frequency_nhz:'0',timing:{dot_ns:'1000000000',dash_ns:'3000000000',intra_gap_ns:'1000000000',character_gap_ns:'3000000000',word_gap_ns:'7000000000'},repeat_count:1,repeat_gap_ns:'3000000000'}}}}; adoptMessageSchedule(false); currentConfig.station.callsign='K2ABC'; defaultMessageDraft()");
    assert.equal(e['message-text'].value,'SAVED');
    assert.equal(e['message-interval'].value,20);
  }
  console.log('Source/shipped fresh defaults, explicit clears, edited drafts and saved CW preservation passed');
})().catch(error=>{console.error(error);process.exit(1);});
