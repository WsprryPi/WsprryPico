// Stable named fixture identities and original port offsets; no process side effects.
const rows=[
  ['consumer-lan',null,false],['blank','blank',true],
  ['network-only','network',true],['unavailable','unavailable',true],
  ['consumer-ap',null,true],['engineering',null,false],
  ['first-use-network','first-use:network',false],['first-use-usb','first-use:usb',false],
  ['first-use-overlay','first-use:overlay',false],['first-use-network-backing','first-use:network-backing',false]
];
export const definitions=Object.freeze(rows.map(([name,profile,ap],index)=>Object.freeze({name,profile,ap,index})));
export function parseProfileSelection(args,firstPort) {
  if(!Array.isArray(args)||!args.every(value=>typeof value==='string'))throw TypeError('Fixture arguments must be strings');
  let names,messages=false;
  for(const argument of args){
    if(argument==='messages'){if(messages)throw Error('Duplicate messages mode');messages=true;}
    else if(argument.startsWith('--profiles=')){
      if(names!==undefined)throw Error('Duplicate profile selection');names=argument.slice(11).split(',');
    }else throw Error('Unknown fixture argument');
  }
  if(names&&(names.some(name=>!name)||new Set(names).size!==names.length))throw Error('Empty or duplicate profile selection');
  const selected=names?names.map(name=>{const definition=definitions.find(value=>value.name===name);if(!definition)throw Error('Unknown fixture profile');return definition;}):[...definitions];
  if(!Number.isInteger(firstPort)||firstPort<1||selected.some(value=>firstPort+value.index>65535))throw RangeError('Invalid fixture port range');
  return {selected,messages};
}
