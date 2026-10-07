# Step 1 execution and adversarial review

## Disposition

Step 1 engineering preparation is complete on `devel`: reusable execution
prompt, fixed six-step record, finite runner/cases, candidate builder and
managed independent evidence collection. Steps 2–6 remain open. Only step 2
normally requires an operator; it has no response deadline. Both named Picos
are connected to the SDR and authorized for all six steps.

The [runner guide](phase13-1-runner.md) records reproducible commands, fixture
scope, exact budgets, one-time setup, recovery and evidence applicability.
The new runner has **not** flashed firmware or admitted RF. Its live adapters
remain unqualified until exercised on the prepared setup. No software or host
result is presented as physical LED/RF acceptance.

## Changes and checks

- Sixteen reviewed cases, eight candidate roles and durable at-most-once RF
  accounting. Every ambiguous admission consumes its reservation; no RF retry
  or resume. The packet charges 469.184002784 seconds against 18/600 seconds.
- Identity/boot/source/image/engine/system-clock/pin binding; root-level device
  user inspection, stable per-board locks, serial-selected ROM operations,
  full-flash snapshots and actual journal CRC/sequence/pin validation.
- Ordinary inhibited restoration with original journals/settings, byte-checked
  full readback and independent cleanup attempts on both boards. Console now
  exposes JobService owner/job authority for cleanup with LAN/time unavailable.
- Finite independent SDR and FFV1 video captures with frame/sample readiness,
  stream liveness, process teardown, duration/count/identity/settings/hash
  checks and preserved private evidence. Physical review remains pending.
- Acceptance commands absent from ordinary builds. External selection remains
  TX-only; AP/Identify retain the onboard output. Actual controller cues,
  checked ON-write rejection, one finite standalone schedule and actual STOP,
  and one inhibited 250 ms open-drain stimulus are isolated in labeled images.
- Full host suite: **155/157 passed**. The two failures remain the independently
  reproduced pre-existing `capacity_pending_tests` and `load_reply_tests`
  documented in the prior [LED review](phase13-1-transmit-led-review.md).
- Affected CTest group: **7/7 passed**. Runner tests cover the complete successful
  suite, schema-valid jobs, durable charging, edited/typed packets, identity and
  pin mismatch, active/owned preflight, changed boots, clock unavailability,
  capture startup/mid-run/final failures, live-but-stalled streams, ambiguous
  ARM, lease/fixture failure, premature completion, uncertain restoration,
  Plain LAN selection and network-independent Console cleanup.
- ASan/UBSan: **5/5 passed** for indicator/field/PIO/worker paths, then **2/2
  passed** for changed standalone/acceptance paths. Normative WTP validation
  passed (23 schema, 7 raw JSON, 1 framing, 8 transition cases).
- Eight worktree candidate roles cross-linked and passed actual linked-image,
  storage/UF2/stack and acceptance-symbol checks; ordinary platform link-check
  passed. Final clean-commit candidates are built by the same script after the
  commit; their generated manifest and logs stay ignored under `build/`.
- Changed Python syntax, C++ formatting and whitespace checks passed. Retained
  SDK/picotool sources were reused; no SDK/tool installation was introduced.

## Adversarial iteration

Candidate preparation also forces the 138 MHz/3.5701 MHz profile and clears
all unrelated fixture cache options, preventing a retained diagnostic cache
from becoming an ordinary restoration image.

First assessment targeted ambiguous admission, owner/lease races, budgets,
cancellation, capture startup/exit and restoration. Repairs included atomic
private ledger writes, preserving the primary case failure, charging before
ARM/SCHEDULE, no retries, both-board cleanup, and correct handling of Failed
state lease expiry. Behavioral failure cases and successful stages passed.

The next assessment found and closed these actionable issues:

1. Consumer profiles cannot use ordinary USB WTP. Add their supported identity-
   bound Plain LAN path; retain USB for engineering profiles and leave access
   policy intact. Add an adapter selection test.
2. Cleanup depended on LAN/time and camera availability. Expose actual Console
   owner/job fields; make recovery require only the frozen inhibited image,
   original backups and verified flash tool. Test unavailable-LAN cleanup.
3. Separate Console/WTP observations could straddle a normal transition.
   Prefer authoritative new Console status, and resample the legacy pairing
   within a finite bound. Permit at most one second for foreground status to
   reconcile independently completed hardware, without counting inactive
   Running as RF activity. Test both transitions.
4. Actual scheduler STOP releases to Empty, rather than retaining Aborted.
   Assert empty/unowned/inactive authority after STOP and disable the temporary
   schedule. Bind normal scheduler status to actual owner IDs in C++ tests.
5. Repeated cues could be refused, typed JSON equality admitted integer RF flags,
   and completion could occur prematurely after one Running sample. Separate
   pre-TX AP and active/post-TX Identify, compare canonical typed packets and
   enforce a conservative software completion interval.
6. A process could remain alive with stalled media, and capture teardown errors
   could bypass final accounting. Require both streams to progress, verify
   video frame/time coverage, retain teardown failures and write STOP state.
7. The GPIO release timer could race delayed activation. Mask interrupts around
   low activation/timer installation; release input immediately on allocation
   failure. Keep one hold per boot and default-off inhibited-only linkage.

A subsequent assessment of the repaired source, evidence authority, bounds,
crash recovery, selected/operational separation, process cleanup and restoration
found no remaining actionable source finding in this slice. Affected tests were
rerun. Electrical stimulus, ordinary network AP operation, optical recording
and independently synchronized RF/LED edge timing remain physical applicability
limits, not source-test passes.

## Actual hardware actions and execution boundary

Read-only existing-tool inventory on wspr5 confirmed:

| Board | USB serial | Device | Installed revision | Boot | Console state |
| --- | --- | --- | --- | --- | --- |
| A | `0BF4B4AEC9FFB344` | `fd6127d11d6aca42a9905fa3fb1bf1d5` | `6c7b14321003` | `85e164b089a940450aaf38035612df63` | Inhibited, empty/inactive, schedules disabled |
| B | `CDDBF8767C506C07` | `29f20b7342051ef947aa56cb9d4fab42` | `58afb2735c23` | `4345b097ce98a6889fcb42498c943386` | PIO GP2, empty/inactive, schedules disabled, safety latch retained |

Both report consumer-preclock profiles, ordinary Plain LAN mode/port 31417,
station link up and unsynchronized clocks. Fresh accepted time is a finite
run prerequisite; no stale clock is accepted for ARM. Existing Console inventory
did not expose WTP owner IDs; the new source fixes that diagnostic gap. No
firmware, GPIO or journal change was performed and no restoration was needed.
The retained SDR helper, FFmpeg and picotool executable hashes were inspected.

Automatic approval review rejected the attempted transfer of a new source
bundle to wspr5 and execution with elevated permissions: it did not find
specific authorization to export that payload to that destination. The rejected
command did not execute. Local checks and already-present read-only tools were
used; no indirect transfer workaround was attempted. This tool-policy export
boundary is separate from the user's RF/USB authorization and the repository's
connected-device rule. New-adapter live inventory is therefore deferred pending
that transfer permission. Step 2 still groups the normal operator setup.
