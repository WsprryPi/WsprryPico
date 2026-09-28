# Phase 12 Wi-Fi-first image flash on Candidate A

Status: **FLASH AND BOOT VERIFIED; PHONE FLOW OPEN** (2026-09-28).

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
