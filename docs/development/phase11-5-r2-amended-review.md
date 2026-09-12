# Amended R2 Tone execution and review

**Three of seven R2 jobs completed; the three-Tone gate passed. R2 remains open.**
R1 closes 5/5 assertions on clean firmware
`049cc929143bdec6ec32817f6df0c73a9637cdf5`; Phase 11.5 remains **1/6 families**
with no accepted configuration. QRSS, FSKCW, DFCW, WSPR and the actual
production-owned/USB-reference submission paths did not run. Their packet was
not prepared within this bounded device interval. This is an incomplete R2
family, not a failed Tone gate or full Phase 11.5 acceptance.

The [execution plan](phase11-5-r2-amended-execution.md),
[build identities](phase11-5-r2-amended-builds.json),
[R1 parent packet](phase11-5-r2-amended-r1-packet.json),
[Tone packet](phase11-5-r2-amended-tone-packet.json) and
[result](phase11-5-r2-amended-result.json) retain exact inputs and outcomes.
The previous e20ae8b MISSED_START attempt remains in its original
[review](phase11-5-r2-review.md); it was not retried or relabeled.

## Scope and measured result

Pico A USB `0BF4B4AEC9FFB344`, WTP
`fd6127d11d6aca42a9905fa3fb1bf1d5`, ran physical 138 MHz, divider 1, RAM renderer,
listener enabled. Its physical boot was `8c5ce0d8c987875856c9b24f1a5fd50e`.
The confirmed GP2 path remained 50 ohms, 60 dB per input, unfiltered, through the
combiner to the SDR. GPSDO settings and Pico B were unchanged. No independent
RF decode, spectral acceptance or SDR calibration was performed.

All six R1 intervals passed, as did the 18,364-byte success → intentional
218,285-byte NULL → 18,364-byte success sequence. Matched quiet heap changed
by **+8 bytes**. Four clean linked layouts were checked; inhibited 150 MHz was
regression evidence and listener-off builds were layout evidence only.

Three sequential ten-second, 135.5 kHz browser-owned Tone jobs completed under
N300/USB360. Raw USB and browser evidence verified Loaded, Armed, Running,
Complete and released/inactive state for each job. The distinct launch epochs
were 1, 2 and 3, with post-enable delays **15, 8 and 8 microseconds**. Those are
software observations, not independently measured electrical-edge delays.

Each job produced 2,634 DMA IRQs, 2,632 running successor links and paired
refills, one launch alarm and one zero-tail IRQ. There were no observed DMA
errors, invalid reserves, unpaired refills, starvation, unexpected allocation
or TLS failures, guard faults or unexplained resets.

| Measurement | Observed | Requirement/context |
| --- | ---: | --- |
| Peak allocated / heap capacity | 136,060 / 218,284 bytes | 82,224-byte reserve; minimum 32,768 |
| Largest successful allocation | 18,364 bytes | Within the demonstrated R1 request size |
| Core 0 / Core 1 stack high-water | 8,248 / 5,616 bytes | Each 16 KiB, valid 4 KiB MSPLIM reserve |
| Full predecessor remaining | 7,515 / 16,384 words | 45.87%; minimum 25% |
| Short predecessor remaining | 1,938 / 2,312 words | 83.82%; minimum 25% |
| Maximum IRQ entry-to-refill-ready | 2,051,000 ns | 2,849,391 ns full-block budget |
| Maximum DMA IRQ / worker service gap | 141,000 / 2,119,000 ns | Separate observations; do not add overlapping maxima |
| Production STATUS offers in N300 | 317 | At least 298 |
| Maximum production STATUS start gap | 1.914 s | At most 2 s |
| Maximum native TLS write-to-response | 1.797 s | At most 5 s; excludes scheduler queue time |
| Browser page actions / GETs | 8 / 14 | Exact normal profile, including six refreshes |

The 138 MHz full block is 3,799,188.406 ns; the 2,312-word short interval is
536,115.942 ns. Remaining-word observations include time consumed before IRQ
entry. IRQ-entry-to-ready alone does not. The 209,000 ns maximum alarm callback
duration remains diagnostic; it is not the launch delay or a cancellation limit.

## Restoration and evidence

A returned to inhibited `802c91a7b86e-dirty`, boot
`8aadfedf02a066b47cb0ffb3c4068695`. B remained inhibited `dbf1d86f0885-dirty`,
boot `feffcd075ab6cb0b74e7e0c2fde6c87f`. Both were Empty, inactive and unowned;
their original configurations matched. Cumulative counts are **30/32
configuration writes and six heap probes**. R2 itself performed no heap probes.

Host networking, recovery timer, temporary chrony ACL and fixture publication
were restored. Permanent time.local, GPS/PPS, chrony, Avahi, Ethernet and wlan1
were verified; chrony remained stratum 1/PPS. Installed WsprryPi PID 1957 and
its executable were preserved. The actual tested production executable remained
source `6f65d5c7d202569102459ab68d7c9ea079b96f35`, SHA-256
`122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`.
It observed this packet; it did not own its jobs.

Private evidence is retained at `/home/pi/phase11-5-r2-amended-049cc92` and
locally under `build/phase11-5-closure/r2-amended-evidence/`. Filtered archive
SHA-256 is `e32cab6667ed39855e3d0268f7a1d497c57d531725e3621f3756cc8ba23bfc87`.
Credentials, firmware and raw captures are excluded from Git.

## Adversarial review and follow-up

Pre-RF review corrected two tooling defects. The new-candidate audit now treats
post-enable timestamp delay as telemetry while relying on the pinned firmware's
guarded execution window. It still rejects inconsistent delay/timestamp values.
The actor now waits for a fresh completed-launch INFO snapshot before RELEASE,
so a valid USB Complete response cannot race away the counter evidence needed
by the audit. Both unexecuted pre-review packet versions remain preserved.

Post-run review corrected the future coordinator's provisional status from
FAILED to RUNNING, with FAILED written only on an actual exception. The frozen
executed helper is preserved with its original hash. New deterministic checks
verify running/success/failure disposition and a single gate invocation without
retry. This reporting repair changes no firmware and requires no R1 replay.

The completed raw evidence passed independent offline R1 and R2 audits. All nine
mutations of source identity, quiet results, missing intervals, restoration,
counts, image identity, duration and actor exit were rejected. An unmodified
copy passed first; intact evidence passed again afterward. Twelve mutations of
the earlier failed-run evidence also remained rejected. The final review found
no further actionable defect in the completed packet; the unexecuted R2 paths
remain explicit acceptance gaps.

Validation: 129 local Phase 11.5 tests passed; the one private amended-evidence
test ran on wspr5 and passed its nine mutations and repeated intact audits.
All 11 Pi load-helper tests passed. Four clean RP2350 targets linked with SDK
2.3.1 and passed the linked heap-hook/MSPLIM checks and applicable RAM-renderer
checks. CMake's forced picotool fetch initially failed DNS; UF2 conversion then
used the already cached tool at the repository's pinned revision, with no tool
download. No firmware source changed during this execution turn.

The full R1 repeat was broader than the user's requirement to repeat affected
checks. The [plan](phase11-5-plan.md) now requires an assertion-level impact list
before retesting. Reuse unaffected evidence and the existing frozen image for
helper/documentation fixes. A firmware revision alone is not a reason to rerun
every earlier family. Preserve actual source/clock provenance when carrying an
assertion forward.

Next work is the prepared remaining-mode/submission packet on this unchanged
candidate, with its operation budget reconciled before new setup. Physical
132/150 MHz remain untested. A newly selected 11.6 clock needs affected 11.5
checks; broad band/mode/clock, filter and spectral qualification remains Phase 13.
Operator documentation and UI are unchanged; no operational RF limits or release
configuration are claimed.
