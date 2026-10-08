# P13.1 step 4: execution and adversarial review

Recorded 2026-10-08. Status: **CLOSED_SCOPED** for the selected active-high
external GP15 functional routing. The [executed prompt](phase13-1-step4-prompt.md)
uses the existing `external_high` case on `devel`. No operator action, new
harness, camera, new backup, rewiring or dependency installation was required.

## Result

On Pico B, actual GP15 readback remained OFF during AP and Identify before and
after transmission. Both cues changed the actual onboard GPIO state. During
the finite RF interval, all 27 active observations read GP15 ON; five also read
the onboard GPIO ON and 22 read it OFF. The two outputs therefore operated
independently. An independently reassessed complete SDR capture confirms RF
presence and an inactive tail. Existing timing/shutdown and software polarity
evidence is reused rather than repeated.

AP and Identify were exercised through the existing identity-bound acceptance
commands; this is indicator-routing acceptance.

The result is `PASS_GPIO_FUNCTIONAL_RF_REVIEWED`, recorded separately in
`assessment.json`. The original machine state remains
`PASS_GPIO_FUNCTIONAL_RF_REVIEW_PENDING`; its disposition is closed by that
assessment, not by rewriting the original ledger.

## Execution identity

| Item | Exact identity |
| --- | --- |
| DUT | Pico 2 W / RP2350 B, serial `CDDBF8767C506C07`, device `29f20b7342051ef947aa56cb9d4fab42` |
| Firmware source | `72d38d505ba252d0019a19461bc952a5650acd2a`, clean restore/high images |
| Reviewed runner | `68516102678082b432087261e52366018f8d19a1`, clean host-only changes from firmware source |
| RF candidate / boot | `72d38d505ba2` / `8b036cdec20e3597ff85bc31e0723532` |
| Job | `174da9330770f781183c091f948effff`, TONE, 16 seconds, 3.5701 MHz |
| RF engine / clock | `pio-dma-gp2`, 138 MHz; GP2 RF, external active-high GP15, GP14 runtime disabled |
| Receiver | RSP1B `2404058C60`, existing conducted SDR path, unchanged GPSDO/path |
| Capture | CF32, 250 ksps, center 3.55 MHz, 200 kHz bandwidth, gain 20, channel 0, AGC/bias off |
| Capture extent | 41 seconds, 10,250,000 samples, 82,000,000 bytes; exact count/hash and verified cleanup |
| Dependencies | Pico SDK `079c6f39023649b154152db30f1d781e884879bc` (2.3.1), picotool source `6f6458d792b93685a11423b244a585eaa99eafcf`, Arm GCC 15.3.1 |

Only the restore and external-high image roles were built. Both passed linked
standalone image checks; the ordinary Pico link check passed with acceptance
options off. The source change repairs the existing observer, not firmware LED
behavior. The earlier requested minimal GP15 wiring sketch is retained under
`tests/hardware/gp15-led/`.

## Adversarial findings and repair iterations

1. The original case checked cached external OFF state during operational cues.
   It also failed to assert successful cue command responses. The runner now
   checks actual external GPIO OFF, actual onboard GPIO activity and successful
   AP/Identify responses independently before and after RF.
2. The pre-RF Identify cue lasts ten seconds. Requesting another Identify at
   launch could return Busy. Source review caught this before RF admission;
   the runner now reuses the acknowledged active cue until it expires.
3. The first target attempt observed GP15 OFF before RF and ON during all 28
   active samples, but no onboard ON sample during RF. It stopped on the
   onboard-activity assertion and restored B. Its incomplete capture and STOP
   ledger remain intact. Sparse sampling of short pulses and a nearly expired
   Identify cue could not establish a stuck output. The existing case now
   requests a fresh Identify during RF after expiry and varies its polling
   interval. One separately reserved corrective run passed, without a firmware
   behavior change. The original attempt is not promoted to PASS.

The 47 existing runner behavioral tests passed on the Mac and `wspr5` after
the final repair. Meaningful rejection coverage includes an external pin ON
despite cached OFF, unknown/stuck onboard GPIO, stuck onboard activity during
TX and refused cues, with restoration and no false PASS. The two RF-presence
tests also passed. Source diff/format checks passed.

Final adversarial assessment independently checked device/boot/job continuity,
actual GPIO states, four non-RF cue checks, active onboard activity, one charged
corrective admission, complete receiver count/hash/settings, RF presence/tail,
clean image/runner binding, unchanged historical ledger hashes and final
two-board authority/settings. No actionable finding remains in this scope.

## Restoration and accounting

B is restored to ordinary inhibited revision `72d38d505ba2`, boot
`8023bdc08dbb9e35d9deb8fbe93d979e`, 150 MHz: RF inactive, schedules disabled,
owner/job null, actual onboard GPIO known OFF/error zero, and retained settings
identical to entry. A was not flashed and remains revision `6c7b14321003`, boot
`e83cac69de154245a974a3efdf5fc8af`, 150 MHz, inactive/disabled/unowned/no job,
with identical settings. Final transport handles and locks were closed.

This work charged two admissions / 34 seconds including warmup: one preserved
STOP and one successful corrective run. With prior spent 16 admissions /
653.368002568 seconds, the aggregate is 18 / 687.368002568 seconds. Separate
reservations are retained; the historical campaign ceiling was neither reset
nor refunded. No automatic RF retry or new flash backup occurred.

Private evidence is under `/home/pi/phase13-led-step4-72d38d5/build/` on `wspr5`:
`external-high-run/` (original STOP), `external-high-corrected/` (passing case
and assessment), `final-readback/`, `prior-ledgers.json` and
`execution-reservation.json`.

| Evidence | SHA-256 |
| --- | --- |
| Corrected run state | `2cd5f4c0e7ff31c0327f0282147fd9e7b697e89994b5380e9a3d60660c6fa7da` |
| Corrected run events | `83a58c726671134cdcce8a4c98bfd5d973852cf347a104e2c9812be0a35f1922` |
| Complete RF capture | `06de2a431a17d217d929d9534e7a1c5d4603f5072a8feea2f533ad446b0c49e9` |
| Receiver metadata | `3aaf68b8a1c84a055f345ac7c4f8c4aeb484b18bebcad110fab75ceaf9c83324` |
| Final two-board readback | `8cc1265c97e21b6cd51b48cb37ac0fe63d3e27c742408d788ffc0078575e33a2` |
| Final live candidate manifest | `9316d1670719826ac78a5afe518324e138d59a7b2e6c14f95055db0cff211544` |
| Corrective reservation | `1a2b287a146f50a431ffee30bafa332683a3e6cf13267bef0a0803d612cfad17` |

The [fixed steps 1–6](phase13-1-closeout-steps.md) are complete. LED addressability
and external TX-only operation are verified. Existing button operation is
recorded in the [Phase 12 closeout](phase12-closure-matrix.md). No LED calibration,
additional polarity campaign or button/header test remains or is carried
forward from P13.1 into Phase 14. Phase 14 retains RF qualification and release
work; P13.2 Si5351 implementation is deferred.
