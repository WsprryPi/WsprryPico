import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {hkdf} from '@noble/hashes/hkdf.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';
const text = (s) => new TextEncoder().encode(s);
const hexBytes = (s) => {
  if (!/^[0-9a-f]{32}$/.test(s)) throw new Error('Invalid device identity');
  return Uint8Array.from(s.match(/../g), (b) => parseInt(b, 16));
};
const b64 = (b) => btoa(String.fromCharCode(...b)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64 = (s) => {
  if (!/^[A-Za-z0-9_-]{43}$/.test(s)) throw new Error('Invalid public key');
  const b = Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + '='), (c) => c.charCodeAt(0));
  if (b64(b) !== s) throw new Error('Invalid public key');
  return b;
};
const join = (...parts) => {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0; for (const p of parts) { out.set(p, at); at += p.length; } return out;
};
const random = (n) => crypto.getRandomValues(new Uint8Array(n));
const hex = (b) => [...b].map((c) => c.toString(16).padStart(2, '0')).join('');
export function recoveryKey() {
  const pair = x25519.keygen();
  return {secret: pair.secretKey, public: b64(pair.publicKey), nonce: hex(random(16))};
}
export function recoverySeal(key, start, device, phrase) {
  if (start.device_id !== device || !['erase', 'reset provisioning'].includes(phrase))
    throw new Error('Invalid reset confirmation');
  let shared, derived, plain;
  try {
    const request = hex(random(16)), nonce = random(12);
    const aad = join(text('WsprryPico/Recovery/1\0'), hexBytes(device), hexBytes(start.boot_id),
      hexBytes(start.slot_id), unb64(key.public), unb64(start.pico_public_key),
      hexBytes(key.nonce), hexBytes(request));
    shared = x25519.getSharedSecret(key.secret, unb64(start.pico_public_key));
    if (shared.every((b) => b === 0)) throw new Error('Invalid public key');
    derived = hkdf(sha256, shared, sha256(aad), text('WsprryPico recovery AEAD v1'), 32);
    plain = text('1:1:' + phrase);
    const box = chacha20poly1305(derived, nonce, aad).encrypt(plain);
    return {version: 1, device_id: device, boot_id: start.boot_id, slot_id: start.slot_id,
      request_id: request, aead_nonce: b64(nonce), ciphertext: b64(box.slice(0, -16)),
      tag: b64(box.slice(-16))};
  } finally { key.secret.fill(0); shared?.fill(0); derived?.fill(0); plain?.fill(0); }
}
