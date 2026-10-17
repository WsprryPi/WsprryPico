# Execute the accepted 100 ms UTC admission policy

## Objective and authorized scope

Work on `devel` in `/Users/lbussy/GitHub/WsprryPi` and
`/Users/lbussy/GitHub/WsprryPico`. Implement the user's accepted 100 ms ordinary
operation UTC uncertainty policy, validate it, review adversarially, repair
every actionable finding and reassess, then commit and push each repository.
This is a product code/configuration and validation change, not a harness-only
override. Preserve unrelated work and concurrent commits. Do not change a
third repository, install services, replace the running Pi application, change
host clock configuration, or transmit RF.

Read each repository's applicable AGENTS.md and current architecture,
configuration, development and USB timing contracts. Pico's README.md,
CONTRACT.md and docs/architecture.md remain architectural authority. Inspect
branch, staged/unstaged/untracked state and exact source revisions before edits.
Do not reset, stash, amend or discard work. Keep all changes on `devel`.

The accepted rationale and preceding repair are in
`docs/development/usb-time-uncertainty.md`: the 1 ms value was a Pi default,
not a universal WSPR protocol requirement. The corrected conservative USB
estimate remains honest; do not alter it merely to satisfy admission.

## Required product behavior

1. Use 100000000 ns (100 ms) as the ordinary WTP job uncertainty default in
   WsprryPi. Cover C++ construction, missing-field JSON/configuration parsing,
   defaults used during serialization and INI loading, newly created fleet
   profiles and discovered candidates, UI defaults, field population/reset,
   persistence and runtime/scheduler consumption. Inspect the full lifecycle.
   This policy applies consistently to USB, Plain LAN and engineering TLS.
2. Preserve every explicitly stored valid limit, including 1000000 ns and
   other stricter or custom values. A saved 1 ms value does not reveal whether
   it was deliberate or an old default. Do not silently migrate it, normalize
   profiles, alter saved configurations on read, or make an unrelated save
   increase the limit. Missing values may receive the new default.
3. Give operators clear, unit-accurate guidance for adopting the recommended
   100 ms value through the existing configuration/review/save workflow. If an
   explicit preset action is added, it must respect that surface's existing
   persistence semantics, preserve other drafts and avoid an automatic device
   switch, reconnect, transmission or background save. Explain which save or
   apply action makes the change effective. Do not add a second policy field.
4. Maintain existing per-job ARM and immediate-pre-launch uncertainty checks.
   A qualifying clock below the selected limit may admit; a clock above it
   must refuse, including deterioration after ARM. Honor explicit stricter
   limits. Do not replace the measured uncertainty with the configured limit.
5. Pico already accepts the per-job limit and advertises a 500 ms maximum.
   Keep its firmware engine and protocol unchanged unless an actual defect
   prevents correct enforcement. Add focused tests for 100 ms boundaries,
   stricter requests and pre-launch aging/refusal using its real authority.
   Distinguish initial observation uncertainty from age-grown uncertainty.

## Invariants

Keep WTP/1 and USB-Management/1 framing and versioning unchanged. Keep one
JobService, local scheduler/clock, ownership, persistence and RF authority.
Jobs are complete before ARM; no per-symbol USB delivery is introduced.

Keep job/event/payload/duration/mode/configuration/session capacities, RF memory
reserves, 64-byte foreground service budget, oscillator aging, host UTC
qualification, clock-step/leap/overflow/identity guards, one-use time samples,
ACK requirements, holdover, ARM lead/horizon, missed-start deadline, STOP,
cleanup and output-unknown reconciliation intact. Preserve standalone, Wi-Fi,
USB configuration, Wi-Fi CRUD, canonical hostname and bounded AP behavior.
Only the accepted ordinary-operation default changes from 1 ms to 100 ms;
existing explicit limits and every other timing limit remain authoritative.

## UI requirements

Use the required Impeccable skill and existing PRODUCT.md, DESIGN.md, tokens,
fonts, spacing and Bootstrap patterns. Keep the current interface structure.
Cover both the active endpoint form and fleet profile editor. Explain the
100000000 ns / 100 ms conversion and saved-setting preservation. Keep custom
values editable, disabled/busy states correct, keyboard operation and feedback
accessible, and drafts intact across visibility, refresh, reload and failure.
Render the changed workflow at desktop/mobile widths in light/dark themes.
Inspect in one batched round, fix findings together, then use at most one
confirmation round. Run the skill's mechanical detector once at completion.

Execution clarification after the first UI assessment: the active endpoint
uses Setup's existing autosave, so guidance must say to enter the new value
and review save status. Do not invent a separate host Save action. A fleet
preset remains draft-only until Save device, followed by Use this device for
active-endpoint adoption.

## Validation and harness

Use the repositories' documented commands and inspect targets first. Do not
compile or link WsprryPi C++ natively on macOS; use an identified retained Linux
container/host with its existing dependencies. Do not install tools or download
SDKs incidentally. Separate compiler, Node, browser, firmware and hardware
evidence, and report prerequisite limitations accurately.

Test default construction and missing-field parsing, explicit-value preservation
through parsing/serialization/INI and catalog save/reload, unrelated updates,
and actual runtime requests. Cover USB and network profiles. Exercise UI fresh
defaults, stored 1 ms/custom values, deliberate adoption of 100 ms, save/apply
semantics and absence of unintended requests. Include meaningful end-to-end
product tests; avoid tests that merely search for new constants.

Verify actual job admission below/at/above 100 ms, explicit 1 ms refusal where
appropriate, and uncertainty deterioration between ARM and launch. Exercise
the existing real Pi/Pico USB application/time pair without network, plus
existing standalone/network regression checks affected by the change. Run
sanitizers where useful. Existing protocol fixtures and historical network
pins retain their distinct evidence; change only a dedicated current pin when
new companion source is actually required by its executable test.

A finite physical USB-only acceptance on the already identified Pico B may
use the normal RF-inhibited image and the retained backup/restore workflow.
Verify serial/device/image/engine and disabled scheduling before operations.
Use qualified host UTC, no saved Pico station network and no SNTP dependence.
Never ARM a physical RF-capable image. If testing ARM on physical hardware,
first establish the inhibited engine from actual CAPS and refuse otherwise.
Use complete finite jobs, bounded deadlines and explicit ABORT/RELEASE or
terminal cleanup. Back up and verify full flash/settings, preserve watermarks,
and restore and verify the exact original flash in an unconditional finally
path. Keep private backups/credentials/captures out of Git. Record exact source,
client/image hashes, clock/error, operation outcomes and restoration. This
qualifies USB/inhibited job admission only, not transmitter RF or absolute
electrical timing. If hardware cannot be exercised safely, finish deterministic
validation and name the remaining physical gate without claiming acceptance.

## Documentation

Save this complete prompt before implementation. Update each repository's
current USB/configuration documentation and a durable result/review record.
Promote the accepted 100 ms policy from proposal to implemented default only
after it is implemented and tested. Preserve the original 1 ms investigation
and physical measurements as dated evidence; explain the subsequent policy
change. State that explicit old values remain and describe deliberate adoption.
Review the separate operator documentation read-only and record precise
follow-up needs; writing there is outside this two-repository scope.

## Adversarial assessment and publication

After implementation and validation, assess the complete change adversarially:
look for hidden 1 ms fallbacks, drift between backend/UI/catalog defaults,
silent migration or autosave, lost custom values, unit/precision errors, a
policy applied only in tests, boundary/aging bypasses, weaker clock or RF
guards, unsafe hardware harnesses and overstated qualification. Record findings
with evidence and disposition. Repair actionable issues, rerun affected checks,
and run another fresh assessment. Repeat until no actionable findings remain.
Do not label a self-review independent; use available authorized review
capabilities honestly and record its scope.

Inspect the final diff and staged content, run whitespace checks and retain
only relevant sources, tests, documentation and sanitized evidence. Commit and
push separately in the two repositories on `devel`; preserve concurrent user
work. Independently verify remote branch hashes. Report the saved prompt,
implemented behavior, validation, visual/review evidence, physical limitations,
documentation impact, commits, push/CI status and actual working-tree state.
