// Bounded authenticated configuration opt-in using the actual product client.
import {RadioClient} from '../src/network/bootstrap_web/radio-client.js';
let input='';
for await (const chunk of process.stdin) {
  input+=chunk;
  if(input.length>4096) throw new Error('Bounded private input required');
}
const {address,password,device_id,boot_id,allow}=JSON.parse(input);
if(!/^192\.168\.1\.[0-9]{1,3}$/.test(address) ||
   !/^[a-f0-9]{32}$/.test(device_id) || !/^[a-f0-9]{32}$/.test(boot_id) ||
   typeof allow!=='boolean') throw new Error('Explicit bench identity and flag required');
const client=new RadioClient((path,options)=>fetch('http://'+address+path,{
  ...options,headers:{...options?.headers,Origin:'http://'+address,'Sec-Fetch-Site':'same-origin'}
}),
  ()=>Date.now(),{authority:address,interface:'station'});
try {
  const id=await client.identity();
  if(id.device_id!==device_id || id.boot_id!==boot_id) throw new Error('Consumer identity mismatch');
  await client.login(password,id);
  const beforeResponse=await client.request('config');
  if(!beforeResponse.ok) throw new Error('Configuration read failed');
  const before=await beforeResponse.json();
  const response=await client.request('config/update','POST',{
    schema:'transmitter-config-update/1',target:{scope:'member',device_id,boot_id},
    mode:'merge',config:{allow_unqualified_frequency:allow}
  },beforeResponse.headers.get('etag'));
  const write=await response.json();
  if(!response.ok) throw new Error('Experimental flag update rejected: '+response.status+' '+JSON.stringify(write));
  const read=await client.request('config');
  const after=await read.json();
  if(!read.ok || (after.config.allow_unqualified_frequency??false)!==allow ||
     (after.config.allow_non_amateur_frequency??false)!==false) throw new Error('Experimental flag readback mismatch');
  process.stdout.write(JSON.stringify({identity:id,before,write,after})+'\n');
} finally {await client.logout();}
