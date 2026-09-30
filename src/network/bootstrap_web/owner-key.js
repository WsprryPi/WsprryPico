import {p256} from '@noble/curves/nist.js';

// A separate flash literal keeps the locally pinned P-256 code within the
// compiler's literal size; the generated HTML streams it with the app script.
globalThis.WsprryPicoOwnerKey = Object.freeze({
  keygen: () => p256.keygen(),
  getPublicKey: (secret, compressed) => p256.getPublicKey(secret, compressed),
  sign: (message, secret) => p256.sign(message, secret),
  verify: (signature, message, publicKey) => p256.verify(signature, message, publicKey),
});
