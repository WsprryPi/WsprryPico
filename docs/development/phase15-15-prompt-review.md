# P15.15 prompt preparation adversarial assessment

Date: 2026-10-17. Scope: the saved
[GPIO drive-strength prompt](phase15-15-execution-prompt.md),
[renamed default-build prompt](phase15-16-execution-prompt.md), current
[acceptance record](../implementation-plan.md#phase-15-acceptance-record)
and [prompt references](phase15-prompt-index.md).

This is an adversarial **self-review of planning documents**, not independent
review of an implementation. No drive-setting feature, firmware build, device
operation or RF test was executed. Implementation acceptance remains future work.

## Evidence inspected

- Pico configuration/update serialization, journal/storage, application and
  hardware responses, internal editor/validation/progress code, USB contract
  and accepted management paths.
- Pi strict application/hardware/capability validators, configuration and USB
  adapters, parent-owned UI/component paths and existing test targets. Pi was
  read-only throughout this planning task.
- The full previously saved default-build prompt and its originating recent
  "Assess WsprryPico installer options" handoff; the recent "Pico Release
  Checklist" list. No message or write was sent to either chat.
- Current Pico instructions and the Impeccable skill's existing-interface and
  Operate guidance. Source-derived controls/design conventions were inspected;
  no UI was changed or rendered during prompt preparation.

The initial Pico snapshot was `100e749c815f7485d5097c9086852d3b97adca9f` on
`devel`, with a modified plan, a modified USB source manifest and an untracked
default-build prompt. A concurrency guard detected a later plan change before
the first attempted write; that write stopped without modifying files. The
fresh document snapshot included the USB task's P15.14 closure, which was
preserved rather than reverted to the earlier in-progress status. This task
does not independently certify that separate USB acceptance.

## Assessment and repair passes

| Finding / attack | Risk | Requirement or document repair |
| --- | --- | --- |
| A new field is added to closed legacy application/hardware objects. | Existing Pi rejects the entire response, so unrelated settings break. | Require negotiated versioned views/operations, preserve old object shapes, immutable old/new exact-pair coverage and meaningful unsupported-client behavior. |
| Removing `drive` from an old `unavailable` list is treated as negotiation. | Old clients infer a capability they cannot encode; USB/network allowlists may still reject new routes. | Second-pass repair explicitly preserves truthful legacy availability and requires negotiated extension paths plus carrier allowlist coverage. |
| A legacy full save or older progress `apply all` omits drive. | A selected nondefault drive silently reverts to 4 mA. | Cover merge, legacy, replacement, Console, profile, Wi-Fi-only reset and draft semantics; second-pass repair names old progress `apply all` and atomic unsupported-mutation rejection. |
| Boot-active selection is described as actual physical drive. | Status claims electrical application before an RF adapter has initialized, including inhibited images. | Second-pass repair distinguishes the validated boot snapshot from verified pad readback and requires unavailable physical observation until initialization. |
| Drive-only changes compare only the pin plan. | A save misses the pending-restart latch or a later unrelated save clears inhibition. | Require drive in equality/revision/digests and hardware activation, A-to-B-to-A tests, existing sticky-latch behavior and immutable boot consumption. |
| Code casts 8 or 12 directly into the SDK enum, programs the wrong GPIO or applies while output is enabled. | Wrong pad strength or an RF transient; local and remote jobs disagree. | Require explicit named-constant mapping, selected-RF-pin scope, inhibited ordering through function changes, failure/readback checks and lifecycle tests. |
| UI-only implementation covers one editor or writes Pi-local GPIO settings. | USB/no-network, consumer/engineering or network/USB Pi workflows are incomplete. | Enumerate every supported surface and forwarding path, preserve separate Pi controls and reported WSPR power, and require actual event/request-path and desktop/mobile validation. |
| Broad hardware qualification is inferred from host checks or old bench captures. | False power/band claims or unauthorized RF work. | Require current setup authority, finite measured scope and restoration; retain historical qualification conditions. Second-pass repair prevents broad completion while required rows remain unresolved. |
| Only checklist labels shift while the saved default-build prompt stays at P15.15. | The wrong task runs, prerequisites become circular, or release/installer/docs omit drive. | Move the saved prompt to P15.16, update downstream identities/dependencies, retain its original review/commit/push terms, warn that the old pathname now means a different task, and inventory pending prompts. |
| Renumbering rewrites historical evidence or concurrent USB work. | Previously accepted source/results are misidentified or other work is lost. | Restrict renumbering to current planning views and the unexecuted saved prompt; preserve historical files/links and current USB closure. No Git mutation is part of this preparation. |

The first pass established coverage and the initial draft. The second pass
reassessed that draft and tightened the explicit legacy-availability,
old-progress-apply, physical-readback and completion requirements above. It also
clarified the renamed prompt's USB prerequisite and retained new-drive baseline.

## Final document reassessment

The repaired documents cover the requested four choices/default and every
requested management/UI surface, preservation, closed-schema compatibility,
activation, device/boot authority, failure and resource cases. The default-build
handoff remains a separate saved task after the new feature. No actionable
in-scope planning finding remains after the repairs and document checks.

Checks performed:

- All 19 task numbers are unique and consecutive; the first 14 titles/statuses
  match the fresh pre-edit plan, including concurrent USB closure.
- Previous pending tasks map exactly to P15.16–P15.19; the renamed saved prompt
  keeps all ten original major sections and its independent review,
  repair/retest/reassessment and commit/push requirements.
- The full list agrees with the authoritative plan's titles/statuses. Both
  future prompts are identified as unexecuted, and the new one grants no Git
  or hardware action during preparation.
- Local Markdown links resolve; historical evidence links in the pre-edit
  current documents remain present; historical Phase 15 files remain unchanged
  by this task. Changed/new documents pass trailing-whitespace and final-newline
  checks, plus `git diff --check`.

These checks validate planning consistency, not firmware behavior, visual
acceptance, USB operation or RF output. Exact new wire versions, compatible
persistence encoding and downgrade behavior must be resolved and tested against
the accepted source pair during execution. No runtime or UI implementation
test was appropriate for this documentation-only preparation.

## Documentation impact and repository boundary

Prepared/updated only six Pico planning documents: the implementation plan,
development index, new P15.15 prompt, renamed P15.16 prompt, this assessment and
the full list/prompt index. Existing product/USB evidence changes belong to the
concurrent USB task and were not authored here. Other family repositories and
existing chats were not modified. No staging, commit, push, release publication
or future-task execution was requested or performed by this planning task.

At final inspection, the concurrent USB task had separately advanced Pico
`devel` to `398b35a7e8caa27b334b5b8c75dca028ad8aa3e8`. The only remaining
Pico changes were these six planning paths: two modified tracked documents and
four untracked documents, with nothing staged. The Pi checkout was clean on
`devel`. These observations are a point-in-time report, not authority to commit
or push the planning work.
