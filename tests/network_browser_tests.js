'use strict';
// Behavioral tests for the shipped browser script; no real browser, network or RF.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/../src/network/web/app.js','utf8');
async function fixture(activeConnections = true, configured = true, localMode = false, consumerMode = false, receipt = '') {
    const ids = ['saved-active-status','saved-readback-details','save-config','save-reconcile-status','saved-readback','read-saved','review-saved','login-recovery','inspect-logins','retire-login','retirement-target','retirement-status','retirement-password','local-logout','local-password-label','local-heading','local-description','consumer-identity-help','notice','local-access','local-login','local-password','local-status','restart','refresh','reload-config','config','settings','wifi-off','job-settings','abort','release','state','output','clock','owner','engine','network','hostname','discovery','discovery-help','recovery','job','job-result','job-file','start','message-settings','message-form','message-text','message-mode','message-frequency','message-shift','message-dot','message-repeats','message-gap','message-dash','message-intra','message-character','message-word','message-preview','message-start','job-progress','pin-settings','i2c-choices'];
    const elements = Object.fromEntries(ids.map(id => [id,{disabled:false,value:'',textContent:'',classList:{toggle(){}},files:[]}]));
    for (const id of ['consumer-setup','consumer-network-settings','consumer-station-settings',
      'consumer-check-save','consumer-network-form','consumer-station-form','consumer-ssid',
      'consumer-password','consumer-time-server','consumer-callsign','consumer-locator','consumer-return','consumer-save-status','consumer-resume'])
      elements[id] = {disabled:false,value:'',textContent:''};
    elements.config.elements = Object.fromEntries(['callsign','locator','power_dbm','ssid','password','ntp_ipv4','enabled','schedules','expiry'].map(id => [id,{value:'',checked:false}]));
    class Option { constructor(text,value) { this.text = text; this.value = String(value); this.disabled = false; } }
    class Select {
        constructor() { this.options = []; this.current = ''; }
        set value(value) { this.current = String(value); }
        get value() { return this.options.some(o=>o.value === this.current) ? this.current : ''; }
        get selectedOptions() { return this.options.filter(o=>o.value===this.value); }
        replaceChildren(...options) { this.options = options; this.current = options[0]?.value || ''; }
        addEventListener(type,callback) { this['on'+type] = callback; }
    }
    for (const key of ['rf_gp','button_gp','indicator','indicator_gp','indicator_active_high']) elements.config.elements[key] = new Select();
    elements['consumer-power'] = new Select();
    elements['retirement-target'] = new Select();
    elements.config.elements.indicator.replaceChildren(...['onboard_led','external','disabled'].map(x=>new Option(x,x)));
    elements.config.elements.indicator_active_high.replaceChildren(new Option('Active-high','true'),new Option('Active-low','false'));
    const config = {version:1,enabled:false,station:{callsign:'AA0NT',locator:'EM18',power_dbm:37},wifi:{ssid:'test',password:null,ntp_ipv4:'192.0.2.1'},schedules:[{period_s:120,phase_s:0}],expires_utc_s:0};
    const state = {job:{boot_id:'a'.repeat(32),state:'empty',owner_id:null,output_active:false,job_id:null},standalone:{reboot_required:false,storage_healthy:true,uncertainty_ns:'1000',clock_state:'synchronized',engine:'test'},network:{enabled:true,link_status:3,ipv4:'127.0.0.1'}};
    elements['config-password'] = elements.config.elements.password;
    elements['local-password-label'].textContent = 'Local-access password';
    for (const id of ['local-password','config-password','consumer-password','retirement-password']) {
        Object.assign(elements[id], {type:'password',selectionStart:0,selectionEnd:0,selectionDirection:'none',
            setSelectionRange(start,end,direction) { this.selectionStart=start;this.selectionEnd=end;this.selectionDirection=direction; }});
        elements[id+'-toggle'] = {attributes:{},setAttribute(name,value) { this.attributes[name]=value; }};
        elements[id+'-slash'] = {attributes:{hidden:true},toggleAttribute(name,value) { this.attributes[name]=value; }};
    }
    for (const e of Object.values(elements)) if (!e.addEventListener) e.addEventListener = function(type,callback) { (this.listeners ||= {})[type] = callback; };
    const calls = [];
    let sequence = 0;
    const f = {elements,state,calls,config,confirm:true,failArm:false,failConfig:false,offline:false,localMode,mappedSession:'d'.repeat(32),restartMode:'success',now:Date.now(),maximumDuration:'3600000000000',maximumEvents:512};
    class TestDate extends Date { static now() { return f.now; } }
    const context = vm.createContext({Option,document:{getElementById:id=>elements[id]},crypto:{randomUUID:()=> (++sequence).toString(16).padStart(32,'0')},AbortSignal,Date:TestDate,setTimeout:fn=>{f.now+=2000;fn();},JSON,BigInt,Number,Error,confirm:()=>f.confirm,
        fetch:async (path, options) => {
            calls.push({path,options});
            if (f.offline) throw new Error('offline');
            let data, status = 200;
            if (path === '/local/v1/identity') { status = f.localMode ? 200 : 404; data = f.localMode ? {device_id:'1'.repeat(32),surface:'normal'} : {error:{code:'not_found'}}; }
            else if (path === '/local/v1/status') data = {wtp_session:f.mappedSession};
            else if (path.endsWith('pins')) data = {choices:{eligible_gps:[...Array(23).keys(),26,27,28],i2c_pairs:[{controller:0,sda_gp:4,scl_gp:5}]}};
            else if (path.endsWith('application/2')) { status=404; data={error:{code:'not_found'}}; }
            else if (path.endsWith('application')) data = {target:{scope:'member',device_id:'1'.repeat(32),boot_id:state.job.boot_id},hardware:f.appHardware || {saved:config.pins || null,active:null,pending_restart:true,application_error:null}};
            else if (path.endsWith('capabilities')) data = {features:{restart:true},active_job_connections:activeConnections,message_jobs:{max_characters:32},wtp:{maximum_arm_uncertainty_ns:'1000000',max_job_duration_ns:f.maximumDuration,max_events:f.maximumEvents}};
            else if (path.endsWith('restart')) {
                if (f.restartMode === 'lost') throw new Error('lost restart response');
                if (f.restartMode === 'success') state.job.boot_id = 'b'.repeat(32);
                status = 202; data = {restart_requested:true};
            } else if (path.endsWith('status')) data = structuredClone(state);
            else if (path.endsWith('config')) {
                if (options.method === 'PUT' && f.configSaveMode) {
                    if (f.configSaveMode === 'before') throw new Error('lost before dispatch');
                    f.configCommits=(f.configCommits||0)+1;Object.assign(config,JSON.parse(options.body));
                    if (f.configSaveMode === 'lost') throw new Error('lost after commit');
                }
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
            return {ok:status>=200&&status<300,json:async()=>{if(path.endsWith('config') && options.method==='PUT'){if(f.configSaveMode==='json')throw new Error('lost body');if(f.configSaveMode==='empty')return {};if(f.configSaveMode==='wrong')return {config:'wrong'};if(f.configSaveMode==='expiry')return {config:{...data.config,expires_utc_s:'bad'}};if(f.configSaveMode==='pins')return {config:{...data.config,pins:{...data.config.pins,indicator:{}}}};if(f.configSaveMode==='null')return {config:null};}return data;},headers:{get:()=> '"original-revision"'}};
        }});
    f.events = {}; context.addEventListener=(name,handler)=>{f.events[name]=handler;};
    context.location={hash:receipt,pathname:'/',search:''};
    context.history={replaceState:(_,__,url)=>{context.location.hash=url.includes('#')?url.slice(url.indexOf('#')):'';}};
    if (consumerMode) {
        f.radio = {
            authenticated:false,
            identity:async()=>({device_id:'1'.repeat(32),boot_id:'a'.repeat(32),generation:'3'}),
            login:async()=>{ f.radio.authenticated=true; },
            request:async(path,method='GET',body)=>{
                if (!f.radio.authenticated) throw new Error('Log in again');
                return context.fetch('/api/v1/'+path,{method,body:body===undefined?undefined:JSON.stringify(body)});
            },
            prepareNetwork:async()=>({kind:'network',device:'1'.repeat(32),generation:'4',digest:'a'.repeat(64),submit:{secret:'must-not-survive'}}),
            submitSetup:async()=>{ f.setupSubmits=(f.setupSubmits||0)+1; f.radio.authenticated=false; throw new Error('reply lost'); },
            checkSetup:async()=> f.setupCheckResult || 'saved',
            logout:async()=>{ f.radio.authenticated=false; }
        };
        context.WsprryPicoConsumerRadio={createClient:()=>f.radio};
    }
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
    const visibility = await fixture(true,true,false,true);
    const password = visibility.elements['local-password'];
    password.value = 'Correctable 63-char draft: ' + 'x'.repeat(36);
    password.selectionStart=3;password.selectionEnd=11;password.selectionDirection='backward';
    const toggle=visibility.elements['local-password-toggle'], requests=visibility.calls.length;
    toggle.onclick();
    assert.equal(password.type,'text');
    assert.equal(password.value.length,63);
    assert.deepEqual([password.selectionStart,password.selectionEnd,password.selectionDirection],[3,11,'backward']);
    assert.equal(toggle.attributes['aria-label'],'Hide saved Wi-Fi password');
    assert.equal(toggle.attributes['aria-pressed'],'true');
    assert.equal(visibility.elements['local-password-slash'].attributes.hidden,false);
    assert.equal(visibility.elements['consumer-password'].type,'password');
    assert.equal(visibility.calls.length,requests); // No login, save or network operation.
    toggle.onclick();
    assert.equal(password.type,'password');assert.equal(password.value.length,63);
    visibility.elements['local-login'].onreset();
    assert.equal(toggle.attributes['aria-pressed'],'false');
    await visibility.elements['local-login'].onsubmit({preventDefault(){}});
    assert.equal(password.value,'');assert.equal(password.type,'password');
    const readonly=visibility.elements['config-password'];
    assert.equal(readonly.readOnly,true);
    visibility.elements['config-password-toggle'].onclick();
    assert.equal(readonly.type,'password');
    assert.equal(visibility.elements['config-password-toggle'].disabled,true);
    visibility.elements['consumer-password'].value='another private draft';
    visibility.elements['consumer-password-toggle'].onclick();
    assert.equal(visibility.elements['consumer-password'].type,'text');
    await visibility.elements['local-logout'].onclick();
    for (const id of ['local-password','config-password','consumer-password','retirement-password']) {
        assert.equal(visibility.elements[id].value,'');assert.equal(visibility.elements[id].type,'password');
        assert.equal(visibility.elements[id+'-toggle'].attributes['aria-pressed'],'false');
    }
    password.value='private page-exit draft';toggle.onclick();visibility.events.pagehide();
    assert.equal(password.value,'');assert.equal(password.type,'password');
    const rejectedPassword = await fixture(true,true,false,true);
    rejectedPassword.radio.login=async()=>{throw new Error('wrong password');};
    rejectedPassword.elements['local-password'].value='private rejected draft';
    rejectedPassword.elements['local-password-toggle'].onclick();
    await rejectedPassword.elements['local-login'].onsubmit({preventDefault(){}});
    assert.equal(rejectedPassword.elements['local-password'].value,'');
    assert.equal(rejectedPassword.elements['local-password'].type,'password');
    assert.equal(rejectedPassword.elements['local-password-toggle'].attributes['aria-pressed'],'false');
    const interruptedSetup = await fixture(true,true,false,true);
    interruptedSetup.elements['local-password'].value='test-password';
    await interruptedSetup.elements['local-login'].onsubmit({preventDefault(){}});
    interruptedSetup.elements['consumer-ssid'].value='preserved draft';
    interruptedSetup.elements['consumer-password'].value='test-password';
    interruptedSetup.elements['consumer-network-form'].oninput();
    await interruptedSetup.elements['consumer-network-form'].onsubmit({preventDefault(){}});
    assert.equal(interruptedSetup.setupSubmits,1);
    assert.equal(interruptedSetup.elements['local-login'].hidden,false);
    assert.equal(interruptedSetup.elements['consumer-check-save'].disabled,true);
    assert.equal(interruptedSetup.elements['consumer-password'].value,'');
    assert.equal(interruptedSetup.elements['consumer-ssid'].value,'preserved draft');
    const receipt = interruptedSetup.context.location.hash;
    assert.ok(receipt.startsWith('#save='));
    assert.doesNotMatch(decodeURIComponent(receipt),/test-password|must-not-survive|submit/);
    const resumed = await fixture(true,true,false,true,receipt);
    assert.equal(resumed.setupSubmits,undefined);
    assert.match(resumed.elements['consumer-save-status'].textContent,/receipt was recovered/);
    await resumed.elements['local-login'].onsubmit({preventDefault(){}});
    assert.equal(resumed.elements['consumer-network-settings'].disabled,true);
    await resumed.elements['consumer-check-save'].onclick();
    assert.equal(resumed.setupSubmits,undefined);
    assert.equal(resumed.context.location.hash,'');
    for (const malformed of ['#save=%','\n#save='+receipt.slice(6),receipt+'x',
      '#save='+encodeURIComponent(JSON.stringify({kind:'network',device:'1'.repeat(32),generation:'18446744073709551616',digest:'a'.repeat(64)}))]) {
        assert.equal(vm.runInContext('readSetupReceipt('+JSON.stringify(malformed)+')',resumed.context),null);
    }
    await interruptedSetup.elements['local-login'].onsubmit({preventDefault(){}});
    assert.equal(interruptedSetup.elements['consumer-check-save'].disabled,false);
    await interruptedSetup.elements['consumer-check-save'].onclick();
    assert.equal(interruptedSetup.setupSubmits,1);
    assert.match(interruptedSetup.elements['consumer-save-status'].textContent,/saved and verified/);
    const experimental = await fixture();
    experimental.config.allow_unqualified_frequency = true;
    experimental.config.allow_non_amateur_frequency = true;
    await experimental.elements['reload-config'].onclick();
    experimental.form.locator.value = 'FN42';
    await experimental.elements.config.onsubmit({preventDefault(){}});
    const experimentalSave = JSON.parse(experimental.calls.find(c=>c.path.endsWith('config') && c.options.method==='PUT').options.body);
    assert.equal(experimentalSave.allow_unqualified_frequency,true);
    assert.equal(experimentalSave.allow_non_amateur_frequency,true);
    const localPage = await fixture(true, true, true);
    assert.equal(vm.runInContext('session',localPage.context),localPage.mappedSession);
    assert.ok(localPage.calls.filter(c=>c.path.startsWith('/api/')).every(c=>c.options.headers['X-WsprryPico-Session']===localPage.mappedSession));
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
                assert.match(lost.elements.notice.textContent,/Outcome unconfirmed/);
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
    f.elements['config-password-toggle'].onclick();
    assert.equal(f.form.password.type,'text');
    f.failConfig = true; await f.elements.config.onsubmit({preventDefault(){}});
    assert.match(f.elements.notice.textContent,/edits are preserved/); assert.equal(f.form.password.value,'unsaved-test-password'); assert.equal(f.form.password.type,'password'); assert.equal(f.elements['config-password-toggle'].attributes['aria-pressed'],'false'); assert.equal(f.configReads(),1);
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
    const pins = await fixture();
    const form = pins.elements.config.elements;
    assert.equal(form.rf_gp.value,'2'); assert.equal(form.button_gp.value,'14');
    assert.equal(form.indicator.value,'onboard_led'); assert.equal(form.indicator_gp.disabled,true);
    assert.equal(form.button_gp.options.find(o=>o.value==='2').disabled,true);
    assert.equal(form.rf_gp.options.find(o=>o.value==='14').disabled,true);
    form.rf_gp.value='0'; form.rf_gp.onchange();
    form.indicator.value='external'; form.indicator.onchange();
    assert.notEqual(form.indicator_gp.value,'0'); assert.notEqual(form.indicator_gp.value,'14');
    assert.equal(form.indicator_gp.disabled,false);
    form.button_gp.value=''; form.button_gp.onchange();
    assert.equal(form.rf_gp.options.find(o=>o.value==='14').disabled,false);
    form.indicator.value='disabled'; form.indicator.onchange();
    assert.equal(form.indicator_gp.disabled,true);

    const localInvalid = await fixture();localInvalid.form.schedules.value='invalid';const localCount=localInvalid.calls.length;
    await localInvalid.elements.config.onsubmit({preventDefault(){}});assert.equal(localInvalid.calls.length,localCount);
    for (const mode of ['before','lost','json','empty','wrong','expiry','pins','null']) {
        const uncertain=await fixture();uncertain.form.schedules.value='240 / 0';uncertain.elements.config.oninput();uncertain.configSaveMode=mode;
        await uncertain.elements.config.onsubmit({preventDefault(){}});
        assert.equal(uncertain.form.schedules.value,'240 / 0');assert.equal(uncertain.configCommits||0,mode==='before'?0:1);
        assert.equal(uncertain.elements['save-config'].disabled,true);assert.equal(vm.runInContext('writeState',uncertain.context),'readback');
        await uncertain.elements.refresh.onclick();assert.equal(uncertain.elements['save-config'].disabled,true);
        uncertain.configSaveMode=null;await uncertain.elements['read-saved'].onclick();assert.equal(uncertain.elements['save-config'].disabled,true);
        assert.equal(uncertain.form.schedules.value,'240 / 0');assert.match(uncertain.elements['saved-readback'].textContent,/"active": null/);
        await uncertain.elements['review-saved'].onclick();assert.equal(uncertain.elements['save-config'].disabled,false);
    }
    for (const expires of [2208988800,4102444799]) {
        const future=await fixture();future.config.expires_utc_s=expires;await future.elements['reload-config'].onclick();assert.ok(future.form.expiry.value.startsWith(expires===2208988800?'2040':'2099'));
        future.form.schedules.value='240 / 0';future.elements.config.oninput();await future.elements['read-saved'].onclick();assert.equal(future.form.schedules.value,'240 / 0');await future.elements['review-saved'].onclick();assert.equal(future.elements['save-config'].disabled,false);
    }
    const changed=await fixture(true,true,false,true);changed.elements['local-password'].value='test-password';await changed.elements['local-login'].onsubmit({preventDefault(){}});
    changed.form.schedules.value='240 / 0';changed.elements.config.oninput();changed.config.station={callsign:'K1ABC',locator:'FN42',power_dbm:30};changed.config.wifi={ssid:'new-network',password:null,ntp_ipv4:'pool.ntp.org'};
    await changed.elements['read-saved'].onclick();await changed.elements['review-saved'].onclick();await changed.elements.config.onsubmit({preventDefault(){}});
    const outgoing=JSON.parse(changed.calls.filter(c=>c.path.endsWith('config')&&c.options.method==='PUT').at(-1).options.body);
    assert.equal(outgoing.station.callsign,'K1ABC');assert.equal(outgoing.wifi.ssid,'new-network');assert.equal(outgoing.schedules[0].period_s,240);
    console.log('Browser edit preservation, conflicts, ownership, failure and RF pause tests passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
