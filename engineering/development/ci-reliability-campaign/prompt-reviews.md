# Prompt adversarial reviews

These records concern the eleven execution prompts, not implemented fixes.
For each prompt, a first authoring assessment identified the issue below, the
prompt was corrected before acceptance, and a second assessment checked its
scope, dependencies, failure gates, accounting, and consistency with the shared
contract. Additional cross-phase findings are recorded as they are closed.

| Phase | First assessment finding | Correction in accepted prompt | Second assessment |
| --- | --- | --- | --- |
| 01 | Documentation branch growth could contaminate the runtime denominator or replace the baseline silently. | Separate executable identity from document-only commits; freeze unknown slices and require explicit cumulative reconciliation. | Closed; read-only scope, missing-evidence outcome, reproducible sets, and handoff checked. |
| 02 | A replacement required-status aggregator could return success after selection failure; settings approval could be confused with code completion. | Fail closed for missing/unknown dependency results; prepare exact settings changes, require separate approval/readback, and keep enforcement pending explicitly. | Closed; cancellation, optional publisher skips, format readers, no-CI scope, and independent continuation checked. |
| 03 | Killing a parent group can miss detached descendants; blanket zero-exit checks can reject intentional shutdown, and failed cleanup can invite unsafe profile deletion. | Map each owned descendant, define fixture-specific orderly termination, retain errors, and preserve live profiles until teardown is confirmed. | Closed; partial reads, late replies/crashes, idempotency, fault restoration, secret handling, and both-carrier gates checked. |
