# Standalone RF and separate-power validation

This September 6, 2026 campaign resumes the RF and separate-power checks deferred
in the [inhibited Wi-Fi campaign](standalone-physical-validation.md). The
[execution prompt](step9-rf-power-execution-prompt.md) defines its bounded scope.

## Exact target and artifacts

- Source: `c064e5b5e31b8df4f54c1ed51e97ee9093bbdaf5`, built clean on `devel`.
- Pico 2 W / RP2350 A2, board serial `0BF4B4AEC9FFB344`, WTP identity
  `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Explicit standalone RF image: 138 MHz PIO/DMA engine, GP2/GND through the
  operator-confirmed 60 dB conducted path to wspr5 RSP1B `2404058C60`.
- Local Type 1 WSPR message `AA0NT EM18 37`; nominal base 3,570,100 Hz,
  162 symbols, 110.592 seconds. Encoded power is not measured output power.
- Device Wi-Fi SNTP uses the previously selected `pool.ntp.org` IPv4 address
  `69.89.207.199`, with the existing 500 ms admission/launch uncertainty budget.
  Credentials remain private in ignored configuration and device flash.
- Receiver: CF32, 250,000 samples/s, 200 kHz bandwidth, 3,550,000 Hz center,
  20 dB gain, channel 0, AGC and bias tee disabled. Receiver axes are uncalibrated.
- Capture helper SHA-256:
  `b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03`.
- Both LBE-1421 reference outputs were verified disabled through the existing
  project-owned CLI before capture. The existing WsprryPi service was left alone.

| Image | SHA-256 |
| --- | --- |
| Standalone RF | `bd5c678ba5a296b5dee1c7aecc08e4db863ca76338ff8fc142e70ec96ae41d4d` |
| RF-inhibited recovery | `86c641c0db02f0a22d64207d30af8ec6d9db061d5e64c39313f3e2cfefe4fca4` |

## Campaign and observations

The RF image was first flashed with scheduling disabled. INFO verified the
expected image revision, healthy storage, synchronized device time and inactive
output. One-time provisioning then enabled a four-minute schedule with phase
120 seconds and expiry `2026-09-06T17:03:53Z`. Eligible starts were 16:50:01,
16:54:01, 16:58:01 and 17:02:01 UTC. No USB TIME SET, LOAD or ARM was used.

The 16:50:01 frame was observed running and then complete in boot
`91d9a418ff4e89feb76759e257e9fd28`, with its durable watermark retained,
29,111 DMA interrupts, maximum reported interrupt time 41 microseconds, no
engine/sink diagnostics, inactive terminal output and successful SNTP reacquisition.
This first frame was not captured and is not an independent decode pass.

The first receiver run, `step9-rf-baseline-1654`, retained a valid 135-second
capture with zero overflow/clipping and verified cleanup, but contained no burst.
The Pico's watermark and DMA counters did not advance. One SNTP rejection was
recorded between surrounding observations. Stale/invalid time can correctly
suppress admission, but the snapshots do not establish this skip's exact gate.
This attempt is retained as a failed baseline, not a decode pass or a proven
network diagnosis. No timing limit was relaxed and no missed slot was replayed.

With a fresh accepted time sample, `step9-rf-baseline-1658` captured one complete
110.592-second frame. WSJT-X `wsprd` independently decoded `AA0NT EM18 37`.
No USB job/time commands were sent, and the Console was closed before admission
and throughout the frame. The same boot then reported completion, inactive
output, healthy storage, watermark 16:58:01, 58,222 cumulative DMA interrupts,
no engine/sink diagnostics, and successful post-frame SNTP reacquisition.
This establishes recurrence after the earlier skipped slot.

The offline diagnostic measured 1.466406 Hz fitted tone spacing and maximum
transition error 1.3 ms relative to the receiver's sample clock. Maximum symbol
fit residual was 0.111766 Hz, exceeding the diagnostic 0.1 Hz limit. Therefore
this run is a complete-frame/decode pass, not a pass of all relative RF checks.
The retained frequency-fit behavior remains a qualification limitation.

After baseline success, one-time provisioning extended the finite expiry to
17:11:53 UTC, providing wall-power slots at 17:02:01, 17:06:01 and 17:10:01.
Saving this configuration suspended new admission until reboot. The operator
then physically transferred USB power from the Mac to a wall adapter, leaving
the conducted path unchanged. Mac USB inventory first recorded absence at
17:01:20.475 UTC; the operator confirmed wall power, recorded at 17:01:56.190 UTC.
All 321 inventory observations audited between 17:01:21 and 17:12:10 UTC
reported the Pico absent; the maximum observation gap was 2.054 seconds.
The operator confirmation and inventory samples establish the physical USB-host
boundary. They do not expose live diagnostics from the wall-powered boot.

All three wall-power occurrences produced complete 110.592-second bursts and
independent `AA0NT EM18 37` decodes. Thus a real power-only boot loaded the saved
configuration, acquired device time and repeatedly scheduled local RF. No USB
host, per-job network command, or WsprryPi scheduler supplied these jobs.
A read-only check at 17:07:09 UTC confirmed the existing wspr5 WsprryPi service
had `Operation.Transmit=false`; its journal showed no transmission requested.

## Capture and decode evidence

Each capture retained 33,750,000 CF32 samples (270,000,000 bytes) over 135 nominal
seconds. Device/settings identity, sample count, file size and SHA-256 agreed;
all overflow/clipping counts were zero and receiver cleanup was verified.

| Run | Functional result | Maximum symbol-fit residual |
| --- | --- | --- |
| `step9-rf-baseline-1654` | No burst; failed baseline | Not available |
| `step9-rf-baseline-1658` | Complete frame; decoded | 0.111766 Hz |
| `step9-wall-1702` | Complete frame; decoded without USB host | 0.145499 Hz |
| `step9-wall-1706` | Complete frame; decoded without USB host | 0.112551 Hz |
| `step9-wall-1710` | Complete frame; decoded without USB host | 0.106696 Hz |

Every received frame exceeds the existing 0.1 Hz symbol-fit diagnostic limit.
The 17:02 frame additionally reports ambiguous/missing transition 83 in the
relative diagnostic. These remain recorded RF diagnostic failures, consistent
with the separate [cold-frame qualification boundary](utc-rf-job-validation.md).
They are not reclassified as spectral or calibrated timing passes because the
message decoded.

| Run | Capture SHA-256 |
| --- | --- |
| `step9-rf-baseline-1654` | `bdb1a0f28706c68408f8553230231eeb8af3aac2feebc276bcf36a10fc0d7a2d` |
| `step9-rf-baseline-1658` | `73640339a340dd84c92c9635bc222c020ebb52b4e3643c43244fc22c6644e0fa` |
| `step9-wall-1702` | `af3428086d49464ffbe25dc2b3007587d9c92c5aedc3b66c07d7cbd094006dc5` |
| `step9-wall-1706` | `9de9a8764adff5f378f79f12684fce0c31309086843ffa11cbf0c28494864bc1` |
| `step9-wall-1710` | `bb407ec69e1d5d59855b5f225dcd1c5ff35c5e22a16b603ebaec3d8b56a64925` |

Independent decoder: installed WSJT-X `wsprd`, SHA-256
`8a5acb25fe8c7072f2157b03fadc1d21543f1ddf432f609fd6907f095dfba2a3`.
The expected message is checked against its output; expected symbols are not
supplied to the decoder. The capture-relative decode windows began at 11.842,
11.960, 12.108 and 11.898 seconds respectively for the four received frames.
Conversion uses the maintained Hann decimation to complex 1 kHz, 241-tap Hann
sinc interpolation to 12 kHz, real 1500 Hz audio, amplitude normalization and
trailing silence. No frequency/drift correction or edits within the selected
window are applied. All decoder matches, including weaker secondary matches,
remain in the logs. Synthetic WAV slot labels and SDR host timestamps do not
establish calibrated UTC onset.

Raw captures, receiver manifests, measurement/decoder reports and WAV hashes
remain under ignored `build/step9-physical-evidence/`. Image identities, sanitized
Console records, power-transfer confirmation, USB inventory samples and the
cross-artifact audit remain under `build/step9-rf-power/`. Credentials and private
configuration are excluded from maintained evidence.

## Final state and adversarial assessment

All finite receiver and USB-inventory observers terminated. Final wspr5 process
inspection found no capture/Soapy helper still running; the existing WsprryPi
service remained in place. The capture-helper hash was unchanged and both
reference outputs were again verified disabled.

After the operator confirmed reconnection, INFO observed a new normal boot
`a0b37711c912a014b6e488840b3a74ab`. Saved station, four-minute schedule and
17:11:53 expiry were intact. The durable watermark was 17:10:01 UTC, matching
the last captured wall-power frame. Device time had reacquired through SNTP;
output was inactive, with no new job or DMA interrupt after the expired campaign.
The previous live counters were reset, as expected after a power interruption.

Console STOP then suspended local scheduling. The original disabled two-minute
configuration was restored, and the exact RF-inhibited image above was flashed
with successful readback verification. Final boot
`8a17b60fb05303d969c0a19ed9c7fee0` reported the inhibited simulator engine,
`enabled:false`, healthy storage, no reboot required, inactive output and the
same 17:10:01 watermark. Wi-Fi was up and SNTP synchronized, with one accepted
sample and approximately 111.675 ms sample uncertainty. No watchdog recovery or
fault diagnostics were present. The Pico remains connected to the Mac.

Adversarial review challenged signal attribution, self-reported completion,
USB-host absence, persistence versus live diagnostics, and clock/RF claims.
It corrected the guide's claim that closing one client proves absence of all
per-job host commands. It also requires receiver completion/decode alongside the
reservation watermark, retains the no-burst attempt and every RF diagnostic
failure, and explicitly excludes synthetic decoder timestamps from UTC evidence.
The physical repeats and independent capture/hash audit passed. A second
assessment checked the corrected claims against raw capture metadata, decoder
logs, USB inventory, before/after boot identities, retained watermark and the
verified disabled/inhibited final state. It found no remaining actionable defect
within this functional slice. Documentation links, whitespace and exclusion of
the actual private credentials passed again. No firmware source change was
needed in this campaign; the tested source/image identities remain those above.

Phase 9's bounded functional acceptance is complete. The skipped baseline's exact
admission gate was not captured, and the RF diagnostic failures remain explicit
qualification limitations; neither is represented as a successful test.

## Validation boundaries

Both exact standalone images passed the memory-layout inspection. The unchanged
source passed all 19 host tests, all 15 sanitizer tests, and WTP contract checks
covering 23 schema, seven raw JSON, one framing and eight transition cases.

This campaign addresses bounded standalone operation on the recorded setup.
It does not qualify calibrated absolute UTC/GPIO onset, receiver frequency,
output power, filters/harmonics, supported band/mode coverage, access-point
compatibility, flash endurance, destructive brownouts or long-duration reliability.
