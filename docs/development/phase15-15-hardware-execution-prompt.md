# P15.15 pad, restart/USB and conducted RF acceptance

Execute this follow-up on `devel`. The operator explicitly requests the pad
readback, restart/physical USB re-enumeration and conducted RF checks, iterative
adversarial assessment, and attributable commits/pushes. Both named Picos are
USB-connected to wspr5 and remain connected through their established conducted
RF paths. This current statement authorizes routine firmware loads, USB/WTP
control and restoration for this finite campaign; do not ask again per job.

## Scope and entry evidence

Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md, the original
[P15.15 prompt](phase15-15-execution-prompt.md),
[software record](phase15-15-results.md), [GPIO contract](gpio-drive.md),
[USB contract](../protocol/USB-Management.md), and the existing physical harness
and restoration contracts. Inspect Pi instructions before changes there.
Preserve concurrent work. Stay on `devel`; do not execute P15.16 or later phases,
publish a release, change the default firmware target, or modify the separate
operator documentation site. No subagent is authorized by this prompt.

Refresh full local/remote source identities and working state. Initial delivered
pair: Pico `d6de1f3cf14dc49266c4401c3bca91b8ce9da688`, Pi
`fe701cf4c2b05e46cb84927188984084503d1cea`. The immediate pre-feature Pico
baseline is `46b256c636fb44c8ed059000d7b3f3b94cceea9e`. Bind exact firmware
bytes to source, SDK, compiler, board, normal 138 MHz, PIO/DMA and RF pin. Existing
builds may be reused only after their product hashes and linked checks match.
Keep credentials, full flash, journal payloads, firmware and IQ in private ignored
evidence. Never publish those materials accidentally.

Identify A: USB `0BF4B4AEC9FFB344`, WTP
`fd6127d11d6aca42a9905fa3fb1bf1d5`; B: USB `CDDBF8767C506C07`, WTP
`29f20b7342051ef947aa56cb9d4fab42`; receiver RSP1B `2404058C60` on wspr5.
Confirm physical parent/interface mapping afresh instead of reusing tty numbers.
Established path: each selected GP2/GND source through its own 20 dB attenuation,
the combiner, then 40 dB attenuation to the receiver; no antenna or LPF.
Use the current operator confirmation and live identity, not historical captures,
as setup evidence. Keep the other Pico and all reference sources inactive.

Read-only preflight checks active jobs, services, device owners, locks, storage,
receiver helper identity and capture dependencies. Acquire nonblocking locks
for both boards and receiver. If WsprryPi is competing, record its initial state
and stop only that service for the finite test, restoring it afterward. Do not
alter boot enablement, Pi GPIO, host network, unrelated workloads or GPSDO output.
If another owner is active, preserve it and report the concrete conflict.

Before any candidate load, capture INFO/STATUS, configuration/profile/progress,
scheduler STOP/enabled state and no-repeat watermarks. Require inactive/unowned
boards and disabled schedules. Save and independently verify each original full
4 MiB flash. Record original firmware and private snapshot hashes. Restore code,
profile, progress and config after testing, but never roll back a no-repeat
watermark advanced by legitimate jobs. Preserve the current cursor region during
restoration and verify the exact restored ranges separately. Do not promise an
unchanged full-flash hash when a legitimate cursor advances.

## Frozen finite matrix and budget

Use maintained tools, inspected before execution. Native Pi C++ compilation
stays on Linux. No SDK downloads, tool installation or unbounded retry loops.
The only RF frequencies are 137600 Hz and 14097100 Hz. Both are established
supported points at normal 138 MHz. No band, clock or harmonic sweep is implied.

1. On the immediate pre-feature image, capture one 5 s Tone at each frequency
   on A and one 5 s Tone at 14097100 Hz on B; record nominal baseline 4 mA and
   the SDK/source basis without inventing a new-API pad readback on old firmware.
2. On candidate firmware, for each board and each of 2/4/8/12 mA, use real USB
   management to save, inspect saved versus boot state, explicitly restart,
   observe disappearance/reappearance of the physical USB device, rediscover
   all three CDC roles by serial/parent, negotiate a new session and boot ID,
   and verify persistence, saved/active state and old-session rejection.
   Include absent/default initialization, explicit 4 mA, A/B/A sticky restart,
   unchanged unrelated fields, and inactive output throughout restart.
3. A normal RF adapter is initialized when a prepared job is armed, before
   its scheduled launch; LOAD alone does not open the hardware.
   Distinguish initial unknown pad observation from a verified SDK getter.
   For all four settings on both boards, LOAD a complete 1 s Tone and ARM it
   15 s in the future. Inspect actual adapter getter readback while armed and
   output-inactive, cancel before launch, then verify clean idle. Reserve the
   possible 1 s RF duration before each ARM, even when cancellation is intended.
   Exercise normal completion and reopen/rearm; cancel a future armed job and
   abort a running job. Check immutable boot selection, no drive application
   during a job, no output resurrection, error/stack/DMA/refill diagnostics,
   and that only the selected RF pin is targeted. External auxiliary-pad
   register evidence is a separate claim; do not infer it from RF silence.
4. Candidate conducted comparison: A gets one 5 s Tone at each frequency for
   each setting; B gets one 5 s Tone at 14097100 Hz per setting. Bracket the
   candidate sequence with one final 4 mA capture at those same board/frequency
   points. Those repeats assess drift/repeatability; retain every original.
5. Complete/cancel/abort/rearm checks may share those captures. Additional
   lifecycle jobs are at 14097100 Hz only, at most 2 s RF each. Freeze their
   count before ARM. Total campaign cap: 36 armed jobs, at most 180 s RF,
   at most 30 receiver captures of 20 s each (1.2 GB at 250 ksample/s CF32).
   This includes at most two diagnostic jobs after a preserved, reviewed failure.
   Unused budget does not authorize more work. Refused pre-ARM preparation is
   recorded separately. Do not repeat failed RF until a desired pass appears.

Before RF, save the resolved machine-readable plan, exact job counts, durations,
images, helper hashes, identities, path and receiver settings. Any deviation
must be recorded before the affected new window and stay within these caps.
The first attempt retained two valid A baseline captures and stopped at a null
LOAD-only observation, without arming the pad probe. The corrected continuation
must reuse those exact baseline captures by verified hash, carry forward all
consumed windows/budget, and require verified previous restoration. This is a
harness correction, not a retry of failed RF.
The second attempt preserved completed A 4/2/8 mA captures and stopped during
HELLO, before CLAIM/ARM for the 8 mA cancellation cell, when an old partial CDC event
remained queued. The next continuation must use the production-equivalent
100 ms DTR-low/discard/discard/DTR-high opening sequence while idle. Reuse every
completed exact-image cell by record/capture hash, carry forward the full used
budget and prior pad/restart evidence, and execute only missing cells. Do not
scan past malformed bytes or replay a mutation on the failed connection.

## Measurement and acceptance

Receiver: channel 0, CF32, 250000 sample/s, 200000 Hz bandwidth, fixed 20 dB gain,
AGC and bias tee off, center frequency equal to RF minus 25000 Hz. Preserve the
same chain/settings between baseline and candidate. Use the maintained capture
helper, discard its initial read as documented, retain exact requested counts,
and require zero overflow/clipping, successful cleanup and independent SHA-256
verification. Reserve at least 2 GiB beyond the next capture. Capture quiet
before and after RF; confirm local job/boot identity and terminal inactive state.

Readback passes only when a real board's adapter reports its SDK getter value
matching 2/4/8/12 mA after actual initialization. Reading saved JSON, an enum
mapping, a mock or a null value is insufficient. The cached observation must be
bound to the current boot and an actual adapter open/verify event. Do not claim
continuous physical sensing or measured pin current.

Restart passes only with durable setting retention, fresh boot/session, physical
USB enumeration change and successful role rediscovery/readback; a process
reconnect alone is insufficient. ACK deferred restart exactly once. Unknown
mutation outcome requires authoritative readback, never automatic replay.

For each valid Tone capture, reduce quiet-subtracted linear power with identical
FFT/window/bin rules, locate the expected carrier, report relative dB/amplitude,
close-in sidebands and available-span added components, and retain a plot/table.
Require a continuous expected carrier, complete finite duration, at least 10 dB
on/off contrast and inactive post-job output. For baseline/candidate 4 mA use
a predeclared comparison screen: carrier power within 1 dB after accounting for
the observed 4 mA repeat spread, and no new resolved in-span feature more than
3 dB above baseline when it is at least 10 dB above local quiet noise. Preserve
the local noise floor with a 31-bin quiet median as well as the actual quiet
bin; compare baseline features within three FFT bins to tolerate sub-bin drift.
These reducer rules are frozen before candidate comparison, with synthetic
regressions for a real added spur and a false quiet-bin null. Preserve
numerical outcomes even if a screen fails; investigate offline before using a
diagnostic slot. These are bounded regression screens, not calibrated watts,
absolute frequency/timing, regulatory emissions or all-band qualification.
For 2/8/12 mA report the measured change and spectral behavior without imposing
an invented current-to-power ratio or inheriting 4 mA qualification.

**Operator clarification during execution:** in-span energy is interesting but
does not invalidate these tests unless it prevents detecting and validating the
pad checks. Preserve the original numerical spectral screens and their failures
as nonblocking observations. The completed captures retain clear carriers and
valid pad/identity/lifecycle evidence, so no further RF window is needed for
this follow-up. Do not reinterpret a diagnostic spectral failure as a failed
pad, persistence or USB check, or silently change a threshold to obtain a pass.

## Failure, restoration, review and delivery

On timeout, identity change, lost control, receiver integrity failure or unexpected
output: abort the owned job, release ownership, close receiver streams, preserve
the failed evidence and stop dependent RF work. Finite job duration remains the
backstop. No new ARM after unverified cleanup. Verify both boards inactive and
unowned before reflashing, and preserve the latest no-repeat cursor while
restoring original firmware/settings. Verify restored flash ranges, settings,
profiles/progress, cursor monotonicity, STOP/schedules, clock/pin, receiver release,
reference state and the original WsprryPi service state. Record any limitation
or required physical intervention explicitly.

Write a sanitized hardware results record and machine-readable result/evidence
manifest. Link original and failed captures privately by hash and include source,
firmware, helper, board, boot, receiver, path, exact commands, counts and remaining
claims. Update the existing execution record and checklist only to the achieved
scope. Retain “In progress — software complete; physical acceptance pending”
until required physical cells and restoration pass; do not waive P15.16 gates.

Perform adversarial self-review of the prompt, harness, state transitions,
measurement reduction, raw evidence integrity, restored state and claims. Attack
false/cached readback, wrong board/boot/pin, session reuse, false re-enumeration,
cursor rollback, unsafe retries, competing signals, baseline mismatch, capture
overflow/clipping, noise-floor subtraction, receiver saturation, selective
reporting and unjustified qualification. Record each finding, fix actionable
code/tooling/documentation defects, rerun affected checks and reassess until no
actionable in-scope findings remain. Name this self-review honestly. Required
missing physical evidence remains open even when no source defect remains.

Commit attributable prompt/tool/test/result/development-documentation changes in
each affected repository, push `devel` without force, independently verify remote
parity and report actual working state. No unrelated files, secrets, snapshots,
generated firmware or IQ enter Git. Documentation Impact must distinguish updated
development records, unchanged WTP/old contracts, and P15.20 operator-site work.
