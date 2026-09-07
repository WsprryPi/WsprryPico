# PIO campaign adversarial review

This review covers the Pico planner, five-mode campaign adapters, and the
Qualification Harness WTP controller. Hardware-free checks do not establish RF
qualification. The physical sweep and final assessment are recorded below.

## Repairs before the full run

- Generalized arithmetic uses exact bounded 64-bit division on RP2350. Independent
  scalar waveform and arithmetic oracles cover frequency/correction boundaries,
  Nyquist rejection, inactive events and excessive distinct frequencies.
- Lost LOAD and ARM replies retain evidence and attempt ABORT of the owned job.
  Receiver hard deadlines and source inactivity checks bound cleanup.
- GPSDO library channels are zero-based. The adapter translates the user's
  physical output number, disables independent PPS, verifies both outputs off
  before Pico jobs, and checks reference lock/output state after capture.
- The artifact validator rejects mismatched plans/jobs, duplicate observations,
  fabricated complete matrices, inconsistent decoder claims and invalid capture
  metadata. Its stated scope is artifact/claim validation; it does not rerun IQ.
- Trial A exposed retained ownership after short jobs: reopening USB does not
  release a WTP lease. The Harness now explicitly releases only its own lease
  after verified terminal/abort state, checks the release, and handles a lost
  CLAIM reply. Consecutive-short-job and foreign-owner regression tests pass.
- The Pico WTP client now rejects wrong-session, wrong-protocol and wrong-operation
  replies even when their request counters match.
- A 20 ms phase difference previously wrapped offsets outside +/-25 Hz. Both
  WSPR and continuous keyed transition measurements now subtract unwrapped phase
  samples. Independent +40/+45 Hz fixtures pass while delayed transitions fail.
  This repairs measurement range without changing acceptance limits.
- WSPR and keyed observations now retain active-interval averaged spectral
  diagnostics. A known -20 dBc synthetic spur checks the estimator. These are
  receiver-span peak-bin comparisons, not wideband emissions qualification.

## Retained physical trial A

The trial used RP2350 A2 chip `0bf4b4aec9ffb344`, GP2, 138 MHz PIO/DMA and
RFWTP UF2 SHA-256
`c1e559eddfc2e4c9456d920e730c76445fe97edd017547c3a84e2e1d4b19d5b1`.
Its source revision string is `27791cf28048-dirty`; the bundle records source
file hashes. RSP1B `2404058C60` received separately attenuated Pico and GPSDO
branches through the user-reported combiner. GPSDO `0673ED0FA107` Output 1 was
selected explicitly by the user.

Ignored evidence: `build/pio-smoke80-20260907a/`. Its validation reports
`complete=false`, `cleanup_verified=true`, five WTP transactions and one
operationally qualified row. TONE passed. All three consecutive WSPR frames
independently decoded AA0NT EM18 37; noisy transitions and a symbol residual
failure prevented RF qualification. QRSS was interrupted after its first
observation by the ownership bug. The remaining observations were not completed.
No acceptance limit was relaxed in response to these measurements.

## USB recovery limits

The old RF-inhibited image was silent on both command ports. macOS continued
listing the same USB service during reported disconnect attempts, so those
listings did not prove firmware execution or failed physical resets. After the
USB service disappeared, physical BOOTSEL was detected and the image was loaded
and verified. The new image answered INFO and WTP probes; its software BOOTSEL
command and return to application mode were verified without another manual
reset. This does not establish the original fault's root cause or prove recovery
from every possible USB or firmware failure.

## Full sweep A interruption and continuation boundary

`build/pio-full-20260907a/` retained all thirteen supported TONE screens,
all scheduled keyed observations for 2200 m and 630 m, and three consecutive
630 m WSPR frames. At the first 160 m WSPR LOAD, the endpoint stopped answering.
No ARM was sent for that job. The finite receiver finished and verified its
cleanup; GPSDO frequency outputs and PPS were verified disabled. Pico INFO and
software BOOTSEL did not answer. The cause remains unresolved. Neither repeated
USB enumeration nor host-only checks prove firmware health.

Artifact validation passes with `complete=false`, `cleanup_verified=false`,
75 matrix rows and 34 completed transaction records. Cleanup failure blocks
qualification from this run even where individual observations passed. The
original bundle is preserved unchanged. A continuation must verify the Pico
again and record its own source, firmware, clock and RF path identities.

Additional review repairs preserve the owned receiver handle until capture
validation succeeds and impose a remote deadline on GPSDO control. Regression
checks cover failed receiver cleanup. One logical WTP session now spans campaign
USB reconnects, with fresh frame parsing and monotonically increasing request
IDs. This bounds session replay accumulation without changing firmware or RF
timing. A reconnect test rejects counter reuse and old queued terminal evidence.
This is a resource-use improvement, not a proven diagnosis of the USB stall.

The operator explicitly excluded another 2200 m retest and any reclocking from
this pass. The prepared continuation plan covers the remaining 160 m through
2 m entries, retaining unsupported 4 m and 2 m rows. The continuation and final band executions are recorded below.

## Continuation B and second control stall

After the operator reconnected the Pico, INFO verified the same device,
`27791cf28048-dirty` firmware revision and 138 MHz clock, with an inactive output.
`build/pio-remaining-20260907b/` completed the 160 m through 17 m workloads and
its first 15 m WSPR frame. It then stopped answering during the second 15 m LOAD.
No ARM was sent for that failed job. One logical WTP session was in use, so this
failure demonstrates that session reuse did not eliminate the fault.

The finite receiver finished with verified cleanup. GPSDO frequency outputs
and independent PPS were verified off. Pico inactivity remained unverified;
INFO and BOOTSEL recovery probes became stuck in macOS serial access and their
owned processes were killed. The fault's root cause remains unresolved. The
firmware and clock were not changed to work around an RF measurement failure.

The sealed continuation validates as incomplete, with cleanup unverified,
65 matrix rows, 96 completed WTP transactions and no operationally qualified
rows. Its original records remain unchanged. All 21 WSPR frames from completed
band sequences decoded independently. The separately preserved first 15 m frame
also decoded, but cannot satisfy the three-consecutive-frame criterion.
`build/campaign-recovery-20260907c/` retains that interrupted receiver capture,
its native metadata, a recovery boundary record and the separate diagnostic.

## Additional adversarial repairs

- WTP control now checks negotiated version, boot continuity, LOAD job/state and
  ARM job/state/start acknowledgments, and requires terminal output inactivity.
  Retained transaction validation checks those same acceptance claims.
- The offline WTP CLI rejects malformed nested evidence with structured failure
  output, including wrong container types and a boolean schema version.
- Pico evidence validation binds each transaction's device, revision and clock,
  and each observation's receiver identity/settings, to the recorded campaign.
  Completed rows must contain the required observations. Nested inventory files
  are included in the artifact boundary, and lifecycle/scope claims are strict.
- The transition analyzers now distinguish excessive frequency-fit residuals
  from timing errors and unresolved boundaries. Independent small phase-wobble
  fixtures produce fit failures with passing timing; delayed-edge fixtures still
  fail timing. No RF acceptance limit changed. Earlier raw logs retain their
  broad labels, and reporting derives the failure category from numeric values.

The applied repairs passed all 23 Pico host checks, WTP contract validation and
59 focused Harness controller/viewer tests. The final full Harness suite passed 1,611 tests in 419.44 seconds after the
malformed-evidence repair. Ruff formatting/lint, mypy (66 source files), package
build and both native checks passed. A final input-review reassessment found no
additional actionable code issue in this implementation slice.

A subsequent targeted libusb reset opened the uniquely enumerated RFWTP device
but did not return before its ten-second deadline; the helper exited on SIGALRM
and the Pico did not reenumerate. Its source and log are retained in the recovery
bundle. This did not establish firmware recovery or output inactivity.
The operator subsequently reconnected the device; the recovery and final
assessment below supersede that waiting state.


## Final recovery, sweep and reporting assessment

The latest physical reconnect produced a new USB service. INFO verified the
same board, RF image revision and 138 MHz clock with empty/inactive state.
Separate 15 m, 12 m, 10 m and 6 m bundles then completed with verified cleanup.
Guarded software BOOTSEL and reload of the identical RF image succeeded between
these bundles. No additional 2200 m retest or reclocking was performed.
Restarting between bundles is a bounded execution workaround, not a repair or
qualification of long-running USB reliability.

The final evidence review checked all 75 row dispositions against their source
bundles, all eleven completed three-frame decode sequences, cleanup precedence,
firmware/path identity and the distinction between diagnostic spectrum and
calibrated emissions. The artifact validator accepted both interrupted runs,
the separate smoke trial and all four final band bundles with their actual
completion and cleanup states. Earlier passing observations were not promoted
across reset boundaries.

Two reporting issues were corrected during the final adversarial assessment:

- The third 10 m WSPR frame's amplitude detector split the signal during a
  roughly 6 dB dip after a peak. Retained IQ remained about 60.7 dB above quiet
  in the affected window. The report identifies a detector/analysis failure;
  it does not infer transmitter silence or a physically shortened frame.
- The broad 6 m coherence/continuity label hid an indicated frequency-placement
  failure: its TONE offset was +146.699 Hz against the fixed 100 Hz limit.
  The report distinguishes that measured cause without claiming calibrated
  transmitter error or relaxing the gate.

Reassessment found no further actionable implementation or reporting defect
within this slice. RF criterion failures and the unresolved USB stall remain
explicit limitations; they are not claimed repaired. Tests after the last code
repairs passed as recorded above. Subsequent changes were results/documentation
only. The final hardware verification confirmed the standard inhibited image,
empty/inactive Pico status and both GPSDO frequency outputs plus PPS disabled.
See the [results](band-campaign-results.md) for exact identity and evidence anchors.
