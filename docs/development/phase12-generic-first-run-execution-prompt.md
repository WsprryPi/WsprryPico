# Phase 12 generic first-run cleanup: execution prompt

Status: **EXECUTED; TARGET RESULT AND ADVERSARIAL REVIEW RECORDED SEPARATELY**.

Work on `devel` in `/Users/lbussy/GitHub/WsprryPico`. Preserve unrelated work.
Read `README.md`, `CONTRACT.md`, `docs/architecture.md`, this prompt, the
[Phase 12 roadmap](phase12-plan.md), the
[Wi-Fi-only proposal](phase12-wifi-only-bootstrap-proposal.md) and the
[prior blank captive result](phase12-blank-captive-physical-result.md) before
editing. Use the selected Pico 2 W / RP2350 target and standard RF-inhibited
image. Do not add Wi-Fi credential input, a network-join transaction, BLE
commissioning, owner authority, TLS identity or job/RF authority in this slice.
The Wi-Fi-only proposal remains design-only until its separate approval gate.

## Objective and exact source policy

Make a truly all-erased **generic** Pico boot into the existing read-only,
passwordless SoftAP captive page without writing a test-only unprovisioned
journal. A generation-zero profile journal is not itself a factory bundle:

- With no compiled TLS bundle and exactly erased profile storage, select
  `Unprovisioned` at generation zero. Ignore legacy standalone Wi-Fi and
  schedules, keep output inactive, and allow only the already bounded read-only
  AP when identity, access health, listener and job gates pass.
- With a configured and matching device-bound compiled bundle and erased
  profile storage, preserve the legacy factory behavior. A configured bundle
  whose identity does not match the board fails closed.
- An explicit `BuildBundle` source selection works only with a matching
  compiled bundle. An explicit `Unprovisioned` tombstone remains authoritative
  even when a matching bundle is compiled.
- A malformed, corrupt, ambiguous or interrupted **first** profile selection
  must not masquerade as erased storage. A valid older committed source may
  survive an incomplete inactive-slot write under the existing journal rules.
  No reset or reboot may resurrect legacy standalone Wi-Fi or superseded trust.

## Execution and acceptance

1. Inspect profile-journal scanning, runtime source selection, compiled
   credential metadata, boot gates and activation reload. Implement the
   narrowest explicit source rule and keep the portable logic outside Pico SDK.
2. Add deterministic host cases for erased generic and matching-bundle boots,
   wrong-board bundle, explicit bundle and tombstone, old standalone Wi-Fi
   suppression, interrupted first writes, older-source recovery and corrupt
   newest journal. Include the activation reload in the target cross-build.
3. Run focused provisioning and field-access tests, affected network contracts,
   the RF-inhibited Pico 2 W build and field-access linkcheck using the pinned
   SDK. Record toolchain and any build workaround; do not infer target behavior
   from compilation.
4. If the previously authorized Candidate A is available, identify its exact
   serial/chip and verify inactive RF before a full flash erase. Flash and
   verify only the RF-inhibited candidate image. Do not seed the profile
   journal. Read back source, generation, access state, inactive output and
   storage health. Check the open AP, DHCP, AP DNS and read-only captive page
   using an isolated host interface; keep the comparator and management links
   untouched. Record the exact image digest, setup, limits and final state.
   Treat phone behavior as operator-reported evidence only if the operator
   actually repeats that check.
5. Run an adversarial review focused on implicit factory fallback, damaged or
   partly written flash, wrong-device bundle activation, legacy credential
   resurrection, AP admission, RF authority, and the distinction between
   source checks and physical acceptance. Repair actionable findings, rerun
   affected checks, and perform a second adversarial assessment.
6. Update the roadmap and contract to reflect only accepted evidence. Commit
   the bounded result on `devel`, push to `origin/devel`, and report the exact
   repository state, physical result and remaining Wi-Fi-only design gates.

## Follow-on gate

After this first-run cleanup, resolve the network-join proposal's runtime
BOOTSEL safety, browser crypto availability and provenance, versioned wire
vectors, network-only generation semantics, AP/STA coexistence and target
acceptance criteria. Approve the resulting P12.7 exception before introducing
mutating credential routes or claiming an iPhone home-network join. Stage B
RF coexistence and the paused Bluefy/native-app work remain separate.
