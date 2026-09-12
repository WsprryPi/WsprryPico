# CYW43 outgoing frame preservation

The pinned CYW43 driver contains a reproducible transmit corruption defect.
`cyw43_ll_send_ethernet()` and `cyw43_send_ioctl()` build their outgoing frame
in `spid_buf`. When credits are unavailable, `cyw43_sdpcm_send_common()` polls
incoming packets into that same buffer before submitting the outgoing frame.
It can consequently return success after sending overwritten payload bytes.
The regression compiles the actual original functions and demonstrates this
failure for both Ethernet and control frames.

This is a supported explanation for missing STATUS delivery, but reproducing
the driver defect does not establish that every historical delayed response
had this cause. N1z's failed cadence remains failed. The ignored `tcp_output()`
return was not established as its cause; the repair does not duplicate queued
TCP bytes, change production polling, or weaken acceptance thresholds.

## Repair and identity

The build generates a modified copy of CYW43 revision
`055d64274b014dd7b1c2fc94d26e8a18face7124` from source SHA-256
`7f4c93755b2ab911d18606652497b2f3cd08085ce63b3b1836171d375f806b10`.
It verifies the actual configured driver checkout and exact file hash, replaces
exactly one build input, and retains original attribution. The external SDK
stays unchanged. A changed source or symlinked output is rejected.

Before bus wake or credit polling, the common send function snapshots the
bounded, padded frame into aligned per-call storage. Nested callback sends
receive separate storage. The existing credit wait, sequence rollover, timeout
and bus error behavior remain intact. There is no driver heap allocation or
shared transmit scratch buffer. The Pico SPI path copies the preserved external
buffer into its bus buffer only after the credit wait has ended.

Ordinary network status exposes saturating `tx_credit.waits`, `preserved` and
`timeouts` counters. `preserved` counts a credit-wait send whose original payload
differs from the reused receive buffer before submission; it does not count
ACKs or prove radio delivery. No payload logging or extra USB polling is added.

## Deterministic and linked validation

The original-source case reproduces successful submission of corrupted bytes;
the repaired-source case preserves bytes across incoming packets, repeated
polls, nested callbacks, aliased control inputs and credit rollover. Tests also
check ordinary sends, padded buffer limits, no-credit timeout, bus error,
oversize rejection, counter saturation and source/output protection. The
maximum-buffer case tests the common function, not a maximum-sized SPI packet.

Run against the already installed pinned checkout without downloading a SDK:

```sh
python3 tests/cyw43_tx_overlay_tests.py /path/to/sdk/lib/cyw43-driver
```

Host CMake accepts `WSPRRY_PICO_TEST_CYW43_PATH` to include this test in CTest.
The host suite passed 58 tests; five affected native adapter/trace/overlay
tests also passed. All four network-enabled/disabled × inhibited/physical
target images linked, including allocator routing, MSPLIM, renderer, heap/stack
overlap and reserved-flash checks. Arm GCC 15.3.1 reports a 2,120-byte static
frame for the repaired common send function. Core-0 has a 16 KiB stack; the
bounded target observation below verifies its 4 KiB guarded reserve while idle.

## Adversarial review

Review checked aliasing before snapshot, nested callback storage, padding and
alignment, single submission on errors, unchanged timeout/rollover semantics,
actual overridden dependency identity, output symlinks and observation cost.
The discovered output-symlink and dependency-override gaps were closed and
covered by the affected checks. The repeated source review found no additional
actionable defect in this repair.

Existing upstream behavior that discards incoming DATA while waiting for TX
credit remains unchanged. A target pass cannot eliminate every packet-loss
cause, and an idle workload cannot qualify active RF contention. The bounded
target check and its result are recorded separately. No clock configuration or
Phase 11.5 closure is accepted by this repair alone.

## Current completion state

Source repair is committed as `e20ae8bea2d5237af017dbd5f73bfe9332ce144e`.
The [machine-readable result](phase11-5-status-delivery-result.json) binds all
four clean ELF/UF2 identities and the completed checks. The final repeated host
suite passed 58/58 and the affected native suite passed 5/5.

The user separately authorized the network fixture and, after automatic approval
review initially rejected the upload, explicitly approved transferring both
frozen UF2 files including their embedded test server private key to wspr5.
The single target check then passed on Pico A USB `0BF4B4AEC9FFB344`, physical
engine `pio-dma-gp2`, 138 MHz, boot `0fa996a26d9319f64385b23f3b6c62bf`, with RF
idle throughout. The production binary remained at source
`6f65d5c7d202569102459ab68d7c9ea079b96f35`.

| Measurement | Observed | Required |
| --- | ---: | ---: |
| Nominal STATUS requests in 300 seconds | 300 | at least 298 |
| Maximum STATUS request-start gap | 1.093778 s | at most 2 s |
| Maximum native TLS write-start to response | 0.650341 s | at most 5 s |
| Browser requests: status / page / CSS / JS | 60 / 10 / 10 / 10 | 60 / 10 / 10 / 10 |
| USB INFO samples in 360 seconds | 360 | at least 359 |
| Maximum USB INFO start gap | 1.022013 s | at most 2 s |
| Heap reserve against allocator peak | 99,848 bytes | at least 32,768 bytes |
| Core-0 / core-1 maximum observed stack use | 8,248 / 544 bytes | 16 KiB each, 4 KiB guarded reserve |
| Allocator / TLS allocation failures | 0 / 0 | 0 / 0 |

USB STATUS and host health each supplied 72 samples; both stack guards stayed
valid without faults. The controller retained one connection and one logical
session. AP/client captures contain 3,756/3,760 packets with zero reported
kernel drops. No RF job, extra NETTRACE read or automatic retry occurred.

**Credit-wait, preservation and timeout counters were zero in every sample.**
This passing nominal run did not exercise the repaired credit-wait path.
Byte preservation under that condition is demonstrated by the deterministic
actual-source regression; the target result does not prove that this defect
caused the historical STATUS stalls. Those failures remain recorded, and no
full A2/A3 case or Phase 11.5 configuration is newly accepted.

## Restoration and final adversarial assessment

The host fixture ran from 14:05:34 to 14:13:47 UTC on 2026-09-12, about eight
minutes thirteen seconds. Pico A was restored to original inhibited revision
`802c91a7b86e-dirty`, boot `69bb9cafe6d99d4f7caca78996e3f5f0`, with its original
configuration. Pico B retained revision `dbf1d86f0885-dirty` and boot
`4e2fb851c08b278dd4b977104d2c2aaa`. Reconstructed final Console/WTP exchanges
verify both empty, inactive and unowned. Cumulative configuration writes are
22 of 32. Host cleanup restored both radios, removed the temporary chrony ACL
and namespace, and reactivated the recovery timer. Ethernet, wlan1 and installed
WsprryPi PID 1957 remained unchanged; GPSDO settings were not changed.

Independent offline USB/TLS audits reproduce the supervisor's result. Review
checked exact source/image/boot/clock bindings, all zero allocation counters,
restoration wire evidence and the distinction between a nominal pass and an
exercised repair. Deliberately fabricated preservation counts and a truncated
interval were both rejected by the raw-evidence auditor. A repeated assessment
found no further actionable issue in this scoped repair or report. The material
coverage limitation above remains explicit; active RF contention is untested
on this candidate. Raw evidence stays private, with archive and file hashes in
the machine-readable result.
