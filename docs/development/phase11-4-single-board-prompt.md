# Execute the remaining single-board Phase 11.4 acceptance

Own the remaining inhibited acceptance for the existing Pico. Do not wait for a
second board before completing independent work. Execute this prompt, retain
evidence, repair findings, repeat adversarial review, then commit and push the
completed authorized changes to `origin/devel` in each changed repository.
Phase 11.4 remains OPEN until every required physical gate has passed.

## Scope and starting identity

Coordinate `/Users/lbussy/GitHub/WsprryPico` (firmware, normative WTP/1, shared
identity contract and the sole joint matrix) and `/Users/lbussy/GitHub/WsprryPi`
(production host, TLS/resolver, scheduling, recovery and host API/UI).
Read applicable AGENTS.md, README, CONTRACT where present, architecture,
development checks, browser API, network/recovery contracts and current
Phase 11.4 plan/reviews. Inspect both working trees before edits; preserve all
existing work. Starting published documentation/tooling commits are Pico
`1db0a99afb579dc2c9ce5ec336a91f4896569a34` and Pi
`6ca7d82319ccf3c5776a45975734992299985757`; verify rather than assume parity.

The actual reviewed runtime pair remains Pico
`d8cde03f8127b3c2aaf727f2c21c20960f658e84` and Pi
`efcc792cb45780c8b87ebfa83838ecb9eb9cdf47`. Pi's isolated source is
`2e47641f6ebdff104e32999f5194f2e0dc408e06`. Preserve clean-source gates and
companion pins; documentation commits do not require circular repinning.

Use the existing Pico 2 W on wspr5, USB serial `0BF4B4AEC9FFB344`, full WTP ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`. Console is
`/dev/serial/by-id/usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00`; WTP ends in
`-if02`. Never open the GPSDO endpoint. Refresh actual identity and state before
dependent work. The installed standard inhibited image is identified in the
joint plan by UF2 SHA-256
`68b617ca7efdcbea65cd7a592d93f346d560aa0aef1e8e16e65d6f2add9d3ca6`,
ELF SHA-256 `f968b3462b635f76c3d2a3667400146a28e28c61a83c9b84d2dbe4cc9a2176bf`
and revision `a9662c3f8323-dirty`. Require deployment match and CAPS engine
`inhibited-standalone-simulator`; layout alone is insufficient.

Use `wsprrypico-0a60df.local:18443`, the explicitly certified MAC-suffix alias.
Keep the full WTP ID as the independent board check. MAC suffixes can collide.
Repeat this alias on renewal; do not change the firmware's full-ID default.
Mac Chrome and wspr5 are the intended clients. Previously observed addresses
were Mac `192.168.1.27` on en0, wspr5 `192.168.1.117` on wlan1 and Pico
`192.168.1.47`; these are observations, not reservations or identity anchors.

Private credentials remain under
`config/local/network/phase11-4-fd6127d1/`. Device CA SHA-256 is
`2ef7ec890d48e9283286ee09c6b549756f3d3cff530e5cb030ced6ae4c40442b`;
the current server fingerprint is
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
Use the existing separate controller and browser identities. Never print keys,
passwords, PKCS#12 contents or credential-bearing firmware.

## Authority and execution discipline

Local source/tooling/documentation work, hardware-free checks and publication
in the two named repositories are authorized. Retain prior specific grants:
bounded INFO/STATUS and WTP HELLO/CAPS/GET_CLOCK/STATUS/PING on this Pico,
the two already exercised exact-image deployments, existing approved Mac
CA/browser imports and SSL trust, authenticated browser reads, and isolated
wspr5 source/controller staging/build. The one approved Console Wi-Fi cycle
has already been exercised; it is not permission for unlimited retries.

Prepare concrete, reviewable operation packets before requesting new finite
jobs, configuration writes, host application invocation, service changes,
faults, reboots, captures, trust changes or flashes. Cite the separate-approval
requirement in phase11-4-acceptance.md and the original handoff. Consolidate
related operations, reuse granted approvals, and continue independent work
while awaiting answers. This prompt does not grant those physical operations.

No RFBench, RFWTP, StandaloneRF, GPIO changes, time falsification, trust bypass,
hosts-file workaround, speculative resolver changes or incidental installation.
Preserve TLS 1.3, mTLS, ALPN, exact SAN and Host/Origin checks, full WTP identity,
ownership, replay, output-unknown and complete LOAD-before-ARM semantics.

## Execution order and physical packets

1. Refresh read-only Pico and client evidence. Preserve earlier short-name
   failures and the user's report that resolution works. Mac/Chrome success and
   wspr5 NSS failure are separate observations; do not generalize either.
   A failed NSS case must not block independent browser/device tests.
2. Prepare production B3/F5 from the isolated reviewed executable
   `/home/pi/phase11-4-acceptance/source-git/src/build/bin/pi-reviewed-source`,
   SHA-256 `3acd44dd6a8933cc816604a4514d8517e7586a2da40bff628378e080af5c6857`.
   Verify its `BACKENDS=simulated ANCILLARY_GPIO=0` build profile and complete
   private INI. Select WTP network explicitly; no local GPIO, LED, amplifier,
   selector, fades, boot transmission or unintended repeat. Never weaken
   `WSPRRYPI_DISABLE_HARDWARE_ACCESS`; it blocks physical network invocation.
   Account for singleton port 1234, independently of HTTP/socket ports.
   Inspect the installed service's startup hooks and output authority before
   proposing a pause/restoration. Do not infer safe hardware from Transmit=false,
   idle labels or process exit. If its state is unknown, retain that limitation
   and advance direct Pico work while planning the required host recovery.
   Test hostname resolution separately from explicit IP + expected DNS identity;
   the latter preserves TLS and HTTP authority but cannot close mDNS acceptance.
3. Prepare a bounded direct-device batch independently of the service: at most
   six WTP jobs, each one complete six-second tone event at nominal
   3,570,100 Hz, no frequency adjustment, on the inhibited engine only.
   Cases: completion; cancellation while loaded, armed and running; socket loss
   after acknowledged ARM and same-session reconciliation; rejection with a
   one-nanosecond uncertainty budget. Normal ARM budget is 500,000,000 ns with
   ten-second start lead, subject to fresh CAPS and clock admission. Claims are
   at most 60 seconds. Use separate browser principal/session to observe status
   and test foreign ABORT/RELEASE rejection. Record every exact request, ID,
   response, observed transition and terminal result. Never relabel this direct
   harness as the WsprryPi production application or an actual Chrome job.
4. Add actual Chrome job/ownership behavior and production finite QRSS workflows
   under their exact reviewed packets. Use the application's supported finite
   planner; continuous Test Tone is not a bounded production job. Verify shared
   host status and management policy while the direct Pico browser observes
   Loaded/Armed/Running. Preserve drafts and unknown-state presentation.
5. Prepare C3/H1 idle management: snapshot private config, revisions, schedule
   history and watermark. Specify an exact reversible nonsecret delta with
   scheduling kept disabled; preserve the password using the documented null
   semantics. Test missing/stale If-Match, intended successful writes, readback,
   restoration and separately approved reboot persistence. Observe actual Chrome
   drafts/redaction and both API paths. Never manufacture completion from a
   watermark or enable an unattended schedule for convenience.
6. Prepare F1–F6 certificate cases: same-name renewal in a new directory,
   replacement clients, wrong name/CA, missing/invalid/expired client, IP absent
   SAN, IP with expected DNS identity, and matching-IP-SAN success. A deliberately
   mismatched full deployment ID can test F4 on this one board. Bind each new
   image and restoration image by hash before separate flash approval. Build,
   client and device rejection are different layers; require a positive control
   and evidence of the intended rejection. Keep validators and clocks intact.
   Issuing a new client does not revoke an old valid client.
7. Prepare C4/D1–D3/E2–E3 network work: exact Pico-only DHCP/link operation,
   bounded captures, deferred HTTP Wi-Fi response delivery, actual goodbye/cache
   observations, and an explicitly approved host alias responder. Identify
   router/lease details before DHCP work; missing details do not block other
   cases. The earlier sudo capture failure produced no packet evidence.
   A host responder tests only the narrower conflict mechanism, not E1 two-board
   identity/trust. Remove only the introduced responder and retry the same name
   through an explicitly approved idle lifecycle operation.
8. Prepare G4–G7 recovery separately: auditable application-response loss for
   LOAD/ARM/ABORT, failed DNS/TLS reconnect, test-process restart, device boot
   change and USB-versus-Console authority. A ciphertext cut does not establish
   which response was lost. Faults must be endpoint-specific, bounded and have
   explicit cleanup. Unknown state prohibits dependent mutations until the
   existing authoritative reconciliation procedure succeeds.

E1 genuinely requires another authorized physical board with independent trust.
The changed-physical-device variant of G6 also needs an independent device;
same-board boot and host-process restart do not. Do not weaken these criteria.

## Tooling, evidence and validation

Use existing helpers first. New physical tooling must be opt-in, bounded,
explicitly targeted, identity-checked before mutations and inspectable offline.
Validate failure paths with deterministic fixtures, not automatic physical CI.
Never auto-retry an ambiguous mutation, claim cleanup from socket closure, or
overwrite an earlier evidence attempt. Record UTC timestamps, exact command and
source/artifact/tool hashes, request/session/job identity, raw result, expected
result and disposition in private owner-only evidence. Commit sanitized findings
and reproducible procedures, not secrets or generated deployment artifacts.

Maintain one joint matrix in phase11-4-plan.md, with PASS/FAIL/BLOCKED/NOT RUN,
equipment/approval prerequisites, evidence, original failure and retest. Partial
coverage is explicit; no compound row passes from a single successful subcase.
Run affected documented Pico/Pi checks. Preserve clean-source interop pins;
rerun both directions when runtime integration changes. Use sanitizer checks for
relevant memory/lifecycle repairs and Impeccable for UI changes/visual review.
Do not install tools or alter services incidentally.

## Adversarial review and publication

After execution, challenge target identity, stale builds, DNS cache/injected
resolution, TLS versus WTP identity, wrong validation layers, unobserved states,
duplicate submission, ownership/output-unknown, cleanup, evidence overwrites,
secret leakage, approval drift and unsupported physical/RF claims. Repair each
actionable local finding and rerun affected checks, then repeat assessment.
Keep unresolved physical findings explicit rather than calling them closed.

Update the coordinating and companion reviews with actual results and
Documentation Impact: changed guides, considered-but-unchanged contracts and
exact follow-up paths in Wsprry_Pi_Docs (read-only, never edit/publish it).
Retain Phase 11.5 resources, 11.6 RF, 11.7 joint closure and Phase 12/13 boundaries.
Review complete staged diffs for secrets/unrelated work, commit and push each
changed authorized repository to origin/devel without force, and verify parity.
Report phase status, tested identities, physical versus local evidence, review
iterations, final device/service/trust/configuration state, remaining approvals
and equipment, changed files, commit IDs and actual working-tree/remote state.
Report remote CI only when observed for the relevant commit.
