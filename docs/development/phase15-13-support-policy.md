# P15.13 clock, build and receiver support policy

Source review applies to initial current `devel`
`165303458e49feaac1de54c8344058f56578d533`. The
[results](phase15-13-results.md) distinguish new RF evidence from historical
qualification. The [plan](phase15-13-plan.md) freezes this follow-up's scope.

`WSPRRY_PICO_RF_SAMPLE_RATE_HZ` selects one image clock. StandaloneRF applies it
once at boot using `set_sys_clock_khz`; the PIO adapter requires that clock.
There is no automatic per-band selection or runtime clock-switch operation.
Changing the clock requires a separately built image and reflash. Never change
the clock inside an active job.

| Image sample clock | Native direct engine range, inclusive | 4 m at 70.0925 MHz | Native 2 m |
| --- | --- | --- | --- |
| 132 MHz | 100,000–65,999,999 Hz | Unavailable | Unavailable |
| **138 MHz, normal** | **100,000–68,999,999 Hz** | **Unavailable** | **Unavailable** |
| 150 MHz | 100,000–74,999,999 Hz | Representable; Unqualified | Unavailable |

These are arithmetic/admission limits, not band qualification. Every requested
and adjusted RF-on state must satisfy the active image's limits and application
frequency policy. WTP CAPS and the browser API's `wtp` capabilities come from
that same `ServiceConfig`; the one policy wrapper admits all job sources.
The UI reads those capabilities and submits complete jobs through that authority.
Its frequency entry remains free text; authoritative LOAD admission enforces the
active limits. It does not implement clock selection or promise that an admitted
frequency is measured/qualified.
The `pico2-w` preset and ordinary firmware build select the normal RF-capable
`WsprryPico` application at 138 MHz. Explicit `WsprryPico-Inhibited` selects
the RF-free simulator; `WsprryPico-StandaloneRF` remains compatible. This target
selection change does not refresh historical RF qualification.

The default-off experimental `allow_unqualified_frequency` flag is required
for the 8 m and 5 m correlation envelopes. Keep it explicit even if the exact
representative P15.13 points pass: one point does not qualify 40–45 MHz or
54.000001–68 MHz as complete intervals. These tests need no
`allow_non_amateur_frequency` permission. Neither permission grants national
legal availability or extends native synthesis limits.

The accepted current-image points are **40.001 MHz (8 m)** and **60.001 MHz
(5 m)** on Pico A. All five modes pass within the [result matrix](phase15-13-result-matrix.json).
WSPR acceptance includes one fixed receiver-audio translation of the original
IQ: **+125 Hz for 8 m**, **+200 Hz for 5 m**. The physical SDR center/gain did not
change for these offline comparisons. Nominal tuning passed 1/3 and 0/3 of those
same accepted sequences; the nominal failures remain. These are demonstrated
reception conditions, not universal correction values for all receivers/boards.

The accepted 5 m sequence follows a verified inactive reboot to clear volatile
history and uses ordinary complete WTP jobs with exact realized NCO frequencies
and adjacent equal-frequency events merged (127 events, same 162-symbol sampled
waveform). It is not evidence that every 162-event request admits under retained
history. Quiet memory preflight preserves the actual firmware reserves; the
original refusal/reset and partial FSKCW observer abort remain in the results.
Short jobs need no renewal when their complete preparation/lead/duration fits
the existing 60-second claim. A missing reply does not establish output silence;
inspect actual identity/status and restore known inactivity before new work.

Historical Phase 14 6 m WSPR includes separately reviewed **Pico A / 138 MHz /
receiver-only +125 Hz retuning**. That is an identified receiver condition;
it neither switches the Pico clock nor establishes fresh current-firmware 6 m
acceptance. Historical 4 m becomes directly representable with a **150 MHz
build/reflash**, while its all-mode release status remains **Unqualified** under
the required reliable-WSPR gate. Historical native 2 m is **Unavailable** at
all three clocks; manually mapped harmonic pilots did not implement a native
route and remain failed evidence. P15.13 adds no 6 m, 4 m or 2 m RF windows.

For P15.14, document the exact measured points, board/image applicability,
experimental flag, any receiver adjustment actually demonstrated in the new
results, and these build boundaries. Do not present older clock comparisons as
automatic firmware behavior. The unfiltered GP2 conducted path qualifies no
LPF, antenna operation, calibrated transmitter watts or absolute RF precision.
