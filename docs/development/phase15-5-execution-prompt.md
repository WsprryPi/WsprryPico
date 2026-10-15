# P15.5 execution prompt

Work on `devel` in WsprryPico. This prompt is authorized for execution, review,
repair, validation, commit and push. WsprryPico leads: its port-80 bootstrap and
Consumer-Radio server owns a single TCP/parser/reply state. WsprryPi consumes
that service; its completed P15.3/P15.4 implementation is a compatibility boundary.

## Orientation and scope

Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md,
docs/development/README.md and the P15 checklist. Inspect status and recent
commits in both repositories, preserving unrelated changes. Start from Pico
`36aca3612af1066d6aed182e303b6f742b70de22` and inspect the accepted Pi
`50097e652b4af70d510f4a29d4edf1ffa24d3f0a` implementation. Review
bootstrap_server, the engineering TLS server, ConsumerRadioApi, HTTP storage,
main-loop admission and setup delivery callbacks before editing.

P15.1 revision checks, P15.2 capabilities, P15.3 management carriers and P15.4
shared-resource behavior remain authoritative. Preserve one local scheduler,
RF ownership, serialized configuration commits and uncertain-write readback.
Do not add another application coordinator or change WTP/JSON wire schemas.
P15.6 will increase authenticated session capacity; this slice must not silently
claim or implement simultaneous authenticated sessions. P15.7 login recovery
remains separate. Preserve the documented failed-save/session-busy reproduction;
no connected-device reproduction is authorized by this software-only setup.

## Implementation

1. Replace the singleton port-80 connection with two bounded cooperative
   connection tasks on core 0. Keep raw lwIP callbacks, crypto, application
   dispatch, storage and deferred effects on their existing single owner. RF
   servicing remains local on core 1. Use no blocking socket/thread waits or
   RTOS/core-1 network work. Explain this realization of the roadmap's
   "multi-threaded" concurrency intent accurately.
2. Give each task independent parser, response, offsets, interface, deadline and
   unique transaction identity. Reject excess connections predictably without
   evicting admitted clients. Keep one request per connection and reject
   pipelining. Enforce an absolute 10-second connection lifetime and bounded
   round-robin output chunks (at most 1024 bytes/task/poll). Retain bounded HTTP
   headers/body and shared paged-buffer admission. Release sensitive input and
   response storage on all exit paths.
3. Keep per-interface admission and actual incoming-netif binding. Withdrawing
   one interface must not close an unrelated connection on the other. Drain
   admitted AP connections when new AP accepts close, subject to the deadline.
4. Tie delivery-dependent provisioning effects to the originating transaction.
   Complete delivery requires all response bytes queued and TCP-acknowledged;
   FIN alone is not delivery. An unrelated close/ACK/request cannot acknowledge,
   cancel or delay another request's setup action. Serialize setup receipts and
   preserve owner-status commit evidence until that receipt finishes. Do not
   allow idle/partial connections to indefinitely postpone a delivered trial or
   restart. Keep competing WTP admission closed when setup is pending.
5. Keep existing engineering HTTPS capacity and single-session consumer
   semantics. Test phone/Mac-equivalent overlapping transport activity without
   overstating target, browser or authenticated multi-session acceptance.

## Validation and adversarial closure

Add deterministic tests against the actual transport implementation with lwIP
boundary doubles: slow/partial upload, stalled output/ACK, capacity rejection,
round-robin bounds, malformed/pipelined input, disconnect/timeout/error cleanup,
interface withdrawal, allocation pressure/reclamation and transaction isolation.
Exercise actual setup receipt/dispatch branches, including deferred mutation and
restart evidence, with regression tests. Run the complete documented Pico host
suite and contract validation in retained Linux tooling, affected ASan/UBSan,
and cross-link both RP2350 firmware images with the pinned SDK. Do not compile
Pi C++ on macOS. Do not install dependencies, flash boards, operate GPIO/RF,
change installed services, or modify another repository incidentally.

After implementation, conduct an adversarial assessment focused on cross-client
state contamination, ACK/FIN/error races, resource starvation, stale interface
contexts, setup cancellation, commit ordering and source/test gaps. Record
findings and repairs; rerun affected checks and reassess until no actionable
software findings remain. Be explicit that this is an adversarial review pass,
not independent third-party or physical qualification. Preserve failed attempts.

Document exact commands/tool versions, source identity, resource budgets,
compatibility boundaries and remaining physical concurrency/RF qualification.
Update the roadmap and development index honestly. Commit only scoped files on
`devel`, push to `origin/devel`, and independently verify remote parity. Report
changes, validation, review results, limitations, commit and repository state.
