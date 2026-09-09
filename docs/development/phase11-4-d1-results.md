# Phase 11.4 D1 execution and adversarial review

D1 remains **OPEN**. The real production client passed its hostname/TLS baseline,
but Orbi rejected the temporary DHCP assignment with HTTP 400. The Pico never
obtained the proposed new address. The temporary reservation was deleted and
ordinary DHCP recovery was verified. No new-address acceptance is claimed.

The [execution prompt](phase11-4-d1-prompt.md) was executed on 2026-09-09 from
clean Pico `bf6d000e821014724aecbf9eb4bdad41775d8db4`. The independent Pi checkout
was read only at `89f23e5d10c8a46ead9f37c7cefa8867280ac4df`. Private artifacts are
under `build/phase11-4-d1/`, bound by the [hash index](phase11-4-d1-evidence.json).
Raw captures, credentials, generated binaries and local helpers remain outside Git.

## Identity and bounded authority

The target was Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344` on wspr5,
device `fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, name
`wsprrypico-0a60df.local:18443`. Console and persistent USB WTP observations
confirmed revision `5ee5bcf93c56-dirty`, matching deployment identity, healthy
storage and the standard `inhibited-standalone-simulator` engine. Boot remained
`cebcd4720cd9919a7cfaff492b717a85`. Firmware was not reflashed. The installed
UF2/ELF identities remain the previously recorded deployment hashes:

- UF2: `2711a54ba57b7754907a5e20dd84d6920dcb5ffe8524c69b8ff2ae569a0686e4`
- ELF: `f21db5220cd403a2306122e9f121e61a6853ab04e8c1810145440363dc26ed65`
- Server certificate: `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`
- Existing CA: `2ef7ec890d48e9283286ee09c6b549756f3d3cff530e5cb030ced6ae4c40442b`

The user's specific D1 execution request and prior all-tests/USB/Wi-Fi/capture/
service approvals covered the bounded test. The original handoff forbids using
a reservation to avoid DHCP acceptance. It does not prohibit a temporary,
Pico-only reservation used to force the actual transition and then removed.
The later plan's blanket prohibition was corrected to preserve that distinction.
No unrelated client, DHCP pool, subnet, AP security, trust store, GPIO or RF
setting was changed. No global router restart or reset was attempted.

## Router and physical outcome

The signed-in Chrome page identified Orbi RBR850 firmware `V7.2.8.2_5.1.18`,
LAN `192.168.1.1/24`, DHCP enabled with pool `.2`–`.254`, and initially no
reservations. The attached-device list had no `.247` assignment; three bounded
ARP duplicate-address probes also received no replies. Those probes alone were
not treated as proof of availability.

Only the Pico received the temporary table entry `.247`, named
`phase11-4-d1-temporary`. Add saved the exact row. Three LAN Apply attempts,
including a fresh native Chrome reload, returned **400 Bad Request** with
“This server does not support the operation requested by your client.” The
saved row did not establish an effective DHCP assignment. NETGEAR's documented
[reservation procedure](https://kb.netgear.com/000070386/How-do-I-reserve-an-IP-address-on-my-Orbi-WiFi-system)
requires Apply and client lease reacquisition; the observed router response
prevented completing that procedure. Router firmware root cause is unproven.

| Run | Observation | Disposition |
| --- | --- | --- |
| `d1-change-20260909T170920Z` | Idle USB Wi-Fi off/on; same boot and `.47`; 23 captured packets, zero drops; no captured DHCP transaction or positive Pico A announcement; Mac removed `.47` and did not re-add it during the bounded observer | Failed expected-new-address assertion; D1 not accepted |
| `d1-cleanup-20260909T172230Z` | After deletion and fresh verification of an empty reservation table, idle Wi-Fi off/on; eight packets, zero drops; Pico DHCP Discover and Request for `.47`, then same-name probing and a positive cache-flush A announcement with TTL 120 | Bounded ordinary-DHCP cleanup PASS at `.47`; no server Offer/ACK captured |

USB final state, successful Linux NSS and authenticated HTTPS independently
confirmed the cleanup address and identity. Missing unicast DHCP replies are
not invented. This does not establish reliable repetition or fix the previous
D2 recovery failure. The router's final reservation table, subnet and pool match
the initial state; ordinary operation retains no test reservation.

The Pico uses the IoT SSID while the Mac and wspr5 use the main SSID. Successful
cross-SSID reads establish that communication is possible. They do not prove
reliable multicast/radio forwarding, and the different SSIDs do not by themselves
establish isolation as the cause. That investigation remains separate from the
router's rejected LAN form submission. No SSID or isolation policy was changed.

## Production, Mac and Chrome evidence

The actual isolated WsprryPi source was
`923ab570fe53ef2ccca7d12e519c9dc36adf7e93`, executable SHA-256
`993ad62def487e5f03d82a5a7a1f5f82b972b16bd36eaa5b0d9a8c13a7166323`, with the
existing original controller identity. Invocation records bind the private
configuration and observer hashes. Transmit was false and Enable on Boot Never;
GPIO controls were disabled. Each bounded service pause restored the installed
service through the wrapper's cleanup path.

| Production attempt | Result |
| --- | --- |
| `d1-production-before-20260909T170348Z` | Hostname startup failed: resolver reported another lookup outstanding. The wrapper then mishandled a null identity. Both failures are retained. |
| `d1-production-before-20260909T170622Z` | The initial observer incorrectly assumed `SSL_get_fd()` exposed a socket for the client's custom BIO. The attempt failed; its exact process exit code was not retained, so no specific exit code is claimed. |
| `d1-production-before-20260909T170740Z` | After correcting the observer, actual production startup resolved `.47`, authenticated the unchanged DNS identity/server certificate and reported the exact Pico device/boot, empty and unowned. |

The corrected observer only records successful TLS I/O and peer-certificate
fingerprints; it does not replace resolution or TLS identity checking. Strict
CRC/schema/frame decoding found exactly HELLO, STATUS, CAPS, STATUS, STATUS and
matching replies. No LOAD or ARM occurred. USB before/after observations supplied
independent authority. No production-after-new-address case was run because its
prerequisite never occurred.

Native Mac resolution and certificate-verified HTTPS passed before the attempt
and after cleanup, with HTTP 200 and the same boot. Actual Chrome retained the
previous `ERR_ADDRESS_UNREACHABLE` and, on the cleanup reload, displayed
`ERR_BLOCKED_BY_CLIENT`. The latter indicates a client-side block, but its source
has not been established. Neither Python HTTPS nor Linux production success
substitutes for Chrome acceptance. Browser URL policy blocked internal DNS-page
inspection; no workaround or security-warning bypass was attempted.

## Review, repairs and reassessment

The first adversarial review found the observer's custom-BIO assumption and the
wrapper's null-identity reporting defect. Both were corrected before the passing
baseline. A copied dry-run description also incorrectly mentioned a QRSS job;
it was corrected to describe the actual read-only execution. Failed attempts
remain in the evidence index.

The offline audit reuses the maintained strict WTP frame/CRC/schema and DNS
parsers. It verifies actual hostname configuration, executable identity, server
fingerprint, bound replies, independent USB state, saved-state equality, allowed
Console/WTP operations, provider restoration and router cleanup. The second
assessment added explicit cleanup DHCP/announcement checks and packet-count
agreement with tcpdump. Fifteen altered-evidence cases were rejected, including
hidden network/USB ARM, wrong certificate/device/boot, literal-IP substitution,
unknown output, changed saved power, missing reply, capture drops, leftover
reservation, stopped service, false transition PASS, missing announcement and
wrong requested DHCP address. The final audit and repeated assessment passed
for **baseline and cleanup only**, explicitly leaving D1 open.

Final host verification at 17:24:45 UTC found `wsprrypi.service` active with
authoritative provider output disabled. Installed binary SHA-256
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273` and INI SHA-256
`e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8` were unchanged.
All bounded candidates/captures exited. The Pico remained Wi-Fi enabled,
empty/inactive/unowned, with AA0NT/EM18/power 20, disabled 120/0 schedule, expiry
zero and watermark `1788714601000000000` preserved. No overnight memory or RF
qualification follows from these short observations.

## Remaining work

| Item | Remaining requirement |
| --- | --- |
| D1 | Working Pico-only DHCP reassignment mechanism; actual new address, same-name peer/Chrome/production recovery and cleanup |
| B2 / D2 reliability | Diagnose intermittent resolver/ARP/TCP recovery and the separate Chrome block; establish repeatable recovery |
| D3 | Actual selective Pico radio/link loss, natural stale-cache expiry and recovery |
| E1 | Second physical Pico; distinct names/device identities and independent trust rejection |
| Startup / overnight stability | Sustained connectivity and Pico memory observations; diagnose the reported web unresponsiveness |

Phases 11.5 resource/contention, 11.6 conducted RF and 11.7 final joint closure
remain separate. This slice changes documentation and private acceptance tools,
not firmware, protocol, UI or production-client source.
