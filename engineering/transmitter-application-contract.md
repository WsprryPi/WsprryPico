# Transmitter members and controllers

WsprryPico operates as a standalone transmitter and a WsprryPi backend. Each
member owns its hardware, admission, execution timing, cleanup, ownership, and
persistence. The controller configures supported resources and submits complete
finite jobs. Pico targets Pico 2 W / RP2350; Pi-specific Linux services, RP1,
and DKMS hardware adapters stay on Pi.

## Shared application resources

The [control contract](browser-api.md) and [canonical schema](protocol/control-1.schema.json)
define `Wsprry-Control/1` under `/api/control/v1`. Application, station, hardware,
progress, and settings updates use one current representation. Pi consumes that
representation through its production management adapters. Full application
parity and physical fleet interoperability are not claimed.

Application state binds device and boot identity and composes station, hardware,
recurrence, capabilities, and WSPR planning observations. Station supports
Type 1/2/3 planning. Hardware includes pin roles, amplifier enable and polarity,
and GPIO drive, with distinct saved and boot-active values. Amplifier timing
and filter settings retain their authoritative domain resources. Aggregate
readback does not combine separate journals or profile transactions into one
atomic write.

Updates preserve omitted settings, validate the complete candidate, and require
exact device/boot/profile bindings, the current contract, and If-Match revision.
Drafts require explicit application. Uncertain writes require authoritative
readback and review before another save. Unknown output, storage faults,
nullable readback, and pending restart remain explicit. Hardware changes latch
restart and output inhibition through A/B/A saves. Settings authority grants no
transmitter ownership.

## Recurrence and execution

A schedule has one recurrence authority. Controller-owned recurrence compiles
and submits each complete job through WTP. It does not implicitly enable the
member's saved schedule. Member-owned recurrence uses local saved settings and
submits complete jobs through the same JobService as remote work. Pico's
standalone `enabled` and Pi's local transmit reservation have distinct meanings;
an idle interval does not establish availability for another owner.

Individual jobs fit the member's advertised limits even when recurrence has no
expiry. Packet arrival never determines symbol boundaries. Lease expiry while
loaded aborts the unarmed job and relinquishes ownership. Armed or running
jobs retain the finite-job terminal extension. Controller loss does not prove
inactive output, select another endpoint, replay work, or start a replacement
schedule. Uncertain outcomes require reconciliation. Durable controller/member
schedule transfer is unavailable; selected work is in the
[TODO list](development/consolidated-backlog.md#possible-future-work).

## Hardware and RF authority

The implemented Pico engine is PIO/DMA. Its build-selected clock and numerical
limits are defined by [clock support](development/clock-support.md). Si5351 is
unavailable on Pico. Pi engine identifiers, resources, and limits do not apply
to Pico. GPIO assignments use device-specific numbering and exclusive roles
under the [pin contract](pin-assignment-contract.md).

Pico supports manual RF correction, GPIO drive, optional amplifier enable and
[timing](development/amplifier-enable.md), and [LPF/band selection](development/lpf-band-selector.md).
WSPR reported dBm is message content; it is independent of pad drive and does
not measure antenna power. UTC discipline and RF correction remain separate.
A controller's clock estimate does not calibrate its member.

Required filter selection covers every nominal and programmed RF-on frequency
in the complete job with one selector. Local preparation clamps RF, confirms
amplifier inactivity, deactivates selectors, waits the configured relay interval,
selects the filter, and allows settling before amplifier lead. RF executes in
the scheduled window; normal amplifier tail precedes selector cleanup. Abort,
missed launch, reset, and faults use the same local cleanup authority. Attempted
writes and GPIO readback do not prove relay position, amplifier readiness, or
RF silence. Unconfirmed cleanup inhibits reuse.

## Transport boundaries

[WTP/1](protocol/WTP.md) carries complete `rf-events/1` jobs. Its closed objects
contain no hardware settings, arbitrary filter identifiers, or envelope events.
CAPS reports the selected engine and execution limits; JSON management advertises
supported configuration functions independently.

USB CDC is the reference WTP carrier; network WTP/TCP carries the same stream.
An available job carrier does not imply a management carrier. The
[management carrier contract](development/management-carriers.md) defines
engineering mTLS HTTPS, authenticated consumer station/AP control, and local
USB management through UMP1. All use the same current management shape with
explicit selected-carrier and device/boot/profile bindings. Plain LAN WTP,
TLS-WTP, and BLE do not carry shared JSON administration. Dedicated provisioning
retains its separate authority. No fallback carrier or older control view is
selected to make an unsupported request succeed.

## Validation boundaries

Both production Pi/Pico network and USB source-pair suites are required for
coordinated control changes. The [development guide](development/README.md#production-pipico-source-pair-checks)
defines the checked-in recipes, explicit candidate selection, dependency pins,
and reporting requirements.

Host tests, cross-linking, physical device observations, and conducted RF
measurements establish different things. Physical claims require the exact
board, source/image, engine, clock, mode, pins, amplifier/filter state,
receiver/reference, and RF path. Software checks and numerical capabilities do
not qualify target timing, electrical behavior, filtering, or RF output.
