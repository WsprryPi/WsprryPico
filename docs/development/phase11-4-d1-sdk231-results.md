# D1 assessment on SDK 2.3.1 — 2026-09-10

**D1 remains open.** Native Chrome reproduced Orbi's HTTP 400 on two distinct
LAN form contexts before a new DHCP lease could be requested. The temporary
A-only reservation was removed and its absence verified with a fresh LAN page.
No Pico Wi-Fi cycle, reboot, flash, job or RF operation was performed in this run.
This is a router-admission failure, not evidence of a Pico DHCP failure or repair.

The [orientation review](phase11-4-d1-sdk231-review.md) preceded implementation.
The [comprehensive prompt](phase11-4-d1-sdk231-prompt.md) was executed through its
blocked-prerequisite branch. The [evidence manifest](phase11-4-d1-sdk231-evidence.json)
binds current observations to exact devices, images, boots and private raw files.
Source base is `f11e2166e8de79d77540ec3e59df110f0e76d892` on `devel`.

## What changed

`tests/network_adapter_tests.cpp` now exercises the actual `PicoNetwork` adapter
with pinned lwIP, changing the netif address while the simulated link stays up.
It requires automatic reprobe, unchanged hostname, positive A records containing
only the current address, suppression after address loss, and correct publication
after address reacquisition. The test does not manually reconstruct the mDNS
registration and requires no extra radio disable. No production implementation,
SDK or firmware changed.

This closes a software integration coverage gap. It does not emulate a DHCP
server or qualify physical delivery, native resolver caching, production-client
reconnection or Chrome at a new address.

## Physical execution and restoration

Both targets were Pico 2 W/RP2350, default 150 MHz system clock, existing SDK 2.3.1
images built with GCC 15.3.1, runtime `dbf1d86f0885-dirty`, engine
`inhibited-standalone-simulator`. No RF mode was selected. Per-board UF2/ELF hashes
were rechecked against the previous deployment manifest; a shared revision string
alone does not identify these images.

| Target | Stable hostname | Observed address before/after | Boot before/after |
| --- | --- | --- | --- |
| A, USB `0BF4B4AEC9FFB344` | `wsprrypico-0a60df.local` | `192.168.1.47` | `3bb4bd7cb18af1e396fa4bf3ad5e5da6` |
| B, USB `CDDBF8767C506C07` | `wsprrypico-0a9d89.local` | `192.168.1.53` | `6a0eca7714ee24db9aff824dd8ffb11b` |

All network testing used Bohica-IoT. Initial/final wspr5 checks show USB `wlan1`,
profile `921301fe-cdfd-4965-8ac7-c96e9d908ea6`, host MAC `90:de:80:47:b9:da`,
address `192.168.1.117/24`, BSSID `7a:cd:d6:f2:f6:c5`, 2432 MHz. Both Pico
NETLINK samples identify that BSSID. The Mac's association was user-confirmed.
`wsprrypi.service` remained active; `pi-wifi-recover.timer` was active and enabled
at both checks. Neither service nor the host network profile was changed.

1. Fresh USB INFO and WTP HELLO/CAPS/STATUS established exact identities,
   inhibited engine, empty/unowned/inactive state and disabled schedules. Linux
   native resolution and authenticated WTP/HTTPS passed for both targets. Mac
   native resolution and certificate-verified HTTPS passed for A. Actual Chrome
   reload showed transient Connecting/Unknown, then Connected with empty/inactive
   status at the original hostname/address. These are baseline observations only.
2. Authenticated native Chrome showed RBR850 firmware `V7.2.8.2_5.1.18`, LAN
   `192.168.1.1/24`, DHCP enabled, pool `.2`–`.254`, no reservations, and no
   attached-client entry for `.247`. Three duplicate-address probes received no
   responses; this supplemented the router inventory, not a standalone guarantee.
3. Native Chrome Add saved only A's MAC `88:a2:9e:0a:60:df` at `.247`, preserving
   its existing router label `phase11-4-d1-temporary`. Apply from the returned
   form produced **HTTP 400 Bad Request**. A fresh direct LAN Setup GET still
   showed that exact row, but its Apply also returned **HTTP 400 Bad Request**.
   The targeted second attempt did not establish a stale-form workaround.
4. No dependent Pico cycle or production-client transition followed. Native
   Chrome Delete removed the exact temporary row. A fresh direct LAN Setup GET
   confirmed the empty original table and unchanged LAN, DHCP enablement and pool.
   No router restart or global lease operation was attempted.
5. Final serial-bound USB INFO/WTP established the same boot, address, saved
   station/schedules/watermark/expiry, healthy storage and empty/unowned/inactive
   state on each board. Linux native resolution and authenticated WTP/HTTPS passed
   again for both boards, with the same server fingerprints. These are bracketing
   samples, not a continuous USB monitor or a lease-change acceptance result.

An independently bounded wspr5 admission capture retained 801 full packets,
with zero kernel drops reported. It covers approximately 156 seconds around
router admission, not a DHCP transition. Its unit was stopped successfully and
is inactive. Raw captures and peer/USB records remain private under
`build/phase11-4-d1-sdk231/`; committed metadata contains their SHA-256 hashes.
Router credentials, session tokens and unrelated client inventory are excluded.

## Validation and adversarial reassessment

Seven relevant CTest targets pass: `mdns_tests`, `network_tests`,
`mdns_lwip_tests`, `network_adapter_tests`, `network_adapter_mac_error`,
`network_adapter_mac_invalid` and `network_certificate_tests`. The existing
SDK-configured host build was used:

```sh
cmake --build build/phase11-4-b2-delivery/host-sdk231 --target network_adapter_tests
ctest --test-dir build/phase11-4-b2-delivery/host-sdk231 --output-on-failure \
  -R '^(mdns_tests|network_tests|mdns_lwip_tests|network_adapter_tests|network_adapter_mac_error|network_adapter_mac_invalid|network_certificate_tests)$'
clang-format --dry-run --Werror tests/network_adapter_tests.cpp
git diff --check
```

Adversarial review found that checking only the first DNS answer could miss a
stale additional A record. The observer now parses every answer, authority and
additional record with the pinned lwIP name parser, validates bounds and the
cache-flush class, and checks all positive A addresses. IPv4/UDP header bounds
were also added before parsing. A second assessment exercised two private compiled
implementation mutants: suppressed address-change notification plus a cached old
address, and retention of a nonzero address after address loss. Both fail the new
state-transition assertions. An initial mutant compilation failure was retained
but not counted as behavioral evidence. Affected tests and mutations were rerun
after the final change.

Final reassessment found no remaining actionable defect in this delivered
test/document slice. It specifically rejected promoting saved router state,
unchanged-address peer success, software simulation or source review into D1
acceptance. The external admission blocker remains open. Existing user edits to
the shutdown results and untracked soak document/script were preserved byte for
byte and excluded from this commit.

## Remaining roadmap

| Item | Repository ownership | Status | Remaining work |
| --- | --- | --- | --- |
| D1 | WsprryPico acceptance; WsprryPi production client | Open, router admission blocked | Obtain a usable actual DHCP reassignment, then prove same-name/trust discovery and production/Chrome recovery at the new address |
| B2 | WsprryPico transport; WsprryPi integration | Open | Explain and repair intermittent delivery/recovery failures and complete the required eight-case evidence |
| D2 | WsprryPico shutdown/discovery | Open | Establish repeatable complete shutdown/goodbye/cache/recovery results; four prior no-reset observations with one complete pass do not close it |
| E1 | WsprryPico identity; WsprryPi trust/client | Bounded pass | Preserve existing two-board scope; end-user Windows provisioning remains unimplemented |
| Eight-hour soak | WsprryPico and WsprryPi | Incomplete | Complete an uninterrupted eligible run after the prerequisite repair gates |

The next D1 attempt needs a concrete change in the router admission path or a
separately authorized DHCP arrangement on Bohica-IoT. Repeating unchanged Apply
requests or cycling Picos before that prerequisite is satisfied adds no useful
new-address evidence. This run does not identify why Orbi rejected the form.
