# Phase 11.4 controlled same-SSID repeat

Repeat the B2/D2 comparison after the user explicitly authorizes pausing wspr5's
Wi-Fi recovery service and requires it to resume after reboot. Begin at Pico
devel `0915647087034c280d353e016a62e3f738eb2f43`; preserve prior actual failures
and the invalidated mixed-SSID comparison. Use the existing standard inhibited
Pico image, serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, certified name
`wsprrypico-0a60df.local`, and existing private credentials. No firmware, router,
DHCP reservation, trust, GPIO, RF or installed transmitter-service changes.

Use USB dongle wlan1 (`90:de:80:47:b9:da`) for the comparison. The onboard wlan0
failed its previous health baseline and must remain excluded. Read the current
recovery timer/service and original connection. Preserve the enabled timer and
static service: stop their current execution, do not persistently disable or
mask them. Before stopping or moving connectivity, arm an independent local
ten-minute restoration timer. It must reactivate original Bohica UUID
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, remove only the test profile, and restart
the recovery timer even if association restoration fails. Bound the main
controller so it cannot remain active beyond the fallback deadline. A reboot
must retain the original recovery timer's enabled boot configuration.

Start native Mac mDNS observation outside the sandbox and require a positive
baseline before dispatch. Create a temporary non-autoconnect IoT profile using
private local credentials. Require successful Bohica-IoT association, original
`.117` DHCP source address and a bounded gateway health check. Monitor actual
SSID/BSSID/profile throughout the test; retain and invalidate any drift instead
of accepting a different path. The Mac remains on Bohica, which preserves a
separate cross-SSID observer.

Execute the existing bounded 150-second Pico Wi-Fi off/on procedure with
Console/WTP identity and inactive/unowned state, Linux mDNS and ARP/TCP/DHCP
captures, native NSS lookups and authenticated HTTPS. Preserve original failure
markers, lookup timeouts, missing packets and later recovery separately. Capture
local resource counters without claiming overnight leak freedom. Same SSID does
not establish same AP or eliminate mesh forwarding as a variable.

Restore the original USB connection and recovery timer in controller cleanup;
only cancel the fallback timer after successful restoration. Verify original
SSID, address, routes, profiles, resolver hash, timer active/enabled state and
unchanged installed transmitter service/output/binary/configuration. Verify
final Pico identity and status through authorized USB/network observations.
Stop observers, retrieve private evidence, audit packets and identity, review
adversarially, correct actionable findings and reassess. Record a hash index,
update the current review/matrix without erasing prior failures, commit/push
and report the bounded outcome and remaining work. A passing comparison alone
cannot close historical B2/D2 reliability or overnight stability.
