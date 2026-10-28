# Amplifier enable

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
WTP/1, Field-GATT and USB management framing are unchanged. The timing extension is coordinated with the production WsprryPi USB and network clients.

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
LOAD renders/prepares without asserting enable. The admitted ARM wait keeps it inactive until the configured lead interval. The final driver launch checks clock/epoch/ownership admission,
safety, indicator acknowledgement, FIFO, deadline and RF drive, then asserts
enable before RF: a configured nonzero lead uses its own local alarm, while zero lead asserts immediately before enabling physical RF. The driver rechecks deadline
and safety after the write and safety after enabling PIO. The IRQ path does no
network/CYW43, allocation, logging, storage or waiting for another core. Existing
local timer bounds and the renderer/refill authority remain unchanged.

One interval covers a finite job including its keyed gaps. Separate jobs,
including each frame of a Type 2/3 pair, deassert between them. Configurable RF-off lead and tail surround each job. Drive regulation and RF warmup remain unavailable.

Emergency cleanup clamps RF, attempts enable deassertion, then enters fallible DMA halt waits. Normal completion may retain enable through its bounded RF-off tail before the same cleanup. It covers normal hardware tail completion, delayed tail IRQ, stop/abort,
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

## Lead and tail timing

Lead is the minimum amplifier-enabled, RF-off settling interval before a job's scheduled RF onset. Tail is an amplifier-enabled, RF-off interval after the zero-data DMA stop has confirmed normal RF completion. Both default to **200 ms** and accept **0–1000 whole milliseconds**, independently. Zero removes that interval. There is no separate settling value to add twice. The maximum bounds RF-chain reservation to two extra seconds and fits the existing minimum two-second standalone WSPR preparation interval; it is a software policy bound, not a measured amplifier requirement. Disabled amplifier configuration uses neither delay and performs no enable GPIO access.

The Pico's Radio pins section places timing beside the amplifier pin/polarity controls. WsprryPi's selected-member hardware section places timing beside supported pin settings; amplifier pin/polarity editing remains on the Pico's Radio pins page. Both editors retain existing form styling and native number controls, with explicit read, save and discard actions. Reads, failed saves and target changes preserve unsaved entries; using preserved entries for a different Pico or boot requires the explicit “Use entries for this Pico” action. Discard restores the last-read saved values. Readback separates saved timing, active timing for this boot, phase at readback and pending restart. Saving never toggles an output. Timing uses the existing idle, unowned, inactive, nonfaulted, revision-checked Config transaction. Timing, pin and drive changes all require restart and latch inhibition through A/B/A saves. Saved values, immutable boot timing and a job's accepted timing remain distinct. Unrepresented timing survives all historical Config, station, pin and progress saves, including legacy replacement. Explicit timing saves set both values; reset domains follow the existing Config reset authority.

`capabilities.amplifier_timing` is the exact `transmitter-amplifier-timing/1` descriptor, with GET/PUT `/api/v1/amplifier-timing`. Its descriptor is independently versioned from `transmitter-amplifier-enable/1`, hardware/3 and WTP/1. A PUT contains exactly `schema`, the device/boot member `target`, and `timing:{lead_ms,tail_ms}`. GET adds `saved`, `boot_active`, `pending_restart`, `phase`, `output_active`, `rf_active` and `storage_healthy`, with the same target and a Config revision ETag. `phase` is `inactive`, `waiting`, `lead`, `rf`, `tail` or `fault`; `output_active` conservatively includes amplifier activity/uncertainty, while `rf_active` identifies the RF engine's running observation. Neither is an independent measurement of emitted RF or amplifier readiness.

Public reads retain the exact `pico-public-read/1` routes and document. The additional `/api/consumer/v1/read/2` selects the closed `pico-public-read/2` descriptor containing only `amplifier-timing`, with prefix `/api/consumer/v1/read/2/`. The browser explicitly selects this version for timing and retains exact version-1 validation for historical settings. Authenticated Consumer-Radio, engineering HTTPS and physically bound USB share the production handler. Unsupported descriptors, versions, fields, bounds and identity/revision bindings refuse before writes; the Pi validates carrier/profile authority and saved readback as well.

Nondefault timing is a sparse `amplifier_timing` Config extension in the existing CRC journal; omitted timing reconstructs 200/200 ms. Default records retain their prior canonical bytes. Firmware lacking the extension rejects nondefault records under the existing fail-closed journal authority; restore default timing with supporting firmware before rollback. Older firmware's immediate timing differs from the new default. No record restores an energized interval on reboot, and no flash address/capacity changes.

ARM must arrive with at least lead plus 2 ms of monotonic preparation headroom, in addition to existing admission rules. WTP CAPS advertises that immutable boot minimum through its existing `minimum_arm_lead_ns`; Pi scheduling consumes the same bound. Activation is scheduled 1 ms before the minimum lead boundary, leaving bounded alarm/write slack; an activation callback more than 1 ms late cannot shorten the configured settling interval. Checked readback completion starts the minimum lead measurement. Both activation and RF launch revalidate the UTC projection and safety latch. RF launch also rechecks the amplifier pad/function/direction without rewriting the output; a changed pad cannot be reasserted and mistaken for a completed settling interval. An earlier clock refinement that would shorten settling fails safely; a later projection preserves the requested UTC onset under the existing WTP start-window rules. Immediate submissions still need an explicit admissible future RF start. No delay silently moves RF onset, inserts RF samples, changes keyed gaps or extends the encoded job's duration.

Hardware deadlines use the monotonic microsecond timer, with nanosecond arithmetic checked before rounding or addition. Lead/tail values have 1 ms resolution; RF start rounding remains upward to the existing 1 µs timer resolution. Lead is a minimum; the deliberate activation margin and interrupt latency may lengthen it. Tail begins at confirmed RF-off observation and may lengthen with timer/worker latency. The physical acceptance record identifies measured GPIO timing; amplifier readiness remains unqualified. IRQ paths neither sleep nor allocate, log, access network/storage or wait for another core.

During lead the job remains armed; during normal tail it retains running/ownership and reports RF inactive. Completion becomes terminal only after verified amplifier deassertion and cleanup. The unchanged 100 µs RF completion acknowledgement allowance is budgeted separately from the configured tail, and complete-job ceilings still bound only the unchanged encoded waveform. Separate jobs, including Type 2/3 frames, always deactivate between intervals; insufficient preparation or ownership time rejects/skips the next job rather than combining intervals. STOP, ABORT, reset, shutdown, maintenance, inhibition, rejected launch and faults cancel all pending intervals and immediately attempt safe output before fallible DMA cleanup. Transport loss retains the existing armed/running finite-job lease extension.

LPF adapters remain unavailable, so timing introduces no filter dependency. Console INFO exposes the last admitted job as the independently versioned `amplifier-readback/1` object: epoch, effective policy, configured state, normal-completion flag and nullable monotonic timestamps for checked enable, RF launch, checked RF-inactive and checked disable. Values are sampled after GPIO/function/direction readback or the physical PIO launch boundary, retain the last job after RELEASE and reset on a newly admitted ARM or boot. Disabled configuration produces no enable/disable timestamps. This board readback establishes commanded GPIO state and local timing; it does not establish external amplifier readiness, power or independently measured RF silence. Host and source-pair fixtures remain software evidence only.
