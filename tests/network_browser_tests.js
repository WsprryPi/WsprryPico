'use strict';
// Behavioral tests for the shipped browser script; no real browser, network or RF.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/../src/network/web/app.js','utf8');
async function fixture(activeConnections = true, configured = true) {
    const ids = ['notice','restart','refresh','reload-config','config','settings','wifi-off','job-settings','abort','release','state','output','clock','owner','engine','network','hostname','discovery','discovery-help','recovery','job','job-result','job-file','start','message-settings','message-form','message-text','message-mode','message-frequency','message-shift','message-dot','message-repeats','message-gap','message-dash','message-intra','message-character','message-word','message-preview','message-start','job-progress'];
    const elements = Object.fromEntries(ids.map(id => [id,{disabled:false,value:'',textContent:'',classList:{toggle(){}},files:[]}]));
    elements.config.elements = Object.fromEntries(['callsign','locator','power_dbm','ssid','password','ntp_ipv4','enabled','schedules','expiry'].map(id => [id,{value:'',checked:false}]));
    const config = {version:1,enabled:false,station:{callsign:'AA0NT',locator:'EM18',power_dbm:37},wifi:{ssid:'test',password:null,ntp_ipv4:'192.0.2.1'},schedules:[{period_s:120,phase_s:0}],expires_utc_s:0};
    const state = {job:{boot_id:'a'.repeat(32),state:'empty',owner_id:null,output_active:false,job_id:null},standalone:{reboot_required:false,storage_healthy:true,uncertainty_ns:'1000',clock_state:'synchronized',engine:'test'},network:{enabled:true,link_status:3,ipv4:'127.0.0.1'}};
    const calls = [];
    let sequence = 0;
    const f = {elements,state,calls,confirm:true,failArm:false,failConfig:false,offline:false, restartMode:'success', now:Date.now(), maximumDuration:'3600000000000',maximumEvents:512};
    class TestDate extends Date { static now() { return f.now; } }
    const context = vm.createContext({document:{getElementById:id=>elements[id]},crypto:{randomUUID:()=> (++sequence).toString(16).padStart(32,'0')},AbortSignal,Date:TestDate,setTimeout:fn=>{f.now+=2000;fn();},JSON,BigInt,Number,Error,confirm:()=>f.confirm,
        fetch:async (path, options) => {
            calls.push({path,options});
            if (f.offline) throw new Error('offline');
            let data, status = 200;
            if (path.endsWith('capabilities')) data = {features:{restart:true},active_job_connections:activeConnections,message_jobs:{max_characters:32},wtp:{maximum_arm_uncertainty_ns:'1000000',max_job_duration_ns:f.maximumDuration,max_events:f.maximumEvents}};
            else if (path.endsWith('restart')) {
                if (f.restartMode === 'lost') throw new Error('lost restart response');
                if (f.restartMode === 'success') state.job.boot_id = 'b'.repeat(32);
                status = 202; data = {restart_requested:true};
            } else if (path.endsWith('status')) data = structuredClone(state);
            else if (path.endsWith('config')) {
                if (options.method === 'PUT' && f.failConfig) { status = 412; data = {error:{code:'revision_conflict'}}; }
                else data = {config:configured ? structuredClone(config) : null};
            } else if (path.endsWith('jobs')) {
                const request = JSON.parse(options.body);
                if (request.operation === 'CLAIM') state.job.owner_id = request.body.owner_id;
                if (['LOAD','LOAD_MESSAGE'].includes(request.operation)) { state.job.state = 'loaded'; state.job.job_id = request.body.job_id; }
                if (request.operation === 'ABORT') { state.job.state = 'aborted'; state.job.output_active = false; }
                if (request.operation === 'RELEASE') state.job.owner_id = null;
                if (request.operation === 'ARM') {
                    if (f.failArm) { status = 409; data = {ok:false,error:{code:'ARM_TOO_LATE'}}; }
                    else state.job.state = 'armed';
                }
                data ||= {ok:true,result:{}};
                if (f.loseOperation === request.operation) {
                    f.offline = !!f.offlineAfterLoss;
                    throw new Error('lost ' + request.operation + ' response');
                }
            } else throw new Error('Unexpected request ' + path);
            return {ok:status>=200&&status<300,json:async()=>data,headers:{get:()=> '"original-revision"'}};
        }});
    vm.runInContext(source,context);
    await new Promise(setImmediate);
    f.context = context;
    f.form = elements.config.elements;
    f.configReads = () => calls.filter(c=>c.path.endsWith('config') && c.options.method==='GET').length;
    f.prepareJob = () => {
        elements['job-file'].files = [{size:100,text:async()=>JSON.stringify({job_id:'3'.repeat(32),total_duration_ns:'1000000000',events:[{}]})}];
        elements.start.value = new Date(Date.now()+60000).toISOString().slice(0,19);
    };
    f.prepareMessage = (mode='qrss',text='E') => {
        const values = {text,mode,frequency:'135500',shift:'5',dot:'3',repeats:'1',gap:'1',dash:'3',intra:'1',character:'3',word:'7',start:new Date(f.now+60000).toISOString().slice(0,19)};
        for (const [key,value] of Object.entries(values)) elements['message-'+key].value=value;
    };
    return f;
}
(async () => {
    const message = await fixture();
    assert.equal(vm.runInContext('durationText(1719000001000n)',message.context),'28 min 39.000001 s');
    assert.equal(vm.runInContext('durationText(3600000000001n)',message.context),'60 min 0.000000001 s');
    for (const mode of ['qrss','fskcw','dfcw']) {
        for (const count of [31,32]) {
            message.prepareMessage(mode,'?'.repeat(count));
            const plan = vm.runInContext('messagePlan()',message.context);
            assert.equal(plan.events,count*12);
            assert.equal(plan.duration,BigInt((count*(mode==='dfcw'?14:18)-3)*3)*1000000000n+1000n);
        }
        for (const text of ['?'.repeat(33),' '.repeat(32)+'E']) {
            message.prepareMessage(mode,text);
            assert.throws(()=>vm.runInContext('messagePlan()',message.context),/32 characters/);
            assert.equal(message.elements['message-text'].value,text);
        }
        message.prepareMessage(mode,' '.repeat(31)+'E');
        assert.equal(vm.runInContext('messagePlan().events',message.context),2);
    }
    message.prepareMessage();
    for (const [dot,expected] of [['3599.999998999',3599999999999n],['3599.999999',3600000000000n]]) {
        message.elements['message-dot'].value=dot;
        assert.equal(vm.runInContext('messagePlan().duration',message.context),expected);
    }
    message.elements['message-dot'].value='3599.999999001';
    assert.throws(()=>vm.runInContext('messagePlan()',message.context),/Maximum: 60 min/);
    message.prepareMessage(); message.elements['message-dot'].value='1';
    message.elements['message-repeats'].value='256';
    assert.equal(vm.runInContext('messagePlan().events',message.context),512);
    message.elements['message-repeats'].value='257';
    assert.throws(()=>vm.runInContext('messagePlan()',message.context),/514 events/);
    message.prepareMessage(); message.elements['message-dot'].value='3599.999999';
    await message.elements['message-form'].onsubmit({preventDefault(){}});
    assert.deepEqual(message.calls.filter(c=>c.path.endsWith('jobs')).map(c=>JSON.parse(c.options.body).operation),['HELLO','CLAIM','LOAD_MESSAGE','ARM']);
    const arm=JSON.parse(message.calls.filter(c=>c.path.endsWith('jobs')).at(-1).options.body);
    message.state.job.state='running';message.state.job.output_active=true;
    message.state.standalone.utc_now_ns=(BigInt(arm.body.start_utc_ns)+1800000000000n).toString();
    await message.elements.refresh.onclick();
    assert.match(message.elements['job-progress'].textContent,/50.0%/);
    assert.equal(message.elements.abort.disabled,false);
    message.state.standalone.utc_now_ns=(BigInt(arm.body.start_utc_ns)+4000000000000n).toString();
    await message.elements.refresh.onclick();
    assert.match(message.elements['job-progress'].textContent,/Running.*100.0%/);
    assert.equal(message.elements.output.textContent,'Active');
    message.offline=true; await message.elements.refresh.onclick();
    assert.match(message.elements['job-progress'].textContent,/status unknown/);
    message.offline=false;message.state.job.boot_id='c'.repeat(32);message.maximumDuration='110592000000';message.maximumEvents=162;
    await message.elements.refresh.onclick();
    assert.equal(message.elements['job-progress'].textContent,'');
    assert.throws(()=>vm.runInContext('messagePlan()',message.context),/Maximum: 1 min 50.592 s/);
    message.prepareMessage('qrss','?'.repeat(32));message.elements['message-dot'].value='0.1';
    assert.throws(()=>vm.runInContext('messagePlan()',message.context),/device limit of 162/);
    const pause = await fixture(false);pause.prepareMessage();
    await pause.elements['message-form'].onsubmit({preventDefault(){}});
    assert.match(pause.elements.notice.textContent,/New network connections pause/);
    for (const operation of ['LOAD_MESSAGE','ARM']) {
        const lost=await fixture();lost.prepareMessage();lost.loseOperation=operation;lost.offlineAfterLoss=true;
        await lost.elements['message-form'].onsubmit({preventDefault(){}});
        assert.equal(lost.calls.filter(c=>c.path.endsWith('jobs') && JSON.parse(c.options.body).operation===operation).length,1);
        assert.equal(lost.elements.output.textContent,'Unknown');
    }
    for (const operation of ['CLAIM','LOAD','ARM']) {
        for (const offline of [false,true]) {
            const lost = await fixture(); lost.prepareJob();
            lost.loseOperation = operation; lost.offlineAfterLoss = offline;
            await lost.elements.job.onsubmit({preventDefault(){}});
            const operations = lost.calls.filter(c=>c.path.endsWith('jobs')).map(c=>JSON.parse(c.options.body).operation);
            assert.deepEqual(operations,['HELLO','CLAIM','LOAD','ARM'].slice(0,['CLAIM','LOAD','ARM'].indexOf(operation)+2));
            assert.equal(lost.elements['job-settings'].disabled,true);
            assert.match(lost.elements.notice.textContent,new RegExp('lost ' + operation));
            if (offline) {
                assert.equal(lost.elements.output.textContent,'Unknown');
                assert.equal(lost.elements.abort.disabled,true);
                assert.equal(lost.elements.release.disabled,true);
                assert.match(lost.elements.notice.textContent,/Status remains unknown/);
                assert.doesNotMatch(lost.elements.notice.textContent,/Status has been checked/);
            }
        }
    }
    const unknown = await fixture();
    for (const output of [null,undefined,true]) {
        unknown.state.job.output_active = output;
        await unknown.elements.refresh.onclick();
        assert.equal(unknown.elements['job-settings'].disabled,true);
    }
    const ownUnknown = await fixture(); ownUnknown.prepareJob(); ownUnknown.failArm = true;
    await ownUnknown.elements.job.onsubmit({preventDefault(){}});
    ownUnknown.state.job.output_active = null;
    await ownUnknown.elements.refresh.onclick();
    assert.equal(ownUnknown.elements.release.disabled,true);
    for (const state of ['loaded','armed','running']) {
        const foreign = await fixture(); foreign.state.job.owner_id = 'f'.repeat(32); foreign.state.job.state = state;
        await foreign.elements.refresh.onclick();
        for (const control of ['abort','release','job-settings','settings']) assert.equal(foreign.elements[control].disabled,true);
    }
    const fresh = await fixture(true, false);
    assert.equal(fresh.form.ntp_ipv4.value,'pool.ntp.org');
    const f = await fixture();
    assert.equal(f.form.ntp_ipv4.value,'192.0.2.1');
    assert.equal(f.elements.settings.disabled,false);
    f.form.callsign.value = 'N0NEW'; f.form.password.value = 'unsaved-test-password'; f.elements.config.oninput();
    await f.elements.refresh.onclick();
    assert.equal(f.form.callsign.value,'N0NEW'); assert.equal(f.form.password.value,'unsaved-test-password'); assert.equal(f.configReads(),1);
    f.confirm = false; await f.elements['reload-config'].onclick(); assert.equal(f.form.callsign.value,'N0NEW');
    f.failConfig = true; await f.elements.config.onsubmit({preventDefault(){}});
    assert.match(f.elements.notice.textContent,/edits are preserved/); assert.equal(f.form.password.value,'unsaved-test-password'); assert.equal(f.configReads(),1);
    f.state.network.configured_hostname = 'wsprrypico-' + 'a'.repeat(32) + '.local';
    for (const state of ['active','conflict','failed','probing','waiting_address']) {
        f.state.network.mdns_state = state; await f.elements.refresh.onclick();
        assert.equal(f.form.callsign.value,'N0NEW');
        assert.equal(f.form.password.value,'unsaved-test-password');
        assert.equal(f.elements.hostname.textContent,f.state.network.configured_hostname);
    }
    f.state.network.mdns_state = 'conflict'; await f.elements.refresh.onclick();
    assert.match(f.elements['discovery-help'].textContent,/will not rename/);
    f.prepareJob(); f.failArm = true;
    await f.elements.job.onsubmit({preventDefault(){}});
    assert.equal(f.elements.abort.disabled,false); assert.equal(f.elements.release.disabled,false); assert.equal(f.elements['job-settings'].disabled,true);
    assert.match(f.elements.notice.textContent,/ARM_TOO_LATE/); assert.equal(f.form.callsign.value,'N0NEW');
    f.state.job.state = 'armed'; await f.elements.refresh.onclick(); assert.equal(f.elements.release.disabled,true);
    await f.elements.abort.onclick(); assert.match(f.elements['job-result'].textContent,/aborted/);
    await f.elements.release.onclick(); assert.match(f.elements['job-result'].textContent,/aborted/);
    f.state.job.state = 'complete'; await f.elements.refresh.onclick(); assert.match(f.elements['job-result'].textContent,/complete/);
    f.state.job.state = 'failed'; await f.elements.refresh.onclick(); assert.equal(f.elements.release.disabled,true);
    f.offline = true; await f.elements.refresh.onclick(); assert.equal(f.elements.hostname.textContent,'Unknown'); assert.equal(f.elements.discovery.textContent,'Unknown'); assert.equal(f.elements.settings.disabled,true); assert.equal(f.elements.abort.disabled,true);
    const rf = await fixture(false); rf.prepareJob();
    const statusReads = rf.calls.filter(c=>c.path.endsWith('status')).length;
    await rf.elements.job.onsubmit({preventDefault(){}});
    assert.equal(rf.calls.filter(c=>c.path.endsWith('status')).length,statusReads);
    assert.match(rf.elements.notice.textContent,/Job armed/); assert.match(rf.elements.notice.textContent,/USB Console ABORT/);
    assert.equal(rf.elements.abort.disabled,true);
    rf.offline = true; await rf.elements.refresh.onclick(); assert.match(rf.elements.notice.textContent,/New network connections pause/);
    assert.doesNotMatch(rf.elements.notice.textContent,/certificate/);
    const reboot = await fixture();
    await reboot.elements.restart.onclick();
    assert.match(reboot.elements.notice.textContent,/Device restarted/);
    assert.equal(reboot.calls.filter(c=>c.path.endsWith('restart')).length,1);
    for (const mode of ['lost','unchanged']) {
        const failed = await fixture(); failed.restartMode = mode;
        await failed.elements.restart.onclick();
        assert.equal(failed.calls.filter(c=>c.path.endsWith('restart')).length,1);
        assert.doesNotMatch(failed.elements.notice.textContent,/Device restarted/);
        assert.match(failed.elements.notice.textContent,mode==='lost'?/lost restart response/:/Restart not confirmed/);
    }
    reboot.state.job.owner_id = 'c'.repeat(32); await reboot.elements.refresh.onclick();
    assert.equal(reboot.elements.restart.disabled,true);
    console.log('Browser edit preservation, conflicts, ownership, failure and RF pause tests passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
