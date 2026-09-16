# Phase 11.5 Package 5 execution prompt

> Execution disposition: the bounded run is complete but Package 5 remains
> open. Replay/session rows pass; terminal capacity passes but expiry was not
> run; three functional reclamation cycles pass but the 1,024-byte comparison
> fails. See the [review](phase11-5-package5-review.md),
> [result](phase11-5-package5-result.json) and separately gated
> [continuation](phase11-5-package5-continuation-prompt.md). The criteria below
> remain unchanged.

Execute only Phase 11.5 Package 5 in `/Users/lbussy/GitHub/WsprryPico`.
Preserve every Package 1-4 result and every failed attempt. Do not claim Package
6 or R3 family closure.

## Objective

Close the current-image retained-state and reclamation rows:

- `R3.RETAINED.replay`: eight replay entries per session, exact replay,
  request-ID conflict, LRU eviction and real 300-second expiry;
- `R3.RETAINED.session`: sixteen logical sessions, normal reuse, intended
  seventeenth-session exhaustion and real 300-second expiry;
- `R3.RETAINED.terminal`: eight actual finite completions, LRU touch, ninth
  completion eviction and real 3,600-second expiry;
- `R3.RECLAIM`: three equivalent executions of the highest measured
  current-image resource path, with matched post-cache state and no retained
  growth.

## Frozen target and source limits

- Pico A: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, source
  `ca3c5dce40360b7eea2f9c45618232caa68cdbb6`, installed UF2 SHA-256
  `6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59`,
  boot `5e0d6bc3e383b8c1cb4b0db9ed636bf5`, 138 MHz, PIO divider 1,
  GP2 PIO/DMA, RAM renderer.
- Pico B remains the unchanged, independently inactive comparator.
- Current source fixes the capacity at eight replay entries per session,
  sixteen sessions, eight terminal records, a 300-second replay/session TTL
  and a 3,600-second terminal TTL. Confirm those values from the executed
  source and current protocol/CAPS evidence; do not substitute a shorter wait.
- The measured highest-resource current-image path is Package 2's bounded
  overload case: one complete 512-event, 128-second FSKCW job while 32,784
  direct WTP input bytes overlap a declared 32 KiB HTTPS body. The server must
  refuse the unsupported HTTP allocation with authenticated `503
  resource_exhausted`, preserve RF/owner continuity, complete WTP, then pass an
  authenticated recovery request.

## Boundaries and budget

Use one isolated retained-Wi-Fi fixture and one unchanged Pico A boot. Do not
flash, reboot, change configuration, cycle Wi-Fi or change the RF fixture.
Acquire the durable two-Pico RF reservation for every RF tranche. Planned
budget: nine one-second terminal-capacity Tone jobs plus three 128-second
FSKCW reclamation jobs, twelve RF jobs and 393 RF seconds. A harness repair may
replace only a case whose prospective criterion could not be evaluated; retain
the failed evidence and do not repeat a passing case.

During each 360-second replay/session quiet window and the 3,660-second
terminal quiet window, allow Console `INFO` observation and required host
health only. Do not issue WTP/HTTPS application traffic, change the fixture or
infer expiry from elapsed host time alone.

## Execution slices

### P5-A — replay and sessions

Begin with a real 360-second application-quiet interval so sessions and replay
entries from earlier packages cannot consume hidden capacity. Then use
authenticated HTTPS job requests with frozen session/request identities:

1. Admit exactly sixteen distinct `HELLO` sessions; require the seventeenth to
   return `BUSY` while a previously admitted session still accepts normal
   reuse.
2. Populate exactly eight responses in one session. Require an exact replay to
   return the byte-equivalent result and an altered payload with the same
   request ID to return `REQUEST_ID_REUSE`.
3. Touch the oldest entry, add a ninth response, prove the untouched LRU entry
   was evicted by accepting its altered payload, and prove the touched entry
   remains by rejecting its altered payload.
4. Start a second 360-second quiet interval at the last response. Afterwards,
   require valid non-HELLO operations on two old sessions to return
   `HELLO_REQUIRED`, then admit the formerly conflicting request ID and the
   formerly refused seventeenth session.

### P5-B — terminal capacity and LRU

With both boards independently inactive and the reservation held, run nine
distinct actual one-second Tone jobs. Each job must traverse CLAIM, LOAD, ARM,
Running, Complete and RELEASE; an aborted or missed job receives no capacity
credit. After completion eight, replay the full LOAD for completion one to
touch its terminal/retained record. Completion nine must leave exactly eight
records: completion one and completions three through nine. Completion two
must be absent. Preserve exact terminal ordering and timestamps.

### P5-C — three equivalent reclamation cycles

Run three fresh hash-bound packets, each reproducing the Package 2 bounded
overload path above. Keep source, image, boot, RF plan, fixture, TLS identities,
observer policy, terminal cardinality and start/end network/cache phase equal.
For every cycle require:

- complete finite RF with continuous independent native and Console authority;
- direct WTP residence of at least 32,768 bytes;
- bounded authenticated `503 resource_exhausted`, complete WTP response and
  authenticated recovery within 15 seconds;
- no allocator/TLS failure, valid stack guards and at least 32 KiB reserve;
- Empty/inactive/unowned final authority and exactly eight terminals.

Compare each cycle's matched pre/post and the three matched post-cycle `INFO`
states. Use live allocated bytes and retained cardinalities, not the sticky
peak counter. The post-cycle live allocation must not grow monotonically, and
the maximum difference between equivalent post-cycle states must be at most
1,024 bytes. Aggregate free memory alone is not fragmentation evidence.

### P5-D — real terminal expiry

After the final reclamation completion and RELEASE, freeze the exact eight
terminal records and start a 3,660-second quiet interval. At its end, issue one
fresh authenticated HTTPS `HELLO` and one status read. Require the terminal
list to be empty, the old current job identity to be cleared, and Pico A to be
Empty/inactive/unowned on the unchanged boot. Record the actual device
monotonic timestamps and demonstrate that every pruned record exceeded the
source 3,600-second TTL.

## Evidence and acceptance

Use new private evidence roots and hash-bound packet/helper manifests. Retain
raw HTTPS requests/responses, peer certificate hashes, WTP frames, Console
samples, RF/native observations, before/final inventories, reservation state,
fixture state and exact monotonic/UTC timestamps. An offline auditor must
reconstruct all capacities, LRU choices, quiet intervals, expiries, job
lifecycles, three workload overlaps, resource comparisons and restoration.

Mutation tests must reject altered source/image/boot, limit or TTL, identity,
quiet-window duration/traffic, replay/conflict outcome, terminal job/order,
RF lifecycle, combined overlap, recovery, live-memory comparison, final
authority and reservation/restoration state.

After capture, perform an adversarial review. Fix each actionable finding
without weakening a frozen threshold, rerun affected deterministic checks, and
repeat physical work only when the original evidence cannot satisfy the same
prospective criterion within the absolute budget. Perform a second adversarial
assessment. If all four rows pass, write Package 5 result/review artifacts,
update the completion matrix/progress/development index, mark only those four
rows accepted and keep R3/Phase 11.5 open for Package 6. Commit to `devel`, push
`origin/devel`, verify local/upstream/remote parity, and report exact checks,
hardware charge, restoration state, limitations and remaining work.
