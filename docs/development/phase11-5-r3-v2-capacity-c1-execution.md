# C1 maximum-event execution packet

Uses the established `phase11_5_r3_v2_rf.py` RF observer and
`phase11_5_r3_v2_nominal_load.py` production WTP/HTTPS load tools. No replacement
runner. One 512-event FSKCW job, 384 seconds, 135500/135495 Hz, full charge before
ARM, 480-second observation plus 150-second restoration reserve. Native WTP
polling and authenticated HTTPS status every 20 seconds provide ordinary
concurrent load. This packet does not claim maximum WTP/HTTP body or USB pressure.

Packet `3c8cea4f50a1e78b62cbb300846f05555360e8e0c91b467c694505b66fc8e3cf`;
root `/home/pi/phase11-5-r3-v2-capacity-c1-20260914`; job
`60723b3b1baf42db814dcc6f6f28ef20`. A retains a740dbb, image
454e03e5165143463d6b5f965ea8f1f3704138f08bfc7057704e3fef8f10ebe4,
boot 2b4583bd3d79a38f030a08c82ed96939, 138 MHz PIO/DMA GP2 RAM renderer,
scheduling disabled and the unchanged conducted RF path. Zero flash, CONFIG,
Wi-Fi or heap-probe operations in C1.

F3 original cleanup deadline is 348101486890000 host monotonic ns. Preflight
verified the client PID 553798/start ticks 34089530, native binary and disabled
transmit INI, frozen dependency hashes, and installed PID 1957/executable.
W2 independently verified restored IP/clock and Empty/inactive/unowned authority
on this same image and boot before C1 admission.

The existing RF observer now opts into the previously tested single-flight INFO
policy when requested by the packet; old packet behavior remains unchanged.
The existing RF auditor uses raw ARM acknowledgment clock mapping already used
for native acceptance. Seven observer-policy and two mapping tests passed.
Independent auditor closure is frozen in
`build/phase11-5-r3-v2-capacity-c1/auditor-closure/manifest.json` before execution.
