# R2 remaining-mode execution prompt

Continue R2 through execution, adversarial review, correction of actionable
findings, affected checks, another review, commits and pushes to devel in Pico
and Pi. A fixture cleanup deadline ends that hardware session, not the overall
task. Preserve failures; never relabel or automatically retry an RF job.

## Existing evidence and impact

Reuse clean source `049cc929143bdec6ec32817f6df0c73a9637cdf5`, physical 138 MHz,
PIO divider 1, RAM rendering and network listener enabled. Physical UF2 SHA-256
`908fbe87a326366710ca0b4be4541e71d26e46b9e439f2d0257a9bfcd1490192`.
Do not rebuild or modify firmware. Reuse the exact image's R1 5/5 and three
passed browser-owned Tone jobs recorded in the amended review. No R1 assertion
is invalidated by these host helper changes. Refresh current board identity,
clock, configuration, output, ownership and resource health as admission checks;
these are not a repeat of R1. No heap probes or clock sweep.

## Remaining finite jobs

At 135.5 kHz, run one native production QRSS ETE job (three-second dots,
33 seconds total), then USB-reference FSKCW ETE (35 seconds), DFCW ETE
(17 seconds), and WSPR AA0NT EM18 37 (110.592 seconds). FSKCW spaces and DFCW
dashes use 135495 Hz. USB jobs retain their exact established events. Native
production QRSS omits the diagnostic one-second quiet prefix/suffix, so its
33-second event list is separately frozen from source, not called the 35-second
padded job. Browser submission is already covered by the three passed Tones.

Use the existing actual production executable from source
`6f65d5c7d202569102459ab68d7c9ea079b96f35`, SHA-256
`122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`.
Do not substitute a custom TLS actor. A private INI enables one scheduled QRSS
launch 90 seconds ahead with a 60-minute repeat interval. Bind the application's
first generated job ID and owner while Waiting, before dispatch, then freeze the
packet and start USB observation. End the process within the bounded interval,
well before a second scheduled dispatch. Audit exactly one LOAD/ARM/RELEASE.
This does not change the installed WsprryPi service or its configuration.

Each submission packet uses N300 browser actions and USB360 observations.
For the USB packet the idle production observer retains its 1 Hz / two-second
maximum start-gap requirement. Actual production-owned execution retains its
source policy: Waiting offers STATUS five seconds after each completed response;
Executing offers STATUS after each completed response and a ten-millisecond
pause, with lease renewals when due. Record native request starts, responses and
actual cadence. Require bounded five-second transactions, no reconnect/replay,
at most eleven seconds between Waiting STATUS starts and six seconds during
execution. Do not misapply the idle 1 Hz policy to a scheduled production owner.

USB submission and WTP observation share one exclusive endpoint owner; Console
INFO remains independent at 1 Hz. Admit only the frozen CLAIM/LOAD/GET_CLOCK/
ARM/RENEW/RELEASE sequence, at most twelve renewals, unique request IDs and no
RF retry. Retain complete raw framing, CRC, schema, response/identity binding,
Loaded/Armed/Running/Complete, output authority, release and terminal history.
The production path can transition through Loaded and Complete between 0.2 Hz
USB polls; its actual production wire must prove those states. Do not artificially
hold production states to satisfy a polling artifact. Independent INFO and USB
must still prove Running/active output and final released inactivity.

## Resource and timing acceptance

Keep heap reserve at least 32,768 bytes, largest successful request at most the
reused R1 demonstrated 18,364 bytes, both 16 KiB stacks with valid 4 KiB MSPLIM
reserves, no unexpected allocator/TLS failure, fault/reset, DMA error, starvation
or unpaired refill. Report new high-water observations and both-core stack use.

At 138 MHz the full 16,384-word block lasts 3,799,188.406 ns; the 75% budget is
2,849,391 ns. Compute each finite job's exact sample/block count, short predecessor
words and deadline. Require exact per-job DMA, alarm, tail, paired-refill and
successor deltas. The instrumentation retains the worst remaining/total ratio
across a boot: carry that observation's actual predecessor length and do not
relabel an earlier worst sample as the current job's short interval. Every
observed predecessor must retain at least 25%. Never add overlapping maxima.

Require unique launch epochs, ARM UTC mapping within measured uncertainty,
successful guarded completion and consistent post-enable delay telemetry. The
firmware cancels only when unable to launch within the requested UTC second.
Post-enable observation is diagnostic, not an electrical-edge measurement or an
independent cancellation threshold. All waveform durations remain unchanged.

## Fixture and restoration

Existing explicit USB, flashing, finite RF and bounded R2 fixture authorization
applies to this continuation. Use SSH outside the sandbox. A is USB
`0BF4B4AEC9FFB344`, WTP `fd6127d11d6aca42a9905fa3fb1bf1d5`. B remains read-only,
USB `CDDBF8767C506C07`, WTP `29f20b7342051ef947aa56cb9d4fab42`.
The confirmed GP2 path remains 50 ohms, 60 dB attenuation per input, unfiltered,
through the combiner to SDR; preserve GPSDO settings and all RF wiring.

Prepare and review the complete remaining packet before hardware setup. Use a
fresh private root and existing guarded lifecycle. Carry **30/32 configuration
writes and six historical heap probes** forward. Setup/restoration consume two
writes, ending at 32/32; do not reset or expand the counter. R5/future setup budget
must be reconciled separately before further writes. Device work is bounded to
45 minutes plus ten minutes restoration; host work to 70 minutes plus ten minutes
cleanup. Expected two measurement intervals total twelve minutes, plus setup
and restoration. Arm independent cleanup before mutation and never extend it.

Preserve Ethernet, wlan1, installed WsprryPi and permanent time.local, chrony,
GPS/PPS and Avahi. Use authorized wlan0 AP/wlan2 client, temporary recovery-timer
pause and chrony ACL with native time.local resolution. Read the maintenance
record and verify stratum 1/PPS NTP before flashing. Restore original A image
and configuration only after authoritative inactive/unowned admission; unknown
output or faults block automatic device reset. Host cleanup remains independent.
Verify both boards and permanent services after restoration.

## Review and report

Audit each packet before dependent RF. Test exact finite admission, production
identity binding, source-derived job bytes, one-owner USB state transitions,
renewals, failed-workload inhibition, raw-wire evidence, timing and scope mutation
rejection. Review again after correcting findings. Preserve historical auditors
and evidence. Commit only scoped source/helpers/tests/docs, not firmware,
credentials, private INIs or raw captures. Update review, results, roadmap and
companion evidence; commit/push each changed repository and verify parity/clean
state. Report actual completed jobs, family count, exact clock/image, findings,
validation, restoration, counts and remaining gates. R2 closure would make
Phase 11.5 2/6; R3–R6 remain separate and the accepted configuration list remains
empty. Phase 11.6 and Phase 13 retain their established RF/clock scope.
