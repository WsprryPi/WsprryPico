// MIT. Synthetic proposal vectors only; no production keys or credentials.
import {
  createCipheriv, createDecipheriv, createHmac, createHash,
  createPrivateKey, createPublicKey, diffieHellman, hkdfSync,
} from 'node:crypto';

const h = (s) => Buffer.from(s, 'hex');
const b64u = (bytes) => Buffer.from(bytes).toString('base64url');
const privateKey = (raw) => createPrivateKey({
  key: Buffer.concat([h('302e020100300506032b656e04220420'), raw]),
  format: 'der', type: 'pkcs8',
});
const publicRaw = (key) => createPublicKey(key).export({format: 'der', type: 'spki'}).subarray(-32);

const deviceId = '00112233445566778899aabbccddeeff';
const bootId = '102132435465768798a9bacbdcedfe0f';
const slotId = '2031425364758697a8b9cadbecfd0e1f';
const requestNonce = '30415263748596a7b8c9daebfc0d1e2f';
const requestId = '405162738495a6b7c8d9eafb0c1d2e3f';
const browserSecret = h('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a');
const picoSecret = h('5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb');
const browserKey = privateKey(browserSecret);
const picoKey = privateKey(picoSecret);
const browserPublic = publicRaw(browserKey);
const picoPublic = publicRaw(picoKey);
const shared = diffieHellman({privateKey: browserKey, publicKey: createPublicKey(picoKey)});
const reverseShared = diffieHellman({privateKey: picoKey, publicKey: createPublicKey(browserKey)});
if (!shared.equals(reverseShared)) throw new Error('X25519 mismatch');
// The RFC 7748 Alice/Bob scalar pair is an independent X25519 cross-check.
if (shared.toString('hex') !==
    '4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742')
  throw new Error('RFC 7748 X25519 vector mismatch');

const transcript = Buffer.concat([
  Buffer.from('WsprryPico/WiFi-Bootstrap/1\0', 'utf8'),
  h(deviceId), h(bootId), h(slotId), browserPublic, picoPublic,
  h(requestNonce), h(requestId),
]);
const salt = createHash('sha256').update(transcript).digest();
const key = Buffer.from(hkdfSync('sha256', shared, salt,
  Buffer.from('WsprryPico network-only AEAD v1', 'utf8'), 32));
const ssid = Buffer.from('LabNet', 'ascii');
const password = Buffer.from('test-only-password', 'ascii');
const plaintext = Buffer.concat([Buffer.from([ssid.length]), ssid,
  Buffer.from([password.length]), password]);
const nonce = h('000102030405060708090a0b');
const cipher = createCipheriv('chacha20-poly1305', key, nonce, {authTagLength: 16});
cipher.setAAD(transcript, {plaintextLength: plaintext.length});
const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
const tag = cipher.getAuthTag();
const decipher = createDecipheriv('chacha20-poly1305', key, nonce, {authTagLength: 16});
decipher.setAAD(transcript, {plaintextLength: ciphertext.length});
decipher.setAuthTag(tag);
if (!Buffer.concat([decipher.update(ciphertext), decipher.final()]).equals(plaintext))
  throw new Error('AEAD round trip failed');
for (const wrongAAD of [false, true]) {
  const bad = createDecipheriv('chacha20-poly1305', key, nonce, {authTagLength: 16});
  const aad = Buffer.from(transcript);
  const authTag = Buffer.from(tag);
  if (wrongAAD) aad[0] ^= 1;
  else authTag[0] ^= 1;
  bad.setAAD(aad, {plaintextLength: ciphertext.length});
  bad.setAuthTag(authTag);
  let rejected = false;
  try { bad.update(ciphertext); bad.final(); } catch { rejected = true; }
  if (!rejected) throw new Error('tampering was accepted');
}
const ackTag = createHmac('sha256', key).update('WsprryPico network-only ACK v1', 'utf8')
  .update(transcript).digest();

const vector = {
  status: 'synthetic-proposal-not-implemented', version: 1,
  private_keys_are_test_only: true,
  device_id: deviceId, boot_id: bootId, slot_id: slotId,
  request_nonce: requestNonce, request_id: requestId,
  browser_private_key_hex: browserSecret.toString('hex'),
  pico_private_key_hex: picoSecret.toString('hex'),
  browser_public_key: b64u(browserPublic), pico_public_key: b64u(picoPublic),
  x25519_shared_hex: shared.toString('hex'),
  transcript_hex: transcript.toString('hex'),
  salt_sha256_hex: salt.toString('hex'),
  hkdf_key_hex: key.toString('hex'),
  aead_nonce: b64u(nonce), plaintext_hex: plaintext.toString('hex'),
  ciphertext: b64u(ciphertext), tag: b64u(tag), ack_tag: b64u(ackTag),
  slot_id_digest_hex: createHash('sha256').update(h(slotId)).digest('hex'),
  request_id_digest_hex: createHash('sha256').update(h(requestId)).digest('hex'),
};
process.stdout.write(`${JSON.stringify(vector, null, 2)}\n`);
