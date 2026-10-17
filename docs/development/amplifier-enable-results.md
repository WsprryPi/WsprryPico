# Amplifier-enable execution and evidence

Executed 2026-10-17 from clean `devel` at
`9497ec42bad305d3b1833d7e680a8614bbd7332a`, matching the live remote entry tip.
Scope is consolidated backlog item 3 and its
[saved execution prompt](amplifier-enable-execution-prompt.md). Implementation,
software checks, three firmware builds and final independent adversarial review
are complete. The operator-selected software/build scope closes item 3.

The operator confirmed that no measurement fixture is connected and selected
software/build completion. Physical enable/RF edge ordering is unmeasured and
is an evidence limit, not deferred backlog work. No Pico, receiver, service,
configuration, firmware or physical wiring was operated; RF accounting is
zero jobs and zero seconds. No restoration was necessary. This result does not
qualify an external amplifier, physical shutdown, reset states or RF performance.

## Configuration and compatible management

`PinPlan.amplifier` reuses `amplifier_gp`: null disables it, and eligible pins
remain GP0–GP22/GP26–GP28 with exclusive ownership across RF, button, indicator,
LPF and both I²C pins. `amplifier_active_high` is a separate boolean with true
default. It never derives from indicator polarity. LPF and I²C RF remain
operationally unavailable. No pin is hard-coded or selected by fallback.

Default Config bytes and legacy pin serialization remain unchanged. Nondefault
active-low storage includes `amplifier_active_high:false`; configured amplifier
pins and nondefault polarity require supporting firmware. Invalid/unsupported
saved records fail closed without resurrecting earlier records or enabling a
default route. An older image must not be loaded over these settings without
first restoring a compatible complete default plan and removing incompatible
progress with supported reset/recovery. Flash addresses and journal capacities
are unchanged. This is a firmware rollback boundary, not automatic migration.

`capabilities.amplifier_enable` is a closed, independently versioned
`transmitter-amplifier-enable/1` descriptor. Its exact supported tuple selects:

| Route | Resource / behavior |
| --- | --- |
| GET `pins/2`, POST `pins/validate/2` | choices/2, explicit effective polarity, nonmutating candidate review |
| GET/PUT `hardware/3` | `transmitter-hardware/3`; saved/immutable boot pins, restart/error/storage state and nested GPIO drive |
| GET `application/4` | `transmitter-application/4`; station/2, hardware/3, existing recurrence and Type 1/2/3 plan |
| GET/PUT `config/4` | Config v1 content with explicit effective pin/polarity and GPIO drive |
| POST `config/update/4` | `transmitter-config-update/3`, merge or deliberate replacement |
| GET `progress/3`, POST `progress/update/3`, POST `progress/apply/3` | `transmitter-progress/3`, independent draft with existing drive domain and explicit application |

All routes use `/api/v1/`. Engineering station, authenticated field,
Consumer-Radio and physically bound USB use existing carrier authority. New
field routes retain Configure classification and preclock refusal. Schemas
cover network and USB management projections and bracketed Type 3 callsigns.
WTP/1, Field-GATT and USB management framing are unchanged. Other repositories
and companion compatibility pins were not modified or qualified.

Ordinary omitted plans preserve amplifier GPIO/polarity; an ordinary complete
pin save with omitted polarity preserves its saved value. Legacy Config pin
edits cannot silently clear either amplifier setting. Explicit replacement
defaults omitted settings. Legacy Config readback retains its closed projection
without the new polarity field and grants no amplifier editing authority.
Legacy choices retain amplifier unavailable; incompatible active pin/hardware/
application views refuse with `amplifier_view_required`. A legacy hardware write
against configured amplifier settings refuses before persistence. Other settings
continue through their established Config/scoped routes.

Progress uses `saved-progress/3` only for amplifier-bearing/nondefault-polarity
pin drafts. Old records still load. Omitted draft polarity preserves a prior
draft, otherwise applied polarity, otherwise true. Invalid pins/polarity reject
the complete batch before sibling saves, receipts or revisions. Incompatible
legacy progress reads/updates refuse before mutation; old radio drafts preserve
applied amplifier settings. A true-default pin draft is made explicit during
application so it can change a saved active-low output back to active-high.

Settings are saved only while idle, unowned, inactive and nonfaulted under the
existing target/revision admission. Saving never programs a GPIO. Changed pins
or polarity latch output inhibition/restart for the boot, including A/B/A;
unrelated saves and draft reversion cannot clear it. The active plan remains
immutable. The existing pin editor adds only enable pin/polarity and uses exact
capability negotiation, overlap lockouts and saved-versus-active readback.

## Local launch, cleanup and failure ownership

Portable `AmplifierEnable` uses a narrow checked `EnableOutput` adapter.
Disabled configuration has no output adapter, no GPIO access and no artificial
launch acknowledgement. Core 0 initializes a healthy, validated boot output
inactive, then transfers the policy to the RF core before job/service calls.
Pinned SDK `gpio_init` sets input direction, clears the SIO latch and selects
SIO; the adapter preloads the declared inactive level before setting output
direction. Both polarities are checked. External bias remains responsible for
reset, boot ROM, unpowered periods and states software cannot control.

Every job producer enters the same JobService, StreamEngine and PIO/DMA sink.
LOAD renders/prepares without asserting enable. ARM and indicator retries keep
it inactive. The final driver launch checks clock/epoch/ownership admission,
safety, indicator acknowledgement, FIFO, deadline and RF drive, then asserts
enable immediately before enabling physical RF. The driver rechecks deadline
and safety after the write and safety after enabling PIO. The IRQ path does no
network/CYW43, allocation, logging, storage or waiting for another core. Existing
local timer bounds and the renderer/refill authority remain unchanged.

One interval covers a finite job including its keyed gaps. Separate jobs,
including each frame of a Type 2/3 pair, deassert between them. No settling,
early lead, tail dwell, drive regulation or RF warmup is introduced.

Cleanup clamps RF, attempts enable deassertion, then enters fallible DMA halt
waits. It covers normal hardware tail completion, delayed tail IRQ, stop/abort,
lease-driven actual termination, missed/rejected launch, partial/no-open state,
DMA faults and repeated disable/rearm. Neither a halt failure nor an early
resource failure can skip the enable attempt. Register/pad mismatch leaves
output active-or-unknown, retains failed state/ownership and blocks admission.
An issued command alone does not prove success. Armed/running lease expiry
continues its finite job until terminal state, as before; transport disconnect
does not add an independent cancellation policy.

Missing-worker/nonreturning fault recovery first latches inhibition, forces RF
OUTOVER low and OEOVER disabled, then forces amplifier OUTOVER inactive before
watchdog recovery. These overrides prevent late SIO writes/final launch from
undoing the emergency state. Recovery does not report verified physical
shutdown or release ownership. Inhibited firmware initializes inactive but
never passes the output to its simulator and links no physical RF worker.

## Validation and artifacts

Fresh ignored work areas: `build/amplifier-enable-20261017/host` and `pico`.
Use the retained Xcode host environment and pinned local dependencies:

```sh
source scripts/xcode_env.sh
cmake --preset host-debug -B build/amplifier-enable-20261017/host
cmake --build build/amplifier-enable-20261017/host --parallel 4
ctest --test-dir build/amplifier-enable-20261017/host --output-on-failure -j 4
python3 scripts/validate_wtp_contract.py
PICO_SDK_PATH="$PWD/build/local-sdk-079c6f3" bash scripts/build_pico.sh WsprryPico build/amplifier-enable-20261017/pico
cmake --build build/amplifier-enable-20261017/pico --target WsprryPico-Inhibited WsprryPico-StandaloneRF --parallel 4
```

The complete host regression selected 185 checks: 183 passed, one optional
`config_update_schema` skipped under Python 3.15 without jsonschema, and
`phase14_tests` hit sandbox denial while binding a local loopback socket. The
unchanged loopback check passed with local network permission. The skipped
schema check passed with the retained check-jsonschema Python environment:

```sh
/opt/homebrew/Cellar/check-jsonschema/0.38.2/libexec/bin/python tests/config_update_schema_tests.py build/amplifier-enable-20261017/host/config_update_tests
```

Adding the retained SDK TinyUSB path registered the 186th check; actual USB
descriptors passed separately. No software assertion remains skipped/unresolved
among those 186 registered checks. Optional numerical capture-analysis and
additional SDK-fixture suites were not configured; no tools/dependencies were
installed. The WTP validator passed 23 schema, seven raw JSON, one framing and
eight transition cases. Initial failures and repairs are retained below rather
than being represented as an initially clean run.

Focused tests exercise both polarities, disabled/no-touch initialization,
conflicts and malformed data, atomic persistence failure, legacy omission and
explicit reset, boot/saved separation, A/B/A, draft-only behavior, true/false
round trips, capability/schema/carrier compatibility, actual shipped pin editor,
long ARM, stale epochs, final launch rejection/cancel, failed assertion,
completion, prelaunch/running ABORT, lease expiry, physical stop authority, DMA
fault, failed RF halt, unconfirmed deassertion, partial initialization, delayed
completion, idempotent stop and rearm. Production JobService + renderer + sink
tests retain ownership on unknown output and retain armed finite-job lease
semantics. Existing LED/button/scheduler/storage/transport checks pass.

Normal, explicit inhibited and compatibility RF targets all link at 138 MHz.
Linked-image checks pass for engine classification, GP14 safety, guarded 32 KiB
primary/16 KiB worker stacks, heap/stack separation, reserved flash journals,
pool/heap hooks and RF renderer SRAM placement. The inhibited image's physical
worker/driver absence passes its image guard. These are build/source observations,
not on-device GPIO or timing measurements.

The [sanitized build manifest](amplifier-enable-builds.json) records every
maintained source-input hash, the aggregate input fingerprint, exact changed
paths, pinned SDK/toolchain/picotool, generated identity and all ELF/UF2 hashes.
Images identify `9497ec42bad3-dirty`, bound to that input fingerprint; they were
built before the publication commit and were never loaded. Artifacts remain
under the ignored task directory. SDK 2.3.1 is
`079c6f39023649b154152db30f1d781e884879bc`, picotool is
`6f6458d792b93685a11423b244a585eaa99eafcf`, Arm GNU is 15.3.1, and owned language
standards/build pins are unchanged.

## Independent adversarial review and repairs

A separate read-only reviewer examined lifecycle, configuration, schemas,
browser behavior and evidence. Findings repaired during implementation:

- Fault recovery could wait for the eight-second watchdog while leaving enable
  active. Immediate inhibited RF/enable overrides now precede that wait; RF OE
  override also resists a late launch clearing OUTOVER.
- Legacy pin editors could clear a saved enable assignment. Ordinary Config
  pin writes preserve it; incompatible hardware routes refuse before mutation.
- Legacy progress updates could commit before an incompatible readback returned
  409. Admission now refuses before journal/receipt/revision changes.
- Legacy radio-draft application could preserve the amplifier by dropping other
  intentional pin edits. It now projects only the two amplifier fields through
  legacy Config preservation; the regression applies RF GP19 while retaining
  GP18 active-low enable.
- New schemas inherited incomplete Type 3 grammar and network-only capability
  variants. They now accept actual bracketed Type 3 and USB-management views.

Implementation verification additionally caught default-true draft omission
concealing an active-low-to-active-high application, missing browser test
controls and a test's non-microsecond-aligned rearm instant. Explicit negotiated
read/application values and corrected behavioral fixtures pass affected checks.
The initial broad test's sandbox loopback denial was environmental and passed
with local network permission; the optional schema dependency was reused from
an existing environment. No hardware test failed or consumed RF budget.

Fresh final read-only assessment found no actionable findings. The reviewer
independently reran seven focused amplifier/schema/browser/worker/RF checks,
all passing, and verified all 770 source hashes, aggregate fingerprint, exact
changed-path inventory and all six ELF/UF2 hashes against the task artifacts.
The final legacy-draft repair passed eleven affected checks and refreshed all
three firmware links; unaffected regression evidence above retains applicability.
Changed Markdown local links (526), JSON parsing, JavaScript syntax, changed-line
C++ formatting and whitespace checks also pass. The source pair has no companion
change. Commit/push/parity are reported with the execution closeout; the manifest
binds these pre-commit images to their exact source content independently of Git
publication. The consolidated backlog remains the sole work list; this record
adds no physical edge-ordering task or parallel roadmap.
