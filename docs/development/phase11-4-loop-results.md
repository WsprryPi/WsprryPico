# Phase 11.4 repeated B2/D2 investigation

Both original failure modes were reproduced: missing goodbye delivery and
prolonged LAN recovery failure. Neither root cause was isolated. The automated
campaign stopped at its predefined three-failed-case localization limit; the
existing telemetry cannot distinguish driver output failure from radio/AP loss.
A subsequent review explained an additional brief TLS reset as the intentional
unsynchronized-clock admission gate. It does not explain either original fault.

Execution is recorded against the [predeclared plan](phase11-4-loop-plan.md).
The prior withdrawal repair and diagnostic firmware remain unchanged. The
standard inhibited UF2 is `524dd721ed6f67fbb21b1544546014fa174a4cb5d92d69d5fdfdbe5138f38664`,
revision `e4ff40a56180-dirty`, boot `f40c48f2e8b61b0da9743f1504ae4f2e`.
The source starting point is Pico devel `59c01ed35797adecfbe96f1832e6681cde599ed7`.
No other repository or upstream dependency is modified.

## Harness changes

The maintained Mac coordinator stages a bounded Linux runner under a new private
directory. Linux independently records INFO at 250 ms intervals while the main
controller uses only read-only WTP and idle WIFI OFF/ON. Blocking NSS/HTTPS
operations cannot prevent Console sampling. Complete raw WTP bytes are compared
with decoded frames offline, with no resynchronization accepted as clean evidence.
The existing strict withdrawal/recovery auditor remains the acceptance authority.

Each cycle retains separate mDNS and ARP/TCP/DHCP captures, native Mac Add/Rmv/Add
callbacks, periodic native Mac DNS and hostname-verified TLS 1.3 status reads,
source-address/USB-dongle/SSID/BSSID/profile observations and authoritative saved
state. Target cleanup and capture children have independent systemd/process bounds.
No additional Mac packet capture or over-air monitor capture is claimed.

The new offline assessment preserves first failures, separates missing observers
from target failures, checks raw USB framing and capture completeness/drop counts,
measures actual independent-USB gaps and reports allocator counters. A pass marker
cannot bypass unsuccessful process exit, failed native Mac recovery reads or
strict per-case acceptance. Aggregate packet counters do not identify individual
frames inside the Pico radio or AP.

## Retained attempts and review iterations

Campaign 1 stopped before any WIFI OFF/ON: `ip -j -4 addr` on this Linux version
did not include the MAC field assumed by the new host observer. The harness now
reads the USB interface MAC from sysfs and validates it separately. A regression
test uses IPv4 metadata without a MAC field and rejects wrong interface, address,
profile, SSID, MAC and recovery-service state. This was a harness failure, not a
Pico connectivity failure.

Campaign 2 completed one full physical case successfully: 150.060-second outage,
six negative lookups, captured TTL-zero A/PTR, three reprobes, local activation in
5.530 seconds, six Linux authenticated recovery checks spanning 31.673 seconds,
and four post-activation native Mac peer checks. There were 792 INFO samples,
83 raw WTP frames, 54 mDNS packets and 195 diagnostic packets, with no kernel
capture drops. The largest independent USB observation gap was 0.636 seconds;
its larger overall gap includes the deliberate post-monitor cleanup interval.
No allocation error or reboot occurred.

Afterward the coordinator incorrectly treated `systemctl stop` exit 5 for the
already-completed and garbage-collected transient unit as a cleanup failure.
The original campaign therefore stopped as ineffective, although its physical
case passed the strict auditor. The coordinator now skips stop only after
independently observing inactive/failed completion; interrupted live units still
receive bounded cleanup. A fresh campaign retains this false alarm rather than
overwriting its original assessment.

Further adversarial checks added explicit process-exit and Mac recovery-read
requirements, rejection of optimized Python that could remove target assertions,
and bounded termination of a real child ignoring INT and TERM. Process cleanup
also tolerates a child exiting between liveness inspection and signal delivery.

## Reproduced failure and counter boundary

The corrected campaign's second full case reproduced the peer failure after a
successful baseline and orderly withdrawal. All six negative lookups passed.
USB reported local mDNS activation, but Linux captured no Pico recovery probes
or announcements. Nine NSS/recovery attempts failed and ten TCP probes timed
out. Linux captured 36 ARP requests for the Pico and no Pico ARP packet; the
explicit broadcast diagnostic sent three requests and received zero replies.
Mac also failed its post-ON DNS/HTTPS observations during this window. There
were 1,171 INFO samples, 96 raw WTP frames, no watchdog/recovery boot and no
allocation errors. The largest independent USB gap was 0.525 seconds. Both
Linux captures completed with zero kernel drops.

The Pico's accepted NTP count increased from 88 before OFF to 89 shortly after
ON and 91 by the end, while TCP received/sent counters remained unchanged after
the baseline. Link status and local mDNS state stayed up/active. This separates
the failure from complete device/USB failure or complete Internet-path loss;
it does not prove where local-client frames were lost.

Review of the exact pinned lwIP `src/core/ipv4/etharp.c` found that `etharp_raw()`
increments `etharp.xmit` after calling `ethernet_output()` without checking that
call's return value. CYW43's `cyw43_netif_output()` can return `ERR_IF` if
`cyw43_send_ethernet()` fails. Thus the exported ARP “sent” count is an attempt
counter, not proof of a successful bus transfer or radio transmission. Neither
aggregate ARP counter deltas nor successful unrelated NTP exchanges identify
specific missing LAN frames. No upstream source was changed.

The third corrected-campaign case reproduced missing goodbye delivery instead.
Linux captured the baseline answer and later recovery probes/announcements, but
no Pico TTL-zero packet. Lookups at OFF+3, +10, +40 and +80 seconds returned the
stale address; +125 and +145 seconds were negative. Mac removed its cached
address only at OFF+115.774 seconds, consistent with expiry of a pre-OFF
120-second answer rather than prompt withdrawal. Recovery afterward succeeded.
The original four negative-lookup failures remain failures; later successful
reconnection cannot close that case. Both clients used the same fixed paths as
the passing case, and Linux captures reported zero kernel drops.

The standard target also disables both Pico SDK stdio UART and stdio USB in
`firmware/CMakeLists.txt`; CYW43 warning prints are not an available diagnostic
channel on the application's separate CDC Console. This review did not silently
enable printf traffic or alter the installed image. The next useful instrument
would be a bounded project-owned RX/TX metadata ring around the netif callbacks,
recording boot/sequence/time, interface, Ethernet/ARP addresses, operation and the
actual lower-level return code. Ring-overflow counts would make missing trace
coverage explicit. Such tracing is a proposal, not implemented or deployed here;
absence from the present firmware limits localization beyond the observed path.

## Final campaign and adversarial assessment

| Attempt | Full OFF interval | Result | Retained finding |
| --- | ---: | --- | --- |
| Campaign 1 / case 1 | Not issued | Harness invalid | Host MAC metadata reader failed before mutation; repaired |
| Campaign 2 / case 1 | 150.060 s | Physical PASS; coordinator false alarm | Completed transient-unit cleanup bookkeeping repaired |
| Campaign 3 / case 1 | 150.072 s | PASS | Complete packet, USB, Mac/Linux and stability evidence |
| Campaign 3 / case 2 | 150.064 s | FAIL | Nine peer-recovery failures; no captured post-ON Pico mDNS/ARP; USB and NTP continued |
| Campaign 3 / case 3 | 150.067 s | FAIL | Four stale lookups; no captured goodbye; later recovery passed |
| Campaign 3 / case 4 | 150.058 s | FAIL retained; clock-gated reset explained | DNS resolved; first HTTPS connection reset before clock recovery; later six checks spanned 31.519 s |

The automated stop retained three failed cases, not three identical defects.
Post-run review distinguished the final case: USB samples bracket the captured
Pico-to-Linux TCP reset with `clock_state:unsynchronized` and unchanged accepted
NTP count. `PicoServer::accept()` deliberately aborts connections while the clock
is unsynchronized. A new accepted NTP sample appears about 0.4 seconds later,
after which the clock and HTTPS recover. This is a known TLS admission boundary;
it is not evidence for the cause of the missing-goodbye or prolonged ARP failure.
The offline auditor now annotates this only when packet identity, reset timing,
bracketing clock samples and unchanged NTP count agree. It never rewrites the
original failed attempt as a clean pass or changes the existing acceptance limits.

Five full physical cycles produced two passes and three retained failures. They
contain 4,437 INFO samples; the largest independent sampling gap was 0.910 seconds.
All remained on the same normal boot with no new watchdog or allocation error.
Quiet OFF-window heap minima were 20,552, 23,640, 23,808, 23,800 and 23,792 bytes;
these are not sustained monotonic growth, but neither five cycles nor mixed
connection-state heap peaks establish overnight leak freedom. Peak sampled heap
across these cases was 75,424 bytes. The original watchdog remains unexplained.

The final adversarial review also required every recorded host observation to
pass the MAC/interface/address/profile/SSID/recovery checks with an unchanged
association. Eleven corruptions of a real passing case were all refused, including
host drift, missing/drop-corrupted packet evidence, malformed raw USB, wrong boot,
inserted failure, observer gap, failed Mac read and failed runner exit. Ten grouped
hardware-free tests pass directly and through CTest, including real INT/TERM-
ignoring child cleanup and wrong-state/clock-annotation rejection. Reassessment
of all five physical records preserves the two passes and three failures.

Completed failed transient units initially retained systemd's failed-state
bookkeeping. Their exact unit states and logs were saved, then only those four
new test-unit states were cleared; no global reset was used. The coordinator now
performs that cleanup only after successful artifact retrieval. The exact cleanup
operation was exercised on the retained units and verified. The final bookkeeping
and offline-audit changes did not change the exercised target runner or firmware;
no new full physical campaign is claimed after those review changes.

No further actionable harness implementation finding remained in the final
assessment. The instrument limitation remains explicit: per-frame firmware
RX/TX metadata and lower-level output return codes, possibly paired with AP or
over-air observation, are required to distinguish the remaining loss locations.
Repeating the same aggregate measurements cannot establish that distinction.

## Final state and publication boundary

Final native Mac DNS/HTTPS, Linux NSS/HTTPS and USB INFO/HELLO/CAPS/STATUS all passed
on the original diagnostic boot. The Pico remained enabled on Wi-Fi at
`192.168.1.47`, normally booted, inhibited, empty and inactive/unowned, with disabled
schedules and preserved station, schedules, expiry, watermark and healthy journals.
These final successes do not erase the preceding failed windows.

At 23:17:32 UTC, wspr5's installed service was active with provider output disabled
and unchanged binary/configuration hashes. Final host checks retained USB wlan1,
Bohica/BSSID `6c:cd:d6:f2:f6:c6`, original profile, power saving ON and active
boot-enabled recovery. Its service journal contains periodic successful recovery
checks; sampled association evidence shows no path change. The Pico remains on
Bohica-IoT. Host-path samples are periodic, not an over-air continuity measurement.
Onboard wlan0, router, reservations, trust and installed configuration were not
changed. No campaign observer/capture/target process remains running, and the
new transient failed-unit bookkeeping is cleared. Private evidence and source
bundles remain available; only their digests are published in
[the evidence index](phase11-4-loop-evidence.json).

B2 and D2 remain OPEN. D1 actual DHCP reassignment, E1 second-board identity/trust,
the original watchdog and overnight memory stability are not closed by this work.
No firmware repair, reflash, job execution or RF qualification is claimed here.
