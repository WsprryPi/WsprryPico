# P12.8 generated TLS identity: execution and adversarial review

Status: **VALIDATED DISCONNECTED SOURCE; P12.8–P12.12 AND PHASE 12 OPEN**
(2026-09-27). This is a source checkpoint under the accepted
[P12.7 Safari/SoftAP contract](phase12-7-decision.md) and
[gated execution prompt](phase12-7-12-execution-prompt.md). It does not grant
hardware or RF authority.

## Executed prompt slice

In clean `devel`, add a Pico-side P-256 per-device CA and a distinct P-256
station server key/certificate, using the pinned Mbed TLS library and a
caller-supplied trusted UTC value. Bound input identity, hostname, UTC and PEM
sizes. Set a ten-year CA and one-year server calendar expiry, server DNS SAN,
server-auth EKU, key usages and full device ID in both distinguished names.
Before use or persistence, verify both key pairs, algorithms, identities,
serials, validity at the supplied UTC, the CA self-signature, chain and exact
server SAN. Confirm that real generated PEMs fit Consumer-Profile/1. Scrub
secrets on all failures. Keep the code disconnected from the live claim route
until trusted clock, target resource and activation gates are met. Use focused
host tests and the RF-inhibited Pico cross-build, then review, repair, reassess, commit
and push a truthful checkpoint.

## Implemented boundary

- `generate_consumer_tls` creates fresh CA and server P-256 keys and
  certificates after a bounded UTC and entropy seed. It rejects an invalid
  full ID or noncanonical local hostname, and produces no reusable key after
  failure. A caller must prove that its UTC source is trusted; a plausible
  number alone is insufficient.
- `validate_consumer_tls` checks both key pairs, P-256/SHA-256, exact full-ID
  binding, exact one-name DNS SAN, server-auth EKU, key usage, nonzero distinct
  serials, calendar expiry against the supplied UTC, CA self-signature and
  server chain. The generator invokes it before returning material.
- The canonical profile serializer checks that the actual generated PEMs fit
  the 2,304-byte TLS aggregate. The tested four-owner/four-client journal
  boundary remains the separate structural capacity proof.
- The generator and validator are compiled for the RF-inhibited Pico target
  but are not called by the AP server, profile journal or runtime. The linker
  may discard those unreferenced functions. Source 5 remains inert.

## First adversarial review and repairs

The initial review found five actionable issues: a reused output could retain
an old private key after failure; the serialized capacity-check copy was not
scrubbed; a failed date/certificate setup could leave partial output; direct
validator calls could parse oversized PEMs; and the CA self-signature was not
checked separately from server-chain validation. An initial root-chain check
was added, but the next adversarial assessment altered a CA signature and
proved that Mbed TLS did not verify the trusted root's own signature in that
call. The validator now hashes the CA certificate body and verifies its ECDSA
signature explicitly. Focused tests cover invalid identity/time, swapped key,
altered CA and server signatures, altered hostname, altered expiry, expiry
boundary, distinct fresh CAs, entropy failure, reused-output scrubbing and
leap-day one/ten-year expiry. The subsequent adversarial assessment found no
remaining issue inside this disconnected source slice.

The host build passed. The full host suite passed 108/109 inside the sandbox;
the one local-loopback `network_tls_tests` socket could not start there and
passed when rerun outside the sandbox, yielding 109/109 test results. The
default RF-inhibited `WsprryPico` Pico cross-build, changed-documentation
relative-link check and `git diff --check` passed. These are source and host
checks only.

## Remaining gates

The code has no trusted-clock admission, owner HTTP route, atomic consumer
journal commit, runtime consumer activation, renewal, client enrollment or
Safari setup. Target key-generation latency, heap/stack peaks and coexistence
have not been measured. No device was flashed or controlled. Host success and
a Pico cross-build do not establish physical commissioning acceptance.
An optional `WsprryPico-StandaloneRF` build was attempted; it stops before
these sources at its existing unconditional `gatt_transport.hpp` include
because that diagnostic target lacks the BTstack include path. The new
consumer TLS sources are linked only into the RF-inhibited field image.
