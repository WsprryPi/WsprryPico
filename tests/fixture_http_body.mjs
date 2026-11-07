// Complete bounded production HTTP output by acknowledging the existing fixture.
// Neither the 100-step service budget nor production deadlines/limits are changed.
import assert from 'node:assert/strict';
export async function fixtureHttpBody(fixture,response) {
  const declared=response.headers.get('content-length');
  assert.match(declared??'',/^(0|[1-9][0-9]*)$/,'declared response length');
  const expected=Number(declared),socket=fixture.socket;
  assert.ok(Number.isSafeInteger(expected)&&expected<=1024*1024,'bounded fixture response');
  let bytes=Buffer.from(await response.arrayBuffer());
  // Each acknowledged 100-step burst can service at least 64 KiB of the current
  // fixture's streaming output. Size-derived admission avoids a four-burst cliff.
  for(let pump=0;bytes.length<expected&&pump<Math.ceil(expected/65536);++pump) {
    const previous=bytes.length;
    await fixture.command({op:'complete',socket});
    const result=await fixture.command({op:'wire',socket});
    const wire=Buffer.from(result.wire,'hex'),end=wire.indexOf('\r\n\r\n');
    assert.ok(end>=0,'complete HTTP header');
    bytes=wire.subarray(end+4);
    assert.ok(bytes.length>previous,'acknowledged response makes progress');
  }
  assert.equal(bytes.length,expected,'exact complete production Content-Length');
  return bytes;
}
