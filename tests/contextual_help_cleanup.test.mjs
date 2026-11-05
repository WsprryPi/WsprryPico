import assert from 'node:assert/strict';
import {test} from 'node:test';
import {closeHelpTarget} from './contextual_help_browser.mjs';

test('closes a live help popup through the requested target',async()=>{
  const calls=[];
  await closeHelpTarget(async(method,params)=>{calls.push([method,params]);return {success:true};},'help');
  assert.deepEqual(calls,[['Target.closeTarget',{targetId:'help'}]]);
});
test('accepts a vanished popup only after a fresh target enumeration confirms absence',async()=>{
  const calls=[];
  await closeHelpTarget(async(method,params)=>{
    calls.push([method,params]);
    if(method==='Target.closeTarget')throw Object.assign(Error('stage=CDP Target.closeTarget; No target with given id found'),{code:-32602,protocolMessage:'No target with given id found'});
    return {targetInfos:[{targetId:'main'},{targetId:'another-popup'}]};
  },'help');
  assert.deepEqual(calls,[['Target.closeTarget',{targetId:'help'}],['Target.getTargets',undefined]]);
});
test('fails when the supposedly vanished popup is still present',async()=>{
  const failure=Object.assign(Error('stage=CDP Target.closeTarget; No target with given id found'),{code:-32602,protocolMessage:'No target with given id found'});
  await assert.rejects(closeHelpTarget(async method=>{
    if(method==='Target.closeTarget')throw failure;
    return {targetInfos:[{targetId:'help'}]};
  },'help'),error=>error===failure);
});
test('preserves other protocol failures without treating them as an already closed popup',async()=>{
  const failure=Error('Connection lost'),calls=[];
  await assert.rejects(closeHelpTarget(async method=>{calls.push(method);throw failure;},'help'),error=>error===failure);
  assert.deepEqual(calls,['Target.closeTarget']);
});
test('fails when absence cannot be confirmed',async()=>{
  const failure=Error('Target enumeration failed');
  await assert.rejects(closeHelpTarget(async method=>{
    if(method==='Target.closeTarget')throw Object.assign(Error('stage=CDP Target.closeTarget; No target with given id found'),{code:-32602,protocolMessage:'No target with given id found'});
    throw failure;
  },'help'),error=>error===failure);
});
