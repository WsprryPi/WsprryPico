# Phase 11.4 network withdrawal investigation

Implemented and tested bounded mDNS withdrawal before station teardown. Real
packets now demonstrate goodbye delivery and cache removal in selected runs.
Phase 11.4 B2/D2 reliability remains open: one target watchdog reboot and
intermittent peer-recovery failures are retained, not declared fixed.

## Initial code review and orientation

Review began at clean Pico devel
`e4ff40a561804cd90e9b823b659405fc7aa37275`. The
[comprehensive investigation prompt](phase11-4-network-withdrawal-prompt.md)
was rendered after reviewing the current capabilities and then executed.

The application already provides standalone scheduling and complete finite WTP
jobs, USB reference control, authenticated WTP/TCP and browser HTTPS, ACK-gated
network management, per-device certified DHCP/mDNS identity, asynchronous DNS
for the `pool.ntp.org` default, and network/TLS resource counters. The standard
image is RF-inhibited. These capabilities do not establish physical network
reliability, overnight memory stability or RF qualification.

Recent runtime history includes `d8cde03` (certified hostname/lwIP lifecycle),
`a34a9a4` (concurrent browser/controller handling), `d9cd3de` (remote settings and
DNS time servers), and `f187555` (TLS certificate alert repair). Later B2/D2 and
same-SSID commits primarily add evidence and audits. The last deployed standard
image is identified as `5ee5bcf93c56-dirty` in the retained manifest; a later Git
HEAD alone does not identify that image's bytes.

Review traced Console idle checks, BrowserApi transaction/idle cancellation,
PicoServer response ACK accounting, PicoNetwork polling and station lifecycle,
portable mDNS state, the project wrapper around pinned lwIP, CYW43 data transfer,
IGMP cleanup, DHCP/netif removal, gratuitous ARP, DNS callback invalidation and
resource ownership. No companion repository or upstream dependency was changed.

## Findings

**Immediate teardown has no radio-completion barrier.** Previously,
`PicoNetwork::set_enabled(false)` called `mdns_.disable(...)` and immediately
`cyw43_arch_disable_sta_mode()`. The wrapper submitted TTL-zero A/PTR through
`udp_sendto_if`, then removed mDNS membership/resources. The SDK disabled the
station netif and submitted disassociation. The exact CYW43 path
`cyw43_ll_send_ethernet` → `cyw43_sdpcm_send_common` → `cyw43_write_bytes` reports
bus transfer, not over-air completion. There is no per-packet radio-completion
callback used at this boundary. A zero local goodbye-error counter cannot
establish peer delivery.

This source ordering permits teardown before a queued wireless goodbye is
transmitted or forwarded. It matches the observed symptom, but source review
alone does not prove where an actual lost frame disappeared. The
[same-SSID failure](phase11-4-same-ssid-results.md) rules out different SSIDs as
a prerequisite; it does not eliminate radio/AP/mesh behavior.

**Existing tests stop before the asynchronous boundary.** The pinned-responder
test captured generated IP packets synchronously in its netif output hook. It
proved packet fields and local cleanup, but could not distinguish radio
submission from later delivery or catch immediate disassociation loss.

**No missing gratuitous-ARP implementation was found.** Pinned lwIP's
`netif_issue_reports()` issues gratuitous ARP for an up, addressed Ethernet
interface when ACD is disabled, as this build configures it. The physical record
already contains successful broadcasts. `netif_remove()` calls `netif_set_down`,
which clears ARP state, and removes IGMP state; DNS lookup epochs invalidate
results across link transitions. These source checks do not explain the earlier
120-second ARP/TCP/NSS failures while USB/NTP remained responsive. No speculative
ARP-cache flush, static-IP fallback or router change was introduced.

## Implemented bounded withdrawal

The mDNS wrapper now separates quiescing/submitting a goodbye from final removal.
It cancels reply/probe timers and releases retained truncated-question chains
before submission. Registration and multicast membership remain allocated while
the station is serviced. The portable owner reports `withdrawing` with an empty
advertised name and ignores late name-result callbacks; it cannot re-advertise
during that interval.

PicoNetwork marks network availability disabled immediately, then continues
foreground CYW43 polling for at most a one-second withdrawal interval before
removing mDNS resources and the station. The withdrawal interval itself does not block USB, watchdog
or job servicing; the existing SDK teardown calls remain synchronous. It does not initiate reconnects or SNTP polls while withdrawing.
Physical link loss ends the interval early. This interval is an engineering
transmission opportunity, not an over-air completion or peer-delivery guarantee.

Repeated OFF cannot extend the original deadline. ON during withdrawal requests
resumption after final teardown; a following OFF cancels that resumption.
Unconfigured, probing, conflicted or unusable-link states do not send an owned-name
goodbye and need no drain. Existing HTTP ACK/transaction/idle checks remain the
entry gate. Status exposes `withdrawal_pending` and `resume_after_withdrawal`;
`enabled:false` means applied network unavailability even while the physical
`link_status` remains up briefly. The browser API documentation distinguishes
those observations.

## Deterministic validation and first adversarial assessment

A new test compiles the actual `PicoNetwork` adapter together with real pinned
lwIP and models the radio output boundary as a queued frame delivered later.
It requires station/multicast membership to survive until delivery, verifies
continued polling and the fixed deadline, and exercises early disable, rapid
ON/OFF, cancelled/applied HTTP requests, link loss, power-management failure and
50 complete resource-stable cycles. It does not use real sockets or hardware.

The pinned-responder test now checks retained membership, rejection of new and
previously queued questions throughout withdrawal, cleanup, and a local send
error with accurate counters and no retained resource leak. Portable mDNS tests
check empty advertisement, late callbacks, repeated withdrawal and conflicts.

Four affected suites (`mdns_tests`, `mdns_lwip_tests`, `network_adapter_tests`,
`network_tests`) pass normally and with address/undefined-behavior sanitizers.
Four compiled mutations are refused by the new behavioral test: immediate
teardown, no driver servicing, early membership removal and repeated-OFF deadline
extension. The failures are runtime assertions, not build failures. WTP contract
validation also passes. The one-second choice remains a physical hypothesis
until target observations; tests do not turn it into a delivery guarantee.

The existing build-host directory referenced a companion checkout that no longer
satisfied its pinned interoperability gate. An isolated host build was used
without modifying that checkout. The first new firmware configure used a different
generator than the existing picotool cache; a separate Ninja directory reused the
installed cache successfully. Failed configure logs are retained. No dependency
was installed or SDK source modified.

## Approved deployment and first target observation

The user approved the exact candidate in the prompt. Existing picotool verified
and started UF2 `99ecfb665b0ed28137b660407fe0bb2e1276b67bcc3f607192c96a1e9ab62954`
on serial `0BF4B4AEC9FFB344`. New boot is
`bcde01522c73ad8e847b003104432cf6`, revision `e4ff40a56180-dirty`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, inhibited standalone simulator.
Console INFO and WTP HELLO/CAPS/STATUS agreed. Storage was healthy; schedules
remained disabled, station AA0NT/EM18/20 and period 120/phase 0 were preserved,
as was watermark `1788714601000000000`. No jobs, ownership or active output
were present. The short certified name, existing server certificate and CA were
retained. Native Mac resolution and authenticated TLS 1.3 HTTP 200 verified
this new boot before testing.

The source manifest/diff bind the dirty firmware to its actual inputs. A later
C_STANDARD 11 declaration affects only the host mDNS test target; comparison
confirmed every other recorded input unchanged. It did not change the deployed
candidate. SDK 2.3.0 (`98a542c1a62fb549ffb5d66a3e5892b06276b670`), pinned lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95` and Arm GNU 15.3.1 identify the build.

The first post-flash IoT attempt (`20260909T211759Z`) failed its Linux NSS
baseline before any Pico WIFI OFF/ON command. Cleanup NSS also returned exit 2.
Its 16 captured mDNS packets include Linux queries and Mac traffic, but no Pico
source packet; tcpdump reported zero kernel drops. USB stayed responsive with
unchanged boot and inactive/unowned state. This is a retained failed baseline,
not a withdrawal test or a successful retry. The controller restored original
Bohica and active, boot-enabled recovery at 21:18:39 UTC. No router change or
onboard wlan0 recovery was attempted.

## Target failure and diagnostic iteration

The original-Bohica attempt `20260909T212100Z` passed its baseline and issued
WIFI OFF at 21:21:06.179706 UTC. Native Mac removed the address at
21:21:06.292. Linux captured only four mDNS packets and no Pico TTL-zero packet;
zero kernel drops do not prove capture of all wireless traffic. The Mac callback
alone does not substitute for decoded TTL-zero A/PTR evidence.

USB observed `withdrawing`, logical enabled false and the physical link up
through 1.003 seconds after OFF began. Its last STATUS was empty, inactive and
unowned. Network pools and TLS reported no allocation errors. At 21:21:15 USB
re-enumerated; recovery INFO recorded watchdog stage 14, no fault hash/PC/status,
and new boot `a076840ce0ec6f1887e86eb025e52ac9`. WTP independently confirmed
empty/inactive/unowned; saved schedules remain disabled and storage healthy.
The firmware intentionally leaves networking uninitialized in recovery mode.

This target failure invalidates full withdrawal/recovery acceptance. It cannot
be explained by a sandbox restriction or called memory-leak evidence. Stage 14
covers code after driver polling, including final mDNS removal and station
teardown; it does not identify which call stalled. The hardware-free radio model
does not model synchronous SDK multicast-filter IOCTLs. A diagnostic candidate
adds stage 15 before mDNS removal, 16 before station disable and 17 after it,
with a new exact-image approval packet. No reliability closure is claimed.

Private artifacts and exact digests are indexed in
[the evidence manifest](phase11-4-network-withdrawal-evidence.json). The first recovery-state host
verification confirmed original Bohica profile, active boot-enabled recovery,
unchanged installed binary/configuration and provider output disabled. Later
diagnostic deployment and final-state observations are recorded below.

## Diagnostic deployment and reproduction

After the user reaffirmed approval, diagnostic UF2 `524dd721ed6f67fbb21b1544546014fa174a4cb5d92d69d5fdfdbe5138f38664`
was verified and deployed. Its new boot is
`f40c48f2e8b61b0da9743f1504ae4f2e`; journals, identity and disabled saved schedules
were preserved. The added watchdog values are internal crash breadcrumbs, not
project phases: all this work remains Phase 11.4, B2/D2.

The full diagnostic attempt `20260909T214308Z` captured a Pico TTL-zero A/PTR
goodbye 0.178 seconds after OFF began. All six Linux negative lookups passed
through the 150.09-second outage. The native Mac removed the address promptly.
No reboot occurred and USB remained responsive. However, after ON the Pico
reported mDNS active in 5.402 seconds while nine Linux peer-recovery checks
failed; broadcast and explicit unicast ARP probes did not restore access. No
recovery pass is claimed. Linux captured 93 mDNS packets with zero kernel drops.

The attempted Mac packet capture did not start: `sudo -n` required administrator
authentication. A private harness startup race checked the child before it
exited. This was corrected to require a live child and a written PCAP header
before dispatch; native DNS callbacks remain valid but are not Mac packet
evidence. A bounded capture using macOS administrator authentication was prepared
under the existing test authorization.

Five subsequent short USB-controlled cycles completed without a watchdog reboot,
with one boot, healthy storage, disabled schedules, inactive/unowned output and
no reported pool allocation failures. They are diagnostic repetitions, not full
B2/D2 peer acceptance. Native Mac authenticated HTTPS subsequently passed. These
successes do not erase the first candidate's watchdog failure or the failed
peer-recovery record; the exact stalled call remains unidentified.

## Paired packet observation and broader diagnostic repetitions

The user completed native macOS administrator authentication for the packet
capture. Short attempt `20260909T215705Z` passed its 10.014-second off interval,
negative Linux lookup, same-name recovery, two authenticated Linux reads over
6.177 seconds and authoritative cleanup. Both captures contain the exact Pico
TTL-zero A/PTR goodbye with TTL 255 and source MAC `88:a2:9e:0a:60:df`; both
also contain the three recovery probes and an announcement. Mac additionally
captured the actual gratuitous ARP. This short diagnostic is not a substitute
for the full 150-second/30-second-stability acceptance procedure.

Matching baseline, goodbye and announcement datagrams were observed about
128–130 ms later in Linux timestamp space. A subsequent eight-sample interactive
clock check independently bounded Linux-minus-Mac clock offset to roughly
121–126 ms at that later time; delivery delay and clock drift are not separated
by the packet comparison alone. Raw timestamps are preserved;
no sub-millisecond cross-host timing claim is made. The Mac goodbye consequently
appears slightly before the Linux OFF timestamp, which does not mean it preceded
the actual command. Same-host intervals and matching packet identity govern
this comparison.

The Mac recorder ignored its first stop signal and its five-second stop wait
expired. The operator completed macOS authentication for exact-process cleanup;
the recorder was stopped and file ownership restored. Actual capture duration
was 279.765 seconds against the requested 120-second limit. The overrun is a
retained harness failure. The PCAP parses completely, but forced cleanup left
no final drop statistics, so no zero-drop Mac claim is made. The helper now uses
TERM then bounded KILL fallback; an actual child ignoring SIGINT was terminated
in the cleanup regression check. The next capture must verify this handling.

Ten additional USB cycles with completed HTTPS reads and light mDNS traffic,
then five cycles with HTTPS reads deliberately in flight during OFF, completed
without a watchdog reboot. Together with the first five short USB cycles, these
are 20 successful local lifecycle repetitions on diagnostic boot
`f40c48f2e8b61b0da9743f1504ae4f2e`. One pre-cycle HTTPS observation failed in the
traffic series and two failed in the in-flight series. Ten in-flight disconnect
observations were expected during the deliberate cuts. None of these is counted
as an all-peer recovery pass. No allocation errors were observed; final sampled
heap was 16,992 bytes after the traffic series and 20,520 after the in-flight
series. Different live connection states make these short samples unsuitable
for an overnight leak-freedom claim.

## Controlled IoT retests and final review

A second controlled IoT attempt (`20260909T221033Z`) failed baseline Linux NSS,
broadcast/unicast ARP recovery and direct-IP HTTPS before any Pico OFF/ON. The
host returned to its original connection at 22:11:21 UTC. Host USB-adapter power
saving was then found enabled. A third controlled attempt
(`20260909T221844Z`) disabled it only at runtime, verified OFF 18 times during
the controlled IoT path, and still failed its baseline before any Pico OFF/ON.
Restoration returned power saving to ON, the original Bohica profile, and active
boot-enabled recovery at 22:19:32 UTC. Both tests had independent restoration
timers and retained gateway/SSID/BSSID observations. Onboard wlan0 stayed outside
the experiment. No router, DHCP reservation or persistent Wi-Fi setting changed.

These failures show that changing the client path affects this test environment;
disabling host power saving was insufficient. They do not locate a lost frame
inside the Pico radio versus the AP/mesh forwarding path. The exact cause of
the earlier watchdog is also unproven after 22 subsequent diagnostic-image OFF
cycles without reboot (20 short series cycles plus the full and paired cases).
No speculative driver or router workaround was applied and the watchdog was
neither lengthened nor disabled.

The final adversarial assessment re-read the portable state owner, actual
adapter, pinned responder cleanup, driver boundary and main-loop listener gate.
No additional actionable deterministic source finding was identified. The
source ordering gap and behavioral-test gap were addressed; harness startup
and stop defects were retained and corrected. The maintained auditor still
rejects the original failed cases, wrong revision, corrupt/missing wire evidence,
short stability windows and all 21 mutated evidence cases. Short diagnostic
success cannot close the full acceptance gate. Formatting and whitespace checks
pass. Upstream dependency sources and companion repositories are unchanged.

This publication is a development investigation checkpoint, **not final device
acceptance**. Remaining Phase 11.4 work is B2/D2 repeatable peer recovery and
watchdog diagnosis, D1 actual DHCP reassignment, and E1 two-board identity/trust.
Overnight memory stability also remains unverified. No RF qualification follows
from these inhibited tests.

## Final restored state

At approximately 22:24 UTC, native Mac and Linux NSS resolved the certified name
to `192.168.1.47`; both authenticated HTTPS successfully against the unchanged
server certificate and diagnostic boot `f40c48f2e8b61b0da9743f1504ae4f2e`.
Console INFO and WTP HELLO/CAPS/STATUS independently verified the expected device,
revision `e4ff40a56180-dirty`, normal boot, inhibited engine, healthy journals,
disabled saved schedules, empty job state and inactive/unowned output. mDNS was
active with 22 goodbye attempts, zero local goodbye failures and no pending
withdrawal. These final samples establish cleanup, not continuous reliability.

At 22:28:42 UTC, the installed wsprrypi service was active with provider output
disabled and unchanged binary/configuration digests. The original Bohica profile,
USB-adapter power saving ON and active boot-enabled recovery were restored after
the final experiment; onboard wlan0 was not altered. Process inspection found
no remaining capture or investigation observer. No DHCP reservation, trust,
router, job or RF change was performed in this investigation.

The final runtime input hashes and pre-commit diff match the diagnostic image's
recorded source. The image retains its build-time dirty revision; the publication
commit does not relabel or rebuild the bytes currently installed on the Pico.
