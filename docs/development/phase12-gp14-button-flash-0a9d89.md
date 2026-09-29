# GP14 diagnostic delivery to Pico 0a9d89

Status: **SERIAL-TARGETED FLASH VERIFIED; TWO GP14 HOLDS OBSERVED THROUGH THE
9-SECOND THRESHOLD; OVER-10-SECOND HOLD PENDING** (2026-09-29). The operator
authorized “Flash 0a9d89” after the exact normal GP14 diagnostic image was
identified. This was
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
  clock readback. During flashing, no GP14 wire, jumper, button press or RF
  output was used.

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
network or SoftAP service. At the time of flashing, no press, stuck hold,
watchdog injection or post-release continuity test was authorized or run.
Those are separate
physical gates under the [bounded procedure](phase12-gp14-button-diagnostic.md).

## Interrupted GP14 hold attempts

Later on 2026-09-29, the operator announced a 2–3 second GP14-to-ground hold
and a repeat while the read-only USB monitor was open. The first monitor
connection exited early. Recovery reports contained `events=0` and advancing
read counts, so no duration or action can be assigned to that attempt. Before
the repeat, the monitor showed `boot=1`, `prior_watchdog=0`, `held=0`,
`events=0` and advancing read counts on both cores. It stopped receiving
reports during the repeat.

The `wspr5` kernel log shows USB over-current warnings at 09:03:35 and
09:06:50 CDT, during the two attempt windows. At each time, the host's USB
hubs and multiple attached devices disconnected, including B. At 09:06:54,
B re-enumerated with the same USB serial. The reopened diagnostic stream
reported `boot=1`, `prior_watchdog=0`, `prior_reason=00000000`, `held=0`,
`events=0` and again showed advancing read counts on both cores. The host
itself did not reboot. The volatile event ring contains no recoverable gesture
record; neither press classification nor continuity across either USB outage
was established. The temporal correlation does not identify the electrical
source of the over-current warning.

Private evidence is in `build/gp14-physical-0a9d89-20260929/` as
`hold-2-3s-usb.log`, `hold-2-3s-recovered.log`, `hold-retry-usb.log`,
`hold-retry-after-reenum.log` and `usb-overcurrent-summary.log`. The last
file's SHA-256 is
`c8077f783ecc0ed69f30973532abd45d39b32a045ea9175e6e7b5116eb5edbfd`.
Further physical holds were paused pending inspection of the GP14-to-ground
wiring and host USB power path. No flash or GPIO action was taken by the
monitor.

## Corrected 2–3 second hold

The operator subsequently reported that the first two attempts had bridged
physical pins **38 and 39** by mistake. The [Pico 2 W pinout](https://datasheets.raspberrypi.com/picow/pico-2-w-pinout.pdf)
labels these GND and VSYS. Shorting that pair is consistent with the host
over-current warnings, although no independent electrical measurement was
made. The operator changed the jumper to physical pins **18 (GND) and 19
(GP14)** and announced another hold. The read-only monitor was already open
and receiving B's idle diagnostic reports before contact.

The stream recorded one debounced `press`, one `would_stop` at duration
900,062 microseconds while `held=1`, `release` at duration 2,584,876
microseconds, and `post_release` one second later. Core-0 flash read counts
at these four events advanced from 689,997,568 to 695,236,096, and core-1
counts from 716,226,560 to 721,670,400. The 180-second monitor completed
with 91 periodic reports and no lost-event marker. Subsequent reports kept
`boot=1`, `prior_watchdog=0`, `held=0`, `events=4`, with both read counts
advancing to 920,114,432 and 952,882,688. The largest reported sample gap
after this gesture was 2,389 microseconds. No further USB over-current or
disconnect was present in the host kernel log through the completed monitor.

This is one valid 0.9-second stop-threshold and post-release continuity
observation with both cores active in XIP. It does not qualify a polling
latency bound, the shorter release classifications, a 9-second/stuck hold,
watchdog recovery, actual RF shutdown, reset or SoftAP service. The private
raw stream is `build/gp14-physical-0a9d89-20260929/hold-corrected-usb.log`
with SHA-256
`d70f314503a1a3e3dfa6e4744dac24efd7ce4bb584b48074d04ac2ea2e9c51b2`.

## Hold reaching the 9-second threshold

The operator requested a hold past 10 seconds. With the same GP14-to-ground
connection, a read-only monitor opened before the gesture and ran for 180
seconds. It recorded one debounced `press`, one `would_stop` at duration
900,066 microseconds, one `would_setup_ap` at 9,000,050 microseconds while
`held=1`, `release` at **9,867,649 microseconds**, and `post_release` one
second later. The requested past-10-second hold was therefore **not reached**.
No second press occurred in that monitor window. Duration here is the
firmware's measurement; no independent external timer was used.

The five events had consecutive sequence numbers 5–9 and increasing flash
read counts on both cores. Across 91 periodic reports, core-0 reads advanced
from 1,374,957,312 to 1,643,244,032 and core-1 reads from 1,425,451,008
to 1,701,529,856. The event ring reported no loss, the boot number stayed
1, `prior_watchdog=0`, and the largest reported sample gap was 2,445
microseconds. After release, `held=0` and `events=9` remained stable while
both cores kept advancing. The host kernel log showed no new USB
over-current or disconnect through this completed monitor.

This validates one physical crossing of both diagnostic thresholds and
post-release continuity. It does not show behavior beyond 10 seconds, a
30-second stuck hold, or actual RF shutdown or SoftAP service. Private raw
evidence is `build/gp14-physical-0a9d89-20260929/hold-over-10s-usb.log`
with SHA-256
`54e7cc5e89150593ecf29aff0774d8bdf6f0a36f239d1a1fa01b7ff7d7cab655`.
