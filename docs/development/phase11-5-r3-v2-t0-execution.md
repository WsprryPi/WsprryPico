# R3 v2 T0 tls pressure

Reviewed under accepted R3-COMPLETE-20260913-v2 and unchanged 60 dB wiring.
A only: source 7d183978d08d77d5de668911be041bb188c851f5, image
38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1,
boot 8e777dadaa81f4618154d84de0df268a, GP2, 138 MHz/divider 1/RAM.
B read-only; protect the installed Pi executable/service, configuration and
management radios. Zero flash/reboot/Wi-Fi/CONFIG/heap probes.

Exactly two 100-second 135,500 Hz Tones, one at a time, 200 planned seconds
charged before ARM including uncertainty. At most twelve lease renewals.
330 seconds execution plus 150 seconds cleanup; the full budget must fit before
F0's unchanged 290477130169000 ns host-monotonic cleanup deadline. No overlapping
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
A/B authority/configuration. A pressure/observer failure stops future actions;
surviving readers continue to the original finite deadline. Preserve every
failed case and independently validated assertion.

Exact pressure sequence (at most 12 TCP connections):

- Job 1 `94b3489c3dbee0ca0497812308d21685`: positive, missing-certificate, recover-certificate, silent-handshake, recover-handshake.
- Job 2 `6067cfb8fa2f9dac91c601a5f3557e00`: positive, slot-excess, recover-slots, duplicate-wtp, recover-wtp.

Use the existing bounded mechanisms and tolerances, now with an explicit v2
validator; old consumed packet bytes and old-source scoring stay unchanged.
Positive and authenticated recovery reads must complete within fifteen seconds.
TLS handshake inactivity, pending-slot expiry, HTTP activation timeout and
endpoint output pressure remain separate mechanisms. Capture the actual client
TCP stream in a task-owned pcap. Transport alert-wait uses only prospective
server-flight-first, zero-TCP-payload ACK suppression, scoped to one frozen
client/server tuple. Remove only that owned nft table in a finally path. Keep
the unread HTTP socket open through authenticated recovery.

Stop only this packet's native process, pressure actor and capture. Keep F0 for
the next reviewed packet. Independently audit raw request/reply/ciphertext/TCP
evidence, counter deltas, complete Running brackets, native identity and final
state before credit. These short pressure cases do not qualify the extended
maximum, browser file limit, retention or three reclamation cycles.

- `packet_sha256`: `eef06c2fefab51ffb7954d1d563c956acb0cbfddf386597163bf91fd927ddce7`
- `archive_sha256`: `3b288df732287df5a2d7e1e13553cd264be132a6dcf6d202dd27b835976d51a2`
- `root`: `/home/pi/phase11-5-r3-v2-pressure-t0-20260913`
- `stager_sha256`: `f57ef410257725aa2c3bbd1e5333f2ffe8232ba94835ee705dbeb159d7e44690`
- `rf_runner_sha256`: `16094f47b48263e3ffa1de079fb862a49459b91c74d9f51591262fe6680347bc`
- `load_runner_sha256`: `045054843e8023b1a4392ea1db892ec56b8931b6d822ddd24786116eacbeb48c`
- `pressure_runner_sha256`: `f61ac9a641223b9c0a339e0e2791d7a9d87a85814551f595407a9dd2879259de`
