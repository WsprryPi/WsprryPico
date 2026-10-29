// Generate checked-in operator scripts. Firmware builds verify their source
// hashes with Python and do not require Node or esbuild.
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const require=createRequire(new URL('../src/network/bootstrap_web/package.json',import.meta.url));
const esbuild=require('esbuild');
if(esbuild.version!=='0.28.2') throw Error('Operator assets require pinned esbuild 0.28.2');
const groups={
  'app.min.js':['udp-logging.js', 'operations.js','standalone-frequency.js','rf-calibration.js','amplifier-enable.js', 'amplifier-timing.js', 'filter-selector.js','gpio-drive.js','ntp-timeout.js','saved-progress.js','utc-datetime.js','message-schedule.js','app.js'],
  'config-validation.min.js':['config-validation.js'],
  'device-presentation.min.js':['device-presentation.js'],
  'organization.min.js':['organization.js']
};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const manifest={schema:'operator-assets/1',tool:'esbuild/0.28.2',target:'es2020',recipe_sha256:sha(await readFile(fileURLToPath(import.meta.url))),groups:{}};
for(const [output,files] of Object.entries(groups)) {
  const inputs=await Promise.all(files.map(async name=>{const bytes=await readFile(path.join(root,'src/network/web',name));return {name,bytes};}));
  // No module/IIFE wrapping or bundling: the four script scopes, boundaries and
  // shared top-level bindings remain the browser application's existing model.
  const result=await esbuild.transform(inputs.map(x=>x.bytes.toString('utf8')).join('\n'),{
    minify:true,target:'es2020',charset:'utf8',legalComments:'eof',treeShaking:false
  });
  if(result.warnings.length) throw Error(JSON.stringify(result.warnings));
  const bytes=Buffer.from(result.code);
  await writeFile(path.join(root,'src/network/web',output),bytes);
  manifest.groups[output]={inputs:Object.fromEntries(inputs.map(x=>[x.name,sha(x.bytes)])),sha256:sha(bytes),bytes:bytes.length};
}
await writeFile(path.join(root,'src/network/web/asset-build.json'),JSON.stringify(manifest,null,2)+'\n');
console.log('Generated four operator script blocks with pinned esbuild; source hashes recorded.');
