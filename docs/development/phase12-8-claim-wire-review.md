# P12.8 claim wire and AEAD checkpoint: adversarial review

Status: **VALIDATED DISCONNECTED FOUNDATION; P12.8–P12.12 AND PHASE 12 OPEN**
(2026-09-27). The accepted [P12.7 decision](phase12-7-decision.md) remains the
consumer contract. The updated [execution prompt](phase12-7-12-execution-prompt.md)
orders the remaining milestones. This checkpoint adds no owner HTTP route and
grants no RF or hardware authority.

## Implemented and checked

- [Owner-HTTP/1](../protocol/Owner-HTTP-v1.md) now defines the exact 261-byte
  claim AEAD AAD, compact 20–109-byte credential/station plaintext, fixed
  `pool.ntp.org` default, source/generation encoding and separate raw JSON
  versus decoded ciphertext limits. Claim start now has an exact response
  field set, including the numeric profile source needed to distinguish a
  virgin blank from a reset tombstone.
- The portable C++ builder and Safari-side JavaScript builder agree with an
  independent Python `hashlib`/`struct` SHA-256 transcript vector and exact
  plaintext bytes. The JavaScript helper seals a one-use X25519/HKDF/
  ChaCha20-Poly1305 envelope and clears its ephemeral secret and temporary
  key material. The Pico Mbed TLS adapter opens that same synthetic envelope,
  scrubs plaintext/key buffers and consumes its PSA key on the first attempt.
- Host tests cover altered device, boot, slot, owner point, browser/Pico point,
  browser nonce, request, source, generation, AEAD nonce, ciphertext and tag;
  changed bindings cannot open the original envelope. Plaintext minimum,
  maximum, malformed length, unsupported power and trailing-byte boundaries
  are checked. This is cross-implementation test evidence, not a live claim.
- The new Pico opener is compiled in the default RF-inhibited target build,
  but no route calls it. The owner-key on-curve check, live journal and output
  admission, physical slot, CA generation, atomic commit and activation remain
  separate required gates.

## First adversarial assessment, repairs and affected checks

| Finding | Repair and evidence |
| --- | --- |
| The prior execution packet still described the historical `fb091f8` image as installed and ended with SoftAP stopped, conflicting with Candidate A's `3f56f5e` diagnostic and the approved always-available consumer AP. | Corrected the prompt's image chronology, final AP state and roll-forward rule. The earlier network-only readback remains historical evidence. |
| A 1,024-byte raw JSON limit cannot carry an operation with 1,024 decoded sealed bytes after base64url expansion. | Owner-HTTP/1 now distinguishes raw JSON caps (4,096 ordinary, 6,144 advanced; 1,024 claim start/submit) from 1,024/2,048 decoded sealed-body caps. No owner handler exists yet; its parser must enforce both. |
| The claim transcript and plaintext were underspecified, and a public status label alone cannot distinguish virgin blank source 0 from reset tombstone source 2. | Fixed binary order, source registry, default time server, exact start response and public numeric `profile_source`. Python, C++ and browser vector checks pass. |
| Temporary C++/JavaScript plaintext copies could outlive an attempt. | Added C++ encoded-buffer destruction scrubbing, target plaintext/key scrubbing and JavaScript intermediate-buffer cleanup; affected C++/browser tests pass. |
| A browser could seal with an ephemeral private key unrelated to the point in the AAD, guaranteeing a confusing failed claim. | Browser sealer checks the derived public point before encryption, clears the secret on failure and tests this rejection. |
| JavaScript regular-expression end anchors admitted a trailing newline in some fields even though the C++ decoder rejects it. | Added explicit lengths/canonical decimal comparison and per-character ASCII checks, plus newline negatives. Browser tests pass. |
| The documented minimum plaintext length was miscounted as 19 bytes. | Corrected to 20 bytes and asserted 20- and 109-byte valid boundaries in C++ tests. |

## Validation and second adversarial assessment

- `owner_wire_tests`, `owner_claim_crypto_tests` and all three bootstrap
  browser tests pass. The pinned Pico 2 W default RF-inhibited image cross-build
  passes, including the new Pico adapter; linked topology reports an SRAM
  BOOTSEL callback and no core-1 launcher. This build was **not flashed**.
- The full host suite initially passed 103/107. Three unrelated subprocess
  tests failed because they inherited the Command Line Tools macOS 27 SDK;
  all three passed on rerun with the installed Xcode 26.5 SDK. The local TLS
  listener failed inside the filesystem/network sandbox and passed its single
  hardware-free rerun outside that sandbox. The new owner-claim crypto test
  also passes, giving a passing result for every registered test after the
  affected build. No device, button, credential or RF operation occurred in
  this checkpoint.
- The second assessment traced all claim transcript fields, one-use target
  key handling, minimum/maximum payloads, browser/C++ validator agreement and
  current route references. It found no further actionable defect within this
  disconnected slice. It does **not** claim P12.8 acceptance: no AP owner
  handler, live physical grant, owner session, generated CA/server certificate,
  consumer journal activation or Safari setup screen is implemented.

P12.9 guided Safari setup, P12.10 iPhone commissioning, P12.11 ownership and
recovery, and P12.12 Stage A closure remain open. Ordinary BOOTSEL
press-and-release actions will be needed for their future physical acceptance;
no timed button gesture is required of the person.
