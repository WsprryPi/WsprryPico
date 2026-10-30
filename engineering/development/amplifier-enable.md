# Amplifier enable

## Configuration and compatible management

`PinPlan.amplifier` reuses `amplifier_gp`: null disables it, and eligible pins remain GP0–GP22/GP26–GP28 with exclusive ownership across RF, button, indicator, LPF and both I²C pins. `amplifier_active_high` is a separate boolean with true default. It never derives from indicator polarity. I²C RF remains operationally unavailable; optional [LPF selection](lpf-band-selector.md) has its own complete settings resource. No pin is hard-coded or selected by fallback.

Default Config bytes and legacy pin serialization remain unchanged. Nondefault active-low storage includes `amplifier_active_high:false`; configured amplifier pins and nondefault polarity require supporting firmware. Invalid/unsupported saved records fail closed without resurrecting earlier records or enabling a default route. An older image must not be loaded over these settings without first restoring a compatible complete default plan and removing incompatible progress with supported reset/recovery. Flash addresses and journal capacities are unchanged. This is a firmware rollback boundary, not automatic migration.

`capabilities.amplifier_enable` is a closed `amplifier-enable` descriptor within
`Wsprry-Control/1`. It identifies the current settings routes:

| Route | Resource and behavior |
| --- | --- |
| GET `pins`, POST `pins/validate` | Pin choices, effective polarity and nonmutating candidate review |
| GET/PUT `hardware` | Saved and immutable boot pins, restart/error/storage state and nested GPIO drive |
| GET `application` | Station, hardware, recurrence and Type 1/2/3 plan |
| GET `config`, POST `config/update` | Redacted configuration readback and atomic merge updates |
| GET `progress`, POST `progress/update`, POST `progress/apply` | Independent drafts and explicit application by domain |

All logical routes use `/api/control/v1/`. Root documents carry
`contract:"Wsprry-Control/1"`; nested resources use stable schema discriminators.
Mutations require the current target and revision as well as carrier authority.
Engineering station, authenticated field, Consumer-Radio and physically bound USB
share the current resource shapes. Field routes retain Configure classification
and preclock refusal. WTP/1, Field-GATT and USB management framing remain independent.

Ordinary omitted fields preserve amplifier GPIO and polarity. Complete pin saves
with omitted polarity preserve its saved value. There are no historical control
views or replacement-mode updates. Progress retains its independent stored-record
format: omitted draft polarity preserves a prior draft, otherwise applied polarity,
otherwise true. Invalid pins or polarity reject the complete batch before sibling
saves, receipts or revisions. A true-default pin draft is made explicit during
application so it can change a saved active-low output back to active-high.

The Pi general settings coordinator consumes the complete amplifier-aware hardware
and progress resources, including amplifier GPIO and active polarity. Pi and Pico
pin editors use the same current contract; amplifier timing retains its separate
supported resource and application path.

Settings are saved only while idle, unowned, inactive and nonfaulted under the existing target/revision admission. Saving never programs a GPIO. Changed pins or polarity latch output inhibition/restart for the boot, including A/B/A; unrelated saves and draft reversion cannot clear it. The active plan remains immutable. The existing pin editor adds only enable pin/polarity and uses exact capability negotiation, overlap lockouts and saved-versus-active readback.

## Local launch, cleanup and failure ownership

Portable `AmplifierEnable` uses a narrow checked `EnableOutput` adapter. Disabled configuration has no output adapter, no GPIO access and no artificial launch acknowledgement. Core 0 initializes a healthy, validated boot output inactive, then transfers the policy to the RF core before job/service calls. Pinned SDK `gpio_init` sets input direction, clears the SIO latch and selects SIO; the adapter preloads the declared inactive level before setting output direction. Both polarities are checked. External bias remains responsible for reset, boot ROM, unpowered periods and states software cannot control.

Every job producer enters the same JobService, StreamEngine and PIO/DMA sink. LOAD renders/prepares without asserting enable. The admitted ARM wait keeps it inactive until the configured lead interval. The final driver launch checks clock/epoch/ownership admission, safety, indicator acknowledgement, FIFO, deadline and RF drive, then asserts enable before RF: a configured nonzero lead uses its own local alarm, while zero lead asserts immediately before enabling physical RF. The driver rechecks deadline and safety after the write and safety after enabling PIO. The IRQ path does no network/CYW43, allocation, logging, storage or waiting for another core. Existing local timer bounds and the renderer/refill authority remain unchanged.

One interval covers a finite job including its keyed gaps. Separate jobs, including each frame of a Type 2/3 pair, deassert between them. Configurable RF-off lead and tail surround each job. Drive regulation and RF warmup remain unavailable.

Emergency cleanup clamps RF, attempts enable deassertion, then enters fallible DMA halt waits. Normal completion may retain enable through its bounded RF-off tail before the same cleanup. It covers normal hardware tail completion, delayed tail IRQ, stop/abort, lease-driven actual termination, missed/rejected launch, partial/no-open state, DMA faults and repeated disable/rearm. Neither a halt failure nor an early resource failure can skip the enable attempt. Register/pad mismatch leaves output active-or-unknown, retains failed state/ownership and blocks admission. An issued command alone does not prove success. Armed/running lease expiry continues its finite job until terminal state, as before; transport disconnect does not add an independent cancellation policy.

Missing-worker/nonreturning fault recovery first latches inhibition, forces RF OUTOVER low and OEOVER disabled, then forces amplifier OUTOVER inactive before watchdog recovery. These overrides prevent late SIO writes/final launch from undoing the emergency state. Recovery does not report verified physical shutdown or release ownership. Inhibited firmware initializes inactive but never passes the output to its simulator and links no physical RF worker.

## Lead and tail timing

Lead is the minimum amplifier-enabled, RF-off settling interval before a job's scheduled RF onset. Tail is an amplifier-enabled, RF-off interval after the zero-data DMA stop has confirmed normal RF completion. Both default to **200 ms** and accept **0–1000 whole milliseconds**, independently. Zero removes that interval. There is no separate settling value to add twice. The two configured intervals total at most two seconds; the activation margin and timer/worker latency also occupy the RF chain. The 1000 ms lead ceiling fits the existing minimum two-second standalone WSPR preparation interval. It is a software policy bound, not a measured amplifier requirement. Disabled amplifier configuration uses neither delay and performs no enable GPIO access.

The Pico's Radio pins section places timing beside the amplifier pin/polarity controls. WsprryPi's selected-member hardware section also exposes amplifier pin and polarity, with timing through its dedicated settings path. Both editors retain existing form styling and native number controls, with explicit read, save and discard actions. Reads, failed saves and target changes preserve unsaved entries; using preserved entries for a different Pico or boot requires the explicit “Use entries for this Pico” action. Discard restores the last-read saved values. Readback separates saved timing, active timing for this boot, phase at readback and pending restart. Saving never toggles an output. Timing uses the existing idle, unowned, inactive, nonfaulted, revision-checked Config transaction. Timing, pin and drive changes all require restart and latch inhibition through A/B/A saves. Saved values, immutable boot timing and a job's accepted timing remain distinct. Unrepresented timing survives ordinary configuration merges, station, pin and progress saves. Explicit timing saves set both values; reset domains follow the existing Config reset authority.

`capabilities.amplifier_timing` is the exact `amplifier-timing` descriptor, with GET/PUT `/api/control/v1/amplifier-timing`. Its descriptor belongs to the same `Wsprry-Control/1` contract as amplifier enable and hardware; WTP/1 remains independent. A PUT contains exactly `contract`, `schema`, the device/boot member `target`, and `timing:{lead_ms,tail_ms}`. GET adds `saved`, `boot_active`, `pending_restart`, `phase`, `output_active`, `rf_active` and `storage_healthy`, with the same target and a Config revision ETag. `phase` is `inactive`, `waiting`, `lead`, `rf`, `tail` or `fault`; `output_active` conservatively includes amplifier activity/uncertainty, while `rf_active` identifies the RF engine's running observation. Neither is an independent measurement of emitted RF or amplifier readiness.

Public discovery uses GET `/api/consumer/v1/read` with the current `public-read`
descriptor and aggregate resource catalog. Its `/api/consumer/v1/read/` prefix
includes amplifier timing. Authenticated Consumer-Radio, engineering HTTPS and
physically bound USB share the production handler. Unsupported contracts,
descriptors, fields, bounds and identity/revision bindings refuse before writes;
the Pi validates carrier/profile authority and saved readback as well.

Nondefault timing is a sparse `amplifier_timing` Config extension in the existing CRC journal; omitted timing reconstructs 200/200 ms. Default records retain their prior canonical bytes. Firmware lacking the extension rejects nondefault records under the existing fail-closed journal authority; restore default timing with supporting firmware before rollback. Older firmware's immediate timing differs from the new default. No record restores an energized interval on reboot, and no flash address/capacity changes.

ARM must arrive with at least lead plus 2 ms of monotonic preparation headroom, in addition to existing admission rules. WTP CAPS advertises that immutable boot minimum through its existing `minimum_arm_lead_ns`; Pi scheduling consumes the same bound. Activation is scheduled 1 ms before the minimum lead boundary, leaving bounded alarm/write slack; an activation callback more than 1 ms late cannot shorten the configured settling interval. Checked readback completion starts the minimum lead measurement. Both activation and RF launch revalidate the UTC projection and safety latch. RF launch also rechecks the amplifier pad/function/direction without rewriting the output; a changed pad cannot be reasserted and mistaken for a completed settling interval. An earlier clock refinement that would shorten settling fails safely; a later projection preserves the requested UTC onset under the existing WTP start-window rules. Immediate submissions still need an explicit admissible future RF start. No delay silently moves RF onset, inserts RF samples, changes keyed gaps or extends the encoded job's duration.

Hardware deadlines use the monotonic microsecond timer, with nanosecond arithmetic checked before rounding or addition. Lead/tail values have 1 ms resolution; RF start rounding remains upward to the existing 1 µs timer resolution. Lead is a minimum; the deliberate activation margin and interrupt latency may lengthen it. Tail begins at confirmed RF-off observation and may lengthen with timer/worker latency. The physical acceptance record identifies measured GPIO timing; amplifier readiness remains unqualified. IRQ paths neither sleep nor allocate, log, access network/storage or wait for another core.

During lead the job remains armed; during normal tail it retains running/ownership and reports RF inactive. Completion becomes terminal only after verified amplifier deassertion and cleanup. The unchanged 100 µs RF completion acknowledgement allowance applies while RF completion is unconfirmed. A verified normal tail carries its own monotonic deadline from the actual RF-off observation through the sink, worker and service; a late IRQ observation cannot consume that dwell or trigger a nominal-end watchdog fault. The service bounds the reported deadline to the immutable tail policy and retains ownership through checked deassertion. Complete-job ceilings still bound only the unchanged encoded waveform. Separate jobs, including Type 2/3 frames, always deactivate between intervals; insufficient preparation or ownership time rejects/skips the next job rather than combining intervals. STOP, ABORT, reset, shutdown, maintenance, inhibition, rejected launch and faults cancel all pending intervals and immediately attempt safe output before fallible DMA cleanup. Transport loss retains the existing armed/running finite-job lease extension.

When [LPF selection](lpf-band-selector.md) is required, its release and settling complete before amplifier lead begins; selection remains active through amplifier tail and releases after amplifier disable. The two timing policies remain independent. Console INFO exposes the last admitted job as the `amplifier-readback` object: epoch, effective policy, configured state, normal-completion flag and nullable monotonic timestamps for checked enable, RF launch, checked RF-inactive and checked disable. Values are sampled after GPIO/function/direction readback or the physical PIO launch boundary, retain the last job after RELEASE and reset on a newly admitted ARM or boot. Disabled configuration produces no enable/disable timestamps. This board readback establishes commanded GPIO state and local timing; it does not establish external amplifier readiness, power or independently measured RF silence. Host and source-pair fixtures remain software evidence only.

## Validation and applicability

The maintained amplifier, PIO/DMA, worker and core tests cover both polarities, blank/corrupt settings, immutable boot policy, clock refinement, late preparation, cancellation, readback failure and deassertion before fallible DMA cleanup. The target-derived delayed-RF-off regression preserves the actual RF-off-anchored tail deadline; the existing unconfirmed-RF acknowledgement rule remains unchanged. Descriptor/schema/browser tests cover the current control contract, rejection of unsupported control versions, exact target/revision checks and saved/boot consistency. Both production network and USB source-pair suites are required when those interfaces change; see the [development guide](README.md).

Recorded software and GPIO timing acceptance is bound to Pico `14cbb5d465c6df489a3a8088ecb97339df4b4b2e` and Pi `e8d10e11c155cfbb4f441e39ae2e42f5f7e08915`, with SDK 2.3.1 and Arm GCC 15.3.1. The exact normal-image UF2 SHA-256 is `a67e11df51d67a6e9cdc8ea257033dee7de09224616162db05544b1fb2022c3d`. The software pair has [Pico](https://github.com/WsprryPi/WsprryPico/actions/runs/40790651718) and [Pi](https://github.com/WsprryPi/WsprryPi/actions/runs/40790757171) CI receipts. These results do not qualify later source revisions automatically.

The GPIO scope is Pico A, serial `0BF4B4AEC9FFB344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`, normal 138 MHz PIO/DMA firmware, GP17 as a temporary enable/LED fixture and no attached amplifier. Finite 600 ms tone and keyed QRSS jobs use 14.097100 MHz; GP2 feeds a 20 dB attenuator, combiner and 40 dB attenuation to RSP1B `2404058C60` on wspr5, without an antenna. Readback comes from checked GPIO/function/direction observations and the local PIO launch boundary. Accepted lead intervals are at least the configured value with at most 2 ms observation excess; normal tail and launch-to-verified-off observations allow 1 ms observer latency. Zero/default/maximum intervals, both polarities, late ARM, lead/tail abort, disabled enable and consecutive jobs are within this scope. The encoded 600 ms sample budget remains unchanged. These are commanded GPIO/timing observations, not external amplifier readiness, independently measured RF silence, RF power or a 100 µs jitter guarantee. Capacity under combined full-diagnostic/reply-cache pressure remains unqualified.

Recovery for that image uses the exact developer bundle at `build/amplifier-hardware/timed-bundle` or `/home/pi/amplifier-timing-20261028-e88fa03/timed-bundle` on wspr5 and its same-board installer reference. Those artifacts remain protected until their present recovery duty is checked. The recorded restoration has amplifier enable disabled, GP17 restored as the active-high indicator, saved/boot timing 200/200 ms, inactive outputs and no owned job. It does not describe the board's present state without fresh readback.
