# Step 9 execution prompt

Implement standalone station configuration, persistent recurring schedules and
autonomous UTC acquisition on Pico 2 W / RP2350. Start from clean synchronized
`devel`, use `codex/step-9-standalone`, preserve existing work and keep changes in
WsprryPico. Read the project contract, architecture and development instructions.

## Required implementation

1. Add a bounded, versioned application configuration with an explicit enable
   switch, validated WSPR Type 1 station identity (callsign, locator and encoded
   dBm), up to eight recurring UTC schedules, and Wi-Fi/SNTP settings. Reject
   unknown fields, malformed values, overlapping schedules and unsupported
   identities. Never print credentials in status. Keep WTP/1 unchanged.
2. Persist configuration using CRC32-checked, sequenced flash records with an
   independently journaled schedule watermark. Reserve flash in the linker so
   firmware cannot overlap it. Verify writes before acknowledging them. Handle
   erased, corrupt, interrupted and exhausted storage safely. Record a slot
   before submitting it so resets and backward UTC steps cannot repeat it.
   Never write flash while a job is armed or running.
3. Acquire UTC through the Pico's Wi-Fi using bounded nonblocking SNTP polling,
   independent of USB. Use a configured numeric IPv4 server, avoiding a new DNS
   or provisioning subsystem. Validate source, response mode/version, origin
   token, stratum, leap state, timestamps, delay and uncertainty. Bound the
   supported UTC era explicitly; age uncertainty and stop scheduling when time
   is unavailable or unacceptable. Do not treat NTP as frequency calibration.
4. Build complete locally encoded jobs and submit through the existing job
   service with distinct local ownership. Use recurring even-minute WSPR slots
   plus one second, bounded preparation lead, no catch-up bursts and no competing
   host ownership. Leave engine preparation, clock rechecks and local RF timing
   under existing service/engine control. Network polling must not starve RF.
5. Provide bounded one-time USB Console configuration and status commands; no
   USB connection or per-job host message is required after provisioning.
   Retain USB WTP as a backend path through the same service. Apply saved network
   changes on reboot; reject conflicting configuration edits during ownership.
6. Keep the standard image RF-inhibited. Supply an explicitly selected standalone
   RF integration build, preserving the existing RF bench and USB-time RFWTP
   images. Limit RF capability to the existing experimental engine/frequency.
   Do not flash, control hardware, connect the device to Wi-Fi or transmit RF.

## Verification and review

Add deterministic host tests for config rejection, storage interruption and
corruption, restart retention, duplicate prevention, competing ownership,
clock loss/steps, scheduler boundaries, SNTP rejection and autonomous complete
jobs without USB input. Run the maintained host/contract checks, sanitizers,
formatting and available pinned-SDK target cross-builds. Inspect linked flash
and SRAM boundaries. Do not install dependencies incidentally.

Perform an adversarial review of the implementation and integration, including
power loss, integer overflow, flash wear, secret exposure, stalled networking,
clock poisoning limitations, WTP coexistence and RF lifecycle. Repair every
actionable finding and rerun affected checks, then reassess until no actionable
software finding remains. Record exact evidence classes and remaining target
qualification needs; host tests do not establish physical autonomous operation.

Update durable docs and the roadmap accurately. Commit attributable changes,
push the feature branch, fast-forward merge into `devel` when possible, push
`devel`, delete the feature branch locally and remotely, and verify clean status
and local/upstream equality. Report changes, checks, reviews, commits and actual
repository state. Any hardware validation remains separately authorized.
