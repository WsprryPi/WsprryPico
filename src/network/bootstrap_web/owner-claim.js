import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {hkdf} from '@noble/hashes/hkdf.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';

const text = (value) => new TextEncoder().encode(value);
const join = (...parts) => {
  const out = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
  let at = 0;
  for (const part of parts) { out.set(part, at); at += part.length; }
  return out;
};
const hex16 = (value) => {
  if (typeof value !== 'string' || value.length !== 32 || !/^[0-9a-f]{32}$/.test(value))
    throw new Error('invalid claim identifier');
  return Uint8Array.from({length: 16}, (_, i) => parseInt(value.slice(2 * i, 2 * i + 2), 16));
};
const b64u = (bytes) => btoa(String.fromCharCode(...bytes))
  .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const fixed = (value, size) => {
  if (!(value instanceof Uint8Array) || value.length !== size)
    throw new Error('invalid claim key');
  return value;
};
const ascii = (value, minimum, maximum) => {
  if (typeof value !== 'string' || value.length < minimum || value.length > maximum ||
      [...value].some((c) => c.charCodeAt(0) < 32 || c.charCodeAt(0) > 126))
    throw new Error('invalid claim input');
  return text(value);
};
const sourceAndGeneration = (source, generation) => {
  if (![0, 2, 4, 5].includes(source) || typeof generation !== 'string' ||
      !/^(0|[1-9][0-9]*)$/.test(generation)) throw new Error('invalid claim source');
  const n = BigInt(generation);
  if (generation !== n.toString() || n > 0xffffffffffffffffn ||
      (source === 0 ? n !== 0n : n === 0n ||
      n === 0xffffffffffffffffn)) throw new Error('invalid claim generation');
  const bytes = new Uint8Array(8);
  let remaining = n;
  for (let i = 7; i >= 0; --i) { bytes[i] = Number(remaining & 255n); remaining >>= 8n; }
  return {source: Uint8Array.of(source), generation: bytes};
};

export function claimTranscript(fields) {
  if (fields.origin !== 'http://192.168.4.1') throw new Error('wrong claim origin');
  const source = sourceAndGeneration(fields.source, fields.generation);
  const owner = fixed(fields.ownerPublicKey, 65);
  if (owner[0] !== 4) throw new Error('invalid owner point encoding');
  return join(text('WsprryPico/Owner-Claim/1\0'), hex16(fields.deviceId),
    hex16(fields.bootId), hex16(fields.slotId), text(fields.origin),
    source.source, source.generation, owner, fixed(fields.browserPublicKey, 32),
    fixed(fields.picoPublicKey, 32), hex16(fields.browserNonce),
    hex16(fields.requestId));
}

export function claimPlaintext({ssid, password, callsign, locator, powerDbm}) {
  const savedNetwork = ssid === '' && password === '';
  const network = ascii(ssid, savedNetwork ? 0 : 1, 32);
  const secret = ascii(password, savedNetwork ? 0 : 8, 63);
  try {
    if (typeof callsign !== 'string' || callsign.length < 3 || callsign.length > 6 ||
        [...callsign].some((c) => !((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9'))) ||
        typeof locator !== 'string' || locator.length !== 4 ||
        !/^[A-R]{2}[0-9]{2}$/.test(locator) ||
        ![0, 3, 7, 10, 13, 17, 20, 23, 27, 30, 33, 37, 40, 43, 47, 50, 53, 57, 60]
          .includes(powerDbm)) throw new Error('invalid station input');
    const padded = callsign[2] >= '0' && callsign[2] <= '9' ?
      callsign.padEnd(6, ' ') : (' ' + callsign).padEnd(6, ' ');
    if (!/^[ A-Z0-9][A-Z0-9][0-9][A-Z][ A-Z]{2}$/.test(padded))
      throw new Error('invalid WSPR callsign');
    return join(Uint8Array.of(network.length), network,
      Uint8Array.of(secret.length), secret,
      Uint8Array.of(callsign.length), text(callsign), text(locator),
      Uint8Array.of(powerDbm));
  } finally {
    network.fill(0);
    secret.fill(0);
  }
}

// A submit consumes the ephemeral browser secret even if validation or sealing
// fails. The caller owns and clears ordinary form fields after the attempt.
export function sealOwnerClaim(fields, browserSecret, nonce, settings) {
  let shared, key, plain;
  try {
    const aad = claimTranscript(fields);
    fixed(browserSecret, 32);
    fixed(nonce, 12);
    const derivedPublic = x25519.getPublicKey(browserSecret);
    if (derivedPublic.some((byte, i) => byte !== fields.browserPublicKey[i]))
      throw new Error('claim browser key mismatch');
    plain = claimPlaintext(settings);
    shared = x25519.getSharedSecret(browserSecret, fields.picoPublicKey);
    if (shared.every((byte) => byte === 0)) throw new Error('invalid shared secret');
    key = hkdf(sha256, shared, sha256(aad), text('WsprryPico owner claim AEAD v1'), 32);
    const sealed = chacha20poly1305(key, nonce, aad).encrypt(plain);
    return {ciphertext: b64u(sealed.slice(0, -16)), tag: b64u(sealed.slice(-16))};
  } finally {
    if (browserSecret instanceof Uint8Array) browserSecret.fill(0);
    shared?.fill(0);
    key?.fill(0);
    plain?.fill(0);
  }
}
