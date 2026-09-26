# Phase 12 blank-AP captive landing: source and adversarial review

Status: **source-validated read-only landing; bounded Candidate A/iPhone result
recorded separately** in the
[physical result](phase12-blank-captive-physical-result.md).
This bounded change is the operator-selected best-effort captive launch for the
existing blank SoftAP. It is not the proposed [Wi-Fi-only credential
bootstrap](phase12-wifi-only-bootstrap-proposal.md), whose policy, physical
gesture, encryption, transaction and target gates remain unapproved. No device
was flashed, joined, reset or operated for this review.

## Implemented boundary

- The blank read-only AP advertises `192.168.4.1` as its DNS server in DHCP.
  A bounded DNS responder bound to the AP interface returns that address for
  ordinary IPv4 address queries and no address for other record types. It
  rejects malformed/compressed questions and uses a two-second answer TTL.
- Safe plain-HTTP GET requests with a foreign Host receive a no-store `302`
  to `http://192.168.4.1/`. The local Host still serves only the existing
  read-only identity/recovery page. Every non-GET remains rejected.
- AP mode transitions tear down the captive DNS responder before a
  provisioned surface can run. Provisioned SoftAP keeps its existing DHCP and
  mDNS behavior. The listener remains AP-interface classified; HTTPS and
  station traffic are not intercepted.
- At source commit `a8834cd4b172`, the blank AP still used its existing WPA2
  passphrase. That original change supplied no Wi-Fi credential form, browser
  encryption, physical claim, owner or station join.

## Evidence

| Check | Result and limit |
| --- | --- |
| Focused host suite | `network_tests`, `bootstrap_http_tests`, `mdns_lwip_tests`, `dhcp_server_tests`, `captive_dns_tests` and three network-adapter cases: **8/8 passed** with Xcode clang and the Xcode 26.5 SDK. Covers AP DNS option isolation, DNS packet bounds, safe GET redirect, non-GET rejection and existing network behavior. |
| Source contract | `python3 tests/network_transport_contract_tests.py` passed. |
| RP2350 Arm cross-build | `WsprryPico` and `field_access_pico_linkcheck` linked with Pico SDK 2.3.1 commit `079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1. The image was not flashed. |
| Resource observation | The lwIP UDP PCB reserve rose from five to six to cover blank-AP captive DNS. The compiler reports 1,072 bytes of static stack use in the DNS receive callback; target runtime headroom is not inferred from this source number. |
| Repository check | `git diff --check` passed after the repair pass. |

## Adversarial findings and repair

| Finding | Disposition |
| --- | --- |
| A DHCP DNS option without a live DNS service would strand captive detection. | Blank AP startup now requires both DNS and DHCP initialization; failure disables the AP. Readiness requires the DNS listener while captive mode is selected. |
| Catch-all DNS could affect station or provisioned SoftAP traffic. | The UDP listener binds the AP address and interface, checks the input interface, and is destroyed on AP stop or surface change. The DHCP DNS option is emitted only in captive mode. Hardware behavior still needs target observation. |
| A malformed or compressed DNS question could overrun a small parser. | The packet handler limits length, accepts one uncompressed question, checks every label, and drops malformed messages. The packet test covers the relevant negative cases. |
| The extra DNS listener could exhaust the previous five-PCB pool. | The reserve is six; DHCP, DNS, mDNS and network-adapter host tests pass. A target resource/concurrency run remains open. |
| The fixed browser address could drift from the SDK AP gateway and create a redirect loop or failed DNS answers. | The Pico adapter now asserts at compile time that its selected SDK AP gateway is `192.168.4.1`; the exact RP2350 cross-build passes. |
| Redirect logic embedded only in the Pico adapter would lack executable host coverage. | The read-only HTTP decision moved into a portable responder. Its test checks an iOS-style probe Host, the fixed local redirect, local identity and foreign POST rejection. |
| An automatic captive screen cannot be promised by source code. | The contract calls launch best effort and retains the fixed Safari URL. The parser currently handles HTTP/1.1 GET probes without a query string; other probe forms may not redirect. The selected iPhone/iOS run must record the actual launch and fallback behavior. |

## Reassessment and remaining gate

No unresolved source-level finding in this bounded read-only landing requires
another repair. It does **not** establish that iOS opens the captive screen,
that Safari remains associated with the Pico AP, or that AP/STA coexistence is
safe. Those require a separately authorized, finite RF-inhibited target run
with the exact board, image, iPhone/iOS, network and restoration recorded.
The later Candidate A result confirmed DHCP, AP DNS, HTTP redirect, the local
page, and operator-reported automatic captive launch and Safari fallback on one
iPhone. It also exposed the legacy factory-bundle selection after full erase;
the test required a manually seeded unprovisioned journal. That result does
not close generic blank first-run, station-join bootstrap, AP/STA coexistence
or P12.7-12.12 commissioning.

## Open blank-AP amendment

The operator then selected passwordless association for the blank read-only
SoftAP. `PicoSoftAp::start_blank` now has no password argument and passes a
null password with `CYW43_AUTH_OPEN` to the pinned SDK. The separate provisioned
`start` path still validates and uses its WPA2 password. Blank AP startup now
requires the explicit unprovisioned source, a healthy non-pending or exactly
erased access journal, no watchdog recovery, an idle/inactive job and a live
read-only HTTP listener. If that listener is absent, the prior fallback that
could advertise an unusable blank AP no longer runs. The identity page now
states only that this page is read-only and has no Wi-Fi setup form.
The unprovisioned source also suppresses the legacy standalone station
network overlay and suspends autonomous scheduling, including when an old
standalone config remains in flash.

The adversarial pass found and closed three issues during this amendment: a
faulted or pending access journal could otherwise expose the new open AP; a
failed blank HTTP listener could leave an AP with no usable page; and an
unprovisioned tombstone could otherwise reuse legacy standalone Wi-Fi and
schedules. The startup/runtime gates above close those paths. The pinned SDK
source confirms that a null
password selects open auth, while the non-null path retains WPA2. The
`bootstrap_http_tests` page assertion, runtime overlay test and the existing
focused network suite passed; the RP2350 standard image and field-access
linkcheck linked. The exact open-AP target and iPhone retest is recorded in the
[physical result](phase12-blank-captive-physical-result.md).

The all-erased factory-bundle selection remains a separate deferred first-run
cleanup. This open, read-only AP does not accept station credentials and cannot
be counted as the proposed Wi-Fi-only network-join flow.
