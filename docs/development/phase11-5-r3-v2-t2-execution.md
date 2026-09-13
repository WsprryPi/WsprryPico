# R3 v2 T2 tls pressure

RETIRED BEFORE STAGING OR EXECUTION: BF1 demonstrated a shared allocation defect.
Zero RF starts. Preserve these packet identities; do not execute them.

Reviewed under accepted R3-COMPLETE-20260913-v2 and unchanged 60 dB wiring.
A only: source c5f00b6109cc1c692b3f6bf258c1a77dadef6639, image
5f681b10d2c076309116cb9c20df1653d21e522ad19b6b33c1ee57efb3f54756,
boot a0badc7b54480767c3d3f907e0962dc7, GP2, 138 MHz/divider 1/RAM.
B independently authorized for zero-RF work; this A packet never opens B; protect the installed Pi executable/service, configuration and
management radios. Zero flash/reboot/Wi-Fi/CONFIG/heap probes.

Exactly two 100-second 135,500 Hz Tones, one at a time, 200 planned seconds
charged before ARM including uncertainty. At most twelve lease renewals.
330 seconds execution plus 150 seconds cleanup; the full budget must fit before
F1's unchanged 306202695885000 ns host-monotonic cleanup deadline. No overlapping
RF/USB owners. Native read-only production companion bba4024ec310589b9f4813e9c6fb3082836e726f,
binary b184cfba8b72a2cb73def207ab01792c5eaaae033607a926593dbad1e91cf124,
Transmit=false, all ancillary output off. One initial authenticated HTTPS
positive control and pressure-observer readiness precede ARM. Normal periodic
HTTPS is disabled during this packet so only the declared pressure actor uses
the second slot. Native polling continues throughout the finite RF window.

One-second INFO, five-second STATUS/host health, five-second observer reply
deadlines, raw observer snapshots with PID/start identity, current Running job
and launch-epoch brackets. Same heap/stack reserve, zero faults and 2,849,391 ns
RF-service/critical budgets. Preserve actual mode timing/counters and final
A authority/configuration. A pressure/observer failure stops future actions;
surviving readers continue to the original finite deadline. Preserve every
failed case and independently validated assertion.

Exact pressure sequence (at most 12 TCP connections):

- Job 1 `366674f3052c5e0cbb1f656121c242e7`: positive, missing-certificate, recover-certificate, silent-handshake, recover-handshake.
- Job 2 `b1678e7709789e09cc38b47cfb029609`: positive, slot-excess, recover-slots, duplicate-wtp, recover-wtp.

Use the existing bounded mechanisms and tolerances, now with an explicit v2
validator; old consumed packet bytes and old-source scoring stay unchanged.
Positive and authenticated recovery reads must complete within fifteen seconds.
TLS handshake inactivity, pending-slot expiry, HTTP activation timeout and
endpoint output pressure remain separate mechanisms. Capture the actual client
TCP stream in a task-owned pcap. Transport alert-wait uses only prospective
server-flight-first, zero-TCP-payload ACK suppression, scoped to one frozen
client/server tuple. Remove only that owned nft table in a finally path. Keep
the unread HTTP socket open through authenticated recovery.

Stop only this packet's native process, pressure actor and capture. Keep F1 for
the next reviewed packet. Independently audit raw request/reply/ciphertext/TCP
evidence, counter deltas, complete Running brackets, native identity and final
state before credit. These short pressure cases do not qualify the extended
maximum, browser file limit, retention or three reclamation cycles.

The F1 client is PID 491605, net:[4026532629], mnt:[4026532725].
A fresh read-only inventory verified the retained c5f00b6 boot, Empty/inactive/
unowned state, 10.77.15.10 association and synchronized clock before freezing.
These tests exercise the final repair image; prior mode-hour passes remain
credited within their recorded source-impact boundaries.

- `packet_sha256`: `e5ace0a8335c7b3bd258e286c5aac96699e671557e17accc0c55f21190f5081e`
- `archive_sha256`: `4dc1be5ea1478c31e09877725030c375858c7df8df8db94b12ea8f9fc7738278`
- `root`: `/home/pi/phase11-5-r3-v2-pressure-t2-20260913`
- `stager_sha256`: `03d3f3d5073d49c71fb84da5f4333037c2047c88e443756892fe6a60546b3af3`
- `rf_runner_sha256`: `0444303898cf3eedffe0d8bfa6dd75fb780e4ea3149c935c1280041870e64cf4`
- `load_runner_sha256`: `889712a5100b90d859aa646d4cfbd21671608c13213fb1468a8f42acf2221902`
- `pressure_runner_sha256`: `f61ac9a641223b9c0a339e0e2791d7a9d87a85814551f595407a9dd2879259de`
