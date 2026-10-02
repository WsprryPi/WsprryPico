# Phase 12 inhibited fault fixtures

Status: test preparation only. No hardware operation is authorized by this
file, a build, or a previous hardware campaign. These are separate inhibited
fixtures, not acceptance or deployment candidates. Every operation needs the
approved packet, exact image hashes, current board identity, fresh recoverable
backup and independently verified restoration.

## Build and identity

The firmware CMake cache variable `WSPRRY_PICO_PHASE12_FAULT_STAGE` defaults to
`0` (absent). Values `1` through `10` select exactly one stage at build time.
Only `WsprryPico` receives the source and macro; `WsprryPico-StandaloneRF` never
receives them. The fixture translation unit refuses compilation unless physical
RF is disabled. Use the pinned SDK/toolchain and offline dependency import
recorded in the parent test-preparation packet. Build in a separate directory;
never overwrite an ordinary candidate directory or infer the stage from a filename.

USB `INFO` includes `phase12_fault_stage` and `phase12_fault_consumed` only in
these images. Confirm both before the approved operation. Stage selection does
not start a save or reset. The ordinary device-bound recovery flow, including
both confirmations and typed phrase, still controls destructive operations.

| Stage | Actual interruption point | Required operation |
|---|---|---|
| 1 | Durable reset intent committed | Selected provisioning reset or full erase |
| 2 | Operational preservation complete phase committed | Same reset |
| 3 | Profile clearing/source selection complete phase committed | Same reset |
| 4 | Access epoch/password/bond authorization reset phase committed | Same reset |
| 5 | Operational erasure phase committed (actual erasure only for full erase) | Same reset |
| 6 | Physical bond clearing verified and phase committed | Same reset |
| 7 | Final access record committed without pending reset | Same reset |
| 8 | First profile payload page physically programmed, before header/commit | One selected profile save |
| 9 | Profile header physically programmed, before commit marker | One selected profile save |
| 10 | Profile commit marker physically programmed, before readback/activation | One selected profile save |

The hook deliberately reboots once after its actual durable boundary, outside
flash's interrupt-masked region. It does not fabricate a success result or
corrupt unrelated RAM/flash. Reset resume uses the real access-journal intent;
profile restart uses the real journal loader. The selected operation can affect
settings/trust, so a fixture is not a harmless status probe.

A watchdog scratch marker suppresses the same stage on subsequent deliberate
watchdog boots. `phase12_fault_consumed=true` is required after the cut. A full
power loss clears this volatile marker and can rearm the fixture; flashing a
different stage also changes its marker. Stop after a cold boot or unexpected
reboot and reassess before any additional operation. Never start an unattended
save/reset loop. An unrelated GP14 reset or panic can replace diagnostic scratch
registers; the packet must forbid those concurrent actions during these cases.

## Finite evidence and restoration

Each approved case permits one operation and one deliberate interruption, with
at most two additional reset-resume/completion boots. Limit each case to five
minutes; no automatic retry. On timeout, storage/identity fault, unexpected
stage/boot, active output or unowned operation, stop and retain evidence.
Capture before/after exact firmware identity, device/boot identity, stage and
consumed flag, profile/access generation and source, reset-pending state,
operational station/schedule/watermark comparison, physical bonds and empty
inactive WTP authority. Observe E10 remains byte-for-byte unchanged using the
approved backup/readback mechanism. Do not expose passwords or private keys in
logs. Retain hashed private backups outside version control.

For stages 1–6 require durable intent and automatic safe completion of that
same reset; stage 7 requires no repeated reset or extra epoch increment. For
provisioning reset retain effective station settings, schedules and watermark;
for full erase require these records empty. For profile stages 8–9 require
previous committed authority or explicit storage-fault closure, never partial
new credentials. Stage 10 requires exact durable request digest/generation
reconciliation and no second POST or unauthorized trust resurrection.

Restore the exact intended inhibited candidate and operational configuration,
not merely an empty fixture. Verify healthy journals, inactive output, no job
or lease, cleared pending recovery and ordinary image absence of fault fields.
This file does not supply permission or a host flash command.

## Software evidence and limits

`reset_storage_tests` cuts all seven named reset checkpoints for both levels,
destroys/reconstructs access/profile/operational stores and resumes the persisted
operation. It verifies effective station preservation, schedules/watermark,
full erasure, bonds, source and a single epoch change. Existing profile journal
cut/corruption tests remain separate deterministic source evidence.

These target fixtures cut at completed pages/phases. They do **not** simulate a
power cut inside a page-program pulse or sector erase, byte-torn physical flash,
engineering A/B/C credential history, reply-loss timing, time-peer callback
races, TLS pool pressure, LED cues or exact GP14/flash coincidence. Those remain
explicit target acceptance assertions; do not report these ten stages as
closing every fault boundary. The separate session-deadline fixture exercises
an accelerated admission deadline and does not accelerate clocks or RF timing.
