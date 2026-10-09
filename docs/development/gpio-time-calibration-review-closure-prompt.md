# Execution prompt: close and publish the GPIO/NTP research review

Authorized on 2026-10-09 for the existing WsprryPico `devel` checkout. Execute
this prompt now using the retained closed-data intake. It does not depend on
completion of the separate active RF campaign. Produce reviewable research
documentation, fix actionable findings, repeat adversarial assessment, then
commit and push the documentation if the checks pass.

## Authority and scope

The latest operator request authorizes this follow-up and Git publication.
It supersedes the earlier acquisition prompt's no-commit/no-publication limit
for this documentation slice only. Preserve the earlier prompt and review as
dated records. The research-only boundary remains in force: no product source,
maintained scripts, tests, firmware, build definitions, application configuration,
PCB changes or hardware control. Research methods embedded in documentation,
sanitized evidence metadata and one-off ignored local calculations are allowed.

Do not contact wspr5 or any Pico, SDR, GPSDO, GNSS, serial port, hardware/campaign
service or reference API. Git origin access is authorized for publication below.
Use the 25 retained input files already copied and hashed under
`build/gpio-time-research-20261009/`. Do not add requests, logging, packet
captures, RF jobs, waits or acceptance gates to the running tests. Do not send
another chat a message. This execution needs no additional bench file reads.

Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md, the selected
[plan](gpio-time-calibration-plan.md), [original prompt](gpio-time-calibration-research-prompt.md)
and [research report](gpio-time-calibration-research.md). Inspect Git branch,
working tree, index and upstream. Preserve unrelated edits and the existing
untracked `tests/hardware/si5351-i2c/` tree. Do not reset, stash, force-push or
rewrite existing commits.

## Selected decisions to preserve

1. Consider NTP filtering and software UTC rate discipline first, with separate
   evidence for filtering alone and filtering plus rate discipline.
2. Consider NTP-derived Pico calibration for GPIO/PIO next. Carrier correction
   and symbol-duration correction remain separate design decisions.
3. Consider optional GPS UTC + PPS after that, without requiring a GPSDO,
   external counter IC or precision oscillator.

Si5351 remains a conditional future addition depending on GPIO RF results.
Its transmission engine and CLK2 feedback are deferred. No firmware implementation,
automatic correction, hardware purchase or longer holdover is selected here.
Preserve standalone operation, complete local jobs, one JobService, manual
correction fallback and the current 500 ms/90-second launch policy.

## Execute the review follow-up

1. Verify all retained input byte sizes and SHA-256 values. Confirm original
   acquisition identities, eight finite jobs, terminal state/output and browser
   failures. Do not promote CONTROL_COMPLETE into release or RF acceptance.
2. Challenge every previously closed finding. Check source-to-executed-byte
   provenance, exact uncertainty-to-PPM semantics, source references, non-atomic
   INFO joins, duplicated idle records, counter gaps and mixed peers/workloads.
   Preserve integer nanosecond arithmetic and explicit unknown source labels.
3. Make the calculation methods durable as documentation, rather than relying
   solely on ignored Python files. Publish their exact reviewed text and hashes
   in a method appendix. Add a sanitized analysis-input manifest with original
   relative paths, sizes, hashes and acquisition/copy cutoff metadata; exclude
   raw records, IQ, credentials, private SSIDs and private network addresses.
   Distinguish this analysis manifest from full original file-copy metadata.
4. Demonstrate reproduction by extracting the documented methods to a new
   ignored local closure directory. Execute those methods against the original
   retained intake, preserve raw inputs and compare output to the prior results.
   Confirm the public manifest describes exactly the same input cohort.
5. Recompute consequential statistics independently using exact rational
   arithmetic: endpoint/OLS rates, uncertainty/age/RTT percentiles, consistent
   single-accept updates and conditional endpoint intervals. A reported timing
   budget is not a validated oscillator bound or an OLS confidence interval.
6. Record what can proceed now and what must await additional evidence. Assign
   explicit exit evidence to filtering, UTC-rate discipline, automatic GPIO
   correction and optional PPS. Missing measurements remain open evidence gates,
   not review defects that can be closed by assumption. Completing the ongoing
   RF campaign alone cannot supply the missing per-observation time-source data.
7. Resolve misleading lifecycle wording: historical unstaged/uncommitted state
   must be labelled as historical; current publication authority must be clear;
   no promise of zero file-I/O interference may be inferred. No new gate may
   hold up the separate campaign.

## Deliverables and verification

Retain this comprehensive prompt; create an executed closure report and a
research-method appendix plus sanitized JSON intake manifest. Link these from
the existing plan, research report and development index. Reconcile roadmap and
Si5351 wording without changing historical acceptance or active Phase 14 records.
Include exact check outcomes, review findings/fixes, remaining evidence gates and
the bounded publication scope.

Check documentation links/anchors, source-line references against the recorded
firmware revision, whitespace, embedded-method hashes and public intake rows.
Scan the publication set for raw records, private SSIDs/addresses and secrets.
Use local file checks only; do not claim product tests, cross-builds or hardware
qualification were performed. Keep the analysis companion ignored and private.

After drafting, perform an adversarial assessment of both the research and the
publication set. Fix each actionable finding and rerun affected checks. Perform
another assessment after repairs; repeat if it reveals another actionable issue.
Record closed defects separately from unresolved measurement limitations.

## Commit, push and report

Refresh `origin/devel` and confirm a normal fast-forward push is possible.
Stage only the named research/documentation files, including the earlier six
documents from this chat. Inspect the exact staged paths and diff; do not stage
unrelated changes, raw evidence, build output or the pre-existing Si5351 test tree.
Commit on `devel` only after review/check closure. Push `devel` normally; its
existing ancestor commits necessarily travel with that branch. Do not count
those commits as implementation by this research or requalify them here.

Verify the remote branch SHA independently after push and report the actual
commit, push outcome, parity and remaining local state. If publication fails,
retain the local reviewed commit and report the concrete blocker. Do not report
a successful push merely because a local commit exists.
