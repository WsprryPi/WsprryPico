// Render geometry and native form association on the actual served control page.
import assert from 'node:assert/strict';
import {writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
export async function checkControlAlignment({evaluate,send,section,output,baseline=false}) {
  await mkdir(output,{recursive:true});
  const original=await evaluate(`JSON.stringify({engine:document.getElementById('config').elements.rf_engine.value,rf:document.getElementById('config').elements.rf_gp.value,gps:[...document.querySelectorAll('[data-gps]')].map(e=>[e.dataset.gps,e.value])})`);
  const measurements=[];
  await evaluate(`globalThis.alignmentApi=api;globalThis.alignmentWrites=[];api=async(...args)=>{if(args[1]&&args[1]!=='GET')alignmentWrites.push(args[0]);return alignmentApi(...args)};`);
  async function geometry(group) {
    return evaluate(`(()=>{document.getElementById('station-settings-lock').disabled=globalThis.alignmentLocked;const nodes=${group==='rf'?"[...document.querySelector('[name=rf_engine]').closest('.fields').querySelectorAll('select')]":"[...document.querySelector('#gps-settings details .fields').querySelectorAll('select,input')]"};return nodes.map(e=>{const r=e.getBoundingClientRect(),label=e.closest('label'),l=label.getBoundingClientRect(),caption=label.querySelector(':scope>.field-caption,:scope>.help-heading'),text=caption?.classList.contains('help-heading')?caption.firstChild:caption||label.firstChild,range=document.createRange();range.selectNodeContents(text);const t=range.getBoundingClientRect();return {textY:t.y,textHeight:t.height,name:e.name||e.dataset.gps,x:r.x,y:r.y,width:r.width,height:r.height,labelX:l.x,labelY:l.y,labelWidth:l.width,labelHeight:l.height,label:e.labels?.[0]?.textContent,hidden:r.width===0||r.height===0,form:e.form?.id||null,disabled:e.matches(':disabled')};});})()`);
  }
  function aligned(rows,columns,label) {
    const visible=rows.filter(r=>!r.hidden);
    for(const r of visible)assert.ok(r.textY>=r.labelY-1.5&&r.textY+r.textHeight<=r.y+1.5,label+' readable caption does not overlap control '+r.name);
    for(let i=0;i<visible.length;i+=columns) {
      const row=visible.slice(i,i+columns);
      assert.ok(Math.max(...row.map(r=>r.y))-Math.min(...row.map(r=>r.y))<=1.5,label+' control tops '+row.map(r=>r.name));
      assert.ok(Math.max(...row.map(r=>r.y+r.height))-Math.min(...row.map(r=>r.y+r.height))<=1.5,label+' control bottoms');
    }
  }
  try {
    for(const viewport of [{width:1280,height:900},{width:900,height:900},{width:740,height:360},{width:651,height:900},{width:650,height:900},{width:390,height:844},{width:320,height:844},{width:1280,height:900,zoom:2}]) {
      await send('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:viewport.width<=740});
      await evaluate(`document.body.style.zoom=${JSON.stringify(viewport.zoom?'2':'')}`);
      for(const locked of [true,false]) {
        // Presentation state only; server authority and serialized values remain untouched.
        // The ordinary native workflow separately verifies real login and saves.
        await evaluate(`globalThis.alignmentLocked=${locked};document.getElementById('station-settings-lock').disabled=${locked};`);
        await section('radio-pins');
        for(const engine of ['direct','i2c']) {
          await evaluate(`{const e=document.getElementById('config').elements.rf_engine;e.value='${engine}';e.dispatchEvent(new Event('change',{bubbles:true}));document.getElementById('station-settings-lock').disabled=${locked};}`);
          await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
          const rf=await geometry('rf');
          await evaluate('document.querySelector("#gps-settings details").open=false');
          assert.equal(await evaluate('document.querySelector("[data-gps=pps_offset_ns]").checkVisibility()'),false,'collapsed GPS details do not render controls');
          await evaluate('document.querySelector("#gps-settings details").open=true');
          const gps=await geometry('gps');
          const state={...viewport,locked,engine,rf,gps};measurements.push(state);
          if(!baseline) {
            const columns=viewport.width<=650?1:3;
            assert.ok(rf.filter(r=>!r.hidden).every(r=>r.disabled===locked),'RF locked/unlocked presentation retains native disabled state');
            aligned(rf,columns===1?1:engine==='direct'?3:2,'RF');aligned(gps,columns,'GPS');
            const rfText=rf.filter(r=>!r.hidden);
            if(columns!==1&&Math.max(...rfText.map(r=>r.textHeight))-Math.min(...rfText.map(r=>r.textHeight))<=1.5)assert.ok(Math.max(...rfText.map(r=>r.textY))-Math.min(...rfText.map(r=>r.textY))<=1.5,'RF label text aligns');
            assert.equal(rf.filter(r=>!r.hidden).length,engine==='direct'?3:2,'conditional RF field uses no layout space');
            assert.ok(rf.filter(r=>!r.hidden).every(r=>r.form==='config'),'external controls retain form association');
            if(engine==='i2c'&&columns!==1) {
              const [a,b]=rf.filter(r=>!r.hidden);
              assert.ok(Math.abs(a.width-b.width)<=1.5,'Si5351 controls share available columns');
              const parent=await evaluate(`document.querySelector('[name=rf_engine]').closest('.fields').getBoundingClientRect().width`);
              assert.ok(Math.abs(b.x+b.width-a.x-parent)<=2,'no empty engine column');
            }
            assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'no horizontal overflow');
            if(viewport.width===651||viewport.zoom||viewport.width===390) {
              const offsets=gps.map(r=>r.y-r.labelY);
              await evaluate(`{const caption=document.querySelector('[data-gps="pps_offset_ns"]').closest('label').querySelector('.field-caption');globalThis.alignmentCaption=caption.textContent;caption.append(' including a deliberately long receiver configuration description');const error=document.createElement('small');error.id='alignment-inline-error';error.className='field-result error';error.role='alert';error.textContent='Review this capture allowance before saving. The entered draft is preserved.';document.querySelector('[data-gps="capture_uncertainty_us"]').closest('label').append(error);}`);
              const expanded=await geometry('gps');aligned(expanded,columns,'GPS with wrapped label and inline error');
              for(const i of [9,10,11])assert.ok(Math.abs((expanded[i].y-expanded[i].labelY)-offsets[i])<=1.5,'inline error stays below the shared control track');
              assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'wrapped help has no overflow');
              await evaluate(`document.querySelector('[data-gps="pps_offset_ns"]').closest('label').querySelector('.field-caption').textContent=alignmentCaption;document.getElementById('alignment-inline-error').remove()`);
            }

          }
          if(viewport.width===1280||viewport.width===390||viewport.width===740) {
            await evaluate('document.querySelector("[name=rf_engine]").closest(".fields").scrollIntoView({block:"start"})');
            if(process.env.UI_REVIEW_NO_CAPTURE!=='1') {
              const shot=await send('Page.captureScreenshot',{format:'png'});
              await writeFile(path.join(output,`${baseline?'before':'after'}-rf-${engine}-${viewport.width}-${viewport.zoom||1}-${locked?'locked':'unlocked'}.png`),Buffer.from(shot.data,'base64'));
              await evaluate('document.querySelector("#gps-settings details .fields").scrollIntoView({block:"start"})');
              const gpsShot=await send('Page.captureScreenshot',{format:'png'});
              await writeFile(path.join(output,`${baseline?'before':'after'}-gps-${engine}-${viewport.width}-${viewport.zoom||1}-${locked?'locked':'unlocked'}.png`),Buffer.from(gpsShot.data,'base64'));
            }
          }
        }
      }
    }
  } finally {
    await writeFile(path.join(output,baseline?'before-geometry.json':'after-geometry.json'),JSON.stringify(measurements,null,2)+'\n');
    await evaluate(`api=alignmentApi;{const o=JSON.parse(${JSON.stringify(original)});document.body.style.zoom='';document.getElementById('config').elements.rf_engine.value=o.engine;syncRfEngine();document.getElementById('config').elements.rf_gp.value=o.rf;for(const [key,value]of o.gps)document.querySelector('[data-gps="'+key+'"]').value=value;document.querySelector('#gps-settings details').open=false;controls(online);}`);
    await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  }
  assert.deepEqual(await evaluate('alignmentWrites'),[],'geometry and engine-switching checks issue no mutations');
  console.log(baseline?'Recorded RF/GPS baseline geometry and renders':'PASS RF/GPS row geometry, conditional columns, locked/unlocked, breakpoints, zoom and native form association');
}
