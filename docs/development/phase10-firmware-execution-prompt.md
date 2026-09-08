# Phase 10 firmware and clock integration execution prompt

Implement the Pico software prerequisites for the WsprryPi WTP host integration.
Work in WsprryPico only; the user authorizes review, implementation, deterministic
validation, adversarial review/repair, then commit and push. Physical device access,
flashing, installation/services and RF operations require separate authorization.

## Reviewed baseline

- WsprryPico `devel` and freshly fetched `origin/devel`:
  `df3f889795af3ea98f7798dc374a7906982f677b`, initially clean.
- WsprryPi host integration:
  `2819f0b8ccb05f12d7f978a4cee2cac830997bbf` on
  `codex/phase10-wtp-slice1`, inspected read-only.
- Host reference tests pin Pico `40812e7438f180c5e8d8ad75d4eb227271152b10`.
  The subsequent Pico commit changes campaign selection, QRSS3 workloads and
  evidence; it does not change the WTP endpoint, clock or RF C++ implementation.
- The SNTP-enabled images advertise only WSPR/TONE at the earlier 80 m profile.
  Their service defaults also advertise 512 events/24 hours, exceeding the
  physical stream engine's 162 events/110.592 seconds.
- The separate RFWTP image already supports five finite modes and broad direct
  synthesis, but relies on a diagnostic USB time source. WsprryPi never provisions
  Console time. Its default 1 ms admission budget can reject valid SNTP estimates.

Read AGENTS.md, README.md, CONTRACT.md, architecture, WTP/1 and its fixtures,
development instructions, standalone/SNTP implementation, stream planner and
the host's integration/review documents before editing. Preserve existing work.

## Implemented slice to deliver

1. Share the existing experimental RF job capability profile across the USB-time
   and SNTP-enabled images. Advertise WSPR, TONE, QRSS, FSKCW and DFCW, selected
   clock frequency bounds, 162 events and 110.592 seconds. Do not advertise CW,
   indefinite tone, more than the engine can execute, or RF qualification.
2. Use the existing standard inhibited image for initial host acceptance and the
   explicit StandaloneRF target for later RF acceptance. Preserve engine identity,
   default RF inhibition, build opt-in, journals, configured autonomous WSPR
   schedules, shared ownership and local event execution. Avoid a new image or
   protocol when the existing image pair suffices.
3. Keep SNTP acquisition, 500 ms maximum uncertainty, drift aging, 90-second
   launch age and leap rejection intact. Explain that 500 ms is an explicit
   bounded functional-acceptance ceiling, not calibrated accuracy. The client
   may choose a stricter budget; never relax it silently. Preserve the separate
   RFWTP USB clock policy. Do not add WTP clock-setting operations.
4. Add deterministic tests of real job-service admission using the shared
   profile, all five modes, clock rejection and aging, frequency adjustment,
   physical planner limits, local execution, cancellation and ownership.
   Distinguish simulator acceptance from physical planner representability.
5. Add an optional hardware-free interoperability target against explicitly
   selected, identity-verified WsprryPi client sources. Compile them only in the
   test build; no runtime dependency or sibling edits. Exercise the current Pico
   endpoint, shared profile, real UTC discipline/SNTP and inhibited engine over
   fragmented in-memory streams. Cover five modes, strict clock rejection,
   independent completion after disconnect, reconciliation, cancellation and
   boot changes. Retain the host's original provenance pin unchanged.
6. Document an execution-ready joint acceptance procedure: exact Linux host/source
   and firmware identities, device/CDC selection, disabled autonomous scheduling,
   independent host/device clock readiness, finite jobs, explicit frequency
   adjustment, no GPIO ancillary actions, no continuous Test Tone, unknown-state
   handling and stop/recovery evidence. Separate inhibited USB acceptance,
   conducted RF acceptance, installation/services and final qualification.
7. Update the roadmap to reflect host integration delivered on its feature branch
   and this firmware software slice, leaving joint target acceptance open.
   Preserve historical campaign failures and later focused successes unchanged.

## Validation and review

Run the documented host CMake/CTest suite and WTP artifact validator. Run new
profile tests at all three supported sample clocks, optional actual-client
interoperability and affected sanitizers. Cross-build the standard, StandaloneRF,
RFWTP and RFBench images with existing pinned dependencies; check memory/journal
layout and prove the standard ELF has no physical RF driver. Keep artifacts in
new ignored build directories so prior campaign artifacts remain intact.

Review the resulting code adversarially against capability truthfulness,
sample-clock consistency, RF inhibition, ownership, clock aging, delayed polls,
replay/boot changes, dependency identity and false acceptance claims. Fix every
actionable finding in scope, rerun affected checks, and perform another assessment.
Record exact commands, failures/repairs, remaining limitations and final findings.

Commit only reviewed changes and push the current Pico devel branch after checking
remote ancestry and the complete diff. Do not force push or mutate sibling
repositories. Report commit, push and working-tree state. Do not mark all Phase 10
or hardware acceptance complete from software tests.
