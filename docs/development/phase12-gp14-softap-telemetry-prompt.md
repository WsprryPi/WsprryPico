# GP14 opt-in SoftAP telemetry: execution brief

Status: execution authorized for source, host checks, pinned Pico 2 W builds,
review, commit and push on `devel`. No flash or physical operation is
authorized by this brief.

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel` from the clean
`cfa14e22f89786f94044e9979ebe98b38fcbdbb1` handoff. Read `AGENTS.md`,
`README.md`, `CONTRACT.md`, `docs/architecture.md`, the GP14 runtime review
and this brief before editing. Preserve device settings, private captures,
generated firmware, and unrelated work. The installed Candidate B image is
the RF-inhibited `c806890fc361` revision with UF2 SHA-256
`10e7ff2a99bce561eb0cbbea7cf95bff91f8f3c52b4c4077be504108cc910252`;
do not assume a new source build is running on that board.

## Objective and scope

Make the opt-in GP14 diagnostic distinguish a setup gesture from an accepted
manual SoftAP request, and distinguish that request from actual AP startup
and service readiness. A read-only USB INFO response should let a later
bounded target test see whether the manual lease remains active while GP14 is
held and after release. The existing `gp14_ap_events` field retains its
meaning as an event count. No value may imply phone association, DHCP,
HTTPS, captive portal, or RF acceptance without the corresponding physical
test.

Implement minimal telemetry at the existing ownership boundaries:

1. Record setup callback attempts and accepted results in `ButtonRuntime`,
   without changing event ordering, stop gating, callback invocation, or
   reset behavior. A setup event after failed shutdown remains an event but
   has zero callback attempts. A callback rejection remains visible as an
   attempt without acceptance.
2. Expose the portable coordinator's manual lease active and button-held
   state without changing the lease policy. During a held jumper, the lease
   remains active beyond the ten-minute limit. Release starts the ordinary
   ten-minute period. Keep the telemetry name and meaning explicit.
3. Add fields to console INFO only in the
   `WSPRRY_PICO_GP14_RUNTIME_BUTTON=ON` build for callback attempts and
   accepts, coordinator requested/ready and manual lease/held state, and
   Pico SoftAP adapter running/ready state. Use the existing core-0 objects;
   do not call `poll`, start/stop the AP, write settings, or query secrets as
   part of formatting. Read one consistent coordinator snapshot and avoid
   exposing SSIDs, passwords, certificates, device journals, or cookies.
   Requested/running/ready describe the whole AP and may reflect station-loss
   fallback or another reason; correlate them with the manual lease and
   accepted-request count rather than attributing them to GP14 alone.
4. Preserve the standard image, WTP/1, browser API, GP14 gesture policy,
   BOOTSEL disconnection, and RF-inhibited engine. Do not link or flash an
   RF-capable image. Do not claim actual RF cutoff or integrated SoftAP
   acceptance.

## Evidence and checks

Add focused deterministic host checks that distinguish setup event,
callback attempt and acceptance for successful stop, failed stop and rejected
setup; also verify manual lease held past ten minutes and its release expiry.
Do not add tests that simply restate JSON formatting. Run the repository host
suite and C++ formatting, review default-image omission of all new GP14 INFO
fields, and build both default and opt-in RF-inhibited Pico 2 W targets with
the existing local pinned SDK. Check the opt-in ELF's linked flash bounds,
stack guards, BOOTSEL topology, and relevant SRAM/INFO response headroom.
Record exact commands, source revision, image hashes, results and limitations.
Do not download SDKs or tools incidentally.

## Adversarial review and delivery

Review callback-result semantics, stale or mixed-state INFO snapshots, lease
expiry while held and after release, AP startup failure, status naming,
unintended mutation, sensitive-data exposure, default-image separation,
response size, and target timing claims. Repair actionable findings, rerun
affected checks, and perform a second adversarial assessment. Record findings
and remaining physical gates in the GP14 runtime review. Update any stale
status in the repository documentation. Commit and push the reviewed source
and record on `devel`, verify remote parity, and report the actual checkout
state. P12.7, P12.11 and Phase 12 remain open.
