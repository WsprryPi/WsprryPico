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

A final delay-focused assessment reproduced an erroneous RENEW after a slow
GP14 response had cleared ownership. Stop renewing once the stimulus is sent;
verify the actual safety latch and terminal inactivity instead. Also renew
between preparation RPCs with a finite 20-second lease/22-second cleanup
allowance, account for GET_CLOCK response age in the future ARM
target, reassert finite AP cues while Running and leave a finite 90-second
capture allowance for control overhead. Keep the bounded ON-write rejection
active for 80 seconds so slow preparation cannot outlast the intended fault. Slow fixture and 2.5-second transport
response regressions now exercise the actual orchestration. Rebuild candidates
against the repaired clean commit before final use.

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
connected-device rule. The user subsequently approved that exact bundle's
transfer and read-only inventory. The continuation below supersedes the pending
transfer disposition. Step 2 still groups the normal operator setup.

## Approved live inventory continuation

The approved 13-file archive from commit
`2c2fac40c7cb3778f4194e2db0c7d4841e5b45c3` was transferred to
`/tmp/phase13-led-step1-2c2fac4-20261007` on wspr5. Its archive SHA-256
`00a83f1609cd3e57e611b87357c9af941dd01c080e2234fef8a624ede0101ae6`
and every extracted source-file hash were verified before execution. The exact
approved runner was executed first for A/B, then separately for B because the
original inventory stopped at A's unavailable WTP handshake.

| Board | Observation UTC, 2026-10-07 | Installed revision | Boot | Console result | LAN WTP |
| --- | --- | --- | --- | --- | --- |
| A | 15:39:26 | `6c7b14321003` | `85e164b089a940450aaf38035612df63` | Inhibited, empty/inactive, schedules disabled | Not ready, unsynchronized; HELLO connection reset |
| B | 15:44:13 | `58afb2735c23` | `4345b097ce98a6889fcb42498c943386` | PIO GP2, empty/inactive, schedules disabled; safety latch retained | Not ready, unsynchronized; HELLO connection reset |

Device/serial identities match the preceding table. Both clocks had expired;
the existing station LAN gate correctly rejects unsynchronized connections.
There is no CAPS/GET_CLOCK/STATUS result from either run, and the installed
legacy Console does not expose owner/job IDs. Do not infer unowned authority,
live WTP qualification or physical LED acceptance from these observations.
Zero RF jobs were submitted; no firmware, settings, GPIO or clock changes were
performed. Original installed revisions and boots were observed on both boards.

Private evidence stays ignored under `build/phase13-led-reviewed-runner/`:
`inventory-summary.json`, both process logs, and the unmodified remote evidence
archive `inventory-approved.tar.gz`, SHA-256
`095db515c2affcd5dc6517c86cb8cc281f19c4ada827ec698a9a8a650db60d2b`.
The remote original state files retain PREPARING, demonstrating the old failure
reporting gap; the derived summary explicitly records Console-only evidence.
No capture or generated firmware is committed.

The live failure prompted a bounded repair: attempt and retain every named
board's inventory, record unavailable transports and cleanup failures durably,
return exit code 2 for partial results, check consumer readiness before opening
LAN, and bind complete results to matching device/boot/engine observations.
Inventory uses only INFO and HELLO/CAPS/GET_CLOCK/STATUS/PING; normal RF
preflight continues to reject unknown owner authority.

Adversarial review then found two related cleanup issues: a failed HELLO could
cache an unverified peer, and a failed evidence write after opening a transport
could leak it. Register the context before emitting its event, close it on every
construction/handshake failure, and cache only an identity-checked peer. Also
record interruption as partial and preserve the primary cleanup error. New
tests cover both unavailable boards without fabricated owner IDs, boot mismatch
with continued B inspection, occupied locks, cleanup failures, interruption,
failed HELLO, uncertain close retry and evidence failure after opening LAN.
**26 runner tests passed**;
the affected CTest group passed **7/7**, and normative WTP validation passed.
Offline packet generation and whitespace checks also passed. A second review
found no remaining actionable issue in this reporting/cleanup slice.

The repaired 13-file worktree archive was staged at
`/tmp/phase13-led-step1-reassessed-20261007`, but automatic approval review
rejected its verification/execution because the user's approval named the
original archive, not the modified payload. That rejected command did not
execute; no indirect execution workaround was used. The repaired live rerun
therefore awaits approval of its final reviewed bundle. Fresh accepted time is
also required for complete consumer WTP inspection and later RF preflight;
inventory does not repair SNTP or alter the station setup. Steps 2–6 remain open,
with only step 2 normally requiring an operator.

The later [step-2 preparation record](phase13-1-step2-review.md) supersedes the
read-only inventory deferral: guarded original-image reboots restored fresh
time, and the publicly published repaired diagnostic subset completed both-board
inventory after automatic approval review accepted the new public-source
evidence/current step-2 authorization. The rejected private worktree archive was
not executed as a workaround. Physical wiring/recording and steps 3–6 remain open.
