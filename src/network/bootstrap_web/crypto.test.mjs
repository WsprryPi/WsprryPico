import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {x25519} from '@noble/curves/ed25519.js';
import {begin, seal, slotDigest, available} from './crypto.js';

const vector = JSON.parse(readFileSync(new URL('../../../docs/protocol/WiFi-Bootstrap-v1-vectors.json',
  import.meta.url)));
assert.equal(available(), true);
const pending = begin();
pending.secretKey = Buffer.from(vector.browser_private_key_hex, 'hex');
pending.browserPublicKey = vector.browser_public_key;
pending.requestNonce = vector.request_nonce;
assert.equal(Buffer.from(x25519.getPublicKey(pending.secretKey)).toString('base64url'),
  vector.browser_public_key);
const start = {boot_id: vector.boot_id, slot_id: vector.slot_id,
  pico_public_key: vector.pico_public_key};
const result = seal(pending, start, vector.device_id, 'LabNet', 'test-only-password',
  {requestId: vector.request_id, nonce: Buffer.from('000102030405060708090a0b', 'hex')});
assert.equal(result.submit.ciphertext, vector.ciphertext);
assert.equal(result.submit.tag, vector.tag);
assert.equal(result.ackTag, vector.ack_tag);
assert.equal(result.requestDigest, vector.request_id_digest_hex);
assert.equal(slotDigest(vector.slot_id), vector.slot_id_digest_hex);
assert.equal(Buffer.from(pending.secretKey).toString('hex'), '00'.repeat(32));
assert.throws(() => seal(begin(), start, vector.device_id, 'Bad\nSSID', 'test-only-password'));
const invalidPeer = begin();
assert.throws(() => seal(invalidPeer, {...start, pico_public_key: 'bad'},
  vector.device_id, 'LabNet', 'test-only-password'));
assert.equal(Buffer.from(invalidPeer.secretKey).toString('hex'), '00'.repeat(32));
for (const changed of [
  {device: '10112233445566778899aabbccddeeff'},
  {start: {...start, boot_id: '002132435465768798a9bacbdcedfe0f'}},
  {start: {...start, slot_id: '0031425364758697a8b9cadbecfd0e1f'}},
  {nonce: '00415263748596a7b8c9daebfc0d1e2f'},
  {requestId: '005162738495a6b7c8d9eafb0c1d2e3f'},
]) {
  const altered = {secretKey: Buffer.from(vector.browser_private_key_hex, 'hex'),
    browserPublicKey: vector.browser_public_key,
    requestNonce: changed.nonce || vector.request_nonce};
  const box = seal(altered, changed.start || start, changed.device || vector.device_id,
    'LabNet', 'test-only-password',
    {requestId: changed.requestId || vector.request_id,
      nonce: Buffer.from('000102030405060708090a0b', 'hex')});
  assert.notEqual(box.submit.tag, vector.tag);
}
console.log('bootstrap browser crypto vector passed');
