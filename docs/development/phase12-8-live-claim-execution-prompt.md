# P12.8 live claim continuation: execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Start from the existing
uncommitted Safari/SoftAP owner-claim candidate and preserve all other user
work. Read `README.md`, `CONTRACT.md`, `docs/architecture.md`, the approved
P12.7 decision, `Owner-HTTP-v1.md`, `Consumer-Profile-v1.md`, and the current
P12.8 review. Treat source tests, target cross-builds, and live phone/device
evidence as separate classes. The objective of this turn is to make the
no-button claim preparation concrete, reviewable, and durable; do not claim
P12.8 or Phase 12 closure from it.

1. Audit the source-linked claim end to end: AP-only request admission; exact
   device/boot/source/generation and owner-key bindings; released-button
   admission and untimed press/release; mutually exclusive Wi-Fi-only and
   owner slots; station/DHCP/fresh-SNTP and output-idle checks; one profile
   journal generation; ambiguous-write reconciliation; secret scrubbing; and
   the reply-before-network-switch and reply-before-restart boundaries.
2. Audit the local Safari page: P-256 key creation, site-storage write/readback
   and self-test before claim; canonical wire values; no ordinary code, default
   password, JSON or certificate step; encrypted settings; wrong-device and
   competing-claim rejection; cancellation, reload and lost-reply handling;
   and no “Setup complete” before authenticated private readback exists.
3. Fix actionable findings in source and add focused tests for behavior and
   failure paths. Rebuild the pinned offline browser assets, run their tests,
   focused host tests, owner-signature tests, the RF-inhibited Pico 2 W target
   cross-build, formatting/diff checks, and link checks for changed docs.
   Inspect the target image hash and linked BOOTSEL/core topology. Do not
   generalize host or build evidence into hardware acceptance.
4. Perform an adversarial review after validation. If it finds actionable
   defects, repair them and rerun affected checks, then conduct another
   adversarial assessment. Record findings, repairs, evidence, and still-open
   gates in the P12.8 preparation record and keep roadmap/status prose accurate.
5. Commit the coherent source/documentation slice on `devel` and push it.
   Verify the pushed remote revision independently and report any blocker.

Hardware boundary: no button press is needed this turn. `AGENTS.md` requires
explicit action-specific authorization before Candidate A USB control or
flashing. A prior request named an earlier UF2 hash and is superseded by the
final source changes; a general instruction to execute this prompt does not
authorize a different image. If fresh exact-image approval arrives, preflight
the full USB identity and journal state, stop on mismatch, and flash only the
approved RF-inhibited UF2; leave it installed and wait for the operator to be
at the device before starting the physical claim. Do not erase, restore an
older image, touch Candidate B, transmit RF, or represent the pending phone
test as complete.

Report the exact commit, remote parity, artifact hash, checks, adversarial
result, device action actually performed, and the next user action. Keep
post-clock consumer cryptographic activation, encrypted owner session/private
readback, station-client enrollment, iPhone storage/phone acceptance, recovery,
and Stage A closure explicitly open until their own gates pass.
