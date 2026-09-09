# Phase 11.4 D1–D3 acceptance results

The [execution prompt](phase11-4-d1-d3-prompt.md) was executed on 2026-09-09.
D2's final bounded packet/cache run passed, but the overall case remains partial
because an intermittent reconnection failure was reproduced without a root-cause
fix. D1 and D3 require the remaining specific
router-operation exception and selective radio-fault arrangement; neither was
replaced by a simulation or marked passed.

## Identity and setup

The coordinating checkout started clean on devel
`16b54128feb4fb260f3bfb0306399d88e68e950c`. The only board was Pico 2 W / RP2350,
USB serial `0BF4B4AEC9FFB344` on wspr5, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`. The unchanged standard inhibited image reports
revision `5ee5bcf93c56-dirty`, engine `inhibited-standalone-simulator` and boot
`cebcd4720cd9919a7cfaff492b717a85`. No flash or reboot occurred in this slice.
The carried-forward deployment hashes are UF2
`2711a54ba57b7754907a5e20dd84d6920dcb5ffe8524c69b8ff2ae569a0686e4` and ELF
`f21db5220cd403a2306122e9f121e61a6853ab04e8c1810145440363dc26ed65`;
this slice refreshed USB identity/boot/engine rather than reading firmware back.

The certified hostname remained `wsprrypico-0a60df.local`, IPv4 `192.168.1.47`,
MAC `88:a2:9e:0a:60:df`. Linux wspr5 used `wlan1` at `192.168.1.117`; the Mac
used `en0` at `192.168.1.27`, native resolver interface 14. The server certificate
SHA-256 remained
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
Existing approved CA, browser and controller identities were used unchanged.

Read-only Chrome inspection identified the actual router as Orbi RBR850 at
`192.168.1.1`, firmware `V7.2.8.2_5.1.18`, DHCP enabled with pool `.2`–`.254`
and no address reservations. Pico was on 2.4 GHz IoT; Mac and wspr5 were on
5 GHz, all associated through the same satellite. These are interface facts,
not proof that the access point caused the failed recovery.

## D1 and D3 prerequisites

The user supplied the signed-in Chrome router session. Its LAN Setup page
exposes Add/Edit/Delete Address Reservation, but no individual lease-release
control. No router setting was changed. A concrete exception was requested to
the plan's blanket reservation prohibition: temporarily reserve `.247` for only
the Pico MAC, force a real new DHCP acquisition, verify the unchanged hostname,
certificate and device from both clients, then remove the reservation. The
address must still be checked against current router state before applying it.
A reservation must never become an operational dependency or substitute for
observing a real address transition. D1 still needs that operation, production
client reconnection and Chrome reload at the new address.

Orbi's web Access Control page says to use its phone app. The inspected UI
provides no selective station deassociation operation. Blocking Internet access
alone would not prove loss of the Pico's Wi-Fi association. A user-assisted
Pico-only radio shield, with the board insulated and USB attached, was proposed
as a bounded alternative; recording must be ready before the user applies it.
D3 still needs an actual USB-observed unexpected link loss, natural stale-cache
expiry without a successful-goodbye claim, local finite-job progress/ownership
and recovery. Neither an orderly Console disable nor a dropped TCP connection
closes that gate. No shared AP outage or unrelated-client change was attempted.

## D2 attempts and diagnosis

Private records are under `build/phase11-4-d1-d3/`. The accompanying
[hash index](phase11-4-d1-d3-evidence.json) binds executed helpers, raw USB and
packet records, peer callbacks, failures and audits. Each run opened a single
USB WTP session and used only HELLO/CAPS/STATUS. No LOAD, ARM, owner claim,
schedule change or RF/GPIO action occurred. Native Mac `dns-sd -G v4` ran through
a PTY to retain flushed callbacks. Linux used bounded `getent ahostsv4` calls;
its existing Avahi daemon was active, while `avahi-resolve-host-name` and
`resolvectl` were unavailable. No resolver service or cache was reconfigured.

| Attempt | Observation | Disposition |
| --- | --- | --- |
| `orderly-20260909T162436Z` / remote `d1-d3-orderly-20260909T162437Z` | Captured Pico A/PTR TTL-zero goodbye; Mac removed the A record; all six Linux outage lookups returned exit 2, not timeout; USB off-to-on interval 150.166 s. Same-boot device recovery and Linux resolution passed. | Capture ended after probing, before the final announcement was retained; Mac re-add was not captured. Incomplete recovery evidence, not a full PASS. |
| `orderly-20260909T162818Z` / matching remote timestamp | Again captured Pico A/PTR goodbye and Mac removal. Linux remained negative through the outage. Device reported active after re-enable, but Linux resolution returned exit 2 and no post-reconnect Pico mDNS packets appeared in the zero-drop capture. | Failed peer recovery retained. Subsequent direct-IP TCP timed out outside the sandbox, and Mac resolution failed. USB remained inhibited, empty and unowned. |
| `d1-d3-recovery-20260909T163329Z` | Five of five ARP replies succeeded **before** the additional authorized Wi-Fi cycle; five of five succeeded afterward. Capture retained same-address DHCP Discover/Request, three probes and positive announcements. | The failure had cleared by the pre-cycle ARP test. Do not attribute its recovery to the toggle. Same-address DHCP acquisition does not close D1. |
| `orderly-20260909T163449Z` / remote `d1-d3-orderly-20260909T163450Z` | Complete 150.174 s outage; 47 captured packets, zero kernel drops, Pico A/PTR goodbye, three probe datagrams, two positive announcements and native Mac Add/Remove/re-Add. Six Linux outage lookups returned exit 2; baseline and recovered lookups returned only `.47`. | Offline bounded-case PASS. This successful repeat does not resolve the preceding failure or establish reliable repeated recovery. |

In the final run, Linux captured the goodbye at 16:34:55.089273 UTC. Its first
negative lookup began about 1.07 seconds later and returned about 6.10 seconds
after reception; the command itself took about five seconds. Mac recorded
removal at 16:34:54.978 local-clock UTC equivalent and re-add at 16:37:30.638.
The small cross-host timestamp reversal is retained rather than interpreted as
negative network latency. Three probe datagrams are a receiver observation,
not qualification of on-air probe spacing.

The initial send-before-radio-teardown hypothesis was not established as a
defect: both orderly captures contained actual Pico-sourced goodbye packets.
The failed reconnection still had successful Pico SNTP samples and increasing
receive counters. Later USB snapshots had lwIP heap usage 200/32768 bytes,
zero TCP PCBs, zero TCP segments and zero packet-pool entries, with no allocation
errors or increase in their sampled high-water marks. These short observations
do not diagnose an overnight memory leak or qualify Phase 11.5. Without packet
observations inside the radio/AP boundary, the underlying intermittent failure
remains unresolved; no speculative firmware workaround was introduced.

## Review and validation

The adversarial review required actual packet origin and PTR target checks,
native cache callbacks, saved-state equality, independent USB authority and
captured post-recovery announcements. It rejected the initial short capture.
The corrected observer retains recording after local active state and preserves
every failed attempt. Cross-host UTC timestamps are not treated as subsecond
latency measurements: the Mac removal timestamp and Linux reception timestamp
differ slightly because their clocks differ. Linux's negative-lookup completion
is an upper bound on observed stale-name availability, not the exact internal
Avahi eviction instant. Orderly goodbye removal is separate from D3's natural
TTL expiration after an unexpected outage.

The offline checker is `scripts/audit_phase11_4_mdns_withdrawal.py`; shared packet
decoding now retains source Ethernet MAC and validates/decompresses PTR targets.
It operates exclusively on private files. No runtime, protocol, SDK, frontend
or independent WsprryPi source change was required.

After strengthening packet checks, a second assessment added exact USB
HELLO/CAPS/session and Console-operation validation. The final audit passed,
and 15 adversarial cases rejected altered source MAC/IP, positive TTL pretending
to be a goodbye, wrong PTR target, wrong owner, changed watermark, hidden LOAD,
Linux timeout counted as negative, missing cleanup, capture drops, missing Mac
removal/re-add, wrong USB identity, unexpected Console mutation and truncated
packets. The earlier E2/E3 audit and its eight adversarial cases also passed
with the shared decoder changes. Both portable and pinned lwIP mDNS CTest suites
passed; the WTP contract validator passed 23 schema, seven raw-JSON, one framing
and eight transition cases. No remote CI or RF qualification is claimed.

## Final cleanup and retained client failure

Final read-only USB and Linux authenticated HTTPS passed in
`d1-d3-final-probe-20260909T164223Z`. The preceding generic probe refused its
extra synchronized-clock precondition at 16:41:49; that refusal is retained.
The dedicated cleanup reader records holdover and performs no job admission or
mutation. Final sampled uncertainty was 181,911,323 ns. No clock was falsified
and no admission threshold was changed.

Mac system resolution and authenticated HTTPS returned HTTP 200 at 16:34:21,
16:39:44 and 16:41:12. A separate Chrome reload and two subsequent reload attempts
returned `ERR_ADDRESS_UNREACHABLE`. This browser failure remains open; successful
Python TLS reads do not stand in for a successful Chrome reload. No browser trust,
router policy or system resolver cache was changed to conceal it.

The board remains in the same boot, empty, explicitly inactive/unowned, with
healthy storage, enabled Wi-Fi, unchanged certified name/address, power saving
disabled and `pool.ntp.org`. Station AA0NT/EM18/power 20, disabled 120/0 schedule,
expiry zero and watermark `1788714601000000000` remain intact. All bounded test
observers/captures exited. The installed service was never paused in this slice;
the final host check found it active with provider output disabled, binary SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273` and INI SHA-256
`e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8` unchanged.

## Remaining scope and documentation impact

Remaining work includes D1, D3, E1 with two real boards, intermittent discovery
and TCP recovery, and the startup/overnight connectivity and memory investigation.
Phase 11.5 resource/contention, 11.6 conducted RF and 11.7 final joint closure
remain separate. The prompt, record, hash index, offline audit and joint matrix
are the maintained deliverables. No new operator deployment or trust procedure
was introduced, and the independent WsprryPi repository was not modified.
