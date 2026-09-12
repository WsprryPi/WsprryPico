# Phase 11.5 R2 execution and launch-policy review

**R2 remains open: 0/7 jobs completed; one Tone missed; six jobs did not run.**
Phase 11.5 remains **1/6 families closed**, with no accepted configuration.
The subsequently requested UTC-second launch policy is implemented and
software-tested; it has not been flashed or physically accepted.

## Executed attempt

The user confirmed unchanged wiring and explicitly authorized the bounded R2
fixture. Pico A (`0BF4B4AEC9FFB344`) ran clean source
`e20ae8bea2d5237af017dbd5f73bfe9332ce144e`, physical 138 MHz, divider 1,
RAM renderer, listener enabled. Its UF2 was
`7a7306b8ad9dab694903434b86aec18e249c79dad0443645cd04ca857e9d4a04`.
Pico B remained read-only. Each Pico had a 50-ohm attenuator load and 60 dB
conducted attenuation through the unfiltered combiner/SDR path; GPSDO settings
were unchanged. The production executable remained the preserved `6f65d5c`
binary; its full SHA and source identity are in the executed packet.

The [original prepared packet](phase11-5-r2-tone-prepared-packet.json) remains
historical. The [executed packet](phase11-5-r2-tone-executed-packet.json) SHA-256 is
`e0c01e66189f2d295a38d6e1a294b32e1c2c5e78c56088a1371db9038d48b2e2`.
Its first subpacket contained three browser-owned ten-second 135.5 kHz Tones
under normal N300 browser/production load and USB360 observation. It could not
by itself close the remaining modes or production/USB submission paths.

HELLO, CLAIM, LOAD and ARM returned success for the first job,
`ba324fb4e892e8dbf57200aee89fe7ff`, on boot
`0da88dc334efa649cbc097ed6dd48c63`. Before a successful launch, Console reported
`missed`; independent WTP reconciliation confirmed `MISSED_START`, output
inactive and no owner. The observer failed its expected lifecycle check, and
the actor stopped. There was no retry or dependent second job. Normal host load
finished its bounded interval; that is not an accepted RF contention interval.

Recorded launch epoch, launch timestamp, DMA and tail counters were zero.
One alarm callback ran; its maximum duration was **293,000 ns = 293 microseconds
= 0.000293 seconds**. That is callback execution time, **not measured launch
lateness**. No output edge or decoder result was measured. The old exact-instant
guard is shared by all modes, but only Tone failed in this attempt. The logs do
not distinguish clock-guard cost, IRQ entry delay and the hardware launch guard
well enough to establish which exact check rejected it.

The historical source required a launch at the selected microsecond. Initial
R2 audit thresholds of 10 microseconds for post-enable observation and
250 microseconds for callback duration lacked an operational justification;
they were withdrawn after user review. Their removal does not relabel this
cancelled job as completed. Raw evidence and the frozen running helpers remain
unaltered. The final auditor reports callback duration diagnostically.

## Restoration and evidence review

Fresh serial-specific reconciliation established the exact missed job, boot,
inactive output, absent owner, healthy stack guards and no DMA/retained fault.
The narrowly guarded `phase11_5_release_missed.py` used only
HELLO/STATUS/CLAIM/RELEASE/STATUS to retire that current Missed slot. The identical
MISSED_START terminal record remained retained. It did not run RF, reset the
board, clear the journal or erase the failed result. This permitted the already
armed original-image/config restoration to complete normally.

A returned to inhibited `802c91a7b86e-dirty`, boot
`f2b9d8477c33c856884485e87394e8fe`. B remained `dbf1d86f0885-dirty`, boot
`feffcd075ab6cb0b74e7e0c2fde6c87f`. Both were authoritatively Empty, inactive
and unowned, with original configurations matching. The original-image boot,
not the earlier configuration-restore observation, proves final A firmware.
Cumulative administration counts are **28/32 configuration writes**, zero
Wi-Fi off/on probes and three historical R1 heap probes.

Host cleanup completed without failures. Ethernet/wlan1 and installed WsprryPi
PID 1957 were preserved; temporary AP/client, chrony ACL, time.local publication
and recovery-timer changes were restored. Permanent time.local, chrony/GPS-PPS,
Avahi, LAN NTP and wspr5.local checks matched the baseline. A derived summary's
`installed_pid:null` was a lookup error; the raw host-restored record explicitly
contains PID 1957. No loss of that process is inferred from the summary field.

Private evidence remains at `/home/pi/phase11-5-r2-tone-20260912` and locally
under `build/phase11-5-closure/r2-evidence/`. Filtered archive SHA-256:
`f90efb97baef7101c1483d605790309ffe532f83c2c21c9ecee3f129a0dfddcc`.
Credentials, firmware and captures are not committed. The offline failure
auditor reconstructs Console/WTP bytes, checks browser request/reply correlation,
retirement operations and retained record, final firmware/configuration and host
restoration. It classifies intact evidence as a verified miss, never acceptance.
All **12 raw-evidence mutations** were rejected, followed by another intact pass.

## Requested launch-policy repair

The user's instruction is: “We should only CANCEL if we are unable to get within
the expected second, and use telemetry for the delay otherwise.” The amended
[WTP contract](../protocol/WTP.md) interprets this as the UTC second containing
the requested start. For a request at `12:00:00.750`, starting before
`12:00:01.000` is permitted; starting at that boundary is missed. This is not a
rolling one-second allowance and not a 250-millisecond universal threshold.

The shared service, stream engine and PIO driver now retain an exclusive latest
start. They aim for the target, round fractional hardware ticks upward, and
accept later launches within that window while preserving clock-state,
uncertainty, holdover and leap checks. Missing the window keeps output inhibited
and records Missed/MISSED_START. No automatic job retry is introduced.

An accepted late launch anchors the full event/sample timeline and completion
deadline to that launch. Symbol durations and generated samples do not change.
The inhibited simulator follows the same policy and reports its simulated anchor.
Console INFO adds `launch_delay_ns` beside target/observed timestamps and epoch.
It is the post-enable observation minus the quantized target; epoch zero means
no launch. The unrounded mapping remains in the ARM response. A separate sample
adjacent to enabling PIO anchors execution, so later diagnostic bookkeeping
cannot retroactively reject an otherwise permitted start. Neither sample is
independent electrical-edge metrology.

WTP/1 wire fields and schema are unchanged; its documented timing semantics
are revised. Existing old firmware retains its old behavior and cannot be
inferred to implement this rule just because it reports WTP/1. The new build is
not a release or accepted target configuration. R1 memory/layout and timing
results are still tied to e20ae8b: the new report/arm records and stream state
require affected R1 checks on a clean, identified new build.

## Adversarial assessments and validation

The initial preparation review fixed packet/baseline identity binding, repeated
observer request IDs, exact short-predecessor length, dependent actor shutdown,
and carrying historical management counts without resetting them. The normal
browser mutation lane preserves eight scheduled actions/fourteen GETs and reserves
five transaction seconds plus one margin second before the next action.

The policy review found and fixed completion being anchored to the old requested
start, early timer rounding, a late alarm being rejected by foreground polling,
and overflow/leap exclusions that needed to cover the entire permitted launch
window plus the full waveform. A separate pre-enable execution sample prevents
post-enable telemetry cost from deciding whether the window was met. Existing
clock-loss, uncertainty, leap, abort, reset, DMA/starvation and tail guards remain.

Final assessment exercised zero delay, a 293-microsecond delay, the last tested
microsecond before a fractional UTC-second cutoff, the exact cutoff, a final
nanosecond with no representable hardware tick, delayed foreground handling,
upward rounding and full-duration completion. No further actionable source or
auditor defect was found in this review. Physical behavior remains unvalidated.

- Phase 11.5 Python discovery with private evidence enabled: **123 tests passed**.
- Pi normal-load helper: **11 tests passed**.
- Native CTest: **59 groups passed**, including TLS via a local loopback test
  outside the sandbox. Its initial sandbox bind failure was environmental;
  no live radio or remote service was involved in that test.
- WTP contract checks: 23 schema, 7 raw JSON, 1 framing and 8 transition cases.
- RP2350 SDK 2.3.1 cross-links: standard inhibited `WsprryPico` and physical
  `WsprryPico-StandaloneRF`, 138 MHz/RAM/listener on. Existing linked heap-hook,
  stack-guard and renderer checks passed. These dirty-development ELFs were not
  flashed; no UF2 was generated. Clean firmware identity and target checks remain.
- Final formatting and whitespace checks passed. Native linking retained the
  existing macOS warnings about mock common-section alignment and duplicate
  core-library linkage; tests passed. RP2350 cross-link checks passed separately.

## Remaining work and Documentation Impact

Freeze a clean new launch-policy candidate, repeat affected R1 checks, then run
a new bounded Tone gate before remaining QRSS/FSKCW/DFCW/WSPR and actual
production/browser/USB submission evidence. Preserve the 28/32 count and reserve
restoration and R5 capacity. Do not replay the spent packet or substitute the
new firmware into its frozen identities. R3–R6 remain open; physical 132/150 MHz
remain untested in 11.5. Phase 11.6 and Phase 13 scope is unchanged.

Updated the execution prompt, prepared/executed packet records, result, ledger,
development pointer, WTP timing contract and Pi companion review. Operator UI,
WsprryPi production binary and separate operator documentation remain unchanged.
The new firmware must be physically accepted before publishing operational
backend limits in Wsprry_Pi_Docs. No UI source or visual review was involved.
