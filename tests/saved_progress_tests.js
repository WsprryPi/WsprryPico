const assert = require('node:assert/strict');
require('../src/network/web/saved-progress.js');
const ui=globalThis.WsprryPicoSavedProgress;
const target={scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)};
const base={schema:'transmitter-progress/1',target,draft_revision:'1',config_revision:'0',profile_revision:'0',fields:{callsign:'AA0NT'},last_receipt:null,last_outcomes:{callsign:'saved'},applied_station:null,station:{callsign:'AA0NT',locator:null,power_dbm:null},station_complete:false,complete:false,apply_domains:{station:false,network:false,radio:false,all:false},wspr_plan:null,schedule_enabled:null,schedule_suspended:null,matches_applied:false};
let assertions=0;
function check(value,want){assert.equal(value,want);++assertions;}
check(ui.valid(base),true);
for(const [key,value] of [['schema','transmitter-progress/2'],['draft_revision',1],['config_revision','18446744073709551616'],['profile_revision','01'],['target',{...target,extra:true}],['fields',{power_dbm:''}],['fields',{power_dbm:1}],['fields',{locator:'BAD'}],['fields',{wifi:{ssid:'net',password:'secret'}}],['fields',{expires_utc_s:2147483648}],['fields',{unknown:1}],['last_receipt','a'],['last_outcomes',{callsign:'applied'}],['station_complete',true],['complete',true],['matches_applied',true],['wspr_plan',{}],['apply_domains',{station:false,network:false,radio:false,all:true}],['schedule_enabled','false']]) check(ui.valid({...base,[key]:value}),false);
check(ui.valid({...base,extra:true}),false);
const request={schema:base.schema,target,request_id:'c'.repeat(32),fields:{callsign:'AA0NT'}};
const ack={...base,outcomes:{callsign:'saved'},request_id:request.request_id};
check(ui.confirms(ack,request),true); // Public station-only metadata is safe and sufficient.
for(const patch of [{request_id:'d'.repeat(32)},{target:{...target,boot_id:'e'.repeat(32)}},{outcomes:{}},{outcomes:{callsign:'cleared'}},{last_outcomes:null},{last_outcomes:{callsign:'invalid'}},{fields:{callsign:'BB1BB'},station:{...base.station,callsign:'BB1BB'}}]) check(ui.confirms({...ack,...patch},request),false);
const cleared={...ack,fields:{callsign:null},station:{...base.station,callsign:null},outcomes:{callsign:'cleared'},last_outcomes:{callsign:'cleared'}};
check(ui.confirms(cleared,{...request,fields:{callsign:null}}),true);
check(ui.confirms({...ack,outcomes:{callsign:'invalid'},last_outcomes:{}},{...request,fields:{callsign:'BAD'}}),true);
check(ui.valid({...base,fields:{callsign:'AA0NT',power_dbm:0},station:{...base.station,power_dbm:0}}),true);
for (const outcome of ['saved','cleared','invalid']) {
  const text=ui.fieldOutcomeText('locator',outcome,true);
  check(text.includes('newer edit remains unsaved'),true);
  check(text.includes(outcome==='invalid'?'not saved':outcome==='cleared'?'cleared':'saved as draft'),true);
  if(outcome==='invalid') check(/Earlier value was saved/.test(text),false);
}
check(ui.summary(base).includes('callsign AA0NT'),true);
check(ui.summary(base).includes('grid locator missing; reported power missing'),true);
check(ui.summary({...base,station:{...base.station,callsign:'BB1BB'}}).includes('callsign BB1BB'),true);
check(ui.summary({...base,station:{callsign:'BB1BB',locator:'EM18',power_dbm:0}}).includes('reported power 0 dBm'),true);
console.log(`saved-progress closed response/ack validation: ${assertions} assertions passed`);
