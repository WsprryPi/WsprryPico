# Si5351 engine design reference

Recorded: 2026-10-03. Updated: 2026-10-17.

These constraints describe the optional external-engine design. They do not
select implementation or qualify an engine. Current work selection is recorded
only in the [Consolidated backlog](consolidated-backlog.md).

An external Si5351 engine would serve standalone and WsprryPi-controlled jobs
through the existing shared job service. Complete jobs and symbol timing remain
local to RP2350, independent of per-symbol USB or network delivery. The
[application contract](../transmitter-application-contract.md) describes the
engine boundary; unavailable capabilities must remain advertised as unavailable.

The [pin-assignment contract](../pin-assignment-contract.md) requires exactly
one approved SDA/SCL pair, allocated atomically with exclusive role ownership
and no simultaneously allocated direct RF-output GPIO. Device/reference,
bus/address, RF clock output, drive level and calibration settings require
explicit validation; this reference establishes no defaults or electrical
compatibility claims.

Preparation, frequency/symbol updates, output enable/disable and terminal
cleanup belong to the existing execution owner. I²C failure or unconfirmed
shutdown cannot be reported as confirmed inactivity merely because a disable
write was attempted. The [TX LED requirements](transmit-led-requirements.md)
apply throughout RF-producing warmup, transmission and cleanup.

Any reused driver requires exact source provenance and preserved licenses.
Portable planning remains separate from Pico SDK/I²C adapters. Host checks and
cross-linking cannot qualify target timing or RF behavior. Physical evidence
must identify the board, firmware, Si5351/reference, bus, output, drive, mode,
clock, RF path and restoration state. No supported band, mode, timing accuracy
or RF performance is established by this design reference.
