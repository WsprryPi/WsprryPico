'use strict';
// Behavioral tests for the shipped browser script; no real browser, network or RF.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const scripts = process.env.WSPRRY_PICO_BROWSER_SHIPPED ? ['device-presentation.min.js','config-validation.min.js','app.min.js'] : ['operations.js','device-presentation.js','saved-progress.js','config-validation.js','utc-datetime.js','message-schedule.js','app.js'];
const source = scripts.map(name=>fs.readFileSync(__dirname + '/../src/network/web/'+name,'utf8')).join('\n');
async function fixture(activeConnections = true, configured = true, localMode = false, consumerMode = false, receipt = '', organizationMode = false, options = {}) {
    const ids = ['device-name','device-name-state','device-id','device-boot','apply-engineering-station-progress','apply-engineering-network-progress','save-engineering-network-progress','progress-engineering-station-status','progress-engineering-network-status','apply-progress','apply-station-progress','save-station-progress','save-engineering-station-progress','progress-settings-status','progress-station-status','settings-save-help','station-area','wifi-host-area','station-link','wifi-host-link','initial-config','engineering-station-form','engineering-station-settings','engineering-network-form','engineering-network-settings','hostname-review','hostname-form','hostname-settings','hostname-input','hostname-help','hostname-status','hostname-save','hostname-default','restart-status','restart-cancel','hostname-continue','saved-active-status','saved-readback-details','save-config','save-reconcile-status','saved-readback','read-saved','review-saved','login-recovery','inspect-logins','retire-login','retirement-target','retirement-status','retirement-password','local-logout','local-password-label','local-heading','local-description','consumer-identity-help','notice','local-access','local-login','local-password','local-status','restart','refresh','reload-config','config','settings','wifi-off','job-settings','abort','release','state','output','clock','owner','network','hostname','discovery-help','recovery','job','job-result','job-file','start','message-settings','message-form','message-text','message-mode','message-frequency','message-shift','message-dot','message-repeats','message-gap','message-dash','message-intra','message-character','message-word','message-preview','message-start','job-progress','pin-settings','unused-i2c-choices'];
    ids.push('settings-actions','setup-result-reveal','settings-recovery-access','network-save-result','station-save-result','consumer-save-recovery','setup-recovery-access','amplifier-pin-settings','radio-result-reveal','radio-pins','save-pins','pins-status','station-settings-lock','wifi-settings-lock');
    ids.push('access-toggle','access-state','access-shackle','access-close','login-submit','recovery-reveal','top','status-heading','section-menu','station-identity','radio-settings','time-calibration','message-section','wifi-settings','pico-password-section','hostname-section','connection-section','saved-settings','device-diagnostics');
    ids.push('console-state','console-warning','console-announcement','console-mode','console-frequency','console-message','console-progress','console-next','console-next-item','console-correction','console-reset','console-actions');
    ids.push('pico-password-form','pico-password-settings','pico-password-default','pico-password-status','pico-password-help','pico-password-error','pico-new-password','pico-confirm-password','draft-comparison','message-availability','jump-identity','jump-settings','jump-message','engineering-identity-heading','consumer-identity-heading','radio-settings-heading','job-heading','hostname-error');
    ids.push('message-frequency-label','message-frequency-help','message-shift-help','message-result');
    ids.push('schedule-save-help','standalone-status');
    ids.push('public-status-note','message-duration','message-scheduling','message-delivery','message-recurrence','message-interval','message-until','message-submit','message-schedule-controls','message-schedule-status','message-schedule-read','message-schedule-adopt','message-schedule-pause','message-schedule-help');
    const elements = Object.fromEntries(ids.map(id => [id,{disabled:false,value:'',textContent:'',classList:{toggle(){}},files:[]}]));
    elements['message-delivery'].value='once';elements['message-interval'].value='20';
    elements['message-mode'].value='qrss'; // Native select initially selects its first option.
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
    for (const key of ['rf_gp','button_gp','amplifier_gp','amplifier_active_high','indicator','indicator_gp','indicator_active_high']) elements.config.elements[key] = new Select();
    elements['consumer-power'] = new Select();
    elements['retirement-target'] = new Select();
    elements.config.elements.indicator.replaceChildren(...['onboard_led','external','disabled'].map(x=>new Option(x,x)));
    elements.config.elements.indicator_active_high.replaceChildren(new Option('Active-high','true'),new Option('Active-low','false'));
    elements.config.elements.amplifier_active_high.replaceChildren(new Option('Active-high','true'),new Option('Active-low','false'));
    const makeNode = tag => ({tag,children:[],ownText:'',attributes:{},classList:{toggle(){}},
      get textContent(){return this.ownText+this.children.map(n=>typeof n==='string'?n:n.textContent).join(' ');},
      set textContent(value){this.ownText=String(value);this.children=[];},
      append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.ownText='';this.children=nodes;},
      setAttribute(key,value){this.attributes[key]=value;},getAttribute(key){return this.attributes[key]||null;}});
    elements['draft-comparison']=makeNode('div');
    const config = {version:1,enabled:false,station:{callsign:'AA0NT',locator:'EM18',power_dbm:37},wifi:{ssid:'test',password:null,ntp_ipv4:'192.0.2.1'},schedules:[{period_s:120,phase_s:0}],expires_utc_s:0};
    const state = {job:{boot_id:'a'.repeat(32),state:'empty',owner_id:null,output_active:false,job_id:null},standalone:{reboot_required:false,storage_healthy:true,uncertainty_ns:'1000',clock_state:'synchronized',engine:'test'},network:{enabled:true,link_status:3,ipv4:'127.0.0.1',configured_hostname:'old.local'}};
    elements['config-password'] = elements.config.elements.password;
    elements['local-password-label'].textContent = 'Local-access password';
    for (const id of ['local-password','config-password','consumer-password','retirement-password','pico-new-password','pico-confirm-password']) {
        Object.assign(elements[id], {type:'password',selectionStart:0,selectionEnd:0,selectionDirection:'none',
            setSelectionRange(start,end,direction) { this.selectionStart=start;this.selectionEnd=end;this.selectionDirection=direction; }});
        elements[id+'-toggle'] = {attributes:{},setAttribute(name,value) { this.attributes[name]=value; }};
        elements[id+'-slash'] = {attributes:{hidden:true},toggleAttribute(name,value) { this.attributes[name]=value; }};
    }
    for (const e of Object.values(elements)) if (!e.addEventListener) e.addEventListener = function(type,callback) { (this.listeners ||= {})[type] = callback; };
    for (const [id,e] of Object.entries(elements)) {
      if (!e.focus) e.focus=()=>{elements.focused=id;};
      e.scrollIntoView ||= ()=>{};
    }
    for (const e of [...Object.values(elements),...Object.values(elements.config.elements)]) {
      e.attributes ||= {};e.setAttribute ||= function(k,v){this.attributes[k]=v;};
      e.getAttribute ||= function(k){return this.attributes[k]||null;};
    }
    elements['local-access'].showModal=function(){this.open=true;};
    elements['local-access'].close=function(){this.open=false;};
    const navigationLinks=[];
    for(const [id,area] of [['radio-settings','station'],['time-calibration','station'],['message-section','station'],['wifi-settings','wifi-host'],['pico-password-section','wifi-host'],['hostname-section','wifi-host'],['connection-section','wifi-host'],['saved-settings',null],['device-diagnostics',null]]) {
      const e=elements[id];e.tagName='DETAILS';e.open=false;e.contains=()=>false;e.querySelectorAll=()=>[];
      e.parentElement=area ? elements[area==='station'?'station-area':'wifi-host-area'] : null;
      e.querySelector=()=>({focus:()=>{elements.focused=id+'-summary';}});
      e.closest=()=>e.parentElement;
      if(e.parentElement)e.parentElement.getAttribute=()=>area;
      navigationLinks.push({getAttribute:()=> (area?'/'+area:'')+'#'+id,addEventListener(type,callback){this[type]=callback;}});
    }
    const calls = [];
    let sequence = 0;
    const f = {elements,state,calls,config,confirm:true,failArm:false,failConfig:false,offline:false,localMode,mappedSession:'d'.repeat(32),restartMode:'success',now:Date.now(),maximumDuration:'3600000000000',maximumEvents:512,...options};
    class TestDate extends Date { static now() { return f.now; } }
    elements['station-link'].getAttribute=()=>'/station';
    elements['wifi-host-link'].getAttribute=()=>'/wifi-host';
    for(const id of ['station-link','wifi-host-link']) elements[id].setAttribute=function(name,value){this[name]=value;};
    for(const input of Object.values(elements.config.elements)) input.reportValidity=()=>true;
    for(const [id,names] of [['engineering-station-form',['callsign','locator','power_dbm']],['engineering-network-form',['ssid','password','ntp_ipv4']],['config',['schedules','expiry']]])
      elements[id].querySelectorAll=()=>names.map(name=>elements.config.elements[name]);
    const context = vm.createContext({Option,URL,URLSearchParams,document:{getElementById:id=>elements[id],createElement:makeNode,addEventListener(){},querySelectorAll:selector=>selector==='a[href]' ? [elements['station-link'],elements['wifi-host-link'],...navigationLinks] : ['.field-result','[aria-invalid]'].includes(selector)?[]:[elements['station-link'],elements['wifi-host-link']]},crypto:{randomUUID:()=> (++sequence).toString(16).padStart(32,'0')},AbortSignal,Date:TestDate,setTimeout:fn=>{f.now+=2000;fn();},JSON,BigInt,Number,Error,confirm:()=>{if(f.confirmAdvance)f.now+=f.confirmAdvance;return f.confirm;},
        fetch:async (path, options) => {
            calls.push({path,options});
            if(f.expireResetRead&&path.endsWith('config')&&options.method==='GET'){f.expireResetRead=false;f.now+=16000;vm.runInContext('consoleTick()',context);}
            if (f.offline) throw new Error('offline');
            let data, status = 200;
            if (path === '/local/v1/identity' && f.localDiscoveryFailure) throw new Error('synthetic discovery timeout');
            if (['/local/v1/logout','/local/v1/login'].includes(path)) data={ok:true};
            else if (path === '/local/v1/identity') { status = f.localMode ? 200 : 404; data = f.localMode ? {device_id:'1'.repeat(32),surface:'normal'} : {error:{code:'not_found'}}; }
            else if (path === '/local/v1/status') data = {wtp_session:f.mappedSession};
            else if (path.endsWith('hostname')) {
                if (options.method === 'PUT') { f.savedHostname=JSON.parse(options.body).hostname; f.hostnameGeneration=(f.hostnameGeneration||1)+1; }
                data = {schema:'transmitter-hostname/1',target:{scope:'member',device_id:f.hostnameDevice||'1'.repeat(32),boot_id:state.job.boot_id},
                    saved:f.savedHostname||state.network.configured_hostname,active:state.network.configured_hostname,default:'default.local',writable:true,pending_restart:!!f.savedHostname&&f.savedHostname!==state.network.configured_hostname,reason:'',generation:String(f.hostnameGeneration||1),storage_healthy:true};
            }
            else if (path.endsWith('hardware')) data={schema:'transmitter-hardware/1',target:{scope:'member',device_id:'1'.repeat(32),boot_id:state.job.boot_id},saved:config.pins||null,saved_generation:'1',active:null,active_revision:null,pending_restart:false,application_error:null,execution_engine:'simulated',storage_healthy:true};
            else if (path.endsWith('message-schedule')||path.endsWith('message-schedule/pause')) {
                if (options.method==='GET' && f.scheduleReadFailure) throw new Error('schedule read unavailable');
                if (options.method==='PUT') {
                    f.scheduleSaves=(f.scheduleSaves||0)+1;f.savedMessageSchedule=JSON.parse(options.body).schedule;
                    if (f.loseScheduleSave) throw new Error('reply lost after save');
                }
                if (path.endsWith('/pause')) {
                    if(f.savedMessageSchedule && !f.schedulePausePending)f.savedMessageSchedule.enabled=false;
                    if(f.loseSchedulePause)throw new Error('reply lost after pause');
                }
                data={schema:'transmitter-message-schedule/1',target:{scope:'member',device_id:'1'.repeat(32),boot_id:state.job.boot_id},saved:f.savedMessageSchedule||null,writable:true,state:f.scheduleState||(f.savedMessageSchedule?(f.savedMessageSchedule.enabled?'waiting':'paused'):'not_configured'),pause_pending:!!f.schedulePausePending,next_start_utc_ns:null,last_start_utc_ns:null,last_job_id:null,last_result:null,last_error:null};
            }
            else if (path.endsWith('pins')) data = {choices:{eligible_gps:[...Array(23).keys(),26,27,28],i2c_pairs:[{controller:0,sda_gp:4,scl_gp:5}]}};
            else if (path.endsWith('application/2')) { if(f.appV2) data=f.appV2; else {status=404; data={error:{code:'not_found'}};} }
            else if (path.endsWith('application')) data = {target:{scope:'member',device_id:'1'.repeat(32),boot_id:state.job.boot_id},hardware:f.appHardware || {saved:config.pins || null,active:null,pending_restart:true,application_error:null}};
            else if (path.endsWith('capabilities')) data = {...(f.operations?{operations_status:{schema:'transmitter-operations/1',path:'/api/v1/operations'}}:{}),...(f.scheduleSupport?{message_schedule:{schema:'transmitter-message-schedule/1',path:'/api/v1/message-schedule',pause:'/api/v1/message-schedule/pause',min_period_s:60,max_period_s:86400,preparation_lead_ns:'2000000000',max_storage_bytes:1984}}:{}),configuration_updates:{schema:'transmitter-config-update/1',path:'/api/v1/config/update',method:'POST',modes:['merge','replace']},features:{restart:true},active_job_connections:activeConnections,message_jobs:{max_characters:32},wtp:{maximum_arm_uncertainty_ns:'1000000',max_job_duration_ns:f.maximumDuration,max_events:f.maximumEvents}};
            else if (path.endsWith('restart')) {
                if (f.restartMode === 'lost') throw new Error('lost restart response');
                if (f.restartMode === 'success') { state.job.boot_id = 'b'.repeat(32); if(f.operations) f.operations.target.boot_id=f.operations.job.boot_id=f.operations.standalone.boot_id=state.job.boot_id; }
                status = 202; data = {restart_requested:true};
            } else if (path.endsWith('consumer/password')) data = {schema:'pico-password/1',target:{scope:'member',device_id:'1'.repeat(32),boot_id:'a'.repeat(32)},wifi_default:true,saved:true};
            else if(path.endsWith('operations')) { if(f.delayObservation) await f.delayObservation; data=structuredClone(f.operations); }
            else if (path.endsWith('status')) data = structuredClone(state);
            else if (path.endsWith('config/update')) {
                const patch=JSON.parse(options.body).config;
                if(patch.station)Object.assign(config.station,patch.station);
                if(patch.wifi)Object.assign(config.wifi,patch.wifi,{password:null});
                data={config:structuredClone(config)};
            }
            else if (path.endsWith('config')) {
                if (options.method === 'PUT' && f.configSaveMode) {
                    if (f.configSaveMode === 'before') throw new Error('lost before dispatch');
                    f.configCommits=(f.configCommits||0)+1;Object.assign(config,JSON.parse(options.body));
                    if (f.configSaveMode === 'lost') throw new Error('lost after commit');
                }
                if (options.method === 'PUT' && f.failConfig) { status = 412; data = {error:{code:'revision_conflict'}}; }
                else data = {config:configured || options.method === 'PUT' ? structuredClone(config) : null};
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
            return {status,ok:status>=200&&status<300,json:async()=>{if(path.endsWith('config') && options.method==='PUT'){if(f.configSaveMode==='json')throw new Error('lost body');if(f.configSaveMode==='empty')return {};if(f.configSaveMode==='wrong')return {config:'wrong'};if(f.configSaveMode==='expiry')return {config:{...data.config,expires_utc_s:'bad'}};if(f.configSaveMode==='pins')return {config:{...data.config,pins:{...data.config.pins,indicator:{}}}};if(f.configSaveMode==='null')return {config:null};}return data;},headers:{get:()=> f.savedRevision || '"original-revision"'}};
        }});
    f.events = {}; context.addEventListener=(name,handler)=>{f.events[name]=handler;};
    context.location={href:'http://127.0.0.1/',hash:receipt,pathname:'/',search:''};
    context.history={state:null,replaceState:(value,__,url)=>{context.history.state=value;context.location.hash=url.includes('#')?url.slice(url.indexOf('#')):'';}};
    if (consumerMode) {
        f.radio = {
            authenticated:false,
            publicRead:async(path)=>{
                f.publicReads=(f.publicReads||0)+1;
                if(f.publicStatusFailure) throw Error('status unavailable');
                return context.fetch('/api/v1/'+path,{method:'GET'});
            },
            publicStatus:async()=>{
                f.publicReads=(f.publicReads||0)+1;
                if (f.publicStatusFailure) throw Error('status unavailable');
                return {schema:'transmitter-public-status/1',device_id:'1'.repeat(32),boot_id:state.job.boot_id,state:state.job.state,output_active:state.job.output_active,owned:state.job.owner_id!==null,clock_state:state.standalone.clock_state,utc_now_ns:state.standalone.utc_now_ns||String(BigInt(f.now)*1000000n),uncertainty_ns:state.standalone.uncertainty_ns,engine:state.standalone.engine};
            },
            identity:async()=>({device_id:'1'.repeat(32),boot_id:'a'.repeat(32),generation:'3'}),
            login:async()=>{ f.radio.authenticated=true; },
            request:async(path,method='GET',body)=>{
                if (!f.radio.authenticated) throw new Error('Log in again');
                return context.fetch('/api/v1/'+path,{method,body:body===undefined?undefined:JSON.stringify(body)});
            },
            prepareNetwork:async()=>({kind:'network',device:'1'.repeat(32),generation:'4',digest:'a'.repeat(64),submit:{secret:'must-not-survive'}}),
            submitSetup:async()=>{ f.setupSubmits=(f.setupSubmits||0)+1; f.radio.authenticated=false; throw new Error('reply lost'); },
            checkSetup:async()=> f.setupCheckResult || 'saved',
            clear:()=>{ f.radio.authenticated=false; },logout:async()=>{ f.radio.authenticated=false; }
        };
        context.WsprryPicoConsumerRadio={createClient:()=>f.radio};
    }
    f.links=navigationLinks;
    context.history.pushState=(value,__,url)=>{context.history.state=value;context.location.pathname=url.split('#')[0];context.location.hash=url.includes('#')?url.slice(url.indexOf('#')):'';};
    vm.runInContext(fs.readFileSync(__dirname+'/../src/network/web/udp-logging.js','utf8'),context);
    vm.runInContext(source,context);
    await new Promise(setImmediate);
    if(organizationMode)vm.runInContext(fs.readFileSync(__dirname+'/../src/network/web/organization.js','utf8'),context);
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
module.exports={fixture};
if (require.main === module) (async () => {
    const recurrence=await fixture();recurrence.scheduleSupport=true;
    vm.runInContext('capabilities=null',recurrence.context);await recurrence.elements.refresh.onclick();
    assert.equal(recurrence.elements['message-schedule-controls'].hidden,true,'no saved schedule clutter for Send once');
    recurrence.prepareMessage('qrss','CQ CQ DE AA0NT EM18 QRSS TEST 73');recurrence.elements['message-delivery'].value='recurring';
    recurrence.elements['message-form'].oninput();
    assert.equal(recurrence.elements['message-schedule-controls'].hidden,false);
    assert.equal(recurrence.elements['message-schedule-read'].hidden,true);
    assert.equal(recurrence.elements['message-schedule-adopt'].hidden,true);
    assert.equal(recurrence.elements['message-schedule-pause'].hidden,true);
    await recurrence.elements['message-form'].onsubmit({preventDefault(){}});
    assert.equal(recurrence.scheduleSaves,1);assert.equal(recurrence.savedMessageSchedule.period_s,1200);
    assert.equal(recurrence.calls.filter(c=>c.path.endsWith('jobs')).length,0);
    assert.equal(recurrence.elements['message-schedule-pause'].hidden,false);
    recurrence.elements['message-text'].value='UNSAVED';recurrence.elements['message-delivery'].value='once';
    recurrence.elements['message-form'].oninput();await recurrence.elements.refresh.onclick();
    assert.equal(recurrence.elements['message-text'].value,'UNSAVED');
    assert.equal(recurrence.elements['message-delivery'].value,'once');
    assert.equal(recurrence.elements['message-schedule-controls'].hidden,false,'existing schedule remains accessible during Send once');
    assert.equal(recurrence.elements['message-schedule-adopt'].hidden,false);
    const beforeRestore=recurrence.calls.length;
    recurrence.context.confirm=()=>false;recurrence.elements['message-schedule-adopt'].onclick();
    assert.equal(recurrence.elements['message-text'].value,'UNSAVED');
    assert.equal(recurrence.elements['message-delivery'].value,'once');
    recurrence.context.confirm=()=>true;
    recurrence.elements['message-schedule-adopt'].onclick();assert.equal(recurrence.elements['message-text'].value,'CQ CQ DE AA0NT EM18 QRSS TEST 73');
    assert.equal(recurrence.elements['message-delivery'].value,'recurring');
    assert.equal(recurrence.calls.length,beforeRestore,'restore changes the editor without network requests');
    recurrence.loseScheduleSave=true;await recurrence.elements['message-form'].onsubmit({preventDefault(){}});
    assert.equal(recurrence.scheduleSaves,2);
    await recurrence.elements['message-form'].onsubmit({preventDefault(){}});assert.equal(recurrence.scheduleSaves,2);
    assert.match(recurrence.elements['message-schedule-status'].textContent,/unconfirmed/);
    await recurrence.elements.refresh.onclick();
    assert.equal(recurrence.elements['message-schedule-read'].hidden,false);
    assert.equal(recurrence.elements['message-schedule-adopt'].hidden,true);
    assert.equal(recurrence.elements['message-submit'].disabled,true,'ordinary refresh does not clear recovery');
    recurrence.loseScheduleSave=false;await recurrence.elements['message-schedule-read'].onclick();
    assert.equal(recurrence.elements['message-schedule-read'].hidden,true);
    assert.equal(recurrence.elements['message-result'].textContent,'','confirmed read clears the resolved save error');
    recurrence.schedulePausePending=true;recurrence.scheduleState='pausing';
    await recurrence.elements['message-schedule-pause'].onclick();
    assert.equal(recurrence.elements['message-schedule-pause'].hidden,true,'pending pause cannot be repeated');
    assert.match(recurrence.elements['message-schedule-status'].textContent,/Keep the Pico powered/);
    recurrence.schedulePausePending=false;recurrence.scheduleState=null;recurrence.savedMessageSchedule.enabled=false;
    await recurrence.elements.refresh.onclick();
    assert.equal(recurrence.elements['message-schedule-pause'].hidden,true,'already paused action is omitted');
    assert.equal(recurrence.elements['message-schedule-help'].hidden,true);
    assert.match(recurrence.elements['message-schedule-status'].textContent,/Save and start schedule/);
    recurrence.scheduleState='recovery_required';await recurrence.elements.refresh.onclick();
    assert.equal(recurrence.elements['message-schedule-pause'].hidden,false,'recovery is actionable even for a disabled saved schedule');
    assert.equal(recurrence.elements['message-schedule-pause'].textContent,'Acknowledge interrupted schedule');
    recurrence.scheduleState=null;recurrence.loseSchedulePause=true;
    await recurrence.elements['message-schedule-pause'].onclick();
    assert.equal(recurrence.elements['message-schedule-read'].hidden,false);
    await recurrence.elements.refresh.onclick();
    assert.equal(recurrence.elements['message-submit'].disabled,true,'lost pause needs explicit readback');
    recurrence.loseSchedulePause=false;await recurrence.elements['message-schedule-read'].onclick();
    recurrence.scheduleReadFailure=true;await recurrence.elements.refresh.onclick();
    assert.equal(recurrence.elements['message-schedule-controls'].hidden,false);
    assert.equal(recurrence.elements['message-schedule-read'].hidden,false,'failed reads retain a recovery action');
    recurrence.scheduleReadFailure=false;await recurrence.elements['message-schedule-read'].onclick();
    assert.equal(recurrence.elements['message-schedule-read'].hidden,true);
    const publicPage=await fixture(true,true,false,true);
    assert.equal(publicPage.elements.focused,undefined);
    publicPage.elements['access-toggle'].onclick();assert.equal(publicPage.elements.focused,'local-password');assert.equal(publicPage.elements['local-access'].open,true);publicPage.elements['access-close'].onclick();
    assert(publicPage.publicReads>1);
    assert.equal(publicPage.form.callsign.value,'AA0NT');
    assert.equal(publicPage.elements['station-settings-lock'].disabled,true);
    assert.equal(publicPage.elements['wifi-settings-lock'].disabled,true);
    assert(publicPage.calls.every(c=>!c.path.startsWith('/api/v1/') || c.options.method==='GET'));
    assert.equal(publicPage.elements.state.textContent,'empty');
    assert.equal(publicPage.elements.output.textContent,'Inactive');
    assert.equal(publicPage.elements['message-settings'].disabled,true);
    publicPage.elements['local-password'].value='unsent draft';
    publicPage.elements.focused='message-text';
    publicPage.state.job.state='running';publicPage.state.job.output_active=true;
    await publicPage.elements.refresh.onclick();
    assert.equal(publicPage.elements.state.textContent,'running');
    assert.equal(publicPage.elements.output.textContent,'Active');
    assert.equal(publicPage.elements.focused,'message-text');
    assert.equal(publicPage.elements['local-password'].value,'unsent draft');
    publicPage.publicStatusFailure=true;await publicPage.elements.refresh.onclick();
    assert.equal(publicPage.elements.output.textContent,'Unknown');
    assert.equal(publicPage.elements['public-status-note'].hidden,true);
    publicPage.publicStatusFailure=false;await publicPage.elements.refresh.onclick();
    assert.equal(publicPage.elements.output.textContent,'Active');
    const durationPage=await fixture();
    for (const mode of ['qrss','fskcw','dfcw']) {
      durationPage.prepareMessage(mode,'CQ CQ DE AA0NT EM18 QRSS TEST 73');
      durationPage.elements['message-frequency'].value='';
      durationPage.elements['message-form'].oninput();
      assert.match(durationPage.elements['message-duration'].textContent,mode==='dfcw' ? /11 min 9.000001 s/ : /15 min 3.000001 s/);
      durationPage.elements['message-repeats'].value='2';durationPage.elements['message-gap'].value='10';
      durationPage.elements['message-form'].oninput();
      assert.match(durationPage.elements['message-duration'].textContent,mode==='dfcw' ? /22 min 28.000001 s/ : /30 min 16.000001 s/);
    }
    durationPage.elements['message-text'].value='unsupported!';durationPage.elements['message-form'].oninput();
    assert.match(durationPage.elements['message-duration'].textContent,/unavailable.*Unsupported character/);
    assert.equal(durationPage.calls.filter(c=>c.path.endsWith('jobs')).length,0);
    const organized=await fixture(true,true,false,false,'',true);
    const submit={preventDefault(){}};
    organized.form=organized.elements.config.elements;
    organized.form.schedules.value='invalid unrelated schedule';
    organized.form.callsign.value='K1ABC';
    organized.form.callsign.reportValidity=()=>false;
    await organized.elements['engineering-station-form'].onsubmit(submit);
    assert.equal(organized.calls.filter(c=>c.path.endsWith('config/update')).length,0);
    organized.form.callsign.reportValidity=()=>true;
    await organized.elements['engineering-station-form'].onsubmit(submit);
    assert.equal(organized.config.station.callsign,'K1ABC');
    assert.equal(organized.form.schedules.value,'invalid unrelated schedule');
    organized.form.password.value='private-test-password';
    await organized.elements['engineering-network-form'].onsubmit(submit);
    assert.equal(vm.runInContext('saveAttempt.intended.config.wifi.password',organized.context),null);
    assert.equal(organized.form.password.value,'');
    assert.equal(organized.calls.filter(c=>c.path.endsWith('jobs')).length,0);
    organized.context.location.pathname='/wifi-host';organized.context.location.hash='#hostname-form';
    const click={button:0,preventDefault(){}};
    organized.elements['station-link'].listeners.click(click);
    assert.equal(organized.elements['station-area'].hidden,false);
    const areaReceipt='#save='+encodeURIComponent(JSON.stringify({kind:'station',device:'1'.repeat(32),generation:'2',digest:'a'.repeat(64)}));
    organized.context.location.hash=areaReceipt;
    organized.elements['wifi-host-link'].listeners.click(click);
    assert.equal(organized.context.location.hash,areaReceipt);
    assert.equal(organized.elements['wifi-host-area'].hidden,false);
    organized.form.callsign.value='UNSAVED';organized.elements['engineering-station-form'].listeners.input();
    await organized.elements['reload-config'].onclick();
    assert.equal(organized.form.callsign.value,'K1ABC');
    const jumpReceipt=organized.context.location.hash, jumpRequests=organized.calls.length;
    organized.links.find(link=>link.getAttribute().endsWith('#message-section')).click(click);assert.equal(organized.elements.focused,'message-section-summary');
    assert.equal(organized.context.location.hash,jumpReceipt);assert.equal(organized.calls.length,jumpRequests);
    assert.match(organized.elements['message-preview'].textContent,/Enter a message/);
    organized.elements['message-form'].oninput();
    assert.match(organized.elements['message-preview'].textContent,/message has 0/);
    const compact=await fixture();
    compact.context.progressSnapshot={fields:{},station:compact.config.station};
    vm.runInContext('savedReadback={config:currentConfig,progress:progressSnapshot};showDraftComparison()',compact.context);
    assert.ok(!compact.elements['draft-comparison'].textContent.includes('Time server'));
    assert.ok(!compact.elements['draft-comparison'].textContent.includes('Standalone schedule enabled'));
    vm.runInContext('currentConfig.pins=readPins();savedReadback.config=currentConfig;showDraftComparison()',compact.context);
    assert.ok(!compact.elements['draft-comparison'].textContent.includes('Switch GPIO'));
    assert.ok(!compact.elements['draft-comparison'].textContent.includes('Indicator GPIO'));
    compact.context.progressSnapshot.fields={enabled:null,wifi:null,schedules:[]};
    vm.runInContext('showDraftComparison()',compact.context);
    assert.match(compact.elements['draft-comparison'].textContent,/Cleared \/ unset/);
    assert.match(compact.elements['draft-comparison'].textContent,/Schedules \(interval/);
    compact.state.standalone.reboot_required=true;await compact.elements.refresh.onclick();
    assert.match(compact.elements['message-availability'].textContent,/require a restart/);
    compact.state.standalone.reboot_required=false;compact.state.job.output_active=null;
    await compact.elements.refresh.onclick();assert.match(compact.elements['message-availability'].textContent,/RF output is unknown/);assert.equal(compact.elements.restart.disabled,true);
    const naming=await fixture();
    naming.elements['hostname-input'].value='bad name';await naming.elements['hostname-form'].onsubmit(submit);
    assert.equal(naming.elements['hostname-input'].getAttribute('aria-invalid'),'true');
    naming.elements['hostname-default'].onclick();
    assert.equal(naming.elements['hostname-input'].value,'default.local');
    assert.equal(naming.elements['hostname-input'].getAttribute('aria-invalid'),'false');
    assert.equal(naming.elements['hostname-error'].textContent,'');
    const initial=await fixture(true,false,false,false,'',true);
    Object.assign(initial.form.callsign,{value:'K1ABC'});initial.form.locator.value='FN42';initial.form.power_dbm.value='30';
    initial.form.ssid.value='first-network';initial.form.password.value='first-password';initial.form.ntp_ipv4.value='pool.ntp.org';
    await initial.elements['initial-config'].onclick();
    assert.equal(initial.calls.filter(c=>c.path.endsWith('config')&&c.options.method==='PUT').length,1);
    const initialBody=JSON.parse(initial.calls.find(c=>c.path.endsWith('config')&&c.options.method==='PUT').options.body);
    assert.equal(initialBody.station.callsign,'K1ABC');assert.equal(initialBody.wifi.ssid,'first-network');
    const bookmark=await fixture(true,true,false,true,'#hostname-form',true);
    await bookmark.elements['local-login'].onsubmit({preventDefault(){}});
    assert.equal(bookmark.context.location.hash,'#hostname-form');
    const returning='#'+new URLSearchParams({'hostname-return':JSON.stringify({device:'1'.repeat(32),boot:'a'.repeat(32),name:'new.local'})});
    const pendingReturn=await fixture(true,true,false,true,returning,true);
    await pendingReturn.elements['local-login'].onsubmit({preventDefault(){}});
    assert.equal(pendingReturn.context.location.hash,returning);
    const hostname = await fixture();
    hostname.context.location.href='http://secret-user:secret-password@127.0.0.1/old?secret=query';
    vm.runInContext('showContinuation({device:"1".repeat(32),boot:"a".repeat(32),name:"pico-a.local"})',hostname.context);
    const continuation=new URL(hostname.elements['hostname-continue'].href);
    assert.equal(continuation.username,'');assert.equal(continuation.password,'');assert.equal(continuation.search,'');
    assert.equal(vm.runInContext('canonicalHostname("K.local")',hostname.context),null);
    assert.equal(vm.runInContext('canonicalHostname("K.LOCAL.")',hostname.context),'k.local');
    hostname.savedHostname='pico-a.local';await hostname.elements.refresh.onclick();
    assert.equal(hostname.elements['hostname-continue'].hidden,false);
    hostname.savedHostname='old.local';await hostname.elements.refresh.onclick();
    assert.equal(hostname.elements['hostname-continue'].hidden,true);assert.equal(hostname.elements['hostname-continue'].href,'');
    const wrongLocalReceipt='#'+new URLSearchParams({'hostname-return':JSON.stringify({device:'2'.repeat(32),boot:'a'.repeat(32),name:'pico-a.local'})});
    const wrongLocal=await fixture(true,true,true,false,wrongLocalReceipt);
    wrongLocal.elements['local-password'].value='test-password';
    await wrongLocal.elements['local-login'].onsubmit({preventDefault(){}});
    assert.equal(wrongLocal.calls.some(c=>c.path==='/local/v1/login'),false);
    assert.equal(wrongLocal.elements['local-password'].value,'');
    const visibility = await fixture(true,true,false,true);
    const password = visibility.elements['local-password'];
    password.value = 'Correctable 63-char draft: ' + 'x'.repeat(36);
    password.selectionStart=3;password.selectionEnd=11;password.selectionDirection='backward';
    const toggle=visibility.elements['local-password-toggle'], requests=visibility.calls.length;
    toggle.onclick();
    assert.equal(password.type,'text');
    assert.equal(password.value.length,63);
    assert.deepEqual([password.selectionStart,password.selectionEnd,password.selectionDirection],[3,11,'backward']);
    assert.equal(toggle.attributes['aria-label'],'Hide pico password');
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
    for (const id of ['local-password','config-password','consumer-password','retirement-password','pico-new-password','pico-confirm-password']) {
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
    assert.match(resumed.elements['consumer-save-status'].textContent,/save needs confirmation/);
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
    f.offline = true; await f.elements.refresh.onclick(); assert.equal(f.elements.hostname.textContent,'Unknown'); assert.equal(f.elements.settings.disabled,true); assert.equal(f.elements.abort.disabled,true);
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
    await new Promise(setImmediate);
    assert.match(reboot.elements['restart-status'].textContent,/Same Pico and new boot confirmed/);
    assert.equal(reboot.calls.filter(c=>c.path.endsWith('restart')).length,1);
    for (const mode of ['lost','unchanged']) {
        const failed = await fixture(); failed.restartMode = mode;
        await failed.elements.restart.onclick();
        assert.equal(failed.calls.filter(c=>c.path.endsWith('restart')).length,1);
        assert.doesNotMatch(failed.elements.notice.textContent,/Device restarted/);
        await new Promise(setImmediate);
        assert.match(failed.elements['restart-status'].textContent,/could not be confirmed within 90 seconds/);
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
    const ordinary=await fixture();
    assert.equal(ordinary.elements['saved-settings'].hidden,true);
    assert.equal(ordinary.elements['consumer-setup'].hidden,true);
    assert.equal(ordinary.elements['consumer-save-recovery'].hidden,true);
    assert.equal(ordinary.elements['setup-result-reveal'].hidden,true);
    assert.equal(ordinary.elements['saved-active-status'].textContent,'');
    ordinary.form.schedules.value='480 / 0';ordinary.elements.config.oninput();ordinary.confirm=false;
    const ordinaryReads=ordinary.calls.length;await ordinary.elements['reload-config'].onclick();
    assert.equal(ordinary.form.schedules.value,'480 / 0');assert.equal(ordinary.calls.length,ordinaryReads);
    ordinary.confirm=true;await ordinary.elements['reload-config'].onclick();
    assert.equal(ordinary.form.schedules.value,'120 / 0');assert.equal(ordinary.elements['saved-settings'].hidden,true);
    const newer=await fixture();newer.form.schedules.value='240 / 0';newer.elements.config.oninput();
    await newer.elements['read-saved'].onclick();newer.savedRevision='"newer-revision"';
    const writesBefore=newer.calls.filter(c=>c.options.method!=='GET').length;
    await newer.elements['review-saved'].onclick();
    assert.equal(vm.runInContext('writeState',newer.context),'readback');assert.equal(newer.elements['save-config'].disabled,true);
    assert.equal(newer.form.schedules.value,'240 / 0');assert.equal(newer.elements['saved-settings'].hidden,false);
    assert.equal(newer.calls.filter(c=>c.options.method!=='GET').length,writesBefore);
    await newer.elements['read-saved'].onclick();await newer.elements['review-saved'].onclick();
    assert.equal(newer.elements['saved-settings'].hidden,true);assert.equal(newer.elements['save-config'].disabled,false);
    const reloadUncertain=await fixture();reloadUncertain.form.schedules.value='240 / 0';reloadUncertain.elements.config.oninput();
    reloadUncertain.configSaveMode='lost';await reloadUncertain.elements.config.onsubmit({preventDefault(){}});
    reloadUncertain.configSaveMode=null;const committed=reloadUncertain.configCommits;
    await reloadUncertain.elements['reload-config'].onclick();
    assert.equal(reloadUncertain.elements['save-config'].disabled,true);assert.equal(reloadUncertain.elements['saved-settings'].hidden,false);
    assert.equal(reloadUncertain.configCommits,committed,'discard/reload never repeats or clears an uncertain save');
    for (const mode of ['before','lost','json','empty','wrong','expiry','pins','null']) {
        const uncertain=await fixture();uncertain.form.schedules.value='240 / 0';uncertain.elements.config.oninput();uncertain.configSaveMode=mode;
        await uncertain.elements.config.onsubmit({preventDefault(){}});
        assert.equal(uncertain.form.schedules.value,'240 / 0');assert.equal(uncertain.configCommits||0,mode==='before'?0:1);
        assert.equal(uncertain.elements['save-config'].disabled,true);assert.equal(vm.runInContext('writeState',uncertain.context),'readback');
        await uncertain.elements.refresh.onclick();assert.equal(uncertain.elements['save-config'].disabled,true);
        uncertain.configSaveMode=null;await uncertain.elements['read-saved'].onclick();assert.equal(uncertain.elements['save-config'].disabled,true);
        assert.equal(uncertain.form.schedules.value,'240 / 0');assert.match(uncertain.elements['saved-readback'].textContent,/"active": null/);
        if(mode==='before') assert.match(uncertain.elements['draft-comparison'].textContent,/Schedules[\s\S]*Browser draft:\s+240 \/ 0[\s\S]*Complete saved settings:\s+120 \/ 0/);
        const comparisonCalls=uncertain.calls.length;uncertain.form.password.value='PRIVATE-DRAFT-PASSWORD';uncertain.elements.config.oninput();
        assert.equal(uncertain.calls.length,comparisonCalls);assert.ok(!uncertain.elements['draft-comparison'].textContent.includes('PRIVATE-DRAFT-PASSWORD'));
        assert.match(uncertain.elements['draft-comparison'].textContent,/Password values are hidden/);
        await uncertain.elements['review-saved'].onclick();assert.equal(uncertain.elements['save-config'].disabled,false);
        await uncertain.elements['reload-config'].onclick();
        assert.equal(uncertain.elements['saved-readback-details'].hidden,true);
        assert.equal(vm.runInContext('savedReadback',uncertain.context),null);
        assert.equal(uncertain.elements['save-reconcile-status'].textContent,'');
        assert.equal(uncertain.elements['saved-settings'].hidden,true);
        await uncertain.elements['read-saved'].onclick();
        if(mode==='before') assert.ok(!uncertain.elements['draft-comparison'].textContent.match(/Browser draft:\s+240 \/ 0/));
    }
    for (const expires of [2208988800,4102444799]) {
        const future=await fixture();future.config.expires_utc_s=expires;await future.elements['reload-config'].onclick();assert.ok(future.form.expiry.value.startsWith(expires===2208988800?'2040':'2099'));
        future.form.schedules.value='240 / 0';future.elements.config.oninput();await future.elements['read-saved'].onclick();assert.equal(future.form.schedules.value,'240 / 0');await future.elements['review-saved'].onclick();assert.equal(future.elements['save-config'].disabled,false);
    }
    const legacyIdentity=await fixture();
    legacyIdentity.config.station.callsign='AA0NT/P/M';
    await legacyIdentity.elements['reload-config'].onclick();
    legacyIdentity.form.schedules.value='240 / 0';legacyIdentity.elements.config.oninput();
    await legacyIdentity.elements.config.onsubmit({preventDefault(){}});
    const legacySaves=()=>legacyIdentity.calls.filter(c=>c.path.endsWith('config')&&c.options.method==='PUT');
    assert.equal(legacySaves().length,1);
    assert.equal(JSON.parse(legacySaves()[0].options.body).station.callsign,'AA0NT/P/M');
    legacyIdentity.form.callsign.value='AA0NT/P';legacyIdentity.elements.config.oninput();
    await legacyIdentity.elements.config.onsubmit({preventDefault(){}});
    assert.equal(legacySaves().length,2); // Schedule save preserves saved identity, ignoring an unrelated station draft.
    assert.equal(JSON.parse(legacySaves()[1].options.body).station.callsign,'AA0NT/P/M');
    const emptyV2=await fixture(true,false);
    emptyV2.appV2={schema:'transmitter-application/2',target:{scope:'member',device_id:'1'.repeat(32),boot_id:emptyV2.state.job.boot_id},
      station:{station:null},hardware:{saved:null,active:null,pending_restart:false,application_error:null},recurrence:{},
      capabilities:{station_encoding:'wspr_type123_auto'},reboot_required:false,wspr_plan:null};
    await emptyV2.elements['read-saved'].onclick();
    assert.equal(vm.runInContext('writeState',emptyV2.context),'review');
    assert.equal(emptyV2.elements['saved-settings'].hidden,false);
    const changed=await fixture(true,true,false,true);changed.elements['local-password'].value='test-password';await changed.elements['local-login'].onsubmit({preventDefault(){}});
    changed.form.schedules.value='240 / 0';changed.elements.config.oninput();changed.config.station={callsign:'K1ABC',locator:'FN42',power_dbm:30};changed.config.wifi={ssid:'new-network',password:null,ntp_ipv4:'pool.ntp.org'};
    await changed.elements['read-saved'].onclick();await changed.elements['review-saved'].onclick();await changed.elements.config.onsubmit({preventDefault(){}});
    const outgoing=JSON.parse(changed.calls.filter(c=>c.path.endsWith('config')&&c.options.method==='PUT').at(-1).options.body);
    assert.equal(outgoing.station.callsign,'K1ABC');assert.equal(outgoing.wifi.ssid,'new-network');assert.equal(outgoing.schedules[0].period_s,240);
    const numeric=await fixture();
    vm.runInContext("saveProgressFields=async fields=>{globalThis.numericFields=fields;return {};}",numeric.context);
    numeric.form.callsign.value='BB1BB';numeric.form.power_dbm.value='2147483648';
    vm.runInContext("progressEdits.set('callsign',1);progressEdits.set('power_dbm',2)",numeric.context);
    await vm.runInContext("saveConfigProgress('station')",numeric.context);
    assert.equal(numeric.context.numericFields.callsign,'BB1BB');
    assert.equal(numeric.context.numericFields.power_dbm,'2147483648');
    assert.equal(vm.runInContext("progressNumber('30.0')",numeric.context),30);
    assert.equal(vm.runInContext("progressNumber('3e1')",numeric.context),30);
    numeric.form.schedules.value='2147483648 / 0';numeric.form.enabled.checked=true;numeric.form.expiry.value='2040-01-01T00:00';
    vm.runInContext("progressEdits.clear();for(const k of ['schedules','enabled','expires_utc_s'])progressEdits.set(k,1)",numeric.context);
    await vm.runInContext("saveConfigProgress('radio')",numeric.context);
    assert.equal(numeric.context.numericFields.enabled,true);
    assert.equal(numeric.context.numericFields.schedules[0].period_s,'2147483648');
    assert.equal(numeric.context.numericFields.expires_utc_s,'2208988800');
    console.log('Browser edit preservation, conflicts, ownership, failure and RF pause tests passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
