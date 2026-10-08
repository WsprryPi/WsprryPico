# P13.1 standalone STOP closeout

This executes the [step-1/5 follow-up prompt](phase13-1-standalone-stop-closeout-prompt.md)
on `devel`. B is the DUT; A is unchanged. External LEDs and GP14 qualification
remain outside this follow-up. No camera, new backups or operator attention is
required.

## Source change and adversarial review

The existing runner now charges an autonomous occurrence with unknown job ID
before SCHEDULE, then binds and persists the real ID from matching device/boot
Running authority before STOP. It accepts only that job's `aborted` state with
inactive output, released ownership, disabled schedules and cleared TX request,
then checks actual GPIO OFF. Empty/complete or another job cannot pass.

The existing behavioral adapter now reproduces the target's retained aborted
job and a scheduler ID different from the template. It checks on-disk charge
before SCHEDULE and actual ID before STOP. Adverse checks cover wrong terminal
state, active output, retained owner, changed job, enabled schedules, retained
TX request, pin stuck ON and malformed/foreign admitted authority. All failures
retain the charge, stop and restore; there is no automatic admission retry.

Source adversarial assessment checked ambiguity before job binding, boot/device
identity, persistence order, STOP authority, failure restoration and candidate
source binding. Both demonstrated findings are repaired. No additional source
finding remains within this slice; target execution and final assessment follow.

## Execution reservation

This newly requested follow-up selects exactly `standalone_stop`, once, with
one admission / 111.591999892 seconds reserved including warmup. The prior
campaign's 15 / 541.776002676 remains spent, without refunds or ledger edits.
If this single attempt stops, it is not automatically repeated. A complete
260-second managed SDR capture includes the finite occurrence and inactive tail.

## Validation and target result

**PASS_GPIO_FUNCTIONAL_RF_REVIEWED.** The single target attempt passed; there
was no RF retry. Both original findings are closed. This completes the
standalone portion of steps 1/5 and brings available target coverage to
thirteen passed GPIO/RF cases.

- All 45 existing/affected runner behavioral checks passed on macOS and
  `wspr5`; the standalone scheduler CTest passed.
- Clean `restore` and `cue` candidates passed linked-image, stack/reserved
  storage, UF2, fixture isolation and ordinary platform link checks.
- Source, firmware and runner commit:
  `f5ecdeb7cd543dfbaa778d9c5f73c8dfe841fd8e`.
- Cue UF2 SHA-256:
  `7efc282bc466a7d78999ac3de48aad31b4749877a70f3557f51f832c2277a11d`.
- Restore UF2 SHA-256:
  `f356fbc996d87b9e2a1fcd9cbe20d78fd79fb30775ea668d24fbcaa903bf542b`.

B is Pico 2 W / RP2350, USB serial `CDDBF8767C506C07`, device ID
`29f20b7342051ef947aa56cb9d4fab42`. Active firmware used 138 MHz, PIO/DMA RF
on GP2, WSPR with warmup, and the onboard CYW43 GPIO 0 indicator. Case boot
`a55148f4823970a1ffc99aef09c36243` admitted the actual scheduler job
`eeeeeeeeeeeeeeee18dc6578bb54ea00`; the unused packet template ID was not
credited as the actual job. The binding was persisted before STOP.

Checked Running authority reported active RF, the expected standalone owner
and actual GPIO ON. STOP/DISABLE succeeded; the same job became `aborted`
with RF inactive, owner released, schedules disabled, TX request cleared and
known GPIO OFF/error zero. It retained its job ID as the protocol permits.

The conducted RSP1B `2404058C60` used CF32, 250 ksps, 3.55 MHz center,
200 kHz bandwidth, gain 20, channel 0 and AGC/bias off. At test frequency
3.5701 MHz, the independent analyzer detected RF and an inactive tail. The
complete 260-second capture contains 65,000,000 samples / 520,000,000 bytes;
receiver identity/settings, sample count, content hash and verified capture
cleanup passed. This is uncalibrated RF presence and functional GPIO evidence;
optical/sub-poll edge timing is not claimed.

The follow-up spent 1 admission / 111.591999892 seconds reserved. The two
campaigns combined retain **16 admissions / 653.368002568 seconds** reserved;
the old 18/600 campaign was not reset or refunded. This newly authorized
one-case follow-up had its separately recorded one-admission limit.

## Final adversarial assessment and restoration

The final assessment checked actual job/boot continuity, binding before STOP,
one SCHEDULE only, valid GPIO ON/OFF, released ownership, complete receiver
evidence, exact clean images, settings retention and final inhibited authority.
No additional actionable finding remains in this slice. The twelve preceding
passes remain applicable; the original partial standalone and failed ledgers
remain unchanged. Their state hashes were checked against the published record.

B is restored to ordinary inhibited revision `f5ecdeb7cd54`, boot
`41fb9fa1294d49c59f094033042654f0`, 150 MHz, empty job, unowned, RF inactive,
schedules disabled, actual onboard GPIO known OFF/error zero, and stable
settings identical to the retained entry. A remains revision `6c7b14321003`,
boot `e83cac69de154245a974a3efdf5fc8af`, 150 MHz, idle/unowned/inactive and
with identical settings; it was not flashed. Final read-only inventory
completed for both boards and closed transport ownership.

Private evidence is under `/home/pi/phase13-led-stop-f5ecdeb/build/` on
`wspr5`: `stop-run/`, `final-inventory/` and `execution-reservation.json`.
`stop-run/assessment.json` closes the reviewed disposition separately from the
unchanged machine ledger's RF-review-pending label.

| Evidence | SHA-256 |
| --- | --- |
| Run state | `b124e048473477dd0a3fc1cdb7fbca609aef97356091db524eb23223e12b3dc0` |
| Run events | `cdead1edbe5ab1bb9ca43bbb0765773eff7d69174cbf58332a663ba66b370a0d` |
| Complete RF capture | `ee8371b7e4fdc3e5652cf45b6f3a25a67d0992da2d6167bf9ff23ff6e4e6dd43` |
| Final inventory state | `9311f058807ef7ae673e636f79efade4cb89e319fddcc4306b3031d4f5e0d553` |

No new backups, camera setup, timed operator actions or new dependencies were
introduced. External LED high/low and physical GP14 cutoff remain the only
unexecuted test cases; their untimed operator setup remains step 2. Full
matrix/release qualification is not claimed by this scoped closeout.
