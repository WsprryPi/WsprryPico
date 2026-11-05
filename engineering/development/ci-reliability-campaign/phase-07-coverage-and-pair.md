# Phase 07 Close coverage and source pair gaps

Execute only phase 07 when explicitly invoked. Read the complete
[shared execution contract](README.md#shared-execution-contract),
[orientation](orientation.md), phase 01's obligation map, and accepted result/
lifecycle/synchronization evidence from phases 02 through 06. Recheck current
registrations and companion sources; preparation-time pins are not the target.

## Objective and scope

Activate valuable missing software coverage and make compatibility versus current
source-pair evidence explicit. Inspect tests/usb_tool_download_tests.py, the USB
installer and bootstrap wrapper, CMake registrations, scripts/ci/run.py,
bundle.py, inputs.json, relevant failure tests, and the actual Pi network/USB
recipes and consumers. Do not activate superseded control views or treat old
unregistered pair scripts as current integration tests.

## Work

1. Reconcile every required obligation to actual registration and execution.
   Verify the tool-download suite's current discovery, prerequisites, imports,
   fake network/tool boundaries, and cleanup. The earlier count of 39 methods
   is a lead, not a hardcoded substitute for current discovery or case execution.
2. Register the complete applicable suite in ordinary supported Linux CI and
   its strict expected inventory/results. Fail on empty discovery, missing tools,
   incorrect user/platform assumptions, and internal required skips. Preserve
   valid platform distinctions without claiming unexecuted contexts passed.
   Exercise download consent, tampering, archive traversal/symlinks, cache
   ownership, locks, cleanup refusal, and failure-before-device-write behavior.
   This phase's software regressions must not download tools or open real USB.
   Arrange the supported non-root execution context for consent/terminal tests;
   running as root and accepting their skip is not equivalent coverage.
3. Reconcile optional second-loopback and other conditional subcases. Decide
   which contexts are required on each supported runner and enforce those
   prerequisites there. Record intentionally optional/unavailable coverage
   separately, with reason and effect; a printed skip cannot silently become
   successful execution of a required obligation.
4. Freeze the intended current Pico/Pi candidate pair and dependency identities.
   Inspect production clients/coordinators, strict validators, generated assets,
   serializers, framing/ACK, and journals before changing the companion pin.
   Update only to an explicit reviewed immutable revision; never resolve mutable
   latest/devel at test execution or substitute an older peer to get green.
5. Reconcile the pin, advertisements/descriptors, negotiation/parsing, generated
   contracts, paired adapters, runtime consumption, and documentation if affected.
   Keep one current Control/1 schema under the prerelease policy and independently
   versioned WTP/transport/storage formats. Any companion implementation change
   requires explicit authority and intended-ref availability before delivery.
   Keep existing frozen-artifact verification and installer guarantees intact.

## Validation and adversarial assessment

Prove missing prerequisites, zero/partial discovery, an internal skip, forged
completion evidence, wrong companion source, changed limits, malformed descriptors,
unknown/superseded control versions, and identity/revision mismatches are refused.
Cover valid current documents and refusal before writes through production paths.
Do not relax validators, expected values, or carrier selection to accommodate
an inherited mismatch; resolve the integration problem in its proper owner.

Run activated and affected existing checks and both actual production network
and USB suites with the exact intended candidates and pinned dependencies.
Record compatibility checks separately from these current-pair results. Review
adversarially, fix, rerun affected checks, and reassess. Missing companion authority
or unavailable required dependencies blocks the affected acceptance gate.

## Acceptance and handoff

Deliver the coverage/discovery reconciliation, optional-context decisions,
immutable source pair and pin changes, actual results, and negative sensitivity
evidence. Disclose every newly activated case/process and its measured runtime;
it adds responsibility and earns no reduction credit. Reconcile cumulative costs
against phase 01, document remaining genuinely external limits, update phase 07
status only after all required gates pass, and stop.
