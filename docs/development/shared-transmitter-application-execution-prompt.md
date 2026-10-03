# Shared transmitter application execution prompt

## Objective

Implement the Pico member configuration/API foundation of the selected shared
transmitter application and fleet contract. A member remains a complete local
application, with one JobService, local RF timing, persistent station defaults,
autonomous schedules and explicit hardware capabilities. Preserve WTP/1 and
existing configuration and transport meanings.

This task is authorized to create its isolated worktree/branch, carry the
existing contract and related documentation, implement and test this foundation,
perform adversarial review and repairs, and commit and push the feature branch.
It does not authorize changes in WsprryPi, Phase 12's shared working tree,
flashing, device control or RF output. Pi compatibility, recurrence ownership
transfer, amplifier/LPF adapters, Si5351 and physical acceptance remain separate
implementation gates; do not advertise them as supported.

## Working tree and dependency management

1. Work only in the attached `shared-transmitter-application` worktree on branch
   `codex/shared-transmitter-application`, based on `codex/pin-allocation` at
   `251ed992245f3b95611de767cc732f3cb1bbb34d`. Preserve the existing pin branch.
2. Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md, the shared
   application contract, pin contract and current development commands. Inspect
   branch, status, ancestry and available checks before editing.
3. Snapshot and carry `docs/transmitter-application-contract.md` and only its
   related README/CONTRACT/architecture/browser API edits from the original
   checkout. Retain the pin branch's newer documentation and supported adapters;
   do not import Phase 12 scripts, tests, fixtures or unrelated dirty changes.
   Record carryover hashes outside tracked source. Correct stale fixed-GP2 and
   documentation-only pin claims using the feature baseline.
4. Check the actual status of the chat named `Close Phase 12 acceptance` and
   committed `devel` before implementation and again before final validation.
   If that work is complete and committed, merge its committed devel baseline
   into this branch, resolve conflicts without losing either change, and rerun
   affected checks. If still active or uncommitted, record that condition and
   leave integration pending. Do not wait indefinitely, copy its dirty tree,
   message or interrupt that chat, or declare Phase 12 closed.

## Application and resource semantics

Add independently versioned application, station and hardware representations
served through the existing authenticated HTTPS BrowserApi. Keep the existing
Config v1 journal and its 1,800-byte limit; new resources are bounded projections
and updates of supported fields through the same coordinator, not new journals.
Use common configuration generations and ETag/If-Match across old and new routes.

- `GET /api/v1/application` identifies the member and exposes the station,
  member-owned recurrence, supported hardware, application status and management
  capability boundaries. Identify the device, boot and `member` scope explicitly.
- `GET/PUT /api/v1/station` exposes callsign, locator and reported WSPR power.
  Station power is encoded message content, distinct from electrical pad/synth
  drive and measured RF power. Preserve the supported Type 1 encoder constraints.
- `GET/PUT /api/v1/hardware` exposes the supported Pico pin plan, saved generation,
  active boot plan, active revision and pending hardware restart. Report actual
  adapter support; candidate eligibility is not operational support.
- Updates carry the exact resource schema and target device/boot/member scope,
  require the common If-Match token and existing authentication/Host/Origin
  policy, and reject malformed, unknown, duplicate and unsupported fields.
- Reject writes when no valid standalone configuration exists; first setup
  continues through the existing provisioning/config flow. Preserve credentials,
  schedule enablement, schedules, expiry, STOP suspension and watermarks in scoped
  writes. Hardware saves must not enable recurrence, renew ownership or clear
  fault/inhibit state.
- Require idle, unowned, inactive, nonfaulted state and serialize all writes with
  scheduler and WTP admission through the existing application owner. Pending
  network/restart transactions exclude these writes too. A loaded external job
  blocks a write. Failed validation and failed saves must not report success.
- Reuse whole-configuration validation and existing verified persistence. Hardware
  changes retain the pin feature's latched inhibition until restart; later station
  edits or restoring the old pins cannot conceal it. Expose saved and active state
  honestly, including unhealthy storage and unconfigured boots.
- Include durable journal generation in revision identity so an A-to-B-to-A save
  or repeated identical save cannot revive an old write token. Boot changes also
  invalidate stale writes. No second scheduler or ownership authority is added.

Management capability reporting must distinguish HTTPS resources from WTP job
carriers. USB WTP, BLE WTP and Plain LAN do not acquire a new JSON configuration
carrier. Keep calibration/drive, amplifier/LPF/Si5351, waveform preferences and
durable recurrence transfer explicitly unavailable in this foundation. Account
for all existing WsprryPi hardware settings in a machine-readable coverage map
with supported, platform-specific or follow-on adapter disposition.

## Schemas and compatibility evidence

Supply closed JSON schemas, positive/negative request vectors and documentation
for the new resource versions, target/revision requirements, byte budgets, errors,
station power meaning and transport policy. Separate structural conformance from
pin conflicts, encoder constraints, target mismatch, state admission and storage
failures. Validate actual emitted responses as well as request examples.

Preserve `/api/v1/config`, `/api/v1/pins`, `/api/v1/schedules`, Pi's distinct
`/api/v1/host/config`, WTP/1 and Field-GATT/1 meanings. Default legacy config
serialization remains unchanged. Nondefault pin downgrade restrictions continue
to apply. No new consumer page, unauthenticated station API, remote TLS-path
installation or silent transport fallback is part of this task.

## Validation

Use deterministic hardware-free tests. C++ builds/tests run on Linux `wspr5`
using a private source snapshot; do not retry the unavailable Mac native C++
toolchain. Use existing pinned SDK/Arm tools for cross-build checks if available,
with existing prebuilt host helpers; do not install or download dependencies.
Python/JavaScript/Git-history checks may run locally with existing dependencies.

Test legacy compatibility and scoped updates, all resource target fields,
authentication and origin rejection, missing/stale revisions, A-B-A tokens,
duplicate/unknown/type-invalid/oversized input, unsupported engines/controls,
conflicting pins, retained credentials/enable/schedules/watermark/STOP state,
loaded/armed/fault exclusions, pending network transactions, failed flash saves,
reload and saved-active/restart reporting. Check that WTP admissions remain
inhibited after hardware saves and that new routes cannot clear that latch.
Validate schema examples and real API output, resource body budgets, local
documentation links and diff whitespace. Run affected and broader host tests.
Attribute baseline failures using an unchanged baseline rather than modifying
historical acceptance records to make this feature look green.

## Adversarial review and delivery

Review the final implementation against wrong-device writes, stale/ABA tokens,
cross-route writers, ownership and stop bypasses, false active/healthy claims,
credential leakage, parser/body limits, persistence interruption and unsupported
capability claims. Record each actionable finding, repair it, rerun the affected
checks and conduct another assessment. Repeat until no actionable findings remain
within this scope. Distinguish code/schema, target and RF evidence.

Commit only this branch's requested feature files and push
`codex/shared-transmitter-application`. Verify remote branch SHA independently.
Do not merge into devel. Report the worktree, prompt, implementation, validation,
review disposition, actual branch/commit/remote state, Phase 12 integration status
and remaining cross-repository/physical gates.
