# P1 attempt 1: failed capacity exchange and preserved completion

**P1 and R3 remain OPEN.** The [immutable result](phase11-5-completion-p1-attempt1-result.json)
records the exact packet, helpers, board identities, charges and restoration.
No firmware changed. The 512-event FSKCW job completed locally after USB
observation failed; this does not pass the full capacity run or reopen the closed
idle LOAD/replay component.

## Findings and disposition

1. The individual WTP boundary probe overlapped an ordinary HTTPS request. Raw
   request/response timestamps establish the overlap. The Console sample
   48.94 ms before the WTP offer reported 78,456 available bytes. Current
   `FrameParser::feed()` requires 65,552 + 32,768 = 98,320 available bytes before
   growing this frame. Sampled state and source support admission refusal;
   there is no direct branch trace. Only 4,096 bytes were written, so neither
   full-frame delivery nor successful allocation can be claimed. Preserve this
   failed supported workload and score Package 2 separately.
2. A failed capacity operation left subsequent USB STATUS unresolved; the HTTPS
   observer stopped on stale authority. Independent Console and host observation
   continued to the frozen deadline. No retry, second ARM or cleanup RF was
   issued. Final raw A/B inventories confirmed inactive, unowned states before
   releasing the durable reservation. Process exit alone did not release it.
3. The nominal 20-second HTTPS schedule did not isolate individual transport
   maxima. Prepare a fresh packet that first completes maximum/oversize WTP with
   the persistent native observer, then starts the HTTP boundary sequence.
   Require raw evidence of that ordering. This changes the test workload; it
   does not turn this failed combination into a pass or expected overload.
   Combined supported/unsupported admission remains Package 2 work.

## Independent review and validation

The failure auditor verifies staged helper hashes, original request bytes/CRC,
LOAD/ARM acknowledgement, all 300 raw Console replies, same-boot launch/tail
counts, native authenticated wire evidence, partial-write accounting, exact
failure records, final identities/configurations and durable reservation state.
Private input hashes were read remotely; credentials were not copied into Git.
The ordinary success auditor cannot accept this failed packet.

Offline altered-evidence cases reject a fabricated complete write, a Console
summary inconsistent with raw bytes and a forged success result. Reservation
tests reject missing/foreign/active board authority and demonstrate that an
unresolved held record survives controller exit. All six new test methods pass,
including three altered-evidence subcases. The affected existing packet, fixture
and nominal-schedule tests passed before execution.

Post-restoration A/B inventories independently match the original observable
configurations and firmware/boot identities; both schedules are disabled. A's
old aborted record expired naturally by that inventory; its new Complete record
remains. Fixture cleanup has no failures, host interfaces/routes match baseline,
and temporary time.local state was independently compared with its baseline.
The installed WsprryPi PID/executable remain 1957 and the recorded SHA-256.

Reassessment: the failed attempt and final authority are supported. Individual
capacity acceptance and the complete-job multi-observer gate remain open. The
next executable packet requires its own offline review and finite budget.
