# R3 preparation and source review — September 12, 2026

This is the preserved preparation snapshot. The subsequently authorized P0
packet [completed 4/4 captures](phase11-5-r3-preflight-review.md), with no R3
physical acceptance credit. Its initial staging rejection was resolved by the
user's explicit authorization; the historical preparation result remains intact.

Phase 11.5 remains **OPEN, 2/6 families closed**. R1 remains 5/5 and R2 remains
7/7 under the existing [impact review](phase11-5-r2-continuation-review.md).
R3 has **zero accepted physical assertions**. Preparation does not close a gate.
The accepted-configuration list remains empty.

The next executable packet is the [R3 read-only admission prompt](phase11-5-r3-preflight-prompt.md).
It collects four inventories, using one logical session per board, before a new
fixture or RF packet is frozen. Its helper cannot flash, write configuration,
reset a board, activate a fixture or submit a job. All R1/R2 hardware windows
are spent. CONFIG remains 34/34 and cumulative heap probes remain six.

## Verified starting state

Mac Pico: clean `devel` at `3c656befadad80208f997a03e9fce078a8d4c9cd`.
Mac Pi: clean `devel` at `a068d706d276144e308d074cbe6042d54ca28576`.
These are preparation starting commits, not the eventual publication commits.

Read-only SSH outside the sandbox verified wspr5 boot
`220e53ca-ca95-4206-9581-dbe28aa1eeb8`, installed WsprryPi PID 1957,
active chrony/GPSD/Avahi, and the four expected radio MACs. This was a host
inspection, not fresh USB, GPSDO, PPS-reference or physical-wiring validation.

Both corrected local UF2s and both linked ELFs match the
[2e43110 build record](phase11-5-r2-upload-builds.json). The ELFs are under
`build/phase11-5-closure/6db650d-on/firmware/`. The detached source remains clean.
`git diff 2e43110 -- src firmware` is empty: the later coordinating checkout has
no firmware implementation difference. No rebuild or replacement image is needed
for this preparation. Generated artifacts remain ignored.

## Source-bound capacities and distinctions

These are implementation facts for selected source
`2e43110f05304efdc2ae25c298baa0ef6426955b`, not new target measurements. Confirm
advertised capabilities again on the physical candidate during authorized admission.

| Boundary | Source and current meaning |
| --- | --- |
| Network capacity | `src/network/pico/server.hpp`: two connection objects and one pending TCP connection; one established WTP connection. A second WTP connection has its own post-handshake rejection path. |
| Active RF admission | `src/standalone/pico/main.cpp` calls `set_active_job_connections(true)`. This is a global capability flag, not a browser-session count. USB ownership does not itself prevent new TLS connections on this image. |
| Pending / handshake | `src/network/pico/server.cpp`: 10 seconds; pending and activated-but-incomplete TLS are separate lifetimes. Handshakes are serialized. |
| HTTP / progress | Same source: 15 seconds from connection activation for HTTP, 30 seconds since progress for the general established transport. Slow header, slow body, stalled output and transport progress are distinct. |
| Failed handshake | Same source: fatal alert output retained until acknowledgement or a one-second bounded failed-handshake wait; do not confuse a client-close cleanup with proving this deadline. |
| TLS heap | Same source: 80 KiB budget, subject also to general memory admission. TLS use is included in application heap. Unexpected allocation failures are not predeclared passes. |
| Finite RF job | `src/rf/waveform.hpp` and `src/rf/wtp_profile.hpp`: at most 162 events and 110.592 seconds, for every exposed mode. The inhibited standalone profile shares these bounds. |
| WTP / HTTP | `src/wtp/codec.cpp` and `src/network/http.hpp`: individual WTP payload 65,536 bytes; HTTP body 32,768 bytes, headers 2,048 bytes. Transport admission does not prove valid job admission. |
| Browser file | `src/network/web/app.js` rejects `file.size > 30000`: 30,000 bytes is admitted by this check; 30,001 is rejected. The displayed wording says “smaller than”; test the actual inclusive predicate without changing UI here. |
| Retained state | `src/wtp/job_service.hpp/.cpp`: eight replay entries per session, sixteen logical sessions, 300-second replay and non-owner idle-session expiry; eight terminal records with 3,600-second retention. Normal reuse and intentional exhaustion require separate evidence. |
| Configuration journal | `src/standalone/storage.cpp`: two 4 KiB banks, two 2,048-byte records per bank. Rotation erases the alternate bank and appends there. Fresh slot inspection is needed to select the minimum write sequence. Watermark journal rotation is a different record size/path. |

The full-block interval at 138 MHz/divider 1 remains
3,799,188.406 ns; the conservative floored 75% budget remains 2,849,391 ns.
Every short predecessor needs its actual word count. Cumulative maxima are not
per-job samples and overlapping maxima must not be added.

### Longer QRSS capability issue

The user correctly pointed out that QRSS modes can exceed a WSPR frame's
110.592 seconds. The selected firmware's duration cap is **global**, not a test
limit or a QRSS protocol requirement. Enforcement occurs in the target CAPS
profile, `samples_at()` in `src/rf/waveform.cpp`, and admission/accounting in
`src/rf/pio_dma_sink.cpp`. WsprryPi's production execution planner also rejects
a job exceeding negotiated CAPS. Changing CAPS alone cannot enable longer jobs.

An expanded duration envelope remains a proposal, with no new limit selected.
It requires reviewing sample/count/time arithmetic, DMA lifecycle and deadline
calculations, plus meaningful long-job boundary tests. If implemented, review
the affected R3 maximum-job assertion and R2 launch/refill/tail applicability;
do not automatically repeat all R1 measurements. Event capacity is a separate
limit and must be considered for longer QRSS messages. No firmware change,
new RF permission, or claim of long-QRSS acceptance follows from this finding.

## R3 execution tranches

These are coverage assignments, not frozen executable RF packets. No old
20-case runner or R2 packet may be relabeled to execute them.

| Tranche | Required assertions | Preparation / acceptance status |
| --- | --- | --- |
| P0 — admission | A-before, B-before, A-after, B-after raw inventories; serial/device/boot, original state, CAPS, source and capture integrity | Executable read-only helper and audit prepared. 0/4 fresh captures; 0 physical acceptance assertions. |
| A — TLS and slots | Valid TLS/HTTPS control; source-distinct target failed lifetimes; supported slots, one-WTP restriction, pending admission/timeout and bounded excess rejection; fresh authenticated recovery after each trigger | Physical NOT RUN. Reuse unchanged 11.4 certificate semantics only after explicit source-impact mapping; never count wrong-name client validation as target rejection. |
| B — partial and stalled traffic | Slow handshake, partial HTTP header and body, stalled reader and writer; intended timeout origin, 2-second observation allowance and recovery within 15 seconds | Physical NOT RUN. Keep 10/15/30-second mechanisms separate. |
| C — boundaries and retained state | CAPS maximum valid finite job; 65,536-byte WTP payload; 32,768-byte HTTP body; actual browser threshold; unsupported simultaneous maxima; USB parser/unread-output pressure; replay, terminal and session capacity/expiry; ordinary reuse | Physical NOT RUN. Successful maximum allocation requires idle valid admission first; BUSY during RF does not prove allocation. Duration-envelope issue above must have an explicit disposition. |
| D — reclamation | One recovery per distinct A–C mechanism; three equivalent repetitions of the measured highest-resource path; resource-state equivalence and required expiry | Physical NOT RUN. Choose the representative path from observed resource use; do not invent which path is highest. Preserve equal terminal cardinality or budget 3,660 seconds. |

Permitted saturation must overlap an actual finite physical RF job. Plan from
CAPS; no proposed job may silently exceed the existing 110.592-second bound.
Use multiple separately identified finite jobs if necessary. No allocation
probes during owned/Armed/Running work. R3 profiles distinguish supported load
from deliberately unsupported load before execution.

The next RF packet needs its own executor/observer/auditor adaptation, frozen
jobs, positive/negative credentials, source-bound administrative cadence and
fixture/restoration policy. The existing device lifecycle hard-codes spent R2
counts for 2e43110 and correctly refuses a 34-write continuation. Do not alter
the old counter, reuse an old result root or invoke the spent recovery helpers.

### Future write budget

P0 adds zero CONFIG writes and zero probes. It cannot read the flash-journal
position through INFO and does not enter BOOTSEL to obtain it. Later R3 setup
and restoration ordinarily require two additional CONFIG writes (34→36).
Reserve R5 schedule installation/disable/restoration and the inspected minimum
rotation sequence separately; consecutive packets may share an authorized
fixture. This is a budget proposal, not authorization for writes 35 or 36 or
an invented R5 allowance. Keep counts cumulative and stop unknown writes.

## Change impact and retained evidence

| Change | Invalidated assertions | Applicable evidence | Targeted checks |
| --- | --- | --- | --- |
| New separate read-only P0 wrapper/auditor and tests | No R1/R2 physical assertion; new capture code needs validation | Exact R1/R2 image, layout, telemetry, failures and closure retain their original identities | Raw reconstruction tests, request/identity/deadline/budget mutations, prior raw inventory re-audits |
| R3 preparation documentation and companion report | None | All existing acceptance records, including amended STATUS disposition | Source/link/hash review, JSON validation and diff review |
| Global duration restriction finding | No source change and no automatic invalidation | Existing short-job results remain applicable to their recorded jobs | Trace profile, waveform and DMA limits; leave expanded duration unqualified |

## Adversarial assessment and validation

The first review required independent raw reconstruction instead of trusting
the inventory finish summary. Further assessment required WTP schema validation,
cross-capture chronological order, unique request IDs across captures, and binding
the full observation window to its packet and host run intent. All were fixed.
The final review checked that an active/faulted/changed board is retained as
blocked evidence and cannot trigger recovery, a BOOTSEL transition or a write.

Ten new deterministic tests pass, including fourteen raw-evidence mutations,
four cross-capture mutations, scope/budget/session guards, active/unknown/faulted
admission cases and a CLI check proving missing `--run` reaches no device action.
Intact synthetic evidence passes again after mutations. Five existing inventory
tests pass. The new auditor also reconstructs the four preserved R2 upload-run
before/after board inventories, retaining their historical identities and granting
no new physical credit. No C++ code changed, so the unrelated CTest matrix was
not repeated. JSON, relative links, artifact/source hashes and whitespace were checked.

Automatic approval review rejected remote staging before execution, requiring
explicit authorization for the exact transfer/destination. Files remain local.
A separate initial rejection of the companion-report edit was resolved by
providing the user's explicit cross-repository documentation authorization; that
edit then succeeded. Neither rejection was bypassed.

The repeat assessment found no remaining actionable defect in the bounded P0
helper/audit. Full R3 RF execution remains unimplemented, and the global duration
restriction remains an open capability issue. These are unfinished work, not
acceptance claims. The [machine-readable preparation result](phase11-5-r3-preparation-result.json)
records the exact packet/source hashes and zero fresh captures.

## Documentation Impact

Updated: this preparation record, the concrete P0 prompt/result, current ledger,
development index and Pi companion report. Considered but unchanged: firmware,
WTP/browser API contracts, UI and all historical results. No Impeccable review
is needed because this changes no UI or documentation depicting the UI.
Operator manuals remain outside scope; the existing Phase 11.5 plan lists the
exact follow-up paths after measured backend limits are accepted. Longer QRSS
support requires a separately resolved product envelope before those limits
can be published as accepted behavior.
