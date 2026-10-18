# Repository and work-harness cleanup execution handoff

Execute only item 8, Repository and work-harness cleanup, in the
[Consolidated backlog](consolidated-backlog.md). Follow the
[permanent cleanup instructions](repository-cleanup-prompt.md) in full.
They define what cleanup means; this handoff adds the requested status,
independent review, commit/push and reporting sequence.

Preparing, saving or committing this prompt does not execute cleanup or change
item 8's status. The instructions below apply only when execution is requested.
Do not create another backlog, permanent cleanup report, evidence archive or
replacement history document.

## 1. Read the contract and inspect the current state

Work in /Users/lbussy/GitHub/WsprryPico. Read AGENTS.md, README.md, CONTRACT.md,
docs/architecture.md, docs/development/README.md, the canonical backlog and
the complete permanent cleanup instructions before changing anything.
Use successor paths if an authorized reorganization has already moved them.
Print the complete current Finish now section in its existing order, including
all NTP Work subitems and selected requirements. Use ✅ finished, ⏳ in flight
and ▧ not started.

Record the actual checkout/worktree, branch, full HEAD, upstream, live remote
tip, staged/unstaged/untracked changes and concurrent work. At preparation,
devel and live origin/devel were
ebe7f9b5f2974668dbc1411120adf2968d69b3b3, with substantial unfinished NTP and
USB installer work and separate backlog edits. This is a snapshot, not a reset
target or permission to include those changes. Refresh it at execution.

Preserve user edits, unique source, active investigations, live configuration,
credentials, recovery inputs, current toolchains and shared tools. Do not
reset, stash, clean, discard edits, rewrite history or absorb another task's
work. A dirty working tree is not a cleanup failure or a reason to erase it.
Partially stage shared files when necessary; preserve another task's index
entries rather than committing or unstaging them.

Execution authorizes the cleanup defined by the permanent instructions,
appropriate deterministic checks, a separate read-only adversarial reviewer,
and the scoped commits/non-force pushes described below. The expected branch
is devel tracking origin/devel; verify the actual accepted destination before
writing or pushing. Other maintained repositories remain outside the write
scope. No release/tag/site publication, firmware behavior change, hardware/RF
operation, installed-service change or execution of another backlog item is
authorized by this cleanup handoff.

## 2. Mark item 8 pending and commit/push that state first

Use ⏳ in flight for the requested pending state while cleanup is unfinished;
preserve the existing legend. Change only item 8's status and retain both its
permanent-guidance link and this handoff link. Do not reset another item's
status, change priorities or incorporate unrelated backlog proposals.

Inspect and commit only that status hunk, then non-force push it to the verified
upstream. Independently query the live remote and verify the intended commit.
If item 8 is already ⏳, inspect whether that exact pending state is already
committed and published; complete a missing commit/push without an empty or
duplicate commit. Do not repeat an already accepted completed cleanup blindly.

This is the first publication point. Complete it before cleanup mutations.
If it cannot be committed/pushed, preserve the actual state and report the
specific blocker before deleting or rewriting cleanup candidates. Read-only
discovery may continue. The initial status update does not waive the inventory
required before the first cleanup change.

## 3. Inventory and execute the permanent cleanup definition

Follow all stages of the permanent instructions. Inspect tracked, untracked
and ignored material in the checkout, attributable local work areas and
identified Raspberry Pi harnesses. Resolve physical paths and aliases, verify
ownership/current use and preserve shared or active material. Historical host
names and paths are discovery leads, never deletion allowlists.

Present the DELETE / REWRITE / RETAIN / HOLD inventory before cleanup changes.
Include exact host/path, role, extent, pre-existing work, references, active use,
audience, reason, retained engineering destination and validation needs. Keep
the detailed inventory in private temporary storage outside maintained source;
link it while needed without copying raw evidence or secrets into a report.
An inventory is not another work roadmap or a mandatory per-file approval gate.

Proceed through clear, inspected in-scope actions. Keep uncertain items on HOLD
and continue independent work. Recheck content, physical target and active use
before deletion. Do not delete first and investigate later, or destroy the sole
input needed by ongoing work. For untracked/external deletions, retain enough
inspection detail for the reviewer to assess the decision without creating a
backup archive of material selected for deletion.

Apply the operator prose standard to meaning and structure throughout README
and other non-engineering material. Describe present capabilities and actual
operating decisions in plain language. The intended level is:

> WsprryPico transmits WSPR, QRSS, FSKCW and DFCW as a standalone device or
> as part of a WsprryPi fleet.

Verify the actual capabilities and preserve relevant operating limits. Remove
the engineering status/validation catalogue, even where its individual facts
are true. Consolidate needed technical information in maintained engineering
material with appropriate applicability. Do not simply shorten or relocate the
development story, substitute an engineering link for the explanation, or add
a documentation placeholder, unavailable site link or future promise.

Remove development phase/step framing outside explicitly retained active plans;
preserve actual operating procedures and technical meanings of those words.
Delete obsolete project outputs and completed/superseded/abandoned execution
prompts, handoffs and reviews according to the inventory. A completed checklist
link or record-presence test does not justify keeping an obsolete prompt.
Repair references and consolidate useful current facts instead. Keep selected
unfinished handoffs and reusable instructions; retain this handoff only while
its execution still needs it, then retire it at the completion publication.

Preserve behavioral coverage, schemas/conformance vectors, licenses, current
contracts, deployment/recovery images with a present duty and necessary source
provenance. Narrow or remove unsupported claims rather than allowing evidence
deletion to broaden qualification. Do not manufacture a new hardware campaign
to replace retired evidence. Do not rename /docs, build the operator site or
publish Read the Docs here; that remains its separate selected task.

Keep the canonical backlog's selected work, requirements, priorities and
statuses intact except item 8. Repair its links when obsolete material is
retired, without creating a parallel list or erasing accepted dispositions.
Refresh the inventory and working-state checks during a long execution so
concurrent NTP, installer or other work remains protected.

## 4. Validate the retained result

Use the permanent instructions' reference, content and workflow validation.
Inspect retained tracked and relevant untracked callers of every removed or
renamed path: Markdown links/anchors, images, JSON/YAML, schemas, CMake/presets,
tests, scripts, CI/packaging inputs and engineering navigation.

Read the resulting operator text as an operator. Confirm the product's purpose,
current capabilities and relevant limitations are understandable without an
engineering chronology or chain of validation records. Confirm needed technical
information has a current engineering home, old execution prompts are gone
where obsolete, and no documentation stub or future promise was introduced.

Derive affected deterministic checks from the current development guide and
actual registrations. Documentation-only edits require link/reference/content
and formatting checks; changed fixtures, build inputs or harness tools require
their meaningful affected checks. Do not weaken behavioral tests to remove
history, invent commands, install an SDK incidentally or retry known broken
local macOS C++ compilation without explicit toolchain-repair authorization.
Use the identified supported Linux/Pi environment where necessary.

Record exact commands/results, failures, skips and limitations in the temporary
review material. Confirm retained tools, current images and active workloads
remain available without opening devices. Recheck reachable cleanup hosts and
actual removed targets; distinguish logical bytes removed from measured free
space. Do not claim a host was cleaned merely because SSH or a script exited.

## 5. Independently review, repair and adversarially check the fixes

Use a separate reviewer agent that did not implement the cleanup. Its authority
is read-only inspection of this slice, inventory, necessary original tracked
content through Git history, retained files and validation results. It must not
edit source, delete files, mutate Git, publish, change services or operate
hardware. Supply this request, the permanent cleanup definition, complete diff,
pre-existing work boundaries, exact deletion inventory, reference repairs and
current check results. Include external/untracked deletions; a Git diff alone
does not cover them.

Require an adversarial challenge of mistaken deletion, concealed user changes,
lost unique engineering content, active/recovery dependencies, shared-harness
scope, dangling links or inputs, lost behavioral coverage, obsolete prompts
retained through backlinks, unreadable operator prose, remaining development
narratives, invented documentation promises, license/provenance loss and
broadened hardware/RF/support claims. Check every claimed host and completion
condition, not just the edited prose.

For each actionable finding, record the issue and consequence, repair it within
scope, rerun affected checks and return the revised complete candidate to an
independent reviewer. Require the reviewer to adversarially check the fixes and
their consequences, including whether the original requirement now holds and
whether the repair creates another defect. Repeat repair, retest and fresh
review until no actionable finding remains. Self-review or merely repeating a
previous pass is insufficient.

Bind the final assessment to the actual final diff, retained files, inventory
and checks. Any substantive later edit requires affected validation and renewed
independent assessment. Legitimate retention for active work is not a failure;
an unresolved required deletion, unknown dependency, inaccessible required host,
failed check or actionable review finding remains a completion gap. Keep item 8
⏳ until those gaps are resolved or the user explicitly changes the task scope.

## 6. Commit and push the reviewed cleanup while item 8 stays pending

After checks and independent reassessment pass, inspect the full current dirty
and staged state and exact scoped hunks. Stage only attributable cleanup,
necessary reference/test repairs and reviewed engineering updates. Keep item 8
⏳. Do not include other work merely because it shares a file or directory.
Run applicable diff checks, commit the reviewed cleanup and non-force push it.
Independently verify the live remote contains the intended commit.
If the push triggers required CI, wait for its actual final-source results;
an earlier passing run is not this commit's evidence. A new failure returns to
repair, affected validation and independent review while item 8 remains ⏳.

This is the second publication point, separate from both the initial pending
commit and the completion commit. Additional scoped work commits are permitted
when needed, but never combine unpublished repairs with a false done status.
If a push fails, report the actual local/remote state and leave completion open.
Inspect and preserve concurrent remote commits; do not force-push, rewrite
published history or use reset/stash to get around another task's changes.

## 7. Mark done, retire this execution prompt and commit/push separately

Recheck acceptance against the final published cleanup, review dispositions,
required local/Pi scope and validation. Have the independent reviewer assess
the proposed completion hunk and retirement of this now-finished handoff.
The reusable cleanup instructions and their AGENTS/development breadcrumbs must
remain available; this task-specific prompt must not become another old record.

Only after completion is established, change item 8 from ⏳ to ✅, remove this
handoff file and its Saved prompt link from the checklist, and repair any other
live reference to it. Retain item 8's permanent Cleanup guidance link. Review
and check these exact closure changes before committing; any substantive new
cleanup or repair must return to the validation/review/work-publication loop.
Do not create a replacement completion journal or archive of this prompt.

Commit and non-force push the completion changes as a distinct third
publication point. Independently verify the live remote tip against local HEAD
and upstream, and verify that the completed status, permanent-guidance link and
handoff retirement are actually published. A local status edit or successful
work push alone does not establish this completion push.

## 8. Report and print the current checklist

Report the concrete operator/engineering changes, deleted artifact/prompt
categories and counts/size by host, retained exceptions and reasons, inaccessible
locations or remaining gaps, exact checks/results, adversarial findings,
repairs and independent reassessment. Report the pending, reviewed-work and
completion commit identities, actual push/remote verification and remaining
staged/unstaged/untracked work. Acknowledge any incomplete stage directly;
do not call required uninspected scope complete.

Keep this report in the conversation. Link the temporary inventory while it is
needed, then remove disposable validation/review scratch after its purpose
ends. Do not commit captures, sensitive backups, bulk evidence or a permanent
cleanup diary. Preserve the usable retained development environment.

Finally, reread the sole canonical backlog and print its complete current
Finish now section, preserving order, links, NTP Work grouping and every current
status. Use ✅ finished, ⏳ in flight and ▧ not started. Report actual state,
including concurrent updates, rather than reproducing an earlier snapshot.
