# P12.8 claim admission and commit boundary: adversarial review

Status: **VALIDATED DISCONNECTED SOURCE; P12.8–P12.12 AND PHASE 12 OPEN**
(2026-09-27). This checkpoint follows the approved
[Safari/SoftAP contract](phase12-7-decision.md) and
[execution prompt](phase12-7-12-execution-prompt.md). No owner HTTP route is
enabled and no consumer generation can be written by the production image.

## Executed prompt slice

In `devel`, add strict request parsing for the public claim endpoints, bound
owner-body allocation before JSON parsing, and put the already defined
claim slot and source-5 journal behind one portable commit boundary. Keep the
live route disabled until the Pico adapter, consumer boot authority and
target safety gates exist. Exercise malformed requests, precommit failures,
source mismatch, interrupted journal write and lost readiness; then review,
repair, reassess, commit and push the scoped result.

## Implemented source boundary

- The HTTP parser caps claim start/submit at 1,024 raw bytes, other owner
  requests at 4,096, and advanced client enrollment at 6,144 before body
  allocation. `owner_claim_http` requires the exact AP Host, Origin, owner
  header, JSON content type, method, route and field set. It rejects
  noncanonical IDs, base64url and source/generation combinations. The
  existing JSON parser rejects duplicate keys, including escaped duplicates.
  These functions parse but do not authorize, decrypt or dispatch a request.
- `commit_consumer_claim` requires a consumed matching physical slot, the
  exact current journal source/generation, the boot-classified unprovisioned
  or network-only runtime source, a checked owner point, fresh output/access
  safety, station association plus DHCP, and trusted UTC. It builds one
  owner/network/station/TLS profile, validates generated TLS and canonical
  serialization, then rechecks the clock, slot, journal, station and safety
  before the single journal selection. The Pico adapter still has to supply
  and prove these observations; this helper is not wired into firmware.
- A failed or unverified journal write returns `Reconcile`. A verified
  generation and terminal slot return `Committed`. A caller cannot infer a
  failed transaction from a lost response; later authenticated readback must
  compare the persisted request digest. Transient profile and serialized
  payload copies are scrubbed on every return.

## First adversarial assessment and repairs

| Finding | Repair |
| --- | --- |
| A generation-0 legacy journal may also boot from a matching factory bundle. Journal source alone cannot prove a blank consumer candidate. | The commit helper now requires the boot-classified runtime source and rejects Factory, Provisioned and Fault. A focused factory-negative test passes. |
| Certificate generation can outlive the 90-second trial or lose Wi-Fi readiness before the journal write. | The helper now rereads monotonic time, expires the slot, and checks station and trusted UTC after generation. Focused lapse and lost-station tests pass without a write. |

## Second adversarial assessment and repair

The next review found that accepting a hostname argument in claim values
could let a caller persist a certificate for a name other than the Pico's
derived local identity. The helper now obtains that hostname from the
platform adapter, requires canonical spelling, and compares it to generated
TLS material. Wrong local or generated hostname tests pass. It also found
that terminal receipt timing used the prewrite clock even if the journal
write crossed the trial deadline. The helper now samples monotonic time after
the write and returns `Reconcile` for a committed generation whose receipt
deadline was missed. That write-boundary test passes. A final code review
found no further actionable defect inside this **disconnected** admission/
commit slice; it did not review a nonexistent live adapter as safe.

## Validation and limits

The focused claim, storage, HTTP and commit tests pass. The full host suite
passed 111/111 with the installed Xcode 26.5 SDK and local loopback access.
The first in-sandbox run could not bind its mock TLS server to
`127.0.0.1:18443`; the same test passed outside the network sandbox. The
default RF-inhibited Pico 2 W image cross-build passed against pinned SDK
`079c6f39023649b154152db30f1d781e884879bc` and Arm GCC 15.3.1. A
later focused rerun and Pico cross-build passed after the hostname repair.
No image was flashed, no button or USB action occurred, and no RF was used.

The Pico AP still serves only WiFi-Bootstrap/1. The owner-key on-curve adapter,
physical claim sampling, trusted-clock admission, target TLS generation
resource/latency measurement, consumer runtime activation, owner sessions,
authenticated readback, Safari page and physical acceptance remain open.
Source-5 boot remains deliberately fail-closed, so this commit helper must
not be connected to a live route until the consumer boot path can select and
enforce the new authority without exposing engineering controls.
