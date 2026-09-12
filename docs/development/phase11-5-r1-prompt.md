# R1 execution prompt

Execution disposition: [R1 remains blocked](phase11-5-r1-review.md). The preserved
packets record failed attempts, not reusable launch instructions. The current
executor additionally checks native-client DNS before board mutation.

Implement and execute only Phase 11.5 family R1, coordinated in WsprryPico on
devel, with scoped production-load tooling in WsprryPi on devel. Preserve all
historical failures. Review and repair actionable findings, repeat adversarial
assessment, commit and push the reviewed changes, and report actual results.

Use firmware e20ae8bea2d5237af017dbd5f73bfe9332ce144e, reusing the four exact
network off/on inhibited/physical ELF/UF2 pairs recorded in the STATUS-delivery
result. Physical acceptance is for 138 MHz, divider 1, RAM renderer; inhibited
150 MHz is a shared-path regression only. Other physical clocks remain untested.
Do not change firmware or start R2-R6. No RF jobs are part of this packet.

Score these assertions independently:

1. R1.1: verify all four artifact identities, linked memory/flash layout, allocator
   hooks and stack guards. Review the changed CYW43 call path, its 2,120-byte
   linked frame, and both 16 KiB stacks with enforced 4 KiB reserves.
2. R1.2: run a short inhibited regression of the changed shared network path:
   180 seconds of production idle control and normal browser actions, with
   240 seconds of independent USB/host observation. Report whether credit waits
   actually occurred; retain source regression evidence for untriggered paths.
3. R1.3: on the physical image, warm with the same 180-second workload. Establish
   the largest successful necessary request before deliberate probes. While
   authoritatively idle/unowned, probe that size, linked capacity plus one byte
   (expected allocation failure), then the necessary size again. Require exact
   outcomes, one intentional failure, no boot/guard/authority error and released
   allocations. This supplies a supported lower bound for allocatable block
   size, not an exact largest-block or all-workload fragmentation claim.
4. R1.4: in that same physical boot, observe Q360, controller-only180, N300 and
   Q360. Q uses the same persistent observer session; compare final post-expiry
   windows with equal empty terminal histories and warmed network state.
   Retained allocation difference must be within 1,024 bytes. Allocation failures
   must remain at the explicitly admitted post-probe baseline.
5. R1.5: report allocator sampling time deltas/fractions, maximum entry/sample
   times, core-0 scan and core-1 probe costs, USB request latencies and host load.
   Do not sum overlapping maxima or call canaries exact stack-pointer maxima.
   Instrumentation remains enabled in the accepted image; its observed cost must
   coexist with all declared service and resource limits. RF timing cost remains R2.

Implement N as sequential page plus capabilities/status/config initialization,
six distributed explicit Refresh actions, and one page reload with initialization.
Freeze exact action offsets for 180/300 seconds. Record action start/finish and
constituent raw responses. Preserve legacy S unchanged. No config writes through
the browser. Actual WsprryPi owns its one persistent WTP session and idle policy.
Require at least seconds minus two nominal STATUS requests, maximum 2-second
start gaps, native-write-entry responses within 5 seconds, each fresh HTTPS
request within 15 seconds, and completion of every scheduled action. Independently
audit raw USB/WTP/TLS records; missing/late actions are failures, never skipped.

Keep INFO 1 Hz (gap <=2 seconds), USB STATUS and host health 0.2 Hz (gap <=6
seconds), 32,768-byte heap reserve, exact guards and zero unexpected faults.
Do not transfer metrics across boots, count TLS separately from its parent heap,
or let probe high-water values masquerade as ordinary workload demand.

Use serial-specific Pico A 0BF4B4AEC9FFB344; Pico B CDDBF8767C506C07 is read-only.
Use a fresh private wspr5 root, exclusive USB handles, independent supervision,
original inhibited image/config restoration, and carried counters (22 config
writes before this packet; two further writes expected). Preserve installed
WsprryPi, Ethernet, wlan1 and GPSDO. Prepare a separately authorized isolated
wlan0 AP/wlan2 client fixture with a temporary chrony ACL and paused recovery
timer. Budget 45 minutes for device work plus 10 minutes guarded restoration;
host fixture 70 minutes plus 10 minutes cleanup. Expected execution is about
35 minutes; bounds are independent cleanup deadlines, not soak durations.

Stop dependent tests on unexpected failure. Preserve fault/unknown-output state;
do not auto-retry, reboot or erase evidence to continue. Guarded device restoration
requires authoritative admission; host cleanup remains independent.

Validate changed tooling using hardware-free positive and adversarial cases,
including profile confusion, omitted actions, malformed identity, changed images,
unexpected allocation counts, unequal quiet state and missing raw evidence.
Record exact helper hashes separately from unchanged firmware identity. After
execution reproduce the raw audits locally, review all five assertions, publish
pass/fail/not-run counts and restoration. Close R1 only if every assertion passes;
R1 alone cannot populate the accepted RF configuration list or close Phase 11.5.

Documentation impact: update this packet, the R1 result/review, acceptance ledger
and both development indexes/review pointers. No operator deployment workflow
or documentation in a third repository changes.

The fresh attempt following user-confirmed between-campaign reboots used a
40-minute device bound within the original host fixture deadline. Actual action
offsets and the admitted workload/service limits are recorded in the R1 review.
Both attempts were preserved; no deadline was extended.
