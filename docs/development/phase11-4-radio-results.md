# Working three-radio setup and DHCP reconnect correction

The controlled setup now provides Ethernet management, an independent wireless
client, and a passive radio capture. A real same-boot DHCP reassignment and
authenticated production connections at both addresses are verified. The
firmware correction below passes host regression and image checks. After the
user approved the exact inhibited image, Pico A was flashed and passed the
bounded new-address Linux reference and production-client checks. Full D1
remains open for native Mac/Chrome acceptance.

The [execution prompt](phase11-4-radio-diagnostic-prompt.md) defines the scope.
The [sanitized manifest](phase11-4-radio-evidence.json) identifies the private
evidence. This record concentrates on the working setup and verified results.

## Working configuration

| Role | Interface and identity | Verified configuration |
| --- | --- | --- |
| Management during testing | wspr5 Ethernet, `2c:cf:67:62:76:64` | Mac-to-Pi link-local IPv6 SSH; Mac retains its normal connection |
| Controlled AP | USB `wlan2`, `e8:4e:06:ae:d7:09` | `WsprryPico-Test`, channel 11, WPA2/CCMP, `10.77.14.1/24` |
| Independent client | Onboard `wlan0`, `2c:cf:67:62:76:66` | `10.77.14.2`, separate network/mount namespaces and native Avahi/NSS |
| Radio observer | USB `wlan1`, `90:de:80:47:b9:da` | Associated station without an IP address; passive `radiomon0` on the same PHY, with control/other-BSS capture |

The associated station supplies the monitor's channel context. Admission
requires captured AP beacons and actual AP/client data. The corrected-image
capture contains 2,855 valid decoded frames and Pico data; its serial trace
contains contiguous events 1–222. Initial Pico authentication was not captured,
so absent reassociation frames cannot establish that no reassociation occurred.
Functional DHCP/client acceptance is supported independently of this radio
coverage limit. Neither capture completeness nor successful radio delivery is
inferred from a driver's submission result.

The opt-in fixture is `scripts/phase11_4_radio_diagnostic.py`. Its commands are
`setup`, `run`, `change`, `trace`, and `cleanup`, with an explicit private
`--root` and `--run`. It requires the existing private Wi-Fi/peer inputs, helpers
and schema, plus independently audited production baseline evidence before
`change`. It is a wspr5 engineering fixture, not an end-user flashing installer.
An independent 20-minute restoration timer is armed before radio changes.
No NAT, bridge, DHCP service on the ordinary LAN, router changes or RF jobs are
part of this setup.

For normal wspr5 management, retain the existing Bohica-IoT profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, BSSID `7a:cd:d6:f2:f6:c5`, and the
previous interface-specific ARP correction. Set its Wi-Fi power saving to
**disable** (`802-11-wireless.powersave=2`), with live `wlan1` power saving off.
Five consecutive ordinary Wi-Fi SSH checks passed in 0.69–2.05 seconds each
with this setting. The original profile is backed up privately; the saved
profile comparison admits only the power-saving field and NM timestamp.
Ethernet is retained as the independent management path. After the approved
flash/test cleanup, three further ordinary Wi-Fi SSH checks passed in
0.78–4.20 seconds each, with the same saved power setting and BSSID.

## Verified Pico and client behavior

Pico A is serial `0BF4B4AEC9FFB344`, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, and certified
name `wsprrypico-0a60df.local`. On 2026-09-10, the approved standard inhibited
image was loaded and verified by picotool against A's serial. It reports
`802c91a7b86e-dirty`, SDK 2.3.1, and a 150 MHz system clock. That runtime string
comes from the pre-commit build; the artifact hashes below identify the exact
image containing source correction commit
`2f68f374e8054a34e21c978bcf39bfd15a0f6324`.

- Native Linux discovery, authenticated WTP STATUS and HTTPS status passed at
  `10.77.14.10` before the lease change. The reference window took 2.54 seconds.
- Captured DHCP REQUEST/ACK transaction `3c7ac6a9` assigned `10.77.14.20`.
  Boot `9f84b996f74af40c3e16a2e8cca0b20e` remained unchanged across the
  transition. Setup and restoration have separate, explicitly recorded reboots.
- The first new-address reference window passed in 1.76 seconds, completing
  3.21 seconds after the DHCP ACK (33.29 seconds after changing the binding,
  including waiting for lease renewal). Native resolution returned only `.20`;
  four captured positive Pico A records after the ACK advertised only `.20`
  with cache flush. Client deadlines were unchanged.
- The installed WsprryPi production binary authenticated the same Pico at both
  addresses. Its SHA-256 is
  `c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`;
  embedded revision is `48a9b92b4dfc553b61a19bdbc274d3550df6e854`.
  Each observation exchanged HELLO, STATUS, CAPS, STATUS, STATUS with five
  successful responses and zero LOAD/ARM operations. These were fresh production
  connections at each address. The certificate SHA-256 remained
  `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
- Firmware identity, stored station/schedule/watermark values, disabled state,
  healthy storage and inactive output remained consistent through the change.

This closes the bounded Linux reference/production part of D1 on the corrected
firmware. Native Mac/Chrome on the controlled network was not exercised; the
Mac kept its ordinary network connection. This single transition does not
establish B2/D2 repeatability or the eight-hour soak.

## Firmware correction and review

`PicoNetwork::poll()` no longer requests another Wi-Fi join while the SDK reports
`CYW43_LINK_NOIP`. That state means the interface and Wi-Fi link remain up but
DHCP has temporarily cleared the address. An expired reconnect timer must not
start another Wi-Fi join in that state. Genuine link loss retains the existing
reconnect behavior and delay.

The pre-correction physical trace made this defect actionable: the Pico generated a SYN-ACK
339 microseconds after receiving the connection request and submitted three
SYN-ACK attempts. The radio capture independently shows Pico authentication and
reassociation during that connection window. The first client-observed SYN-ACK
arrived about 8.79 seconds after its SYN. This supports investigating the join
decision rather than changing TCP retry deadlines. It does not identify each
encrypted radio emission or establish that this correction resolves every
earlier connectivity issue. Cross-clock offset spread was 118 ms, so no
sub-100-ms cross-clock ordering is claimed.

Adversarial review corrected the host radio mock: it previously returned UP
even with a zero IP address. The regression now reproduces DHCP address removal
after the reconnect deadline, waits 61 seconds without another join or stale
advertisement, acquires the new address, and verifies genuine link-loss
reconnection. It fails on the original adapter and passes with the correction.

Fixture review also closed stopped-service name reuse, partial-setup management
restoration, monitor-child ownership, malformed/incomplete capture rejection,
bad-FCS exclusion, refusal to reuse stale admission after cleanup, and
optimized-Python execution refusal. Reassessment found no
remaining actionable source/test finding in this slice. The approved physical
case above supplies the bounded functional verification.

Checks passed:

- All 34 configured host tests; three adapter cases under AddressSanitizer and
  UndefinedBehaviorSanitizer.
- Seventeen radio diagnostic tests and sixteen existing hotspot audit/refusal tests.
- Standard inhibited Pico A build; endpoint/flash reservation, shutdown
  interception and pinned-SDK semaphore checks; C++ formatting and whitespace.

Approved and flashed UF2 SHA-256:
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`.
ELF SHA-256:
`500996b4db93dd280ea917ee462db7e0ccf3235d2b1196b3175751f02d6c0529`.
SDK `079c6f39023649b154152db30f1d781e884879bc`, GCC 15.3.1, and Pico A's
existing MAC-suffix credentials are preserved. Only Pico A was flashed.

The post-flash adversarial evidence review independently checked DHCP transaction
identity, unchanged boot, native resolution, TLS fingerprint, production wire
operations, trace continuity and final USB authority. Eleven refusal checks
rejected altered boot/device identity, active output, failed production/reference
results, incorrect trust, truncated captures, a trace gap, incomplete cleanup
and optimized-Python audit execution. Review identified the radio association
coverage limit above and corrected the report to avoid an unsupported absence
claim. Final reassessment passed the functional evidence with that limit; no
remaining actionable finding was identified in this bounded assessment.

## Restored state and remaining acceptance

Pico A is back on Bohica-IoT at `.47`, boot
`d6605a9751502843fc4f9c41abe985e7`; comparator B remains at `.53`, boot
`4e2fb851c08b278dd4b977104d2c2aaa`. Fresh serial-specific INFO and WTP checks
verify both inhibited, disabled, empty, unowned and inactive. The test AP,
namespace and monitor child are removed. Normal Wi-Fi recovery and WsprryPi
services are active, the test time-service allowance is removed, and the
restoration timer is cancelled after verification.

| Item | Status | Remaining work |
| --- | --- | --- |
| B2 — Linux discovery/reconnection | Open; one corrected DHCP recovery passed | Verify repeatability for the broader discovery/reconnection cases. |
| D1 — DHCP address change | Linux reference and production PASS; full item open | Native Mac/Chrome new-address acceptance remains. |
| D2 — Orderly withdrawal/recovery | Open | Existing orderly-withdrawal and repeatability acceptance remains. |
| E1 — Two-board identity/trust | Bounded pass retained | No new E1 work required by this slice. |
| Eight-hour memory/connectivity soak | Incomplete | Complete the uninterrupted eight-hour acceptance run. |
