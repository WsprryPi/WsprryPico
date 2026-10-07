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
ASan/UBSan CTests passed; 37 deterministic runner/setup checks passed;
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
zero RF admissions were charged. Recovery and a rebuilt clean-source run are
pending. No ambiguous ARM will be replayed. The selected cases are warmup, WSPR, QRSS, FSKCW,
DFCW, active abort, armed cancellation, inhibited behavior, onboard AP,
onboard Identify, disabled indication, standalone STOP and controlled
ON-write launch failure. External high/low and physical GP14 cutoff remain
pending their fixtures. No calibrated optical edge timing is claimed or
required for the operator-selected GPIO functional scope.
