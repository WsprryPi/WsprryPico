# Short WSPR Type 2 and Type 3 decode on 20 m

Execute only item 2 in the [Consolidated backlog](consolidated-backlog.md):
capture and independently decode one Type 2 → Type 3 pair on one Pico at
14.097100 MHz RF base frequency. Record the result and evidence closeout,
perform independent adversarial review, repair actionable findings and repeat
affected checks/review, then commit and push the scoped result.

This saved prompt does not start the test. Hardware operations and publication
begin only when the operator asks to execute it. Prompt preparation leaves
item 2 not started.

## Entry and scope

Work in /Users/lbussy/GitHub/WsprryPico. Read AGENTS.md, README.md, CONTRACT.md,
docs/architecture.md, docs/development/README.md and the consolidated backlog.
Print its complete Finish now section, preserving order and NTP Work grouping.
Use ✅ finished, ⏳ in flight and ▧ not started. The consolidated backlog is the
sole current/future work list; do not create another roadmap or punchlist.

Inspect branch, full HEAD, upstream, live remote devel tip, staged/unstaged
changes and untracked files. At preparation, devel and the queried remote tip
were 0c0b0654e169c8881168af4324e4d6b4a94c994d; contract reconciliation and other
documentation edits were in progress. Refresh actual state rather than using
this snapshot as a reset target. Preserve all concurrent work. Change only
item 2's status during this execution, first to ⏳ and finally according to
the actual outcome.

Read the accepted implementation and evidence before choosing commands:

- [Type 2/3 software acceptance](phase15-8-wspr-type23.md), especially automatic
  planning, frozen-pair scheduling, receiver context and original RF limitations.
- [Standalone behavior](standalone.md), [current API](../browser-api.md),
  [normal firmware selection](phase15-16-results.md) and
  [GPIO drive](gpio-drive.md).
- [Recorded physical setup](phase15-15-hardware-results.md) and
  [earlier independent RF decode](rf-wspr-validation.md).
- src/encoding/wspr_plan.cpp, src/standalone/scheduler.cpp,
  tests/wspr_plan_tests.cpp and tests/wspr_oracle_vectors.json.
- scripts/decode_rf_wspr.py and the actual retained capture/decoder tools
  proposed for this run. Historical reproduction commands are examples tied
  to their original firmware and setup, not current commands to run blindly.

Type 2/3 encoding, all-symbol/oracle checks and software acceptance already
exist. This task adds a short captured-RF observation. Do not repeat the old
implementation campaign or modify WsprryPi, WsprryPi-Docs, installed product
software, protocols, schemas, admission limits or qualification policy.

Do not implement amplifier enable, NTP/calibration improvements, CI/deployment
infrastructure, installer, UI review, release publication or broad band/mode
qualification. Optional amplifier settling/lead/tail and automatic NTP-server
discovery/preference remain future work. Reading this prompt does not invoke
repository or harness cleanup; retain historical evidence and failed attempts.

## Fixed setup and RF budget

The operator selects **20 m** and says to assume the RF chain is still as it
was before. Carry forward the established conducted setup without requesting
another routine RF approval or rebuilding the physical path:

- One Pico 2 W / RP2350, direct GP2/GND, through its existing 20 dB attenuation,
  the combiner, then 40 dB attenuation into SDRplay RSP1B 2404058C60 on wspr5.
  No antenna, extra amplifier, filter or reference is added.
- Prefer Pico A if present: USB serial 0BF4B4AEC9FFB344, recorded WTP identity
  fd6127d11d6aca42a9905fa3fb1bf1d5. Pico B is USB CDDBF8767C506C07,
  recorded WTP identity 29f20b7342051ef947aa56cb9d4fab42. Use exactly one;
  identify the actual physical parent, CDC roles, device and boot live.
  If only B is available, select and record B before freezing the run.
- The unselected Pico remains inactive. Respect existing board/receiver locks
  and other users. Do not take over active work or infer inactivity from a
  missing reply. Resolve only a concrete identity, ownership or access conflict.
- Preserve actual boot drive, RF pin, correction, attenuation, cabling and
  reference state. Do not change drive strength or introduce calibration.
  Keep unused GPSDO outputs disabled as in the recorded setup.
- Use the normal 138 MHz PIO/DMA engine. Retain the established receiver
  settings: CF32, channel 0, 250000 samples/s, 200000 Hz bandwidth, 20 dB gain,
  AGC and bias tee off. Verify and record actual settings. Tune for the selected
  20 m signal; receiver tuning is distinct from modifying the physical chain.

The RF budget is **one pair: two complete 162-symbol frames**, Type 2 first,
Type 3 second. No warmup, pilot, tone, other band, other board or automatic
retry is included. Charge an actual RF start against the budget even if capture
or decoding fails. Offline analysis may be repeated on the same captures.
Any additional RF attempt requires an explicit extension from the operator.

Use a finite watchdog and an expiry that permits the complete pair but excludes
the next recurrence. Bound acquisition/awaiting the pair to 20 minutes after
arming the test workflow; do not leave indefinite schedules or capture tasks.
On uncertainty, stop and verify inactivity before doing anything else.

## Newest uninhibited firmware prerequisite

Before starting, identify and load the **newest accepted uninhibited normal
WsprryPico firmware** from the current accepted source. Refresh devel at the
execution boundary, freeze the full source SHA and check for a newer accepted
product change before starting RF. Do not let an old available image silently
become the test candidate. A label or filesystem timestamp alone is insufficient.

The backlog also requires a CI-produced image for decode verification. Retrieve
the successful matching CI run's normal WsprryPico UF2, source/build manifest
and checksums; verify run, full commit, target, build inputs and image hashes.
Use those exact bytes. An inhibited, bench, RFWTP, fault-fixture or old
compatibility artifact does not satisfy the selected normal-firmware test.

**The autonomous RF base is currently a build setting**, not a runtime station
frequency field. The selected image must have
WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ=14097100 and the normal
138000000 Hz clock. The default 3570100 Hz image cannot run this scheduler
pair on 20 m. Verify the accepted source, manifest, linked image and reported
standalone base; the expected reported base is 14097100000000000 nanohertz.
Do not add a Pi dial offset to the RF job frequencies.

If the newest accepted normal CI image with the required 20 m build selection
does not exist, complete offline preparation and report that specific
prerequisite. Do not implement backlog item 7, silently substitute a local
build/older image, or relabel a two-raw-job test as the native scheduler pair.
An operator instruction that explicitly changes this image requirement may
supersede it; record the resulting evidence scope accurately.

Preserve private configuration backups and the exact original restore image
before loading firmware. Use an ordinary settings-preserving update, not a
whole-flash erase. Verify live device/product/source identity, a new boot where
applicable, the physical PIO/DMA engine, 138 MHz, RF base, saved versus boot
drive, restart state and inactive/unowned status before enabling any schedule.
RF capability alone is not permission to bypass clock, ownership, fault,
frequency or output-admission checks. Do not install tools or download an SDK
incidentally to this test.

## Freeze one native pair

Use the Pico application's accepted automatic planner and standalone scheduler,
not host-generated substitute symbols or per-symbol network delivery. On this
conducted path, prefer the source-tested unambiguous payload PJ4/AA0NT,
EM18IG, 20 dBm unless the operator supplies another supported test identity.
Reported dBm is message content, independent of actual transmitter power.
Do not use explicit angle brackets, which select a Type 3 single, or the known
/Z versus /09 ambiguity for this bounded confirmation.

Before any RF, record the authoritative plan: count 2, Type 2 then Type 3,
exact full call, six-character locator, power, payload/symbol identities and
the same RF base for both halves. Tone 0 is 14097100 Hz; the remaining
tones use the existing WSPR spacing. Keep profile-owned station changes on
their accepted transactional authority; preserve revisions and readback rules.

Back up original settings privately. Arrange exactly one future recurrence
through accepted configuration/schedule interfaces, initially disabled. A
600-second period with a chosen future slot and bounded expires_utc_s can
exclude another occurrence; verify this against actual scheduler preflight.
Expiry must include the second frame's entire accepted launch second and
duration, yet precede any next eligible occurrence. Preserve STOP semantics
and do not reset or roll back the durable watermark to force a replay.

Both frames are complete local jobs: nominally 110.592 seconds each, launch
starts 120 seconds apart, RF-off gap 9.408 seconds and total nominal span
230.592 seconds. These are expected software values, not new measured results.
Verify current UTC quality and independent admission for both launches; do not
relax uncertainty or holdover bounds. The scheduler's ownership/renewal path
must remain intact across the gap. Begin capture before enabling the bounded
occurrence, and stop further scheduled work after the pair.

## Capture and independent wsprd decode

Capture real receiver data covering both full frames and the intervening gap.
Bind sample ranges to the two job IDs, device/boot, UTC and monotonic event
observations. Preserve raw IQ and metadata, sample counts, overflow/drop and
clipping observations, actual tuning/gain/rate, and SHA-256s. Incomplete or
unattributable capture is not a pass. Keep raw IQ, WAVs, firmware and private
settings under a fresh ignored build/short-wspr-type23-decode-* directory.

Identify the actual independent WSJT-X wsprd executable by version, source or
package provenance and binary hash. Inspect that version's help/source before
choosing flags or output parsing. Do not patch its packing/demodulation/hash
arithmetic to agree with Pico, seed it with expected symbols or inject a known
call into its hash table.

Audit the existing decode helper before reuse: it hard-codes a 3570100 Hz
conversion base, a 3.568600 MHz dial argument, Type 1 three-token matching,
synthetic slot naming, separate output directories and -H. Those assumptions
are not a Type 2/3 pair decoder. Current official wsprd source uses -H to
disable the hash table; verify the installed version and omit that flag for
the primary context-preserving run. See the
[official decoder source](https://raw.githubusercontent.com/WSJTX/wsjtx/master/lib/wsprd/wsprd.c).

Convert each real capture window transparently into decoder audio. Record
exact sample boundaries, fixed IQ frequency translation, filters, resampling,
normalization, padding and WAV hashes. Preserve elapsed time, modulation,
frequency offset and drift. Do not synthesize replacement audio, stretch time,
fit away drift or search offsets until an expected message appears. The usual
1500 Hz mapping gives a 14.095600 MHz dial label for this RF base; derive and
record the actual mapping. A synthetic filename is not UTC evidence.

Use a fresh isolated decoder data directory with no preexisting callsign hash
state. Decode captured Type 2 first; preserve only the state naturally produced
by that decode, then decode captured Type 3 using the same isolated state.
Record commands, flags, working/data directories, timeouts, return codes,
stdout/stderr and hash-file existence/content hashes before and after each
step. Keep decoder files out of the user's normal WSJT-X data directory.

Acceptance requires an actual Type 2 decode with the exact compound call and
power, followed by a Type 3 decode with the matching resolved full call,
six-character locator and power under that naturally learned context. Parse
the two actual formats separately; Type 2 has no locator. Exit code zero,
unrelated decodes or a bare unresolved <...> are insufficient for full-pair
identity resolution. Report frame decoding and context resolution separately
if only part succeeds; do not manufacture success from expected metadata.

Reuse the captured Type 3 WAV in a second clean decoder directory as an offline
cold-context control. Record its actual unresolved/resolved behavior without
preloading expected identity. Run a wrong-call/grid/power comparison against
the unchanged decoded output to verify the acceptance check fails as intended.
Neither control consumes another RF window. Expected values are compared only
after independent decoding. No WSPRnet upload is part of this task.

If a small capture/conversion/reporting helper is necessary, keep it narrowly
scoped and test meaningful failures: wrong identity, missing half, stale hash
state, wrong order, decoder failure/timeout and incorrect frequency mapping.
Do not change product firmware, firmware dependencies or admission policy to
rescue a failed run. Preserve failures; additional RF needs more budget.

## Restoration and durable evidence

Stop the bounded schedule and verify output inactive, no pending pair and no
remaining test ownership. Restore original configuration, enablement/STOP
state, receiver/service state and any firmware changed for this test, using
the retained restore image and supported procedures. Restore enabled schedules
only when the original state is known and the operator's standing instruction
permits normal operation. Do not copy old flash wholesale or roll back consumed
watermarks. Record intentional watermark advancement and every restoration
check; a requested command or lost reply is not proof of restoration.

Write a concise result in short-wspr-type23-decode-results.md and a sanitized
machine-readable evidence manifest beside it. Include exact source/CI/build/
UF2 identity; board, boot, engine, clock, pin/drive; fixed 20 m frequency;
physical path; actual settings and test payload; pair/jobs/slots; capture,
conversion, decoder and hash-state provenance; decoded output and explicit
pass/fail per half/context; actual RF budget; failures and restoration.
Use relative durable links and hashes; leave credentials and bulk captures
untracked and identify their retained local location without exposing secrets.

Keep the tested image/source identity separate from the later evidence-only
commit. Link the result from the existing Type 2/3 record with a narrow dated
follow-up; preserve its original software acceptance and failures. This one
pair establishes only the recorded board/image/20 m/payload/path observation,
not every compound call, hash collision, band, board, clock, calibrated power,
absolute RF accuracy, launch timing or release qualification.

## Adversarial review and publication

Use a separate read-only adversarial reviewer to inspect the final scoped diff
and retained evidence. Challenge newest uninhibited/20 m image selection,
CI/source/hash binding, native planner versus substitute jobs, two-frame budget,
capture authenticity/completeness, Type 2 versus Type 3 matching, hash-state
isolation/ordering, circular expectations, hidden signal correction, authority,
expiry, restoration and overstated acceptance. Require specific actionable
findings with evidence and consequences.

Repair actionable in-scope findings; rerun affected host/offline checks and
obtain fresh review of the repaired final result. Iterate until no actionable
finding remains. Review requiring new RF must respect the remaining budget;
report an exhausted budget or missing prerequisite instead of claiming closure.
Do not broaden the task into a firmware repair or another backlog item.

Set only item 2 to ✅ when the complete pair passes, restoration is verified
and final review is clear. Otherwise leave it ⏳ with the actual unresolved
result. Keep the saved-prompt link, 20 m requirement, NTP grouping and all other
statuses intact. No parallel pending-work list is needed.

Inspect the final and staged diffs, run appropriate documented checks plus
git diff --check and git diff --cached --check, and stage only attributable
prompt/tool/test/result/link/status changes. Do not absorb concurrent contract
reconciliation, cleanup or other user changes. Commit and non-force push the
scoped result to origin/devel; this is authorized on execution without another
routine confirmation. Preserve concurrency and never reset, stash, clean or
force push user work. Do not tag, create a release or publish firmware/docs.

Independently query the remote tip after push and compare with local HEAD and
upstream. Report actual outcome, evidence paths, tests/skips, review repairs,
RF count, restoration, commit/push/parity and remaining working-tree changes.
Reprint the complete canonical punchlist using ✅/⏳/▧. Stop after item 2.
