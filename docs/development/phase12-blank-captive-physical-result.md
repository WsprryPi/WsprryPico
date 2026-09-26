# Phase 12 blank captive landing: Candidate A physical check

Status: **Pico/AP path passed; automatic iPhone captive launch and Safari
fallback reported** on 2026-09-26.
This is a read-only captive landing check. It does not test station credential
entry or joining, owner claim, TLS setup, RF scheduling or Stage B.

## Exact target and image

- Candidate A: Pico 2 W, USB serial `0BF4B4AEC9FFB344`, RP2350 chip ID
  `0x0bf4b4aec9ffb344`, device ID `fd6127d11d6aca42a9905fa3fb1bf1d5`;
  station MAC `88:a2:9e:0a:60:df`, SoftAP SSID `WsprryPico-0a60df`.
- Source: clean `devel` commit `a8834cd4b172f8790b7a156f39d3a34803b6b43d`.
  Image: `Standalone RF-inhibited a8834cd4b172`; UF2 SHA-256
  `a4cc0b483f9b9d91abb8ac468506d1ef9afea709b487eac924db6bd3b4112340`.
  Built with Pico SDK 2.3.1 and Arm GNU 15.3.1.
- Comparator USB serial `CDDBF8767C506C07` remained connected and untouched.
  `wspr5` management remained on `eth0` and `wlan1`; only isolated `wlan2`
  joined the candidate AP for a short local check.

## Preparation and blank-state discovery

Before mutation, Console `INFO`, `STATUS` and `STORAGE` identified Candidate A
at firmware `932d10dc1c43`, provisioned profile generation 3, access generation
3, healthy config/watermark sequences 72/12, and an empty unowned job with
`output_active=false` under `inhibited-standalone-simulator`. The operator
explicitly chose to erase all saved state. The target entered BOOTSEL through
its identity-checked Console; picotool confirmed the exact chip ID, erased all
4,194,304 flash bytes, then loaded and verified the candidate UF2. No backup
or restoration of the old profile, configuration, watermark, access record or
firmware was requested.

The first post-erase boot selected the legacy factory-bundle source at profile
generation 0. Its bundled identity did not match this generic target, so
`deployment_identity_matches=false`; it did not start the blank AP. This is a
separate first-run product gap. To exercise the already implemented blank
read-only path without changing firmware, an offline helper used the project's
`ProfileStore::select(Unprovisioned)` and reloaded its own 16 KiB image for
verification. Picotool wrote and verified that exact journal image at the
reserved profile area `0x103f7000`; SHA-256 was
`27223c275cee58a6e95669505b6ebb7059ec2c7a369d06d236792368a192aae9`.
The target then reported `provisioning_source=unprovisioned`, generation 1,
erased access state, no station configuration, empty schedules and watermark,
the same RF-inhibited engine and `output_active=false`. This journal setup is
a test fixture, not proof that a fully erased consumer device can start its AP.

## AP-side results

| Check | Observed result |
| --- | --- |
| AP advertisement | `WsprryPico-0a60df` visible on channel 3; `wspr5` `wlan2` joined it. |
| DHCP | `wlan2` received `192.168.4.16/24` and DNS `192.168.4.1`; the temporary connection had no default route. |
| DNS | AP DNS returned one `192.168.4.1` A answer and zero AAAA answers for `captive.apple.com`. |
| Captive HTTP probe | `GET http://captive.apple.com/hotspot-detect.html` with the AP address returned `302 Location: http://192.168.4.1/`, `Cache-Control: no-store`. |
| Local page | `GET http://192.168.4.1/` returned HTTP 200 and the read-only recovery page with the exact device ID and firmware version. |
| Host cleanup | The temporary `wlan2` NetworkManager profile was deactivated and deleted. |
| iPhone captive launch | The operator used the same iPhone 17 Pro Max as the earlier Phase 12 phone work and reported that the page popped up automatically after a short delay on joining the AP. The current iOS build was not reconfirmed. |
| iPhone Safari fallback | While still joined to the Pico AP, the operator opened `http://192.168.4.1/` in Safari and reported that the same read-only recovery page loaded. |

The current page still directs setup through BLE or USB and the blank AP still
uses a MAC-derived WPA2 passphrase. Neither is the proposed code-free Wi-Fi-only
station-join flow. The page copy must be revised when that separate design is
approved and implemented.

## Remaining observations

The operator's automatic-launch and Safari reports are evidence for this one
phone and AP join, not a guarantee across iOS versions or devices. A post-phone
Console read still showed the same image,
unprovisioned source generation 1, empty job and `output_active=false`; lwIP
reported no memory-pool errors and the allocator reported zero failures.
Candidate A remains on the blank read-only image with the explicit
unprovisioned journal; the old state is intentionally not restored.

The legacy factory-bundle selection on fully erased flash needs a separate
design and source repair before a generic blank-device experience can be
accepted. Preserve explicit source selection, reject corrupt journals, avoid
legacy Wi-Fi/trust resurrection, and test power-cut recovery. Repeat this
physical check from an all-erased device without a manually seeded journal.
