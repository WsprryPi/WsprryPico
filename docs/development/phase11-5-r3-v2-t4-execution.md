# R3 v2 T4 tls pressure

Reviewed under accepted R3-COMPLETE-20260913-v2 and unchanged 60 dB wiring.
A only: source 8921a70081839f168edef5926e92445f251d8e1d, image
3899b498d05ca5b39e23a45e455c44b2784bcf2aca35f62a8ef4db644cc7241b,
boot fc90d1a04eb0acc703de907917277921, GP2, 138 MHz/divider 1/RAM.
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

- Job 1 `d0f3d2bada2d84266718ad429133fd37`: positive, missing-certificate, recover-certificate, silent-handshake, recover-handshake.
- Job 2 `7677571d46f4c014de5c0af84bab1237`: positive, slot-excess, recover-slots, duplicate-wtp, recover-wtp.

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
E2 independently verified the repaired 8921a70 boot and Empty/inactive/
unowned state. Fresh network and clock admission is required before RF.
These tests exercise the final repair image; prior mode-hour passes remain
credited within their recorded source-impact boundaries.

- `packet_sha256`: `a96a14455d08caa37fab21e7ef96be5bd5249afdf6471e8450c64a2e5d73f5a4`
- `archive_sha256`: `3340fe08636642e12870c1d5362ab43fcdbe9af026b4b25221e1bbff29cffd4f`
- `root`: `/home/pi/phase11-5-r3-v2-pressure-t4-20260913`
- `stager_sha256`: `d81262d706323cc75a1467a9f8b0d896598976acae063664f40b72bdf6ea6712`
- `rf_runner_sha256`: `c971d846259e9b4f15d5c26d98f32bf81c5b89cde6f2ff9c5124834d2e0daff2`
- `load_runner_sha256`: `889712a5100b90d859aa646d4cfbd21671608c13213fb1468a8f42acf2221902`
- `pressure_runner_sha256`: `f61ac9a641223b9c0a339e0e2791d7a9d87a85814551f595407a9dd2879259de`
