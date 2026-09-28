import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {hkdf} from '@noble/hashes/hkdf.js';
import {hmac} from '@noble/hashes/hmac.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';

const encoder = new TextEncoder();
const text = (value) => encoder.encode(value);
const join = (...parts) => {
  const out = new Uint8Array(parts.reduce((n, part) => n + part.length, 0));
  let at = 0;
  for (const part of parts) { out.set(part, at); at += part.length; }
  return out;
};
const fromHex = (value, length) => {
  if (typeof value !== 'string' || value.length !== length * 2 ||
      !/^[0-9a-f]+$/.test(value)) throw new Error('invalid hex field');
  return Uint8Array.from({length}, (_, i) => parseInt(value.slice(i * 2, i * 2 + 2), 16));
};
const hex = (bytes) => [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
const fromB64u = (value, length) => {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value))
    throw new Error('invalid base64url');
  const bytes = Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') +
    '='.repeat((4 - value.length % 4) % 4)), (c) => c.charCodeAt(0));
  if (bytes.length !== length || b64u(bytes) !== value) throw new Error('noncanonical base64url');
  return bytes;
};
const b64u = (bytes) => btoa(String.fromCharCode(...bytes))
  .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const random = (size) => {
  const bytes = new Uint8Array(size);
  globalThis.crypto.getRandomValues(bytes);
  return bytes;
};
const ascii = (value, minimum, maximum) => {
  if (typeof value !== 'string' || value.length < minimum || value.length > maximum ||
      !/^[\x20-\x7e]+$/.test(value)) throw new Error('invalid Wi-Fi input');
  return text(value);
};

export function available() {
  if (!globalThis.crypto || typeof globalThis.crypto.getRandomValues !== 'function' ||
      !globalThis.TextEncoder || !globalThis.Uint8Array || !globalThis.BigInt ||
      !globalThis.atob || !globalThis.btoa) return false;
  try {
    const sample = random(16);
    const alice = x25519.keygen();
    const bob = x25519.keygen();
    const shared = x25519.getSharedSecret(alice.secretKey, bob.publicKey);
    const reversed = x25519.getSharedSecret(bob.secretKey, alice.publicKey);
    const key = hkdf(sha256, shared, sha256(sample), text('self-test'), 32);
    const nonce = random(12);
    const box = chacha20poly1305(key, nonce, sample);
    const plaintext = text('ok');
    const opened = box.decrypt(box.encrypt(plaintext));
    const okay = hex(shared) === hex(reversed) && hex(opened) === hex(plaintext);
    alice.secretKey.fill(0); bob.secretKey.fill(0); shared.fill(0); reversed.fill(0);
    key.fill(0); plaintext.fill(0);
    return okay;
  } catch { return false; }
}

export function begin() {
  const pair = x25519.keygen();
  const requestNonce = hex(random(16));
  return {secretKey: pair.secretKey, browserPublicKey: b64u(pair.publicKey), requestNonce};
}

export function seal(pending, start, deviceId, ssidText, passwordText, fixed = {}) {
  const ssid = ascii(ssidText, 1, 32);
  const password = ascii(passwordText, 8, 63);
  const timeServer = fixed.timeServer === undefined ? undefined :
    ascii(fixed.timeServer, 1, 253);
  let shared, key, plain;
  try {
    const requestId = fixed.requestId || hex(random(16));
    const nonce = fixed.nonce || random(12);
    const picoPublic = fromB64u(start.pico_public_key, 32);
    const transcript = join(text('WsprryPico/WiFi-Bootstrap/1\0'),
      fromHex(deviceId, 16), fromHex(start.boot_id, 16), fromHex(start.slot_id, 16),
      fromB64u(pending.browserPublicKey, 32), picoPublic,
      fromHex(pending.requestNonce, 16), fromHex(requestId, 16));
    shared = x25519.getSharedSecret(pending.secretKey, picoPublic);
    if (shared.every((byte) => byte === 0)) throw new Error('invalid shared secret');
    key = hkdf(sha256, shared, sha256(transcript),
      text('WsprryPico network-only AEAD v1'), 32);
    plain = join(Uint8Array.of(ssid.length), ssid,
      Uint8Array.of(password.length), password,
      ...(timeServer ? [Uint8Array.of(timeServer.length), timeServer] : []));
    const sealed = chacha20poly1305(key, nonce, transcript).encrypt(plain);
    const ackTag = hmac(sha256, key,
      join(text('WsprryPico network-only ACK v1'), transcript));
    return {
      submit: {version: 1, device_id: deviceId, boot_id: start.boot_id,
        slot_id: start.slot_id, request_id: requestId, aead_nonce: b64u(nonce),
        ciphertext: b64u(sealed.slice(0, -16)), tag: b64u(sealed.slice(-16))},
      ackTag: b64u(ackTag), requestDigest: hex(sha256(fromHex(requestId, 16))),
    };
  } finally {
    pending.secretKey.fill(0); shared?.fill(0); key?.fill(0);
    ssid.fill(0); password.fill(0); timeServer?.fill(0); plain?.fill(0);
  }
}

export const slotDigest = (slotId) => hex(sha256(fromHex(slotId, 16)));
