# Phase 11.5 Package 6 execution and adversarial review

## Outcome

Package 6 is **COMPLETE** and R3 is **CLOSED**. The closeout reconciles all
fourteen normative R3 groups, twenty-four mandatory assertion rows and seven
extended-feature checks. Phase 11.5 advances to **3 of 6 families closed**:
R1-R3 are closed in their recorded scope; R4-R6 remain open. No complete Phase
11.5 configuration is accepted.

The [execution prompt](phase11-5-package6-prompt.md) froze Package 6 as an
evidence/applicability closeout. Source and evidence review found no missing
physical assertion after Packages 1-5, so Package 6 performed no RF, flash,
configuration write, reboot, Wi-Fi cycle, fixture mutation or device control.
The [machine result](phase11-5-package6-result.json) records the decisions and
the [adversarial result](phase11-5-package6-adversarial-result.json) records the
final mutation assessment.

## Immutable evidence and candidate

The closeout binds thirteen committed inputs by exact SHA-256: the R2 closure,
software/boundary checkpoints 002 and 004, the three QRSS/FSKCW/DFCW physical
hours, controller/lifecycle checkpoint 043 and Package 1-5 result artifacts.
Their original source, image, boot, failure and limitation boundaries remain
unchanged.

The selected candidate remains Pico A source
`2b25ca05c270819466a04498f9bc4894a4c5bace`, UF2
`16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`
and boot `80d558e5804547749eca849c53ba27e1`: Pico 2 W / RP2350 Arm,
138 MHz, divider 1, GP2 PIO/DMA, RAM renderer and configured network listener.
No source under `src/`, `firmware/` or `cmake/` changed between that candidate
and Package 6. The top-level CMake change registers only the Package 5 and 6
host tests.

## Source-impact decision

The audit independently hashes and reconstructs two source ranges.

From Package 1 source `8dd6f08` to the Package 2-4 source `ca3c5dc`, changes
cover event storage, memory admission/reporting, adapters and related RF/compiler
support. Packages 2-4 supply the corresponding simultaneous-load, timeout and
USB-pressure evidence; Package 5 supplies later current-image coverage. The
three physical-hour results retain their exact original identities rather than
being relabeled as current-image measurements.

From `ca3c5dc` to the selected `2b25ca0` candidate, the only production changes
are in the network/scheduler/USB adapters and job service. They transfer an
already decoded request into the service and move its event pages into the
accepted job, reducing duplicated maximum-LOAD memory demand. They do not
change TLS deadlines, connection slots, HTTP partial-I/O handling, WTP progress
timers, USB parsing/output buffering, RF timing, limits or retained-state TTLs.
Package 5 physically covers the affected path on the current image with eight
maximum-event normalizers, three maximum-event bounded-overload cycles,
authenticated recovery, retained-state expiry and equivalent-state resource
comparisons.

## R3 group closeout

| Group | Assertions | Closeout basis |
| --- | ---: | --- |
| JOB-MAX | 3 | Atomic boundaries and three recorded physical hours plus Package 1 and current-image Package 5 maximum-event work |
| WTP-MAX | 2 | Package 1 exact payload boundary; Package 5 covers the repaired ownership path |
| HTTP-MAX | 2 | Package 1 HTTP boundary plus Package 2/5 current memory interaction and recovery |
| COMBINED | 2 | Package 2 supported overlap/bounded overload and three Package 5 current-image overload cycles |
| TLS-SLOW / TLS-FAIL / SLOT / HTTP-PARTIAL | 4 | Package 3 mechanisms are source-unchanged; Package 5 authenticates current-image recovery/resource guards |
| PROGRESS | 3 | Package 3's distinct drained/input/output-progress paths; later change affects ownership after decode rather than timers |
| USB | 2 | Package 4 parser/unread-output evidence; later move occurs after complete frame decode and does not change output/DTR handling |
| TLS-VALID / BROWSER-MAX | 2 | Package 1/3 accepted paths plus Package 5 current-image authenticated operation |
| RETAINED | 3 | Package 5 capacity, LRU and real replay/session/terminal expiry |
| RECLAIM | 1 | Package 5's three equivalent same-boot cycles, eight-byte spread and no monotonic growth |

All twenty-four rows are `accepted/applicable`. R3 closes without converting any
historical failure into credit.

## Extended features and R1.4

Features 1, 2, 4, 5 and 6 retain their existing software, boundary, physical-hour,
controller and R2 evidence. Package 6 resolves the two affected flags:

- `FEATURE.3` is applicable because Package 1 covers maximum individual
  capacity, Package 2 reports direct per-path residence and Package 5 exercises
  maximum-event memory/reclamation on the repaired candidate.
- `FEATURE.7` is applicable because Package 2 covers shared-storage lifetime
  under overlap and Package 5 covers real expiry plus three equivalent reuse
  cycles.

`R1.4` current-image applicability is also accepted from Package 5's normalized
same-boot cycles. Their post-live values span eight bytes, do not grow
monotonically and remain below the unchanged 1,024-byte gate. This preserves the
historical R1 closure and adds a current-image applicability decision; it does
not rewrite old R1 measurements.

## Adversarial review and repair

The first adversarial pass found two actionable weaknesses in the new closeout
auditor:

1. candidate source/image/boot were bound, but clock and engine/configuration
   fields were not exact; and
2. each group required some evidence, but the exact group-to-artifact mapping
   was not enforced.

The auditor now binds the complete candidate configuration, both exact source
ranges, changed-file lists, diff hashes, every immutable artifact hash and each
group/feature evidence assignment. The second assessment rejects all 25 altered
cases: source and clock identity, immutable hashes, source ranges/files/decision,
group presence/membership/evidence/disposition, matrix row state, feature
evidence/disposition/resolution, R1.4 resource comparison, failure preservation,
family status/count, accepted-configuration boundary, validation count, hardware charge,
restoration, invented physical credit and remaining scope. The intact result
passes again.

The final source-drift strengthening initially counted an unchanged Package 4
`add_test` context line as a new registration. The focused test exposed the
false rejection. The auditor now counts only added CMake lines, retains the exact
diff hash and still requires exactly the Package 5 and Package 6 host-test
registrations. The focused and adversarial assessments pass after that repair.

## Validation and final state

The focused Package 6 suite passes four tests. The documented host configure and
build pass, and the complete registered suite passes **76/76** including the new
Package 6 publication test. Python syntax checks, JSON parsing and the direct
Package 6 auditor pass.

Package 6 made no physical or fixture change. Its final-state statement inherits
Package 5's last authoritative evidence: both Picos Empty/inactive/unowned,
scheduling disabled, shared RF reservation released and host fixture restored.
No later Package 6 operation can change that state.

## Remaining boundary

Package 7 is next. It must close the remaining R4 authority/interruption rows;
Package 8 owns R5 network/storage/autonomous lifecycle and Package 9 owns R6
mixed operation. R5, R6 and full Phase 11.5 remain open, and the accepted
configuration remains empty until R4-R6 close.
