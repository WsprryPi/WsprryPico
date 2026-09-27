# Phase 12 Wi-Fi-only transaction source review

The approved P12.7 Safari-only path subsequently requires the network-only
AP to remain available for full setup. Current working source removes the
post-commit withdrawal override; the findings below describe the exact
`fb091f8` implementation and Candidate A image, not acceptance of the new
AP lifetime or its AP/STA resource cost.

Status: **SOURCE IMPLEMENTED AND REVIEWED; NETWORK-ONLY GENERATION-1
REBOOT READBACK PASSED; FINAL PHONE PAGE/AP-RETURN ROWS OPEN** (2026-09-27).
This is the approved network-only exception to P12.7. It does not approve
consumer ownership, station API, RF output, or the rest of P12.7–P12.12.
The exact `fb091f8` RF-inhibited image was flashed to Candidate A on
2026-09-27 and passed the bounded USB/open-AP preflight recorded in the
[target result](phase12-wifi-only-physical-result.md). The selected-iPhone
credential submission reached a station trial with an address, and the
approved restart independently selected network-only generation 1 at that
address with inactive output. The iPhone final-page result and AP fallback
remain open.

## Implemented boundary

The RF-inhibited standard image serves the local setup document only when the
blank generation-zero profile, unclaimed access state, derived identity,
inactive output and AP-local runtime gate all hold. The AP listener classifies
each TCP connection by the AP netif. Start, submit and acknowledgement use the
strict WiFi-Bootstrap/1 parser. One slot binds full device, boot, browser key,
nonce and random slot ID. A sampled runtime BOOTSEL press and release grants
it once; exactly erased access storage is initialized to a healthy unclaimed
record after that edge. The Pico decrypts one binary credential payload with
the existing PSA adapter and clears its ephemeral key.

The station trial keeps the AP running. Association plus nonzero IPv4 must be
observed within 45 seconds before one network-only journal commit. The
response is initially `checking`; read-only status is the source of truth for
response loss. `connected` requires the committed source and live address.
Failure tears down transient station credentials and permits a fresh physical
attempt after bounded terminal retention. The AP remains through status and
the authenticated acknowledgement. It withdraws after stable station service
and ACK, or after 60 seconds of stable service without ACK, and returns as a
read-only fallback on later link loss. Network-only mode starts no station
TLS/WTP/browser listener or RF job.

## Adversarial pass and repair

| Finding | Repair |
| --- | --- |
| A failed station start after credential copy could retain the attempted password and prevent a new trial. | Trial teardown now clears both station credential strings and the UDP PCB even when start failed before PCB creation. A host adapter test starts, tears down and starts a different network-only trial. |
| A rebooted generation-one device had no volatile commit flag, so its AP could remain up indefinitely despite a stable station link. | The join gate initializes from the durable journal source at boot and uses the bounded no-ACK timer. |
| AP withdrawal after ACK could close the TCP response before delivery. | Withdrawal checks the active AP response connection and only proceeds after it closes and the station has been stable. |
| A wildcard port-80 listen PCB could remain bound after AP withdrawal. | The AP server now closes its listener when the captive AP is inactive and reopens it when the read-only fallback returns; every accepted connection still passes the AP-netif classifier. |
| A journal fault during submit would leave the browser on “Checking connection.” | The page now shows a distinct setup-fault state and clears the entered SSID and password. |
| Association without DHCP could be mistaken for a complete trial. | A portable join gate requires both link and an address; host tests cover missing DHCP, timeout, response in flight, loss/recovery and reboot without ACK. |
| A source change or long scheduling delay could cancel/expire a trial slot without stopping its transient station connection; an expired terminal could retain the ACK verifier. | Cancellation and expiry now tear down an in-flight trial and scrub the bounded verifier, while a committed network-only connection remains governed by its journal. |

The second source assessment found no further actionable defect in this
bounded transaction. It does **not** establish live AP/STA coexistence,
browser crypto capability on the selected iPhone, target heap headroom during
the 50-KiB asset transfer, physical BOOTSEL behavior in this new image,
transactional reboot readback or station DHCP success. Those are separate
opt-in target gates. The RF worker image remains outside this runtime BOOTSEL
design; its independent build currently stops at the pre-existing missing
BTstack include in `gatt_transport.hpp`.

## Source evidence

- Browser crypto and flow tests: 2 passed; local bundle rebuilt.
- Host build and focused join, HTTP, wire, crypto and network-adapter tests:
  passed. The 93-case host run passed 92 in the sandbox; the sole TLS test
  could not bind loopback port 18443 there and passed when rerun with local
  loopback permission. No target was touched by these tests.
- RF-inhibited Pico 2 W cross-build passed with pinned SDK 2.3.1 and GNU Arm
  toolchain. Its link checks found one SRAM BOOTSEL callback and no linked
  core-1 launcher or reader. A cross-build is not a flashed or physical test.
- `git diff --check` and local documentation links were checked before commit.

The bounded target continuation recorded the selected iPhone's
BOOTSEL-confirmed station attempt, address and generation-one reboot
readback. Captive-sheet final completion, failed-join retry and AP return
after station loss were not exercised. The installed image remains the
RF-inhibited `fb091f8` image unless a later exact authorization changes it.
