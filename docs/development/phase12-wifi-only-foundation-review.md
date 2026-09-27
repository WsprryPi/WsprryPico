# Phase 12 Wi-Fi-only foundation adversarial review

Status: **SOURCE FOUNDATION REVIEWED; CREDENTIAL FLOW AND TARGET ACCEPTANCE OPEN**.
This review covers the bounded source changes made after the operator approved
the [network-only exception](phase12-wifi-only-bootstrap-proposal.md) on
2026-09-26. It does not claim an implemented Wi-Fi credential form or a
physical BOOTSEL result. The current AP HTTP handler still returns `405`
for every non-GET request.

## First adversarial assessment and repairs

| Finding | Repair and affected check |
| --- | --- |
| An initial network-only journal admission could select credentials after an unprovisioned tombstone at generation 1 or later, contrary to the blank-generation-zero rule. | Restricted that transition to generation zero; the host test now rejects tombstone-to-network-only while retaining generation-one network-only and generation-two full-profile upgrade. `provisioning_tests` passes. |
| The journal's validation of a temporary parsed network profile released a password-bearing string without explicit scrubbing. | Added a validation helper that scrubs the parsed profile on success. The storage failure and reboot tests pass. |
| The browser `seal()` path scrubbed keys only on success, leaving an ephemeral key alive after a malformed peer key or crypto failure. | Moved key and plaintext cleanup into `finally`; added a malformed-peer negative test. The synthetic vector and tamper tests pass. |
| The browser package's build script referenced a nonexistent `app.js`, so the proposed pinned code could not be bundled reproducibly. | Made it build the crypto candidate into ignored `build/bootstrap-crypto.js`; `npm test` and `npm run build` pass. Added pinned provenance and MIT attribution. The bundle is not served yet. |
| The roadmap and older design review still called the network-only exception unapproved after the operator's explicit approval. | Updated their statuses, the field-access exception note and the new implementation prompt; checked nine edited documents for broken local links. |

## Reassessment and evidence boundary

The second source assessment found no enabled credential-write route. The
`PicoBootstrapServer` still dispatches through the GET-only
`bootstrap_http_wire`; neither a physical grant nor a browser form is wired to
the target. The new profile source is device-bound and selects generation 1
from a virgin journal, rejects a post-tombstone bootstrap and permits a later
full-profile generation 2. Runtime network-only mode suppresses legacy
schedules and TLS deployment credentials. The USB-local BOOTSEL probe is
read-only, requires idle/inactive output, uses SDK flash-safe coordination,
and retains a failure result rather than treating it as a button reading.

Validation on this source: 88/88 host CTests passed with the full Xcode
compiler and macOS 26.5 SDK environment; `npm test`, `npm run build`, the
RF-inhibited `WsprryPico` cross-build, image heap/stack checks,
`network_transport_contract_tests.py`, `git diff --check` and the nine-document
local-link check passed. The default shell's command-line SDK fails three
temporary native-link tests on macOS 27 `.tbd` architecture entries; rerunning
the full suite with the selected Xcode compiler resolves that environment
failure. `WsprryPico-StandaloneRF` did not cross-build in this SDK copy because
BTstack headers are absent; no RF target was flashed.

Open implementation gates remain the exact runtime BOOTSEL physical/core-1
proof, AP-local mutating protocol, Pico-side independent AEAD vector,
transactional AP/STA trial and commit, browser page, stable AP withdrawal,
failed-join/response-loss tests and selected-iPhone acceptance. The
[probe record](phase12-wifi-only-bootsel-gate.md) defines the next target
measurement. No source or host result closes Phase 12, Stage B or RF work.
