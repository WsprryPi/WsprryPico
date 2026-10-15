// Authenticated wrappers around the existing transactional commissioning APIs.
// The inner setup transcripts retain their AP origin; the outer radio session
// is admitted and bound to the browser's actual station/AP origin by firmware.
import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {begin as beginNetwork, seal as sealNetwork} from './crypto.js';
import {sealOwnerClaim, claimPlaintext} from './owner-claim.js';
import {b64, hex, unhex} from './radio-crypto.js';

const random = size => crypto.getRandomValues(new Uint8Array(size));
const decodeKey = value => {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(value)) throw new Error('Invalid Pico key');
  const bytes = Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')+'='), c => c.charCodeAt(0));
  if (b64(bytes) !== value) throw new Error('Invalid Pico key');
  return bytes;
};
export async function setup(client, path, body) {
  const response = await client.request('consumer/setup' + path, body === undefined ? 'GET' : 'POST', body);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.code || result.error || 'Setup is busy or unavailable');
  return result;
}
export async function prepareNetwork(client, identity, settings) {
  const pending = beginNetwork();
  try {
    const started = await setup(client, '/api/bootstrap/v1/start', {version:1,device_id:identity.device_id,
      browser_public_key:pending.browserPublicKey,request_nonce:pending.requestNonce});
    if (started.version !== 1 || started.device_id !== identity.device_id || started.boot_id !== identity.boot_id)
      throw new Error('Pico identity changed. Log in again');
    const sealed = sealNetwork(pending, started, identity.device_id, settings.ssid, settings.password,
      {timeServer:settings.time_server});
    return {kind:'network',device:identity.device_id,generation:(BigInt(identity.generation)+1n).toString(),
      digest:sealed.requestDigest,submit:sealed.submit,ack:{version:1,device_id:identity.device_id,
        boot_id:started.boot_id,slot_id:started.slot_id,request_id:sealed.submit.request_id,ack_tag:sealed.ackTag}};
  } finally { pending.secretKey.fill(0); }
}
export async function prepareStation(client, identity, settings) {
  claimPlaintext({ssid:'',password:'',...settings}).fill(0);
  const owner = globalThis.WsprryPicoOwnerKey.keygen();
  const ownerPublic = globalThis.WsprryPicoOwnerKey.getPublicKey(owner.secretKey, false);
  owner.secretKey.fill(0);
  const pair = x25519.keygen(), browserNonce = hex(random(16));
  try {
    const started = await setup(client, '/api/owner/v1/claim/start', {version:1,device_id:identity.device_id,
      owner_public_key:b64(ownerPublic),browser_public_key:b64(pair.publicKey),browser_nonce:browserNonce,
      profile_source:5,generation:identity.generation});
    if (started.version !== 1 || started.device_id !== identity.device_id || started.boot_id !== identity.boot_id ||
        started.profile_source !== 5 || started.generation !== identity.generation ||
        started.browser_nonce !== browserNonce || started.browser_public_key !== b64(pair.publicKey) ||
        started.owner_key_sha256 !== hex(sha256(ownerPublic))) throw new Error('Pico setup identity changed');
    const requestId = hex(random(16)), nonce = random(12);
    const envelope = sealOwnerClaim({origin:'http://192.168.4.1',deviceId:identity.device_id,
      bootId:started.boot_id,slotId:started.slot_id,ownerPublicKey:ownerPublic,browserPublicKey:pair.publicKey,
      picoPublicKey:decodeKey(started.pico_public_key),browserNonce,requestId,source:5,generation:started.generation},
    pair.secretKey, nonce, {ssid:'',password:'',...settings});
    return {kind:'station',device:identity.device_id,generation:(BigInt(identity.generation)+1n).toString(),
      digest:hex(sha256(unhex(requestId,16))),submit:{version:1,device_id:identity.device_id,boot_id:started.boot_id,
        slot_id:started.slot_id,request_id:requestId,aead_nonce:b64(nonce),...envelope}};
  } finally { pair.secretKey.fill(0); }
}
export async function submitSetup(client, attempt) {
  if (attempt.sent) throw new Error('This save was already sent. Check its result before trying again');
  attempt.sent = true;
  const path = attempt.kind === 'network' ? '/api/bootstrap/v1/submit' : '/api/owner/v1/claim/submit';
  const result = await setup(client, path, attempt.submit);
  if (result.version !== 1 || result.state !== 'checking' || result.request_id_digest !== attempt.digest)
    throw new Error('The Pico did not confirm acceptance. Check the saved result');
}
export async function checkSetup(client, attempt) {
  const path = attempt.kind === 'network' ? '/api/bootstrap/v1/status' : '/api/owner/v1/claim/status';
  const status = await setup(client, path);
  if (attempt.device !== (await client.identity()).device_id) throw new Error('This is a different Pico');
  // The legacy bootstrap status uses a JSON number. Never label an uncertain
  // save as failed after JSON parsing rounded a uint64 generation.
  if (typeof status.generation === 'number' && !Number.isSafeInteger(status.generation))
    return 'unconfirmed';
  if (String(status.generation) === attempt.generation && status.request_id_digest === attempt.digest)
    return 'saved';
  if ((status.slot_state === 'terminal' &&
       (status.attempt_request_id_digest || status.request_id_digest) === attempt.digest) ||
      (status.slot_state === 'none' && BigInt(status.generation) + 1n === BigInt(attempt.generation)))
    return 'failed';
  return 'unconfirmed';
}
