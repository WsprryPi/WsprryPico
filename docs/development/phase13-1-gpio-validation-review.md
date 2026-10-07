# P13.1 GPIO functional execution and adversarial review

The operator declined recording setup on 2026-10-07 and selected command
results plus actual hardware pin reads, accepting the preceding B OFF/ON/OFF
visual observations. The [executed prompt](phase13-1-gpio-validation-prompt.md)
uses no camera, repeats no visual operator check and creates no new backups.
Both named Picos retain RF authorization. B is the DUT; A stays unchanged.

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

Standalone STOP and controlled launch failure remain to execute with rebuilt
cue/restoration images. Their reservations bring the aggregate to **15
admissions / 541.776002676 seconds**, with all prior charges retained. No
external or GP14 case is added. The selected cases are warmup, WSPR, QRSS, FSKCW,
DFCW, active abort, armed cancellation, inhibited behavior, onboard AP,
onboard Identify, disabled indication, standalone STOP and controlled
ON-write launch failure. External high/low and physical GP14 cutoff remain
pending their fixtures. No calibrated optical edge timing is claimed or
required for the operator-selected GPIO functional scope.
