# P15.13 finite 8 m / 5 m qualification plan

Frozen before acquisition on 2026-10-17. The initial clean local `devel` and
fresh remote `devel` tip are `165303458e49feaac1de54c8344058f56578d533`.
Firmware is built in an isolated detached checkout of that revision. Changes
to Python qualification tools are separately manifested; they are not firmware
repairs. No other repository is changed. Phase 14 and P15.1–P15.12 closures stand.

The normal uninhibited `WsprryPico-StandaloneRF` image uses GP2, the saved pin
and consumer profile authority, 138 MHz/divider 1 and the ordinary GP14 default.
No acceptance fixture or clock switching is enabled. Both the standard inhibited
target and the explicit StandaloneRF target are rebuilt with SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, Arm GCC 15.3.1 and picotool source
`6f6458d792b93685a11423b244a585eaa99eafcf`. Complete source, helper, command,
cache and artifact manifests are private under `build/phase15-13-20261017/`.

## Frozen workload and budget

| Band | Engineering base (Hz) | Tone | WSPR | QRSS | FSKCW | DFCW | Windows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 m | 40,001,000 | 1 | 3 | 1 | 1 | 1 | 7 |
| 5 m | 60,001,000 | 1 | 3 | 1 | 1 | 1 | 7 |

These exact conducted points are not national operating channels or on-air
permission. Every state is within the 138 MHz direct engine and experimental
amateur correlation envelopes. Enable only `allow_unqualified_frequency` on A;
preserve `allow_non_amateur_frequency=false` and restore the original flag.
Do not promote the broad 40–45 MHz or 54–68 MHz envelopes from these two points.

Tone lasts 5 seconds. WSPR uses the existing complete 162-symbol Type 1 fixture,
expected external decode **AA0NT EM18 37**, 110.592 seconds per frame. Three
requested UTC frame starts are exactly 120 seconds apart in one continuous receiver capture
per band. No Type 2/3 or message-generation testing is selected.

The existing keyed message is **ETE**, with three-second dots. QRSS/FSKCW dash
marks last nine seconds and inter-character spaces last nine seconds. QRSS
spaces are silent; FSKCW spaces use base minus 5 Hz. DFCW uses three-second
dot-high/dash-low marks, 5 Hz separation and three-second silent character gaps.
All keyed jobs have one second of silence at each end. Total job durations are
35 s for QRSS/FSKCW and 17 s for DFCW. Each complete job is loaded before ARM.

The source plan is `src/phase15_13/plan.py`; its immutable JSON is retained before
RF. It defines exactly **14 nominal windows**, with **zero diagnostic windows
preauthorized by this plan**. Any diagnostic is separately enumerated against
a preserved failure and hypothesis. Pico B is inactive unless a failure on A
leaves a plausible board/branch explanation after offline review.

Ten receiver groups total **1,124 s / 2,248,000,000 bytes** of CF32 IQ at
250 ksample/s. WSPR groups each last 370 s; other groups include 25 s beyond
their complete job. Retain at least five seconds quiet between groups and at
least 2 GiB free reserve beyond each capture. Lossless WSPR child slices add
1,480,000,000 bytes while the two full parents remain. Allow roughly 21–25
minutes acquisition including setup, hashing and quiet intervals, plus offline
analysis; elapsed time does not grant RF windows. No blanket clock campaign.

## Setup, evidence and acceptance

Bench host wspr5; the operator also authorizes wspr1/wspr2/wspr4. Pico A serial
`0BF4B4AEC9FFB344`, WTP ID `fd6127d11d6aca42a9905fa3fb1bf1d5` is primary.
B serial `CDDBF8767C506C07`, WTP ID `29f20b7342051ef947aa56cb9d4fab42` is
diagnostic only. RSP1B serial `2404058C60`, GPSDO `0673ED0FA107`.
Each source passes through its own 20 dB attenuator, then the combiner and
another 40 dB into the SDR. No antenna and specifically no LPF.

Take exclusive board/receiver locks; inspect and quiesce competing transmitter
service activity. Verify disabled schedules, inactive/unowned output, identity,
fresh boot/source/engine/clock and boot-applied GP2 before RF. Read GPSDO lock,
enables, levels, frequencies and PPS routing before enabling measurement output
1; keep output 2 and unrelated settings unchanged and restore all changed state.

Receiver: CF32, 250 ksample/s, 200 kHz bandwidth, 20 dB gain, channel 0, AGC and
bias-T off; center is base minus 25 kHz and simultaneous GPSDO is base minus
40 kHz. This comparison cancels common tuning error on a nominal sample axis;
it does not discipline the Pico, calibrate SDR sample time or qualify absolute
UTC. Report indicated error, reference-compared error and measurement limits.

Require complete valid capture, zero overflow/clipping, exact identities/hashes,
local job completion, unchanged ownership and final silence. Tone requires
continuity, expected duration and established >=10 dB contrast. WSPR requires
three original consecutive valid frames, each externally decoded by wsprd with
retained stdout/stderr/exit status, exact command, audio/capture hashes and
lossless sample-range binding to its full parent. Human-copy modes require
ordered readable marks/spaces, 20 ms timing tolerance, proportions, continuous
marks, >=10 dB contrast and distinguishable states (at least half the requested
5 Hz separation). Preserve drift/coherence screens as diagnostics.

Inspect allocator, authority reserve, stack guards, DMA/refill and lifecycle
counters during these same windows. Analyze available in-span spectra only.
No added endurance, harmonic survey, calibrated-power or filtered-emissions claim.
Continue other planned cells after a valid RF failure if control and capture
integrity permit. Preserve failed originals; do not retry until three pass.

Review source and numeric limits for historical 6 m receiver +125 Hz retuning,
4 m at 150 MHz and native 2 m unavailability without transmitting on those
bands. No clock change inside a job. Record precise current support policy,
fresh self-review or independent review, all affected deterministic checks,
actual final firmware/settings and P15.14 documentation handoff before closure.

## Recorded execution amendments

The frozen nominal matrix above remains the original plan. The
[execution record](phase15-13-results.md) preserves its failures and later
finite dispositions: quiet memory preflight, one inactive reboot, three
waveform-equivalent compact 5 m WSPR diagnostic windows and one FSKCW diagnostic
without unnecessary short-job renewal. Actual accounting is 12 nominal RF
windows plus four diagnostics, 16 total; two original WSPR slots were not
transmitted. Exact diagnostic plans were saved before RF. No original invalid
case is promoted, and no further RF retry followed these four windows.
