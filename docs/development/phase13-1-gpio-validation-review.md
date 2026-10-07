# P13.1 GPIO functional execution and adversarial review

The operator declined recording setup on 2026-10-07 and selected command
results plus actual hardware pin reads, accepting the preceding B OFF/ON/OFF
visual observations. The [executed prompt](phase13-1-gpio-validation-prompt.md)
uses no camera, repeats no visual operator check and creates no new backups.
Both named Picos retain RF authorization. B is the DUT; A stays unchanged.

**Final disposition: twelve full GPIO/RF cases passed; standalone STOP has
partial target evidence and an open checker finding.** External LED polarity
and GP14 fixture tests remain open. This round stopped after restoration;
no additional runner development or RF repetition was performed.

## Reviewed implementation

The pinned SDK's `cyw43_gpio_get` issues `WLC_GET_VAR` for `ccgpioin`, reading
CYW43 GPIO input bits. Pico 2 W's onboard LED uses that GPIO, not an RP2350
pad. The low-level set path returns success without propagating its IOVAR
write result, so the adapter now checks the actual level after ON and OFF
writes. An error or disagreement fails the write; it cannot acknowledge the
local transmit launch ticket. GPIO calls remain on the foreground core.

Console INFO exposes separate actual selected/onboard known, logical level
and error fields. Cached indicator state is still reported separately.
External logical readback respects polarity; disabled/uninitialized selected
outputs are unknown. The disabled case independently reads onboard OFF.

The runner selects canonical cases, uses only applicable fixtures, checks
hardware reads during actual Running and uncued Loaded/terminal states, and
collects managed SDR evidence without optical capture. Retained recovery
files are bound by serial/hash and live stable settings before mutation.
Verified application loads and a bounded reserved-range comparison replace
new full-flash saves. Final restoration requires ordinary inhibited firmware,
disabled schedules, released ownership, preserved settings and hardware OFF.

## Adversarial iterations and checks

- Read errors and mismatched pad levels cannot pass a write or the actual
  indicator-controller launch gate. Both external polarities and disabled
  unknown state are checked.
- Stale retained settings stop before ROM. Candidate deployment verifies
  application/reserved bytes without `save`; post-boot settings drift fails.
- Missing, duplicate or unknown selected cases and missing candidate roles
  fail before hardware. Onboard cases need no external or stop fixture.
- Review found that a steady RF signal could be mistaken for inactive noise.
  The repaired analyzer checks neighboring noise, presence expectations and
  an inactive tail; failed comparison reports are retained before STOP.
  Synthetic idle, burst, steady carrier, nonfinite, zero and short captures
  pass their behavioral checks. This evidence is uncalibrated RF presence.
- Second assessment found no remaining actionable source finding within this
  selected functional scope. Target execution remains required below.

Validation: seven affected CTests passed (indicator adapter/acceptance,
field access, RF worker, PIO/DMA, standalone and runner); three affected
ASan/UBSan CTests passed; 42 deterministic runner/setup checks passed;
two synthetic RF-presence tests passed; WTP contract validation passed.
The prior two unrelated full-suite baseline failures remain outside this
slice; this record does not claim a new full-suite pass.

## Target disposition

Four clean candidates passed linked-image/UF2/fixture checks. The first
launch stopped at control-host directory permissions before device mutation.
The subsequent runner stopped after deploying onboard firmware, before any
RF admission: the ownership tool reports a missing post-reboot endpoint as
a validation error. Immediate cleanup also encountered re-enumeration, leaving
STOP_UNCERTAIN. A fresh read identified the correct B, idle, schedules disabled,
RF inactive and actual GPIO OFF.

The repair distinguishes absent/disappearing Console endpoints (retryable
boot readiness) from an existing occupied endpoint (still an immediate STOP).
Three adverse endpoint checks pass. Existing failed records are retained;
zero RF admissions were charged. Recovery succeeded with verified inhibited restoration and zero admissions.
A rebuilt run then identified a second readiness race: Console is available
before the consumer Plain LAN clock listener. That run stopped before admission
and restored automatically. The repair retries only the two explicit listener/
station-readiness messages within the existing finite clock wait; identity
validation errors still stop before ARM. Behavioral checks cover both transient
messages and identity rejection. All stopped ledgers are retained and have zero
charged RF. A subsequent run reached LOAD, whose valid reply was coalesced with JOB_STATE.
The inventory decoder rejected the response suffix. The repaired LED peer
retains partial frames, decodes coalesced messages, validates event schema,
session and boot identity, and preserves command reply identity/CRC checks.
A real socket test covers fragmented events across two commands and coalesced
events before/after replies; wrong session/boot events fail. All seven existing
inventory regression checks still pass in their default strict mode.

These are host-adapter changes; all firmware inputs match clean source
`de06bc3f60da4bb15e0c42baaa5aab5c76db9f7d`. Explicit separate clean runner
and firmware commits permit reuse of the four verified images. Git comparison
rejects any changed firmware/CMake/protocol/dependency input; that rejection is
tested. Image revisions and hashes remain bound to the actual firmware commit.
The third stopped run also restored automatically with zero RF admissions.
No ambiguous ARM is replayed. Live LOAD/ABORT/RELEASE then passed on ordinary inhibited B, with actual GPIO
OFF and unchanged settings. The next run admitted one 15-second tone and
recorded 26 actual active-ON observations, followed by actual OFF. It stopped
because the harness expected `completed`; both Console and WTP use normative
`complete`. The model and runner are corrected to that real state. A controlled
launch failure also accepts a verified `missed` deadline as well as `failed`,
requiring no Running/RF observation, rejected ON writes and actual OFF.

The stopped tone is definitively complete: its matching WTP JOB_STATE event
has the charged boot/job and inactive output; cleanup is VERIFIED_INHIBITED.
Its 16-second reservation remains spent. Budget continuation requires verified
restoration and a matching terminal event for every unconfirmed admission;
an ambiguous admission refuses repeat. Tests cover refusal and retained charges.
A complete reviewed repeat plus the other cases reserves **14 admissions /
430.184002784 seconds** across runs, within 18/600; no reservation is refunded.
The continued target run passed eleven cases: all five modes, active abort,
armed cancellation, inhibited behavior, AP/Identify priority and disabled
indication. The standalone fixture saved its finite schedule but admitted no
job during the full 130-second window: ConsumerPreClock intentionally suspends
the ordinary scheduler. Cleanup restored inhibited firmware and settings.

The repair creates a separate real Scheduler only in explicit test images;
ordinary consumer suspension remains intact. The fixture preserves station,
network and pins, permits one finite daily occurrence with expiry, polls the
actual scheduler and sends STOP to the same instance that admitted its job.
Adversarial review also identified competition from an unsuspended engineering
scheduler and setup too close to a boundary. The fixture now suspends the
ordinary scheduler before saving its occurrence and skips a boundary that
lacks arm margin. A real Scheduler test covers both consumer/engineering
suspension, a near-boundary setup, unsynchronized refusal, admission, STOP, no second
occurrence and preserved settings; its normal and ASan/UBSan runs pass.
The no-admission budget exception is bound to exact pre-fix firmware `de06bc3`,
matching device/revision/profile and a full-window immutable suspension trace.
Other unknown or ambiguous admissions still refuse continuation.

## Final target results and assessment

| Cases | Target result |
| --- | --- |
| Warmup/tone, WSPR, QRSS, FSKCW, DFCW | PASS: actual selected GPIO ON while RF active, OFF after completion; independent RF presence and inactive tail |
| Active abort, armed cancellation, inhibited behavior | PASS: expected RF activity/absence, checked GPIO and terminal cleanup |
| Onboard AP, onboard Identify, disabled indication | PASS: TX priority or independently checked onboard OFF for disabled selection; expected RF evidence |
| Controlled ON-write launch failure | PASS: 55 rejected writes, terminal `missed`, no active RF, actual GPIO OFF; independent RF absence and inactive tail |
| Standalone STOP | PARTIAL: scheduled job reached Running with actual GPIO ON; STOP produced `aborted`, owner released, RF inactive and actual GPIO OFF. Checker expected `empty` and timed out; full case remains open |
| External high/low, GP14 cutoff | NOT RUN: fixtures unavailable |

The eleven-case run used runner `c84c3b6178b0caecc6d7de02c1dbb1bc9f7bae0f`
and firmware `de06bc3f60da4bb15e0c42baaa5aab5c76db9f7d`. The standalone and
failure runs used clean runner/firmware
`66da06e8522ca00dc0a4d62da741fd40d8e5e8c8`. The later acceptance-fixture
portability fixes at `cacdd75` passed host/sanitizer checks; those fixes were
not rebuilt or flashed during this final round.

B is serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`. Active candidates used RP2350 at 138 MHz,
PIO/DMA RF on GP2 and onboard CYW43 GPIO 0. The conducted receiver was RSP1B
`2404058C60`, CF32 at 250 ksps, center 3.55 MHz, 200 kHz bandwidth, gain 20,
channel 0, AGC/bias off; test frequency 3.5701 MHz. These observations establish
functional GPIO and uncalibrated RF presence, without optical edge claims.

Private original ledgers remain on `wspr5`:

- `/home/pi/phase13-led-gpio-c84c3b6/build/gpio-run`: eleven PASS rows;
  overall STOP on the earlier suspended-scheduler fixture; VERIFIED_INHIBITED.
- `/home/pi/phase13-led-gpio-66da06e/build/gpio-run`: standalone STOP partial;
  overall STOP on terminal predicate; VERIFIED_INHIBITED. Its stopped
  236,630,016-byte SDR fragment detects RF followed by an inactive tail using
  the existing analyzer. The capture is explicitly incomplete and does not
  qualify full case acceptance.
- `/home/pi/phase13-led-gpio-66da06e/build/gpio-failure-only`: failure case
  PASS_GPIO_FUNCTIONAL; final RF review passed; VERIFIED_INHIBITED.

Aggregate reservations are **15 admissions / 541.776002676 seconds**, within
18/600. The final one-case run adds 1/11 to the preceding cumulative 14/
530.776002676 ledger; it does not reset or refund the aggregate. No ambiguous
admission was replayed. No new backups, external cases, GP14 cases or operator
recording were added.

Final adversarial assessment preserves two related automation gaps for
standalone STOP: accept the actual terminal `aborted` state with inactive RF
and released owner, and bind the charged attempt to the scheduler's actual
job ID rather than the unused template ID. The retained attempt remains
ADMISSION_PENDING, not retroactively PASS. These findings are open; further
runner work and target repetition stopped in response to the operator's
cost/time concern. A full standalone repeat exceeds the remaining RF
reservation, so no such repeat was attempted.

Final read-only inventory at
`/home/pi/phase13-led-gpio-66da06e/build/final-inventory-ready` completed for
both boards and closed transport ownership. B is ordinary inhibited revision
`66da06e8522c`, boot `7b64397af68aae0a6a7bd847de04516f`, 150 MHz, schedules
disabled, RF inactive, actual onboard GPIO known OFF with error zero and stable
settings matching the retained entry. A retains revision `6c7b14321003`, boot
`e83cac69de154245a974a3efdf5fc8af`, 150 MHz and identical stable settings;
it was not flashed. The immediate earlier inventory was partial only because
B's LAN listener was still starting; its successful Console restoration
read and the later complete inventory are both retained. Final inventory state
SHA-256: `076bf264413018d5249f67da0be477dd2d32437e346be823e0354bf9271effdd`.
