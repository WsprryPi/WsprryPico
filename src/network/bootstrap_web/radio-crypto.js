import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {hkdf} from '@noble/hashes/hkdf.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';

const utf8 = new TextEncoder(), decoder = new TextDecoder('utf-8', {fatal:true});
export const text = value => utf8.encode(value);
export const join = (...parts) => {
  const result = new Uint8Array(parts.reduce((size, part) => size + part.length, 0));
  let at = 0;
  for (const part of parts) { result.set(part, at); at += part.length; }
  return result;
};
export const hex = bytes => [...bytes].map(b => b.toString(16).padStart(2, '0')).join('');
export const unhex = (value, size) => {
  if (typeof value !== 'string' || !new RegExp(`^[0-9a-f]{${size*2}}$`).test(value)) throw new Error('Invalid Pico identity');
  return Uint8Array.from({length:size}, (_,i) => parseInt(value.slice(i*2,i*2+2),16));
};
export const b64 = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const unb64 = value => {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(value)) throw new Error('Invalid Pico key');
  const result = Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/') + '='), c => c.charCodeAt(0));
  if (result.length !== 32 || b64(result) !== value) throw new Error('Invalid Pico key');
  return result;
};
const u64 = value => {
  const number = BigInt(value);
  if (number < 0n || number > 0xffffffffffffffffn) throw new Error('Invalid session sequence');
  const bytes = new Uint8Array(8);
  new DataView(bytes.buffer).setBigUint64(0, number);
  return bytes;
};
const equal = (a,b) => a.length === b.length && a.every((v,i) => v === b[i]);
const nonce = sequence => join(new Uint8Array(4),u64(sequence));
export const header = (session,sequence) => join(text('CR01'),unhex(session,16),u64(sequence));
export const retirementSelector = (identity,session) => hex(sha256(join(text('WsprryPico/Consumer-Recovery/1/selector\0'),unhex(identity.device_id,16),unhex(identity.boot_id,16),unhex(session,16))).subarray(0,16));
export function transcript(pending, grant) {
  return join(text('WsprryPico/Consumer-Radio/1\0'),unhex(grant.device_id,16),unhex(grant.boot_id,16),
    unhex(grant.session_id,16),u64(grant.generation),unb64(pending.public_key),unb64(grant.public_key),
    unhex(grant.challenge,16),unhex(pending.nonce,16));
}
export function begin(secret, randomNonce) {
  const owned = secret || x25519.utils.randomSecretKey();
  try {
    const pair = x25519.keygen(owned);
    const bytes = randomNonce || crypto.getRandomValues(new Uint8Array(16));
    return {secret:pair.secretKey,public_key:b64(pair.publicKey),nonce:hex(bytes)};
  } catch (error) { owned.fill(0); throw error; }
}
export function authenticate(pending, grant, password, identity, recovery) {
  let shared, passwordBytes, passwordHash, secret, login;
  try {
    if (grant.version !== 1 || grant.device_id !== identity.device_id || grant.boot_id !== identity.boot_id ||
        grant.generation !== identity.generation || grant.login_ms !== (recovery ? 5000 : 30000) ||
        typeof password !== 'string' || !/^[\x20-\x7e]{8,63}$/.test(password)) throw new Error('Invalid radio login');
    let binding = transcript(pending,grant);
    if (recovery) {
      if (!grant.recovery || Object.keys(grant.recovery).sort().join(',') !== 'authority,interface,target_selector' ||
          grant.recovery.target_selector !== recovery.target_selector || grant.recovery.authority !== recovery.authority ||
          grant.recovery.interface !== recovery.interface || !['ap','station'].includes(recovery.interface) ||
          typeof recovery.authority !== 'string' || !/^[a-z0-9.:-]{1,72}$/.test(recovery.authority)) throw new Error('Recovery scope does not match');
      const authority = text(recovery.authority);
      const context = sha256(join(unhex(recovery.target_selector,16),new Uint8Array([recovery.interface === 'ap' ? 1 : 2,authority.length]),authority));
      binding = join(binding,text('WsprryPico/Consumer-Recovery/1\0'),context);
    }
    const digest = sha256(binding);
    shared = x25519.getSharedSecret(pending.secret,unb64(grant.public_key));
    if (shared.every(b => b === 0)) throw new Error('Invalid Pico key');
    passwordBytes = text(password); passwordHash = sha256(passwordBytes);
    secret = join(shared,passwordHash);
    login = hkdf(sha256,secret,digest,text('WsprryPico radio login v1'),32);
    const keys = hkdf(sha256,secret,digest,text('WsprryPico radio traffic v1'),64);
    const h = header(grant.session_id,0n);
    const finish = join(h,chacha20poly1305(login,nonce(0n),join(digest,h)).encrypt(digest));
    return {finish,keys,digest,session:grant.session_id};
  } finally {
    pending.secret.fill(0); shared?.fill(0); passwordBytes?.fill(0); passwordHash?.fill(0); secret?.fill(0); login?.fill(0);
  }
}
export function seal(state, sequence, value) {
  const plaintext = text(JSON.stringify(value));
  try {
    if (plaintext.length > 32724) throw new Error('Radio request exceeds the device limit');
    const h = header(state.session,sequence);
    return join(h,chacha20poly1305(state.keys.subarray(0,32),nonce(sequence),join(state.digest,h)).encrypt(plaintext));
  } finally { plaintext.fill(0); }
}
export function open(state, sequence, packet) {
  const h = header(state.session,sequence);
  if (packet.length < 44 || packet.length > 32768 || !equal(packet.subarray(0,28),h)) throw new Error('Radio response identity does not match');
  const plaintext = chacha20poly1305(state.keys.subarray(32),nonce(sequence),join(state.digest,h)).decrypt(packet.subarray(28));
  try { return JSON.parse(decoder.decode(plaintext)); }
  finally { plaintext.fill(0); }
}
export function clear(state) { state?.keys.fill(0); state?.digest.fill(0); }
