# Repair the Package 2 LOAD allocation failure

## Objective and baseline

Execute in /Users/lbussy/GitHub/WsprryPico on devel, baseline a6a564d.
Read README.md, CONTRACT.md, docs/architecture.md and the development guide.
Preserve existing work and all failed evidence. Complete reproduction, focused
repair, adversarial review and repairs, affected validation, separately frozen
physical packets, independent raw audits, restoration, commit and push with
independent remote verification. No other repository may be modified.

Close P2-LOAD-20480 only with repaired source and target evidence. Close Package 2
assertions 2.2a/2.2b only if supported overlap and separately declared overload
meet all original gates. Preserve P1/R1/R2 recorded evidence and assess source
impact; do not promote historical results to a new firmware identity.

A is Pico 2 W / RP2350 Arm, serial 0BF4B4AEC9FFB344, device
fd6127d11d6aca42a9905fa3fb1bf1d5, source 8dd6f0812292e9264c2a72745078a95ee606c191,
recovery boot 4768a88991247131bdc7c0fc421dbe8f. B is CDDBF8767C506C07,
device 29f20b7342051ef947aa56cb9d4fab42, source 8921a7008183,
boot 6684b4b197d80cfa0ce83b3aaf205cb0. Verify live before device changes.
Both were independently Empty/inactive/unowned with schedules disabled, the host
fixture restored and shared reservation released. A's recovery disables network;
its volatile history was lost. Persisted configuration fields survived.

## Evidence and reproduction

Frozen failed packet d5d9b1a813909e3f880084887cf7962bbe7a12b76944cf3d73d9367d88f46c9d
at /home/pi/phase11-5-p2-supported4-20260915 records a 52,105-byte LOAD, no ARM,
a 20,480-byte null allocation, USB-stage watchdog recovery, and zero capacity
stimuli. The request matches a 512-event array. Both codec decoding and service
copying allocate that size. The exact target caller and fragmented versus peak
occupancy cause are unproven; do not claim a desktop model proves them.

Review raw-frame, decoded-job, service-copy, RF-preparation, adjustment-response,
retained-history and native TLS lifetimes. Reproduce the large-block dependency
in production decoding using deterministic host allocation constraints. Exercise
sufficient aggregate space with a maximum contiguous block below 20,480 bytes,
and separately inject nullable allocation failures. If caller ambiguity prevents
a repair decision, use a narrowly scoped nonallocating target stage marker and
one bounded non-RF diagnostic packet rather than arbitrary traffic retries.

## Repair requirements

Prefer bounded paged event storage if reproduction supports that choice. Keep
job content, event ordering, typed digest, replay behavior and RF timing unchanged.
Cover both decoding and the accepted service copy. Page allocations must use a
nullable allocation path and free partial preparation. Failed storage must be
explicitly observable and rejected before job/owner/execution state changes.
No incomplete event list may be accepted as a shorter valid job. Audit all event
producers and copies, including browser message compilation and standalone WSPR.
Preserve ordinary value semantics and release after acknowledged independent RF
handoff. Keep the 32,768-byte reserve and existing response/observation deadlines.
Use the existing defined protocol refusal; do not invent a new WTP error code.
A refusal does not count as successful supported capacity.

## Host validation and adversarial assessment

Test the old contiguous dependency, successful paged decoding under constrained
block size, failure on every page boundary, partial-allocation cleanup, failed
service copying without mutation, malformed input, valid replay, conflicting
replay, retained histories, move/copy independence, and repeated release cycles.
Exercise production endpoint/service/RF preparation, not only the container.
Verify byte-identical event/digest/waveform behavior and unchanged ownership.
Run affected checks, sanitizers where configured, and the full available host
suite for this shared representation change. Build and inspect the four current
layout variants using existing pinned dependencies. Fix actionable findings and
reassess until none remains in the implemented slice. Record residual limits.

## Bounded physical execution

Use September 15 standing authorization and only named wspr5/A/B. Freeze each
packet before execution, never modify or reuse consumed packets. One shared RF
reservation prevents simultaneous A/B RF. Preserve management interfaces,
permanent host configuration, installed WsprryPi and physical RF path.
Copy public helpers only; reference original private INI/credentials in place
with hashes. Raw authenticated evidence stays on wspr5 or ignored local build;
only sanitized results/hashes enter Git.

Deploy one reviewed clean-source image to A after independently verified
inactivity: one BOOTSEL/flash, zero configuration saves, exact image/source/hash
and same selected 138 MHz/divider 1/GP2 PIO-DMA/RAM/listener configuration.
Read both boards independently after deployment. Do not update B without a
specific source-impact reason. Establish one new isolated fixture, at most
90 minutes execution plus 15 minutes cleanup, independently supervised and never
extended. Each dependent packet must fit the remaining restoration allowance.

First run a bounded non-RF LOAD/replay test with the actual native observer and
retained maximum jobs; reproduce the prior retained-state context as far as
possible without claiming identical lost heap geometry. Then independently
accept one 512-event, 128-second FSKCW job at 135,500/135,495 Hz with a resident
32,768-byte valid WTP payload overlapping small authenticated HTTP. Withhold the
last WTP byte until the complete HTTP response, bind residence to fresh raw INFO,
and preserve five-second WTP completion, native continuity, RF counters and reserve.
Only after its independent PASS run a separate 128-second overload packet with
the same resident WTP input plus a declared 32,768-byte HTTP body, header only,
expecting HTTP 503 resource_exhausted and authenticated recovery. Freeze a revised
combination only if source/evidence proves the original prediction inapplicable;
never relabel failed supported input as overload. Initial RF allowance is two
jobs/256 planned seconds. Additional packets require a recorded concrete repair
or diagnosis under standing limits, never arbitrary retries. Each flash packet
permits one flash/BOOTSEL; each readiness recovery must have concrete diagnosis
and a separately frozen count. Default saves, probes and controlled reboots zero.

## Acceptance and publication

Raw audits must reconstruct frames/CRC/schema, complete responses and deadlines,
actual overlap, peer/device/boot/owner identity, preserved configuration,
retained state, continuous independent RF/native observation and final inactivity.
Alter raw evidence to test rejection, then reassess intact evidence. Distinguish
source tests, target functional evidence and RF acceptance. Restore the host and
freshly inventory both boards; disconnect or process exit never proves RF off.
Record actual budgets, image identities, failures and limits in a durable review
and result. Update only affected matrix/current summaries. Commit and push the
reviewed source/helpers/tests/docs, independently verify remote SHA and clean
state, and report exact closure or the unresolved evidenced blocker.
