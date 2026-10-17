# P15.19 Impeccable web UI review execution prompt

Prepared 2026-10-17. **Saved for future execution; P15.19 is Not started.**
Writing, linking or reviewing this prompt does not execute it. Do not run the
review, change UI/product/design files, launch browsers or services, operate
hardware, stage, commit or push merely because this document was saved.

## Objective and execution boundary

Execute **P15.19 — Impeccable review of the web UI, including provisioning**
in `/Users/lbussy/GitHub/WsprryPico`, after accepted P15.18 Installer. Review
the delivered interface, repair actionable issues within this scope, validate
the actual user flows and leave a durable acceptance record for P15.20 user
documentation. Start from the UI that exists at execution. Preserve its useful
identity and behavior while making it familiar to WsprryPi operators.

When explicitly invoked for execution, this prompt authorizes Pico-only UI
review, bounded repairs, affected source/bundle/test/documentation changes,
local hardware-free fixture/browser runs, and separate read-only subagents
for Impeccable's independent assessments and final reassessment. It does not
authorize executing another phase, deploying/flashing, RF jobs, Pi service or
repository changes, release publication, or Git staging/commit/push. Obtain
separate instructions for those actions if requested later. Preserve existing
work and any current hardware/setup limits. P15.20 remains Not started.

## 1. Refresh prerequisites, instructions and the real baseline

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/development/README.md`, the current [Consolidated backlog](consolidated-backlog.md),
the [acceptance record](../implementation-plan.md#phase-15-acceptance-record)
and actual P15.14–P15.18 acceptance records, including the final firmware/Pi
pair, GPIO drive setting, uninhibited/inhibited target mapping, testing release
and delivered installer paths. Saved execution prompts are not acceptance.
If a prerequisite is incomplete, identify it and stop before executing P15.19;
do not implement the missing phase here.

Inspect full HEAD/branch/upstream, current remote `devel`, staged/unstaged/
untracked work, source-owned UI, generated bundles and applicable instructions.
Begin from the current accepted `devel` state; use an isolated checkout when
necessary to preserve concurrent work. Never reset, stash, clean, overwrite
existing evidence or silently absorb unrelated changes. Record exact source,
asset and fixture identities before edits. Mark P15.19 In progress only when
its execution actually starts.

The preparation checkout was `e8b5fb53691526c9cd5370fb334843fd6124220b` on
Pico `devel`; the interface already had an incumbent design and engineering
`src/network/web/DESIGN.md`, but no discovered Pico `PRODUCT.md`. These are
preparation observations, not the future accepted source or a fresh UI audit.

## 2. Use the existing-interface Impeccable flow

Read the installed Impeccable `SKILL.md` and recheck the operator-specified
[Designing with Impeccable guidance](https://impeccable.style/designing/).
Use its **Improve an existing interface → Check before release** route:
critique and technical audit, then evidence-driven refinement and verification.
This is an **Operate** surface. The supplied task and incumbent UI settle the
starting direction; this is not a new visual world or a rebrand.

Run the installed skill's context helper once for the resolved source target;
follow its actual returned documentation and paths. Cover both
`src/network/web/` and `src/network/bootstrap_web/`, not only the engineering
page. Read the applicable critique/audit references and Operate guidance.
Read the relevant refine command and craft floor before any actual UI edit.
Use clarify, harden, adapt, layout, optimize or polish only where a finding
requires them; do not ritualistically run every command.

Use the supplied startup answers below and current source as context. Missing
PRODUCT.md does not erase the incumbent visual authority or automatically turn
an existing-interface review into greenfield init/shape/new-work. Record the
resolved facts in the P15.19 record. Reuse an existing Pico product record if
one is present at execution. Do not create a competing product authority,
copy Pi's product record wholesale, or repair skill/sidecar drift incidentally.
If genuinely new product facts or a binding design decision are missing, ask
only about that delta. If creating PRODUCT.md becomes necessary, follow the
installed init flow, including its required confirmation round, with the
answers already filled in; do not ask the user to repeat settled facts.

Do not launch a mockup/concept tournament, generate a replacement brand, ask
for a new framework, or persist a new build-path default for this review.
WsprryPi's recorded `buildPath: code` is reference context, not permission to
change Pico's permanent skill settings. Preserve intentional design choices;
propose any substantial redesign separately.

## 3. Startup answers: reuse Pi context with explicit Pico adaptations

Read these WsprryPi files **without editing that repository**:

- `/Users/lbussy/GitHub/WsprryPi/WsprryPi-UI/PRODUCT.md`
- `/Users/lbussy/GitHub/WsprryPi/WsprryPi-UI/DESIGN.md`
- Representative source-owned Pi navigation, station/member settings, status,
  validation and recovery controls relevant to the comparison.

Record the inspected Pi revision and distinguish source comparison from a
rendered comparison. The reusable answers are:

| Startup question | Answer for this P15.19 execution |
| --- | --- |
| Who uses it? | Technically capable amateur-radio operators, including returning WsprryPi users. Preserve precise controls and meaningful technical distinctions; make first provisioning understandable to someone new to Pico. |
| What is it? | A browser interface to the local WsprryPico transmitter application on Pico 2 W/RP2350, usable standalone and as a WsprryPi member. The browser configures and observes; RP2350 owns scheduling, authority and RF timing. |
| What must users accomplish? | Provision Wi-Fi and station identity, identify the intended Pico, configure supported transmission/hardware settings, operate and monitor admitted jobs, understand saved versus active state, and recover without losing their work. Include only capabilities delivered by the accepted baseline. |
| What does success mean? | Users recognize familiar WsprryPi concepts, find the next action and its consequences, see truthful state and validation, retain drafts on failure, and finish supported tasks on desktop or mobile without unnecessary steps. |
| What voice should it use? | Pi's precise, clean, technical, direct, pragmatic and trustworthy language. Explain necessary terms and units beside the control; avoid promotional copy, invented assurances or excessive simplification. |
| What visual character carries over? | Pi's bench-instrument character: compact but readable technical values, restrained appliance chrome, consistent controls, clear task grouping and recovery beside the problem. Existing Pico design and source determine concrete implementation. |
| What makes Pico different? | Firmware-served, fast and lightweight pages that work over its supported local/AP paths. Preserve offline/local assets, native controls, existing stack and embedded resource budgets. Pi's complete shell and dependency set are not a Pico requirement. |
| What must remain truthful? | Requested, draft, persisted, pending restart, active, last confirmed, unknown and physically qualified are distinct. A selected drive value is not measured RF power; a lost connection is not proof of inactivity or success. |
| Which platforms and themes? | Responsive web on the supported desktop/mobile browsers, with keyboard access and usable zoom. Inspect actual Pico themes; Pi's light/dark parity is a consistency principle where themes exist, not authorization to add an unimplemented Pico theme. |
| What are the evidence limits? | No invented users, performance guarantees, hardware support, certifications, RF qualification or successful installation. Browser fixtures and host tests establish their software scope only. |

These answers reuse Pi's audience, operator goals, voice and state principles;
its reception reports, support bundles, Linux maintenance, backend controls and
other Pi-only features are not automatically Pico capabilities. Retain the
WsprryPico product identity.

Build familiarity through vocabulary, action placement, grouping, control
behavior, units, restrained hierarchy and state feedback. Start from Pico's
current navy/slate header, neutral surfaces, compact forms and system-font
implementation where still current. Do not import Bootstrap, jQuery, Pi fonts,
a large icon library, remote assets or a new framework merely to resemble Pi.
Reuse actual code/assets only after checking provenance, license and cost.

## 4. Inventory every delivered page, profile and entry path

Trace actual route/profile dispatch and embedded assets before reviewing.
Relevant preparation sources include `src/network/assets.hpp`,
`src/network/bootstrap_http.cpp`, `src/network/web/`,
`src/network/bootstrap_web/` and its README/build scripts. Determine which
markup/scripts are actually served in each accepted firmware profile.

Create a finite coverage matrix with source, route/alias, profile/authority,
initial state, task, desktop/mobile evidence, result and limitation for:

- Blank and network-only provisioning: Wi-Fi-first setup, password visibility,
  network trial/save/reconnect and optional station commissioning.
- Consumer operation over admitted AP and station LAN/hostname paths:
  Station/Transmission, Wi-Fi/Host, login, session retirement/recovery,
  independent valid-field saves, profiles, pending restart and diagnostics.
- Engineering pages and their supported authentication/capability states.
- Recovery/provisioning variants and transitions, including `owner.html` and
  `recovery.html` where actually admitted. Legacy file names do not establish
  persistent phone ownership or equivalent authority between profiles.
- Delivered P15.15 drive controls and any applicable P15.18 installer/status
  presentation. Inventory actual ownership: a Pi-hosted installer screen is
  reference/read-only context, not an excuse to add it to Pico or edit Pi.

Preparation aliases included `/`, `/index.html`, `/station`, `/wifi-host`,
`/radio` and `/owner.html`; resolve their current profile-specific behavior.
Do not count hidden HTML as a working route or assume an old fixture models
the current production composition. Include provisioning explicitly in both
the design assessment and technical/browser evidence.

## 5. Freeze representative states and resource baselines

Use deterministic hardware-free fixtures serving the real maintained assets
and real client request paths. Reuse current production browser/integration
harnesses; keep fixture-only code outside firmware. Use synthetic credentials,
station identity and device IDs. Do not expose real passwords, bonds, trust
material, browser profiles or private captures in reports/screenshots.

Cover the initial, loading, empty, edited, validating, saving, confirmed,
pending-restart, unsupported, busy/owned, unauthenticated/session-expired,
conflict, failed-save, lost-reply, disconnected and reconnect states where
applicable. Include long hostnames/IDs, invalid and partial fields, untouched
versus edited prefill, target/boot changes, navigation/reload and mobile keyboard
behavior. Test recovery through authoritative readback rather than auto-replay.

For provisioning, exercise Wi-Fi-first ordering, clear optional station setup,
password privacy/toggle labels, failed association, saved-result uncertainty,
retry guidance, loss of AP after a successful save, and the transition to the
configured hostname without falsely promising reachability. Clarify AP expiry
and recovery while preserving the fixed ten-minute cap; do not extend it as a
generic accessibility fix or add an unrelated owner/confirmation gate.

Record baseline raw/minified/actually transferred asset sizes, request count,
external requests, relevant first-usable interaction observations and linked
firmware/resource figures. Name the browser, fixture and conditions; do not
invent a latency budget or present a localhost timing as Pico performance.
Keep shared scripts lean and local; polling, crypto and bounded service work
must not grow casually. Measure and justify any increase against accepted
flash, RAM, stack, response and timing budgets; never relax guards to fit UI.

## 6. Run independent critique and technical audit

Follow the installed critique workflow, including its two independent
assessments. This execution prompt explicitly authorizes those read-only
subagents; no duplicate delegation permission question is needed when invoked.
Give both the same resolved target/context and isolated fixture/browser tabs:

- **A — design review:** task flow, hierarchy, Pi familiarity, cognitive load,
  terminology, error prevention/recovery and all applicable Nielsen heuristics.
  Review provisioning and normal operation before seeing detector findings.
- **B — detector/browser evidence:** the skill's maintained detector over the
  actual markup/source directories, rendered desktop/mobile inspection and
  technical audit of accessibility, responsive behavior, performance, existing
  theming and implementation integrity. Record false positives and omissions.

Keep their findings isolated until A finishes; hold B's report if needed.
Do not anchor A with an earlier critique score or B's detector output.
Respect the skill's ignore-list, snapshot and reporting rules. If a required
agent/tool is unavailable, use only its documented fallback and declare the
method/degradation honestly; do not invent independence, overlays or scores.

Use fresh browser tabs and supported browser tools. Local fixture servers must
have recorded URLs/PIDs/stop methods and cleanup. Do not weaken firmware CSP
or authentication to enable a visual overlay. A blocked injection is a reported
tool limitation; it is not permission to bypass browser restrictions. Reuse
valid detector output instead of rescanning to chase a score.

Present and save a synthesized critique plus technical findings, with exact
surface/state, severity, evidence, user impact and proposed repair. Preserve
strengths and distinguish bugs, intentional constraints, false positives and
optional redesign ideas. Score applicable criteria honestly; do not label an
unimplemented optional theme a defect or claim formal accessibility certification.
Follow critique's closing-question rule. Ask only if a material choice remains;
otherwise use its documented `Questions skipped: <reason>` closure explaining
that this brief already supplies the direction and authorizes bounded repairs.

## 7. Repair the findings within the existing design

The executed task includes actionable, in-scope repairs. Prioritize blocked
flows, data loss, false success/state, inaccessible controls and unclear recovery;
then consistency, hierarchy, responsive layout and polish. Read the relevant
refine guidance before editing. Preserve exact units, valid advanced inputs,
WSPR message distinctions, draft retention and explicit save/apply/restart rules.

Keep one shared application authority. Do not alter protocol/storage formats,
RF clock/band qualification, job capacity, UTC acceptance, AP lifetime, ownership,
STOP/fault behavior or security admission as a presentation shortcut. A server-
side defect that prevents a UI acceptance row needs a clearly bounded repair
and affected contract tests; a broader feature or policy change is a blocker
or separate proposal, not hidden inside a visual cleanup.

Edit maintained HTML/CSS/JavaScript and applicable shared helpers. Regenerate
bundles through the existing build. Do not patch generated/minified output as
the sole source, replace maintained files with an installed web root, move all
controls into one generic form, or introduce a parallel settings store. Keep
shared vocabulary coherent without merging distinct commissioning/auth roles.

Use one batched initial visual inspection across desktop/mobile and the
coverage matrix, one repair batch, and at most one visual confirmation round.
This ceiling covers the entire visual cycle, including critique, audit and
polish; it does not restart per page or command. Functional regressions and
correctness repairs still require affected retests. Do not continue open-ended
cosmetic loops; record a material unresolved issue instead of claiming closure.

## 8. Validate actual flows, bundles and firmware resources

Inspect current commands and test registration before running them. At
preparation, maintained entry points included:

```sh
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
bash scripts/check_host.sh
python3 scripts/validate_wtp_contract.py
```

The host preset configure/build/CTest path is the maintained alternative to
the platform helper. Refresh affected browser tests, including organization,
hostname, saved-progress, session/recovery, bootstrap/commissioning and network
UI coverage. Execute the supported real-browser harness against current assets;
passing DOM stubs or a static screenshot alone does not exercise save/recovery.
Use current pinned dependencies; do not install an SDK or update npm packages
as incidental review work. Report missing prerequisites precisely.

For changed embedded assets, cross-build both accepted normal and explicitly
inhibited variants using the P15.16 recipe. Retain linked-image, renderer,
flash/UF2, stack/heap/pool, response-size and numeric-capacity checks, and compare
with the immediate baseline. Verify generated bundles, route composition and
served assets agree with maintained sources. Re-run affected checks after fixes.

In the bounded confirmation round, verify primary tasks at representative
narrow mobile and desktop sizes, keyboard-only traversal, visible focus, labels,
error associations, status announcements, touch targets, zoom/reflow, long
content and every repaired state. Inspect the screenshots, not just their file
existence. Reuse initial evidence for unchanged rows; mark unexercised browsers
and physical captive-portal/USB/device behavior explicitly.

No RF transmissions, dual-board campaign or firmware flash is required by this
UI task. Browser/host evidence does not qualify those behaviors. If the operator
later authorizes a specific physical check, define its finite setup and restore
it separately; do not infer that authority from historical tests or these files.

## 9. Record the final design, review and P15.20 handoff

Create `docs/development/phase15-19-results.md` with exact Pico/Pi reference
identities, startup answers and their sources, route/profile/state coverage,
critique method/scores, detector/audit findings, repairs, commands/results,
asset/resource comparisons, browser/screenshot evidence, cleanup and remaining
limitations. Store local screenshots/logs in an identified ignored location;
keep the durable evidence inventory and relevant hashes in the result record.

Update the applicable DESIGN.md only for intentional implemented decisions,
including provisioning-specific conventions where needed. Preserve source-
derived truth; do not turn a pre-existing defect or a planned token into an
approved system rule. Use the skill's document guidance for actual design
record changes without reopening the settled visual direction. Keep transient
skill caches, private snapshots and sidecars out of source commits.

Obtain an independent final assessment of changed source, actual flows,
acceptance evidence and documentation. Reviewers must not implement repairs
or operate devices. Fix actionable findings, rerun affected checks and reassess;
respect the visual-round ceiling and disclose any genuine incomplete row.
The implementer's self-review is not independent acceptance.

Only mark P15.19 Complete when the required surface/state coverage, actionable
repairs, applicable checks and final reassessment are complete. Otherwise record
In progress and the precise remaining work. Link the result from the checklist
and synchronize indexes. Leave P15.20 Not started and provide final terminology,
route/flow descriptions, screenshot inventory, supported device/browser limits
and provisioning/recovery instructions for that documentation task. Do not
build or publish the documentation site.

Report the complete critique/audit outcome and final repairs/evidence, including
Pi familiarity, Pico resource impact, provisioning coverage, limitations and
actual working-tree/index state. Stop at P15.19. Do not stage, commit, push,
tag or publish unless separately requested.
