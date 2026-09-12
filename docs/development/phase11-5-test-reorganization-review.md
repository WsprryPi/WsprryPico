# Phase 11.5 test reorganization review

The [documentation-only prompt](phase11-5-test-reorganization-prompt.md) was
executed on September 12, 2026. The [current plan](phase11-5-plan.md) replaces
20 separately organized cases with six acceptance families and explicit subcase
traceability. This changes prospective test organization and workload definitions,
not firmware, application behavior, past results or executable tooling.

## Evidence and decisions

The intended use is autonomous scheduling plus WsprryPi, direct browser and USB
control of complete locally executed RF jobs. The essential gates remain real
RF timing/continuity, memory/stacks, bounded supported control, safe resource
rejection, ownership and recovery. Physical-idle or inhibited results cannot
supply active RF contention evidence.

Reviewed source establishes that the served page embeds CSS/JS and ordinary
refresh is action-driven. The prior load driver requests `/`, `/style.css` and
`/app.js` repeatedly and imposes periodic browser status with one-second lateness.
Those are retained as declared stress, not described as faithful ordinary page
behavior. Prospective N includes actual initialization, operator Refresh/control
and a page reload under RF; its concrete schedule must be frozen before execution.
The 1 Hz idle-controller count/gap gate remains. Source-bound scheduler wait
policy is separate; it cannot be silently substituted for idle cadence.

The six families consolidate shared state setup and measurements. Distinct
timeout, capacity, mutation, uncertain-operation and waveform paths remain
mandatory. Uniform 20-fold rejection tests and three full runs of every mode
are replaced with path coverage and explicit reclamation/endurance repetition.
R2 still begins with three Tone jobs; each other exposed mode runs once, with
the demanding paths repeated in R6. R3 repeats the selected highest-resource
reclamation path over three equal-state cycles. These are finite engineering
checks, not statistical reliability claims.

Exhaustive unchanged certificate semantics and discovery/cache permutations stay
in the relevant 11.4 functional regression evidence. Source-impact review and
representative current physical contention checks remain required. Nothing is
deferred merely because a previous test failed. Phase 11.6 retains per-band/mode
conducted acceptance; Phase 13 retains systematic clock/filter/spectral/release
work. No clock/configuration or revised family was accepted by this task.

## Adversarial assessment and repairs

| Round-one finding | Repair and check |
| --- | --- |
| Renaming the old matrix could imply that existing runners/validator implement the new plan. | Added prominent implementation-readiness boundaries in Pico plan/ledger and Pi review. The legacy JSON, all runner/test sources and validator are unchanged. A later code-authorized slice is explicitly required; bypassing the old validator is prohibited. |
| Historical 2/20 and the stale register candidate could be read as current-image acceptance. | Added a separate current ledger, exact current candidate/diagnostic scope and prominent historical pointers. Revised status is 0/6 families closed, with useful partial evidence itemized. No historical PASS/FAIL or result JSON changed. |
| Saturation coverage could be performed only at idle and falsely qualify RF contention. | Required physical RF during permitted pressure/reclamation; valid maximum-job admission and destructive probes occur separately at idle. BUSY cannot prove capacity. |
| Mode consolidation left the initial Tone repetition count ambiguous. | Specified three complete Tone jobs plus one per other exposed mode: seven initial jobs minimum. Required timing paths remain explicit. |
| Endurance wording could confuse 30 minutes of traffic with total wall-clock time and treat five minutes as sufficient cache expiry. | Specified 30 cumulative minutes N plus quiet time; three five-minute observations and final Q imply at least 51 minutes before setup/restoration, with extra expiry time when needed. |
| Owned-but-empty storage/control rejection could disappear from the merged state table. | Added claimed-but-empty alongside Loaded/Armed/Running where prohibited by the actual contract; retained complete host state/principal semantics. |
| Rotation could be silently dropped because only ten configuration writes remain. | Kept actual rotation as mandatory, with preallocated schedule/setup/restoration writes. If it does not fit, the assertion stays OPEN; no erase, budget reset or persistence-as-rotation claim. |

The repeated assessment checked all 20 mappings, all six family closure
conditions, N/S/O/M distinctions, current and historical identities, state-dependent
cadence, active RF requirements, quiet equivalence, standalone coverage, authority,
clock deadlines, restoration and code-readiness claims. No further actionable
documentation finding remained. Unimplemented tooling and unexecuted physical
coverage are explicitly outstanding, not review findings claimed resolved by prose.

## Validation performed

- Compared the archived old plan byte-for-byte with its pre-edit committed
  contents. SHA-256:
  `75f4d230e0aaf28330e03726c635a75520cf0c971850be2a9ce012dd98ed3700`.
- Checked the crosswalk contains all 20 A1-G1 IDs exactly once and maps each
  to the defined R1-R6 families.
- Checked current candidate source/ELF/UF2, tested production identity,
  restoration boots and write count against the unchanged latest result.
- Recalculated the 138 MHz full-block interval and conservative 75% budget;
  verified no new selected or accepted clock and no physical 132/150 MHz claim.
- Validated relative Markdown links in changed/new files and checked whitespace
  with `git diff --check` in each changed repository.
- Ran the inspected, read-only existing command:
  `python3 scripts/validate_phase11_5.py docs/development/phase11-5-register.json`.
  It reports legacy register valid, phase OPEN, zero accepted configurations.
  That result does not validate or execute the revised six-family campaign.
- Inspected changed/untracked paths: only scoped Markdown documentation. No
  historical result JSON, code, tests, runners or validators changed.

No firmware builds, application tests, hardware, SSH, USB, flashing, RF,
network/service mutations or fresh device inventory ran. Prior physical results
are cited with their original scope, not presented as tests of this documentation.

## Documentation Impact and next work

Updated: Pico plan, preserved legacy plan, reorganization prompt, current ledger,
this review, development index, historical review/continuation/progress pointers,
metric introduction, and Pi's companion Phase 11.5 development review.

Considered but unchanged: README/CONTRACT/architecture, normative WTP and browser
API, source/build/test files, legacy JSON register and all historical result
manifests. No product behavior or protocol limit changes here. Operator manuals
remain outside this slice; the exact future Wsprry_Pi_Docs paths are listed in
the coordinating plan and require measured acceptance before publication.

Next work needs separate code authority: adapt and test the existing workload
driver, subcase/evidence accounting and validator for the revised plan; freeze
exact executable packets and necessary hardware/network bounds. Then complete
R1's missing current-image evidence and the small R2 Tone packet before broader
mode, overload or endurance work. The documentation task itself is complete;
Phase 11.5 remains OPEN.
