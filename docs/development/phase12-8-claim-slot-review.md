# P12.8 portable consumer claim-slot review

Status: **PORTABLE AUTHORITY STATE ONLY; NO OWNER HTTP ROUTE OR TARGET CLAIM**
(2026-09-27). This follows the
[approved P12.7 decision](phase12-7-decision.md) and
[structural journal review](phase12-8-structural-foundation-review.md).

The new `ConsumerClaimSlot` permits one exact bound claimant. It checks the
full device, boot and slot IDs; owner and browser public-key encodings;
browser nonce; fixed Safari AP origin; and current journal source/generation.
A held button at start cannot claim. One 100–600 ms press/release in 60 seconds
grants the slot; the user then has five minutes to submit. Submit consumes the
slot once and must match the original binding. A trial has 90 seconds, and a
terminal result lasts 60 seconds. All deadlines use monotonic time; clock
rollback cancels the slot. A committed result requires generation exactly one
greater than the bound source and a digest of the completing request ID's 16
decoded bytes. No response-loss retry can reuse the consumed slot.

The slot is **not connected** to an HTTP handler. A future target adapter must
still validate P-256 owner points on curve, X25519 and AEAD, entropy, exact
current boot/journal, idle and output state, safe BOOTSEL topology and
transactional commit/readback. The class grants no BLE, WTP, station TLS or RF
authority. Candidate A remains on the earlier installed RF-inhibited
`fb091f8` network-only image; no flash, button press, credentials or RF action
occurred in this slice.

## Adversarial findings and repairs

| Finding | Repair |
| --- | --- |
| A provisioned sampler or output could become unsafe after the tap but before submit. | Recheck both at consume and cancel on a later unsafe/active sample, including granted and trial states. Tests cover both drifts. |
| The first source rule admitted virgin blank and network-only but stranded a device after a committed unprovisioned reset tombstone. | Allow a completed unprovisioned source at generation N to claim at N+1, subject to the future access-journal reset-intent gate. Test journal and slot cases. |
| The slot initially accepted a caller-provided request digest at finish. | Recompute SHA-256 over the decoded 16-byte request ID and require an exact match before reporting a committed generation. |
| Output could become active after the slot was consumed but before its terminal result. | Require idle output again at finish; cancel the slot on drift. A focused regression covers this final boundary. |

The second assessment traced start, bounce, held/long press, wrong current
binding, single consumption, commit generation, digest, activity/sampler drift,
deadline and terminal cleanup. Focused `consumer_claim_tests` and
`consumer_storage_tests` pass 2/2 after the final repair. The complete host
suite passed 96/96 immediately before that focused final repair; the repaired
claim boundary was rerun in its focused test. An RF-inhibited Pico 2 W
cross-build then passed with one SRAM BOOTSEL callback and no linked core-1
launcher; its unflashed UF2 SHA-256 is
`7849b5b041e3212c032dcef8f65c6223d16c785170f71aceb34924d0c9ca1c39`.
The second assessment found
no further actionable defect within the portable slot. It does not promote
the structurally valid test owner key to a cryptographically valid P-256 key,
or a test call to a real physical claim.

The remaining P12.8 gates are the Owner-HTTP/1 route and crypto vectors,
on-Pico CA/server credential generation, exact certificate/CSR validation,
durable activation and legacy-authority cutover. Safe provisioned/core-1
BOOTSEL and Safari AP/STA behavior require separate bounded target evidence.
