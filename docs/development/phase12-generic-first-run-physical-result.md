# Phase 12 generic first-run: Candidate A RF-inhibited result

Status: **PASS for the bounded, truly erased generic first-run and read-only
open-AP path** on 2026-09-26. Network credential entry, home Wi-Fi join,
owner claim, phone acceptance, AP/STA coexistence and Stage B remain open.

## Exact source, image and fixture

- Candidate A was Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`, BOOTSEL
  chip ID `0x0bf4b4aec9ffb344`, device ID
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, station MAC
  `88:a2:9e:0a:60:df` and SoftAP SSID `WsprryPico-0a60df`.
- The tested source was `devel` base `5977c98755f6` plus the first-run source
  patch (SHA-256 of `git diff` over `src/provisioning`,
  `src/standalone/pico/main.cpp` and `tests/provisioning_tests.cpp`:
  `147799892272dac881f08183113699ed9ed76c5cb02c9910d7f05c9ba8db38c6`).
  The RF-inhibited UF2 SHA-256 was
  `a5ceb160449553435bcede8d74f1be73484870f181b328a5e8d9eb4fecae7244`.
  The running image identifies itself as `5977c98755f6-dirty`; the UF2 and
  patch digests, rather than that shortened revision, identify the exact test.
  The build used Pico SDK 2.3.1 commit
  `079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1.
- `wspr5` used only isolated `wlan2` for association. Its management interfaces
  `eth0` and `wlan1` remained connected. Comparator USB serial
  `CDDBF8767C506C07` stayed present and untouched.

## Operation and observations

Candidate A initially reported the prior read-only image `e481bac807ab`, an
explicit unprovisioned profile generation 1, erased access state, an empty
job, inhibited simulator and `output_active=false`. The operator had already
authorized clearing Candidate A's saved state and, while away, explicitly
authorized autonomous testing from a Pi. An identity-bound Console command
moved only Candidate A to BOOTSEL; picotool confirmed the exact RP2350 chip ID.
Picotool erased all 4,194,304 flash bytes, loaded the candidate UF2, verified
it and rebooted. **No profile or access journal was seeded.**

The first boot reported `provisioning_source=unprovisioned`, profile generation
`0`, `provisioning_fault=0`, erased access generation `0`, checked radio
identity, no station config, no schedules, empty unowned job, inhibited engine,
healthy storage and `output_active=false`. The compiled generic image exposed
no station TLS listener and reported `deployment_identity_matches=false`.

| Check from `wspr5` | Result |
| --- | --- |
| AP beacon | `WsprryPico-0a60df`, BSSID `88:a2:9e:0a:60:df`, channel 3, no advertised Wi-Fi security. |
| Passwordless association and DHCP | A fresh `wlan2` profile with no security method joined and obtained `192.168.4.16/24`, DNS `192.168.4.1` and no default route through `wlan2`. |
| AP DNS | `captive.apple.com` A returned one `192.168.4.1` answer; AAAA returned no answer. |
| Captive probe | Plain-HTTP GET for `captive.apple.com/hotspot-detect.html` returned `302` to `http://192.168.4.1/` with no-store behavior. |
| Local page | The first run's `GET http://192.168.4.1/` returned 200 with the correct device ID and read-only recovery text. The final-source repeat returned 200 from the same unchanged handler. |
| Mutation rejection | JSON POST to the local page returned `405` and `read_only`; no station credential form was exposed. |
| Resource and output readback | No allocator failures or lwIP pool errors; final job empty and `output_active=false`. |

After the last source repair, Candidate A was again chip-ID checked, fully
erased, loaded and verified with the UF2 digest above. The complete host AP
status checks passed again. A subsequent Console reboot retained unprovisioned
generation `0`, erased access generation `0`, empty job, healthy storage,
inactive output and the open AP beacon. The temporary `wlan2` profiles and
remote UF2/probe files were removed; `wlan2` ended disconnected.

The selected iPhone was not used during this run because the operator was
away. The earlier phone observation on a different, explicitly seeded image
still establishes only passwordless association and automatic captive launch
for that image. This run closes the generic **full-erase source-selection** gap
on Candidate A and does not qualify the future encrypted form or station join.
