# Phase 11.4 B2/D2 repeat and failure diagnosis

The user requested another run because the [initial series](phase11-4-b2-d2-results.md)
had incomplete packet evidence. This repeat **reproduced a real failure**, not
merely a missing probe. The same firmware remained responsive through USB and
continued accepting NTP samples while peer ARP/TCP and native name resolution
failed. B2/D2 cannot be closed by substituting later successful observations.

Execution started from clean Pico devel
`e0dda001f5e3217be94321d7293dfa6db0e1b4fd`, using the existing
[prompt](phase11-4-b2-d2-prompt.md). Private evidence is under
`build/phase11-4-b2-d2-repeat/`. The standard inhibited image, device, USB serial,
MAC, CA/server certificate, hostname, address and saved configuration are those
in the initial identity ledger. USB independently confirmed revision
`5ee5bcf93c56-dirty`, matching deployment and boot
`4a21c44244ee0c3885565bfa23e84d37`. Schedules remained disabled, storage healthy,
output inactive, owner/job absent. No firmware, router, trust, installed service, GPIO or RF setting was changed.
Temporary wspr5 Wi-Fi profiles were used for the authorized SSID comparison and
removed afterward; original routing and resolver contents were restored.
Network evidence used execution outside the sandbox. One mistakenly sandboxed
Mac observer was excluded, as detailed below.

## First repeat: retained recovery failure

Recorder `194819Z` disabled Wi-Fi for 150.150 seconds and enabled it at
19:50:55.633201 UTC. USB first observed local mDNS active at 19:51:01.038575.
The 120-second recovery window did not produce a stable peer recovery:

- Nine original peer failures were recorded. Linux returned completed negative
  NSS lookups and one timeout; these are distinct outcomes.
- All nine bounded direct-IP TCP probes failed. Linux neighbor state remained
  unresolved. The capture contains 27 Linux ARP requests for `.47` after enabling,
  including unicast and broadcast requests, with no captured Pico ARP reply.
- No post-enable Pico mDNS packet reached the Linux capture. Mac's native
  observer did not re-add the name, and a separate Mac system lookup failed.
- USB remained responsive and the same boot stayed empty/inactive/unowned.
  Accepted NTP samples increased from 59 to 61 after local-active observation.
  Allocated heap stayed 20,496 bytes throughout that interval; network/TLS
  allocator errors remained zero.

The mDNS and diagnostic captures contain 83 and 58 packets, respectively,
matching tcpdump counts with zero kernel drops. These are receiver observations;
they do not locate packet loss within the radio/mesh/driver path. Cleanup's NSS
check also failed, so no successful cleanup marker was emitted. Wi-Fi was enabled
and USB state known; peer recovery was still unproven at recorder termination.

## Bounded diagnosis without another Wi-Fi cycle

The series paused for diagnosis before the next off/on. Recorder `195423Z`
started with Linux's neighbor entry marked FAILED. Its first direct-IP TCP
probe succeeded at 19:54:25.273, before the explicit ARP comparison. Five correctly
sourced broadcast ARP requests and five unicast ARP requests then each elicited
Pico replies; USB ARP counters increased correspondingly. No permanent neighbor
entry, cache flush, spoofed source identity or network setting was used.
Direct-IP authenticated HTTPS passed from Linux and Mac, while Linux native NSS
still returned a completed negative at 19:54:39.484.

Recorder `195633Z` compared alternating direct-unicast and multicast DNS queries
from ephemeral ports. All twelve received matching Pico unicast answers with
record TTL 10. Those legacy-query responses are **not native mDNS acceptance**.
A subsequent native NSS query received a separate multicast cache-flush A record
with TTL 120 at 19:56:59.732054, and NSS succeeded. No reset or Wi-Fi cycle occurred
between the failed recovery and these observations. The chronology establishes
recovery before/through read-only probing; it does not establish which probe,
timer or network event caused recovery.

The evidence narrows the failure below browser TLS and includes failure of
ordinary ARP reachability. It does not establish a particular router component,
CYW43 driver defect, mDNS implementation defect or memory leak. Source inspection
included the project network lifecycle, pinned lwIP interface reports and
CYW43 multicast-filter handling. No unsupported runtime repair was introduced.

## ARP announcements on reconnect

The user asked whether the Pico should announce itself through ARP. Yes: DHCP
recommends announcing the usable address to refresh stale peer caches.
[RFC 2131 section 4.4.1](https://www.rfc-editor.org/rfc/rfc2131.html#section-4.4.1)
and [RFC 5227 section 2.3](https://www.rfc-editor.org/rfc/rfc5227.html#section-2.3)
describe the announcement behavior.

The pinned lwIP `netif_issue_reports()` path calls `etharp_gratuitous()` when
the interface/link are up and the IPv4 address is valid. This build disables
DHCP ACD checking, so the non-ACD gratuitous-ARP path applies. This is source
evidence, independently corroborated by the second repeat's cleanup capture:
at **19:59:16.498906 UTC**, Pico MAC `88:a2:9e:0a:60:df` broadcast an ARP
announcement with sender and target IP `192.168.1.47`. Thus the mechanism exists
and an actual announcement was delivered on that reconnect. None was observed
on wspr5 during the failed first reconnect. An absent announcement alone does
not explain the lack of replies to 27 subsequent ordinary ARP requests.

## Second repeat: goodbye delivery failure

Recorder `195902Z` had a native positive A baseline at 19:59:07.706676 and disabled
Wi-Fi at 19:59:08.982687. The lookup beginning at 19:59:12.104288 still returned
`.47`. Unlike the original one-second test race, this was the corrected
three-second check. No TTL-zero Pico goodbye reached the Linux capture, and the
Mac observer contained only the initial Add, with no removal. The attempt was
stopped as failed and Wi-Fi restored. Cleanup captured the ARP announcement,
three mDNS probes and two announcements; NSS and authenticated HTTPS passed.
This later cleanup does not convert the failed withdrawal into a pass.

For the final repeat, the recorder was adjusted to retain an early stale-cache
failure while continuing the full 150-second observation. Original failures
still prevent CASE_PASS. Immediate bounded broadcast/unicast ARP comparison was
also prepared for a first recovery failure, avoiding the diagnostic startup gap
that lost the first failure's live conditions. Each runner version is retained.


## Third repeat and subsequent recovery

Recorder `200253Z` again failed the 120-second peer recovery window. Wi-Fi was
requested on at 20:05:30.080896 UTC; USB observed local-active state at
20:05:35.515519. Nine peer checks failed. The Linux capture contains 36 ARP
requests after enabling, with no captured Pico ARP reply or post-enable mDNS.
Immediate three-request broadcast and three-request unicast ARP comparisons
also captured no Pico reply. Aggregate USB ARP counters advanced during the
broadcast stage, but do not identify individual received or transmitted packets.
Mac direct-IP TCP also timed out outside the sandbox during this failure.

USB remained responsive through 20:07:48.137464, on the same boot. NTP accepted
samples increased from 72 to 74 and allocated heap ranged from 20,488 to 20,504
bytes after local-active observation. The 83 mDNS and 68 diagnostic captured
packets match recorder totals with zero kernel drops. This is a second actual
recovery failure, not an incomplete successful run or evidence of a memory leak.

A separate read-only observer, `200821Z`, then recorded four paired positive
Linux NSS/TCP/authenticated HTTPS checks from 20:08:24 through 20:08:45, with
unchanged authoritative USB state and no further Wi-Fi cycle/reset. This proves
later recovery, while preserving the original failed deadline.

## SSID comparison and adapter health

The Pico uses Bohica-IoT at 2.4 GHz; Mac and the original wspr5 USB connection
use Bohica at 5 GHz. Sharing a DHCP server and IP subnet does not itself prove
that every multicast, broadcast and peer-unicast path is equivalent. The
user authorized moving wspr5 for a comparison and warned about onboard Wi-Fi.

The unused onboard `wlan0` (`2c:cf:67:62:76:66`) failed a bounded 30-second
association attempt. Its temporary profile was removed, its health was not
qualified, and it was excluded from acceptance evidence. The USB dongle
`wlan1` (`90:de:80:47:b9:da`) remained the management interface.

A detached controller then temporarily moved the USB dongle to Bohica-IoT.
At 20:17:25 it was associated to `42:98:b5:fe:36:a1`, channel 7, signal -42 dBm,
with the same DHCP address `.117`. Five gateway pings returned without loss.
Recorder `201730Z` began with positive native Linux resolution and authenticated
Pico status. Its three- and ten-second offline lookups returned negative.

However, at **20:18:14.900 UTC**, the existing `pi-wifi-recover.service`
explicitly activated the preferred original Bohica profile. The system journal
identifies the service, nmcli PID 417024, and locally initiated deauthentication.
This was not an observed spontaneous USB-adapter or AP failure. wspr5 was back
on Bohica before the Pico reconnected at 20:20:05.700233. Therefore this run
**does not qualify same-SSID recovery or isolate inter-SSID forwarding**.

The mixed-path run retained one HTTPS failure (`No route to host`) despite
positive NSS, followed by six successful peer checks over 33.43 seconds and
verified cleanup. The initial failure remains FAIL. The late Mac observer saw
an Add at 20:20:19.654, but lacks a complete baseline/removal sequence and cannot
supply a passing full Mac withdrawal audit.

The controller's final restoration completed at 20:21:38.264767. It removed
only its temporary profile. Final checks confirm original USB profile UUID
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, Bohica, `.117`, gateway `.1`, metric 100,
onboard wlan0 disconnected, original resolver SHA-256
`bbea1627272790a4e1c4b7256f398ab0d931f3bdf106598d75eb19dd968ede25`, and five
additional gateway replies without loss. `pi-wifi-recover.timer` remains active.
No watchdog or installed service was disabled or modified.

A future controlled same-SSID run must account for that recovery service,
record SSID/BSSID/profile throughout the outage and recovery, and abort the
comparison on path drift. Any bounded suspension must include an independent
local timed restoration before moving the management link. The onboard adapter
must not be substituted without passing a separate health baseline.

## Adversarial assessment and corrections

1. **Recorded failure obscured by secondary evidence gaps:** the offline checker
   originally reported missing cleanup before noticing the actual failed case.
   It now refuses original failure markers first, including the new
   `OUTAGE_LOOKUP_FAILURE` marker. Positive packet/identity/time requirements
   remain unchanged. The original audit output is retained alongside its corrected
   FAIL classification; it was not erased.
2. **Early abort hid later cache behavior:** the final private runner preserves
   an early stale lookup as failure while completing the bounded outage. It
   cannot turn a later successful recovery into CASE_PASS.
3. **Invalid observer execution:** an initial Mac-only observer was inadvertently
   launched in the sandbox. `DNSServiceGetAddrInfo` returned -65563, followed by
   an EOF-loop defect that wrote empty records. That log is retained but excluded
   from network conclusions. The observer was stopped, its EOF handling fixed,
   and a new observer launched outside the sandbox. Its late start is retained
   as an evidence limitation.
4. **SSID drift:** review of the final interface snapshot caught the unexpected
   Bohica association. NetworkManager and system journals identify the recovery
   service's intervention. The comparison is invalidated, rather than attributing
   it to the Pico, adapter or router. The user's recovery safeguard remains intact.

Two review rounds rejected all 21 altered-evidence cases, including hidden
failures, wrong boot/certificate/output, missing peer reads, lookup timeouts,
resource failures, forbidden USB mutations and mismatched raw responses. Two
previous complete physical fixtures still pass the unchanged positive gates.
All four new attempted cases are refused as failures. WTP contract validation
passes its 23 schema, 7 raw JSON, 1 framing and 8 transition cases. No runtime
firmware repair is claimed: the actionable checker/observer/reporting issues
were corrected; the physical reliability defect and invalid SSID comparison
remain explicit open work.

## Final state and remaining work

Final Mac native resolution and certificate/hostname-verified authenticated HTTPS
pass on the same device/boot with inactive output and no owner/job. The installed
wsprrypi service remains active with provider output false and unchanged binary
and INI hashes. Bounded recorders completed; the Mac observer was stopped.
Private evidence and runner revisions are indexed in
[the artifact hash ledger](phase11-4-b2-d2-repeat-evidence.json).

| Remaining item | Required evidence |
| --- | --- |
| B2 / D2 — FAIL reproduced | Explain and repair intermittent ARP/TCP/NSS and goodbye delivery; repeat with complete evidence. Same-SSID comparison remains unqualified because the recovery service changed the path. |
| D1 | Actual DHCP address change followed by same-name and identity recovery. |
| E1 | Two physical boards with independent names, identities and trust rejection. |
| Overnight stability | Sustained web/USB responsiveness and bounded memory use. These short samples do not establish leak freedom. |
