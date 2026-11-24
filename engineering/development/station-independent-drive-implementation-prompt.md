# Station-independent GPIO drive saves: implementation prompt

Implement this correction in WsprryPico on the existing
`codex/issue-478-pico-drive-current` feature branch. This is execution guidance,
not a statement that the correction is already implemented. The starting feature
includes the public finite Test Tone interface at commit
`37b90bc069a400f0b1e05b19c7933d4eeed95161`; inspect the actual checkout before
editing and preserve subsequent work.

## Outcome and scope

Allow an authenticated client to save direct GPIO drive strength before WSPR
station setup. Callsign and locator are not prerequisites for general RF hardware
settings. A client preparing QRSS or a Test Tone must be able to select an existing
drive value, explicitly restart, and verify its boot activation without inventing
a station identity or commissioning WSPR.

Fix the dependency exposed by the existing drive workflow, including its storage,
boot, authority, and readback paths. Do not undertake a general settings redesign.
The existing RF pin plan must be preserved and validated; this task does not add
a new pin-selection endpoint or broaden other settings' write authority. Test Tone
continues to use the boot-active pin and drive, its absolute carrier and finite
duration, and all native admission rules.

This task is Pico-only. Do not edit WsprryPi, HP 437B Automation, other repositories,
or installed devices. Reading companion sources for contract assessment and running
the required hardware-free paired checks is permitted; keep their build outputs
separate from maintained companion sources. Do not merge, release, increment any
version, flash, restart a physical board, transmit RF, or operate instruments.
Committing/pushing an implementation requires the executing user's authorization;
the request that created this prompt authorized publishing the prompt itself.

Do not add arbitrary job submission, scheduling, queues, per-tone drive overrides,
hot pad reprogramming, a bench-only firmware/configuration mode, Si5351 changes,
station placeholders, historical configuration/control views, migration machinery,
new journals/flash regions, or a new storage/transport/control version. Do not
redesign QRSS messages or their execution path. Preserve reported WSPR dBm as an
independent setting.

## Read and trace before editing

Read repository instructions, [README](../../README.md),
[CONTRACT](../../CONTRACT.md), [architecture](../architecture.md), and the
[development guide](README.md). Inspect the current working state, branch,
authoritative settings schema, and generated definitions. Then trace:

- [GPIO drive](gpio-drive.md), [configuration updates](configuration-updates.md),
  [saved progress](saved-progress.md), [USB local configuration](usb-local-configuration.md),
  and [finite Test Tone](../protocol/Native-Execution.md#authenticated-finite-test-tone).
- `src/network/api.cpp`: `effective_config()`, drive GET/PUT, drive-only
  `config/update`, progress drive Apply, profile overlays, station transfer,
  response revisions, and deferred effects.
- `src/standalone/config.*`, `progress.*`, `scheduler.*`, and the Config journal's
  preparation, size validation, selection, reboot, and recovery paths.
- `src/application/config_update.*`, resource serializers, Test Tone snapshots,
  `src/standalone/pico/main.cpp`, provisioning overlays/local settings services,
  USB management, encrypted Consumer-Radio, engineering HTTPS, and their fixtures.
- `engineering/protocol/control-1.schema.json`, control policy/checker, generated
  contract/assets, and every affected strict consumer/adapter. Inspect the actual
  companion source when determining shared-contract consequences; an old green
  run or version label does not establish compatibility.

The current failure is not just a missing HTTP branch: drive PUT returns
`not_configured` without `effective_config()`, Wi-Fi-only profiles return no such
configuration, progress drive application requires an applied Config, and Config
parsing requires valid WSPR station identity. Fix the owning boundaries rather
than bypassing one check or treating saved drafts as applied settings.

## Required settings model

Separate a valid persisted RF/settings configuration from a complete WSPR station
and from permission to transmit. Preserve the current storage envelope and field
types. Represent absent applied station identity explicitly within the current
station object as both callsign and locator empty, with a valid independently
typed reported-power value. Empty identity is absence, never a valid WSPR station.
Reject one-sided empty identity, malformed nonempty identity, invalid reported
power, wrong types, missing required structure, and extra fields. Independently
saved partial station drafts retain their existing non-runnable progress semantics.

Persisted absent station identity requires WSPR disabled. Reject an absent-station
record with WSPR enabled rather than relying only on a later launch refusal.
Admitting this initial hardware-settings state does not add a station-clearing
operation: existing station updates and commissioning still require their valid
station payloads. A drive save must never erase an established identity or apply
empty/partial station drafts. Explicit mixed writes retain their domain validation.

Use the existing journal, transaction verification, and boot selection for this
current representation. Do not accept arbitrary malformed configurations under an
"unconfigured" exception. Keep the existing decoding of already supported stored
records, including omitted drive, unchanged; do not add compatibility branches or
claim that older firmware can consume newly station-absent settings.

When applied settings exist, derive a drive candidate from the authoritative saved
settings plus the existing legitimate profile overlay, changing only the drive.
Preserve unknown-to-the-caller but supported settings, explicit false/zero/null
semantics, credentials, trust, station identity/absence, frequency permissions,
manual/GPS correction, pins, filters, amplifier timing, time sources, schedule
preferences, STOP, watermarks, and profile ownership. Do not reconstruct credentials
from a redacted GET or from browser/client defaults.

An established profile may supply a complete applied station even without a Config
record. Preserve that station and its existing authority when materializing the
first Config; absence of a Config record alone is not absence of station settings.

When neither a Config nor an authoritative applied station exists and storage is
healthy, derive the initial candidate from the existing validated factory hardware/
operating defaults and authoritative network/profile state. Leave station identity
absent and WSPR disabled; do not
enable or create a message schedule. Do not require network credentials for local
USB-only hardware settings. Wi-Fi-only authenticated users retain their existing
network profile and sessions. Initial drive save must not promote them to a
station profile, transfer station authority, replace credentials, or start setup.
Retain existing factory defaults as inert defaults, including any default WSPR
dial/preference; do not turn them into operator-selected or enabled recurrence.
An explicitly absent saved dial remains absent. Test Tone never consumes that
dial and adds no requirement to supply one.

Use any existing authoritative boot-applied hardware as the preservation baseline
where that is the active source, rather than overwriting it with generic defaults.
Pending or invalid drafts are not a source of applied hardware. Do not interpret
the Config type's 4 mA omission default as a fresh-device drive selection.

Do not reinterpret an unhealthy, corrupt, reset-pending, or ambiguously selected
journal/profile as a fresh device. Factory defaults are available only for a
healthy, authoritatively unconfigured state. Existing recovery/refusal duties win.

## Writes, activation, and authority

1. Keep PUT `/api/control/v1/gpio-drive` and its existing closed body
   `{contract,schema,target,gpio_drive_ma}`, legal values 2/4/8/12 mA, exact current
   device/boot, and If-Match. Keep the 12 mA new-installation default. Save only
   drive without requiring station fields or changing another domain.
2. Apply the same settings rules to the existing drive-only `config/update` patch
   and explicit progress `drive` Apply. A saved drive draft alone remains inert.
   Apply reads the identified saved draft/revision, never live browser inputs or
   unrelated invalid drafts. Do not let mixed patches inherit the drive-only
   exemption or implicitly apply incomplete station/network/schedule changes.
   Preserve existing rules for other patch domains; shared helpers may be factored
   only as needed for this correction.
3. Reuse existing authenticated carrier/profile authority: encrypted consumer
   station/AP, engineering HTTPS, and local physical USB. Page access, a public
   observer GET, plaintext HTTP, or a caller-supplied authority field grants no
   mutation. Do not promote an engineering or network caller to USB authority.
   No hidden route/carrier fallback or automatic save retry.
4. Require healthy storage and the current idle/unowned, inactive, nonfaulted
   output admission. Retain maintenance, STOP, schedule, and pending-restart rules;
   do not call global abort, clear faults, suspend schedules, release another owner,
   or treat scheduled/loaded/armed work as idle to make a save succeed. Validate
   the full hardware allocation, direct-engine applicability, journal capacity,
   and complete resulting candidate before writes.
5. A valid hardware-only change must not require WSPR encoding, a WSPR dial, or
   station completeness. Existing saved schedule intent must remain unchanged,
   including disabled or suspended preferences; preserving preferences is not
   permission to resume them. Explicit WSPR station/schedule enablement still
   requires the existing valid complete station and all WSPR prerequisites.
6. Commit through the existing verified Config transaction. Preserve failure,
   rollback, power-interruption, lost-reply, ETag consumption/no-op, and delivery
   receipt semantics. Do not report a durable save until authoritative readback
   confirms it. A lost response calls for readback and review before another
   deliberate write, never retry-by-fallback.
7. Save never programs GPIO or starts RF. A real drive change retains the sticky
   restart/output-inhibition latch, including A/B/A. Boot-active drive stays fixed
   until the existing explicit restart succeeds. A first save of the already
   active factory 12 mA is not a hardware change merely because a Config record
   is being created. Preserve existing no-op behavior and pending unrelated latches.

## Boot, observations, and execution

Reboot must select the saved drive and unchanged validated pin plan even without
station identity. Keep hardware validity and station readiness separate throughout
startup, scheduler construction, profile overlay, and runtime publication. Saving
hardware must not make `station_complete` true or make WSPR runnable. Adding a
real station later must preserve the prior hardware settings and authority.

After the first confirmed drive save, saved drive is the actual persisted value
even while station is absent. Before any saved configuration, saved drive remains
null and boot drive may be the factory 12 mA. Audit GPIO, hardware, config,
application/progress, and Test Tone readbacks so they agree about saved settings,
station absence, and restart state. Use existing nullable station observations
where defined; do not serialize absent identity as a valid station or make clients
infer readiness from Config existence. Preserve one current closed schema and
validate shape before access; update all affected Pico validators, serializers,
schema definitions, generated assets, and paired adapters together. Preserve all
unrelated schema constraints and the fixed Control/1 identifier/namespace.

Keep saved drive, immutable boot drive, and nullable SDK pad readback distinct.
The existing ARM-time observation remains job/epoch attributable; a save, Review,
or restart alone does not invent SDK evidence or measured current/power.

The already implemented Test Tone contract remains intact: absolute carrier
(including exactly 5,366,200 Hz), bounded duration, dry Review of proposed drive,
Start requiring the expected boot drive and both saved native schedules disabled,
native RF/clock/filter admission, exclusive ownership, local expiry after
disconnect, identified receipts/status, exact-job Stop, and unresolved-shutdown
inhibition. No new Test Tone field, per-tone pin/drive override, weaker clock rule,
or station metadata requirement is introduced. QRSS payload/message validation
remains mode-specific; this fix neither inserts WSPR identity into it nor redesigns
that execution path.

## Required deterministic acceptance tests

Exercise production handlers/journals and boot reconstruction, not only helpers.
Use existing RF-free engines/fake SDK fixtures; no physical RF is needed.

| Case | Required evidence |
| --- | --- |
| Healthy blank USB and Wi-Fi-only consumer | With no station identity, independently save each of 2/4/8/12 through the normal drive resource, read authoritative saved state, reconstruct boot, and verify active drive/pins. No station/profile promotion, credential changes, or schedule enablement. |
| Drive-only alternative paths | Drive-only merge and saved progress drive Apply have equivalent semantics; unrelated drafts stay inert; wrong draft revision refuses. |
| Initial 12 mA and A/B/A | First save of active 12 does not falsely change hardware; actual changes and A/B/A retain restart inhibition until boot. Saving never calls SDK pad setters or executes a job. |
| Existing complete configuration | Deep-compare all unrelated effective settings, credentials/authority, schedule preferences, STOP, and watermarks before/after save/reboot; preserve advanced settings and explicit absence of dial. |
| Profile-owned station without Config | First drive save preserves the complete effective station, network settings, profile authority, and sessions; it neither erases identity nor performs a station-authority transfer. |
| Absent versus invalid station | Both-empty identity persists/reloads without WSPR readiness; partially empty or invalid nonempty identity, invalid power, malformed/extra/missing fields refuse before mutation. Partial station progress remains a draft. |
| WSPR boundary | Absent station cannot enable or launch WSPR through config, progress, schedule, Console, boot, or other production admission paths; supplying a real valid station later preserves saved drive/pins. Existing valid WSPR operation remains unchanged. |
| Hardware and output boundaries | Invalid/conflicting pins, unsupported engine, oversized record, unhealthy/corrupt/reset-pending storage, wrong device/boot/revision, unauthorized carrier, owned/loaded/armed/running/faulted output, and unresolved shutdown refuse with no unauthorized writes or effects. |
| Interrupted and lost writes | Inject preparation/append/verification/selection failures and power interruption; selected settings remain verified old/new or explicitly unhealthy. A lost reply is reconciled by ordinary authoritative readback, never automatic replay. |
| Station-free Test Tone | For each drive, after simulated save/reboot, exercise Review/Start/status/Stop and per-job SDK evidence with station absent. Cover 52 dry Reviews over the existing 13-carrier fixture including 5,366,200 Hz. Retain policy refusals, disconnect expiry, early/stale Stop, lost Start reply reconciliation, fault inhibition, and zero Review execution/settings effects. |
| Carriers and strict schema | Exercise USB framing/ACK plus authenticated consumer station/AP and engineering routes; prove no new public/plaintext execution/write authority and consistent closed readbacks/limits. |

Run affected unit/API, storage, provisioning, progress, scheduler, Test Tone,
strict-contract/generation/policy checks and normal/inhibited firmware/link checks
using documented recipes and installed pinned dependencies. If a browser path or
generated asset changes, run its source/shipped checks and actual affected browser
fixture; do not build a new settings UI as part of this task. Use `git diff --check`,
strict Sphinx, and `scripts/check_documentation.py` for documentation changes.

The shared-control completion gate still requires both real production source-pair
network and USB integration suites from WsprryPi's checked-in
`.github/workflows/debian-non-hardware.yml`, using the intended candidate Pico,
explicit Pi revision, and pinned dependencies. Record commands and exact results.
Pico-only CI, mocks, old green runs, skipped tests, or another source snapshot do
not replace them. If actual companion changes are required for the current strict
contract, report the precise dependency as a blocker: do not modify Pi, relax
validation, bypass a suite, or claim coordinated completion. The present
documentation-only prompt task does not itself implement a protocol change.

## Documentation, assessment, and completion

Update existing owning operator/engineering guides to remove the complete-WSPR-
configuration prerequisite for drive saves. Explain station-independent settings,
factory defaults versus saved values, explicit restart/readback, no automatic RF,
and retaining/restoring the original drive for an HP 437B Automation sweep. Correct
the current bench-setup paragraph in Native-Execution.md and affected GPIO/
configuration/progress/USB explanations. Do not claim implementation or RF
qualification solely by editing docs, and do not label the HP client as a
qualification-harness project. Keep published documentation on Read the Docs.

After implementation, adversarially review the complete diff against every
requirement above, especially profile overlays hiding saved drive, first-write
semantics, boot reversion to defaults, station promotion, WSPR enablement bypass,
mixed patches, stale SDK evidence, latches, interrupted storage, and source-pair
coverage. Fix actionable findings and rerun affected checks. Perform a new full
assessment after the fixes; repeat until no actionable findings remain. Do not
create a permanent assessment diary or broaden scope to eliminate unrelated debt.

Report actual changed files, settings/boot behavior, review/fix outcomes, exact
test commands/results and source pair, remaining blockers, working-tree state,
and any separately authorized commit/CI links. Do not claim a merge, deployment,
physical SDK observation, or RF qualification that did not occur.
