# Phase 11.5 Package 5 execution and adversarial review

## Outcome

Package 5 is **COMPLETE**. `R3.RETAINED.replay`,
`R3.RETAINED.session`, `R3.RETAINED.terminal` and `R3.RECLAIM` are accepted.
The continuation preserved the earlier replay/session and terminal-capacity/LRU
passes, replaced the invalid reclamation comparison with three equivalent
post-quiet cycles, and executed the real terminal expiry.

The machine-readable [result](phase11-5-package5-result.json) binds the accepted
and failed evidence. The [continuation prompt](phase11-5-package5-continuation-prompt.md)
was executed within its amended finite allowance. Package 6, R3 family closure
and Phase 11.5 closure remain open.

## Fixed image and prior accepted evidence

The continuation used Pico A source
`2b25ca05c270819466a04498f9bc4894a4c5bace`, UF2
`16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`
and unchanged boot `80d558e5804547749eca849c53ba27e1`. Pico B remained the
unchanged comparator. No continuation flash, reboot or configuration write
occurred.

Replay and session acceptance remains based on packets `2039a76...` and
`df03ad8...`: exactly sixteen sessions, a bounded seventeenth-session `BUSY`,
eight replay entries, exact replay/conflict/LRU behavior and real 360-second
expiry/reuse. The later LOAD ownership repair does not change those paths.

Terminal capacity/LRU remains based on packet `ed7db2e...`: nine actual
one-second Tone jobs established capacity eight and the intended touched-entry
ordering. The failed later packet `0e959b6...` remains a failure: its LOAD reply
took 7.666 seconds, exceeded the five-second gate and inserted an aborted
terminal record. The continuation did not convert that packet into credit.

## Equivalent-state normalization

Packet `78b7a9...` completed eight distinct one-second FSKCW jobs. Every job had
exactly 512 alternating 135.500/135.495 MHz events and traversed CLAIM, LOAD,
ARM, Running, Complete and RELEASE. The raw audit observed eight RF jobs and
eight seconds, exact final ordering, complete/inactive records, zero allocator
or TLS failures and unchanged image/boot identity. This evicted the contaminated
aborted record while making all retained terminal histories maximum-event
histories.

Quiet packet `c4f8469...` then ran 360.096 seconds with thirteen Console INFO
and host-health samples and no WTP/HTTPS application traffic. Its isolated
audit result hash is `e5ea9cf...`. The normalized live allocation was 36,840
bytes; allocator live allocation was 42,992 bytes; heap capacity was 218,840
bytes and the observed allocator peak was 175,872 bytes.

The first quiet attempt stopped before its interval because it expected WTP
owner/job fields in Console INFO. The initial offline auditor then used stale
event names. Both harness defects remain recorded. The unchanged successful
capture passed the corrected isolated audit.

## Three equivalent reclamation cycles

Packets `05573ec...`, `417ddd2...` and `e1e8428...` each ran one 512-event,
128-second FSKCW bounded-overload job. Each raw audit verified:

- 32,784 resident direct-WTP bytes;
- authenticated HTTP `503 resource_exhausted` with no offered body;
- complete WTP exchange within the unchanged five-second deadline;
- authenticated recovery, native continuity and Console authority;
- exact completion and final Empty/inactive/unowned authority;
- eight ordered complete maximum-event terminal records;
- zero allocator/TLS failures and valid stack guards.

After every RELEASE, a separate 360-second application-quiet interval captured
thirteen Console/host-health samples. The normalized/post live values were
36,840/37,088, 36,840/37,080 and 36,840/37,088 bytes. The three posts span eight
bytes, remain within the frozen 1,024-byte tolerance and do not grow
monotonically. The 42,968-byte observed reserve exceeds 32 KiB.

Aggregate packet `b082905...` returns
`PACKAGE5_THREE_CYCLE_RECLAMATION_VERIFIED`. The strengthened audit also binds
its staged files, the normalizer RF/audit predecessor, exact terminal-record
chain and the three quiet captures. Its result SHA-256 is `47be8dc...`.
`R3.RECLAIM` is accepted.

The prior functional cycles (`7878985...`, `fc55afc...`, `a536693...`) remain
valid overload evidence but receive no reclamation credit: their immediate
post values differed by 12,384 bytes because retained terminal content and
session/replay phase were not equivalent.

## Real terminal expiry

Packet `ffb4116...` froze the exact eight complete records after cycle three.
It collected 124 Console INFO samples through a 3,660-second interval. The HTTPS
trace contains no HTTP or status operation between the initial status response
and the fresh post-quiet HELLO. Every frozen record exceeded the device's
3,600-second source TTL.

The fresh mutually authenticated HELLO and final status completed in 3.190
seconds, within the fifteen-second gate. Final terminal records were empty and
authority remained Empty, inactive and unowned on the same Pico boot, with
zero allocator/TLS failures and valid stack guards. A post-audit sticky host
health observation retained host boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`,
`throttled=0x0` and installed WsprryPi PID 1957. The strengthened audit result
hash is `dc79fa3...`. `R3.RETAINED.terminal` is accepted.

## Adversarial review and repairs

The first continuation assessment found three actionable audit gaps:

1. the reclamation aggregate did not bind its staged files or prove that the
   quiet normalizer descended from the accepted normalizer RF packet/audit;
2. the quiet auditor trusted the sampler's host checks without independently
   checking each recorded host boot and throttle value;
3. the terminal-expiry auditor excluded `http_*` traffic but did not also
   exclude `status_*` traffic, and only applied its full authority/resource
   checks to the final Console sample.

The auditors now enforce those bindings and every immutable capture passes the
strengthened checks. The second [adversarial result](phase11-5-package5-adversarial-result.json)
rejects all eighteen mutations: identity, normalizer event count and duration,
LOAD deadline, quiet duration and traffic, terminal type and order, resident
WTP, HTTP outcome, recovery, memory comparison, expiry, authority, reservation,
restoration, hardware charge and retained failure removal.

The documented host build passes after regenerating its expired ephemeral test
certificate, and the complete registered suite passes 75/75. The focused
Package 5 policy/publication suite passes six tests.

Non-RF staging failures remain visible in the result: an initial denied fixture
credential copy, an incomplete WiFi-recovery staging root, the two normalizer
quiet harness defects, shadowed Python modules during early cycle-1 audit
launches, and two incomplete strengthened-audit bundles. They stopped before
the affected acceptance operation and receive no credit.

## Hardware charge and restoration

The continuation consumed its full amended allowance: eleven RF jobs and 392
RF seconds, comprising eight one-second normalizers and three 128-second
reclamation cycles. It used one explicitly added Pico A WiFi OFF/ON recovery,
zero flashes, zero configuration writes and zero controlled reboots. Including
the original Package 5 work, the cumulative charge is 24 RF jobs, 913 RF
seconds, two WiFi cycles, three flashes, zero configuration writes and zero
controlled reboots.

One host-only fixture-timer extension changed no network or device state. Final
cleanup exactly restored the saved interfaces and routes, resumed the WiFi
recovery timer, removed the namespace and temporary units, retained installed
WsprryPi PID 1957 and reported no failures. The last authoritative device reads
show A Empty/inactive/unowned with no terminal records and B
Empty/inactive/unowned; the shared reservation is released.

## Remaining boundary

Package 5 is closed. Capacity/pressure and retention/reclamation execution
groups are complete, but the revised family count remains **2 of 6** because
R3 is not a family pass until Package 6 performs the complete assertion-level
closeout. No Package 6, R3-family or Phase 11.5 closure is claimed here.
