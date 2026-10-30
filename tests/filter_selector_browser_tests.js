'use strict';
const assert=require('node:assert/strict'),filters=require('../src/network/web/filter-selector.js'),dom=require('./filter_dom.cjs');
const settings={policy:'fixed_manual',release_ms:20,settle_ms:20,selectors:[],ranges:[]};
let value={schema:filters.descriptor.schema,target:{scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)},saved:structuredClone(settings),boot_active:structuredClone(settings),pending_restart:false,selected_id:null,selection_known:true,admission_error:null,output_active:false,rf_active:false,storage_healthy:true,reserved:[{gp:2,role:'rf'},{gp:14,role:'button'}]};
(async()=>{
 assert(filters.supported(filters.descriptor));for(const change of [{maximum_ranges:11},{extra:0},{schema:'filter-selector/99'}])assert(!filters.supported({...filters.descriptor,...change}));
 const b=dom();let rev='1'.repeat(64),puts=0,fail=false,wait=null;
 const editor=filters.mount(b.host,{exchange:async(method,body)=>{if(method==='PUT'){puts++;if(fail)throw Error('Lost reply');value={...value,saved:body.settings,pending_restart:true};rev='2'.repeat(64);}if(wait)await wait;return {data:structuredClone(value),revision:'"'+rev+'"'};}});
 editor.setAvailability(true,false);await editor.load();assert(b.button('Save selectors').disabled);assert(b.button('Add selector').disabled);
 editor.setAvailability(true,true);b.button('Add selector').onclick();b.change('Selector name','HF');b.change('Pico GPIO',3);b.button('Add frequency range').onclick();b.change('Range name','40m');b.change('Selector',1);b.change('From (Hz)',7000000);b.change('Through (Hz)',7300000);b.change('Selection policy','required');
 assert(!b.button('Save selectors').disabled);fail=true;await b.button('Save selectors').onclick();assert.match(b.status(),/entries are preserved/);assert(b.button('Save selectors').disabled);assert.equal(b.inputs('Selector name')[0].value,'HF');
 fail=false;await editor.load();assert(!b.button('Save selectors').disabled);await b.button('Save selectors').onclick();assert.match(b.status(),/Selectors saved/);assert.equal(puts,2);
 b.change('Settle new selection (ms)','1.5');assert(b.button('Save selectors').disabled);assert.equal(b.inputs('Settle new selection (ms)')[0].getAttribute('aria-invalid'),'true');assert.equal(b.inputs('Release old selection (ms)')[0].getAttribute('aria-invalid'),'false');assert.equal(b.inputs('Settle new selection (ms)')[0].getAttribute('aria-describedby'),'filter-selector-controls-validation');b.change('Settle new selection (ms)','20');
 value={...value,target:{...value.target,boot_id:'c'.repeat(32)}};editor.invalidate();await editor.load();assert(!b.button('Use entries for this Pico').hidden);assert(b.button('Save selectors').disabled);b.button('Use entries for this Pico').onclick();assert(!b.button('Save selectors').disabled);
 const original=structuredClone(value);for(const change of [{target:[]},{extra:1},{selected_id:5},{pending_restart:false},{reserved:[{gp:3,role:'rf'}]}])assert(!filters.valid({...original,...change}));
 b.change('Pico GPIO',2);assert(b.button('Save selectors').disabled);b.change('Pico GPIO',3);b.change('Selector name','A name longer than sixteen');assert(b.button('Save selectors').disabled);assert.equal(b.inputs('Selector name')[0].value,'A name longer than sixteen');b.change('Selector name','HF');
 let release;wait=new Promise(r=>release=r);const pending=editor.load();editor.invalidate();release();await pending;wait=null;assert(b.button('Save selectors').disabled);
 console.log('Shared selector editor: strict shapes, lock, drafts, uncertain save, identity review, invalid inputs and stale reads passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
