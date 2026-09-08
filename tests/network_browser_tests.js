'use strict';
// Behavioral tests for the shipped browser script; no real browser, network or RF.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/../src/network/web/app.js','utf8');
async function fixture(activeConnections = true) {
    const ids = ['notice','refresh','reload-config','config','settings','wifi-off','job-settings','abort','release','state','output','clock','owner','engine','network','recovery','job','job-result','job-file','start'];
    const elements = Object.fromEntries(ids.map(id => [id,{disabled:false,value:'',textContent:'',classList:{toggle(){}},files:[]}]));
    elements.config.elements = Object.fromEntries(['callsign','locator','power_dbm','ssid','password','ntp_ipv4','enabled','schedules','expiry'].map(id => [id,{value:'',checked:false}]));
    const config = {version:1,enabled:false,station:{callsign:'AA0NT',locator:'EM18',power_dbm:37},wifi:{ssid:'test',password:null,ntp_ipv4:'192.0.2.1'},schedules:[{period_s:120,phase_s:0}],expires_utc_s:0};
    const state = {job:{state:'empty',owner_id:null,output_active:false,job_id:null},standalone:{reboot_required:false,storage_healthy:true,uncertainty_ns:'1000',clock_state:'synchronized',engine:'test'},network:{enabled:true,link_status:3,ipv4:'127.0.0.1'}};
    const calls = [];
    let sequence = 0;
    const f = {elements,state,calls,confirm:true,failArm:false,failConfig:false,offline:false};
    const context = vm.createContext({document:{getElementById:id=>elements[id]},crypto:{randomUUID:()=> (++sequence).toString(16).padStart(32,'0')},AbortSignal,Date,JSON,BigInt,Number,Error,confirm:()=>f.confirm,
        fetch:async (path, options) => {
            calls.push({path,options});
            if (f.offline) throw new Error('offline');
            let data, status = 200;
            if (path.endsWith('capabilities')) data = {active_job_connections:activeConnections,wtp:{maximum_arm_uncertainty_ns:'1000000'}};
            else if (path.endsWith('status')) data = structuredClone(state);
            else if (path.endsWith('config')) {
                if (options.method === 'PUT' && f.failConfig) { status = 412; data = {error:{code:'revision_conflict'}}; }
                else data = {config:structuredClone(config)};
            } else if (path.endsWith('jobs')) {
                const request = JSON.parse(options.body);
                if (request.operation === 'CLAIM') state.job.owner_id = request.body.owner_id;
                if (request.operation === 'LOAD') { state.job.state = 'loaded'; state.job.job_id = request.body.job_id; }
                if (request.operation === 'ABORT') { state.job.state = 'aborted'; state.job.output_active = false; }
                if (request.operation === 'RELEASE') state.job.owner_id = null;
                if (request.operation === 'ARM') {
                    if (f.failArm) { status = 409; data = {ok:false,error:{code:'ARM_TOO_LATE'}}; }
                    else state.job.state = 'armed';
                }
                data ||= {ok:true,result:{}};
            } else throw new Error('Unexpected request ' + path);
            return {ok:status===200,json:async()=>data,headers:{get:()=> '"original-revision"'}};
        }});
    vm.runInContext(source,context);
    await new Promise(setImmediate);
    f.context = context;
    f.form = elements.config.elements;
    f.configReads = () => calls.filter(c=>c.path.endsWith('config') && c.options.method==='GET').length;
    f.prepareJob = () => {
        elements['job-file'].files = [{size:100,text:async()=>JSON.stringify({job_id:'3'.repeat(32)})}];
        elements.start.value = new Date(Date.now()+60000).toISOString().slice(0,19);
    };
    return f;
}
(async () => {
    const f = await fixture();
    assert.equal(f.elements.settings.disabled,false);
    f.form.callsign.value = 'N0NEW'; f.form.password.value = 'unsaved-test-password'; f.elements.config.oninput();
    await f.elements.refresh.onclick();
    assert.equal(f.form.callsign.value,'N0NEW'); assert.equal(f.form.password.value,'unsaved-test-password'); assert.equal(f.configReads(),1);
    f.confirm = false; await f.elements['reload-config'].onclick(); assert.equal(f.form.callsign.value,'N0NEW');
    f.failConfig = true; await f.elements.config.onsubmit({preventDefault(){}});
    assert.match(f.elements.notice.textContent,/edits are preserved/); assert.equal(f.form.password.value,'unsaved-test-password'); assert.equal(f.configReads(),1);
    f.prepareJob(); f.failArm = true;
    await f.elements.job.onsubmit({preventDefault(){}});
    assert.equal(f.elements.abort.disabled,false); assert.equal(f.elements.release.disabled,false); assert.equal(f.elements['job-settings'].disabled,true);
    assert.match(f.elements.notice.textContent,/ARM_TOO_LATE/); assert.equal(f.form.callsign.value,'N0NEW');
    f.state.job.state = 'armed'; await f.elements.refresh.onclick(); assert.equal(f.elements.release.disabled,true);
    await f.elements.abort.onclick(); assert.match(f.elements['job-result'].textContent,/aborted/);
    await f.elements.release.onclick(); assert.match(f.elements['job-result'].textContent,/aborted/);
    f.state.job.state = 'complete'; await f.elements.refresh.onclick(); assert.match(f.elements['job-result'].textContent,/complete/);
    f.state.job.state = 'failed'; await f.elements.refresh.onclick(); assert.equal(f.elements.release.disabled,true);
    f.offline = true; await f.elements.refresh.onclick(); assert.equal(f.elements.settings.disabled,true); assert.equal(f.elements.abort.disabled,true);
    const rf = await fixture(false); rf.prepareJob();
    const statusReads = rf.calls.filter(c=>c.path.endsWith('status')).length;
    await rf.elements.job.onsubmit({preventDefault(){}});
    assert.equal(rf.calls.filter(c=>c.path.endsWith('status')).length,statusReads);
    assert.match(rf.elements.notice.textContent,/Job armed/); assert.match(rf.elements.notice.textContent,/USB Console ABORT/);
    assert.equal(rf.elements.abort.disabled,true);
    rf.offline = true; await rf.elements.refresh.onclick(); assert.match(rf.elements.notice.textContent,/New network connections pause/);
    assert.doesNotMatch(rf.elements.notice.textContent,/certificate/);
    console.log('Browser edit preservation, conflicts, ownership, failure and RF pause tests passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
