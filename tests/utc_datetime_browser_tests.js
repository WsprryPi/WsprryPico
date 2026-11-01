'use strict';
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const {parse,format,select,create} = require('../src/network/web/utc-datetime.js');
const now = Date.parse('2026-10-26T00:01:20Z');

// A small eventful DOM fixture exercises the shipped controller's actual
// buttons. Calendar defaults and edits never depend on an OS-native picker.
class Element {
  constructor(tag,doc) { Object.assign(this,{tagName:tag,ownerDocument:doc,children:[],attributes:{},dataset:{},listeners:{},value:'',hidden:false,disabled:false,readOnly:false,textContent:''}); }
  append(...nodes) { for (const node of nodes) { node.parentElement=this; this.children.push(node); } }
  replaceChildren(...nodes) { this.children=[];this.append(...nodes); }
  setAttribute(key,value) { this.attributes[key]=String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  addEventListener(type,handler) { (this.listeners[type] ||= []).push(handler); }
  dispatchEvent(event) { for (const handler of this.listeners[event.type] || []) handler(event); }
  matches(selector) { return selector === ':disabled' && this.disabled; }
  closest() { return this.parentElement; }
  contains(target) { return this===target || this.children.some(child=>child.contains(target)); }
  focus() { this.ownerDocument.activeElement=this; }
  setCustomValidity(message) { this.validationMessage=message; }
  find(predicate) { if (predicate(this)) return this;for (const child of this.children) { const result=child.find(predicate);if(result)return result; }return null; }
  querySelector(selector) {
    if (selector==='select') return this.find(node=>node.tagName==='select');
    if (selector==='[data-utc-date]') return this.find(node=>node.dataset.utcDate!==undefined);
    if (selector==='[data-utc-time]') return this.find(node=>node.dataset.utcTime!==undefined);
    const day=selector.match(/^\[data-utc-day="([^"]+)"\]$/);
    if (day) return this.find(node=>node.dataset.utcDay===day[1]);
    const label=selector.match(/^button\[aria-label="([^"]+)"\]$/);
    if (label) return this.find(node=>node.tagName==='button' && node.getAttribute('aria-label')===label[1]);
    throw Error('Unsupported fixture selector: '+selector);
  }
}
function fixture(value='') {
  const doc={listeners:{},defaultView:{listeners:{},addEventListener(type,handler){this.listeners[type]=handler;}},createElement(tag){return new Element(tag,this);},addEventListener(type,handler){(this.listeners[type] ||= []).push(handler);}};
  const container=doc.createElement('div'),input=doc.createElement('input'),date=doc.createElement('button'),time=doc.createElement('button');
  Object.assign(input,{id:'message-start',value});date.dataset.utcDate='';time.dataset.utcTime='';container.append(input,date,time);
  const editor=create(input,()=>now), panel=container.children.at(-1);
  const click=text=>{const node=panel.find(node=>node.tagName==='button'&&node.textContent===text);assert(node,text);node.focus();node.onclick();};
  return {doc,container,input,date,time,panel,editor,click};
}
async function main() {
  assert.equal(format(now),'2026-10-26T00:01:20');
  assert.equal(parse('2026-10-26 00:01:20').ms,now);
  assert.equal(parse('2026-10-26T00:01').value,'2026-10-26T00:01:00');
  for (const value of ['2026-02-29T12:00:00','2026-02-30T00:00:00','2026-10-26T24:00:00','2026-10-26T00:60:00','2026-10-26T00:00:60','2026-10-26','00:01:20','2026-10-26T00:01:20Z','2026-10-26T00:01:20-05:00']) assert.equal(parse(value),null,value);
  assert(parse('2028-02-29T12:00:00'));
  for (const component of ['date','time']) {
    const f=fixture();assert.equal(f.input.value,'','initial rendering does not set optional expiry');
    f[component].onclick();assert.equal(f.input.value,'2026-10-26T00:01:20');assert(!f.panel.hidden);
  }
  for (const value of ['2027-01-01','T12:34:56','2027-01-01T','']) {
    for(const component of ['date','time']) {const f=fixture(value);f[component].onclick();assert.equal(f.input.value,'2026-10-26T00:01:20');}
  }
  {
    const f=fixture('2027-01-01T12:34:56');f.date.onclick();assert.equal(f.input.value,'2027-01-01T12:34:56');
    f.click('Today (UTC)');assert.equal(f.input.value,'2026-10-26T12:34:56');assert(f.panel.hidden);assert.equal(f.doc.activeElement,f.date);
    f.time.onclick();f.click('Now (UTC)');assert.equal(f.input.value,'2026-10-26T00:01:20');
  }
  {
    const f=fixture('2026-10-31T23:59:58');f.date.onclick();
    const last=f.panel.querySelector('[data-utc-day="2026-10-31"]');last.onkeydown({key:'ArrowRight',preventDefault(){}});
    assert.equal(f.doc.activeElement.dataset.utcDay,'2026-11-01');assert.equal(f.input.value,'2026-10-31T23:59:58');
    f.doc.activeElement.onclick();assert.equal(f.input.value,'2026-11-01T23:59:58');
  }
  {
    const f=fixture('2028-02-29T12:34:56');f.time.onclick();
    const selects=[];f.panel.find(node=>{if(node.tagName==='select')selects.push(node);return false;});
    ['01','02','03'].forEach((value,index)=>selects[index].value=value);f.click('Use time');assert.equal(f.input.value,'2028-02-29T01:02:03');
    f.date.onclick();f.container.dispatchEvent({type:'keydown',key:'Escape',preventDefault(){}});assert(f.panel.hidden);assert.equal(f.input.value,'2028-02-29T01:02:03');
  }
  {
    const f=fixture('2026-02-30T12:34:56');f.date.onclick();assert.equal(f.input.value,'2026-02-30T12:34:56','opening does not discard a complete invalid draft');assert(f.input.validationMessage);
    f.click('Today (UTC)');assert.equal(f.input.value,'2026-10-26T12:34:56');assert.equal(f.input.validationMessage,'');
  }
  {
    const f=fixture();f.input.disabled=true;f.date.onclick();assert.equal(f.input.value,'');assert(f.panel.hidden);
  }
  {
    const f=fixture('2028-02-29T12:34:56');f.date.onclick();f.doc.defaultView.listeners.resize();
    assert(f.panel.hidden,'an orientation change closes an obsolete popup position');assert.equal(f.input.value,'2028-02-29T12:34:56');
  }
  assert.equal(select('2026-11-01T01:30:00','date','2026-11-02',now),'2026-11-02T01:30:00');
  assert.equal(select('2026-11-01T01:30:00','time','02:30:00',now),'2026-11-01T02:30:00');
  assert.equal(select('2026-10-26T00:01:20','date','2026-02-30',now),null);
  process.env.WSPRRY_PICO_BROWSER_SHIPPED='1';
  const {fixture:browser}=require('./network_browser_tests.js');
  for(const mode of ['qrss','fskcw','dfcw']) {
    const f=await browser();f.prepareMessage(mode,'CQ CQ DE AA0NT EM18 QRSS TEST 73');
    const stale=new Date(f.now-5*3600000).toISOString().slice(0,19);f.elements['message-start'].value=stale;
    await f.elements['message-form'].onsubmit({preventDefault(){}});
    assert.equal(f.calls.filter(c=>c.path.endsWith('jobs')).length,0,'a past UTC time never claims or loads');
    assert.match(f.elements['message-result'].textContent,/future UTC start time/);assert.equal(f.elements['message-start'].value,stale);
    const future=new Date(f.now+120000).toISOString().slice(0,19);f.elements['message-start'].value=future;
    await f.elements['message-form'].onsubmit({preventDefault(){}});
    const jobs=f.calls.filter(c=>c.path.endsWith('jobs')).map(c=>JSON.parse(c.options.body));
    assert.deepEqual(jobs.map(j=>j.operation),['HELLO','CLAIM','LOAD_MESSAGE','ARM']);
    assert.equal(jobs.at(-1).body.start_utc_ns,String(BigInt(Date.parse(future+'Z'))*1000000n));
    assert.match(f.elements['job-result'].textContent,/observed \d{2}:\d{2}:\d{2} UTC/);
  }
}
if (!process.env.WSPRRY_PICO_UTC_TEST_ZONE) {
  for (const zone of ['UTC','America/Chicago','America/Los_Angeles','Pacific/Auckland']) {
    const result = spawnSync(process.execPath,[__filename],{env:{...process.env,TZ:zone,WSPRRY_PICO_UTC_TEST_ZONE:'1'},encoding:'utf8'});
    assert.equal(result.status,0,zone + '\n' + result.stdout + result.stderr);
  }
  console.log('UTC picker defaults, paired edits, date boundaries and pre-claim validation passed in four timezones');
} else main().catch(error=>{console.error(error);process.exitCode=1;});
