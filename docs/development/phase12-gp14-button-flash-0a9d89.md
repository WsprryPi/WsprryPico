# GP14 diagnostic delivery to Pico 0a9d89

Status: **SERIAL-TARGETED FLASH VERIFIED; IDLE TWO-CORE CONTINUITY OBSERVED;
NO BUTTON GESTURE TESTED** (2026-09-29). The operator authorized “Flash
0a9d89” after the exact normal GP14 diagnostic image was identified. This was
an image delivery and idle observation, not RF shutdown, reset, SoftAP or
button acceptance. P12.7, P12.11 and Phase 12 remain open.

## Exact target and image

- Target: Candidate B, Pico 2 W / RP2350 QFN60, USB serial and ROM chip ID
  `CDDBF8767C506C07`, application device ID
  `29f20b7342051ef947aa56cb9d4fab42`, local suffix `0a9d89`.
- Host: `wspr5`; the other Pico, serial `0BF4B4AEC9FFB344`, remained
  enumerated and was not addressed.
- Source repository HEAD: `f58d9eeb43a849d324031e4e0549b67c54154f58`.
  The image embeds its clean source commit
  `17851aee2db1d68e69c40d75ad2ee1d7f293c7e1` because the final commit
  only recorded hashes. Normal diagnostic UF2 SHA-256:
  `d1a97341ddad1e9b526968db84f0f6ac2a236f1672f02e4310a620c916ef28a2`.
  The transferred 128,512-byte copy on `wspr5` matched that hash.
- Engine/mode: this separate image links no RF engine, Wi-Fi, SoftAP or
  settings writer; both cores execute the XIP flash workload. The pinned
  RP2350 SDK default system clock is 150 MHz; this diagnostic has no target
  clock readback. No GP14 wire, jumper, button press or RF output was used.

## Preflight and preservation

The identity-bound Console `INFO` on B reported revision `5aab673a8f0f`,
network-only profile generation 1, healthy access generation 1, station
address `192.168.1.53`, an empty job with no schedules, the
`inhibited-standalone-simulator` engine and `output_active=false`. B accepted
its own `BOOTSEL` Console command. ROM `picotool info -d --ser
CDDBF8767C506C07` reported the same chip ID and 4096 KiB flash.

The existing `wspr5` picotool SHA-256 was
`4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`.
Before loading, `picotool save -a -v ... -t bin --ser CDDBF8767C506C07`
saved and verified all 4,194,304 flash bytes with `OK`. Private copies at
`/home/pi/gp14-button-0a9d89-20260929/before-flash.bin` and
`build/gp14-physical-0a9d89-20260929/before-flash.bin` each have SHA-256
`c47eb7b69f33348343894d876abdbbe0ebc2d049ff2d465636a347a4e1401413`.
Both files are mode 600 in private evidence directories. They contain the
device's prior firmware and settings and are intentionally ignored by Git.

The UF2 payload check passed for the reserved application range below
`0x103f3000`, apart from the pinned RP2350-E10 workaround block. The linked
FLASH region ended at `0x103f3000`, below profile and other reserved storage.
No erase-all command was issued. These checks and the full backup preserve a
recovery path; the diagnostic has no settings reader, so saved settings were
not independently read back after installation.

## Load and idle observation

The exact command on `wspr5` was:

```sh
/home/pi/phase11-4-e1/picotool-build/picotool load -v -x \
  /home/pi/gp14-button-0a9d89-20260929/gp14-diagnostic.uf2 \
  --ser CDDBF8767C506C07
```

Picotool completed byte verification with `OK` and rebooted the application.
The new USB CDC device enumerated as
`usb-Raspberry_Pi_Pico_CDDBF8767C506C07-if00`. Six seconds of read-only USB
observation yielded three complete `GP14_DIAG` reports: boot 1,
`prior_watchdog=0`, `held=0`, `events=0`, no fault word. Core-0 flash reads
advanced from 62,962,944 to 68,941,312; core-1 reads advanced from
65,356,800 to 71,503,360. Both digests changed. The largest reported
sample gap was 1,565 microseconds. A partial first line from attaching to a
live stream was excluded from this assessment. This shows short idle
continuity, not arbitrary-press timing or a proven latency bound.

Private raw evidence is retained in the two directories above: preflight
`INFO`, ROM transition, picotool load log, full flash backup and local
`postflash-usb.log`. A local audit checked the exact identity, inactive
preflight, backup size/hash, picotool `OK`, and increasing counts in all three
complete status reports. The diagnostic remains installed on B. The original
settings are backed up but not restored; this image intentionally offers no
network or SoftAP service. No press, stuck hold, watchdog injection or
post-release continuity test was authorized or run. Those are separate
physical gates under the [bounded procedure](phase12-gp14-button-diagnostic.md).
