# Phase 14 PIO/DMA qualification and release plan

Status: ACTIVE. Authorized 2026-10-08. This plan is frozen before new RF
measurements. Results and any explicit method amendments are recorded in
[phase14-results.md](phase14-results.md); historical failures remain unchanged.
P13.1 is complete, P13.2 Si5351 and GP14 production enablement remain deferred.

## Source review and intended scope

The starting checkout is devel at `4b42a5d624cc68aa318b6e8d69c84f9460dc1bb4`.
The untracked `tests/hardware/si5351-i2c/` is unrelated and preserved.
Reviewed areas: JobService validation/leases/replay/terminal retention, portable
NCO/sample planning, two-buffer PIO/DMA and zero-tail stop, UTC reprojection,
core-1 execution, standalone journals/watermark, transport/profile admission,
network/browser concurrency, allocation limits and Phase 12/13 launch changes.

Complete immutable jobs reach one JobService. Local RP2350 execution has no
per-symbol transport dependence. A disconnected owner or expired running lease
cannot establish RF inactivity. Failed disable retains failure/unknown output.
Absolute event boundaries are rounded to samples rather than accumulated.
The driver forces GPIO low on stop and drains a zero tail on natural completion.
P13.1 adds a checked indicator launch handshake, which can delay launch within
the admitted UTC second. Consumer profiles deliberately gate USB WTP and use
Plain LAN; engineering profiles retain USB/mTLS. The existing profile is recorded,
not silently replaced to make an unavailable transport pass.

Direct synthesis supports 100 kHz through sample-clock/2 minus 1 Hz, at most
four distinct NCO increments, 512 events and 3,600 seconds per job. Compare
132, 138 and 150 MHz/divider 1/RAM renderer on GP2. The 15 candidate band points
are inherited from the Phase 11.6 plan (2200 m through 2 m). At 132/138 MHz,
4 m and 2 m are unsupported. At 150 MHz, 4 m is a synthesis candidate and
2 m remains unsupported. Representability alone is not release support.
Modes are Tone, WSPR, QRSS, FSKCW and DFCW. DFCW retains dot-high/dash-low.

Positive correction ppb means a fast oscillator and reduces the NCO increment.
It does not calibrate the RP2350 timer or change sample-count duration. Bench
correction is volatile; ordinary standalone firmware currently has no operator
correction setting. Accepted nHz describes nominal NCO quantization, not a
measured calibrated carrier. These limitations must remain in the disposition.

## Bench and identity binding

Each Pico GP2 and the GPSDO passes through its own 20 dB attenuator into the
combiner. Combined signals pass through 40 dB attenuation into the SDR. There
is no antenna. This established setup is accepted, with 60 dB nominal source
path loss; no further operator setup confirmation is required. No assembled
output filter, buffer, matching or coupling network is identified by this
setup. Raw GPIO/attenuator/combiner results cannot qualify an output filter.
Loading, calibrated insertion loss and post-filter emission performance remain
unqualified until actual hardware measurements establish them.

Automatically bind Pico A `0BF4B4AEC9FFB344` / device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, B `CDDBF8767C506C07` / device
`29f20b7342051ef947aa56cb9d4fab42`, RSP1B `2404058C60` and GPSDO
`0673ED0FA107`. Both boards are USB-connected to wspr5. Capture settings start
at CF32, 250 ksps, 200 kHz, gain 20, AGC/bias off, center carrier minus 25 kHz.
Use the retained Harness exact-count capture helper, existing phase-fit/keyed
analyzers and independent WSJT-X wsprd. Capture helper and decoder hashes,
firmware source/UF2 hash, boot, clock, job/digest, settings and actual capture
count/hash are mandatory bindings. Logs/captures/configuration stay private.

Read GPSDO frequency, enabled outputs, levels, lock and PPS before changing its
measurement output. Preserve unrelated reference/PPS settings and restore only
measurement settings actually changed. Its RF reference does not discipline
the Pico or SDR. A simultaneously recorded reference estimates tuning offset;
it does not by itself establish sampling-time scale. Report this separately.

## Methods and criteria established before acquisition

| Assertion | Method and acceptance source |
| --- | --- |
| Job/control | WTP/1 validation, identity/boot continuity, exact accepted adjustments, one finite local job; same-job terminal Complete and output false; RELEASE/inactive successor when owned. |
| Synthesis | Source range/quantization, all requested states distinct; reject unsupported LOAD without ARM; no fifth distinct frequency. |
| Screening carrier | Complete on/off capture, >=10 dB contrast, no clipping/overflow; existing analysis's 100 Hz acquisition window is a screening locator, not a calibrated carrier specification. |
| Operational keyed RF | Existing analyzer: 20 ms relative envelope, >=10 dB contrast, phase residual <=0.15 rad; two-state separation/residual <=0.2 Hz; frequency-transition fit <=20 ms and <=0.15 Hz. This retains a consistent screen; ambiguity is reported, not relabeled. |
| Operational WSPR | Complete 162-symbol, 110.592 s frame and quiet before/after; 375/256 Hz spacing, existing <=0.05 Hz separation / <=0.1 Hz residual / <=10 ms transition screens; independent exact-message decode. A decode alone cannot satisfy the other assertions. |
| Release timing/frequency | Report error and uncertainty independently. WTP permits launch within the requested UTC second, subject to admitted clock uncertainty. No inferred microsecond UTC claim. Physical symbol/frame precision and calibrated absolute carrier remain unqualified if receiver/reference uncertainty is not bounded. Historical suggested 10 us/100 us/0.1 Hz budgets are not promoted into new contracts. |
| Spectra/filter | Record close-in sidebands, in-window spurs, separately tuned harmonics/images through at least fifth harmonic where receiver coverage permits; exact coverage and receiver attribution. Retain operator's better-than-WsprryPi close-in benchmark. No all-band or filtered-output acceptance without applicable measurements of the actual output network. |
| Resources | No new unexpected allocator/TLS/DMA/stack faults; refill-to-ready below actual full-buffer period, no exhausted predecessor; >=32 KiB preserved authority reserve. Compare equivalent idle windows for growth, with the established 1,024-byte return screen and retained raw samples. |
| Endurance | Finite 60-minute complete jobs, maximum 512-event and 32-character workloads, repeated jobs, transport recovery, realistic Wi-Fi/browser load, natural completion/abort/cancel; no output afterward. An eight-hour mixed soak is proposed for final release, distinct from the historical inhibited soak. |
| Reproducibility | Same pinned SDK 2.3.1, Arm GCC 15.3.1 and picotool commit; clean independent build directories; identical UF2 payload/artifact hashes or investigated differences. No generated firmware or secrets committed. |

Use short Tone screens across band/clock on both boards before expensive mode
acceptance. Start with Tone and complete WSPR at 80 m/138 MHz on both boards.
Then screen all representable band/clock candidates. For promising release
configurations require three complete WSPR frames and three keyed repetitions,
including disconnect/reconnect, plus both-board consistency. A rejected Tone
screen may exclude that configuration from expensive acceptance, with an explicit
failed/unresolved disposition for dependent modes rather than a false pass.

Retain raw phase/timing/spectral measurements even when a historical analyzer's
composite flag fails. Investigate receiver artifacts with retuning/gain/reference-
only controls; do not weaken frozen limits to obtain PASS. Preserve every failed
attempt and create new results after repairs. Capture failure is acquisition
failure, not a transmitter failure or successful measurement.

## Prior evidence and final applicability

Phase 11.5 closes six resource families only at 138 MHz/divider 1/GP2/RAM on
its identified firmware. Phase 11.6 accepts exactly 13 rows and no WSPR row.
Phase 11.7 reconciles that scope; earlier 80 m/2200 m independent WSPR decodes
are useful historical demonstrations. Phase 12/13 changed the running network,
allocator/layout and launch paths; current RF candidates require fresh affected
resource/launch measurements. Alternative clocks require their own load checks.
Existing LED/button functional evidence is reused; no new LED/polarity/button
campaign is a release prerequisite.

Stage completion is assertion-level, not a runner PASS label. The final review
challenges incomplete IQ, source/boot/job substitutions, nominal-vs-measured
frequency, reference uncertainty, matrix gaps, stale runtime applicability,
filtered-output claims and final cleanup. Finish each bounded batch, verify
actual RF inactivity and disabled schedules, retain useful RF firmware, close
owned connections/processes, and commit/push only intended Phase 14 files.
Phase 14 is complete only after all required qualification and release gates,
final review, commit/push and independently checked remote parity. An unresolved
physical output-network requirement must be reported as an open phase.
