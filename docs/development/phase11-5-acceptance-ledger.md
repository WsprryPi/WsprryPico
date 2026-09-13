# Phase 11.5 current acceptance ledger

Status on September 12, 2026: **OPEN; 2 of 6 families closed; no accepted
configuration.** [R2 closure and review](phase11-5-r2-continuation-review.md)
close **7/7 jobs**. R1 remains **5/5**, with explicit change-directed reuse.
The selected firmware is `2e43110f05304efdc2ae25c298baa0ef6426955b`, physical
138 MHz/divider 1/RAM/listener on. Three browser Tone jobs and native production
QRSS retain their 049cc929 identities; FSKCW, DFCW and WSPR passed on 2e43110.
The review identifies reused and newly measured assertions rather than relabeling
old measurements. Inhibited 150 MHz is regression evidence only.

The [closure result](phase11-5-r2-closure-result.json) records the explicitly accepted
administrative STATUS amendment and preserves the original strict-gap failure.
The earlier WSPR LOAD OOM, recovery and superseded unflashed images remain
recorded. At R2 closure both boards/configurations and host services were restored;
CONFIG writes were **34/34**, with six cumulative probes. R3–R6 require new bounded
packets. Future fixes invalidate affected assertions, not automatically all R1.

R3 [source review and tranche preparation](phase11-5-r3-preparation.md) now
identify the actual target boundaries, including the global 110.592-second
duration restriction that also affects QRSS. The next
[read-only admission packet](phase11-5-r3-preflight-prompt.md) completed
**4/4 fresh inventory captures** with **zero R3 physical assertions passed**;
the [P0 review](phase11-5-r3-preflight-review.md) records exact raw evidence and
twelve rejected mutations. At P0 completion both boards retained their original
inhibited images, unchanged boots and authoritative Empty/inactive/unowned state.
CONFIG was 34/34 and probes six. The P0 staging/USB grant is consumed.
The approved A1 attempt [failed before RF submission](phase11-5-r3-tls-failure-review.md)
because the pressure driver assumed Console INFO had WTP job/owner fields.
No job or pressure connection was submitted. A/B and the host were restored;
CONFIG is now **36/36**, probes six. A is back on original inhibited firmware,
boot `7a772a4eb283b23afdd1e25acbc449cd`; B's boot remains unchanged.
The failed packet is consumed. The driver/audit and recorded-response tests are
repaired, with no new physical acceptance credit. The subsequent
[A1b preparation packet](phase11-5-r3-tls-a1b-execution.md) and
[review](phase11-5-r3-tls-a1b-review.md) froze the corrected helpers, two new job
IDs and a specific proposed CONFIG 36→38 allowance. The supervisor re-audits
the failed attempt before host setup. At preparation, counters remained 36 and
six; the following paragraph records the subsequent execution outcome.

A1b subsequently [failed at its first HTTP check](phase11-5-r3-tls-a1b-failure-review.md).
One 100-second Tone completed and no second job was submitted. No pressure
assertion passed. Host cleanup succeeded; A remains Complete/inactive/unowned,
with the job retained on physical 2e43110. The user explicitly chose to keep the
test configuration between runs; the restoration timer was cancelled. Actual
CONFIG saves are 37, probes six. Fresh final A/B inventories confirm that baseline
and unchanged B. The [result](phase11-5-r3-tls-a1b-result.json) preserves the failed
attempt and the separate final-retention evidence. Future packets must reconcile
this state rather than reusing a spent packet or assuming original restoration.

The subsequent [A1c/A1e/A1f execution review](phase11-5-r3-completion-review.md)
retains zero acceptance. A1c failed network readiness before RF. A1d was staged
but never launched; automatic approval review required explicit permission for
its added Wi-Fi cycle. The user then approved A1e: one OFF/ON restored readiness,
and one Tone completed before a confirmed harness freshness failure. A1f used
no further cycle and completed two Tones and all ten traffic cases, but its frozen
audit failed on harness integration errors and a separate INFO completion-bracket
miss. Component evidence is retained without promoting it to acceptance.
Final A was Empty/inactive/unowned, B unchanged and host restored. The retained
test configuration remains in place; CONFIG saves remain 37 and probes six.
The user approved [A1g](phase11-5-r3-retained-a1g-execution.md)'s prospective
observation rule; network admission then failed before RF. A1h exposed a transient
JOINING admission bug before consuming its separately approved recovery/RF
allowance. [A1h2](phase11-5-r3-a1h2-result.json) completed that allowance and
passed the initial TLS/slot subset **10/10** under independent raw audit. Both
100-second Tones, 300-second production load and 360-second observation passed;
A was Empty/inactive/unowned, B unchanged and host restored. Configuration remains
37 saves and six cumulative probes. R3 is OPEN: TLS-FAIL/SLOT are partial, and the
remaining maximum-allocation, timeout, USB, retained-state and reclamation paths
still need physical acceptance. The [current review](phase11-5-r3-completion-review.md)
preserves all failures and exact scope. Phase 11.5 remains 2/6 families closed.

## Evidence that already exists

| Evidence | Exact scope | Reuse boundary |
| --- | --- | --- |
| [N1t A1/A2](phase11-5-n1t-result.json) | Two of the historical 20 cases passed on `8fb3894253ef45adc3aad28f25a684168487490f`; A3 failed | Preserve 2/20 as a historical count. Do not transfer its physical baselines to another firmware. |
| [Later single attempt](phase11-5-single-attempt-result.json) | `4058d3a4a95110326006a7db6e37eb4b562a500c`: inhibited A2 passed; physical conditioning failed | Preserve both the successful restricted evidence and the failed STATUS cadence. |
| [Historical e20ae8b builds](phase11-5-status-delivery-result.json) | `e20ae8bea2d5237af017dbd5f73bfe9332ce144e`: four clean linked ELF/UF2 records, host/source regression and linked checks | R1 inputs available. Builds alone do not close R1's physical comparisons or any RF gate. |
| [Current 138 MHz RF-idle diagnostic](phase11-5-status-delivery-repair.md) | Same `e20ae8b` candidate; 300-second controller/browser load and 360-second USB observation passed; boot `0fa996a26d9319f64385b23f3b6c62bf` | Reuse only measured idle/resource assertions. No full matched quiet/controller baseline or active RF. Credit wait/preservation/timeouts all zero; historical-stall causation remains unproven. |
| [Historical e20ae8b R1 time.local campaign](phase11-5-r1-review.md) | `e20ae8b`: four layouts and six target intervals; physical 138 MHz/divider 1/RAM/listener on; inhibited 150 MHz regression | R1 5/5 only. No RF jobs or R2–R6 acceptance. |

The historical e20ae8b physical candidate UF2 SHA-256 is
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

Historical 049cc929 image hashes and all four layouts are in
[049cc929 build identities](phase11-5-r2-amended-builds.json). The physical UF2 is
`908fbe87a326366710ca0b4be4541e71d26e46b9e439f2d0257a9bfcd1490192`.

## Revised family readiness

| Family | Status | Existing input | Required next evidence |
| --- | --- | --- | --- |
| R1 | CLOSED — 5/5 applicable to 2e43110 through impact review | Earlier 049cc929 layouts/intervals/probes plus affected new-image layout, heap and stack checks; [review](phase11-5-r2-continuation-review.md) | Reuse unaffected assertions; invalidate demonstrated impacts of future changes |
| R2 | CLOSED — 7/7 jobs | Three browser Tones, native production QRSS and USB FSKCW/DFCW/WSPR; [result](phase11-5-r2-closure-result.json) | Repeat affected paths only if later changes invalidate this evidence |
| R3 | OPEN — attempted, zero accepted assertions | Preserved A1/A1b tooling failures and A1c pre-RF rejoin failure | Approved bounded rejoin recovery, corrected TLS/slot execution, remaining boundary and reclamation assertions |
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
  for 11.6; **R2 also closed**, but **not accepted for full Phase 11.5**.
- Physical 132/150 MHz: **untested** in 11.5. Inhibited 150 MHz is separate.
- Selecting another clock during 11.6 requires the affected 11.5 checks and
  recalculated timing budgets; broad clock/band/spectral qualification is Phase 13.

Historical R1 read-only inventories after restoration: Pico A USB
`0BF4B4AEC9FFB344` returned to inhibited `802c91a7b86e-dirty`, boot
`a4e5c91e63bf3a3e40e8e311d378a076`; B USB `CDDBF8767C506C07` remained inhibited
`dbf1d86f0885-dirty`, boot `feffcd075ab6cb0b74e7e0c2fde6c87f`. Both were
authoritatively empty, inactive and unowned, with original configurations matching.
Host networking was restored and
installed WsprryPi PID 1957 remained unchanged. Refresh identity and state before
future hardware work. The historical first R1 admission preserved a boot mismatch; the user
confirmed rebooting both Picos between campaigns.

The preserved e20ae8b R2 restoration returned A to boot `f2b9d8477c33c856884485e87394e8fe`;
B retained its R1 boot. Both were empty, inactive and unowned; original
configurations matched. Host and permanent time.local/GPS-PPS were restored.
That attempt ended at 28/32 writes. The amended campaign restored A to boot
`8aadfedf02a066b47cb0ffb3c4068695`, with B unchanged and both inactive/unowned.
That campaign ended at **30 of 32** writes. The continuation/recovery then
reached 32/32, and the separately authorized repair run ended at **34 of 34**.
Reserve restoration and R5 schedule/rotation writes in a new bounded allowance
before more setup. Historical restoration inputs
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
remain explicit in the review. That historical R1 slice did not adapt R2–R6. R2 is now closed above; freeze new packets without modifying or rerunning preserved attempts.

Latest final inventories: A boot `587c672d4267e467649bb43765542284`, original
inhibited `802c91a7b86e-dirty`; B boot `feffcd075ab6cb0b74e7e0c2fde6c87f`,
inhibited `dbf1d86f0885-dirty`, unchanged. Both Empty/inactive/unowned and original
configurations matched. Host and permanent time.local/GPS-PPS were restored.
The selected 2e43110 [build record](phase11-5-r2-upload-builds.json) binds physical
and inhibited listener-on images; it does not claim new listener-off layouts.
