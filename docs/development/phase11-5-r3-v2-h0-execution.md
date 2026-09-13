# R3 v2 H0 one-hour QRSS with nominal contention

Reviewed under accepted R3-COMPLETE-20260913-v2. Same confirmed 60 dB
conducted wiring, Pico A only, 138 MHz/divider 1/RAM/GP2 at 135.5 kHz.
Source 7d183978d08d, image 38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1,
boot 8e777dadaa81f4618154d84de0df268a. S0 is independently audited and checkpointed.
B stays read-only; installed Pi executable/service and management routes stay
protected. No flash, reboot, Wi-Fi cycle, CONFIG save or heap probe.

Exactly one 3,600-second QRSS job, 32 question marks, 384 events including a
1,000 ns final RF-off interval. Morse `..--..` for every character.
Dot/intra-element gap 6,282,725,000 ns; dash 18,848,175,000 ns; character gap
18,848,129,000 ns. These explicit timings solve 480*dot + 31*character_gap +
1,000 = 3,600,000,000,000 ns. Every event boundary is an integral 138 MHz
sample; real message transitions occupy the hour, with no idle padding.

USB submits one complete immutable rf-events/1 job. Claim a 60-second lease,
confirm Loaded, read synchronized normal-leap clock, then ARM ten seconds ahead.
Charge the full 3,600 seconds before ARM, including an ambiguous start.
At most 100 renewals; release only after matching authoritative Complete, inactive
output and current INFO launch epoch. No abort counts as completion.

Run an identified native production Pi companion as a separate executable,
source bba4024ec310589b9f4813e9c6fb3082836e726f, SHA-256
b184cfba8b72a2cb73def207ab01792c5eaaae033607a926593dbad1e91cf124.
Its reviewed private INI has Transmit=false, Enable on Boot=Never, WTP network
backend and all ancillary controls disabled. Native TLS plaintext observation
uses the existing pinned interposer. It is a read-only concurrent controller
for this packet, not the job's submission path.

Also send a mutually authenticated HTTPS GET /api/v1/status every twenty seconds,
at most 190 requests, each within fifteen seconds. Require the certificate pin,
TLS 1.3/HTTP ALPN, exact target boot and two active slots with no pending slot.
This declares supported native WTP plus HTTPS concurrency throughout the hour.
It is nominal contention, not the later distinct saturation/expiry mechanisms.
Both clients run only in F0's independent network/mount namespace. Native identity
and an authenticated HTTPS positive control must succeed before any RF ARM.

Preserve independent one-second INFO and five-second STATUS/host-health cadence,
five-second individual observer reply bounds, raw traffic and target counters.
Require the same heap/stack reserves, zero faults, full/short predecessor limits
and 2,849,391 ns critical service budget as S0. Each USB interface has one owner.
A failed load/observer stops future actions; remaining readers continue through
the original finite deadline and output is reconciled from authoritative state.
No silent mutation retry or conversion of a failed observation into a pass.

Packet execution is at most 3,720 seconds plus 150 seconds for final observation
and process cleanup. F0's live monotonic cleanup deadline must still equal
290477130169000 ns and exceed the entire remaining packet budget. The timer is
not extended. Stop only the separately spawned native client; retain F0 for
the next reviewed tranche. Verify A/B final state and retained configuration.

Before scoring, independently audit full-hour coverage, exact RF timing/counters,
lease ownership, native wire identity, HTTPS bytes/concurrency and resource bounds.
Preserve all passing assertions and failed evidence independently. This packet
can qualify QRSS's physical hour within its scope; it cannot alone close R3,
qualify FSKCW/DFCW hours or replace retained-state/reclamation tests.

- `packet_sha256`: `065cb07e6ace4261caf4ba24cb7d6e1417186d1d7c1445bae25d102b256df3b5`
- `archive_sha256`: `16ab6f70a24e1ddcc0b752927b8e3c870802d712e3d39654e6693c35e96b33d4`
- `root`: `/home/pi/phase11-5-r3-v2-hour-h0-20260913`
- `rf_runner_sha256`: `9ec079e03abb66f040fa2c47799f083c31877183d885d5ac2640bac057ee8d0a`
- `load_runner_sha256`: `0ebed7f719ee51dbc9361e1f90b3501e308574abfa439114b190ca275a151149`
- `stager_sha256`: `399b4f5adfb75b6acdc14237e036eb96302ebdf5d0f7bb7f9c92165ca3a1a5d0`
- `job_id`: `cb5a5b1ef19146c9ad6b95304f6f2275`
- `dot_ns`: `6282725000`
- `character_gap_ns`: `18848129000`
