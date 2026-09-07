# Experimental PIO band campaign

The [execution prompt](band-campaign-execution-prompt.md) defines this effort.
The portable planner now accepts direct-baseband frequencies from 100 kHz to
one Hz below half the selected sample rate, with at most four distinct NCO
increments, 162 events and 110.592 seconds per job. The explicit RFWTP image
advertises TONE, WSPR, QRSS, FSKCW and DFCW and its actual event/duration limits.
The standard firmware remains RF inhibited; its standalone schedules retain
their existing 80 m profile. WTP/1 is unchanged.

## Plan and adapters

`src/campaign/plan.py` creates the version-1 fixed campaign. `scripts/pio_campaign.py`
is its command-line entrypoint. The plan uses the WsprryPi family's nominal
actual RF test frequencies, 137,500 Hz through 144,490,500 Hz, including 4 m.
At the selected 138 MHz sample clock, 4 m and 2 m are unsupported direct
synthesis and receive explicit matrix entries without output attempts.

The host loads complete events through the Qualification Harness's portable
`wtp_control.run_transaction` API. That API owns protocol validation, HELLO,
CLAIM, LOAD, ARM, matching terminal evidence and bounded ABORT attempts. Pico's
adapter owns Mac USB ports, sampled host UTC, wspr5 SSH capture, GPSDO sequencing,
source identity and final quiescence. There is no per-symbol host delivery.
This is a Pico campaign route using Harness capabilities; it is not the existing
WsprryPi `complete-test` CLI route.

The user reports two separate 60 dB attenuated branches into a shared combiner:
Pico GP2 and the wspr5-connected Leo Bodnar GPSDO. The adapter uses project-owned
`/home/pi/lbgpsdo/lbe142x.py`, separately verifies frequency-output and PPS states,
and never enables a reference while Pico output is active or unknown. GPSDO
reference captures are sequential. The connected output is an explicit input.
Attenuation and filter response are not calibrated measurements.

Hardware-free planning:

```sh
python3 scripts/pio_campaign.py plan build/pio-campaign-plan.json
```

Use `--band` repeatedly to create a bounded subset. Omission selects all 15 bands.
`run --help` describes the explicit device, firmware, receiver, GPSDO and decoder
inputs. Live execution requires `--enable-rf`. All runtime output belongs in a
new ignored evidence directory. `--screen-only` is a diagnostic subset and never
marks the full campaign complete. The supplied output path contains a flushed
`progress.jsonl`, exact plan, matrix, source/tool hashes, captures, native metadata,
WTP logs, decoder output and an artifact index.

The existing Harness terminal viewer also accepts Pico band/mode progress logs:

```sh
/path/to/harness/.venv/bin/python /path/to/harness/src/wsprrypi_qualification/progress_viewer.py EVIDENCE_DIRECTORY/progress.jsonl
```

It is read-only and does not open either Pico serial port. Use `--replay` to
render a retained log and exit. The compact display is a convenience; the
artifact-validated matrix and retained captures remain the evidence.

## Measurements and scope

Each supported band starts with a five-second TONE screen and a separate GPSDO
reference observation. The Harness carrier analyzer measures off/on contrast,
requested-frequency placement and concentration; independent Pico measurements
check continuity, duration and captured-span spurs. WSPR runs only after its
band's carrier screen passes, using one coherent 370-second capture containing
three consecutive even-UTC slots at +1 second. Each frame is independently
decoded as AA0NT EM18 37 and checked for spacing, drift, symbol residuals,
transitions and silence. Encoded 37 dBm is message content, not measured power.

WSPR and keyed jobs also retain averaged active-interval spectrum diagnostics
with their receiver span and resolution.

Three independent ETE jobs per keyed mode use 0.7-second dots and a 5 Hz shift.
QRSS keys the carrier off; FSKCW marks high and spaces low; DFCW uses equal-length
high dots and low dashes with its reviewed one-dot inter-character gaps. The
independent Harness reference generator checks the complete expected timelines
in host tests. IQ analysis checks a single shared timing alignment, mark/space
frequencies, carrier continuity, envelope edges, FSK transition timing and quiet
intervals. It cannot hide a dropout by independently realigning each mark.

Operational gates are fixed before execution: 10 dB contrast, 100 Hz indicated
placement, 20 ms envelope timing, WSPR spacing within 0.05 Hz and residuals within
0.1 Hz, and keyed spacing/residuals within 0.2 Hz. Frequency transitions have a
10 ms WSPR timing limit, a 20 ms keyed timing limit and a 0.15 Hz fit-RMS limit.
A fit-noise failure is reported separately from a timing or unresolved-boundary
failure. Spectrum remains a diagnostic
relative peak-bin measurement. A `qualified` matrix entry applies only to these
operational criteria at the listed frequency and workload on the recorded
board/image/clock/path. It does not cover every frequency or workload within a
band and does not claim
calibrated UTC/GPIO onset, receiver sample clock, power, filter performance,
out-of-band emissions or regulatory compliance. Reference observations remain
separate from a calibrated receiver profile.

The matrix contains qualified, failed, blocked or unsupported results. Missing
observations and invalid receiver/cleanup evidence cannot qualify. Cleanup
failure overrides successful measurements. An incomplete campaign retains all
unattempted entries as blocked, and never substitutes old-build evidence.

Read-only artifact and scope validation:

```sh
python3 scripts/pio_campaign.py validate EVIDENCE_DIRECTORY
```

Use the existing Harness Python environment for analysis and validation (NumPy
and the Harness package must be installed). The validator checks all retained
hashes, plan/matrix scope, counts, consecutive slots and WTP evidence. It reports
its limit explicitly: it does not independently rerun every IQ analysis.

## Validation status

The [adversarial review](band-campaign-review.md) records repairs and retained
physical trial failures.

Host frequency/planner, independent keyed-reference, IQ fault, WTP lifecycle and
contract checks precede live operation. The pinned RFWTP and inhibited firmware
builds pass their memory-layout checks. The [conducted results](band-campaign-results.md)
record all 75 band/mode dispositions: eight qualified, eleven failed, forty-six
blocked and ten unsupported. Final band bundles completed with verified cleanup;
earlier interrupted runs remain blocked. The standard inhibited image was
restored and verified after the last RF observation.
