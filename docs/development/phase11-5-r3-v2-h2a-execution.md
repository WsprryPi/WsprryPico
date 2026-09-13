# R3 v2 H2A physical DFCW hour

Reviewed under accepted R3-COMPLETE-20260913-v2 and unchanged 60 dB conducted wiring.
Run only after the preceding hour packet has stopped and its authoritative final
A/B state has been reconciled. No simultaneous USB owners or RF jobs. This packet
uses the frozen bounded RF runner and a corrected nominal HTTPS scheduler.
The first HTTPS request establishes an absolute twenty-second start schedule;
a separate finite thread keeps local native HTTP reads and response latency from
shifting those starts. Require at most one second scheduled lateness and retain
the strict twenty-one-second start-gap audit. Seven deterministic scheduler
checks pass; actual target cadence remains subject to independent audit. H0's
completed QRSS hour remains validated in checkpoint v2-006, while its separate
HTTPS cadence finding is preserved. This fresh packet allows 3,720 seconds execution and 150 seconds cleanup.
At most 190 HTTPS requests and 100 lease renewals. The unchanged F0 cleanup
deadline is 290477130169000 host monotonic ns; require the whole budget to fit
before execution. No silent deadline extension or consumed-root replay.

Pico A serial 0BF4B4AEC9FFB344, source 7d183978d08d77d5de668911be041bb188c851f5,
image 38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1,
boot 8e777dadaa81f4618154d84de0df268a. 138 MHz/divider 1/RAM/GP2. B read-only,
installed Pi executable/service and management connectivity protected. Zero
flash, reboot, Wi-Fi cycle, CONFIG save and diagnostic heap probe.

One exactly 3,600-second DFCW job containing 32 question marks, Morse
`..--..`, 384 events including the 1,000 ns final off interval. Dot and intra-gap
8080005500 ns; dash 24240016500 ns (DFCW marks all use dot duration); character gap
24381873000 ns. Mark 135,500 Hz, space/dash 135,495 Hz. FSKCW gaps remain RF-on at
space frequency; DFCW gaps are RF-off. Every event is precompiled by the actual
source's compile_message function and frozen in packet.json. All boundaries are
integral 138 MHz samples. There is real keying throughout, with no idle padding.
The same compiler independently reproduced H0's frozen QRSS event list exactly.

The USB reference transports the complete immutable job. Charge all 3,600
seconds before ARM, including an uncertain submission. Verify Loaded, synchronized
normal-leap clock and current INFO/health, then ARM ten seconds ahead. Keep one-
second INFO and five-second STATUS/health starts and five-second reply bounds.
Require unchanged source/boot, zero faults/failures, at least 32 KiB heap reserve,
valid stack guards and the existing 2,849,391 ns RF service/critical budgets.
Release only after authoritative matching Complete/inactive plus current launch
epoch, and preserve final A/B inventories. No abort counts as completed hour.

A workload or observer failure stops future mutation and future jobs. Remaining
readers continue through the original finite deadline. Preserve failed evidence
and diagnose product, harness or administrative causes without erasing passing
assertions. An independent audit must verify full-hour raw coverage, exact
launch/refill/tail deltas, native TLS identity and HTTP concurrency before scoring.
This packet provides a scoped USB mode-hour result, not browser/native submission
credit, saturation, reclamation or whole R3 closure. Those remain distinct gates.

- `packet_sha256`: `dd834b829b6745d64385a4b831e96018be51edcf09dcfbc544cc6dc4d4eb82ed`
- `archive_sha256`: `1219a8b520cb7b75c3c8d768ac12d3578c4715b4fc7bc59220c8fc6e3c3a980b`
- `root`: `/home/pi/phase11-5-r3-v2-hour-h2a-20260913`
- `rf_runner_sha256`: `9ec079e03abb66f040fa2c47799f083c31877183d885d5ac2640bac057ee8d0a`
- `load_runner_sha256`: `889712a5100b90d859aa646d4cfbd21671608c13213fb1468a8f42acf2221902`
- `stager_sha256`: `399b4f5adfb75b6acdc14237e036eb96302ebdf5d0f7bb7f9c92165ca3a1a5d0`
- `job_id`: `a922caa7626e5006efa752629d8c8390`
- `dot_ns`: `8080005500`
- `character_gap_ns`: `24381873000`
- `compiler_driver_sha256`: `76e349ac7d34d449b48f38cce452107c4881f06396d8140d49474f501f9fc791`
- `morse_header_sha256`: `b0dd499da763cb51464c9f431077e9a46e5cec983160bde3c8abcd52905f8f2e`

## Retired before execution

Zero RF starts and zero RF duration charged. The observer publication-race
repair is frozen in fresh H2b; this staged packet remains unchanged.
