# Phase 12 product-decision execution and adversarial review

Date: 2026-10-02. Work on `devel`, starting at `cc9e672313391e59237e6ab5b4941368c108e1f0`.
The [execution prompt](phase12-product-decisions-execution-prompt.md) was written
and executed under the [selected product contract](phase12-product-decisions.md).
This closes its software implementation/review scope; Phase 12 remains
**OPEN_PARTIAL**, with physical acceptance in the [closure matrix](phase12-closure-matrix.md).

## Implemented behavior

- Offline station saves persist a device-bound consumer profile. Existing
  trust/client lists are copied exactly even when time is unavailable or trust
  is expired; those credentials remain independently validation-gated. No
  station edit silently rotates trust. First offline saves use a strict version-2
  TLS-pending format: empty credentials, zero validity deadlines, canonical
  hostname/443 and no clients. Version-1 profiles remain readable and retain
  their serialization. Only missing TLS is generated after fresh accepted SNTP,
  while idle and outside another setup transaction, with bounded 30-second
  retry spacing and restart after durable completion/reconciliation. The exact
  original save digest survives the incremented journal generation. Browser
  results distinguish saved settings from readiness. RF time policy is unchanged.
- Production uses portable reset/storage orchestration. Provisioning reset
  first preserves effective consumer station values into the standalone store,
  keeps schedules/watermark, removes network credentials from retained config
  and purges superseded config history. Disabled station-only records are valid
  without schedules; an enabled configuration still requires schedules. Empty
  network fields represent retained operational-only configuration, not a valid
  network setup submission. Full erase removes operational records too.
- Durable access intent precedes destructive writes. Runtime immediately
  inhibits shared job authority and LAN admission, fences the current iteration
  and Console, drains only the recovery response, then reboots. Boot resumes
  idempotent preservation/profile clearing/access reset/operational clearing/
  bond clearing before transports start, verifies completion and reboots again.
  Both profile banks and BLE storage are wiped; alternating access-journal phase
  writes erase superseded access records. All adapter ranges exclude E10.
- `/recovery.html` provides separate actions, two explicit checkboxes and exact
  phrases. Recovery uses an independent three-minute single-use X25519/HKDF/
  ChaCha20-Poly1305 domain, bound to device, boot, slot, request and key/nonces.
  Unknown responses never automatically resubmit. Both inhibited and normal RF
  images include recovery; RF image station-save mutation remains under its
  existing restriction. Pending TLS materialization is available in both.
  The open AP supplies no operator authentication, as selected.

## Adversarial findings, repairs and reassessment

Independent implementation cross-review and a fresh independent assessor found
and repaired these actionable issues:

| Finding | Repair and behavioral evidence |
| --- | --- |
| Alternate access-bank corruption could strand a verified pending reset. | Admit only independently verified pending intent under alternate-bank corruption; ordinary corrupt authority remains rejected. Added journal corruption/resume regression. |
| Recovery loader could treat all corrupt configuration records as empty and discard schedules. | Ignore torn records only when a complete preserved configuration survives; otherwise fail closed. Added all-corrupt configuration with valid watermark/consumer-profile regression. |
| A marker-applied or failed-readback intent write could return failure without fencing runtime. | Production-used volatile `blocks_admission` latch survives uncertainty until reboot; callback quarantines and restarts. Added marker-applied failure and readback-failure reboot/resume cases. |
| Full erase could not recover a corrupt profile. | Permit Full with healthy access intent storage and idle authority; provisioning still requires readable profile preservation. Production storage-target corruption test added. |
| A network callback could write intent after the loop fence and allow same-iteration Console mutations. | Immediate job/LAN denial, post-network-poll fence and Console guard; final independent reassessment confirmed closure. |
| Station-claim access checks incorrectly excluded populated engineering state from recovery. | Recovery has a separate configuration and uses reset-coordinator activity checks, independent of station-save authority. |
| Confirmation ciphertext boundary excluded the longer provisioning phrase. | Corrected parser bounds and verified both browser-generated phrases against C++ crypto vectors. |

The second full adversarial assessment found no unresolved actionable finding
in this implemented scope. It explicitly excludes target durability, worker
shutdown timing, pressure, actual commissioning and RF qualification.

## Validation

Final results are recorded below after the final source checks. Private logs
remain under ignored `build/phase12-product-*`.

- Full retained-Mbed-TLS/lwIP host suite: **112/112 passed**, 83.54 seconds,
  including the actual localhost TLS/Plain LAN and recovery crypto checks.
- ASan/UBSan `field_access_tests`, `reset_storage_tests`,
  `consumer_claim_commit_tests`: **3/3 passed**.
- Default inhibited, GP14 opt-in inhibited and normal standalone RF builds
  pass on retained pinned SDK 2.3.1 and GNU Arm 15.3.1. Linked BOOTSEL absence,
  allocator wrappers, stack guards, SRAM placement and RF acceptance-control
  separation checks pass. Default GP14 remains OFF. These are development
  builds, not selected deployment candidates.
- WTP contract: 23 schema, seven raw JSON, framing and eight transition cases pass.
- C++ formatting, whitespace and six concurrent-file hash checks pass.
- Recovery browser tests cover two confirmations, exact phrase, stale boot,
  success/uncertainty and no destructive resubmit. Crypto tests check browser/C++
  vectors, every transcript binding, invalid tag and replay. TLS completion tests
  cover erase/every program cut both before and after application, reboot exact
  old/new authority and original digest. Production reset-target tests cover
  preserved consumer-only station, schedules/watermark, raw history removal,
  partial config erasure, full clear, corruption and ambiguous intent.
- Desktop and 390-pixel mobile mocked recovery preview inspected: checkbox
  alignment, consequence text, focus, disabled confirmation and wrapping pass;
  mobile document/scroll widths both 390 pixels. No device requests occurred.
  Impeccable detector ran once with no regex findings but degraded parser support;
  it did not evaluate computed contrast/selector matching.

Earlier checks retained: the first full suite ran during source changes and
found a stale corruption expectation and obsolete listener-source invariant,
which were repaired/rebuilt. Two TLS runs failed at different stages while
firmware compilation was concurrent. The final serial validation supersedes
those incomplete runs without claiming their root cause. Initial firmware
compile caught use of a private endpoint method; replaced with public disconnect.
No dependencies were installed/downloaded and no hardware was accessed.

## Remaining acceptance

Physical offline station-save/readiness transition, both destructive levels,
interrupted reset on target, populated trust retention, new phone, isolated
portal, recovery/network faults, resource pressure/soak, remaining GP14 RF/AP
row and exact restoration remain open. No new RF acquisition/job occurred;
ledger remains 16/11. Target actions need their consolidated exact approved
packet and fresh Ready. Six concurrent user files are excluded and preserved.
