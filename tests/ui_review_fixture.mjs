import {fixtureHttpBody} from './fixture_http_body.mjs';
// Opt-in review server: maintained pages and production handlers, synthetic RAM
// journals and deterministic board/TCP boundaries. Never connects to hardware.
import assert from 'node:assert/strict';
import http from 'node:http';
import {appendFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import {Fixture} from './consumer_sessions.test.mjs';
import {deadlinePromise,preserveCleanup} from './browser_deadline.mjs';
import {parseProfileSelection} from './ui_fixture_profiles.mjs';

const executable = process.argv[2];
if (!executable) throw new Error('Usage: node tests/ui_review_fixture.mjs DRIVER [PORT] [OUTPUT] [messages] [--profiles=NAME,...]');
const firstPort = Number(process.argv[3] || 18719);
const {selected,messages}=parseProfileSelection(process.argv.slice(5),firstPort);
const output = path.resolve(process.argv[4] || 'build/ui-review');
await mkdir(output, {recursive:true});
const instances = [];
let stopping;
async function stop(primary) {
  if(stopping)return stopping;
  stopping=(async()=>{
    await preserveCleanup(primary,instances.flatMap(({server,fixture})=>[
      async()=>{
        if(!server)return;
        server.closeAllConnections();
        await deadlinePromise('fixture-http-close',(resolve,reject)=>{
          server.close(error=>error&&error.code!=='ERR_SERVER_NOT_RUNNING'?reject(error):resolve());
        },3000);
      },
      ()=>fixture.stop()
    ]));
    if(primary)throw primary;
  })();return stopping;
}
// Ownership and signal recovery apply during initialization, not only after READY.
for(const signal of ['SIGTERM','SIGINT'])process.once(signal,()=>{
  void stop().catch(error=>{console.error(error);process.exitCode=1;});
});


function decodeWire(wire) {
  const bytes = Buffer.from(wire, 'hex'), boundary = bytes.indexOf('\r\n\r\n');
  assert.ok(boundary >= 0);
  const lines = bytes.subarray(0, boundary).toString().split('\r\n');
  return {status:Number(lines.shift().split(' ')[1]), body:bytes.subarray(boundary+4),
    headers:lines.map(line => { const i=line.indexOf(':'); return [line.slice(0,i), line.slice(i+1).trim()]; })};
}

try {
  for (const {index,name,profile,ap} of selected) {
    if(stopping)throw Error('fixture initialization interrupted');
    // Native drivers stay inside this server's owned group. A parent must still
    // be able to kill every driver if this orchestrator cannot finish teardown.
    const fixture = new Fixture(executable,[],{processGroup:false});
    const instance={fixture,server:null};instances.push(instance);
    await fixture.time(1000);
    if (profile?.startsWith('first-use:')) await fixture.command({op:'first_use_profile',mode:profile.slice(10)});
    else if (profile) await fixture.command({op:'page_profile', mode:profile});
    if (messages) await fixture.command({op:'message_review'});
    if(stopping)throw Error('fixture initialization interrupted');
    let queue = Promise.resolve();
    const server = http.createServer((request, response) => {
      queue = queue.then(async () => {
        const started = performance.now(), chunks = [];
        if (request.url === '/.fixture-control' && request.method === 'POST' &&
            request.headers.host === `127.0.0.1:${firstPort+index}`) {
          const chunks=[]; for await (const chunk of request) chunks.push(chunk);
          const command=JSON.parse(Buffer.concat(chunks));
          assert(['reboot','flash_failure','frequency_state','accepted_job','field_clock','time','activate','forget_engineering_station','schedule_tick','message_review','sensitivity_saved_mutation'].includes(command.op));
          const result=await fixture.command(command);
          if (command.op === 'time') fixture.now = Number(command.ms);
          response.writeHead(200,{'Content-Type':'application/json'}); response.end(JSON.stringify(result)); return;
        }
        const authority=ap ? '192.168.4.1' : '192.168.1.53';
        const url=new URL(request.url,'http://'+authority);
        const resource=url.pathname+url.search;
        if(url.host!==authority){response.writeHead(403);response.end();return;}
        for await (const chunk of request) chunks.push(chunk);
        const body = Buffer.concat(chunks);
        let status, headers, bytes;
        if (name === 'engineering') {
          // The existing engineering adapter fixture supplies an authenticated
          // principal. TLS admission is covered separately by the TLS suite.
          const result = await fixture.command({op:'engineering_request', path:resource,
            method:request.method, b64:body.toString('base64url'), match:request.headers['if-match'] || ''});
          const decoded = decodeWire(result.wire);
          status=decoded.status; headers=Object.fromEntries(decoded.headers); bytes=decoded.body;
        } else {
          if (resource.endsWith('/start')) await fixture.time(fixture.now+1000);
          const result = await fixture.fetch(authority, ap, resource,
            {method:request.method, body, headers:{'Content-Type':request.headers['content-type'] || 'application/json'},
              marker:resource.startsWith('/api/owner/') ? 'Owner' : /^\/api\/(bootstrap|recovery)\//.test(resource) ? 'Bootstrap' : 'Radio'});
          bytes=await fixtureHttpBody(fixture,result);
          status=result.status; headers=Object.fromEntries(result.headers);
        }
        await appendFile(path.join(output,'requests.jsonl'), JSON.stringify({surface:name,
          method:request.method,path:resource,status,bytes:bytes.length,
          fixture_ms:performance.now()-started})+'\n');
        response.writeHead(status,headers); response.end(bytes);
      }).catch(error => { response.writeHead(500,{'Content-Type':'text/plain'}); response.end(error.message); });
    });
    instance.server=server;
    await deadlinePromise('fixture-http-listen',(resolve,reject) => {
      server.once('error',reject);server.listen(firstPort+index,'127.0.0.1',resolve);
      return()=>server.removeListener('error',reject);
    });
    console.log(JSON.stringify({name,url:ap?'http://192.168.4.1/':'http://192.168.1.53/',
      proxy:`http://127.0.0.1:${firstPort+index}`,pid:process.pid,driver_pid:fixture.process.pid,
      authority:ap ? '192.168.4.1' : '192.168.1.53',synthetic_password:profile ? undefined : 'test-password'}));
  }
  console.log('READY; configure an isolated test browser with the named loopback proxy and canonical URL. Direct loopback previews do not qualify commissioning or retirement. Stop with SIGINT/SIGTERM. No physical-network claim.');
} catch (error) {
  await stop(error);
  throw error;
}
