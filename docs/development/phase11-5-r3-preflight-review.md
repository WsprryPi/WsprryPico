# R3 P0 execution and review — September 12, 2026

**P0 complete: 4/4 read-only captures. R3 physical acceptance: zero assertions
passed. Phase 11.5 remains OPEN at 2/6 families, with no accepted configuration.**
R1 stays closed 5/5 and R2 stays closed 7/7. The
[machine-readable result](phase11-5-r3-preflight-result.json) binds raw evidence,
observations, authorization and adversarial review.

The user explicitly approved staging the reviewed packet and five manifest files
at `/home/pi/phase11-5-r3-preflight-20260912`, then executing its four inventories.
This resolved the earlier automatic staging rejection; that historical preparation
result remains unchanged. Local staging archive entries and bytes, remote helper
hashes, packet hash and host boot were verified before execution. The frozen
packet SHA-256 was
`6695194cae5fbbf0611a2480e70074761be218da7e749f6c9f4b319fcf766119`.
The packet is now consumed and must not be replayed.

## Observed result

A-before, B-before, A-after and B-after completed in order. Each issued one INFO
and exactly HELLO/CAPS/GET_CLOCK/STATUS/PING, with one logical administration
session reused per board. Twenty WTP requests and four INFO requests completed;
each inventory took 75–79 milliseconds. The interval from run intent to the
final capture was 0.641234699 seconds, within the five-minute maximum.

| Board | USB serial | Observed firmware / clock | Boot and final authoritative state |
| --- | --- | --- | --- |
| A | `0BF4B4AEC9FFB344` | Original inhibited `802c91a7b86e-dirty`; clock not exposed by INFO | `587c672d4267e467649bb43765542284`; Empty, inactive, unowned, no job or terminal records |
| B | `CDDBF8767C506C07` | Unchanged inhibited `dbf1d86f0885-dirty`; clock not exposed by INFO | `feffcd075ab6cb0b74e7e0c2fde6c87f`; Empty, inactive, unowned, no job or terminal records |

Both device identities and boots matched the restored handoff snapshots and
remained unchanged throughout P0. Visible configuration fields and CAPS matched
before/after; no fault or admission blocker was observed. This does not establish
full private configuration byte parity or flash-journal position.

Both inhibited boards advertise 162 events, 110.592 seconds maximum job duration,
65,536-byte WTP payloads, eight replay entries per session, 300-second replay
expiry and eight terminal records with 3,600-second retention. These are fresh
**inhibited-image** CAPS observations, not physical-candidate resource acceptance.
The global duration restriction discussed in the
[source review](phase11-5-r3-preparation.md) remains unresolved for longer QRSS.

No firmware was installed and no RF job, CONFIG write, heap probe, fixture,
reset, BOOTSEL operation or service change ran. CONFIG remains **34/34**, probes
remain **six**. The selected physical 2e43110 / 138 MHz / divider 1 / RAM /
listener-on candidate remains distinct from the restored images above.

Read-only postchecks found the same host boot, installed WsprryPi PID 1957,
active chrony/GPSD/Avahi and unchanged radio MACs/states. No process retained the
four USB endpoints. Since this packet made no persistent device or host changes,
no restoration write or service operation was needed. Administrative session and
replay entries may persist until ordinary expiry; this is not a leak measurement.

## Adversarial assessment

The local copy reproduced the remote audit result exactly. The audit reconstructed
every Console response and CRC-checked WTP frame, validated schemas and exact
request/reply bindings, and checked source, serial, session, order, deadlines,
raw-to-summary equality and the packet/host run-intent binding.

Twelve temporary-copy mutations of this actual capture were rejected: truncated
envelope, missing record, forged CAPS summary, wrong board, wrong helper source,
forbidden Console write, wire CRC corruption, missing finish, swapped capture
order, wrong host, wrong packet and observation beyond the packet deadline.
The unchanged original evidence passed again afterward. Temporary mutations
did not touch the original logs or either board.

Publication review caught an attempted clock lookup absent from these older
inhibited INFO formats. The draft now records clock as unavailable rather than
inferring a fresh 150 MHz observation. No device retry or source change followed.
No actionable P0 source or evidence finding remained on repeat assessment.
The previously validated helper is unchanged, so its 15 deterministic tests
were not repeated merely for documentation. No C++ source changed and no
unrelated firmware/test matrix was rerun. JSON, links and diffs were checked.

## Change impact and next work

This result changes only P0 readiness and documentation. It invalidates no R1/R2
assertion and earns no R3 saturation, reclamation or timing credit. Preserve the
existing firmware and measurement identities and all historical failed attempts.

R3 A next requires its TLS/slot executor, independent observation/audit and
concrete finite RF packet. The new fixture/flashing/RF/CONFIG allowance has not
been granted. Carry 34 writes forward, reserve restoration and later R5 work,
and retain the global QRSS-duration issue explicitly when defining boundaries.
R3 B–D and R4–R6 remain outstanding. No further device action follows from P0.

## Documentation Impact

Updated: current ledger/index, P0 execution status, this review/result, preparation
pointer and Pi companion report. Historical preparation and R1/R2 result JSONs
remain unchanged. Firmware, production client/load helper, protocol, UI and
operator manuals are unchanged. The Phase 11.5 plan retains operator-documentation
follow-up after measured acceptance; no new operator limit is published here.
