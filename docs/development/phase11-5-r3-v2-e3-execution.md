# E3: deploy the INFO allocation repair and verify idle boundaries

This is an execution packet under accepted R3-COMPLETE-20260913-v2. The
unchanged conducted wiring remains the authorized setup. E3 produces no RF.
The demonstrated reason for changing A's retained image is B3's 194,260-byte
allocator peak in a 220,348-byte heap: only 26,088 bytes remained against the
unchanged 32,768-byte gate. Allocation failures, TLS failures and reset counters
remained zero. Independent final inventory proves Empty/inactive/unowned on
boot fc90d1a04eb0acc703de907917277921. Preserve the original stopped result.

Source f5502cff9fa6b56747b2e1b1036a77fc0e270f6f changes only INFO suffix
construction in firmware: append scheduler status to the existing string instead
of copying the existing report through lvalue concatenation. The host regression
compiles this actual formatting block, proves identical bytes and bounded
additional allocation, and rejects the original expression. All 62 host groups
pass. This explains and removes an avoidable peak; corrected physical reserve
acceptance remains required. No source-level RF, TLS, protocol or encoder change
is included. The image comparison preserves static layouts and 70 exact RAM
functions; 27 RAM functions differ, so this is not whole-image equivalence.

Build both variants from the clean detached source checkout with existing SDK
2.3.1, 138 MHz/divider 1/RAM and A's existing TLS identity. Both linked-image
checks pass. Deploy only the standalone RF-capable image; keep it deployed.

- Standalone RF UF2: a71447e8fe00c023a106ac682f4b11cf8e9e7d93cabb7b5868da10025e2cd5a2
- Standalone RF ELF: 7d310b01ef78da7078e3afa36d98d04b88dcb880d3206cdb8a31125616ca5907
- Packet: 8bd146adfccd861974e86fe669584ef5de221c56826c9a2589b4315a3b6433c1
- Public archive: f5b08acbecd883990930c68cdc3afc8a72e0579604a6ea1ea7de71e1d3555727
- Stager: f5b57069a10e97219eb9b98d68423dca66ddf12ca18728e76e3c88ea46141d76
- Runner: 0958e73ae7389eb06cfd7ab9c20907412f9133f48296050701348bbbd9ebb195
- Fresh root: /home/pi/phase11-5-r3-v2-idle-e3-20260913

Admit exact A serial 0BF4B4AEC9FFB344/device fd6127d11d6aca42a9905fa3fb1bf1d5,
prior source 8921a70081839f168edef5926e92445f251d8e1d and the above boot. Read B
only, preserving source 8921a7008183 and boot 6684b4b197d80cfa0ce83b3aaf205cb0.
Protect installed Pi PID 1957 and its existing executable hash. Require the B3
independent audit hash 7ddd6632414f01a230e149630ef81e4978bae8579cab1689e32c47f105a94b65
and its inactive owned supervisor before launch. Check fresh admission inside
the runner; a historical inventory is not a substitute.

The 600-second execution plus 150-second restoration bound allows one BOOTSEL
and one serial-specific load/verify/start sequence, seven idle boundary assertions,
and final A/B inventory. No extra reboot, Wi-Fi cycle, CONFIG save, heap probe,
ARM or RF job. Keep the test configuration and standalone scheduling disabled.
Verify the complete 65,536-byte STATUS, 65,537-byte rejection/recovery, 513-event
and over-duration rejection, and 512-event/3,600-second inactive LOAD with all
adjustment replies, then ABORT/RELEASE and authoritative Empty. Record the
single deliberately aborted inactive record separately from completed RF jobs.

F1's original absolute cleanup deadline remains 306202695885000 host monotonic
nanoseconds. Require 750 seconds plus reserve before it; do not extend it. Any
failure stops future mutations and preserves the raw result for diagnosis.
Independently audit raw bytes, firmware/boot/configuration and final authority
before the following browser packet. No repeat of this consumed packet is allowed.
