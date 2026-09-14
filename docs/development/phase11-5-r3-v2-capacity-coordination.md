# Group 2 capacity and pressure execution basis

Group 1 is CLOSED at checkpoint 043. Group 2 is OPEN. This record now includes
C1–C4 and E5. Checkpoint 047 ends the bounded attempt OPEN. Older preparation
statements below are historical, not live fixture state.

## Checkpoint 047: bounded attempt ended OPEN

The sole diagnostic C4 was admitted once and reported `MISSED_START` before the
capacity trigger. Raw ARM acknowledgment, JOB_STATE/MISSED_START events, Console
launch epoch zero and both final inventories agree: zero launches, zero capacity
stimuli, zero capacity bytes and zero new allocator failures on this diagnostic
boot. The full 90-second ARM charge is retained. The original runner result stays
`STOPPED_FINAL_STATE_UNVERIFIED`; its admission helper excludes Missed even though
raw final STATUS is authoritative. A separate raw replay verifies Missed, inactive
and unowned. It does not turn the failed physical attempt into a pass.

The allocation defect remains unidentified. C2/C3's two failures remain attached
to their original source and boot. C4 provides no failed-allocation site to resolve.
No repair was selected, the archived parser refactor remains withdrawn, and no
replacement physical test or Group 3 work was attempted. The smallest next
decision is whether to authorize another bounded diagnostic period after reviewing
C4's launch/clock guard evidence and freezing one revised diagnostic schedule.
That decision must precede any further physical attempt or parser repair.

C4's ARM clock and first Missed sample differ in UTC-minus-monotonic offset by
25.805 ms. `StreamEngine::check_clock` can refuse launch after a clock refinement
that makes the armed mapping exceed the current uncertainty. This is a possible
explanation, not a demonstrated cause: the exact guard snapshot/rejection branch
was not captured. No timing threshold, guard or clock policy was changed.

### Final assertion disposition on diagnostic source 4da3672

E5 and C4 use source `4da36726ac6809bdf4e73d281fe13b2393dd3b31`,
UF2 `0153107c517b673bfad7850957c8387a7dbfb12ddb0a3b1e90edb94b804b9a9f`,
ELF `8855dd77cb0057ff8f33f91d02a3447cf39ca96cb2782b606c51f2e44e4f7353`,
boot `0bd82f1324920c360d796988cf31cb5b` on A, Pico 2 W/RP2350,
PIO/DMA GP2, 138 MHz/divider 1/RAM rendering. Historical identity keys and the
pre-change table below remain unchanged. No allocator or parser repair exists.
The diagnostic adds retained failure metadata and INFO output; host behavior is
covered, but physical resource/timing equivalence remains unestablished.

| ID | Status | Accepted component or exact remaining requirement |
| --- | --- | --- |
| 2.1a | PARTIAL | E5 revalidates 512-event admission; C1 completion remains accepted on its old identity. New diagnostic timing/resource equivalence is unproven. |
| 2.1b | PASS | E5 independently verifies 513 and overduration rejection plus exact maximum idle LOAD on the diagnostic image. |
| 2.1c | PARTIAL | Prior maximum-plan, hour and WSPR records remain; complete assertion-level source/resource reuse is not established. No repeated hour campaign. |
| 2.1d | FAILED | C2/C3 supported WTP maximum attempts failed at 4096 bytes. E5 idle passes; C4 sent zero capacity bytes. RF case unresolved. |
| 2.1e | PARTIAL | E5 verifies 65537 framing rejection and same-connection recovery while idle; RF case unexecuted. |
| 2.1f | PARTIAL | BF4 exact HTTP maximum remains B-only evidence; A under-RF valid 32768-byte API body unexecuted. |
| 2.1g | PARTIAL | BF4 B HTTP limit/recovery retained; A under-RF 32769 rejection and authenticated recovery unexecuted. |
| 2.2a | FAILED | C2 supported simultaneous allocation failed. No final workload/overlap allocation succeeded. |
| 2.2b | NOT_RUN | Intended unsupported allocation, preserved owner/RF and authenticated recovery missing. Failed supported input is not overload acceptance. |
| 2.2c | PARTIAL | T4 TLS handshake timeout/reuse retained on its identity; diagnostic resource applicability unproven. |
| 2.2d | PARTIAL | T5 failed-alert ACK/unacknowledged lifetimes retained on its identity; diagnostic resource applicability unproven. |
| 2.2e | PARTIAL | T4/T5 slot, one-WTP and pending mechanisms retained; diagnostic resource applicability unproven. |
| 2.2f | PARTIAL | T5 HTTP header/body/stalled reader retained; diagnostic resource applicability unproven. |
| 2.3a | NOT_RUN | Distinct 30-second drained WTP inactivity, closure and authenticated reuse absent. |
| 2.3b | NOT_RUN | Five-second incomplete-input mechanism and recovery absent physically. |
| 2.3c | NOT_RUN | Five-second no-output-progress mechanism and recovery absent physically. |
| 2.3d | NOT_RUN | Actual USB parser pressure during independently observed finite RF absent. |
| 2.3e | NOT_RUN | Actual unread USB output pressure during independently observed finite RF and authenticated recovery absent. |

### Evidence, validation and restoration

E5's seven idle assertions passed independent raw replay and ten evidence
mutations. R4's one prior-state CLAIM/RELEASE passed raw replay and four missing
evidence mutations; zero RF. C4's normal acceptance audit rejects the final
state. Separate failure classification verifies raw framing/CRC, identities,
single ARM, absence of capacity writes and final inactive/unowned authority.
The originally frozen C4 auditor omitted C4 from its packet whitelist. The later
independent audit adds only that identity and still rejects the run; the frozen
closure and original result are preserved. No retroactive threshold relaxation.

Validation: 70/70 current host CTests; 23 WTP schema, seven raw, one framing and
eight transition fixtures; 101 R3 v2 Python tests (85 passed, 16 private-evidence
skips), plus selected E5/R4 raw tests. Both firmware targets built using the
pinned SDK 2.3.1 and Arm 15.3.1. Linked allocator hooks, stack guards and RAM
placement checks passed. Sixty compared RAM functions are byte/address identical
to the old ELF; veneers/static addresses changed, heap capacity fell by 20 bytes
to 220328. This does not establish physical timing equivalence. The original
expired test credentials and sandbox loopback failure remain recorded; refreshed
ephemeral credentials and permitted localhost access produced the passing run.
The optional historical companion-source TLS interop target was not selected.

F3 was restored without extending its original deadline before fresh F4. F4 was
restored at host monotonic 347850093812794 ns, before its unchanged deadline
357877820026000. Both cleanup records have zero failures and matching protected
file hashes. Fixture units/namespace/subnet are gone and WLAN radios are back
down. Permanent time.local, chrony, GPSD/PPS and Avahi checks passed. Installed
WsprryPi remained active as PID 1957, binary SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`.
Host boot remains `220e53ca-ca95-4206-9581-dbe28aa1eeb8`.

Post-restoration raw Console and WTP inventories independently confirm A on the
diagnostic identity above, Missed/inactive/unowned, job
`9f0ae5cb9bf19c6366c53c33a75d86e0`; B on the unchanged BF4 identity,
Empty/inactive/unowned. Scheduling remains disabled and configuration unchanged.
The diagnostic image is retained; no restoration flash was performed.

This attempt consumed one diagnostic candidate, zero repair candidates, one A
flash, one BOOTSEL, zero extra reboots, one 90-second charged ARM, zero RF launches
or completed jobs, zero CONFIG saves, zero commanded Wi-Fi cycles and zero heap
probes. The original four-hour monotonic budget was not restarted. Restoration
began early after the sole failed diagnostic; another work period needs direction.
Checkpoint 047 records elapsed time and evidence/tool hashes. Private raw captures,
frozen scripts, generated images, credentials and the refactor archive stay under
ignored build/private roots. Unrelated pending R3 work and `.impeccable/` remain.

## Bounded attempt, 2026-09-14

Four-hour monotonic budget: start 710199726832375 ns on this Mac, 14,400 seconds;
reserve at least 1,800 seconds for restoration/reporting. New RF ceiling 900 seconds.
No Group 3 work. At most one diagnostic candidate and one focused repair candidate.
Initial reconciled source was `a740dbb8e7319beb20c4807b35f6672bf9fdfd27` after
withdrawing only the attributable unfinished paged-input refactor. All 12 files,
including two untracked headers, are retained with hashes and the original diff in
`build/phase11-5-r3-group2-bounded-20260914/withdrawn-paged-input/manifest.json`.
Unrelated R3 work and `.impeccable/` are preserved.

Read-only admission confirms A source/boot E4 below, Complete/inactive/unowned,
C3 job `c0779e0176119170554cb961d2991c11`, allocator failures two, no DMA/TLS
allocation errors, and scheduling disabled. B remains Empty/inactive/unowned on
BF4 identity. F3 live host boot matches its record; original deadline remains
348101486890000 ns. It was not expired at initial inspection (346425413770994 ns).
No new fixture lifetime is inferred from this observation.

### Assertion table before any firmware change

Identity keys (source / UF2 / boot):

- E4 and C1–C3, A: `a740dbb8e7319beb20c4807b35f6672bf9fdfd27` /
  `454e03e5165143463d6b5f965ea8f1f3704138f08bfc7057704e3fef8f10ebe4` /
  `2b4583bd3d79a38f030a08c82ed96939`.
- BF4, B: `8921a70081839f168edef5926e92445f251d8e1d` /
  `67c27f20da8212097d60cd6b58fbbb4e774286df728ed7ea3e2746b5c6a59f58` /
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- T4/T5, A: `8921a70081839f168edef5926e92445f251d8e1d` /
  `3899b498d05ca5b39e23a45e455c44b2784bcf2aca35f62a8ef4db644cc7241b` /
  `fc90d1a04eb0acc703de907917277921`.

Evidence refers to the corresponding existing `phase11-5-r3-v2-*-result.json`.
Statuses apply to the complete assertion, so an idle component cannot pass its
under-RF requirement. No repair has been selected. Proposed diagnostic telemetry
changes only failed-allocation retention and INFO fields, but its layout/INFO
cost needs new linked/host checks and physical timing/resource observation.
Any later repair must replace this prospective impact assessment before flashing.

| ID | Required assertion | Status | Evidence / missing test and reuse | Proposed diagnostic impact |
| --- | --- | --- | --- | --- |
| 2.1a | 512-event admission and actual completion under contention | PASS | E4 idle plus C1 512-event FSKCW, 384 s; exact current A source. Original C1 observer/result failure retained; no native host-HTTP credit. | Functional plan unchanged; new image timing/resource observation required. |
| 2.1b | 513-event and over-3600 s atomic rejection; exact maximum admission | PASS | E4 seven assertions on current A; parser/service unchanged. | Host regression; no limit change. |
| 2.1c | Worst 32-character plans, physical 3600 s QRSS/FSKCW/DFCW, ordinary WSPR and rejection precedence | PARTIAL | Existing Group 1/hour and compatibility records retained; assertion-level source-impact mapping still required before complete reuse. | No automatic hour repetition; assess layout and measured instrumentation impact. |
| 2.1d | Valid WTP 65536 full transfer and success during RF | FAILED | E4 idle only; C2/C3 supported attempts fail at 4096 host-written bytes. | Failure-site diagnostic needed. |
| 2.1e | WTP 65537 correct framing/CRC rejection, full transfer and same-connection recovery during RF | PARTIAL | E4 idle pass; C2/C3 never reached case. | Framing unchanged; physical case missing. |
| 2.1f | Exact valid HTTP API body 32768 success during RF | PARTIAL | BF4 B idle only; no A RF credit. | API unchanged; physical case missing. |
| 2.1g | HTTP 32769 intended HTTP rejection and authenticated recovery during RF | PARTIAL | BF4 B header-limit/recovery only; no A RF credit. | API unchanged; physical case missing. |
| 2.2a | Declared supported simultaneous allocation with final event plan | FAILED | C1 nominal traffic is not maximum simultaneous capacity; C2 failed; overlap schedule missing. | Diagnostic first; resource budget must be demonstrated. |
| 2.2b | Declared memory overload at intended boundary, owner/RF preserved and authenticated recovery | NOT_RUN | C2/C3 are failed supported cases; slot rejection is not allocation overload. | No overload reclassification. |
| 2.2c | Activated TLS handshake timeout and authenticated reuse | PARTIAL | T4 mechanisms accepted on its identity; A static-response and INFO changes need explicit current-image resource applicability. | New INFO cost/layout assessment. |
| 2.2d | Failed TLS alert ACK and unacknowledged lifetime | PARTIAL | T5 distinct mechanisms retained; same source-impact boundary as 2.2c. | New INFO cost/layout assessment. |
| 2.2e | Both active slots, one-WTP restriction, pending expiry/excess and reuse | PARTIAL | T4/T5 mechanisms retained; source implementation unchanged, resource reuse assessment outstanding. | New INFO cost/layout assessment. |
| 2.2f | HTTP partial header/body activation deadlines and stalled reader recovery | PARTIAL | T5 distinct mechanisms retained; no five-second WTP credit. | Static response change may affect reader allocation; assess specifically. |
| 2.3a | Distinct 30 s WTP inactivity from drained exchange, closure and authenticated reuse | NOT_RUN | No earlier timeout may substitute; schedule and independent observation missing. | Mechanism unchanged; physical activation required. |
| 2.3b | Five-second incomplete-input mechanism with correct progress origin/recovery | NOT_RUN | Existing host coverage only; physical mechanism not established. | Mechanism unchanged; physical activation required. |
| 2.3c | Five-second no-output-progress mechanism, distinct from queue saturation | NOT_RUN | Existing host coverage only; physical mechanism not established. | Mechanism unchanged; physical activation required. |
| 2.3d | Actual USB parser pressure under finite RF and independent authority | NOT_RUN | C3 failed input does not establish intended pressure/recovery. | Physical stimulus/observer required. |
| 2.3e | Actual USB unread-output pressure under finite RF and independent authenticated authority | NOT_RUN | No accepted case; USB interface must have one exclusive opener. | Physical stimulus/observer required. |

### Diagnosis basis

C3's raw files and source do not identify the exact failed allocator call.
`FrameParser` requests 65552 contiguous bytes after a valid header; nullable
`InputBuffer::reserve` may fail, but other allocator paths remain possible.
Cumulative largest-request/free totals do not identify that failure. The existing
panic-only last-attempt fields are overwritten by later successful allocations.
Retaining last failure size, allocator entry and input-allocation context in the
existing locked metrics is the proposed bounded diagnostic, not an OOM repair.

## Historical preparation (superseded by the reconciliation above)


Group 1 is CLOSED at checkpoint 043. Group 2 remains OPEN. No new Group 2
RF job has run.

Reuse the established RF observer, capacity exchange, TLS/transport pressure
and raw-evidence auditors. Coordinate their bounded invocations and add only
missing stimuli. Do not introduce a replacement campaign application.

Preserve E4 current-image idle WTP 65536/65537, 512/513-event and 3600/+1 ns
admission evidence; BF4 B-specific HTTP bounds; and T4/T5 individually audited
timeout mechanisms. These do not substitute for A's enlarged-job allocation
under RF. Do not repeat the completed QRSS, FSKCW and DFCW physical hours.

The proposed new C0 runner was retired before execution following the user's
scope correction. Its packet hash is
`ae660d464f1e3a0e54505f24944fe01808599351966c65fc9b33563aaf9334a1`.
Its 19 new runner/auditor/test files were removed from proposed repository
changes after byte-for-byte archival in
`build/phase11-5-r3-v2-capacity-c0/stage/`. The retirement manifest is
`build/phase11-5-r3-v2-capacity-c0/retirement.json`. Its remote result marks it
RETIRED_NOT_EXECUTED and prevents admission from replaying that packet.
C0 consumed zero RF jobs and zero RF duration. Local harness tests are not
physical evidence or Group 2 acceptance.

F2 is restored. Fresh F3 is active with 7200 seconds execution plus 900 seconds
cleanup, exact deadline 348101486890000 host monotonic nanoseconds, client
PID 553798. The installed Pi PID 1957 and executable hash are preserved.
Read-only preflight confirmed A's retained a740dbb image/source and boot
2b4583bd3d79a38f030a08c82ed96939, Empty/inactive/unowned. A associated to F3
but had no IPv4 lease or synchronized clock after more than 240 seconds.
This is an unresolved network-acquisition prerequisite, not an RF failure.
One separately bounded idle Wi-Fi recovery packet W1 is prepared; it has not
yet executed. Its result must be audited before RF admission.

Remaining mechanisms: actual 512-event RF; maximum WTP and HTTP payloads
under RF; supported simultaneous allocations; bounded unsupported allocation
and recovery; distinct 30-second WTP inactivity and five-second input/output
mechanisms; actual USB parser/unread-output pressure with independent authority.
Measure live allocation with the stimulus/state identity intact. Elapsed silence
or cumulative allocator peak alone cannot establish the intended mechanism.

## Diagnostic deployment source-impact review

Candidate `4da36726ac6809bdf4e73d281fe13b2393dd3b31`, UF2
`0153107c517b673bfad7850957c8387a7dbfb12ddb0a3b1e90edb94b804b9a9f`,
ELF `8855dd77cb0057ff8f33f91d02a3447cf39ca96cb2782b606c51f2e44e4f7353`.
All 70 current host CTest groups pass, including actual pinned Mbed TLS tests;
WTP contract passes. The optional historical fb0a2eb client-interoperability
checkout is not selected; current native-client evidence is separately retained.
Old host credential expiry and sandbox-blocked loopback were environment failures,
retained in the private build logs. Both standard inhibited and physical images
build and pass linked flash, heap, stack, interception and RAM placement checks.

1. No framing, CRC, JSON, admission limit, codec, service, event, RF renderer or
   timing algorithm changes. Existing functional boundary/lifecycle evidence is
   retained within its exact historical identity; no new whole-image credit.
2. Host failure retention, nested realloc, overflow, input context cleanup,
   concurrency, guards, protocol and network checks passed. The recorded suite contains exactly 70 CTest groups.
3. New target identity, failure-site addresses, INFO cost, heap reserve and
   physical timing require observation. RF functions in the compared RAM region
   are byte-identical (60 matching RAM functions overall), while linker veneers
   and some static addresses change. Measured linked heap capacity decreases from 220348 to 220328 bytes. This is a
   diagnostic candidate only; it cannot close capacity by its build or a reboot.
4. No hour campaign is admitted for this diagnostic. If diagnosis justifies a
   repair, that candidate needs a new source-impact review and a complete
   acceptance schedule fitting the remaining 900-second RF allowance. If broader
   resource/hour evidence cannot be reused defensibly, Group 2 stays open.

F3 cleanup verified with no failures at host monotonic 346755676051449 ns;
installed PID 1957/hash unchanged and namespace list empty. Fresh F4 has 10800 s
execution plus 900 s cleanup. Its timer must never be extended, and the earlier
four-hour attempt checkpoint remains controlling.

### E5 diagnostic deployment packet (reviewed before execution)

Existing admission runner, fresh packet
`e41c50ae3cef279a28082cdb0ae9de639e57e6f940cf1a0fbe6731b8da8da39d`,
root `/home/pi/phase11-5-r3-v2-idle-e5-20260914`. One A BOOTSEL and one
verified flash/start; zero extra reboot, RF, Wi-Fi commands, CONFIG saves or heap
probes. B receives read-only inventory only. R4 first reconciled the known C3
Complete state using one exact-identity CLAIM/RELEASE; historical failures remain.
E5 reuses the seven existing idle admission assertions (65536 full-write,
65537 rejection/recovery, 513 and overduration rejection, 512/exact duration LOAD,
abort/release), a 600-second runner deadline and 150-second supervision reserve.
A fresh boot's success cannot establish a repair of the prior contention failure.

### C4 sole diagnostic RF reproduction: frozen schedule

Packet `3265c16e1a970c79c1beee2bd6a9cf4b9198381ee051a08f5f0dd40d7ed95277`,
root `/home/pi/phase11-5-r3-v2-capacity-c4-20260914`, diagnostic source/image
above, boot `0bd82f1324920c360d796988cf31cb5b`. One 90-second finite Tone at
135500 Hz, full 90-second charge before ARM, 180-second execution plus 150-second
reconciliation allowance. F4 deadline is 357877820026000 host-monotonic ns.
No flash, extra reboot, Wi-Fi command, CONFIG save, probe, HTTP or native TLS load.

USB WTP if02 is the single exclusive owner and stimulus connection; Console if00
independently reads INFO with the existing single-flight policy, and host health
is independent. WTP STATUS/host health offer at five-second cadence. The first
owned Running STATUS, bracketed by fresh matching INFO, triggers the existing
capacity exchange. Send exactly one 65536-byte valid STATUS payload (65552 frame
bytes), then, only if successful while Running, exactly one correctly CRC-encoded
65537-byte payload plus same-connection PING. Transfers use the existing duplex
4096-byte write chunks, no retry, each whole exchange deadline five seconds from
its start; no artificial request flood or extra connections. Full-write evidence
and exact response identity/state are mandatory. Capacity traffic cannot claim
continuous authority if it blocks the owner path and INFO subsequently fails.

The generator is `wtp_capacity_frame` with the packet's exact session/request IDs;
PING token is `after-capacity`. Frozen bytes:

- maximum: 65552 bytes, SHA-256 `3ebdfbfadf630d37c118e98dd8c0da3c16d17ec6a884742d138d43bb303e03e3`.
- oversized plus recovery: 65748 bytes, SHA-256 `9daa8eec31651ed93dc03cc6b7ffefe0f19325bd366958d00f07f0d3e88684ed`.

Any new allocator failure, observer fault or unexpected state stops dependent
operations. Let the bounded local job complete; use the existing final inventory
and, if necessary, a separately bound known-completion reconciliation. Do not
retry the stimulus. The primary diagnostic evidence is retained allocator entry,
request size, caller and input-context caller resolved against the exact ELF,
plus raw transfer count and independent final output/owner state. A failed
capacity attempt remains FAILED even if its diagnostic fields are useful.

This reproduces C3's declared Tone/input/no-native-load schedule after E5's idle
maximum allocation sequence. It cannot recreate C3's complete prior boot history;
a nonfailure leaves that historical mechanism unresolved. E5's idle seven-assertion
audit and ten evidence mutations passed; no new RF acceptance is inferred.
