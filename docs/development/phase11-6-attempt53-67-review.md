# Phase 11.6 attempts 53-67 adversarial review

Status: **ACCEPTED AS AN OPEN CHECKPOINT; FURTHER RF PAUSED.** This review does
not close Phase 11.6, accept failed rows, authorize a reboot or turn sequence 67
into a pass. The immutable public result is
[`phase11-6-80m-60m-attempt53-67.json`](phase11-6-80m-60m-attempt53-67.json).

## Evidence decisions

- Sequences 53, 54 and 63 remain zero-RF failures. Their later corrections do
  not erase them or add an RF charge.
- Sequence 55 passes the exact-candidate zero-tail/lifecycle requalification and
  80 m TONE row. It does not transfer acceptance to keyed rows.
- Sequences 56, 57, 62 and 64 remain RF-charged failures at the unchanged
  phase-coherence/state-frequency gates. Their unspent paths remain unspent.
- Sequences 58-60 and 65-66 pass only their recorded reverse-profile DFCW
  paths. The project profile is dot-high/dash-low; the external/default
  convention remains dot-low/dash-high.
- Sequence 67 is an RF-charged failure. Physical completion and a valid capture
  do not replace the failed independent observer/resource gate or the absent
  ordinary analysis result.
- Cumulative accounting is 67 sequence attempts, 61 RF attempts and
  1,926.000045 charged planned seconds. The 15-attempt continuation contributes
  424.000010 seconds to the 1,502.000035-second sequence-52 baseline.

## Adversarial findings

The original sequence-67 browser result claimed `PASS` despite 120 refreshes,
107 unavailable results and target resource exhaustion. Accepting that label
would violate the campaign rule that the audit must not trust runner labels.
The retained final inventory is authoritative: 428 allocator failures, 214 TLS
allocation failures and a 16,693-byte last failed request. The row therefore
remains failed.

The repaired watcher maintains a consecutive-unavailable counter, resets it
after a successful refresh and fails on the fourth consecutive unavailable
result. This bounds additional pressure and makes a sustained unavailable page
fatal. It changes no firmware, waveform, frequency, target threshold or prior
evidence. A future physical packet must carry the new watcher hash; no prior
attempt may be re-audited as though it used the repair.

The timing evidence rejects the premise that coarser time is preferred. The
host waits for uncertainty at or below 10 ms. Sequences 65 and 67 admitted
newer 3.948996 ms and 3.948780 ms samples after initial 11.813152 ms and
13.001644 ms observations. The `210599d` firmware reprojects an Armed immutable
UTC target when a better sample changes the UTC/monotonic mapping. It retains
the minimum-launch guard, so a target that is genuinely too near after
reprojection still rejects safely.

## Restoration and continuation boundary

Sequence 67 reconciliation proves the terminal job complete and both Picos
empty, inactive and unowned before releasing the shared reservation. Subsequent
host cleanup restored wspr5's production service and recovery timer, removed
the isolated client namespace, stopped wspr4's campaign AP units and restored
its recovery timer. No Pico reboot, flash, CONFIG write or RF request was made
during restoration.

The nonzero allocation counters are latched for the current boot and the frozen
resource gate requires zero. Continuing therefore requires one separately
authorized controlled reboot of Pico A, followed by exact source/image/boot,
retained configuration, empty/inactive/unowned and zero-counter verification.
Sequence 67 is not scheduled for retry; the next independent slice is sequence
68, 40 m TONE.

## Validation

- `node --check scripts/phase11_6_browser_watch.js`: pass.
- Phase 11.6 attempt, plan, audit and WSPR-group unit suites: 39/39 pass.
- Both maintained Phase 11.6 JSON documents parse; continuation accounting
  recomputes to 424.000010 seconds and the cumulative total to 1,926.000045.
- `git diff --check`: pass.
- The full pre-existing `build-host` CTest registration ran 84 tests: 75 passed
  and nine did not. The failures are outside this watcher/documentation slice:
  stale historical source-drift assertions, a missing unbuilt `pio_dma_tests`
  executable, an expired test certificate and the local macOS 27 SDK/TAPI
  linker incompatibility. The affected Phase 11.6 suites passed independently.

Raw IQ, authenticated traffic, browser images and device journals remain in the
mode-0700 private campaign roots on wspr5. Absolute frequency remains
receiver-indicated and uncalibrated; no calibrated-power, harmonic, filter or
regulatory conclusion is added.
