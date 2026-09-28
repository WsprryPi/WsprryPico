# Phase 12 Wi-Fi-first image flash on Candidate A

Status: **CLEAN `b14022c` IMAGE FLASHED; HEALTHY-STATION AP WITHDRAWAL OBSERVED;
PHONE FLOW OPEN** (2026-09-28).

## Follow-up clean image and AP policy check

The operator authorized commit, push and flash after the AP lifetime,
replacement-save and LED changes. Commit `b14022c77319d81b264ddf4effa4f61694ee9bf0`
was pushed to `origin/devel`; a fresh Release build from that clean commit
embedded revision `b14022c77319`. The Pico 2 W/RP2350 Arm secure UF2 was
3,299,328 bytes, SHA-256
`700909ab8bc8ed210dd3f64cb48ec2e8964c2e096a2adfb968fa14da525c5f27`.
The local and transferred hashes matched. The `wspr5` picotool SHA-256 was
`4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`.

Preflight Console `INFO` on Candidate A, USB serial
`0BF4B4AEC9FFB344`, reported device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`, prior revision
`f1ed7d34b521-dirty`, healthy consumer pre-clock generation 2,
station address `192.168.1.47`, idle inhibited simulator and inactive output.
The idle device accepted USB `BOOTSEL`. ROM `picotool info -d --ser` identified
chip ID `0x0bf4b4aec9ffb344`. Serial-targeted `picotool load -v -x` completed
flash verification with `OK` and rebooted Candidate A. Candidate B was not
addressed. No profile erase or rollback was performed.

Postflash Console `INFO` reported revision `b14022c77319`, the same device
ID and generation-2 consumer pre-clock profile, healthy access generation 1,
station address `192.168.1.47`, synchronized UTC, empty job service,
`inhibited-standalone-simulator` and `output_active=false`; boot ID changed to
`ba90f9228ba7f3bb77b7fb61791dc9c1`. Two successful isolated `wspr5`
`wlan2` scans did not see `WsprryPico-0a60df` while the station was connected.
This is bounded evidence for automatic AP withdrawal on this saved profile.
The manual BOOTSEL hold, station-loss fallback, LED pattern, repeated save and
phone captive flow were not physically exercised in this flash check. The new
image remains installed.

## Earlier Wi-Fi-first delivery

Status: **FLASH AND BOOT VERIFIED; PHONE FLOW OPEN** (earlier 2026-09-28 image).

The operator requested the new Wi-Fi-first image be flashed. This is a bounded
image delivery record, not acceptance of the captive page or either save flow.

| Item | Observed value |
| --- | --- |
| Target | Candidate A, Pico 2 W / RP2350, USB serial and ROM chip ID `0BF4B4AEC9FFB344`; device ID `fd6127d11d6aca42a9905fa3fb1bf1d5` |
| Host and connection | `wspr5` USB Console `usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00`; Candidate B `CDDBF8767C506C07` was present and untouched |
| Source/build | Uncommitted `devel` Wi-Fi-first source; Pico SDK 2.3.1 pinned complete local copy; `pico2_w`, RP2350 Arm secure, Release; firmware reports `0.0.0-devel` and `f1ed7d34b521-dirty` |
| Image | `build/pico2-w-safari-pinned/firmware/WsprryPico.uf2`, 3,298,816 bytes, SHA-256 `0c3098978de75fc2f9a70a337c34343d4d098de2f2b3b52367ee70acdf1b94da` |
| Engine/clock/mode | `inhibited-standalone-simulator`; system clock 150 MHz; UTC clock `unsynchronized`; boot ID `605dc01e1ee6c87b328ba002ddd8379e`; empty job service and `output_active=false` |
| Station/AP | Existing station address `192.168.1.47`; open `WsprryPico-0a60df` observed from isolated `wspr5` `wlan2` at BSSID `88:a2:9e:0a:60:df`, channel 3 |

Before flashing, Console `INFO` reported the exact device ID, revision
`f1ed7d34b521`, healthy consumer pre-clock generation 2, healthy access
generation 1, no recovery/fault and inactive output. The UF2's local and
transferred hashes matched. An identity-bound USB `BOOTSEL` command returned
`{"ok":true,"rebooting":true}`. ROM `picotool info -d --ser
0BF4B4AEC9FFB344` reported RP2350 chip ID `0x0bf4b4aec9ffb344`.
Serial-targeted `picotool load -v -x` verified the image with `OK` and rebooted
Candidate A. The newer image was left installed; no rollback or journal erase
was performed.

After reboot, Console `INFO` returned the same device ID, revision
`f1ed7d34b521-dirty`, consumer pre-clock generation 2, healthy access
generation 1, no recovery/fault, existing station address and an empty,
inactive RF-inhibited service. `STATUS` and `STORAGE` each returned
`profile_runtime_unavailable` in this pre-clock state; they do not establish
station/TLS activation. A `wlan2` scan saw the open AP. The phone captive
page, password reveal, Wi-Fi replacement, separate station save, and
generation/readback still require their own target check.
