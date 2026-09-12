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
frame for the repaired common send function. Core-0 has a 16 KiB stack; its
required 4 KiB runtime reserve still needs the target observation.

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

The user authorized the fresh bounded network fixture. Automatic approval
review then rejected the firmware upload because the UF2 files contain the
existing test server private key and it requires explicit authorization for
that payload and the wspr5 destination. A concrete request with both UF2 hashes
is pending. No fixture, USB control, flashing or RF action occurred in this
repair task. The target interval and runtime stack reserve remain unverified;
the prepared packet must not be described as an executed target result.
