# Phase 11.5 Package 6 R3 closeout prompt

> Execution disposition: complete. The assertion-level and source-impact audit
> closes R3 with no new physical operation. See the
> [review](phase11-5-package6-review.md),
> [result](phase11-5-package6-result.json) and
> [adversarial result](phase11-5-package6-adversarial-result.json).

Execute only Phase 11.5 Package 6 in
`/Users/lbussy/GitHub/WsprryPico`. Preserve every Package 0-5 result and every
failed attempt. Close R3 only if all fourteen normative groups and all seven
extended-feature checks have current applicable evidence. Keep R4-R6 and full
Phase 11.5 open.

## Objective

Perform the assertion-level R3 closeout required by the accepted September 15
completion request:

1. reconcile the twenty-four mandatory R3 assertion rows into the fourteen
   groups `JOB-MAX`, `WTP-MAX`, `HTTP-MAX`, `COMBINED`, `TLS-SLOW`, `TLS-FAIL`,
   `SLOT`, `HTTP-PARTIAL`, `PROGRESS`, `USB`, `TLS-VALID`, `BROWSER-MAX`,
   `RETAINED` and `RECLAIM`;
2. reconcile extended features 1-7;
3. audit source applicability from each physical evidence image to the selected
   candidate;
4. resolve the current `R1.4`, `FEATURE.3` and `FEATURE.7` applicability flags;
5. produce a machine-readable result, independent auditor, adversarial mutation
   assessment and review; and
6. update only current status documents if every mandatory R3 item passes.

Package 6 is a closeout package. Do not repeat a physical test merely to give
Package 6 its own run. A new physical packet is required only if source-impact
review or evidence audit identifies a mandatory assertion that remains missing
or affected.

## Starting state and boundaries

- Repository branch: `devel`, clean at Package 5 commit
  `f981a53d9da0d9b17051e6cd4be208f57bab4ba2`.
- Selected physical candidate: Pico A, serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, source
  `2b25ca05c270819466a04498f9bc4894a4c5bace`, UF2 SHA-256
  `16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51`,
  boot `80d558e5804547749eca849c53ba27e1`.
- Pico B remains the unchanged comparator at source `8921a7008183`, boot
  `6684b4b197d80cfa0ce83b3aaf205cb0`.
- Exact configuration: Pico 2 W / RP2350 Arm, 138 MHz, divider 1, GP2 PIO/DMA,
  RAM renderer and network listener enabled.
- Package 5's final authoritative reads show both Picos Empty, inactive and
  unowned, scheduling disabled, the shared RF reservation released and the host
  fixture restored.

This package authorizes no RF job, flash, BOOTSEL transition, configuration
write, reboot, Wi-Fi cycle, network-fixture mutation or new device control. It
operates on committed source and immutable sanitized evidence. If a mandatory
physical gap is found, keep R3 open and freeze a separate finite packet under
the standing authorization rather than silently expanding this closeout.

## Immutable input set

Bind and independently validate these committed results:

- Group 1 controller/lifecycle: `phase11-5-r3-v2-validation-043.json`.
- Package 1 individual capacity: `phase11-5-memory-pressure-result.json`.
- Package 2 combined workload: `phase11-5-event-pages-result.json`.
- Package 3 network pressure/progress: `phase11-5-package3-result.json`.
- Package 4 USB parser pressure: `phase11-5-package4-result.json`.
- Package 4 unread-output completion:
  `phase11-5-package4-unread-retest2-result.json`.
- Package 5 retention/reclamation: `phase11-5-package5-result.json`.
- The current assertion register:
  `phase11-5-completion-matrix.json`.

Require exact SHA-256 values for every immutable result. Do not accept a row
because its prose says complete; validate its machine status, assertion IDs,
source/image/boot identity, applicable outcome, retained failures and closure
boundary.

## Source-impact review

Review two production-source ranges separately:

1. Package 1 source `8dd6f0812292e9264c2a72745078a95ee606c191`
   through the Package 2-4 source
   `ca3c5dce40360b7eea2f9c45618232caa68cdbb6`.
2. `ca3c5dce40360b7eea2f9c45618232caa68cdbb6` through the selected
   Package 5 source `2b25ca05c270819466a04498f9bc4894a4c5bace`.

Bind the exact changed production-file lists and diff hashes. Distinguish:

- changed event storage, allocation reporting and maximum-LOAD memory paths;
- unchanged TLS handshake, socket-slot, HTTP partial/stalled-I/O and WTP timeout
  mechanisms;
- unchanged USB frame parsing and unread-output buffering;
- unchanged RF worker, PIO/DMA launch/refill/tail behavior after the applicable
  physical-hour evidence; and
- unchanged protocol limits, retained-state capacities and TTLs.

The post-Package-4 production change transfers an already decoded request into
the service and moves its event pages into the accepted job. It lowers
simultaneous maximum-LOAD memory demand while preserving validation and response
semantics. Its affected path is not accepted from inspection alone: Package 5
must supply current-image maximum-event LOAD, RF, bounded-overload, retained
state and same-boot reclamation evidence. Earlier timeout and USB-pressure rows
may be reused only after proving their mechanisms were not changed.

Verify that no production source changed between the selected candidate and the
Package 6 repository state. Later documentation, auditor and test registration
changes do not create a new firmware identity.

## Required decisions

For each of the fourteen R3 groups, record:

- all member assertion IDs;
- physical board, source, image and boot that supplied the evidence;
- immutable result files and hashes;
- the relevant source-impact class;
- whether later evidence covers the affected path; and
- an explicit `ACCEPTED_APPLICABLE` or unresolved disposition.

For extended features 1-7, apply the same standard. In particular:

- `FEATURE.3`: accept only if Package 1 maximum-event capacity, Package 2
  per-path resident allocation, and Package 5 current-image maximum-event and
  reclamation observations jointly cover the changed memory path.
- `FEATURE.7`: accept only if Package 2 current shared-storage lifetime and
  Package 5 retained expiry and three equivalent same-boot cycles cover
  sustained reuse without monotonic retained growth.
- `R1.4`: preserve the historical R1 family closure and resolve current-image
  applicability only if Package 5's normalized same-boot cycles are equivalent,
  non-monotonic and within the unchanged 1,024-byte limit.

R3 may close only when all twenty-four R3 rows and all seven features are
`accepted/applicable`, every group has at least one valid evidence source, no
failed attempt is promoted, and the full accepted-configuration list remains
empty because R4-R6 have not closed.

## Validation and adversarial review

Add a deterministic Package 6 auditor and focused tests. The auditor must fail
closed on missing files, hash drift, candidate identity drift, changed source
ranges, missing group membership, nonaccepted assertions/features, weakened
limits, omitted Package 5 failures, incorrect hardware charge, false fixture
restoration, premature R4-R6 closure or a claimed full accepted configuration.

Run the documented host build and complete registered test suite because the
Package 6 validator becomes a registered check. Also run the focused Package 6
tests, syntax checks, JSON validation and repository consistency checks.

Perform an adversarial assessment against altered copies of the Package 6
result and matrix. Challenge identity, immutable hashes, source-impact ranges,
group membership, row counts, feature disposition, R1.4 applicability, Package
5 memory comparison, retained failure preservation, family counts, no-hardware
charge, restoration and remaining-scope boundaries.

Fix every actionable finding, rerun affected checks and perform a second
adversarial assessment. Do not weaken a frozen threshold or relabel a failed
attempt. If the final audit passes, publish Package 6 as complete, close R3,
advance Phase 11.5 to 3/6 families, make Package 7 the next package, commit to
`devel`, push `origin/devel`, and independently verify local/upstream/remote
parity.
