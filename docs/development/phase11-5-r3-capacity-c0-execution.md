# R3 C0: idle advertised WTP capacity admission

Executed and FAILED with a confirmed target allocation panic. No acceptance
credit; the original frozen preparation follows. Prepared under the user's comprehensive R3 execution and review request. This
packet performs no RF jobs, CLAIM/LOAD/ARM, CONFIG saves, Wi-Fi changes, flashing,
reboot or heap probes. It keeps the test configuration and physical wiring.

Packet SHA-256: `e5b9d24bea51101d3344e4c86c56a4128c03c8d317fca47914da8834dc41493c`.
Archive SHA-256: `d73b5546e2e8047056949434c049399479b22351675ce48b29a204c9478008f1`
(870,400 bytes, 76 public tooling/manifest files, zero private inputs).
Stager SHA-256: `26495073f3d96991dfca758c8bd100b9ab86eb7e96dd7ad206298fe9c415eec5`.
Fresh wspr5 root: `/home/pi/phase11-5-r3-capacity-c0-20260913`.
Local packet: `build/phase11-5-r3-capacity-c0/stage/packet.json`.

Use the exact A/B/host/physical-source identities in the
[complete execution prompt](phase11-5-r3-final-completion-prompt.md).
Inventory B then A before opening A's sole USB WTP endpoint exclusively. Require
both inactive/unowned, A's expected boot/source/138 MHz/RAM/GP2, healthy guards
and allocator reserve, and CAPS advertising 65,536 bytes. A fresh frozen logical
session sends HELLO, one valid STATUS padded outside JSON to exactly 65,536 bytes,
then one correctly framed/CRC-encoded 65,537-byte STATUS followed by a valid PING.
Require successful maximum STATUS, exactly one INVALID_FRAME advisory, and the
correct PING token on the same connection. Finish with a fresh ordinary STATUS.
No retry of any failed operation. Each duplex operation has a five-second bound;
the complete probe, including four inventories, has a 300-second bound.

Always attempt final A then B inventories. Require unchanged configuration,
boot/source/engine, RF launch/DMA/alarm/tail counters and authoritative Empty /
inactive / unowned status. Preserve source-defined terminal expiry; this idle
probe makes no terminal retention claim. No host network fixture is created.

The single-byte Endpoint feed transfers the completed parser buffer into dispatch,
requiring an exact 65,552-byte successful request. Prospectively require that new
largest allocation, zero unexpected allocator/TLS failures, 32 KiB reserve and
unchanged valid 4 KiB stack guards. This is idle admission only; it cannot establish
capacity under contention or relax old frozen RF evidence thresholds.

Pre-execution verification uses the actual compiled Endpoint/JobService with an
inhibited host engine. The exact 65,536-byte request succeeds; the complete
65,537-byte frame yields one INVALID_FRAME followed by the expected PING response
without closing. The driver's own control JSON requires chunked hex input; the
test now respects that wrapper limit while preserving exact transport bytes.
Five capacity tests pass. No firmware implementation changes were made.

After capture, independently reconstruct all four inventories and each complete
wire request/response, verify lengths/CRC/schema/identity, exact rejection and
recovery, chronology, helper hashes, resource results and supervisor agreement.
Adversarially mutate that evidence and repeat the intact audit before accepting
idle capacity. Continue the remaining R3 register; C0 cannot close R3.

## Outcome

See the [independent failure result](phase11-5-r3-c0-failure-result.json) and
[current review](phase11-5-r3-completion-review.md). Archive SHA-256:
`7fea4b144454fc7c4ffe909dc61450f1078f2753f564ad4916229047602cd06d`
(1,085,440 bytes, 84 files). Separate read-only reconciliation proved a recovery
boot, allocation panic and inactive/unowned A; B remained unchanged. No RF or
oversized frame was sent. Complete delivery of the maximum request is unproven.
