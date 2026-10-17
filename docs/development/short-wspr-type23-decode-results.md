# Short WSPR Type 2/3 captured decode

Execution date: 2026-10-17. **The captured Type 2/3 pair passed independent
decoding at 3.570100 MHz (80 m); restoration and final independent evidence
review are complete.**
The [executed prompt](short-wspr-type23-decode-execution-prompt.md) defines the
one-pair budget and the [evidence manifest](short-wspr-type23-decode-results.json)
records the final observations. Current work remains in the
[Consolidated backlog](consolidated-backlog.md).

## Operator selections and frozen image

During execution the operator changed the selected frequency to the established
test frequency, **3.570100 MHz (80 m)**, and explicitly selected a **fresh
current-source local build**. The original prompt's 14.097100 MHz/20 m and
CI-produced-image requirements are superseded for this observation. The live
CI inventory contained Pages deployments and no eligible normal firmware image.
This execution does not implement the separate CI backlog item.

The normal `WsprryPico` image was freshly built from an immutable Git archive of
accepted source `14698ca1dba32914959530a3b5a0cf41f74caf8f`. The later accepted
`76b794f7a770e6a1d80f140e30ecb89c1da3e851` contains a documentation-only handoff;
its product/build inputs match the frozen source. No product implementation,
protocol, admission limit or clock policy changed for this test.

| Image property | Actual identity |
| --- | --- |
| Target/version | Normal `WsprryPico`, Pico 2 W/RP2350, `0.0.0-devel` |
| Build revision | `14698ca1dba3-dirty` |
| UF2 SHA-256 | `6cbe319e996b4a935dc7ba311583832e68228177cb2b7434573776ab19284528` |
| ELF SHA-256 | `a8c75d1e79d95007724e65bd831895aea9ecd77e9d710736e0e923a7750c1845` |
| Engine/clock/base | `pio-dma-gp2`; 138000000 Hz; 3570100000000000 nHz |

The revision label inherits the enclosing checkout's documentation change;
the archived compilation inputs match the frozen commit. This image predates
the evidence-only delivery commit and is not relabeled with that later commit.
Pinned SDK/toolchain inputs and build-log hashes are in the manifest.

## Setup and native pair

Pico A is USB `0BF4B4AEC9FFB344`, WTP
`fd6127d11d6aca42a9905fa3fb1bf1d5`. Its direct GP2/GND path retains the existing
20 dB attenuation, combiner and 40 dB attenuation into wspr5 RSP1B
`2404058C60`. No antenna, amplifier, filter or reference was added. Pico B
remains inactive. Both GPSDO outputs remain disabled. Saved and boot drive are
4 mA; reported WSPR dBm is message content, not measured RF power.

The device's authoritative preview selects exactly Type 2 then Type 3 for
`PJ4/AA0NT`, `EM18IG`, 20 dBm, without suffix ambiguity. Accepted USB configuration
transactions transfer station authority to the standalone configuration. An
explicit reboot with the schedule disabled clears the volatile STOP latch for
the bounded test. Restoration returned the original disabled/STOP state.
The Pico scheduler creates both complete local jobs; host-generated symbols
are not submitted. Oracle payload/symbol identities are retained only for
software provenance and are not supplied to the independent decoder.

The selected occurrence uses a 600-second period, launches at 20:02:01 and
20:04:01 UTC, and expires at 20:05:54 UTC. Expiry includes the complete second
launch second and frame while excluding the next recurrence. Capture starts
before enablement. Its fixed settings are CF32/channel 0, 250000 sample/s,
200000 Hz bandwidth, 3545100 Hz tuning, 20 dB gain, AGC/bias tee off.

## Capture, decode and restoration outcome

Exactly two RF starts produced two complete frames on Pico A. The retained
480-second capture contains all 120000000 requested complex samples
(960000000 bytes), with zero reported overflow, timeout or clipping. Receiver
deactivation, stream closure and device release are verified. IQ SHA-256 is
`6d1e821ce38474bd0eaf2233d31c82694208805f2808e8581e72d22f920d121b`.

| Native frame | Job ID | Slot (UTC) | Independent result |
| --- | --- | --- | --- |
| Type 2 | `eeeeeeeeeeeeeeee18df69a1f2befa00` | 20:02:01 | `PJ4/AA0NT 20` — pass |
| Type 3 | `eeeeeeeeeeeeeeee18df69bde34daa00` | 20:04:01 | `<PJ4/AA0NT> EM18IG 20` — pass, full call resolved |

Both running jobs retain the same device/boot, normal engine, 138 MHz clock,
4 mA ARM-time pad readback and scheduler owner across the gap. Each launch
passed ordinary UTC admission. The receiver sample intervals are
`[58643500,86291750)` and `[88649500,116297500)`: 110.593 and 110.592 seconds,
with 120.024 seconds between onsets on the nominal receiver sample axis.
Software host UTC observations associate these intervals with the two jobs
within an explicit two-second screen. The receiver has no hardware timestamp;
these values do not qualify launch timing or calibrated elapsed time.

The independent executable is Debian WSJT-X `wsjtx 2.7.0+repack-1`,
`/usr/bin/wsprd`, SHA-256
`3e1f562239d86c2deb08b237cef9fcb8511d4dd7579fee33c969abb784465be3`.
Its actual help confirms `-H` disables hash use/update; the primary run omits
that flag. The [decoder helper](../../scripts/decode_wspr_type23_pair.py)
uses separate Type 2 and Type 3 matching, one fresh shared primary data
directory, a separate cold Type 3 directory, explicit 1500 Hz audio mapping
and a 3.568600 MHz dial label. Exact transformations, windows, commands,
return codes, outputs and before/after hash-table states are retained.

Primary decoding starts without a hash file. Type 2 naturally creates
`10051 PJ4/AA0NT`; Type 3 consumes that unchanged table (SHA-256
`d8c7d3eed8349de62c06126b67eb774f1f8bd4ca584b8e8d9c06d0b12b780ab4`).
The full primary output is:

```text
2002  40 -0.0   3.570110  0  PJ4/AA0NT 20
<DecodeFinished>
2004  40 -0.0   3.570109  0  <PJ4/AA0NT> EM18IG 20
2004 -21 -0.4   3.570179  0  <PJ4/AA0NT> EM18IG 20
2004 -21 -0.3   3.570183  0  <PJ4/AA0NT> EM18IG 20
<DecodeFinished>
```

The weaker duplicate Type 3 lines are retained as decoder output; they do not
represent additional transmitted frames or a spectral-quality assessment.
The cold-context control on the same Type 3 WAV returns
`2004  40 -0.0   3.570109  0  <...> EM18IG 20`: the frame decodes, but its full
call is unresolved. All three decoder processes return zero. Comparisons
against wrong call `PJ4/AA0NTX`, grid `AA00AA` and power 23 each fail as required.
No known call, symbols or hash entry is injected, and no WSPRnet upload occurs.

Conversion selects real 120-second windows starting one second before each
detected onset, applies a fixed 25000 Hz IQ shift, Hann decimation to 1000 Hz,
241-tap Hann-sinc interpolation to 12000 Hz and real 1500 Hz audio mapping.
Normalization sets peak magnitude to 28000 in 16-bit PCM; actual padding is
zero. No frequency/drift fit, time stretching or offset search is applied.
The manifest records exact boundaries, filters, multipliers and WAV hashes.

The actual workflow's raw status remains `FAILED`, with its sole error
`ValueError('receiver ended before complete pair')`. Its termination check
incorrectly required persistent `complete` state: after the second frame, the
native scheduler releases ownership, and `JobService::clear_job()` changes
state to `empty`. A separate hashed completion assessment records this
controller error. It requires both ordered running jobs, full associated IQ
intervals and a pre-STOP terminal sample with frame 2/2, last job equal to the
second job, no pending pair/owner/output/error, and zero DMA/fault diagnostics.
The original failed record is preserved; no replacement RF was transmitted.

Restoration reads back original revision `165303458e49` and the exact original
executable-region SHA-256
`d79128ffd81421d78523ddac21ed939a3c6ce21e8594006b669e800e4ee52d55`.
Only executable flash `[0x10000000,0x103f0000)` is restored. Private profile
comparison verifies equality apart from the acknowledged transaction digest;
the original station, schedules, expiry, enablement and STOP state match.
The profile generation intentionally advances from 9 to 11 for the test and
restoration transactions. The durable watermark advances from
`1791199541540946076` to `1792267441000000000`, preserving the consumed second
slot. Whole-flash restoration and watermark rollback are not performed.
Pico A is disabled, suspended, empty, unowned and inactive with no pending pair;
Pico B retains its original boot and inactive state. The original active host
service is active again, receiver cleanup is verified, and both GPSDO outputs
remain disabled.

An earlier disabled preparation was deliberately stopped for review repairs
before any RF. A station-restoration reply was lost. Subsequent private
code/profile/receipt and live readback checks verified restoration; its
failures remain retained. That recovery advances profile generation 5 to 9;
it leaves the original watermark unchanged. No RF budget was consumed by that
preparation. The initial toolchain invocation and decoder-test import failure
are also retained alongside their passing corrections.
The initial build-provenance record contains a stale digest for a repeated
decoder-test log. That initial record is preserved separately; an explicit
reconciliation records the retained log's digest and unavailable original log
bytes. Source, dependency and firmware hashes are unaffected. Final checks
have separately retained logs.

## Checks, review and evidence

Fresh archived-source host planner/scheduler checks passed 2/2. The decoder
failure-path checks passed 6/6, including wrong identity, unresolved call,
missing half/order, stale state, decoder failure/timeout with partial output,
frequency mapping and sample/job time association. WTP validation passed 23
schema, seven raw JSON, one framing and eight transition cases. All maintained
normal-image link/engine/stack/flash checks passed. The initial build-helper
toolchain failure and successful corrected invocation are retained.

Independent pre-RF review repaired ROM/partial-load cleanup, independent
restoration stages, ambiguous-save reconciliation, private profile checking,
RF-count uncertainty and decoder failure/context/attribution checks. Final
captured-evidence review is clear, with no actionable findings remaining.
The read-only reviewer independently checked source/image bindings, IQ/WAV
hashes and hash-state
ordering, and reproduced both WAVs byte-for-byte from the retained IQ.

Private local evidence is retained under
`build/short-wspr-type23-decode-20261017T194248Z/`; receiver/workflow originals
are under `/home/pi/short-wspr-type23-decode-20261017T194248Z/` on wspr5.
Raw IQ, WAVs, firmware and private backups remain untracked. The manifest
contains sanitized identities, relative retained paths and SHA-256s.

This observation can establish only the recorded board/image/frequency/payload/
conducted-path result. It does not qualify every compound call/hash collision,
another board/band/clock, calibrated power/frequency/launch timing or a release.
