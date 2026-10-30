const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {ppm,create} = require('../src/network/web/rf-calibration.js');
for (const [value,expected] of [['10',10000],['-0.001',-1],['+100.000',100000],['0',0]]) assert.equal(ppm(value),expected);
for (const value of ['NaN','1e2','1.0000','100.001','-100.001','.1','1.',' 1','1 ']) assert.equal(ppm(value),null);
const element = value => ({value,disabled:false,setAttribute(){},textContent:''});
(async()=>{
  const input=element('0.000'),mode=element('manual'),read=element(),save=element(),discard=element(),adopt=element(),status=element();
  let target={scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)};
  let writes=0, fail=false, reportedErrors=0;
  const editor=create({input,mode,read,save,discard,adopt,status,onError:()=>{reportedErrors++;},exchange:async(method,body,match)=>{
    if (method==='PUT') { writes++; assert.equal(match,'revision'); if (fail) throw Error('Lost reply'); }
    return {revision:'revision',data:{schema:'rf-calibration',target,storage_healthy:true,
      saved:{manual_ppm:body?.calibration.manual_ppm ?? '0.000',mode:body?.calibration.mode ?? 'manual'},
      selection:{next_ppb:0,reason:'manual_mode'}}};
  }});
  editor.setAvailability(true);
  assert.equal(save.disabled,true);
  await read.onclick();
  input.value='10.000'; input.oninput();
  assert.equal(save.disabled,false);
  mode.value='ntp'; mode.onchange();
  assert.equal(save.disabled,true);
  mode.value='manual'; mode.onchange();
  assert.equal(save.disabled,false);
  await save.onclick(); assert.equal(writes,1);
  input.value='20.000'; input.oninput(); fail=true;
  await save.onclick(); assert.equal(input.value,'20.000'); assert.equal(save.disabled,true);
  assert.match(status.textContent,/Read saved/);assert.equal(reportedErrors,1);
  await read.onclick(); assert.equal(input.value,'20.000'); assert.equal(save.disabled,false);
  target={...target,boot_id:'c'.repeat(32)};
  editor.invalidate(); assert.equal(save.disabled,true);
  await read.onclick(); assert.equal(input.value,'20.000'); assert.equal(save.disabled,true);
  assert.equal(adopt.hidden,false); adopt.onclick(); assert.equal(save.disabled,false);
  discard.onclick(); assert.equal(input.value,'0.000'); assert.equal(save.disabled,true);
  editor.setAvailability(false); assert.equal(read.disabled,true);
  // Execute the real app API adapter; this catches revision/etag shape drift.
  const app = fs.readFileSync(require.resolve('../src/network/web/app.js'),'utf8');
  const apiSource = app.slice(app.indexOf('async function api('),app.indexOf('async function local('));
  const requests=[];
  const actualApi = vm.runInNewContext(fs.readFileSync(require.resolve('../src/network/web/control-contract.js'),'utf8') + '\n' + apiSource + '\napi;',{
    returnReceipt:false,consumerAttempt:false,localIdentity:null,radio:null,accessCarrier:'certificate',accessEpoch:0,accessClosing:false,localLocked:false,
    supportsAmplifier:()=>false,controlsUnlocked:()=>true,AbortSignal,
    frequencyEditor:{observeRevision:value=>assert.equal(value,'actual-revision')},
    fetch:async(path,options)=>{
      requests.push({path,options});
      const body=options.body ? JSON.parse(options.body) : null;
      return {ok:true,headers:{get:name=>name==='ETag' ? 'actual-revision' : null},
        json:async()=>({contract:'Wsprry-Control/1',schema:'rf-calibration',target,storage_healthy:true,
          saved:{manual_ppm:body?.calibration.manual_ppm ?? '0.000',mode:'manual'}})};
    }
  });
  const ui={input:element('0.000'),mode:element('manual'),read:element(),save:element(),status:element()};
  const integrated=create({...ui,exchange:(method,body,match)=>actualApi('rf-calibration',method,body,match)});
  integrated.setAvailability(true);
  await ui.read.onclick();
  ui.input.value='1.234'; ui.input.oninput();
  assert.equal(ui.save.disabled,false);
  await ui.save.onclick();
  assert.equal(requests[1].options.headers['If-Match'],'actual-revision');
  assert.equal(JSON.parse(requests[1].options.body).calibration.manual_ppm,'1.234');
  assert.match(ui.status.textContent,/Manual calibration saved/);
  console.log('RF calibration browser checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
