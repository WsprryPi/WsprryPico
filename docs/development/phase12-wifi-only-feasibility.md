# Wi-Fi-only bootstrap contract feasibility record

Status: **SOURCE/HOST EVIDENCE ONLY; BOOTSEL AND IPHONE CRYPTO TARGET GATES OPEN**.
Date: 2026-09-26. Base: `devel` at `6136c5ef107df925b384d354f4502099d1c49327`.
The [read-only full-erase target result](phase12-generic-first-run-physical-result.md)
predates this proposed encrypted form and is not a credential-join result.

## Runtime BOOTSEL

The [Raspberry Pi button example](https://github.com/raspberrypi/pico-examples/blob/master/picoboard/button/button.c)
temporarily makes flash chip select high impedance, reads the QSPI CS input,
and restores it. Its own comment warns that the example fails if the other
core or XIP streamer accesses flash concurrently. It disables interrupts on
its calling core, but does not coordinate the other core. This firmware's RF
build launches core 1 from `src/rf/pico/worker.cpp`; the RF-inhibited dry-run
build has a different execution path. A simple copied sampler is therefore
unsuitable as the production contract.

The pinned SDK at `/private/tmp/wsprrypico-sdk-profile-079c6f3` is commit
`079c6f39023649b154152db30f1d781e884879bc`. Its `pico/flash.h` says
[`flash_safe_execute`](https://www.raspberrypi.com/documentation/pico-sdk/high_level.html)
enters a zone with calling-core interrupts disabled and the other core
blocked from flash, or returns an error if safety cannot be established.
The firmware already calls `flash_safe_execute_core_init()` on the launched
RF worker and uses `flash_safe_execute` for journal writes. The candidate
sampler is a short RAM-resident callback inside that same safe zone, only
while a blank bootstrap slot awaits its physical edge. It must restore the
exact prior QSPI CS override on every path. A non-success return, including
an exit timeout after the callback, must discard the sample and grant nothing.
No flash write may overlap the sample. A release edge must be observed from
fresh runtime samples; a held-at-boot level cannot count.

This is an **implementation candidate**, not proof. Before any credential
admission, inspect generated machine code and static data references for
flash/XIP access inside the callback; bound the interrupt-off and core-lockout
interval; measure actual no-button, press/release, timeout and failure paths
on the exact Pico 2 W build while the AP and CYW43 are active; and prove
no DHCP, DNS, HTTP, watchdog, RF worker or journal regression. The sampler
must run only in the blank network-only flow and fail closed if coordination
cannot be measured. The radio/AP and target timing were **not** exercised in
this contract pass.

## Browser crypto

The proposed locally bundled pure-JavaScript family is
[`@noble/curves`](https://github.com/paulmillr/noble-curves) for X25519,
[`@noble/hashes`](https://github.com/paulmillr/noble-hashes) for SHA-256,
HKDF and HMAC, and [`@noble/ciphers`](https://github.com/paulmillr/noble-ciphers)
for ChaCha20-Poly1305. Their project repositories identify MIT licenses
and document the needed primitives. The implementation slice must pin exact
versions and source hashes, inspect transitive source and licenses, make a
local offline bundle, record its byte size, and independently check it
against [the synthetic vector](../protocol/WiFi-Bootstrap-v1-vectors.json).
No third-party code was copied or vendored in this pass.

The [Web Cryptography specification](https://www.w3.org/TR/webcrypto/)
marks `crypto.subtle` as secure-context-only. Its `getRandomValues` method
does not carry that restriction, but generic API support is not proof that
the selected iPhone captive sheet supplies it. The page must test random
generation, required typed arrays, text/binary conversion and the bundled
X25519/HKDF/AEAD self-test **before** accepting a password. Failure shows
Safari instructions without a credential field. Test both automatic captive
sheet and Safari at the Pico's actual HTTP origin on the selected iPhone;
record model/iOS, exact image and result. Node's built-in crypto produced and
round-tripped the proposed synthetic vector, with the RFC 7748 Alice/Bob
X25519 shared secret `4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742`.
That validates the proposed bytes, not the future bundled browser code or
Pico implementation.

The Pico side also needs an explicit randomness review. The existing
`PicoRandomSource` uses the SDK `get_rand_64()` helper for access tokens;
the new ephemeral X25519 key, boot ID and slot ID must use a reviewed
RP2350 source with failure handling rather than assume this helper has the
required properties for a fresh key exchange.

## Generation and phase boundary

Current `ProfileStore` has two transactional 8192-byte slots, sources for
legacy/bootstrap, full runtime profile, unprovisioned and build bundle, and
a generation counter. `RuntimeProfile::load` rejects an absent or malformed
full profile. A network-only source therefore needs a new versioned source
record and runtime branch; relabeling a full profile or writing standalone
legacy Wi-Fi would be unsafe. A clean blank starts at generation 0. The
first network-only commit would be generation 1; a later full-profile upgrade
would be generation 2. No network-only journal code or target migration was
performed here.

The operator must approve the complete blank-AP exception and limits before
credential-accepting implementation. Target flash/BOOTSEL and AP/STA tests
remain separately authorized operations. The earlier native-Pi read-only AP
checks and iPhone captive pop-up do not verify this proposed encrypted form.
