# P15.13 current-firmware qualification results

Status: **CLOSED_SCOPED — 2026-10-17**. All ten selected band/mode cells have
evidence-backed Qualified dispositions under their explicit point/board/image,
receiver and complete-job conditions. Original failures are preserved.
See the frozen [plan](phase15-13-plan.md) and source-reviewed
[support policy](phase15-13-support-policy.md). Phase 14 and P15.1–P15.12
closures remain unchanged. P15.14 has not been started.

The initial clean checkout and freshly resolved remote `devel` tip were both
`165303458e49feaac1de54c8344058f56578d533`. The isolated detached source checkout
remains separate from subsequent host-only harness changes. Firmware version
`0.0.0-devel`, compiled revision `165303458e49`, normal 138 MHz, GP2,
PIO/DMA/divider 1, default GP14 capture, saved consumer profile and pin authority:

| Artifact | SHA-256 |
| --- | --- |
| StandaloneRF UF2 | `cb6ccfa3e9354d84c5ca3c993f4965f70716ed8bd99b076011406199fa1850eb` |
| StandaloneRF ELF | `128c975c6af14350a72df7f4c672eb534c60eb36023d41aba6afa30696cbe84c` |
| Standard inhibited UF2 | `cf52b41a411e1ae56adfb07a93b94ab56b375d2c1e72e3c6b3c0a152929240d8` |

SDK 2.3.1 `079c6f39023649b154152db30f1d781e884879bc`, Arm GCC 15.3.1,
picotool source `6f6458d792b93685a11423b244a585eaa99eafcf`. Both targets were
freshly compiled. Native helper compilation initially failed against the Mac's
27.0 SDK/linker combination; pinned pioasm was built with the existing 26.5 SDK,
and the retained pinned-source picotool executable was used. Firmware source
and dependency pins were unchanged; no SDK/tool installation occurred.

Private evidence roots are local `build/phase15-13-20261017/` and
`wspr5:/home/pi/phase15-13-20261017/`. Original captures are under
`source/build/acquisition-5/` on wspr5. All original preparation refusals and
subsequent assessments are retained. Raw samples, firmware, credentials and
private settings receipts remain outside Git.

## Preparation findings

No preparation refusal below consumed an RF window. The initial host guard
assumed an explicit saved pin field; the valid legacy record uses firmware's
default GP2/GP14/onboard plan. The harness now preserves that default and
custom assignments. A cleanup enumeration race was repaired, and the host
service was explicitly restored and both boards verified inactive/unowned.

After the first fresh flash, the ordinary consumer profile correctly rejected
Console `STOP`/configuration authority. The harness now uses allowed local
`ABORT` for suspension and the product's authenticated Consumer-Radio client
for a target/revision-bound merge of only the experimental-frequency flag.
Further guards caught an attempt before station readiness and absent optional
false fields in canonical Config readback. Those host assumptions were repaired;
the actual default flags were verified false again. The final campaign resumes
the exact verified flashed boot; these refusals are not RF/firmware failures.

The current image reserves flash from `0x103f0000` for saved progress and other
journals. The legacy image checker expected `0x103f3000`; it now recognizes
both historical and current maps and validates payloads against the actual map.
The full current journal range through `0x103ff000` was privately saved and
byte-verified unchanged across the firmware load. No journal rollback occurred.

## 8 m evidence reduction

All five selected modes have passing evidence on A at 40.001 MHz/138 MHz.
The original nominal WSPR decodes were fail/pass/fail. One fixed **+125 Hz
receiver-audio tuning translation**, applied independently once to each of the
same three original frames, produced three expected external decodes. No IQ,
RF waveform, symbol timing or drift trajectory changed, and no frame was
retransmitted. Keep the receiver condition explicit. This does not establish
that an arbitrary receiver needs exactly that correction.

An initial offline slicing guard wrongly demanded receiver start spacing within
50 ms of exactly 120 seconds. Original ARM targets are exactly 120 seconds apart;
SNTP reprojected their monotonic targets, and measured intervals were 119.941
and 120.017 s. They agree with the recorded monotonic projections within 2 ms.
Every burst is 110.592 s. The repaired reducer checks consecutive requested UTC
slots, complete envelopes and existing WTP launch semantics; the original guard
refusal, full parent and all child sample-range bindings remain retained.
This is an analysis repair, not a missing-frame replacement or RF retest.

8 m Tone: 5.000 s, minimum contrast 89.20 dB, interior amplitude ratio 0.9956.
Indicated offset mean +124.81 Hz; simultaneous-reference mean +81.03 Hz,
observed +80.65 to +81.48 Hz. Half-range 0.42 Hz is empirical drift/repeatability;
combined absolute uncertainty remains unavailable on the nominal SDR sample axis.
The old +100 Hz indicated-frequency screen remains failed; frequency error is
reported separately under the selected packet.

## 5 m admission and finite continuation

The first 5 m Tone LOAD was rejected with WTP `INTERNAL_ERROR` before ARM and
before engine preparation. INFO showed 68,784 bytes available before CLAIM and
66,584 after refusal, no allocator/DMA errors and no engine diagnostic. Source
requires a 32 KiB preparation workspace plus an independent 32 KiB authority
reserve while the request remains resident. The claim outlived the rejected
LOAD; an initial harness cleanup incorrectly depended on an accepted job ID.
The owner expired inactive; the harness now releases its own claim even when
LOAD admitted no job. GPSDO and the host service were restored throughout.

The seven unused 5 m windows continue on the same image/boot, with the existing
bounded LOAD workspace estimate checked before capture/CLAIM. The WSPR group
waited quietly 82.8 s for 86,640 bytes: observed availability rose from 70,832 to
89,136 bytes. This changed no firmware reserve, cache TTL, schedule or clock.
The failed LOAD/incomplete receiver attempt remains separate, with zero RF;
there is no board-specific synthesis failure requiring B and no clock issue.

## Focused retest conditions

The original 5 m WSPR acquisition ended after frame 1 completed: the next LOAD
connection reset before ARM, and the receiver was stopped incomplete. That
original capture cannot qualify a frame; original frame slots 2 and 3 were not
transmitted. The first rejection is bound to the explicit memory gate; the later
connection reset is consistent with pressure but is not independently proven to
have that sole cause.

One diagnostic is exactly three frames after a verified inactive reboot of the
same image. It requests the exact four realized NCO frequencies and merges only
adjacent equal-frequency events: 127 events instead of 162, no adjustment replies,
same sampled waveform and 110.592-second duration. A regression compares every
original symbol boundary against the equivalent realized state. This tests RF
operation with an existing complete-job representation; it does not add a WTP
profile, change the encoder, lower firmware reserves or switch the clock.
The initial quiet preflight emitted no diagnostic RF and was ended before this
cold-start condition. Source/image, all boots and original refusals remain bound.

The first 5 m FSKCW observer aborted its running job after a five-second RENEW
reply timeout, leaving an incomplete capture. The 60-second claim already covers
its 35-second job and eight-second launch lead. One separately enumerated FSKCW
diagnostic omits that unnecessary renewal. Control request budgets are recorded
as ten seconds in the final observer; local RP2350 timing remains independent.
No further RF retry is authorized by these focused plans if unresolved.

The expected accounting is twelve nominal ARMs (fourteen planned, two original
5 m WSPR slots untransmitted) plus four diagnostic ARMs, sixteen total. The
original partial FSKCW and invalid 5 m WSPR acquisition are not relabelled passes.
Final receipts, rather than this forecast, determine the reported counts.

## Final matrix and six accepted WSPR frames

| Band / engineering point | Tone | WSPR | QRSS | FSKCW | DFCW |
| --- | --- | --- | --- | --- | --- |
| 8 m / 40.001 MHz | Qualified | Qualified, +125 Hz audio | Qualified | Qualified | Qualified |
| 5 m / 60.001 MHz | Qualified | Qualified, +200 Hz audio; cold compact jobs | Qualified | Qualified, focused retest | Qualified |

Each entry applies only to **Pico A / GP2 / PIO-DMA / 138 MHz / the identified
UF2**. See the [machine-readable matrix](phase15-13-result-matrix.json) for every
actual job/boot, capture/metadata/analysis hash, decoder/audio command binding,
resource receipt and original versus diagnostic window identity. Both bands work
in the normal 138 MHz image; no alternate-clock build/reflash was used.
Broad admission envelopes retain their experimental flag. B has no new RF result.

| Accepted sequence | Frame | Nominal audio decode | Fixed audio translation | Expected decode |
| --- | --- | --- | --- | --- |
| 8 m original | 1 | Fail | +125 Hz | AA0NT EM18 37 |
| 8 m original | 2 | Pass | +125 Hz | AA0NT EM18 37 |
| 8 m original | 3 | Fail | +125 Hz | AA0NT EM18 37 |
| 5 m focused | 1 | Fail | +200 Hz | AA0NT EM18 37 |
| 5 m focused | 2 | Fail | +200 Hz | AA0NT EM18 37 |
| 5 m focused | 3 | Fail | +200 Hz | AA0NT EM18 37 |

Every accepted decoder run exited zero and retained actual stdout/stderr, WAV
hash and parent/slice binding. Decoder `/usr/bin/wsprd`, WSJT-X 2.7.0,
SHA-256 `3e1f562239d86c2deb08b237cef9fcb8511d4dd7579fee33c969abb784465be3`,
uses `-d -H`: no hash-table context. The helper's `691231_2359.wav`/`2359`
filename/output time is a synthetic burst-alignment label, not actual UTC.
Actual ARM/clock/monotonic/capture timestamps remain separate. The decoder also
reported weaker same-message solutions about 120 Hz above the primary in the
three 5 m captures; those lines remain in stdout. They do not establish calibrated
spur power, harmonic emissions or filtering performance.

5 m Tone: 5.000 s, minimum contrast 74.01 dB, interior amplitude ratio 0.9931.
Indicated offset mean +180.87 Hz; reference-compared mean +117.09 Hz, observed
+116.65 to +117.61 Hz. Empirical half-range is 0.48 Hz; combined absolute
uncertainty is unavailable. All keyed cases meet the declared human-copy checks;
phase/drift screens remain separate. These checks are not a formal human study.

The 14 accepted observations have no new allocator/TLS/DMA/stack faults. Minimum
observed available heap is **60,144 bytes**, above the unchanged 32 KiB authority
reserve. Maximum refill-to-ready is **2,008,000 ns**, below the 138 MHz full-buffer
period **3,799,188 ns**. These are observed counters, not an endurance/leak-freedom
claim. In-span spectral observations reuse the same captures; no harmonic survey
or calibrated watts/post-filter/antenna-ready claim is made.

## Actual finite accounting

- Nominal plan: **14** RF windows. **12** were armed; 11 completed control
  execution and the original 5 m FSKCW was observer-aborted. The original 5 m
  WSPR frame 1 completed RF but belongs to an incomplete acquisition and is not
  qualification evidence. Original 5 m WSPR slots 2 and 3 were never transmitted.
- Diagnostics: **four RF windows**, exactly three compact 5 m WSPR frames and
  one FSKCW retest, all complete. **16 total RF windows**; no B transmissions.
- Two pre-ARM/non-RF LOAD failures, all earlier preparation refusals, the
  interrupted quiet preflight and the partial first compact analysis remain.
  They add no RF-window credit. There was no repeat-until-three-pass loop.

The first nominal sequence is not called a successful fourteen-window run.
The ten final cells are supported by the separately identified valid observations;
no omitted or invalid original case is relabelled a pass. This is the explicit
focused-retest disposition permitted by the execution packet.

## Source, validation and reassessment

The separate project snapshots used are Pico `devel` above and optional offline
Harness `devel` `62aa6e2ffa904a10b674bb1792a3bd66ba8afea6`. The GPSDO tool's
remote `devel` is `7cba700821b13a7a8fd63ac54b046707ab52b31a`; the actually used
`lbe142x.py` is byte-identical to that snapshot, SHA-256
`97ca1f8c6737c19901edc853848eea5a39a3d8dc3d1a8c387f1ecc45cea3cff2`.
Its installed checkout is `541abd200210145fb36e83c9d6137cb56cdb5dcf`.
The Harness's existing unrelated dirty paths were preserved. No other repository
was edited. The receiver helper is retained instrument version 0.2.0,
SHA-256 `b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03`;
actual settings/device identity are verified in each complete metadata record.

Both fresh firmware targets and the linked image/journal checks pass. Hardware-
free C++ RF worker/failure, arithmetic/sample timing, frequency policy, standalone
lifecycle and core tests pass on wspr2. The exact new mark/space points were added
to arithmetic and admission regressions, then those targets rebuilt and passed.
The initial wspr2 Phase 14 Python run lacked NumPy; final wspr5 runs pass all
40 Phase 14 cases, eleven P15.13 cases and two image-reservation cases. Optional
campaign planning/analysis/evidence/adapter tests pass with the current clean
Harness snapshot and existing dependencies. RF analysis/measurement/correction
checks and ten product radio-client tests pass. No dedicated Type 2/3 or message-
generation suite, new endurance campaign or software-test CI pass is claimed.
Changed C++ ranges pass clang-format; unrelated pre-existing formatting warnings
were preserved. Whitespace, JSON and local documentation links were checked.

A fresh **self-review** covered source/image applicability, legacy-tool defaults,
profile authority, capture integrity, consecutive-slot versus local projection,
compact waveform equivalence, result reduction, actual decoder outputs,
frequency/coherence versus mode acceptance, finite accounting and restoration.
It repaired the host assumptions and cleanup described above, plus the compact-
event frequency annotation and terminal owner-expiry cleanup. A read-only audit
rehashes complete captures and every selected binding and compares all six child
slices byte-for-byte with the two retained full WSPR parents. No unresolved
finding remains inside this scoped claim. This is not an independent reviewer.

Actual full configure/build commands, caches, complete 1,945-file source manifest,
helper identities, ELF/UF2/map hashes and failure logs remain in private
`build/phase15-13-20261017/commands.json`, `manifest.json` and companion logs.
The reproducible configuration uses `pico2-w`, Release, pinned SDK/toolchain,
`WSPRRY_PICO_FIRMWARE_VERSION=0.0.0-devel`, normal 138 MHz, ordinary GP14 default,
no acceptance fixtures, and the explicit command:

```sh
cmake --build build/pico2-w --target WsprryPico WsprryPico-StandaloneRF --parallel 4
```

Local SDK paths, credentials, generated firmware and IQ are kept out of Git.
No runtime C++/web firmware repair was made: all RF observations use the same
clean current-devel firmware bytes. Subsequent changes are host tools, tests
and documentation; historical Phase 14 defaults/results remain reproducible.

## Restoration and P15.14 handoff

A separate fresh-lock final check verified A at revision `165303458e49`, boot
`05c4a2859477659b1dd7b594029f0c1a`, 138 MHz, consumer profile generation 5,
GP2/default saved pins, empty/unowned/output-inactive, disabled and suspended
scheduling, both experimental flags false. Its retained useful current firmware
is the UF2 above. B remains unchanged at `7bff45c0f32f`, boot
`bb49f3b37634173826df565b9faaef9f`, 138 MHz, generation 5, empty/unowned/inactive
and disabled/suspended. A watermark `1791199541540946076` and B watermark
`1791705481000000000` are unchanged. Config journal revisions legitimately advanced
for flag saves; no cursor or profile journal was rolled back.

GPSDO is locked, outputs 1/2 disabled, both frequencies 10 MHz, both LOW levels
unchanged, PPS1 false. wsprrypi.service is active as at entry; no boot-enable or
host network setting changed. Complete receiver processes closed/released the
RSP1B. Final process/lock closure is recorded privately. The no-antenna/no-LPF
conducted topology remains the operator's setup; filtering is their responsibility.

P15.14 must explain experimental opt-in and canonical omitted-false fields;
exact point/board/image scope; the fixed WSPR receiver-audio conditions; safe
inactive restart/quiet memory headroom and compact complete jobs; the partial/
failed nominal cases and finite diagnostics; normal 138 MHz operation without
per-band switching; historical-only 6 m receiver retuning; 4 m's required 150 MHz
build/reflash and Unqualified status; native 2 m unavailability; and the absence
of calibrated watts/absolute precision, LPF or antenna-ready qualification.
It must preserve station/profile/saved-progress, STOP and ownership boundaries.
P15.14 and its documentation site have not been started.

At qualification closeout, devel remained at the original revision, with these
changes uncommitted and the index empty. The concurrent roadmap update was
preserved and reconciled with this evidence. No staging, commit, push,
publication or release occurred during qualification. Subsequent repository
publication records the host tools, tests and documentation; the tested firmware
remains the exact source and artifact identified above.
