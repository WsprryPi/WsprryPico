# R3 v2 E0a extended-image idle admission

Standing authority: accepted R3-COMPLETE-20260913-v2. Internally reviewed
September 13, 2026. Execute without another routine approval.

Pico A only; same serial/device, 138 MHz, divider 1, RAM, GP2 and retained
test configuration. B read-only. Host boot and installed PID/hash were refreshed
and match the packet. No fixture setup, Wi-Fi, CONFIG, heap probe or RF output.

A maximum of one acknowledged BOOTSEL and one serial-specific verified flash,
within a 600-second packet. Fresh inactive/unowned A/B inventory precedes the
flash; then verify clean embedded source, new boot, 512 events / 3,600 seconds,
65,536-byte framing, heap reserve and both guards.

Issue an exact 65,536-byte STATUS and a framed 65,537-byte oversized stimulus
followed by a valid STATUS on the same connection. Record full write counts and
raw CRC-framed responses. Claim one 60-second owner lease. Reject 513 events
at codec validation and 3,600 seconds plus one nanosecond at the job limit,
checking atomic unchanged inactive authority. LOAD the frozen 512-event,
3,600-second FSKCW plan; require 512 returned adjustments and inactive Loaded
state. Never ARM. ABORT the loaded job, RELEASE, and verify Empty/inactive/unowned.
Retain test configuration. Independently inventory A/B and protected host state.

A failure stops this packet and retains all observed assertion checkpoints.
An ambiguous or owned final state requires reviewed reconciliation under the
existing v2 authority; do not infer inactivity from USB closure. There is no
automatic flash or mutation retry. Runner observations require an independent
raw audit before receiving validation credit. No physical hour/RF claim.

The earlier local E0 packet was rejected before staging because its RF ELF
had not been rebuilt by the default target. Its identities and rejection remain
private evidence. E0a explicitly built both targets and verified the RF image's
embedded clean revision plus linked heap/stack/RAM and flash-journal reservation.

Packet and public tools are separate from the private credential-bearing UF2.
No image or credential is included in Git or the public staging archive.

- `packet_sha256`: `ddfb38d310f2eb30f5888380013bc87c91e9bbb84d77ef6883a7cea8abb2ec53`
- `public_archive_sha256`: `79933328c232569ec9a005c342be4fd8a5385045e0a16f41e4b0f50428495ff1`
- `stager_sha256`: `2589a3b2f47bb205370a9e8a2e8e184855228757ac1449ce3abf28d880b2a8e7`
- `runner_sha256`: `0958e73ae7389eb06cfd7ab9c20907412f9133f48296050701348bbbd9ebb195`
- `image_sha256`: `38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1`
- `elf_sha256`: `aa36962f795377bc1560bd7fa251f87b493e6c1a1ae49048f6e53e0c815b909d`
- `source_revision`: `7d183978d08d77d5de668911be041bb188c851f5`
- `root`: `/home/pi/phase11-5-r3-v2-idle-e0a-20260913`

Pure runner validation: 3 tests passed, including budget/identity/plan mutations
and rejection of any ARM path. R3 Python discovery: 85 tests, 15 archive-dependent
skips; skips carry no validation credit. Existing private-archive results retain
their recorded prior scope. No acceptance threshold was weakened.
