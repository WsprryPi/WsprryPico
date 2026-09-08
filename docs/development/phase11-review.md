# Phase 11 implementation and adversarial review

Date: 2026-09-08. Repository: WsprryPico, branch `devel`, clean fetched baseline
`91e57e6`. This record covers source and hardware-free validation. No Pico was
flashed, no USB device was controlled, and no RF output was requested. WsprryPi
was read for orientation only; no companion-repository changes were made.

## Initial orientation

README, CONTRACT, architecture, WTP/1, standalone and Phase 10 acceptance records
were reviewed before implementation. The baseline already provides USB WTP,
complete local jobs, persistent config/schedules/watermark, SNTP and recovery.
Recent changes preserve sample-clock realization, RF servicing around complete
request stages, post-frame SNTP refresh and coherent launch state. Phase 10 is
complete in the current record. TCP was disabled in lwIP; browser API resources
were still proposals. The normative TCP contract already requires TLS 1.3 and
mutual authentication. The existing Wi-Fi loop defers polling throughout RF jobs.

The [execution prompt](phase11-execution-prompt.md) records the implementation
scope. The [network guide](network-control.md) describes the resulting operator
workflow and certificate lifecycle; the [API contract](../browser-api.md) defines
the implemented surface. WsprryPi currently integrates over USB. Shared browser
API adoption and a companion TLS controller remain separate work.

## Implementation and review passes

The first implementation review traced HTTP framing, certificate authentication,
Host/Origin checks, ownership, persistence, network changes, disconnect handling
and allocations through the real server and portable service. Findings repaired:

- Maximum WTP frames could trigger geometric 128 KiB parser allocation plus a
  second complete-frame copy. Growth is capped, single-frame storage transfers
  to dispatch, and disconnect releases parser storage. The HTTP body limit is
  separately advertised at 32 KiB. These changes reduce identified peaks; they
  do not prove target heap sufficiency under all concurrent workloads.
- Sequential browser connections could overlap TLS shutdown. One bounded TCP
  connection can now wait for the single TLS slot, with a ten-second deadline.
  Promotion occurs after old peer state is cleared. Extra connections are rejected.
- Wi-Fi disable could cut off its response. The adapter queues it until response
  acknowledgment or connection termination, rechecks service idle state and cancels
  it if ownership changed. Shutdown tracks outstanding TCP ciphertext acknowledgments.
- TLS input buffering is paired with a receive window below buffer capacity;
  callbacks retain backpressure without TLS/application work. HTTP has an absolute
  deadline in addition to handshake and WTP stall deadlines.
- Credential initialization now verifies the certificate/key pair, generated
  credential headers and firmware build directories are private, credential inputs
  trigger reconfiguration, and noncanonical numeric ports fail configuration.
- Browser WTP operation bodies and response envelopes were aligned with the strict
  codec. Physical Console ABORT uses the same service shutdown/terminal path,
  suspends autonomous scheduling and releases ownership only after safe shutdown.

An independent UI review found four actionable issues: status refresh discarded
unsaved edits; failed multi-step job actions left stale owner controls; Release
was offered during active/faulted jobs; successful physical ARM was subsequently
reported as a generic certificate/network failure. Repairs preserve dirty forms
and revisions, add explicit confirmed settings reload, reconcile status after
failure, restrict Release, and show the expected RF connection pause with physical
USB recovery guidance. Behavioral regression tests cover each finding.

The second UI assessment verified those repairs and found a fifth issue: the job
panel retained an old armed message after abort/completion. The panel now renders
the latest observed job ID/state, with Abort, Release and Complete regressions.
The final independent assessment closed all five findings and found no further
material UI issue within the tested scope.

The final backend assessment revisited pending connection ownership, EOF/error
promotion, authentication failure recovery, idle-only writes, physical abort
failure latching, parser boundaries and credential renewal. It closed a dependency-validation gap by checking the
actual SDK-selectable Mbed TLS path and rejecting local modifications in both
firmware and host TLS builds. It added actual TLS
rejection cases for untrusted and expired client certificates. No further
unresolved actionable source finding was identified in this review. Physical
resource/timing behavior remains the explicit acceptance gate below.

## Validation performed

- Host Debug build: **28/28 CTest checks passed**, including the configured optional
  WsprryPi client interoperability and descriptor tests. New tests cover strict
  HTTP/API behavior, browser state transitions, certificate lifecycle and actual
  pinned Mbed TLS over host loopback adapters.
- ASan/UBSan Debug build: **20/20 CTest checks passed**. C and C++ compilation are
  instrumented, including the actual TLS library/adapter. This configuration does
  not enable all optional companion/harness/descriptor checks of the other build.
- Actual TLS tests verify TLS 1.3 and ALPN, reject missing/unsuitable/untrusted/
  expired client certificates, TLS 1.2 and plaintext, then verify recovery. They
  exercise split HTTP, duplicate headers, origin checks, stale ETags, redaction,
  inline CSP hashes, queued connections, slow-client deadlines, a 65,536-byte WTP
  payload, and a 512-event job completing locally after ARM/disconnect.
- The WTP artifact validator passed: 23 schema cases, seven raw JSON cases,
  one framing case and eight transition cases. Existing core/endpoint/RF tests
  also remain passing; this does not alter the normative WTP contract.
- Default-disabled and explicitly credential-enabled firmware builds cross-linked
  both `WsprryPico` and `WsprryPico-StandaloneRF` using the pinned SDK/toolchain.
  All four ELF/UF2 image checks passed: 16 KiB primary stack and flash-journal /
  reserved boot-sector separation. Credentials used here are ephemeral test inputs.
- Enabled inhibited image: text **941,240 bytes**, BSS **75,848 bytes**, data zero.
  Enabled StandaloneRF: text **956,000 bytes**, BSS **279,692 bytes**, data zero.
  These are linker sizes, not measured maximum runtime heap or stack use.
- Embedded HTML/CSS/JS document: **14,265 bytes**, served uncompressed; gzip size
  5,309 bytes is informational. Browser simulation at 1280 x 900 and 390 x 844
  showed readable desktop/mobile layout and the new Reload control without
  horizontal overflow. Browser warnings/errors were empty. Screenshots cover
  idle/unconfigured state; lifecycle/error paths have behavioral tests, not visual
  or hardware qualification. The optional design detector ran in degraded regex
  mode because parser modules were unavailable; it is not an accessibility audit.

Ignored build logs and screenshots remain under `build/phase11-*` and
`build/phase11-review/`. A test-certificate fixture initially used an unsupported
negative OpenSSL day count; it was replaced with explicit historical CA validity
and the expanded suite passed. A preview start overlapped the test's loopback port
and was refused; the preview ran after the test exited. Neither attempt involved
hardware. Do not run the TLS test and preview simultaneously.

## Remaining acceptance limits

Phase 11 software is implemented; **physical acceptance remains open**. New TLS
handshakes are refused while a physical job is armed/running, including its future
arming lead. One established WTP owner can continue control; a browser cannot
continuously inspect/abort through new connections during that interval or while
a persistent WTP client occupies the sole active TLS slot. Physical Console ABORT
is the recovery path. The UI and capabilities disclose these limits.

Separately authorized target work must begin with the inhibited image and verify
real browser certificate selection/trust, device UTC/certificate expiry, DHCP/IP
identity, reconnect/backpressure, malformed peers, config persistence and recovery.
Measure actual peak heap/stack, TLS CPU cost, watchdog behavior and Wi-Fi/USB
contention before RF acceptance. Then establish exact firmware, clock, engine,
mode and conducted path for TLS/RF coexistence and independent decoding. Earlier
RF qualification does not transfer to these network-enabled builds.

Certificate deployment/renewal currently rebuilds and reflashes a device-specific
private image. There is no runtime CA/key rotation or individual-client CRL/OCSP;
compromise recovery rotates that device CA and reissues clients. SoftAP/BLE and
runtime provisioning remain Phase 12. Continuous browser availability during RF,
companion WsprryPi TLS/API adoption, final hardware/timing/RF/reliability coverage
and reproducible public release UF2 remain open work.

## Subsequent concurrency work

This is the retained original single-connection acceptance record. Its physical
handshake restriction is superseded by the [Phase 11.2 review](phase11-2-review.md)
for the new standalone images. Earlier software and RF results are not target
qualification of that execution architecture.
