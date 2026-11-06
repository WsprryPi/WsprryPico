// Independent OS process inventory for selected native fixture ownership.
import assert from 'node:assert/strict';
import {readdir,readFile,readlink,realpath} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import path from 'node:path';
const execute=promisify(execFile);
export async function qualifyNativeChildren(driver,group,expected){
  const rows=[];
  if(process.platform==='linux'){
    for(const entry of await readdir('/proc')){
      if(!/^\d+$/.test(entry))continue;
      try{
        const text=await readFile(`/proc/${entry}/stat`,'utf8'),fields=text.slice(text.lastIndexOf(') ')+2).split(' ');
        if(Number(fields[2])===group&&Number(entry)!==group&&fields[0]!=='Z')rows.push({pid:Number(entry),parent:Number(fields[1]),executable:await readlink(`/proc/${entry}/exe`)});
      }catch(error){if(error.code!=='ENOENT'&&error.code!=='ESRCH')throw error;}
    }
  }else{
    const {stdout}=await execute('ps',['-axo','pid=,ppid=,pgid=,comm='],{timeout:5000});
    for(const line of stdout.split('\n')){const match=line.trim().match(/^(\d+)\s+(\d+)\s+(\d+)\s+(.*)$/);if(match&&Number(match[3])===group&&Number(match[1])!==group)rows.push({pid:Number(match[1]),parent:Number(match[2]),executable:match[4]});}
  }
  assert.equal(rows.length,expected.length,'OS inventory must contain exactly the selected native drivers');
  assert.deepEqual(rows.map(value=>value.pid).sort((a,b)=>a-b),expected.map(value=>value.driver_pid).sort((a,b)=>a-b));
  const binary=await realpath(driver);
  for(const row of rows){assert.equal(row.parent,group);assert.ok(row.executable===binary||(process.platform!=='linux'&&row.executable===path.basename(binary)),'each process must execute the actual candidate driver');}
}
