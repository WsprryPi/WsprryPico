# Phase 12 Wi-Fi-only bootstrap: Candidate A target record

Status: **RF-INHIBITED NETWORK-ONLY JOIN AND DURABLE GENERATION-1 READBACK
PASS; FINAL PHONE PAGE AND AP-RETURN ROWS OPEN**
(2026-09-27). This is the bounded network-only exception, not P12.7 owner
commissioning, station mTLS, RF output or Phase 12 closure.

## Authorization and exact setup

The operator authorized Candidate A USB serial
`0BF4B4AEC9FFB344` for read-only USB preflight, flashing the named
RF-inhibited `fb091f8` UF2, isolated `wspr5` `wlan2` AP checks and one
iPhone BOOTSEL-confirmed home-network join. The new image is to remain
installed. The operator separately approved one identity-checked USB
`REBOOT` and `INFO`/`STATUS` readback after the phone trial. No RF output or
Candidate B mutation was authorized. The
operator's home Wi-Fi credentials are not in this record or command history.

| Boundary | Exact value |
| --- | --- |
| Target | Candidate A, Pico 2 W / RP2350, USB serial and chip ID `0BF4B4AEC9FFB344`; full device ID `fd6127d11d6aca42a9905fa3fb1bf1d5` |
| Comparator | Candidate B `CDDBF8767C506C07`, connected but not operated |
| Source | Clean pushed `devel` `fb091f8af5be`; later documentation edits do not affect the UF2 |
| Image | UF2 flashed from `build/phase12-captive-pico231/firmware/WsprryPico.uf2` at the time; SHA-256 `d262c9a92a0b7ec3be4739e50e39c8b7ac59a80f25863e4bf840e40b38a18ce2`. The build path was later overwritten by a newer unflashed source build. |
| Target build | Pico SDK 2.3.1, Arm GNU 15.3.1, `pico2_w`, `Standalone RF-inhibited fb091f8af5be` |
| Runtime | `inhibited-standalone-simulator`, boot `40ea8d3d0041a2562aa890be2b1a479e` after flash |
| AP | Open `WsprryPico-0a60df`, BSSID `88:A2:9E:0A:60:DF`, channel 3 |
| Pi host | `wspr5`; management stayed on `eth0` and `wlan1`; only `wlan2` joined the Pico temporarily |

## Preflash admission

Candidate A Console `INFO`, `STATUS` and `STORAGE` returned the expected
full identity and GET-only revision `fc9caab158b7-dirty`. The source was
unprovisioned generation 0, access journal exactly erased at generation 0,
healthy storage, no station configuration, an empty job, RF-inhibited
simulator and `output_active=false`. Config and watermark sequences were
both 0. The device was not in recovery and reported no fault stage. The Pi
showed `wlan2` disconnected while management remained connected.

The local and transferred UF2 SHA-256 matched. Candidate A's identity-checked
Console accepted `BOOTSEL`; serial-targeted picotool in ROM reported RP2350
chip ID `0x0bf4b4aec9ffb344`. Serial-targeted
`picotool load -v -x` verified the new UF2 with `OK` and rebooted only
Candidate A. No flash erase or restoration to the prior image was performed.

## New-image checks

Postflash Console returned exact revision `fb091f8af5be`, the boot ID
above, generation 0 unprovisioned source, access generation 0 erased,
healthy storage, empty job, inactive output, no recovery/fault and station
MAC `88:a2:9e:0a:60:df`. A later read before the phone action showed
the same source/generation, boot and inactive output.

A fresh `wlan2` scan found `WsprryPico-0a60df` at the exact BSSID on
channel 3 with no Wi-Fi security advertised. A temporary, BSSID-pinned
NetworkManager profile with **no security property** joined it and received
`192.168.4.16/24` plus DNS `192.168.4.1`. There was no default route
through `wlan2`; `eth0` and `wlan1` retained the host's default routes.
AP-local `GET /` returned HTTP 200 and the bundled document with local
script/CSP headers. `GET /local/v1/identity` returned the exact full device
ID. `GET /api/bootstrap/v1/status` returned unprovisioned generation 0,
`slot_state=none`, `join=idle` and `address_ready=false`.
The temporary `wlan2` profile was deactivated and deleted; `wlan2`
ended disconnected for the iPhone step.

At the prephone checkpoint, these results proved the exact new image boots
and its open AP serves the blank setup surface from an isolated Pi. They did
not prove selected-iPhone
cryptography, a physical BOOTSEL grant on this image, credential submission,
station association/DHCP, transactional generation 1, AP withdrawal or
read-only fallback after link loss. Those rows remain open pending the
phone-assisted run and post-run readback.

## Selected-iPhone attempt and durable readback

The operator joined the open AP on the selected iPhone, used the locally
served page, pressed and released BOOTSEL when prompted, and entered the home
network settings without disclosing the password in chat or commands. The
page showed **Trying your network and checking the saved result**; the
operator observed that iOS may have switched Wi-Fi networks before showing a
final page result. The iPhone model/iOS build were not reconfirmed for this
attempt and remain an evidence limit.

Candidate A USB readback in the same boot showed the access record initialized
healthy at generation 1, station link status 3 and IPv4 `192.168.1.47`,
empty job, healthy config/watermark stores and inactive RF output. The Pico
AP later disappeared from a fresh `wspr5` scan; an isolated `wlan2`
reassociation attempt timed out, and its temporary NetworkManager profile
was deleted. This matches the source's post-commit AP withdrawal condition,
which requires a `NetworkOnly` profile and live station link. However,
Console `INFO` reports the `RuntimeProfile` snapshot selected at boot,
not the live `ProfileStore` journal; it still printed unprovisioned generation
0. The observed station address and AP withdrawal were strong evidence of a
successful trial/commit, but at this checkpoint the independent durable
generation-1 readback had not yet been recorded. No second BOOTSEL press, new
credential submission or flash has occurred.

The approved single USB `REBOOT` acknowledged `ok=true` after an exact
device-ID and `fb091f8af5be` revision check. The serial port reappeared at
the same USB identity. In the new boot, `INFO` selected
`provisioning_source=network_only`, `provisioning_generation=1`,
`provisioning_fault=0`, `access_state=healthy`,
`access_generation=1`, `recovery_boot=false`, `fault_stage=0`, station
link status 3 and IPv4 `192.168.1.47`. `STATUS` reported new boot ID
`7ca4364afc34d14719959554b7bb38e8`, `state=empty` and
`output_active=false`. This is independent durable generation-one network
join readback with RF inhibited; it does not grant owner, TLS, station API,
job or RF authority. The preceding paragraph records what was unknown at
the pre-reboot checkpoint and is retained as chronology.

The operator did not observe a final **connected** screen after iOS left the
Pico AP. The iPhone model/iOS version was not reconfirmed, and AP return after
station loss was not exercised. The source change that keeps the network-only
AP available for later Safari commissioning was built after this run and was
**not** flashed to Candidate A. AP/STA continuity for that newer source is
therefore still a target gate.
