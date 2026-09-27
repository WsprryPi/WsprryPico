# Phase 12 Wi-Fi-only foundation adversarial review

Status: **SOURCE FOUNDATION REVIEWED; CREDENTIAL FLOW AND TARGET ACCEPTANCE OPEN**.
This review covers the bounded source changes made after the operator approved
the [network-only exception](phase12-wifi-only-bootstrap-proposal.md) on
2026-09-26. It does not claim an implemented Wi-Fi credential form or a
complete second-core BOOTSEL result. The current AP HTTP handler still returns `405`
for every non-GET request.

## First adversarial assessment and repairs

| Finding | Repair and affected check |
| --- | --- |
| An initial network-only journal admission could select credentials after an unprovisioned tombstone at generation 1 or later, contrary to the blank-generation-zero rule. | Restricted that transition to generation zero; the host test now rejects tombstone-to-network-only while retaining generation-one network-only and generation-two full-profile upgrade. `provisioning_tests` passes. |
| The journal's validation of a temporary parsed network profile released a password-bearing string without explicit scrubbing. | Added a validation helper that scrubs the parsed profile on success. The storage failure and reboot tests pass. |
| The browser `seal()` path scrubbed keys only on success, leaving an ephemeral key alive after a malformed peer key or crypto failure. | Moved key and plaintext cleanup into `finally`; added a malformed-peer negative test. The synthetic vector and tamper tests pass. |
| The browser package's build script referenced a nonexistent `app.js`, so the proposed pinned code could not be bundled reproducibly. | Made it build the crypto candidate into ignored `build/bootstrap-crypto.js`; `npm test` and `npm run build` pass. Added pinned provenance and MIT attribution. The bundle is not served yet. |
| The roadmap and older design review still called the network-only exception unapproved after the operator's explicit approval. | Updated their statuses, the field-access exception note and the new implementation prompt; checked nine edited documents for broken local links. |

## Portable slot and wire continuation

After the first checkpoint, the portable `BootstrapSlot` and strict start,
submit and acknowledgement envelope parsers were added without connecting
them to `PicoBootstrapServer`. An adversarial pass found that an early terminal
slot retained the full public transcript after commit. It now clears the
binding, raw request ID and ciphertext digest at terminal transition, leaving
only the bounded request digest and a committed flag; the eventual target
adapter must retain and verify the derived acknowledgement tag separately.
The pass also found that generic HTTP parsing could allocate a large body
before a bootstrap route rejected its 512-byte limit. The parser now rejects
oversize bootstrap bodies at header parse time. Copy/move of the one-slot
authority object is disabled. Focused tests cover bounce, held/stale button,
unsafe sampling, expiration, competing start, exact IDs, single use, terminal
retention, wrong Host/Origin/content type, unknown/duplicate JSON fields,
noncanonical base64url and preallocation body rejection.

The candidate captive page is also bundled locally but is **not served** by
firmware. Its browser test exercises first load, one physical-confirmation
request, gated credential entry, encrypted JSON submit, durable-success
status, acknowledgement and a capability fallback. An adversarial page pass
found that an encryption exception could leave the page offering a retry with
an already consumed browser key; that path now starts a fresh attempt. A
rebooted committed device may legitimately clear the request digest, so the
page can reconcile a durable generation and connected address without that
digest while still rejecting a different non-null digest. A second page pass
found that a changed slot could leave the original page waiting indefinitely,
and that a postcommit disconnect needed its own state. The page now identifies
a competing slot before credential entry and distinguishes **Wi-Fi saved;
connection lost** from **Network connected**. The page avoids
browser-persistent secrets, external scripts, setup codes and certificate
prompts. Its rendered layout and selected-iPhone capabilities remain target
gates; source and mock-browser tests cannot establish those behaviors.

## Reassessment and evidence boundary

The continuation adversarial pass found three actionable source/documentation
gaps: a failed PSA key-destroy result was ignored; the Pico test did not
tamper the ciphertext or cover a valid AEAD tag over invalid credential
bytes; and the top-level project documents still described the approved
network-only exception as merely proposed or left the earlier iPhone captive
observation ambiguous. The crypto path now fails closed on key-destroy
failure, the negative cases run against the vector, and README, CONTRACT and
architecture describe the exception and its current GET-only boundary.
The second assessment found no remaining actionable issue within this
disabled-route foundation. It did not clear the physical and transaction
gates listed below.

The independent Pico-side crypto adapter now reproduces the synthetic browser
vector using the pinned Mbed TLS/PSA implementation: X25519 public key,
authenticated plaintext and derived acknowledgement verifier agree. The
focused host test rejects replay, changes to each transcript field, ciphertext, tag and
nonce, an all-zero browser public key and an authenticated but invalid binary
credential payload. Its ephemeral PSA key is consumed by the first open
attempt; failed key destruction now fails closed. The adapter is compiled into
the RF-inhibited image but has no caller in its HTTP route. This validation
does not prove target entropy, heap or concurrency under an enabled route.

The first physical continuation used an exact serial-targeted diagnostic
flash. Thirty released-button BOOTSEL probes passed, including twenty during
77 successful open-AP GETs from isolated `wspr5` `wlan2`. After the separate
core-1 attempt, the standard image was restored and a 50-second USB probe
observed nine consecutive held-button samples followed by release; all 100
safe-zone calls succeeded. The final Pico read retained erased profile/access
state, inactive output and an empty job. The [target record](phase12-wifi-only-bootsel-gate.md)
names both images and their limits. The temporary Pi AP profile was removed.

The first opt-in RF-inhibited core-1 diagnostic was flashed under separate
exact-image authority. It booted, but two `BOOTSEL PROBE` calls returned
`core1_unready`, so no second-core BOOTSEL sampling was attempted. Adversarial
review found the diagnostic supplied a 4-KiB stack to a startup guard that
requires a 4-KiB reserve plus working room; this prevents the core-1 entry
from publishing readiness. The repaired candidate supplies an 8-KiB stack and
passes a fresh cross-build plus both-core stack and heap link checks. It then
passed 20 released-button safe-zone probes on Candidate A, with the flash-reading
core advancing across every call while the isolated Pi completed 52 open-AP
GETs without failure. The former GET-only image was restored and verified.
This bounded result does not prove a physical press transition with core 1
active; the target gate remains open.

The core-1 adversarial pass also found no build-time check tying the opt-in
stack to the project guard reserve. The repair adds a compile-time requirement
for 4 KiB of working stack beyond that reserve and host boundary assertions
for rejected 4-KiB and admitted 8-KiB stacks. The focused `stack_bounds_tests`
and `stack_guard_image_tests` pass; the ordinary RF-inhibited image also
cross-builds after the diagnostic changes. A fresh assessment of the repaired
source and target trace finds no further stack-admission or released-button
coordination defect. A separately authorized live press/release run is still
required before enabling the credential route; the blank captive page remains
GET-only.

The final probe-script review found that its core-1 assertion required only a
nonzero starting count and end-to-end progress. Each individual sample now
also requires an advancing read counter, with subtraction interpreted modulo
the 32-bit counter width. The captured target trace already showed progress
within all twenty calls; this repair makes that requirement executable for
subsequent runs. Python syntax and the affected source checks pass.

The next authorized live run **failed the hard physical gate**. With the same
RF-inhibited core-1 image, a timed probe saw one valid held-button sample,
then lost the USB reply while AP traffic also failed. Candidate A rebooted into
recovery with `UFSR.INVSTATE`; the available fault PC does not locate the
faulting instruction or core. The restored GET-only image booted healthy with
generation 0, erased access and inactive output. The [exact run](phase12-wifi-only-bootsel-gate.md)
is non-qualifying. The previous source reassessment covered the released-button
path only and cannot be extended to a held-button/core-1 claim.

Adversarial review of the probe harness found that its `finally` block raised
an AP-traffic failure over the primary USB timeout. The repair still reports
both AP counters and observed button transitions, then lets the original USB
exception propagate. The captured run remains failed under either error. No
credential POST or journal mutation was enabled. The contract sends a failed
sampler gate back to design; a narrowed core-1-absent/parked topology or a new
physical gesture requires fresh review and target evidence. The operator also
directed future image changes to roll forward without routine restores.

The separately authorized **no-flash** test on the installed standard image
provided the missing narrow-topology evidence: all 60 safe-zone calls passed
while the operator pressed and released BOOTSEL, and 424 AP GETs succeeded with
none failing. The boot ID, generation-0/erased state, healthy storage and
inactive output were unchanged. The standard ELF contains no linked core-1
launcher or flash reader. The failed core-1 diagnostic build option has been
removed; the StandaloneRF worker build refuses runtime BOOTSEL sampling. A
standard-image link check requires a single SRAM callback and rejects known
core-1 launcher symbols, with a source review confirming no core-1 start. This
narrows the proposed physical-claim design to a blank RF-inhibited image with
core 1 absent; it does not erase the failed core-1 row or enable credential
POST.

The follow-up adversarial pass found that the failed flash-reading diagnostic
remained an opt-in build target, which could reproduce the unsafe physical
button combination. That option and its launcher were removed. The ordinary
RF-inhibited image cross-build passes the new single-core/SRAM-callback link
check; the checker rejects the retained historical diagnostic ELF. The
StandaloneRF sampler object cross-compiles to a direct
`PICO_ERROR_NOT_PERMITTED` return with no button callback. A second source
assessment found no remaining actionable issue in this narrowed BOOTSEL
admission layer. The credential route and end-user join flow remain open and
the newly guarded image has not been flashed.

The second source assessment found no enabled credential-write route. The
`PicoBootstrapServer` still dispatches through the GET-only
`bootstrap_http_wire`; neither a physical grant nor a browser form is wired to
the target. The new profile source is device-bound and selects generation 1
from a virgin journal, rejects a post-tombstone bootstrap and permits a later
full-profile generation 2. Runtime network-only mode suppresses legacy
schedules and TLS deployment credentials. The USB-local BOOTSEL probe is
read-only, requires idle/inactive output, uses SDK flash-safe coordination,
and retains a failure result rather than treating it as a button reading.

Validation on the preceding foundation source: 90/90 host CTests passed with the full Xcode
compiler and macOS 26.5 SDK environment; `npm test`, `npm run build`, the
RF-inhibited `WsprryPico` cross-build, image heap/stack checks,
`network_transport_contract_tests.py`, two browser tests, `git diff --check` and the ten-document
local-link check passed. The focused Pico crypto host test and standard
RF-inhibited cross-build passed on this continuation. The default shell's
command-line SDK fails three
temporary native-link tests on macOS 27 `.tbd` architecture entries; rerunning
the full suite with the selected Xcode compiler resolves that environment
failure. `WsprryPico-StandaloneRF` did not cross-build: its shared main includes
Field-GATT types but the diagnostic RF target does not receive the production
BTstack include/link configuration. This target issue predates the new
network-only route and was not repaired by enabling field service in an RF
diagnostic image. The separately verified standard RF-inhibited diagnostic
was flashed for the bounded single-core probe.

Open implementation gates now start with review of the narrowed physical-claim
design and its source guards, then AP-local mutating protocol,
transactional AP/STA trial and commit, streaming the roughly 50-KiB browser
bundle within the target heap and a matching CSP, stable AP withdrawal,
failed-join/response-loss tests and selected-iPhone acceptance. The
[probe record](phase12-wifi-only-bootsel-gate.md) defines the next target
measurement. No source or host result closes Phase 12, Stage B or RF work.
