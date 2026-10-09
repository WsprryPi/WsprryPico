# GPIO/NTP research review closure

Recorded: 2026-10-09. Executed under the
[closure prompt](gpio-time-calibration-review-closure-prompt.md) on `devel`.
Status: research/documentation review complete; future implementation unselected.

## Outcome

The original [research conclusions](gpio-time-calibration-research.md) remain
unchanged. Closed-data review can proceed now; it does not need the remaining
RF campaign to finish. This follow-up uses the retained local intake only and
makes its calculation method and input binding durable in documentation.
It performs no additional bench reads or hardware/campaign service control.

The selected stages remain NTP filtering/UTC discipline, then NTP-derived Pico
calibration for GPIO/PIO, then optional GPS UTC + PPS. Si5351 transmission and
CLK2 feedback remain conditional future work, deferred pending GPIO results.
No implementation is selected by this closure.

## Executed work and reproduction

- Added the [exact research methods](gpio-time-calibration-research-methods.md)
  with source hashes. These are documented one-off calculations, not maintained
  product scripts or a calibration implementation.
- Added the [sanitized input manifest](gpio-time-calibration-intake-manifest.json)
  for the original 25 files. It excludes raw records, IQ, SSIDs, network addresses,
  credentials and source inode/mtime details. The full original transfer manifest
  remains private, with its SHA-256 bound by the public manifest.
- Extracted the published methods into ignored local storage and executed them
  against the original intake. Primary and independent result files match the
  earlier results byte-for-byte; the original transfer manifest and raw input
  hashes remain unchanged.
- Rechecked the independent exact-rational rates, percentiles, consistent single-
  accept clock updates and conditional endpoint intervals. Duplicated idle samples
  and skipped counters were not converted into extra observations.

Execution used local Python 3.14.8 and its standard library. Private checks/output
are retained under `build/gpio-time-review-closure-20261009/`. A fresh clone can
recover the method and input metadata, but still needs the exact private files.
No raw intake or generated network diagnostic output is published.
An isolated restoration check used the public manifest and recovered methods
with links to the same retained inputs, avoiding another copy or acquisition.
Its primary and independent output files also match byte-for-byte.

| Rechecked quantity | Result |
| --- | --- |
| Input cohort | 25 files; 187,925,869 bytes; all SHA-256 values verified |
| Coverage | 365,335 events; 2,563 target INFO rows; 249 A / 234 B anchors |
| Largest consistent single-accept offset update | A 201.404 ms; B 205.551 ms |
| Apparent long-span OLS timer error | A +0.908 ppm; B -0.735 ppm; diagnostic only |
| Conditional endpoint range | A [-9.112, +10.585] ppm; B [-1.209, +0.367] ppm; assumes valid reported endpoint budgets |
| Original browser-load disposition | Four B windows still below 300 requests; original failures preserved |

Both conditional endpoint ranges include zero. Neither is an OLS confidence
interval or independently established oscillator/RF uncertainty. Missing time-
source provenance and incomplete per-exchange history remain material limits.
The findings support investigating filtering, not automatic RF correction or
increased holdover.

## Work now and evidence gates

Retained-data/source/design review and documentation publication can finish now.
Stage 1 filter design or illustrative offline work can also proceed, but sparse
INFO cannot qualify absolute accuracy or every launch-admission decision.
Firmware implementation, automatic calibration and PPS capture remain unselected.
These evidence gates stay open rather than being closed by an offline calculation:

| Gate | Required exit evidence |
| --- | --- |
| E1: observation provenance | Accepted observation ID/source, peer, raw receive-monotonic time, estimated reference UTC, raw quality fields and acceptance reason, bound to board/boot/image/clock. Distinguish source arbitration from the latest network diagnostics. |
| E2: filtering effectiveness | Baseline, bounded filter and filter-plus-rate comparisons using suitable timing truth; assess absolute error when measurable, jitter, uncertainty, freshness, bootstrap/outage recovery and launch availability. Retain the age of older selected samples. |
| E3: rate-aware scheduling | Consistent forward/inverse UTC mapping, propagated arbitration intervals, timer rounding, leap behavior and armed-launch handling under bounded stale/step/reacquisition cases. Preserve raw monotonicity and the current launch gates. |
| E4: RF applicability | Confirm timer-to-PIO clock paths for the exact image/configuration; show stable disjoint-window estimates, a defensible bound and matching independent RF evidence. Select one correction authority and freeze prepared jobs; assess symbol-duration correction separately. |
| E5: GPS/PPS qualification | Electrical/peripheral/pin ownership, which UTC second each pulse labels, GNSS validity/leap state, capture latency/quantization, missing/extra pulses and source transitions/holdover on an identified target. |
| E6: independent tool/binary audit | Exact executed host-script and deployed-image association if that audit is required. Recorded revision/hash evidence and a contextual tool snapshot do not establish a fresh flash/script audit. |

Matched closed RF results may address part of E4; completing the current campaign
does not retroactively add E1 telemetry or prove E2/E5. Reconsider Si5351 only
after assessing GPIO results and obtaining a future operator selection. The
500 ms/90-second launch policy, manual fallback and complete local execution
remain unchanged. This work adds no campaign gate, request or waiting period.

## Adversarial assessments and publication

Closure inspection resolved three documentation gaps: methods had existed only
in ignored storage, the original Git-state paragraph needed an explicit
historical label, and the no-delay wording needed to describe campaign gate
dependencies without guaranteeing zero I/O effects. The appendix/manifest,
historical label and revised policy close those defects.

The first adversarial assessment then challenged reproduction and publication:

| Finding | Repair and disposition |
| --- | --- |
| Recovery could print hashes without enforcing them or checking that both methods were extracted. | Added exact block-count/name and SHA-256 checks, UTF-8/LF byte writes and private file permissions. Closed. |
| A composite calculation command could hide a child failure behind a later successful exit. | Reproduction now requires each child to succeed and parses its fresh stdout; documented shell commands stop on error. Closed. |
| The recovery-example check initially mistook inline backticks for a closing Markdown fence and failed compilation. | Corrected the check to recognize fences on their own lines; reran actual extraction and both intake paths. Closed. |
| A broad service prohibition could conflict with authorized Git origin access. | Scoped it to hardware/campaign services and explicitly retained Git publication authority. Closed. |
| Python optimization can disable the frozen methods' validation assertions. | Recovery refuses optimization; documented isolated commands ignore optimization environment variables. A deliberately wrong input hash was rejected with assertions enabled even under an optimized parent environment. Closed. |

The second assessment after repairs found no remaining actionable defect within
the research/documentation scope. Final checks confirmed:

- Both published method hashes match the original reviewed text. Original and
  restored-manifest execution reproduce the prior results byte-for-byte, with
  successful child exits and independently recomputed statistics.
- All 25 input size/hash bindings and the private transfer-manifest hash match;
  raw inputs and the original manifest remain unchanged. A changed SHA-256 in
  an isolated test manifest is refused before raw observation analysis.
- All 1,017 tracked product/source/helper/build files match the start snapshot;
  this task modifies research documentation only.
- Ten documentation/metadata files pass 274 local-link checks, seven anchor
  checks, 14 source-line references, 25 published intake rows and whitespace
  checks. Publication scans find no actual private SSID/LAN-address values or
  private keys; the public manifest contains only the permitted metadata keys.
- The local analysis/closure directories remain ignored; no raw records, IQ,
  generated diagnostics or pre-existing Si5351 tests enter the publication set.

No product unit tests, firmware build, hardware control or new RF qualification
was performed. E1-E6 remain explicit evidence limits rather than defects declared
closed by this review. The original report's Git state is historical.

The publication set comprises only this chat's research documentation, methods
as Markdown and sanitized intake metadata. Product code, tests, maintained
scripts, build files, raw evidence and generated firmware are excluded. Preserve
the pre-existing untracked Si5351 test directory outside the commit. Existing
`devel` ancestor commits are separate Phase 14 work; the normal branch push
includes them without claiming this research authored or qualified them.
Commit and independently verified remote parity are reported after publication.
