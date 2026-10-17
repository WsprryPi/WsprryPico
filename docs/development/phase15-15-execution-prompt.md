# P15.15 GPIO drive-strength execution prompt

Preparation date: 2026-10-17. **Saved for future execution; not implemented or
executed by preparing this document.** The requirements below become the work
request when the operator invokes this prompt. This document describes selected
future behavior, not an implemented firmware/API contract.

Numbering warning: P15.15 now means GPIO drive strength. The previously saved
P15.15 uninhibited-build task is [P15.16](phase15-16-execution-prompt.md).
See the [complete list and prompt index](phase15-prompt-index.md) and
[preparation assessment](phase15-15-prompt-review.md).

## Objective, scope and prerequisites

Implement **P15.15 — GPIO drive-strength configuration across Pico and
WsprryPi**, after verifying accepted P15.14 USB control. Deliver exactly four
RF GPIO drive choices: **2, 4, 8 and 12 mA**, with **4 mA as the default**.
The selected value must persist, reach the actual RP2350 RF pad, and have
consistent controls/readback through USB, the shared JSON API, the Pico's
internal web pages and the WsprryPi interface for the selected Pico.

Implementation scope, when invoked, comprises:

- `/Users/lbussy/GitHub/WsprryPico`: portable configuration/storage, RF adapter,
  management services and adapters, internal UI, tests and development docs.
- `/Users/lbussy/GitHub/WsprryPi`: only the companion Pico management client,
  USB/network adapters, selected-member UI and related tests/development docs.
  `WsprryPi-UI`, `WTP-Client` and `WTP-Server` are component paths owned by the
  parent repository, not independently published repositories.

Read each repository's applicable `AGENTS.md`, component instructions and
contracts. In Pico read `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/development/README.md`, the current implementation plan,
`docs/development/configuration-updates.md`, `docs/browser-api.md`,
`docs/transmitter-application-contract.md`, `docs/development/saved-progress.md`,
`docs/development/usb-control-results.md`,
`docs/development/usb-local-configuration.md` and
`docs/protocol/USB-Management.md`.

Refresh the actual branch, full HEAD/upstream identities, staged/unstaged work,
accepted P15.14 source pair and evidence. The preparation checkout was Pico
`devel` at `100e749c815f7485d5097c9086852d3b97adca9f`; concurrent USB acceptance
documentation was changing. This snapshot is not the execution baseline.
Do not begin implementation until P15.14's required acceptance is confirmed.
Preserve all existing work and evidence; never reset, stash or absorb unrelated
changes. Read-only inspection of another family repository grants no write scope.

This task does not change the default firmware target (P15.16), publish a
prerelease (P15.17), implement the installer (P15.18), perform the final web UI
review (P15.19) or build/publish the user documentation site (P15.20).
It does not authorize staging, committing, pushing,
tagging, creating a PR or publishing. Obtain those instructions separately if
requested at execution time. Hardware authority comes from current operator
setup statements and repository instructions, not this saved prompt or old
captures. Continue all independent software work if physical evidence is absent.

## 1. Establish one setting and its meaning

Use one portable, validated setting named `gpio_drive_ma`, with integer values
`2`, `4`, `8`, `12` and default `4`. Scope it to the selected member's **direct
RF output GPIO**. The value follows the member's selected RF pin and applies
equally to standalone and controller-submitted Tone/WSPR/QRSS/FSKCW/DFCW jobs.
It is a member hardware setting, not a per-job WTP parameter.

Do not apply it to button, indicator, amplifier-enable, LPF-selector, I2C,
USB, Wi-Fi or other auxiliary pins. Do not convert Pi BCM power-level indices,
Pi RP1 drive values or Si5351 current selections into Pico values. Preserve all
existing Pi local-backend controls and defaults. A future Si5351 engine must
have its own capability and setting; this task does not implement it.

Label the control **GPIO drive strength**, with `2 mA`, `4 mA (default)`,
`8 mA`, `12 mA` options and concise help: electrical RF-pin drive; actual RF
power depends on load and frequency. Keep `station.power_dbm` and the WSPR
reported-power editor unchanged. No measured-power claims or automatic WSPR
power adjustment follow from this selection.

Initial/legacy stored configurations lacking the new field resolve to 4 mA.
An absent field in a partial or legacy unrelated save preserves an existing
selection. An explicit selection of 4 mA resets drive to the default. Do not
infer reset intent from client age or missing fields.

## 2. Freeze compatible configuration and API contracts before coding

Trace every representation from default and parser through validation,
serialization, journals, profile conversion, saved progress, management read/
write, browser population, Pi forwarding, restart and RF consumption.
Start with these source families, then follow their current callers:

- `src/standalone/config.*`, `storage.*`, `scheduler.*`, `progress.*` and
  `src/standalone/pico/main.cpp` / `flash_layout.hpp`.
- `src/application/resources.*`, `config_update.*`, `src/network/api.*`,
  management/consumer adapters, and `src/usb/management_endpoint.*`.
- `src/rf/pico/pico_pio_dma.*`, `worker.*`, the pin plan and its validation.
- `src/network/web/` and the source-owned consumer/bootstrap assets under
  `src/network/bootstrap_web/`; identify actually served sources and aliases.
- Pi `src/wtp_integration/configuration.*`, `usb_management.*`,
  `network_http.*`, `consumer_radio.*`, `WTP-Client/` and
  `WsprryPi-UI/data/wtp*.js`, plus their application/resource validators.
- Checked-in schemas/vectors, compatibility fixtures, existing USB and UI
  tests, firmware-profile checks and linked-image/resource checks.

Record a compact contract table before implementation: canonical field and
units, internal owner, each route/method/schema/capability, legacy view,
omission/reset behavior, saved/active readback, revision and activation rules.
Exact wire/schema/resource versions are implementation choices to resolve from
the accepted baseline; do not label a proposed extension already implemented.

Existing hardware/application/capability responses and Pi validators contain
closed objects. **Do not add keys to an existing closed version or simply
relax all unknown-field validation.** Add explicitly advertised, independently
versioned views/operations where needed. Keep previous views valid for old
clients, with unchanged semantics. New clients negotiate support for this
exact field, legal values, default, engine, read/write paths and activation
policy; firmware version strings or WTP CAPS alone are insufficient.
Keep legacy `unavailable:["drive", ...]` declarations truthful for the legacy
view that cannot configure drive; advertise availability only in the negotiated
extension. Updating a top-level flag must not make an old Pi validator reject
the entire application or cause it to send the wrong write shape. USB and
network route/resource allowlists must admit the new negotiated versions.

Provide coherent drive support in config reads/updates, hardware and application
resources, capabilities, saved-progress/apply and relevant diagnostics, using
those negotiated contracts. Include the drive value in applicable equality,
revision/digest, pending-application and restart calculations: a drive-only
change must not vanish because the pin plan is unchanged. Define readback for
an unconfigured member and inhibited engine truthfully; a default or retained
value does not prove pad programming or RF readiness.

Validate exact integers; reject zero, negatives, 3/6/16 and other unsupported
values, strings, booleans, null, fractions and noncanonical numeric tokens
under the chosen parser contract. Reject duplicate/unknown keys and unsupported
schemas. Never round, clamp, accept an enum ordinal as mA or silently fall back
on malformed supplied data.

Preserve the P15.1/P15.9 rules:

- Merge and ordinary legacy updates preserve omitted drive and other fields.
  Existing full PUT clients cannot erase the selected drive inadvertently.
- Explicit complete replacement, initial creation, Console `CONFIG` and reset
  retain their documented replacement semantics: omission defaults to 4 mA
  only where deliberate replacement/creation is already the contract. State
  and test those differences; a Console read must show the effective value.
- Include this independently valid hardware field in the supported saved-
  progress flow, without requiring valid station identity or transmit-ready
  schedules merely to save its draft. Version closed progress contracts as
  necessary. Saving progress does not program the pad or apply configuration;
  explicit application still uses the common authority.
- Unrelated station/network/profile/hostname/pin/schedule/progress operations
  preserve the drive selection. A deliberate full reset returns it to 4 mA;
  a Wi-Fi-only reset preserves it. Reapplying older drafts must not overwrite
  a newer drive selection unless that field is explicitly being applied.
  In particular, an older client's progress `apply all` payload that has no
  drive field must preserve the saved drive, not reset it to 4 mA. An unsupported
  drive mutation must reject atomically without partially saving sibling fields.
- Keep redaction, auth/CSRF/session authority, device and boot identity,
  If-Match/ETag, one validated candidate and one verified journal commit.

Keep flash addresses, journal integrity/recovery, STOP/fault state, consumed
transmission slots/watermarks, profiles, bonds and E10 reservations intact.
Select the smallest compatible persistence extension. Read old valid records;
do not use malformed new data as a reason to erase settings or revive an older
enabled record. Document downgrade behavior if old firmware cannot decode the
new representation. Preserve unchanged legacy serialized fixtures where the
contract requires them; do not manufacture compatibility by rewriting fixtures.

## 3. Apply drive through existing hardware activation

Use the existing **explicit restart** hardware activation model. Saving a
different drive is allowed only through current idle, unowned, inactive,
nonfaulted configuration admission; loaded, armed, running, cleanup-uncertain
and other excluded states stay excluded. A drive save must not hot-change the
pad, abort/claim a job or enable transmission. Scheduler admissions remain
inhibited while changed hardware is awaiting restart under the existing policy.

Expose saved drive, boot-active drive, pending restart and any application
error distinctly. An unchanged save follows existing generation semantics.
Boot-active here means the validated selection used by this boot. Report actual
pad readback separately, and as unavailable until a real RF adapter has applied
and verified it; do not equate a boot snapshot with an electrical observation.
Define A-to-B-to-A behavior against the boot-active hardware snapshot and retain
existing sticky restart/output-inhibit rules. Unrelated saves cannot clear the
pending-drive or pre-existing pin/network/STOP/fault latch. A lost reply means
outcome unknown; reconcile authoritative identity/revision/saved/active state
before a fresh explicit action. Do not retry or restart automatically.

At boot, take an immutable validated drive/pin snapshot and pass it from the
portable application into the RP2350 adapter. Map mA to the named SDK constants
explicitly, including an explicit 4 mA initialization; do not depend on reset
defaults or cast mA to `gpio_drive_strength` enum ordinals. Set the selected pad
before enabling PIO/state-machine/DMA RF output, preserving output inhibition
through GPIO function changes and error paths. Validate/read back programming
where the SDK permits, and fail closed on mismatch/application failure with
truthful status. Do not clear an existing output-disable failure.

Audit reopen/rearm/abort/error-cleanup and RF-pin changes so subsequent jobs use
the boot-active selection and cleanup does not resurrect output or alter other
pads. The inhibited image exposes consistent saved settings without energizing
RF or claiming active physical drive where none was applied. Keep portable
logic free of SDK register types; do not change waveform generation, clock,
slew rate, mode/band policy, timing, resource limits or WTP/1 job messages.

Hardware references: the [SDK GPIO API](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html#gpio_set_drive_strength)
defines the four nominal strengths. Verify the repository-pinned SDK's RP2350
`pads_bank0.h`, GPIO and PIO initialization code; use `gpio_set_drive_strength`
and the corresponding getter rather than assuming Pi register behavior.

## 4. Deliver every supported control path

| Surface | Required result |
| --- | --- |
| USB management | Discover, read, save, inspect saved/active/pending state and explicitly restart/apply with Pico Wi-Fi disconnected. Use existing UMP framing, request/response bounds, local physical authority, revision and delivery acknowledgement rules. |
| USB Console | Existing configuration inspection/export and explicit `CONFIG` import represent the field and its default/validation. Reuse the existing grammar and authority; no separate unversioned drive command. |
| Shared JSON API | Negotiated capability and coherent versioned config/update, application/hardware and saved-progress views/operations use the same validator, commit and activation path on every supported management carrier. |
| Pico internal pages | Every currently served consumer and engineering Station/Transmission editor, AP/LAN/hostname entry and supported alias has the applicable drive control/readback. Bootstrapping pages without hardware management preserve drive and do not gain an unrelated radio form. |
| Pi over USB | Selected-Pico settings use the same supported value and target identity with no Pico network requirement. Expose and forward the new resources; a Pi-local setting is not a substitute. |
| Pi over network | Supported authenticated Consumer-Radio and engineering paths carry equivalent negotiated behavior. Plain WTP job transport does not acquire a new JSON configuration authority. |

No parallel settings store, extra listener, bypass authentication, new protocol
repository or transport-specific RF behavior. Test USB response framing and
budgets with the new largest responses, not just direct handler calls. Preserve
P15.14 USB time, WTP and AP lifetime behavior.

## 5. Keep Pico and Pi UI behavior consistent

Use the Impeccable skill required by the Pi repository and inspect each UI's
own incumbent design (`src/network/web/DESIGN.md` and Pi's
`WsprryPi-UI/PRODUCT.md` / `DESIGN.md`). This is a narrow Operate-mode extension;
preserve each application's layout, typography, controls and navigation.

Use a labelled native select beside the member's RF pin/hardware settings in
Station/Transmission. Include exactly the four choices and default label from
section 1. Clearly identify the selected Pico and mA units. Separate it from
reported WSPR power and Pi-local BCM/RP1 controls; do not move or repurpose those
controls. Use existing Save and explicit Restart flows.

Represent unavailable/older firmware, disconnected/unknown readback, loading,
unchanged, edited draft, saving, confirmed saved, pending restart, active and
validation/conflict/failure states. Default 4 mA only for confirmed initial or
legacy data under the negotiated contract; never display 4 mA as observed on an
unsupported or unreachable device. Preserve drafts on error, session loss and
unrelated refresh. On target/boot change, invalidate old capability/readback
and bind drafts to their original member so they cannot be submitted to another
Pico. Never silently coerce an unexpected returned value into the default.

The browser cannot enable a save blocked by server authority. Keep feedback
beside the control/save action, keyboard operation, accessible label/help/error
associations, visible focus and mobile layout. Selecting or previewing a value
must not write, restart, transmit or adjust reported WSPR power.

At execution, render the actual affected Pico consumer/engineering and Pi
USB/network editors at desktop and mobile sizes with realistic connected,
pending-restart, failure and unsupported-member fixtures. Inspect the existing
screen behavior and actual event/request path. Use Impeccable's bounded visual
passes; functional/adversarial repairs still require affected retests. Record
visual evidence separately from device evidence. Generated browser bundles must
be regenerated through their maintained build, not edited as the sole source.

## 6. Validate behavior, compatibility and resource limits

Use actual documented commands and inspected test targets from the accepted
baseline. Pico entry points currently include `bash scripts/check_host.sh`
(macOS), `cmake --preset host-debug`, build/CTest for that preset and
`python3 scripts/validate_wtp_contract.py`. Cross-build both ordinary inhibited
and StandaloneRF applications using pinned dependencies and maintained helpers
in task-specific build directories, retaining all linked-image checks. Refresh
the exact command/profile at execution; do not download an SDK or install tools
as incidental work, change dependency pins or overwrite existing evidence.

Pi has existing `wtp-config-test`, `wtp-config-interop-test` and
`wtp-production-test` targets under `src/Makefile`, plus USB management and UI
tests. Inspect prerequisites, choose affected targets and run C++ builds/tests on
an identified Linux host or Linux CI. Do not try local macOS Pi C++ compilation
unless the operator explicitly requests it or confirms the toolchain repaired.
Safe local JavaScript/schema checks may run independently. Do not substitute
a portable subset for required full integration coverage without reporting it.

Required test matrix:

1. **Defaults and validation:** old absent-field records, factory/initial setup,
   all four round trips, explicit default/reset, invalid type/value/duplicate/
   unknown cases, redaction and exact request/config/response size boundaries.
2. **Preservation and persistence:** every ordinary/merge/replace/Console path,
   nondefault drive plus unrelated station/Wi-Fi/hostname/pins/schedules/profile
   changes, draft save/apply, wrong revision/target/boot, concurrent writers,
   journal failure/torn write, reboot recovery and explicit reset semantics.
3. **Lifecycle and pad selection:** verify the SDK value/call targets the selected
   RF GPIO before output enable for all four choices, plus 4 mA missing-field
   initialization, drive-only restart latch, boot snapshot, A-to-B-to-A, busy
   exclusions, application/readback failure and output-disable failure. Check
   rearm/abort/cleanup and changed RF pins; no auxiliary pin is reprogrammed.
4. **Carrier parity:** actual USB management framing with Wi-Fi absent, Console
   configuration, authenticated consumer/engineering API and Pico web flows,
   and Pi forwarding/UI over USB and network. Exercise save/read/restart/
   reconnect with matching identities, plus lost reply, revision conflict,
   session loss and device-switch cases. Software fixtures alone cannot prove
   physical restart/re-enumeration.
5. **Exact-pair compatibility:** immutable pre-change Pi + new Pico, new Pi +
   each retained supported old Pico, and new Pi + new Pico. Preserve previous
   schemas, Type 1/2/3, P15.1/P15.2 preservation, P15.9 progress and P15.14 USB
   behavior. Old clients may lack the control but their unrelated saves must
   preserve all four selected values on a new Pico. New clients on old firmware
   must retain other usable settings and show drive unavailable without sending
   unsupported writes. Record full revisions/profiles, actual commands/results,
   and distinguish read-only legacy fixtures from updated companion fixtures.
6. **Build/resource regression:** normal inhibited and RF images retain accepted
   numeric job limits, stack/heap/renderer/flash checks, AP/USB concurrency and
   timing admission. Compare final sizes/reserves with the immediate baseline;
   do not shrink capacity or weaken assertions to fit the new UI/schema.

Test behavior and concrete failure paths; source-string searches and mocks of
the SDK call are not sufficient acceptance by themselves. Run existing affected
host/schema/vector, storage/scheduler, configuration/resource, transport and
UI tests. Add focused regressions where missing. Re-run affected checks after
repairs and bind the final results to the final source pair.

## 7. Bound physical evidence and keep qualification honest

No hardware operation is authorized by prompt preparation. At execution, use
current setup statements and `AGENTS.md`; a named Pico connected to the SDR
authorizes the finite tests and routine loads/control/restoration in that scope
without repeated per-job permission questions. Historical campaigns are not a
current setup statement. Pi service/install/local-GPIO actions retain the Pi
repository's own authorization boundary.

With an authorized setup, freeze a finite test matrix and budget before RF:
exact board and stable identity, candidate/previous image hashes, engine,
normal clock, RF GPIO, all four mA selections, frequencies/modes/durations,
load/filter/attenuation/cabling, receiver settings, output stop and restoration.
Read back the actual pad register/SDK getter where available; inspect saved vs
active before/after explicit restart. Include one nondefault persistence test,
4 mA behavior against baseline and a bounded comparison of loaded output and
spectral behavior for the other strengths on the same chain. Do not redesign
or sweep all bands, clocks and modes as an incidental feature test.

Preserve settings, STOP state, schedules, watermarks, image and RF-path identity;
restore and verify the original setup and inactive output even after failure.
Report deviations, failed/uncertain cleanup and exact untested claims. Separate
configured nominal current, actual programmed pad and measured RF amplitude/
spectra. Higher mA is not a guaranteed power ratio or a qualification of every
band. Existing qualified results retain their original drive/source conditions;
new nondefault strengths are not automatically RF-qualified. Hardware-free
completion is scoped software acceptance and must list remaining physical
acceptance, without claiming the complete pad/RF workflow measured.

## 8. Documentation, adversarial review and finish

Update the implemented configuration/USB/API/schema/vector/development docs in
Pico and companion Pi docs; retain historical captures and qualification scope.
Add operator-facing drive, default, save/restart and compatibility text to the
P15.20 documentation handoff; the separate documentation repository and site
remain outside this execution slice. Record a **Documentation Impact** section
as required by Pi instructions.

Create a focused P15.15 execution record with exact baseline/final revisions,
schema decisions, persistence/downgrade behavior, all surface coverage, tests,
resource evidence, visual checks, physical evidence/limits and restoration.
Update checklist status according to achieved acceptance, never merely because
the field exists or the implementation builds.

Perform an adversarial assessment of the complete Pico/Pi diff, tests, docs,
compatibility views and validation claims. An independent reviewer is preferable
when authorized and available; this prompt does not itself grant permission to
spawn agents. Identify the reviewer/method honestly. Explicitly attack:

- Default mismatch or false 4 mA readback; wrong GPIO, enum mapping or apply order.
- Legacy-client overwrite, profile/draft loss, broken closed schemas or silently
  changed old resources; capability inferred from a version or wrong member.
- Bypassed ownership/revision/auth, mid-job pad mutation, restart-latch clearing,
  stale target/draft submission, ambiguous-write replay and startup RF glitches.
- Missing USB/no-network, Console, consumer/engineering or Pi UI/forwarding paths.
- UI-only persistence, mock-only electrical claims, reduced resource margins,
  inherited RF qualification and accidental later-phase execution/publication.

Record every actionable finding, repair the implementation/specification/test
gap, rerun affected checks and reassess the final result. Repeat until no
actionable in-scope findings remain. Do not call a self-review independent.
If a required check or independent review explicitly requested at execution is
unavailable, record that limitation instead of claiming it passed.

Finish by reporting changed files/repositories, actual contracts and behavior,
checks and visual workflows, review findings/fixes/reassessment, remaining
physical/compatibility limitations, documentation handoff and real staged/
unstaged/untracked state. No commit or push is authorized by this prompt.
Do not mark broad P15.15 acceptance complete while required matrix rows or
actionable findings are unresolved. If only software acceptance is achieved,
record that narrower disposition and leave physical acceptance explicit for
operator disposition; do not turn an unavailable bench into a claimed pass.
Stop at P15.15; P15.16 remains a separate invocation.
