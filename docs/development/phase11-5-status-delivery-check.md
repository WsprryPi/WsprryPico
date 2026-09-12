# Focused TX preservation target check

Status: authorized by the user's explicit reply to this bounded packet;
exact clean artifacts and helper hashes must be frozen before activation.
This is a single diagnostic of the STATUS delivery repair, not A2/A3 or phase
acceptance. No RF jobs, alternative clocks, GPSDO changes or full phase matrix.

The concrete host packet uses a fresh private root
`/home/pi/phase11-5-tx-guard-check` on wspr5, boot
`220e53ca-ca95-4206-9581-dbe28aa1eeb8`. Use the existing guarded network helper,
with runtime 2,400 seconds plus 600 seconds for independent cleanup: **50-minute
ceiling**, expected test/setup/restoration duration about ten minutes. Pause
`pi-wifi-recover.timer`, use wlan0 `2c:cf:67:62:76:66` as the isolated AP and
wlan2 `e8:4e:06:ae:d7:09` as its independent client, and temporarily allow chrony
access from `10.77.15.0/24`. Use the same isolated DNS record and no upstream
resolver, NAT, forwarding or test default route. Preserve wlan1, installed
`wsprrypi.service` PID 1957, and current Ethernet management including the
newly observed `192.168.1.54/24` address and link-local IPv6. Never restore an
older host snapshot over current state. Capture and restore current radio state.
Reuse existing wspr5 credentials; no private-key transfer.

The separately authorized device lifecycle will bind clean source, exact UF2
hashes and helper hashes before activation. Verify A USB `0BF4B4AEC9FFB344`,
last restored boot `5b1ae867c8b6888a7a671b7170d66aba`, and read-only B USB
`CDDBF8767C506C07`, boot `4e2fb851c08b278dd4b977104d2c2aaa`. Back up A, install
the candidate inhibited image for configuration, switch to the candidate
138 MHz physical image, and run exactly one N300/USB360 nominal controller and
browser interval with output idle. Device runtime is 900 seconds plus 600
seconds for guarded restoration. No LOAD/ARM/RF job is included.

Use ordinary INFO/STATUS observations to collect saturating TX credit-wait,
frame-preservation and timeout counters, plus both passive packet captures.
Do not add NETTRACE polling. Preserve the existing two-second STATUS start gap,
request count, USB/browser, heap and stack gates. Inspect preservation-counter
changes to distinguish exercised repair from a no-pressure pass. A failed
interval stops dependent actions; do not retry automatically.

Restore A's original inhibited UF2/configuration only after authoritative idle
admission, verify B unchanged, then restore the host immediately. Independent
cleanup survives SSH loss. Preserve failure or output uncertainty if restoration
admission fails. Cumulative configuration writes start at twenty, maximum 32.
The original setup remains 50 ohm/60 dB/unfiltered; no RF operation is needed.
