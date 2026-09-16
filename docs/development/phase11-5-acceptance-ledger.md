# Phase 11.5 current acceptance ledger

## Current completion campaign — September 15, 2026

**OPEN: R1 CLOSED 5/5; R2 CLOSED 7/7; R3 CLOSED; R4-R6 OPEN.** The
[current assertion matrix](phase11-5-completion-matrix.md) records current
applicability and remaining work. [Standing authorization](phase11-5-completion-authorization-20260915.md)
permits fresh bounded packets on either Pico with one shared RF reservation.
Pico A runs firmware `2b25ca05c270819466a04498f9bc4894a4c5bace`, image
`16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`
and boot `80d558e5804547749eca849c53ba27e1`; Pico B runs
`8921a7008183` on unchanged boot `6684b4b197d80cfa0ce83b3aaf205cb0`.
Repository HEAD is a separate identity. Both boards are independently
Empty/inactive/unowned, the shared reservation is Released and the host fixture
is restored.

Packages 1-6 are complete. [Package 5](phase11-5-package5-review.md) accepts all
4/4 replay/session/terminal/reclamation rows. Eight maximum-event normalizers,
three equivalent bounded-overload cycles and their 360-second quiet windows
produce an eight-byte post spread under the unchanged 1,024-byte gate; the
subsequent 3,660-second quiet interval expires all eight terminal records. The
[Package 6 closeout](phase11-5-package6-review.md) binds thirteen immutable
results, audits both source-impact ranges and accepts all fourteen R3 groups,
twenty-four mandatory rows and seven extended features. It resolves `R1.4`,
`FEATURE.3` and `FEATURE.7` without new physical work. R3 is closed; Package 7
and R4 are next. Phase 11.5 remains open at 3/6 families.

The records below preserve earlier identities, counts and outcomes. Their
then-current candidate and device restrictions are historical.

## Historical September 13 ledger

Status on September 13, 2026: **OPEN; 2 of 6 families closed; no accepted
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

Current R3: A1h2 and B2 passed 24 TLS/transport pressure cases on 2e43110; C0
then confirmed an allocation panic during idle maximum WTP admission. R3 remains
OPEN. That C0 attempt ended with A Empty/inactive/unowned in recovery boot
`bccea7c09794539c4f64bc22b0e76c56`; B was unchanged. See the
[current review](phase11-5-r3-completion-review.md) and
[machine register](phase11-5-r3-completion-result.json). Nine jobs/900 seconds
have completed in this effort; CONFIG remains 37, heap probes six. A prospective
diagnostic image is not a repaired or accepted configuration.

The user subsequently accepted **R3-COMPLETE-20260913-v2**, including the
32-character / 60-minute implementation and complete bounded execution/recovery
scope. D0 is now completed: one diagnostic flash, a full maximum STATUS request
and valid response, no RF, CONFIG writes, Wi-Fi cycles or heap probes. Its
[audited result](phase11-5-r3-d0-result.json) establishes fresh-boot maximum-input
success only. Last observed A is non-recovery, Empty/inactive/unowned in boot
`1271822b30097b5539961a7a2fe49302`, source `481da3c3ff17`; B is unchanged.
This does not establish a C0 fix or close another R3 group.

## Incremental v2 validation

The user explicitly requires preservation of passing tests as work proceeds.
Record each completed assertion before the next source or fixture change,
including evidence hashes, actual tested source/binary/device identities,
applicability and outstanding limits. Later failures do not erase independent
passes. Review each change for affected dependencies and runtime/layout impact;
rerun affected assertions, retain unaffected credit, and record the reason.
Keep earlier results immutable when adding a superseding result. A final-image
claim requires current applicable evidence for every mandatory assertion.

| Checkpoint | Preserved validation | Remaining boundary |
| --- | --- | --- |
| [v2-001](phase11-5-r3-v2-validation-001.json) | 41 host CTest groups; updated heap-checker seven-test pass; Pi plan 1,073 checks and 1,937 independent frequency vectors; local desktop/mobile browser checks; both provisional images linked and passed linked checks | Software/build evidence only. New Pi limit UI cases, parent request-builder checks, final image admission and physical extended-job/R3 acceptance remain outstanding. |
| [v2-002](phase11-5-r3-v2-validation-002.json) | 62 host CTest groups; Pi plan 1,085 checks and 1,937 independent frequency vectors; 6,871 production configuration/runtime checks; virtual-hour backend lifecycle checks; eight reviewed desktop/mobile browser captures with exact duration and numerical event ceilings | Software and local browser evidence only. A later HTTP-envelope boundary repair has a focused follow-up; current physical image admission and extended-job/R3 acceptance remain outstanding. |
| [v2-003](phase11-5-r3-v2-validation-003.json) | Four affected host groups pass after HTTP body/envelope separation and complete allocator-entry timing | Hardware-free assertions only; unrelated v2-002 checks retain scoped credit. |
| [v2-004](phase11-5-r3-v2-validation-004.json) | Seven independently audited E0a idle assertions on clean source `7d183978d08d`: extended image admission, 65,536-byte input, 65,537-byte rejection and same-connection recovery, 513-event and over-duration rejection, 512-event/3,600-second LOAD, Loaded ABORT/RELEASE | No RF job armed. Physical hour, Running contention and reclamation remain open. Ten evidence mutations rejected; intact evidence passes again. |
| [v2-005](phase11-5-r3-v2-validation-005.json) | S0: 10-second Tone and 32-character, 384-event QRSS at 143.250001 seconds completed; three renewals; exact launch/DMA/refill/tail and raw observation cadence verified on `7d183978d08d`, same E0a boot | Staged network-on USB RF admission only. No hour or saturation credit. Ten evidence mutations rejected and intact audit repeated. |
| [v2-006](phase11-5-r3-v2-validation-006.json) | H0: actual 3,600-second QRSS, 32 characters and 384 events; raw USB authority/cadence, exact launch/DMA/refill/tail, resource guards and final A/B state independently verified; ten core evidence mutations rejected | Preserve the completed physical QRSS hour. The separate combined HTTPS cadence audit failed on observer scheduling; no firmware failure inferred, no saturation or R3 closure claimed. Fresh H1a/H2a packets use a corrected scheduler. |
| [v2-007](phase11-5-r3-v2-validation-007.json) | H0 component audit: native production WTP and native HTTP full-hour coverage pass; all 182 HTTPS replies authenticate and show supported slot counts; three prior terminal records cross actual 3,600-second expiry correctly | HTTPS cadence remains FAILED under its unchanged bound. Component reporting preserves that failure. This adds scoped terminal TTL evidence, not full RETAINED or RECLAIM closure. |
| [v2-008](phase11-5-r3-v2-validation-008.json) | Reproduced and repaired unnecessary HTTP outer-padding admission/storage demand; affected API, adapter and real loopback TLS checks pass; both provisional firmware targets build and RF image checks pass | Software/source-patch credit only. Repair is not deployed; final identified image, equivalence assessment and affected physical HTTP/browser/contention checks remain required. Expired old-build credentials and denied loopback binding are recorded separately. |

Raw logs and tested binaries are retained under
`build/phase11-5-r3-v2-checkpoints/checkpoint-NNN/`; each public checkpoint binds
its hashes. The source snapshots are explicitly dirty checkpoints, not a clean
firmware deployment identity. D0 and all historical physical passes retain their
recorded image scope. Progress is tracked in
[the campaign record](phase11-5-r3-v2-campaign.json) and
[execution progress](phase11-5-r3-v2-progress.md).

The following R3 preparation/attempt history retains its original chronology.

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
| R1 | CLOSED — 5/5 with current applicability reviewed through Package 6 | Earlier layouts/intervals/probes plus Package 5 normalized same-boot resource cycles; [Package 6](phase11-5-package6-review.md) | Reuse unaffected assertions; invalidate only demonstrated impacts of future changes |
| R2 | CLOSED — 7/7 jobs | Three browser Tones, native production QRSS and USB FSKCW/DFCW/WSPR; [result](phase11-5-r2-closure-result.json) | Repeat affected paths only if later changes invalidate this evidence |
| R3 | CLOSED — 14/14 groups, 24/24 rows and 7/7 features | Packages 1-5 physical evidence plus exact Package 6 source-impact/applicability audit; [result](phase11-5-package6-result.json) | Preserve failed attempts and exact image scope; invalidate only affected rows after later production changes |
| R4 | OPEN — partial reusable evidence | Existing ownership/replay/recovery semantics and selected Group 1 physical results | Package 7 current-image authority, owner abort and interrupted-operation closeout |
| R5 | OPEN — idle Wi-Fi accepted | Prior network/storage/standalone evidence | Package 8 targeted physical lifecycle, journal rotation and autonomous scheduling under contention |
| R6 | OPEN — not run | Prior inhibited soak is contextual only | Package 9 mixed physical workload after mandatory R1-R5 gates pass |

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

Historical R2 final inventories: A boot `587c672d4267e467649bb43765542284`, original
inhibited `802c91a7b86e-dirty`; B boot `feffcd075ab6cb0b74e7e0c2fde6c87f`,
inhibited `dbf1d86f0885-dirty`, unchanged. Both Empty/inactive/unowned and original
configurations matched. Host and permanent time.local/GPS-PPS were restored.
The selected 2e43110 [build record](phase11-5-r2-upload-builds.json) binds physical
and inhibited listener-on images; it does not claim new listener-off layouts.

## R3 v2 scoped validation preservation

Checkpoints v2-006/007 preserve the complete QRSS hour and its separate HTTPS
cadence finding. Checkpoint v2-010 preserves the complete FSKCW hour and passing
independent native/Console/HTTPS observations, while retaining its failed full
USB observer gate. Both are actual source 7d183978/image 38daadfd/boot 8e777dadaa81
measurements; later-image reuse needs completed impact review and affected
physical regression. Checkpoint v2-011 preserves zero-RF recovery verification
and 62 passing host groups. These assertions do not close R3 or advance the
2/6 family count. H2b DFCW remains in progress. Keep A's tested RF image in place;
change it only for a demonstrated code defect and retain the repaired image.

### Additional immutable v2 checkpoints 012–016

- [012](phase11-5-r3-v2-validation-012.json): DFCW physical hour with full nominal contention.
- [013](phase11-5-r3-v2-validation-013.json): final c5f00b6 A idle admission.
- [014](phase11-5-r3-v2-validation-014.json): B deployment, zero RF and retained configuration.
- [015](phase11-5-r3-v2-validation-015.json): four BF0 HTTP assertions; original harness failure retained.
- [016](phase11-5-r3-v2-validation-016.json): six BF1 HTTP assertions and independently classified allocation fault/recovery state.

012/013 have additive dependency supplements preserving their original hashes.
Each later checkpoint freezes its complete isolated auditor closure. No full R3
family is closed by these component results. BF1 physical repair remains open.
