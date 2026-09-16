# Phase 11.5 Package 2 review and execution

**COMPLETE — assertions 2.2a and 2.2b accepted. Phase 11.5 remains OPEN.**

The [execution prompt](phase11-5-package2-prompt.md) limits this package to a
supported simultaneous workload and a separately bounded overload. The
[current result](phase11-5-event-pages-result.json) records the exact firmware,
packets, metrics, failures and restoration evidence. The earlier
[failed result](phase11-5-package2-result.json) remains historical evidence.

## Repair

The original 52,105-byte LOAD failed while allocating one contiguous
20,480-byte vector for 512 RF events. Commit `b51cd30` replaced that vector with
eight nullable pages of 64 events. Allocation now grows page by page, returns a
specific resource failure, and unwinds partially allocated pages. All event
producers handle allocation failure explicitly.

The repaired image accepted the maximum LOAD and fresh-ID replay with zero RF,
continuous native observation and a 142,576-byte allocator peak under the
218,840-byte cap. Four altered evidence cases were rejected.

The first supported RF packet then exposed an evidence problem. Its RF job
completed and both boards returned inactive, but no HTTP request was sent
because the global heap delta was 32,488 bytes, 280 bytes below the proof gate.
The parser had reserved the entire frame; an unrelated 296-byte release made the
aggregate heap delta unsuitable for proving parser residence. No assertion was
accepted from that packet.

Commit `ca3c5dc` added read-only `wtp_input_reserved_bytes` reporting from the
WTP endpoint. It does not change input admission or RF behavior. The final
packets require a direct reservation increase of at least 32,768 bytes while
retaining the aggregate heap delta as a secondary measurement.

## Accepted supported workload — 2.2a

Packet `43c42e4d…` ran one 128-second, 512-event FSKCW job. During Running state,
one authenticated HTTP connection was warmed, a 32,784-byte WTP frame reserved
32,784 parser bytes, and the small declared HTTP request completed with status
200 before WTP completion. The WTP exchange completed in 1.520 seconds.

One native TLS connection remained continuous and bracketed the overlap. The
job completed, configuration remained unchanged, Pico B remained unchanged,
and both boards returned Empty/inactive/unowned. The independent audit rejected
mutations to overlap, WTP writes, HTTP response, native capture and reservation
state.

## Accepted overload — 2.2b

Packet `5dc59798…` ran a separate 128-second, 512-event FSKCW job. With the same
32,784-byte WTP parser reservation resident, the client submitted only the
headers for a separately declared 32,768-byte HTTP body. Admission returned the
required bounded 503 `resource_exhausted`; no body bytes were offered. The WTP
exchange completed in 1.653 seconds and the authenticated recovery request
succeeded.

Native continuity and RF ownership held throughout. The job completed and both
boards returned Empty/inactive/unowned. The same five independent evidence
mutations were rejected.

## Adversarial findings

1. The original RF auditor contained a growing packet-digest allowlist even
   though the caller already supplies the frozen digest and the packet is fully
   schema/profile validated. The redundant list was removed; exact packet bytes,
   helper hashes, source/image/boot and workload remain mandatory.
2. The first final audit assumed the last WTP write must be exactly one byte.
   Direct parser capacity can become fully reserved before the penultimate host
   byte, allowing a larger final bounded write after HTTP completes. The audit
   now requires every pre-response write to remain below the complete frame,
   the HTTP response to precede the final write, exact total bytes and the
   five-second whole-exchange deadline.
3. The first metric helper archive included local bytecode cache entries. Packet
   freezing rejected it before device access. The archive was rebuilt from
   reviewed source files only and the rejected root was retained.
4. A restoration check used an 11-character displayed revision. The device
   correctly reports 12 characters. Fresh evidence labels and the corrected
   `ca3c5dce4036` assertion passed.

No actionable finding remains in Package 2. The failed attempts retain no
acceptance credit and no threshold was relaxed.

## Restoration and scope

The bounded host fixture restored its exact baseline with no cleanup failures.
Fresh inventories show Pico A on `ca3c5dce4036`, boot
`5e0d6bc3e383b8c1cb4b0db9ed636bf5`, and Pico B unchanged on
`8921a7008183`, boot `6684b4b197d80cfa0ce83b3aaf205cb0`. Both are Empty,
inactive and unowned. Configuration is preserved and the shared reservation is
released.

This package used two controlled flashes and three 128-second RF jobs: one
failed proof attempt, one accepted supported packet and one accepted overload
packet. It made no configuration writes, controlled reboots or Wi-Fi cycles.

Package 2 is complete only for assertions 2.2a and 2.2b on Pico 2 W at 138 MHz,
PIO divider 1, GP2 PIO/DMA, RAM rendering and the recorded listener setup.
Assertions 2.2c–2.2f and Packages 3–9 remain open. R3–R6 and full Phase 11.5
remain open; the accepted-configuration list remains empty.
