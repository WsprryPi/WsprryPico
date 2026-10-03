# Pico 2 W pin-assignment contract

Status: selected design contract, documentation only, agreed 2026-10-01.
The [pin allocation feature](development/pin-allocation.md) implements boot-applied
direct RF, active-low switch and indicator selection plus candidate allocation
validation. Amplifier/LPF adapters and Pico Si5351 support remain unimplemented. Hardware eligibility is not RF qualification.

## Target and numbering

The target is Raspberry Pi Pico 2 W / RP2350. Configuration uses Pico GPIO
numbers, such as GP2. Physical header numbers are wiring aids and must not be
accepted interchangeably with GPIO numbers.

The external assignment set is **GP0–GP22 and GP26–GP28**. Each can serve as a
PIO waveform output, digital input or digital output, subject to implemented
engine support and exclusive allocation. GP26–GP28 also support ADC; any future
ADC use must participate in the same exclusive allocation model.

GP23–GP25 and GP29 are reserved for onboard functions. Power, ground, RUN,
BOOTSEL, USB and SWD connections are outside the application assignment model.

## Exactly one RF engine allocation

Every valid transmitter configuration must select exactly one RF engine and
exactly one of the following resource allocations:

| Engine family | Required allocation | Forbidden allocation |
| --- | --- | --- |
| Direct GPIO/PIO generation | One and only one RF-output GPIO | Any I²C pair |
| I²C-controlled generation | One and only one approved SDA/SCL pair | Any direct RF-output GPIO |

Both allocations, neither allocation, multiple direct RF outputs and multiple
I²C pairs are invalid. Disabling transmission does not remove this configuration
invariant. There is no independently enabled auxiliary I²C bus in this contract.

I²C controls an external RF generator; RF is emitted from that generator's
selected output, not SDA or SCL. That output and the device address belong to
engine configuration. Unsupported engines or assignments must remain
unavailable; documentation selection does not make them implemented capabilities.

## Application roles and defaults

| Role | Resource | Default |
| --- | --- | --- |
| Direct RF output | Exactly one external GPIO when the direct engine is selected | GP2, direct GPIO/PIO engine |
| I²C RF control | Exactly one approved pair when the I²C engine is selected | Unallocated with the direct engine |
| Switch/button input | Optional single external GPIO | GP14, active-low |
| Amplifier enable | Optional single external GPIO | Disabled |
| LPF selectors | Optional set of distinct external GPIO outputs | Disabled |
| TX indicator | Onboard LED, optional single external GPIO, or disabled | Onboard LED |

The GP14 default preserves the selected local button wiring. Its application
reset/stop/setup gestures are governed by the existing button contract; this
contract does not redefine them. Making the input configurable requires adapter
implementation and affected validation.

## Exclusive ownership and lockouts

Each allocated external GPIO must have exactly one owner. RF, switch,
amplifier, LPF, external indicator and I²C allocations must never overlap.
Selecting an I²C pair reserves both GPIOs together. Disabled optional roles
reserve no resources.

Each LPF selector owns its GPIO once. Multiple bands may refer to the same named
filter/selector resource; they must not create duplicate pin allocations or
independent owners. Conflicting polarity or inactive-state definitions are
invalid.

The interface must make allocated pins unavailable to other roles and identify
the current owner. An I²C pair is unavailable if either GPIO is owned elsewhere.
Firmware must independently enforce these rules for every configuration entry
path, including local, remote and persisted configuration. UI lockouts alone are
insufficient. Invalid saved assignments must inhibit RF admission and report the
error rather than silently substitute pins.

Configuration validation is atomic: reject the entire invalid replacement,
report the conflicting roles, and retain the existing valid configuration. An
assignment change releases old reservations only when its complete replacement
is accepted. Engine changes replace the old RF allocation with the new allocation
in that same transaction; the final allocation is checked without treating the
replaced role as a competing owner.

## Fixed I²C pair choices

The operator selects a complete pair. The selection determines the controller;
SDA and SCL are not independently selectable. Only these pairs are allowed:

| Choice | Controller | SDA | SCL | Physical header pins: SDA / SCL |
| --- | --- | --- | --- | --- |
| GP0/GP1 | I²C0 | GP0 | GP1 | 1 / 2 |
| GP4/GP5 | I²C0 | GP4 | GP5 | 6 / 7 |
| GP8/GP9 | I²C0 | GP8 | GP9 | 11 / 12 |
| GP12/GP13 | I²C0 | GP12 | GP13 | 16 / 17 |
| GP16/GP17 | I²C0 | GP16 | GP17 | 21 / 22 |
| GP20/GP21 | I²C0 | GP20 | GP21 | 26 / 27 |
| GP2/GP3 | I²C1 | GP2 | GP3 | 4 / 5 |
| GP6/GP7 | I²C1 | GP6 | GP7 | 9 / 10 |
| GP10/GP11 | I²C1 | GP10 | GP11 | 14 / 15 |
| GP14/GP15 | I²C1 | GP14 | GP15 | 19 / 20 |
| GP18/GP19 | I²C1 | GP18 | GP19 | 24 / 25 |
| GP26/GP27 | I²C1 | GP26 | GP27 | 31 / 32 |

GP22 and GP28 are excluded from these fixed pair choices because their adjacent
SCL options are board-reserved. They remain eligible for the other roles. The
hardware permits some nonadjacent SDA/SCL combinations; this contract deliberately
offers only the listed fixed pairs. Software/PIO-emulated I²C is outside scope.

The bus declares a supported speed and engine device address. Compatible devices
may share the single selected bus with distinct addresses and compatible wiring,
pull-ups and voltage levels; they share the bus resource, not independent GPIO
ownership. Additional device adapters are not implemented by this contract.

## TX indicator

Exactly one indicator selection is active:

- **Onboard LED:** default; uses the CYW43439 LED resource and consumes no exposed
  RP2350 GPIO.
- **External GPIO:** reserves one eligible GPIO with configurable active polarity.
- **Disabled:** reserves no resource.

The onboard resource must be identified explicitly, for example `onboard_led`,
never as GP0. Its SDK identity is `CYW43_WL_GPIO_LED_PIN`; it is controlled through
the wireless-chip API. Any other LED behavior must use the same indicator owner
rather than compete for the onboard resource.

The TX indication follows the application's RF-active state. It is not an
independent measurement of RF emission.

## Electrical state and local execution

The switch declares active level, pull-up/pull-down/external bias and debounce
policy. Its action is distinct from its electrical assignment.

Amplifier, LPF and external indicator outputs declare active polarity. Active-high
means high when active and low when inactive; active-low means low when active
and high when inactive. External interfaces must accept 3.3 V logic or provide
suitable buffering, level conversion or relay drivers. External bias establishes
required startup/reset/unpowered states; software does not guarantee driven
levels throughout those conditions. I²C requires compatible pull-ups and voltage.

Assignments may change only while the member is idle, unowned, RF-inactive and
nonfaulted, with configuration revision validation. The member owns the complete
local RF chain and must confirm RF/amplifier disabled, select and settle the
filter, prepare the engine, apply amplifier lead timing, execute the finite job,
stop RF, apply amplifier tail timing and restore declared inactive states.
Completion, cancellation and faults use the same cleanup authority. Unconfirmed
cleanup blocks another transmission. Pin assignment does not authorize output.

## Implementation and validation boundary

This is the selected target design. The feature guide above records its current
implemented subset and pending restart behavior.
Exact schema names, configuration migration, drive settings, bus speeds, filter
circuits and settling/lead/tail values remain separate implementation decisions.
These settings belong to the member management API, not WTP/1.

Future implementation must verify valid choices, each overlap class, engine
exclusivity, pair completeness, atomic replacement, saved-config rejection and
indicator selection with deterministic hardware-free checks. Opt-in target
validation must identify board, firmware, engine, clock, pins and physical setup;
RF qualification is separately scoped. No hardware operations are authorized by
this document.

## References

- [Application architecture](architecture.md).
- [PIO output adapter](../src/rf/pico/pico_pio_dma.hpp).
- [Pico 2 W datasheet](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf),
  especially board-reserved GPIO and the wireless-chip LED.
- [Pico 2 W pinout](https://pip-assets.raspberrypi.com/categories/1088-raspberry-pi-pico-2-w/documents/RP-008305-DS-1-pico-2-w-pinout.pdf).
- [RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf),
  GPIO function selection and I²C controller mappings.
