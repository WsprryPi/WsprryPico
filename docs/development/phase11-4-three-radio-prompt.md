# B2/D2 controlled three-radio acceptance prompt

Review WsprryPico devel at `62bc1b9c532cb73a6d2e8304ab5b5bb604746169` and
preserve all preexisting user changes. Read the project contract, architecture,
current acceptance matrix and latest D1 evidence before implementation. Use the
user-authorized wspr5 Ethernet management connection and all three available
Wi-Fi radios. Keep the Mac on its existing network; it is not a required observer
for this Linux-scoped campaign. No router or mesh configuration changes.

Use onboard wlan0 (`2c:cf:67:62:76:66`) as the known-working temporary 2.4 GHz
channel 11 WPA2/CCMP AP. Use USB wlan2 (`e8:4e:06:ae:d7:09`) and USB wlan1
(`90:de:80:47:b9:da`) as two independent native Linux clients, each with a separate
network namespace, mount namespace, Avahi daemon and resolver socket. Static
client addresses are 10.77.14.2 and .3; only Pico A receives DHCP at .10. The AP
has .1, no forwarding/NAT/default route, and supplies local NTP. Keep Ethernet
eth0 (`2c:cf:67:62:76:64`) and WsprryPi available throughout. Save wlan1's existing
Bohica-IoT profile, BSSID and power setting, suspend only the Wi-Fi recovery timer
and service while that adapter is reassigned, then restore and verify them.
Arm independent, bounded restoration before the first mutation.

Admit only Pico A, serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, name
`wsprrypico-0a60df.local`, reviewed runtime `802c91a7b86e-dirty`, standard inhibited
simulator UF2 SHA-256
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`.
No flashing, RF, job loading or arming. Require fresh identity-bound USB INFO and
WTP inactive/empty/unowned authority before configuration. Temporarily configure
the private AP and reboot for that configuration, then hold its boot identity
unchanged through every acceptance case. Preserve station, schedules, watermark,
expiry and disabled output. Pico B is a read-only comparator. An unexpected
recovery boot blocks further device mutation and must retain its breadcrumbs.

Run eight full cases on the same boot. Before each OFF, qualify both client paths,
native NSS results, certificate-verified WTP and HTTPS, and actual captured Pico
A answers at all three NICs. Capture mDNS and ARP/DHCP/TCP independently at each
NIC. Sample USB INFO independently every 250 ms with a two-second maximum
coverage gap; retain raw WTP frames and contiguous NETTRACE records. Network
failure must not stop USB observation.

Each case uses WIFI OFF, 150 seconds of outage, and six distributed native
negative lookups per peer at 3, 10, 40, 80, 125 and 145 seconds. D2 requires the
actual matching TTL-zero A/PTR goodbye at every NIC, absence of native cached
answers promptly after the goodbye grace period and beyond the old 120-second
TTL, and three same-name recovery probes plus announcements. WIFI ON must yield
local activation within 40 seconds. Wait for the existing TLS clock-admission
condition without extending the 120-second recovery deadline. B2 requires both
native resolvers to return only the Pico, followed by authenticated WTP/HTTPS
checks at least five times per peer spanning 30 seconds within that deadline.
Serialize authenticated clients to avoid turning recovery acceptance into a TLS
capacity test. Resume a distinct, stable logical WTP session for each peer across
connections and cases, with fresh request IDs. Do not allocate a new retained
session for each status poll. Record first failures; later success cannot erase them.

Stop the campaign at the first failed case or observer/identity/path defect.
Inspect USB boundaries and all three NIC captures before deciding whether any
separate diagnostic action is justified. Retain incomplete/failed raw evidence
privately. Do not restart a failed case under the same evidence directory.
Eight clean cases can qualify this bounded controlled topology; they cannot
explain historical failures on other infrastructure or establish overnight
stability. Report B2 and D2 separately, and state the remaining scope precisely.

Restore Pico A to Bohica-IoT and all three radios to their original roles; verify
both Picos over USB, saved state, wlan1's original profile/BSSID/power, active and
boot-enabled Wi-Fi recovery, working Ethernet and ordinary Wi-Fi management,
WsprryPi service, and absence of owned AP, namespaces, captures and test NTP
access. Keep raw captures, credentials and images ignored/private. Maintain only
the procedure, reusable tools, sanitized working results and evidence hashes.
Adversarially review implementation and evidence, fix actionable issues, rerun
affected checks and reassess. Commit and push only owned changes, preserving
preexisting user files byte-for-byte. Report actual outcomes and repository state.
