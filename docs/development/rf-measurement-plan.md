# Bounded conducted RF measurement plan

Status: suggested measurements for Step 8 and later. The operator decides when
to transmit, selects the setup and can change the sequence or comparison targets.
This document adds no transmission permission mechanism or mandatory interlock.
No cable, SDR operation, flashing, GPIO action or RF output is needed to complete
Step 7. The [feasibility decision](../rf-feasibility.md) selects an experimental
PIO/DMA candidate; it does not establish a safe output circuit or qualified RF.

## Setup record for interpreting results

Record the following in the run manifest; identify unknowns as limitations:

- Pico 2 W board identity/revision; RP2350 revision where readable; exact Git
  revision, firmware SHA-256, SDK/toolchain, configuration and engine version.
- Actual system/sample/reference clocks, frequency correction and uncertainty;
  UTC source, start epoch and uncertainty; pin and header number, drive setting,
  complete buffer/coupling/filter/inhibit circuit and power supply.
- SDR make/model/serial, input port, manufacturer absolute input and DC limits,
  reference source/calibration age and uncertainty, sample rate, bandwidth,
  gain/AGC state and software revision. Do not infer the available SDR from
  another repository or earlier campaign.
- Counter/scope/logic instrument identity, timebase/reference and uncertainty.
  A USB arrival timestamp or ordinary SDR waterfall cannot independently verify
  microsecond GPIO deadlines or absolute UTC start.
- Every cable, attenuator, DC block, termination, buffer and filter; frequency
  range, impedance, measured loss/tolerance, power rating and connection diagram.
- Exact tone/event job and digest, maximum RF-on duration, repetition count,
  expected transitions, local deadline, inhibit action and operator stop method.
  Synthetic tone sequences need no encoder extraction or valid station message.
- Tested recovery procedure, output-off observation method and evidence paths.
  Record remaining instrument limitations before interpreting a pass/fail result.

Missing identities or instrument limits affect what the evidence can establish.
Report them to the operator without inventing values or turning this checklist
into an additional approval process.

## Connection and level calculation

Proposed topology: candidate GPIO -> reviewed buffer/protection and matching ->
DC isolation as required -> characterized filter -> rated attenuation -> SDR
input. Include a terminated measurement point for initial power/spectrum checks.
Use conducted connections only; an antenna is outside this plan. A GPIO is not
a specified 50-ohm source. Attenuators protect the receiver but do not by
themselves make the GPIO load, DC path or return wiring acceptable.

Determine a conservative maximum source power across the signal and relevant
harmonics, including startup/fault conditions. Let Pmax be that maximum in dBm,
Lmin the minimum total path loss in dB after tolerances, and Plimit the lower of
the receiver's documented damage limit and its chosen linear measurement ceiling.
Require Pmax-Lmin <= Plimit-M, where M is an explicit safety/uncertainty margin
of at least 10 dB for this proposed bench plan. Also verify DC/peak voltage,
attenuator dissipation at each stage, frequency coverage and source loading.
Do not count unmeasured filter rejection as protection.

Illustration only: if independently established Pmax=+10 dBm and the selected
linear ceiling is -20 dBm, M=10 dB requires at least 40 dB *minimum* path loss.
These are not values for the user's SDR or Pico output. No fixed attenuation
recommendation is possible until the setup is identified. Verify power into a
rated termination before attaching the protected SDR. Connect, move cables and
change attenuation only with output inhibited and verified off.

## Proposed finite sequence

The following counts and durations define one reproducible suggested sequence.
The operator chooses stages, changes, repetitions and whether to proceed after a
finding. Preserve failed results when interpreting subsequent evidence.

1. With output physically inhibited, verify the local timeout and stop path,
   including producer/DMA faults. Inspect boot/reset/abort behavior with appropriate
   instruments. Record the observed stop behavior.
2. Verify the connection and source-power bound into a suitable termination,
   using one 2 s tone at 3,570,100 Hz in this suggested sequence. Record output
   power and the chosen stop method before interpreting receiver measurements.
3. Through the chosen protected SDR path, acquire four separate 5 s tones at
   base+t*(375/256) Hz, t=0..3, each separated by at least 5 s verified off.
   Keep raw IQ, actual output start/stop observations and overload indicators.
4. Acquire one 16-symbol job with repeated 0,3,1,2 ordering (10.922666667 s
   rounded at the final nanosecond), preserving phase state. Record physical
   transition timing and IQ together; compare all tone changes, not just averages.
5. Acquire one 162-symbol synthetic WSPR-timed job (110.592 s), then at least
   10 s off. This is a timing/FSK test, not proof of WSPR encoding or decoding.
   Confirm completion without further USB data. Bound any induced load in the
   manifest; transport disconnect alone must not alter a running WTP job.
6. Three separate 2 s maximum fault jobs: requested abort, producer starvation,
   and engine reset. Observe whether the selected stop path prevents stale-buffer
   replay or reactivation. Distinguish an intentional fault stop from job completion.
7. One separately recorded repeat of stages 3..5 after
   15 minutes of powered, RF-off warm-up estimates drift. Any additional bands,
   wireless load tests or long runs can be recorded as operator-selected changes.

Maximum RF-on time for this proposed sequence is 291.029333334 s, including the
initial power check, three fault jobs and the warm repeat. Wall time is longer
due to off intervals and warm-up. Each job must have its own local deadline;
these are ordinary finite-job semantics. Report unexpected RF, overload, missing
samples, clock loss, deadline misses or inability to verify off. The operator
decides the response and any subsequent testing; this plan does not add a
separate permission policy.

## Measurements and proposed comparison targets

These are candidate screening budgets, not regulatory limits, WTP amendments or
release qualification or transmission prerequisites. To compare a result with a
chosen budget, include its measurement uncertainty:
pass only when |measured error| plus its declared uncertainty is within the limit.
If the instrument cannot resolve a quantity, mark it unqualified, not passed.

| Quantity | Method and proposed target |
|---|---|
| Mean frequency | Fit phase slope on each steady 5 s IQ segment with a calibrated independent reference. Error relative to the frozen accepted frequency <=0.1 Hz. Report requested-to-accepted quantization separately. |
| Tone separation | Compare fitted tone differences with 375/256 Hz, error <=0.05 Hz; all four distinct. Receiver/reference error must be accounted for. |
| Start | Reference-triggered scope/counter against the manifest epoch; physical RF onset error <=1 ms including UTC uncertainty. A synthetic monotonic start only qualifies relative start. |
| Symbols / frame | Physical transitions or phase fits against absolute deadlines; each boundary <=10 us and total frame error <=100 us. State the sample-clock contribution. |
| Retuning | Fit phase before/after transitions against a continuous-phase model; residual step <=0.1 rad, no unexplained dropout >10 us or transient tone. Resolve sample-grid ripple separately. |
| Drift | Warm/cold difference <=0.1 Hz after reference correction for the initial point; report temperatures and reference uncertainty. No general temperature specification follows. |
| Spurs / harmonics | On steady tones, screen discrete emissions >=10 Hz away from carrier to at least the fifth harmonic, including modeled folded images, against -40 dBc after the actual filter. Record closer-in phase/noise behavior separately. No claim outside measured coverage. |
| Disable / faults | Physical RF suppression >=60 dB relative to on level within 1 ms of local fault/abort detection, including receiver noise-floor uncertainty; no reactivation through at least 10 s and a tested reset cycle. A status flag alone is insufficient. |
| Resources | No underruns, stale buffers or missed events; half-buffer generation worst case <=1.747626 ms under the declared load. Log high-water memory and latency without disturbing the RF deadline path. |

Use long coherent records and phase estimation for sub-hertz measurements;
zero padding does not improve actual resolution. Record FFT window, segment
length, effective noise bandwidth, integration and level calibration. Subtract
frequency-dependent cable/filter loss when comparing upstream source emissions;
clearly distinguish those from emissions measured after the filter. Repeat a
suspected spur with more attenuation to distinguish receiver distortion from a
source component, recording any operator-selected additional observations.

The SDR's tuned bandwidth is not full harmonic coverage. Use separate bounded
captures or a suitable spectrum analyzer when necessary; lack of coverage
leaves that spectral result unqualified. This sequence uses the initial frequency.
High-band
folded images may be inside the passband and cannot be assumed removed by a
low-pass filter. Characterize filter loss/rejection with appropriate equipment
before claiming it fixes the model's spur risks.

## Closeout and promotion

Record commanded and observed output state at the end of each selected stage,
including failed cleanup. Keep raw captures,
manifest, analysis versions, checksums, uncertainty calculation and rejected
runs together outside source control. A final record states pass/fail/unqualified
against each comparison target and lists exact engine/mode/frequency/setup coverage. No evidence
transfers to another pin, clock, firmware, receiver or filter without assessment.
The operator decides how to proceed; describe supported performance only to
the extent established by the measurements.
