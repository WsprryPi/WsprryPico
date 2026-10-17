import assert from 'node:assert/strict';

// Optional pinned scanner supplied by the test operator; never a product dependency.
export async function scanAccessibility(cdp,axeSource) {
  // Test instrumentation runs in an isolated DevTools world. Production
  // CSP headers and admission remain unchanged; no scanner is shipped.
  const {frameTree}=await cdp.send('Page.getFrameTree');
  const world=await cdp.send('Page.createIsolatedWorld',{frameId:frameTree.frame.id,worldName:'p1519-accessibility'});
  const injected=await cdp.send('Runtime.evaluate',{expression:axeSource,contextId:world.executionContextId});
  assert.ok(!injected.exceptionDetails,'axe injection in isolated test world');
  const scan=await cdp.send('Runtime.evaluate',{contextId:world.executionContextId,awaitPromise:true,returnByValue:true,
    expression:`axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}).then(r=>({version:axe.version,url:location.href,viewport:{width:innerWidth,height:innerHeight},violations:r.violations,incomplete:r.incomplete,passes:r.passes.map(x=>x.id),inapplicable:r.inapplicable.map(x=>x.id)}))`});
  assert.ok(!scan.exceptionDetails,'axe scan completed');
  assert.equal(scan.result.value.version,'4.14.0');
  return scan.result.value;
}
