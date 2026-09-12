# Focused STATUS delivery repair prompt

Address only the intermittent WTP STATUS reply delivery failure captured by
N1z. Execute this prompt, review the implementation adversarially, fix actionable
findings, repeat affected checks, commit and push the scoped result, and report
both verified behavior and unresolved target gates.

## Baseline and exact failure

Work in `/Users/lbussy/GitHub/WsprryPico`, initially clean `devel` at
`f3b9d9648156c93ab9d428aa9381aa370d3af355`. WsprryPi is an independently owned
companion checkout; prior scoped editing/commit/push authorization is recorded,
but change it only if this defect requires a Pi-owned change or companion record.
Read repository instructions and preserve existing work.

Use `phase11-5-single-attempt-result.json` and its hash-bound private evidence.
Exact Pico firmware is `4058d3a4a95110326006a7db6e37eb4b562a500c`; production
client is `6f65d5c7d202569102459ab68d7c9ea079b96f35`. N1z passed the complete
150 MHz inhibited A2 matrix, then failed 138 MHz physical-image conditioning
with RF idle: 177 nominal STATUS requests versus minimum 178, maximum request
start gap 2,684,961,482 ns versus 2 seconds. STATUS replies ending `6b` and `a9`
took 2.581 and 2.470 seconds. USB and browser checks passed. Physical A2 and A3
were not run, and no RF jobs were submitted. Preserve all prior failures.

## Investigation and implementation

1. Follow the exact pinned lwIP/CYW43 source from TLS queueing through bus output.
   Distinguish bytes accepted into the TCP queue, successful driver submission,
   radio delivery and acknowledgment. Do not label the ignored `tcp_output()`
   return value as the cause without evidence; never repeat `tcp_write()` for
   bytes already accepted.
2. Reproduce any discovered defect using the actual pinned source with mocked
   bus/credit inputs. Initial source inspection identifies a specific candidate:
   `cyw43_sdpcm_send_common()` can poll incoming packets into `spid_buf` after
   the outgoing Ethernet/control payload has already been built there.
   Demonstrate whether the subsequent bus write sends altered bytes while
   returning success. Exercise credit rollover, incoming data/events, no-credit
   timeout and ordinary output as relevant to the supported repair.
3. Implement the smallest maintained repair. Keep external SDK checkouts clean;
   use the repository's pinned generated-overlay convention if the defect is
   upstream-owned. Verify source revision/hash and exact patch anchor, preserve
   upstream licensing, and fail closed on incompatible source. Do not update
   dependencies or change TCP/USB/browser acceptance thresholds.
4. Keep the remedy bounded in memory, stack and runtime. Account for callback
   reentrancy and aliased control inputs. Add allocation-free diagnostics only
   where needed to identify the defect or verify the repair; avoid continuous
   additional USB trace reads during the measured workload.
5. Run deterministic regression tests and affected host checks. Build the exact
   target candidate with installed, pinned tools and verify linked resource
   limits. Source/host success is not target or RF acceptance.

## Target validation and authority

Continuing explicit flashing/USB/RF authority is recorded, and SSH must run
outside the sandbox. No RF job is needed for this issue. Before target work,
freeze exact artifacts, board/boot identities, the bounded diagnostic and cleanup
limits. Reuse existing wspr5 credentials locally; do not transfer private keys.
Previously completed network fixtures are not reusable authority windows. Any
new fixture must have explicit authorization for its concrete bounds; prepare
and validate the packet before requesting any missing authorization.

Use Pico A USB `0BF4B4AEC9FFB344` and keep B `CDDBF8767C506C07` read-only.
Last restored A boot is `5b1ae867c8b6888a7a671b7170d66aba`; B is
`4e2fb851c08b278dd4b977104d2c2aaa`. Verify live state before mutations. Preserve
wspr5's installed service, Ethernet management, wlan1 and GPSDO settings.
A short targeted nominal controller/browser interval at the selected 138 MHz
clock may validate the remedy; do not launch full A2/A3 or the remaining phase
matrix as part of this issue-only task. Stop dependent actions at a failure,
preserve evidence and restore only after authoritative safe admission. Keep
independent host/device cleanup and cumulative write budgets.

## Review and completion

Adversarially assess byte preservation, duplicate/lost submissions, error/timeout
semantics, reentrancy, memory/stack costs, source-pin enforcement, diagnostic
observer effects, restoration and evidence claims. Fix supported findings and
rerun affected checks until no actionable finding remains in the scoped change.
Do not conceal a remaining target gate or declare an unproven mechanism proven.

Publish the exact failure, reproduction, repair, tests, artifacts and limitations.
Phase 11.5 still accepts resources/contention only at selected clocks; Phase
11.6 owns per-band/mode conducted RF acceptance and Phase 13 systematic
band/mode/clock/spectral qualification. No new clock or phase closure is implied.
Commit and push only scoped source/tests/development documentation; no raw
captures, private credentials, generated firmware or SDK checkouts. Verify clean
working trees and live remote parity, and report the next unresolved step.
