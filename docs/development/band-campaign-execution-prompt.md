# PIO band campaign execution prompt

Work in WsprryPico's `devel` branch. Preserve existing changes and independent
repositories. Read the project contract, architecture, development procedures,
current RF implementation, WTP contract and Qualification Harness operating
contracts. Inspect source state and tools before changing anything. The user
requests implementation, bounded conducted measurements, adversarial review,
iterative repairs, then commit and push.

## Objective and scope

Implement a reproducible campaign covering the amateur-band test frequencies
from 2200 m through 2 m. Establish usable engine/mode/band combinations rather
than assuming coverage. Generalize the portable PIO waveform planner, expose
truthful experimental WTP capabilities, add Pico/WTP campaign control, implement
QRSS/FSKCW/DFCW complete event jobs, and reuse the independent Qualification
Harness receiver/analysis capabilities. Keep target-specific adapters and run
records in WsprryPico. The user subsequently explicitly included the Harness
repository: implement its device-neutral WTP controller, evidence validation,
tests and operating documentation on devel and commit/push both repositories.

Keep WTP/1 device neutral and unchanged. Use complete, immutable, bounded event
jobs; all transitions and symbol timing remain local on RP2350. Retain GP2,
the selected 138 MHz sample clock, pinned SDK/toolchain, standard-image RF
inhibition, finite stopping, ownership, abort/disconnect and fault cleanup.
Reject invalid arithmetic, unsupported frequencies, excessive distinct tones,
invalid event timing and unsupported job sizes before RF. Support only direct
baseband synthesis below Nyquist; mark 2 m and any other out-of-range band
unsupported rather than silently using an alias or harmonic. A future image or
harmonic engine requires a separate declared design and qualification.

## Physical setup and bounds

The user reports Pico RF -> 60 dB attenuation -> combiner -> SDR and Leo Bodnar
GPSDO RF -> separate 60 dB attenuation -> the same combiner/SDR. The GPSDO is
USB-connected to wspr5 and controllable using project-owned lbgpsdo Python code.
Verify exact Pico/device/image, SDR serial/settings, GPSDO serial/output/lock,
source states, tool versions, storage and non-interference before operating.
Use `ssh wspr5` and existing trusted tooling. Preserve unrelated services and
work. Treat attenuation as user-reported, not measured frequency response.

Install cleanup before source activation. Keep both GPSDO outputs disabled
and verify that state before Pico jobs. For reference observations, first
verify Pico output inactive, enable only the identified connected GPSDO output,
record lock/state and a finite capture, then disable and verify both outputs.
Never enable a reference when Pico output is active or unknown. Bound each
capture and job, preserve diagnostic evidence on errors, stop on fixture or
cleanup failures, and leave both sources inactive at completion. Restore the
inhibited Pico image after measurements. Do not operate an antenna path.

## Campaign and evidence

Resolve and retain a complete plan with frequency list, modes, exact jobs,
clock/correction, identities, receiver geometry, repetition counts, durations,
measurement thresholds and output paths before live execution. Hardware-free
planning and tests must not access devices. Require an explicit live flag.

For each supported band, first obtain RF-off evidence and a finite TONE screen.
Measure requested-frequency offset, on/off contrast, continuity, observed
spectral concentration/spurs and final silence. Only a passing carrier screen
permits WSPR on that band. Schedule three consecutive even-UTC WSPR slots,
retain complete captures and decoder stdout/stderr, and independently decode
each frame. Measure four-tone spacing, placement, drift, continuity and shutdown.
Run bounded QRSS, FSKCW and DFCW jobs with declared Morse text, timing and shift,
three observations per mode, and analyze transitions, durations, spacing and
quiet intervals. Do not relax gates after observing results to manufacture passes.

Bind every result to exact source/image hashes, board, pin, engine, clock,
calibration, RF path, receiver, tools, jobs, IQ and metadata. Separate indicated
from calibrated frequency and record uncertainties. Narrowband SDR captures
cannot establish wideband emissions or regulatory compliance. Unknown path
response or uncalibrated UTC must remain explicit limitations.

Generate a complete band-by-mode matrix with statuses qualified, failed,
blocked or unsupported and concrete reasons. Qualified means only the named
measured operational criteria for the recorded setup. Never infer qualification
from a build, simulation, a single decode, a neighboring band or old firmware.
Receiver/fixture failure is blocked; verified transmitter measurement failure is
failed; absent synthesis capability is unsupported. Cleanup failure overrides
measurement success. Retain interrupted/unattempted entries as blocked.

## Validation, review and delivery

Add deterministic behavior/failure tests for frequency planning and correction,
Nyquist/range boundaries, distinct-tone limits, waveform continuity and off
intervals, keyed event semantics, WTP lifecycle, campaign bounds, cleanup,
artifact authentication and classification. Use existing host CMake/CTest,
contract checks, appropriate Python tests, pinned firmware cross-build and image
checks. No test may incidentally access hardware.

Review implementation and evidence adversarially: seek false passes, wrong
frequency/clock/correction, stale identity or messages, timing truncation,
receiver-before-transmit violations, simultaneous sources, unbounded waits,
missing cleanup, misclassified receiver failures and unjustified scope claims.
Repair every actionable finding, rerun affected checks and repeat assessment.
Document verified results and real blockers without claiming incomplete work
complete. Commit attributable source/docs/tests only, push devel, verify remote
and local commit equality and working state, then report changes, checks,
measurements, limitations, final hardware state and commit identity.


## Operator amendments applied during execution

The connected GPSDO branch is physical Output 1. The user explicitly authorized
hardware and RF operations in both project scopes. After interrupted runs, the
user excluded another 2200 m retest and reclocking for this pass; finish the
remaining sweep with the existing 138 MHz image and report the retained limits.
