# Prompt adversarial reviews

These records concern the eleven execution prompts, not implemented fixes.
For each prompt, a first authoring assessment identified the issue below, the
prompt was corrected before acceptance, and a second assessment checked its
scope, dependencies, failure gates, accounting, and consistency with the shared
contract. Additional cross-phase findings are recorded as they are closed.

| Phase | First assessment finding | Correction in accepted prompt | Second assessment |
| --- | --- | --- | --- |
| 01 | Documentation branch growth could contaminate the runtime denominator or replace the baseline silently. | Separate executable identity from document-only commits; freeze unknown slices and require explicit cumulative reconciliation. | Closed; read-only scope, missing-evidence outcome, reproducible sets, and handoff checked. |
