# R3 D0: one allocation diagnostic flash and one idle request

Status: **PREPARED; NOT APPROVED, STAGED OR EXECUTED**. R3 remains OPEN.
The user requested completion, adversarial review, repair, reassessment and
commit/push. C0 exposed a confirmed target allocation panic. The original
execution boundaries explicitly prohibit automatic reflash/reboot/retry after
an unexpected fault, so this newly prepared flash needs one concrete approval.
This is ordinary firmware diagnostics; no cybersecurity restriction is claimed.

## Exact image and target

Source: `481da3c3ff171bae53d6c7d1d2e30525ae748f4b`, clean when configured and built.
Embedded revision: `481da3c3ff17`. Candidate:
`build/phase11-5-r3-allocation-d0/diagnostic.uf2`.
UF2 SHA-256: `5589b165b3cce03f2dc2f351088c88f08d7a5ebbf6c10702c17d0d38424bc534`
(2,049,536 bytes). ELF SHA-256:
`19ed081ff40c3fa571d8667f5789753ce9d563983abe3b1071a5e2396eee2557`.
The ELF is in `build/phase11-5-r3-allocation-diagnostic/firmware/`.

A: Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, physical PIO/DMA GP2, 138 MHz,
divider 1, RAM renderer, compiled TLS/HTTPS listener on port 18443. The existing
per-device certificate, certified hostname `wsprrypico-0a60df.local`, stored test
configuration and unchanged 60 dB conducted wiring remain the setup.
The image contains existing device credentials and stays private, outside Git.
The expected current source is `2e43110f0530`, recovery boot
`bccea7c09794539c4f64bc22b0e76c56`, fault stage 5 / hash 3833354787.
Both Console and WTP must confirm Empty, inactive, unowned, healthy storage and
standalone disabled before issuing BOOTSEL.

B is observation-only: USB serial `CDDBF8767C506C07`, WTP device
`29f20b7342051ef947aa56cb9d4fab42`, unchanged boot
`feffcd075ab6cb0b74e7e0c2fde6c87f` and revision from the fresh initial inventory.
No B image, GPIO, GPSDO, SDR/receiver, filters, cables or attenuation changes.

Host: wspr5, boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`.
New root: `/home/pi/phase11-5-r3-allocation-d0-20260913`.
No network fixture, namespaces, firewall rules, services, DNS, clock or installed
WsprryPi binary changes. A normal application boot may attempt its stored Wi-Fi
association; no Wi-Fi OFF/ON command or reconnection procedure is included.

## Bounded operation

Within one 600-second invocation, with no retries:

1. Stage the hash-bound public tooling into the new private root. Copy the
   exact diagnostic UF2 separately, mode 0600, and verify its hash. The public
   tooling archive has no firmware, captured evidence, private configuration or
   credentials. No existing private input is copied by the stager.
2. Read B and A inventories independently; require the exact identities and
   stopped A state above. Verify the image and existing host picotool hashes.
3. Issue at most one Console `BOOTSEL` to A. Record the command before issuing
   it and require its successful ACK. Only EIO/ENODEV during cleanup after that
   ACK is an expected disconnect; it never substitutes for the next gate.
   Require this exact serial in the 2e8a:000f ROM loader within 15 seconds.
4. Perform at most one verified load-and-start using existing host tool
   `/home/pi/phase11-4-e1/picotool-build/picotool`, SHA-256
   `4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`:
   `picotool load -v -x diagnostic.uf2 --ser 0BF4B4AEC9FFB344`, 60-second bound.
   Wait at most 15 seconds for the application, then inventory it. Require the
   new embedded revision, a new non-recovery boot, inactive/unowned authority,
   unchanged saved station/schedules/watermark/hostname, valid 4 KiB guards on
   both cores, zero allocator failures, 32 KiB reserve, expected clock/engine/
   RAM placement, and advertised 65,536-byte capacity.
5. Open A's USB WTP endpoint exclusively, send HELLO in the frozen new session,
   then at most one valid STATUS frame with a 65,536-byte payload, including
   outside-JSON padding and correct length/CRC. Use a five-second duplex bound
   and log each successful write, with chunks at most 4,096 bytes. No oversized
   request, CLAIM, LOAD, ARM, RF job, CONFIG save or heap probe is included.
6. After the maximum-request attempt, allow twelve seconds of read-only waiting
   to cover the eight-second watchdog. Independently attempt final A and B
   inventories even if an earlier action failed. Record any new boot and tagged
   allocation fields; require authoritative inactive/unowned state and unchanged
   saved configuration. The old recovery boot's empty live station MAC is not
   mistaken for a change to saved configuration. Require no RF launch/DMA/alarm/
   tail activity and unchanged B boot/revision/configuration.

Inventory subprocesses each have a 65-second bound. A write-ahead counter and
exclusive result creation prevent replay in the same root. The packet fixes
sessions, request ID, source/image hashes, helper hashes and maximum actions.
No wall-clock expiration creates an automatic retry allowance.

The approved flash would consume one BOOTSEL and one load/start, not an RF job.
The stored configuration stays in place; the candidate is left installed,
inactive/unowned or in authoritatively reconciled recovery. There is no
restoration flash, journal erase, CONFIG save, extra reboot or retry. If any
state cannot be established, preserve output-unknown and report it; do not
infer inactivity from USB loss. A failed transition stops dependent actions.
Only the final independent read-only inventories remain authorized on failure.

Cumulative CONFIG writes remain 37 and heap probes six. The completed RF budget
remains nine jobs / 900 seconds, with at most 31 jobs / 3,523.68 seconds remaining
under the existing envelope. D0 consumes none of that RF budget. The previous C0
watchdog reboot remains recorded as unexpected, distinct from this proposed
commanded bootloader/flash transition.

## What the diagnostic establishes

The source change records each core's latest completed allocation byte count
and NULL/non-NULL result. If the SDK emits its pinned `Out of memory` panic,
the panic handler stores that core's record in tagged watchdog scratch 0/3.
Recovery INFO exposes `fault_allocation_recorded`,
`fault_allocation_request_bytes` and `fault_allocation_returned_null`.
SDK scratch 4–7 and ordinary hardfault fields retain their existing meanings.
The snapshot takes no lock, allocation or heap traversal. No allocator policy,
limits, parser behavior or recovery behavior was changed.

This is **diagnostic instrumentation, not an allocation repair or an accepted
R3 configuration**. C0's exact failing allocation and full delivery remain
unproven. A fresh-boot maximum response would be useful new evidence but would
not explain or close C0's failure after the prior contention history. An absent
or invalid allocation tag remains unknown. Do not declare fragmentation, a
65,552-byte failure, or successful capacity acceptance without matching evidence.

Collect and hash the complete raw run, partial-write counts, tool output and
independent A/B inventories. Reconstruct the exact request length/CRC and all
responses, cross-check source/boot/configuration/guards, distinguish intended
bytes from successful writes, and classify the resulting target fault or
response independently of the runner's summary. Adversarially remove a write,
alter a fault tag/source/boot and change final output authority; reject those
unsupported claims, then reassess intact evidence. D0 runner outcomes always
require independent audit; none close R3. Prepare any resulting repair and its
specific affected checks before seeking further hardware authority.

## Build and adversarial preparation

The pinned SDK 2.3.1 and existing toolchain configured clean source 481da3c.
Both standard inhibited and standalone RF firmware built successfully. Linked
allocator interception, stack-guard startup, RF worker/renderer RAM placement,
16 KiB stack separation and UF2 flash-reservation checks passed. Application
payload ends below 0x103fb000, preserving both journals; only the pinned E10
absolute block at 0x10ffff00 lies outside that application region.

Local UF2 conversion used existing picotool 2.3.0, SHA-256
`8bfa2bc5dc1a066688ccd96e7ba0e5cf1c5846385d090223f66e0770abcf006f`,
with SDK-defined RP2350 ARM-S family 0xe48bff59 and `--abs-block`.
The separately built inhibited UF2 is **not a flash target** in D0:
SHA-256 `c97d61483a6353f35cb3224bbf8fce44720f23c6b65248e6129a8d08cd4b1682`.

Host tests exercise tagged-record validity, overflow, zero-size NULL, free-list
non-interference and cross-core isolation, plus exact D0 limits, opt-in behavior,
authoritative inactivity, acknowledged bootloader disconnects and saved versus
runtime identity. Review findings were fixed and affected tests passed again.
The full Phase 11.5 Python suite passed 237/239 with two unrelated private skips
and eleven supplied R3 archives. All 62 host CTest entries passed across the
full run and necessary affected/environment reruns. No image has been flashed.

## Frozen packet and staging identities

Packet: `build/phase11-5-r3-allocation-d0/stage/packet.json`.
SHA-256: `349634192b03f8a79bc8ef72c43eb30b6da201b35a79d3cc35067380de70c25c`.

Public tooling: `build/phase11-5-r3-allocation-d0/public-tooling.tar`.
SHA-256: `1bf25435cccbf03ba61d58c01fb6b7abb27723b1490576e0702f5cf3205e3527`
(798,720 bytes, 77 public files, zero remote private inputs).
Stager SHA-256: `7f39dadffe7ad22071db41b3db66da85d6136575f6bc688e2d93651cd322e4cb`.
The extracted exact helper closure imports successfully in plan-only mode.

After approval only, invoke the frozen D0 runner with the exact root above,
`--packet-sha256` equal to the recorded packet hash and `--run`. Staging and
execution are separate operations; neither has occurred. The generated images
and raw evidence remain private and outside Git. Approval of this packet covers
its staging, single bootloader/flash transition and one idle request only.
