# Phase 11.4 A2 completion execution prompt

Complete the remaining device UTC-gating evidence in WsprryPico Phase 11.4 A2.
Prepare and execute this prompt, perform adversarial review, correct actionable
findings and repeat the assessment, then commit and push the scoped artifacts to
`origin/devel`. Preserve original attempts and other open phase gates.

## Scope and identity

Read README, CONTRACT, architecture, development checks, WTP clock/ARM semantics,
the acceptance procedure and current joint matrix before acting. Inspect the
working tree and preserve unrelated changes. Starting source is Pico `4ef5246`;
installed standard inhibited runtime is `23ac5b1aee66`, UF2 SHA-256
`a7013feccf36abb9c9da17db057d4d12158942a019d74d787f56336f64a6c8f2`.
Verify the actual runtime instead of inferring it from Git HEAD.

Use only Pico 2 W/RP2350 on wspr5, serial `0BF4B4AEC9FFB344`, full WTP device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`, Console `-if00`, WTP `-if02`. Do not open the
adjacent GPSDO. Existing user grants authorize these bounded inhibited tests and
Pico-only Wi-Fi control. No RF, GPIO, router, service pause, trust import, firmware
flash or saved configuration change is needed. Never set, falsify or inject a
clock sample. Do not change WsprryPi or represent direct USB as production-client
or TLS acceptance.

## Concrete execution

1. Create owner-only ignored `build/phase11-4-a2/` evidence. Record UTC times,
   exact invocation, script hash and device/boot/revision. Cross-check Console
   INFO with WTP HELLO/CAPS/STATUS; require normal boot, matching deployment,
   `inhibited-standalone-simulator`, healthy storage, explicit inactive/unowned
   state and disabled standalone schedules. Record station, schedule, watermark,
   configured `pool.ntp.org` and network status for restoration comparison.
2. Read GET_CLOCK before network/TLS observations. Require a real synchronized
   sample with normal leap and uncertainty within CAPS. Use one complete
   one-second finite tone job at nominal 3,570,100 Hz, never continuous output.
   Validate against CAPS. CLAIM/LOAD, then ARM with a 1 ns requested uncertainty;
   require exactly `CLOCK_UNCERTAIN`, matching Loaded job/owner and inactive
   output. ABORT/RELEASE with authoritative empty/unowned verification.
3. While idle, send Console WIFI OFF. Leave the host/router and clock untouched.
   Poll USB GET_CLOCK on a bounded cadence. A normal clock sample transitions
   from synchronized through holdover to unsynchronized as its actual age grows.
   Current source policy is synchronized through 90 seconds and holdover through
   180 seconds; use observed fields, not a sleep or assumed state, as the oracle.
4. Once holdover age exceeds advertised `maximum_holdover_age_ns`, submit a fresh
   one-second job and require `CLOCK_UNSYNCHRONIZED` from ARM. Verify unchanged
   Loaded ownership/output before ABORT/RELEASE. Then wait for the actual
   `unsynchronized` state and repeat with another fresh job. Use fresh unique
   request/job IDs; preserve errors and never blindly retry a mutation.
5. Bound Wi-Fi-off observation to 210 seconds plus bounded cleanup, and restore
   WIFI ON in a finally path. Poll for up to 90 seconds for actual SNTP recovery;
   require same boot/device, increased accepted-sample count, synchronized normal
   clock and usable uncertainty. Saved configuration must be unchanged.
6. Use a fourth one-second finite job as the post-recovery positive control.
   Choose a fresh device-UTC start ten seconds ahead within CAPS. Require ARM
   acceptance and matching complete terminal status with output explicitly false;
   release and prove empty/unowned state. If a negative ARM unexpectedly succeeds,
   immediately abort that same owned job, record failure and stop dependent work.
7. Use same-owner ABORT/RELEASE cleanup in finally; authoritative status determines
   cleanup, not process exit. Restore Wi-Fi even when an assertion fails. Do not
   clear journals or use Console override as routine cleanup. If ownership cannot
   be resolved, retain output unknown and report the exact cleanup blocker.
8. After final USB verification, perform an authenticated read-only HTTPS status
   with existing trust, expected DNS identity and fresh USB-reported address.
   This verifies recovered network usability; it does not prove DHCP/mDNS
   reliability or pre-synchronization TLS certificate behavior.

## Review, validation and reporting

Review clock-state/error precedence, expired holdover, uncertainty limits,
otherwise-valid job/start/lease, same-boot continuity, mutation-response identity,
no automatic late ARM/replay, natural aging versus injected clocks and cleanup
under failure. Run the existing relevant host clock/job/standalone tests using
verified CTest names; add implementation tests only if a runtime defect is found.
Hardware results remain distinct from deterministic tests and prior TLS evidence.

Write an identity-bound sanitized execution/review record and update only A2's
joint-matrix status. Retain earlier positive SNTP, boot-unsynchronized and 1 ns
cases as historical evidence. A natural-age unsynchronized rejection is not a
fresh-boot race measurement, calibrated UTC accuracy, leap-transition test,
physical output qualification or production-host clock recovery. Leave all
unrelated gates open. Keep private captures/configuration and generated files
out of Git, validate links and whitespace, inspect staged changes, commit and
push without force, then report actual repository/remote and device state.
