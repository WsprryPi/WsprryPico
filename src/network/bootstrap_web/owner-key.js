import {p256} from '@noble/curves/nist.js';

// Separate flash asset keeps each C++ static string within the compiler's
// supported literal size while retaining the locally pinned P-256 code.
globalThis.WsprryPicoOwnerKey = Object.freeze({
  keygen: () => p256.keygen(),
  getPublicKey: (secret, compressed) => p256.getPublicKey(secret, compressed),
  sign: (message, secret) => p256.sign(message, secret),
  verify: (signature, message, publicKey) => p256.verify(signature, message, publicKey),
});
