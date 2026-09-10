# Phase 11.4 D2 after Pico SDK 2.3.1

D2 remains **open**. The released-SDK shutdown investigation did not reproduce a
watchdog in the observed shutdown windows, but retained actual baseline, goodbye
and recovery failures prevent full acceptance. This work fixes a recovery-observer
clock-readiness defect and adds a strict offline shutdown sub-assessment. It does
not change or flash firmware, establish the cause of historical watchdogs, or
repair delivery between Bohica-IoT radios.

The [executed prompt and refinements](phase11-4-d2-sdk231-prompt.md) define the
boundaries and stop rules. The [evidence manifest](phase11-4-d2-sdk231-evidence.json)
records exact image identities, individual verdicts and hashes of private raw
observations. Earlier failed records remain unchanged. No RF mode, job, ownership,
GPIO, router change, SDK edit or sibling-repository change occurred.

## Identity and setup

Testing on 2026-09-10 used the existing SDK 2.3.1 images from the
[B2 deployment record](phase11-4-b2-delivery-results.md#exact-targets-and-images).
SDK commit is `079c6f39023649b154152db30f1d781e884879bc`, GCC 15.3.1, target
Pico 2 W/RP2350, standard `inhibited-standalone-simulator`, default 150 MHz system
clock. Runtime revision `dbf1d86f0885-dirty` alone is not a unique image identifier;
the manifest retains both per-board UF2 and final checked ELF hashes.

A is the original D2 subject: USB `0BF4B4AEC9FFB344`, WTP
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`,
`wsprrypico-0a60df.local`, `192.168.1.47`, boot
`3bb4bd7cb18af1e396fa4bf3ad5e5da6`. B is a read-only comparator: USB
`CDDBF8767C506C07`, WTP `29f20b7342051ef947aa56cb9d4fab42`, MAC
`88:a2:9e:0a:9d:89`, `wsprrypico-0a9d89.local`, `192.168.1.53`, boot
`6a0eca7714ee24db9aff824dd8ffb11b`. B was not cycled. Both retain independent
certificate identities, AA0NT/EM18/20, period 120/phase 0 disabled schedules,
expiry zero and healthy storage. A's watermark is `1788714601000000000`; B's is zero.

All testing used Bohica-IoT, the user's simple 2.4 GHz bridge. wspr5 retained USB
wlan1, MAC `90:de:80:47:b9:da`, IP `192.168.1.117`, original profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, radio `7a:cd:d6:f2:f6:c5` at 2432 MHz.
Its recovery timer stayed active and boot-enabled. Mac association was previously
user-confirmed. A's preflight BSSID was `42:98:b5:fe:36:a1`; it rejoined the host's
radio after case 1, then was observed on `42:98:b5:fe:36:a1` after case 3.
Association samples do not establish continuous association or prove AP causality.
No cache flush, static neighbor, radio lock or host reassociation hid these changes.

## Retained initial series

The initial series stopped at three failed cases. Each held WIFI OFF for at least
150 seconds with independent Console INFO, USB WTP, NETTRACE, Linux packet/NSS and
native Mac DNSService callbacks. A separate systemd restoration timer preceded
each bounded controller. Only WIFI OFF/ON controls were issued during the cases.

| Case | OFF seconds | USB samples / maximum gap | Station-disable call | Goodbye and recovery | Full case |
| --- | ---: | --- | ---: | --- | --- |
| 1, idle before OFF | 150.139 | 1,018 / 3.029 s | 51.815 ms | No captured baseline or goodbye; later positive answer and six authenticated checks spanning 31.845 s | Fail: baseline and delivery |
| 2, ordinary prior traffic | 150.078 | 811 / 3.029 s | 51.779 ms | Matching TTL-zero A/PTR goodbye and Mac removal/re-add; first recovery TLS reset, then six successful checks spanning 33.129 s | Fail: original recovery read |
| 3, ordinary prior traffic | 150.097 | 1,137 / 3.035 s | 51.778 ms | Matching goodbye and Mac removal; no captured recovery positive, twelve native lookup failures and no authenticated recovery | Fail: recovery |

All three retain the same A boot, inactive output, empty state, unchanged saved
configuration and complete current-window shutdown markers. Goodbye calls took
636–649 microseconds. The separate interval from goodbye return to disable entry
was about 1.053 seconds and includes the intentional withdrawal grace. It is not
the station-disable call duration. Case 1's trace independently verifies at least
eight seconds without TCP before withdrawal; cases 2–3 include recent TCP traffic.
Both packet captures in every case exited normally with zero kernel drops.

Case 1's native Mac removal happened roughly 121 seconds after its initial add;
without a captured goodbye it cannot prove goodbye-driven invalidation. Local
activation took 35.548 seconds and eventual peer recovery was within 120 seconds,
but missing preconditions remain failures. Case 2 activated locally in 6.571
seconds; case 3 in 5.550 seconds. Case 3 remained locally healthy while peer
resolution failed through the deadline and cleanup. Later reachability does not
retroactively pass that case.

## Observer repair and separate verification

Case 2's first HTTPS attempt occurred 6.629 seconds after WIFI ON. Packet evidence
contains the Pico-origin TCP reset; bracketing USB INFO samples both report an
unsynchronized clock. The first observed ready clock was 7.251 seconds after ON.
`PicoServer::accept` intentionally aborts connections while UTC is unavailable.
The evidence supports a premature observer request, not disabling that TLS gate.

The shared recovery observer now waits for synchronized/holdover state and
positive UTC before attempting recovery reads. It retains the original 120-second
ON-based deadline, original 40-second local-activation bound, certificate/name/
fingerprint verification, and every failed attempted read. A successful stability
check finishing outside 120 seconds cannot pass. The recorded case-2 reset stays
a failure. Deterministic tests exercise missing, zero, invalid and unsynchronized
clock data as well as both valid clock states; replay binds the wait decision to
the actual failed attempt.

Separately labeled **case 4 passed the complete bounded audit** after positive
Mac/Linux authenticated and captured mDNS baselines. OFF lasted 150.090 seconds;
780 USB samples had a maximum 3.030-second gap, with 565 continuous trace events.
The station-disable call returned in 51.882 ms. Linux captured the matching
TTL-zero A/PTR goodbye, three recovery probes and two announcements; native Mac
callbacks show Add/120, Remove/0 and Add/120. Linux's six outage lookups were
negative. Local activation took 5.526 seconds; six authenticated recovery checks
spanned 31.591 seconds, completing about 38.645 seconds after ON. Both captures
exited normally with zero kernel drops. The original A boot and output state
were unchanged.

The live case's clock was already ready at local activation, so it validates the
corrected observer's complete lifecycle but does not dynamically exercise the
wait branch. The case-2 replay and deterministic tests cover that branch. The
native Mac/Linux timestamps come from different host clocks; they are not a
measurement of cross-host packet latency. This one pass cannot replace the three
failed cases or provide the required eight clean complete cases.

## Adversarial review

Review found and corrected three evidence/observer issues: an old trace-ring
shutdown could satisfy a later incomplete window; marker 4 indicates entry to
station disable, whereas marker 5 proves return; and the recovery client could
connect before the firmware's clock admission prerequisite. The audit now binds
markers 2/3/4/5 to the current OFF interval and rejects reversed marker timestamps.

The offline auditor independently checks exact boot/image/device, saved state,
USB continuity, raw CRC-framed WTP versus decoded frames, allowed operations,
continuous trace, unchanged host path, complete captures and exact Pico-origin
A/PTR records. Its success never grants full D2 acceptance. Separate tests reject
hidden resets, wrong devices, coverage gaps, unsafe output, altered watermarks,
extra controls, truncated outages, stale marks and reversed times. Mutations of
actual evidence reject unexpected USB/Console commands, corrupt CRC, capture-count
mismatch and hidden kernel drops; a changed recovery boot is classified as failure.

A final reassessment reran every case against the corrected auditor and the
complete case-4 recovery audit. The three failures remain failures; only case 4
passes its complete bounded case. No actionable finding remains in the changed
observer/auditor slice. The physical delivery and repeatability blockers remain
explicitly open.

Both unchanged images pass the three existing image checks. The eight affected
CTest targets pass. Raw captures, credentials and generated images remain private
under ignored build directories; committed artifacts contain source, sanitized
results and hashes. Full physical D2 repeatability, B2 delivery repair and the
historical watchdog's causal attribution remain unresolved acceptance limits.

## Final state and remaining roadmap

Final USB checks on both exact boots confirm healthy storage, synchronized
clocks, inactive output, empty/unowned state, disabled scheduling and unchanged
station/schedules/expiry/watermarks. Both BSSID samples are the host's radio,
`7a:cd:d6:f2:f6:c5`. Final Linux observations completed at 14:00:00 UTC and Mac
observations at 14:00:48 UTC: both names resolved and both boards passed
certificate/name/fingerprint-verified read-only WTP and HTTPS. These later
positive observations do not replace the failed case-3 deadline and cleanup.

wspr5 retained its original Bohica-IoT wlan1 profile; `pi-wifi-recover.timer` is
active and enabled, and `wsprrypi.service` is active. All D2 transient units and
restoration timers are gone; all four Mac observers recorded stopped reader
threads and terminated native DNSService processes. Existing user shutdown and
soak work remains byte-for-byte unchanged and outside this commit.

| Item | Repository ownership | Status | Remaining work |
| --- | --- | --- | --- |
| B2 discovery/reconnection | WsprryPico; joint WsprryPi acceptance | Open | Resolve retained delivery failures, then eight complete cases |
| D1 DHCP address change | WsprryPico; joint WsprryPi acceptance | Open | Actual new lease/address with unchanged identity and trust |
| D2 orderly withdrawal | WsprryPico | Open | Four observed shutdowns without reset and one complete case pass; retained goodbye/recovery failures and eight-case repeatability remain |
| E1 two-board identity/trust | WsprryPico; joint WsprryPi acceptance | Pass, bounded | Preserve recorded scope; general end-user provisioning remains unimplemented |
| Eight-hour soak | WsprryPico; joint WsprryPi observation | Incomplete | Uninterrupted run after repair gates; prior power-outage investigation is closed |
