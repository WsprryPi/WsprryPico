# Phase 11.5 current acceptance ledger

Status on September 12, 2026: **OPEN; 1 of 6 revised families closed; no accepted
configuration.** The [R1 time.local execution](phase11-5-r1-review.md) closes
**5 of 5 R1 assertions** on the exact physical 138 MHz candidate below, with
150 MHz inhibited shared-path regression. Both devices and the host were
restored. No RF jobs ran. The [earlier DNS failures](phase11-5-r1-dns-failure-review.md)
remain preserved; this count does not relabel historical evidence or accept
R2–R6. The six families contain multiple mandatory assertions.

## Evidence that already exists

| Evidence | Exact scope | Reuse boundary |
| --- | --- | --- |
| [N1t A1/A2](phase11-5-n1t-result.json) | Two of the historical 20 cases passed on `8fb3894253ef45adc3aad28f25a684168487490f`; A3 failed | Preserve 2/20 as a historical count. Do not transfer its physical baselines to another firmware. |
| [Later single attempt](phase11-5-single-attempt-result.json) | `4058d3a4a95110326006a7db6e37eb4b562a500c`: inhibited A2 passed; physical conditioning failed | Preserve both the successful restricted evidence and the failed STATUS cadence. |
| [Current candidate builds](phase11-5-status-delivery-result.json) | `e20ae8bea2d5237af017dbd5f73bfe9332ce144e`: four clean linked ELF/UF2 records, host/source regression and linked checks | R1 inputs available. Builds alone do not close R1's physical comparisons or any RF gate. |
| [Current 138 MHz RF-idle diagnostic](phase11-5-status-delivery-repair.md) | Same `e20ae8b` candidate; 300-second controller/browser load and 360-second USB observation passed; boot `0fa996a26d9319f64385b23f3b6c62bf` | Reuse only measured idle/resource assertions. No full matched quiet/controller baseline or active RF. Credit wait/preservation/timeouts all zero; historical-stall causation remains unproven. |
| [Current R1 time.local campaign](phase11-5-r1-review.md) | `e20ae8b`: four layouts and six target intervals; physical 138 MHz/divider 1/RAM/listener on; inhibited 150 MHz regression | R1 5/5 only. No RF jobs or R2–R6 acceptance. |

The physical candidate UF2 SHA-256 is
`7a7306b8ad9dab694903434b86aec18e249c79dad0443645cd04ca857e9d4a04`;
its ELF SHA-256 is
`2f5c5ce29c659ca9ffbbd5698c58fe96b0376578f4669b15d808a28584d42d5d`.
The inhibited companion UF2 is
`d4564a5c28db81e6e000542632cae3a4ae00f7a0263ecb4b2061f3f477c7e6e8`.
Actual tested production source is
`6f65d5c7d202569102459ab68d7c9ea079b96f35`, executable SHA-256
`122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`.
Neither a later Mac checkout nor the installed wspr5 executable is implicitly
this tested binary. Full dependencies, helper identities and archives remain
in the linked immutable results.

## Revised family readiness

| Family | Status | Existing input | Required next evidence |
| --- | --- | --- | --- |
| R1 | CLOSED — 5/5 | Four rechecked layouts; six target intervals; exactly three idle probes; [R1 result](phase11-5-r1-result.json) | Reuse only for the exact firmware/clock/layout scope; repeat affected checks if those inputs change |
| R2 | NOT RUN | Earlier mode/RF investigations identify paths, not acceptance of this candidate | Actual current-image state/mode/launch/refill/tail execution with normal traffic |
| R3 | NOT RUN | Existing functional tests and prior inhibited results | Distinct physical resource-boundary and reclamation assertions |
| R4 | NOT RUN | Existing ownership/replay/recovery semantics | Current-image physical authority, owner abort and interrupted-operation checks |
| R5 | NOT RUN | Prior network/storage/standalone evidence | Targeted physical lifecycle, journal rotation and autonomous scheduling under contention |
| R6 | NOT RUN | Prior inhibited soak is contextual only | Mixed physical workload after mandatory R1-R5 gates pass |

For each future packet, record its family/assertion IDs, exact inputs, prior
evidence reused with rationale, and `passed / failed / not run` counts. A failed
assertion stays failed even if later independent assertions pass. A family closes
only when every mandatory assertion has current applicable evidence. Report
historical 20-case counts and revised family counts separately; do not add them.

## Clock and device boundary

- 138 MHz, divider 1, RAM renderer, network listener on: **R1 closed**; selected
  for 11.6, **not accepted for full Phase 11.5**.
- Physical 132/150 MHz: **untested** in 11.5. Inhibited 150 MHz is separate.
- Selecting another clock during 11.6 requires the affected 11.5 checks and
  recalculated timing budgets; broad clock/band/spectral qualification is Phase 13.

Final R1 read-only inventories after restoration: Pico A USB
`0BF4B4AEC9FFB344` returned to inhibited `802c91a7b86e-dirty`, boot
`a4e5c91e63bf3a3e40e8e311d378a076`; B USB `CDDBF8767C506C07` remained inhibited
`dbf1d86f0885-dirty`, boot `feffcd075ab6cb0b74e7e0c2fde6c87f`. Both were
authoritatively empty, inactive and unowned, with original configurations matching.
Host networking was restored and
installed WsprryPi PID 1957 remained unchanged. Refresh identity and state before
future hardware work. The historical first R1 admission preserved a boot mismatch; the user
confirmed rebooting both Picos between campaigns.

Recorded cumulative configuration writes are **26 of 32**. Reserve restoration
and R5 schedule/rotation writes before more setup. Historical restoration inputs
and finite authorization windows are not permission to silently restart an old
campaign or reset its budget.

## Tooling readiness and historical register

The unchanged `phase11-5-register.json` retains its 20-case schema, older
`pending_candidate` snapshot and original PASS/FAIL entries. It remains valid
for that historical format; its `pending_candidate` is not today's selected
candidate. The current candidate and prospective readiness are recorded here.
Do not repin historical results or edit them into six-family passes.

The R1 slice adds an explicit e20ae8b registry, normal browser workload, bounded
executor, raw auditor and guarded reconciliation for user-confirmed reboots.
Historical defaults and the synthetic S workload remain intact. The current
executor admits native time.local mDNS/NTP from the independent client before
flashing and audits the target's own exchanges. All six intervals passed;
18,364-byte success/oversized NULL/recovery probes and matched quiet delta of
−8 bytes support scoped R1 closure. Both guards and observer costs were reviewed.
Permanent time.local and GPS/PPS services were preserved and verified after
cleanup. The original DNS failures and one later unlocalized Mac NTP timeout
remain explicit in the review. R2–R6 runner/closure adaptation remains outside
this slice; freeze new packets without modifying or rerunning preserved attempts.
