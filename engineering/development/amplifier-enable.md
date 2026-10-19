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
