# Shared transmitter application and fleet contract

Status: selected application arrangement with a Pico configuration/API foundation
implemented in source. The [foundation guide](development/shared-transmitter-application.md)
and [review](development/shared-transmitter-application-review.md) define its
supported scope and evidence. Broader schemas, compatibility adapters and
migrations remain proposals. Full application parity and physical qualification
are not claimed.

Recorded: 2026-09-30. Foundation update: 2026-10-03.

Every Pi or Pico fleet member runs a local transmitter application that owns its
hardware, validates jobs and executes them locally. A fleet controller manages
members through a shared JSON application model and the existing WTP job
protocol. Hardware configuration is one part of that application model; station,
message, schedule, ownership, time, status and management behavior also belong
in it.

The same member can support standalone operation and fleet operation. Each
schedule has one recurrence authority, and every submission path on a member
uses one transmitter ownership and execution authority.

## Scope and authority

This contract records the arrangement for WsprryPico and its intended
interoperability with WsprryPi. The Pico target remains Pico 2 W / RP2350. Pi
and Pico use their existing platform adapters; Linux services, RP1 DKMS and
Linux hardware access are not ported into Pico firmware.

The normative [WTP/1 contract](protocol/WTP.md), its
[schema](protocol/wtp-1.schema.json) and
[machine-readable contract](protocol/wtp-1-contract.json) continue to define
finite job control. The [browser API v1](browser-api.md),
[standalone configuration](development/standalone.md) and
[architecture](architecture.md) describe existing Pico behavior. This document
defines the application direction and additional implementation requirements;
it does not silently revise those existing wire or storage contracts.

In this document, **must** states an implementation requirement and **proposed**
identifies a choice that still needs a concrete design. Requirements in this
contract do not themselves grant authority for another repository, hardware
control, flashing or RF output. Each implementation and publication task requires
its applicable authorization.

## Application roles and responsibilities

A **member** is an identified transmitter node with its own application and
selected RF chain. A **controller** maintains a fleet catalog and may manage
recurrence or configure a member's autonomous recurrence. A Pi may be both a
member for its own output and a controller for other members.

| Function | Member responsibility | Controller responsibility |
| --- | --- | --- |
| Identity and discovery | Report device and boot identity, capabilities and available bindings. | Discover candidates and verify the selected identity and binding. |
| Hardware | Own RF engine, output pins, reference calibration, amplifier and filter controls. | Read or explicitly configure the identified member through its management API. |
| Station and messages | Store supported station and message defaults; compile local submissions. | Compile centrally submitted jobs or install supported member configuration. |
| Recurrence | Generate finite jobs for member-owned schedules. | Generate finite jobs for controller-owned schedules. |
| Execution | Validate complete jobs, own launch/event timing and perform cleanup. | Load and arm complete jobs and service their ownership policy. |
| Ownership | Arbitrate all local and remote work and expose supported local takeover. | Respect leases, local reservation, takeover and unresolved output. |
| Time and health | Enforce local clock/admission limits and report faults and output state. | Check readiness and preserve uncertainty in observations. |
| Management | Validate, persist and apply supported changes; report saved and active state. | Use device revisions and reconcile uncertain write results. |

Shared semantics do not require identical engines, limits, operating systems,
browser assets or implementations. Unsupported functions must be explicitly
reported and rejected. A member that executes controller-compiled jobs does
not need full autonomous scheduling to be useful in a fleet.

Local browser jobs, standalone schedules, USB WTP and network WTP must converge
on the member's existing ownership/execution boundary. Controller browser
actions must use the controller's existing runtime rather than create another
RF or job authority. The existing Pi browser adapter's restriction on raw job
submission remains in effect until a separately specified implementation
changes it.

## Scheduling arrangements

### Controller owned recurrence

The controller stores the schedule, station/message inputs and per-output
assignment. At each admitted occurrence it compiles a complete finite job,
checks the member's current capabilities and clock, obtains ownership, then
loads and arms through WTP. The member's persistent schedule is not implicitly
enabled by this operation.

The controller may run recurrence indefinitely while every WTP job remains
finite. Complete events, repeats, gaps and tails must fit the member's advertised
limits before ARM. Network packets never supply symbol boundaries.

The member executes under WTP's defined lease and disconnect behavior. Expiry
while loaded aborts that unarmed job and releases ownership. Once armed or
running, the lease extends through a terminal state; connection or lease loss
must not alter local event timing. Faults and explicit abort still follow the
normal lifecycle. Controller loss does not establish output-off and must not
trigger an automatic local replacement schedule, endpoint substitution or job
replay. The controller records uncertain outcomes and reconciles them before
resuming work.

### Member owned recurrence

The member stores supported station/message configuration, schedule, enable
state and occurrence history. Its local scheduler creates and submits complete
finite jobs through the same application service as remote work. After setup,
recurrence can operate without the controller when local clock and safety
conditions permit.

The controller configures and observes this arrangement; it does not also
dispatch the same occurrences as remote jobs. Persistent recurrence may be
unbounded, with optional expiry, while individual jobs remain bounded.
Per-device persistence, missed-slot and no-repeat policies must be specified
and tested. Existing Pico watermarks and Pi assignment policies are preserved
until an explicit migration defines their replacement.

### Ownership and schedule transfer

Recurrence authority is a property of each schedule or assignment. It does not
replace the member's transmitter ownership gate. Local enable may reserve a
member between occurrences, as it does on the managed Pi; clients must not
interpret an idle RF gap as availability for a remote claim.

Moving recurrence between controller and member requires pausing the old
authority, reconciling any in-flight work and confirming the applicable output
is inactive, then installing the destination schedule disabled. Enablement is
a separate explicit action after saved-state readback. An interrupted transfer
must leave no automatic duplicate dispatch. Cross-device writes are not assumed
to be atomic; durable transfer/recovery semantics remain a schema-design gate.

Local safety stop and supported local takeover remain available without a
controller's approval. Takeover must prevent stale controller assignments from
silently reacquiring authority. The existing Pi takeover/revocation contract is
preserved; equivalent Pico behavior must be designed and validated before it is
advertised. A failed cleanup or unknown output inhibits reuse of that RF chain.

## Shared application configuration domains

The shared model describes an identified member and its supported application
functions. The controller's connection choices and fleet catalog are separate
from that member's settings.

| Domain | Target contents |
| --- | --- |
| Operation and admission | Local scheduling enable, requested/effective reservation, boot policy and supported stop/takeover operations. Persistent policy and volatile actions are distinguished. |
| Station | Callsign, locator and reported WSPR power. Support for encodings and locator lengths follows advertised capability. |
| Messages and job planning | Mode, frequency/presets, random offset, WSPR planner preferences, CW message, shift, timing/gaps and supported waveform preferences. |
| Schedules | Recurrence authority, period/phase, enable/expiry and occurrence/recovery state with explicit ownership and persistence rules. |
| Hardware | Selected RF engine, engine-specific settings, calibration, amplifier, band/filter selectors, indicators and buttons. |
| Network and services | Supported connection/time-server/listener settings and explicitly separate credential provisioning. |
| Capabilities and status | Supported management functions, legal resources, actual engine/limits, clock health, saved/active revisions, job/owner state and cleanup results. |
| Controller configuration | Target identity/binding, endpoint references, transport acceptance, TLS file references, fleet catalog and controller-owned assignments. These remain on the controller. |

WSPR reported power is message content. GPIO pad drive and synthesizer drive
are electrical settings. None is measured antenna power, and one must not be
used as a substitute for another.

The Pi's `Operation.Transmit` must retain its existing local-reservation and
takeover meaning. Pico's standalone `enabled` controls autonomous admissions.
Neither is silently renamed into a universal RF-inhibit switch. The future
schema must make these distinctions explicit.

## Hardware configuration coverage

The following inventory defines target coverage for compatibility adapters.
Each member exposes only the implemented and validated subset. Inclusion here
does not select exact JSON member names or implement new Pico hardware drivers.

| Current WsprryPi setting | Shared model requirement |
| --- | --- |
| `Operation.Transmit Backend` | Device RF engine selection; the controller's `wtp` adapter is a separate connection choice. |
| `GPIO.Transmit Pin` | RF output assignment with explicit device pin numbering and engine/board validation. |
| `GPIO.Power Level` | Preserve the legacy 0–7 driver setting as implementation-specific drive configuration. |
| `GPIO.RP1 Drive mA` | Optional pad-drive setting; Pi RP1 choices are 2/4/8/12 mA. Pico advertises its own choices only after implementation. |
| `GPIO.Use System Clock Frequency Estimate` | Optional supported frequency-estimate provider selection. Linux/Chrony semantics remain Pi-specific. |
| `GPIO.Frequency Residual PPM` | Residual correction associated with an eligible provider estimate. |
| `GPIO.Manual PPM` | Fixed GPIO reference correction and defined fallback semantics. |
| `Calibration.PPM` | Explicit Si5351 reference correction; it is not a generic correction for every engine. |
| `Si5351.I2C Bus`, `I2C Address` | Controller/bus resource and address. Pico additionally needs validated SDA/SCL assignments. |
| `Si5351.Reference Frequency`, `Reference Source` | Nominal reference Hz and supported external-clock/TCXO or crystal source. |
| `Si5351.Crystal Load Capacitance` | Crystal-only load setting, currently 6/8/10 pF on Pi. |
| `Si5351.TX Output` | RF clock-output selection, currently CLK0/CLK1/CLK2, with other uses reserved. |
| `Si5351.Power Level` | Explicit synthesizer drive; current Pi levels 1–4 map to 2/4/6/8 mA. |
| `Operation.Use Amp`, `Amp Pin`, `Amp Pin Active High` | Optional amplifier control, resource assignment and polarity. |
| `Band GPIO` per-band `Enabled`, `GPIO`, `Active High` | Band selector mappings for the 19 current Pi bands; shared outputs require consistent polarity. |
| Frequency-entry `@GPIO[H\|L]` | Preserve Pi compatibility behavior; propose named selector/filter references for future portable overrides. No GPIO suffix is added to WTP/1 jobs. |
| `Operation.Use LED`, `LED Pin` | Optional transmitter indicator, using an onboard indicator or external output where supported. |
| `Operation.Use Shutdown`, `Shutdown Button` | Optional local input and supported actions. Pi shutdown and Pico stop/reset/setup gestures retain distinct semantics. |
| CW `Fade Shape`, `Fade In Ms`, `Fade Out Ms` | Supported waveform preferences, with explicit engine and job-path applicability. WTP/1 has no envelope fields. |
| CW `Fade Slice Ms` | Optional advanced approximation setting for the implementation that uses it. |

Related Pi settings stay in their appropriate domains: `Transmit` and
`Enable on Boot` in operation; WSPR station/frequency/planner fields and CW
message/frequency/shift/dot/gap fields in job planning; CW start/repeat fields,
`Loop TX` and `TX Iterations` in recurrence or finite execution policy.

`WTP` endpoint identity, USB path/serial/VID/PID, transport, hostname/port, TLS
identity/file references, start-uncertainty acceptance and frequency-adjustment
consent remain controller settings. `WTP Server` enable/port/interface, web/socket
settings and platform service options belong to service adapters. Experimental
frequency overrides and RP1 development confirmation remain explicit engineering
policy. Logging, INI paths and Linux installation details do not become required
portable hardware fields. Detection, bus/address inventories, route readiness
and effective correction belong in read-only capabilities/status.

## Engine and resource rules

GPIO generation and Si5351 are interchangeable engine families at the application
boundary. The implemented Pico PIO/DMA path remains the starting engine; a Pico
Si5351 engine is an additional implementation with separate timing and RF
qualification. Pi BCM/RP1 and Pico PIO identifiers, resources and numerical
limits must not be conflated.

Pin references must identify the device numbering scheme, such as Pi BCM GPIO
or Pico GP, rather than a bare header-pin number. Validation covers RF output,
amplifier, filters, indicator, local button, I²C SDA/SCL and all board-reserved
resources together. The [selected Pico pin-assignment contract](pin-assignment-contract.md) defines
exclusive GPIO ownership, exactly one direct RF GPIO or one fixed I²C pair, and
the onboard-default/configurable TX indicator. GP14 remains the default button
assignment and is reserved while enabled. Compatible devices may share the single
selected I²C bus with distinct addresses; independent GPIO sharing is forbidden.

Calibration is bound to the physical reference, device and engine. The schema
must define correction sign, provider qualification, age/holdover and fallback
composition. Pi's system-clock estimate must not be applied to the Pico or
Si5351 reference merely because a Pi is the controller. UTC discipline and RF
frequency calibration remain separate. Effective values and provenance are
reported without applying correction twice.

Engine selection, pin selection and clock/drive configuration never authorize
RF output. Build-fixed clock choices remain read-only until configurable
operation and its affected timing, resource and RF behavior are validated.

## Amplifier and filter execution

Existing Band GPIO is a selector model. It does not describe LPF response or
establish filtering qualification. The target application adds named filters,
declared frequency coverage, selector wiring/polarity, inactive states,
settling requirements and an explicit policy for requiring a valid selection.
These are implementation requirements; exact representation and timing values
remain proposals.

Admission checks every RF-on frequency in a complete job, including shifts and
planner-realized frequencies. The initial implementation selects one configured
filter suitable for the complete job. Jobs needing a different filter during
execution are rejected until an explicit locally timed switching design is
implemented and qualified. Disabled selection must distinguish fixed/manual
filtering from an absent required filter; it must not silently imply coverage.

The member performs the sequence locally: confirm RF and amplifier disabled,
prepare the engine and filter, allow required settling, enable the amplifier
with any supported lead time, execute the complete job, disable RF, then return
amplifier and selector outputs to their defined safe states. Lead/tail delays
are proposed additions, not existing Pi configuration fields. Their admission,
lease and cleanup accounting must fit the advertised lifecycle bounds. Any RF
warmup must be represented by an explicitly supported job/engine behavior; no
unannounced RF interval may precede the job.

Abort, missed launch, pre-arm lease expiry, reboot and fault paths use the same
cleanup boundary. Armed/running lease expiry follows the terminal-extension
rule above. Amplifier or selector control failures must not be reported as
successful execution or cleanup. Confirmation states the adapter's actual
observation method; a commanded/read-back GPIO state does not prove physical
amplifier shutdown or measured RF silence. Unconfirmed chain safety inhibits
further admission and requires local recovery.

## JSON API compatibility and configuration transactions

The Pico foundation freezes `GET /api/v1/application`, `GET/PUT /api/v1/station`
and `GET/PUT /api/v1/hardware` with independently versioned resource identifiers,
explicit member/device/boot targets, closed
[schemas](protocol/transmitter-application-1.schema.json),
[vectors](protocol/transmitter-application-1-vectors.json) and an
[inventory coverage map](protocol/transmitter-application-1-coverage.json).
These bounded projections reuse the existing configuration coordinator and
journal. Expanded message/schedule resources and Pi compatibility mapping remain
implementation gates. Existing routes retain their existing meanings.

In particular, current Pico `/api/v1/config` is its standalone version-1
configuration. The Pi adapter's `/api/v1/config` projects that remote Pico
resource, while `/api/v1/host/config` manages Pi application and transport
settings. A new local/remote projection must identify its target and scope;
the route must not silently switch between Pi and Pico configuration.

The current Pico parser rejects unknown fields and limits its stored document
to 1,800 bytes. The pin branch explicitly extends Config v1 with optional `pins`:
default plans retain legacy canonical output; older firmware rejects documents
containing nondefault plans. The new resources add no stored fields or journal
regions. Scoped updates are limited to 1,024 UTF-8 bytes and emitted resources
are checked against a 4,096-byte response budget. Later hardware/application
fields still require explicit schemas and migration/storage/parser/body budgets.

New hardware mutations must meet all of the following requirements:

- Verify the intended member identity and the applicable revision using
  `ETag`/`If-Match`; boot/recovery changes invalidate stale application contexts.
- Atomically require an unowned, inactive, nonfaulted service with no pending
  admission, preparation or cleanup. A loaded externally owned job blocks the
  change; a configuration request never aborts or steals it implicitly.
- Serialize mutation with local scheduling, CLAIM/LOAD/ARM and all other writers.
  Validate the entire resulting configuration and dependent schedules before
  changing storage or active hardware.
- Commit and verify persistence before reporting a successful save. Preserve a
  recoverable configuration through interruption; invalid recovery inhibits
  admissions rather than selecting an unsafe fallback.
- Report saved revision, active revision, pending application/restart and errors
  separately. Unsupported values are rejected rather than approximated or
  silently replaced.
- Keep hardware saves separate from transmit/schedule enablement. A configuration
  write does not clear a fault, unsuspend STOP, renew a lease or grant RF authority.

Where hardware is inactive pending restart, job admission uses the active
configuration or remains inhibited as explicitly specified; it must not pretend
the saved hardware is active. Related documents/resources need a common validated
generation or equivalent dependency checks. Independent ETags alone cannot make
conflicting hardware and schedule writes safe. Changes to a filter, RF range or
engine must invalidate or revalidate dependent work before it can be enabled.

A controller passes the member's revision through unchanged. On an ambiguous
save it reads authoritative saved/active state before retrying. Management
must not create a second connection or authority that bypasses owned work.
Credentials remain redacted, and controller-local TLS paths are never installed
as Pico paths.

## Transport and capability boundaries

WTP/1 continues to carry complete finite jobs with `rf-events/1`. Its closed
objects prohibit adding hardware fields, arbitrary filter identifiers or
envelope events without a new protocol version. Existing WTP CAPS still report
the selected engine, supported modes/ranges and execution limits. New management
features are advertised in the JSON API rather than inserted into WTP CAPS.

USB CDC remains the canonical/reference WTP carrier; network WTP/TCP is also
first-class. An implemented WTP carrier does not imply a configuration carrier.
The current Pi remote JSON management path uses engineering HTTPS over its
`network` transport; USB WTP and `network_plain` do not provide that path.
Consumer management, station HTTP/HTTPS and USB JSON administration must each
have an explicit supported carrier and access policy before advertising the
new configuration functions. The foundation uses the existing authenticated
HTTPS BrowserApi, including the existing normal field cookie/session policy;
blank and pre-clock field configuration remains denied. It adds no listener,
consumer HTTP resource, new management binding or authentication downgrade.

Discovery locates candidates. Device identity, security binding, boot identity,
current CAPS and status determine selection and admission. Plain LAN identity
observations are not authenticated. A connection failure does not establish
output-off or justify substitution of another node.

## Implementation path

These slices are ordered implementation gates. The Pico foundation delivers
the supported station/pin resource subset of slices 1 and 2 using the pin branch's
supported slice-3 adapters. This does not close an entire slice or claim any
later adapter, transfer or physical gate. Pico and Pi changes remain independently
scoped repository tasks.

| Slice | Deliverable | Gate before progressing |
| --- | --- | --- |
| 1. Schema and compatibility | Freeze application domains, target/scope identity, supported-field semantics, resource versions, recurrence authority and migration/error rules. Supply machine-readable schemas and positive/negative vectors in this repository. | Account for every setting in the inventory; preserve WTP/1 and existing API meanings; define management carriers and storage/body bounds. |
| 2. Portable application model | Implement bounded parsing, cross-resource validation, configuration generations, persistence/recovery coordination and status/capability reporting behind platform adapters. | Deterministic tests for malformed/unsupported input, stale writes, conflicting resources, save failures, interrupted application and admission races. |
| 3. Pico hardware integration | Make supported PIO output configuration explicit; implement optional amplifier/filter/indicator/button adapters and one-chain local execution/cleanup. Retain unsupported Si5351 and clock choices as unavailable. | Host fault/lifecycle checks and pinned cross-build; opt-in RF-inhibited target verification before separate RF qualification. |
| 4. Pi compatibility and controller integration | Map existing INI/CLI settings to the common model, preserve local takeover, project explicit member configuration and add capability-driven fleet management. | Test target identity/revision errors, native/remote scope, existing control behavior, management contention and independent output contexts without hardware. |
| 5. Autonomous scheduling and transfer | Expand supported member station/mode/frequency/schedule configuration; implement recurrence ownership transfer and durable duplicate prevention. | Test local/remote contention, expiry, missed slots, power-loss recovery, offline takeover and uncertain transfers. Central finite-job operation remains useful before this slice. |
| 6. Physical and release acceptance | Qualify each selected board/engine/control chain and publish exact supported capabilities and operator documentation. Add Pico Si5351 in a separately bounded engine tranche if selected. | Pass the applicable target timing/control, conducted RF and controller/member acceptance matrices with restoration recorded. |

The implementation must reuse portable validation, encoders and ownership
concepts where their semantics match. It must not add a third protocol
repository, independent per-interface schedulers or a Linux web stack to Pico
firmware. Passing a schema or cross-build gate does not close physical gates.
This path does not reopen or close the existing Phase 11/12 acceptance records.

## Required acceptance evidence

| Boundary | Required evidence |
| --- | --- |
| Schema and adapters | Round-trip compatibility, unsupported fields/versions, duplicate keys, bounds, pin/bus conflicts, calibration composition and explicit power meanings. |
| Persistence and application | Stale revisions, concurrent writers/admission, failed/interrupted saves, old-versus-new recovery, saved/active reporting and restart requirements. |
| Jobs and recurrence | Complete-job validation, clock rejection, one owner per chain, loaded-job configuration exclusion, missed/consumed slots, uncertain reconnects and no duplicate transfer dispatch. |
| Control lifecycle | Amplifier/filter preparation and settling, abort/missed/lease/fault cleanup, safe boot/reboot and failure to confirm inactive output. |
| Host/controller behavior | Correct local/remote scope and identity, unchanged Pi control semantics, credential redaction, explicit management availability and no automatic binding fallback. |
| RF-inhibited target | Exact device/image/engine/clock/pin setup, persistent readback, observable control states, reset/recovery and bounded transport/resource coexistence. |
| Conducted RF | Separately authorized physical chain, measured launch/transitions/cleanup, frequency correction, decoding where applicable and spectrum/filter/amplifier behavior. |

Hardware evidence must name the board, firmware/source, engine, clock, mode,
pins, amplifier/filter state, receiver/reference and physical RF path, together
with cleanup/restoration. Mock/host results and numerical capabilities do not
qualify target timing, electrical behavior, filtering or RF output. Existing
bounded campaign results remain bound to their original configurations.

## Open design choices

- Expanded application/hardware schemas and Pi local/remote projection paths.
  The Pico foundation's resource identifiers, paths and bounded shapes are frozen
  in the linked schemas; unsupported additions require a separately specified version.
- Consumer and USB management carriers and access policy, including whether
  supported device profiles expose the new management resource.
- Recurrence-transfer journal, schedule identifiers/revisions and recovery of
  interrupted cross-device changes. Automatic offline fallback is not selected.
- Implemented/qualified Pico pin assignments and drive settings, configurable
  clock scope and bus electrical settings. The eligible pin set, fixed I²C pairs
  and exclusive allocation rules are selected in the
  [pin-assignment contract](pin-assignment-contract.md); Si5351 remains a separate
  unimplemented Pico engine option.
- Fixed/manual LPF declaration, supported selector circuitry, settling and
  amplifier lead/tail values, and physical confirmation methods.
- Waveform/envelope configuration applicability. Per-job envelope control or
  selector references cannot be assumed interoperable through WTP/1.
- Migration of stored Pico configuration and existing Pi INI/CLI representations
  without losing station, schedules, credentials, watermarks or takeover history.

## Current source baseline and references

The inventory was checked against WsprryPico
`70f71dc504dba57398b64ed8cbc712b3e128a0b7` and WsprryPi
`2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19`. Relevant Pi configuration and fleet
sources were read without edits; unrelated Pi installer working changes were
outside this contract's source inventory. These revisions identify the reviewed
baseline, not an implementation or qualification of this new contract.

The current Pico has a standalone application, browser API and common JobService.
At pin baseline `251ed992245f3b95611de767cc732f3cb1bbb34d`, direct RF, active-low
button and indicator plans have supported boot-applied adapters; GP2 is the
default RF assignment. The foundation exposes these through shared member
resources. Its configuration remains narrower than Pi's. Amplifier/LPF, drive,
reference calibration and Si5351 remain unavailable Pico adapters. The Pi has
controller-owned per-output fleet schedules and an inbound
WTP endpoint using its native Si5351 backend; these are separate from complete
shared application/configuration parity.

- [Pico standalone model](../src/standalone/config.hpp) and
  [strict parser](../src/standalone/config.cpp).
- [Pico PIO output assignment](../src/rf/pico/pico_pio_dma.hpp).
- [Pi configuration inventory](https://github.com/WsprryPi/WsprryPi/blob/2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19/src/config_handler_serialization.cpp).
- [Pi local control and WTP exclusions](https://github.com/WsprryPi/WsprryPi/blob/2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19/src/arg_parser.cpp).
- [Pi shared browser adapter](https://github.com/WsprryPi/WsprryPi/blob/2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19/docs/wtp-browser-api.md).
- [Pi management carrier](https://github.com/WsprryPi/WsprryPi/blob/2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19/src/wtp_runtime_bridge.cpp).
- [Pi fleet recurrence](https://github.com/WsprryPi/WsprryPi/blob/2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19/docs/wtp-fleet.md).
- [Pi member ownership and takeover contract](https://github.com/WsprryPi/WsprryPi/blob/2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19/docs/wtp-pi-endpoint-contract.md).
- [Pi implemented endpoint scope](https://github.com/WsprryPi/WsprryPi/blob/2f67b0003f055bb4a7cc7c72fdf71a2b9c4cab19/docs/wtp-pi-operation.md).
