# Phase 11.4 controlled same-SSID comparison

This comparison follows the [reproduced B2/D2 failures](phase11-4-b2-d2-repeat-results.md)
and the user's explicit instruction to pause wspr5's Wi-Fi recovery service
while preserving recovery after reboot. The [execution prompt](phase11-4-same-ssid-prompt.md)
defines the bounded scope. Source began at clean Pico devel
`0915647087034c280d353e016a62e3f738eb2f43`.

## Execution and recovery controls

The existing `pi-wifi-recover.timer` was enabled, with a static oneshot service.
The controller stops current timer/service execution without disabling or
masking either unit. Thus the original timer remains enabled for subsequent
boots. Before pausing recovery, a separate systemd timer was armed to run local
restoration after 600 seconds. The main controller has a 540-second runtime
limit and 35-second stop timeout; its normal cleanup restores the original
connection and starts recovery before cancelling that fallback timer.

Only the USB dongle wlan1, MAC `90:de:80:47:b9:da`, moves to a temporary
non-autoconnect Bohica-IoT profile. The onboard wlan0 remains excluded after its
previous failed health check. Credentials are passed privately and the transient
activation password is removed after use. Original Bohica profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6` is retained throughout.

The Pico remains the same standard inhibited device and revision
`5ee5bcf93c56-dirty`, serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, certified hostname
`wsprrypico-0a60df.local`, MAC `88:a2:9e:0a:60:df`, address `.47`. The Mac stays
on Bohica, providing a separate cross-SSID observer. All network execution uses
the path outside the sandbox. No router, firmware, trust or transmitter-service
change is part of this comparison.

Actual SSID/profile observations are repeated throughout the Linux/Pico test;
drift aborts the comparison. USB identity, state and resource samples accompany
Linux packet captures, native NSS results and authenticated HTTPS. The native
Mac observer starts before dispatch with a positive `.47` baseline at
20:36:04.931 UTC. The controller and independent restore timer were dispatched
at 20:36:18 UTC, with logs flushed locally on wspr5.


## Observed result: withdrawal failed, recovery succeeded

This is a valid bounded same-SSID comparison, but **not a B2/D2 pass**.
There are 104 confirmed IoT path observations from 20:36:37.900012 through
20:40:05.240867 UTC, spanning all device observations. The largest gap is
2.037 seconds; every observation reports the same temporary profile and BSSID
`42:98:b5:fe:36:a1`. The recovery timer is inactive throughout those checks.
The host journal confirms no recovery-service intervention until restoration.
Five gateway pings before and five after the test each returned without loss.
This establishes the observed USB-adapter path, not general Wi-Fi health or that
the Pico was associated with the same AP.

Recorder `b2-d2-orderly-20260909T203637Z` disabled Pico Wi-Fi at
20:36:44.209925 and requested it on at 20:39:14.400730, an outage of
150.190807 seconds. The native Linux lookups at 3, 10, 40 and 80 seconds still
returned the cached `.47` address. Each is retained as an original failure.
The 125- and 145-second lookups returned completed negatives, without timeout.
No Pico TTL-zero goodbye reached the Linux capture, despite the USB goodbye
attempt counter increasing by one with no reported send failure.

The Mac removed the name at 20:38:40.696 and re-added it at 20:39:20.232.
The delayed removal is consistent with expiry of the earlier 120-second A
record, not evidence of prompt goodbye processing. No Mac packet capture was
made in this run, so its removal mechanism is not independently established.
The complete native callback log is retained.

Recovery itself succeeded: local-active state was observed 6.434526 seconds
after the on request, with six positive Linux NSS/authenticated HTTPS pairs
spanning a 33.874101-second stable window and no peer recovery failure.
The capture contains three same-name probes and one subsequent A/PTR
announcement. At 20:39:19.385259 the Pico broadcast a gratuitous ARP request
with sender and target `.47`. Cleanup verified the same device/boot
`4a21c44244ee0c3885565bfa23e84d37`, inactive output, no owner/job and preserved
saved state. These successes do not erase the failed withdrawal.

The mDNS capture contains 34 packets, matching its capture/filter counters.
The diagnostic capture contains 207 packets, matching tcpdump's captured count;
its filter counter is 221. Both report zero kernel drops. The 14-count diagnostic
difference is retained; zero reported kernel drops does not establish complete
radio delivery. No inference about the missing goodbye rests on that diagnostic
capture; the separate mDNS capture supplies that observation.

Resource errors remained zero in sampled network pools and TLS status. Allocated
heap was 15,696 bytes initially, 20,496 at final USB observation, and ranged from
20,496 to 50,576 after enabling. The differing allocation levels are retained;
this single short run neither proves a leak nor establishes leak freedom.

The goodbye failure therefore occurs even with both Linux and Pico on
Bohica-IoT and the recovery service stopped. Different SSIDs are not required to
reproduce it. This does not locate loss between the Pico send/lifecycle path,
radio, AP or mesh. The earlier intermittent ARP/TCP/NSS recovery failure was not
reproduced during this one same-SSID recovery and remains unexplained.

## Restoration and adversarial assessment

The original Bohica connection was restored and its temporary replacement
removed by 20:40:23.288333 UTC. The recovery timer was started and verified
active/enabled before the independent fallback timer was cancelled. The journal
records recovery-service execution again after restoration. No reboot was
performed: reboot behavior is supported by preserved enabled configuration,
not a new physical reboot test. The fallback timer was armed and cancelled;
its emergency firing path was not exercised.

Final verification confirms USB wlan1 on Bohica, `.117`, gateway `.1`, metric
100, onboard wlan0 disconnected, original profile UUID, and unchanged resolver
SHA-256 `bbea1627272790a4e1c4b7256f398ab0d931f3bdf106598d75eb19dd968ede25`.
Five additional gateway probes returned without loss. Native Mac resolution and
certificate/hostname-verified Pico HTTPS pass. The installed wsprrypi service is
active, provider output is false, and the binary/INI hashes remain
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273` and
`e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8`.
All observers completed or were stopped and their private artifacts retrieved.

The first review verified timer pause versus persistent enablement, independent
local restoration, SSH loss independence, unchanged connection/source MAC,
continuous SSID/profile/BSSID observations, complete device-record coverage,
USB/HTTPS identity and authority, captured versus attempted goodbyes, native
cached versus negative results, original failure retention and cleanup. Eight
altered controller records were refused: SSID/profile drift, observation gap,
controller failure, failed restoration, persistent disable, lost boot enablement
and inactive recovery timer. The original controller record passes its audit.

The second assessment reran the evidence analysis, confirmed the maintained
B2/D2 checker refuses this failed attempt, and checked the packet count caveat,
allocation difference, delayed Mac removal and one-run causal limits. WTP
contract validation passes 23 schema, 7 raw JSON, 1 framing and 8 transition
cases. No firmware or maintained test code changed; no physical reliability
repair is claimed. The report retains all observed failures and incomplete
qualification boundaries.

Private evidence is bound by the [artifact hash index](phase11-4-same-ssid-evidence.json).

| Remaining item | Required work |
| --- | --- |
| B2/D2 | Investigate lost goodbye delivery and intermittent ARP/TCP/NSS recovery; repeat affected acceptance after an evidenced repair. |
| D1 | Real DHCP address change and same-name/identity recovery. |
| E1 | Second physical Pico with independent identity and trust. |
| Overnight stability | Sustained web/USB responsiveness and controlled memory observations. |
