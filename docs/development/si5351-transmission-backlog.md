# Si5351 transmission backlog

Recorded: 2026-10-03. Status: selected future feature; implementation deferred.
Roadmap assignment: **Phase 13 / P13.2**, selected on 2026-10-05; see the
[feature backlog](../implementation-plan.md#phase-13-feature-backlog).
Final hardware/release qualification follows in Phase 14.
The user requested backlog/documentation/memory only. This entry does not
authorize firmware implementation, hardware control or RF output.

Implement transmissions through an external Si5351 as an interchangeable Pico
RF engine, usable by standalone operation and WsprryPi/backend jobs through
the existing shared job service. Complete jobs and symbol timing remain local
to RP2350; no per-symbol USB or network delivery dependency is permitted.

Current [application contract](../transmitter-application-contract.md) records
Si5351 as unimplemented on Pico. Keep its capabilities unavailable until the
engine and applicable acceptance checks exist. No bands, modes, timing accuracy
or RF performance are qualified by this backlog entry.

## Deferred implementation and acceptance

- Recheck source and exact provenance before reusing a driver; preserve licenses
  and keep portable planning separate from Pico SDK/I²C adapters.
- Preserve the [pin-assignment contract](../pin-assignment-contract.md): select
  exactly one approved SDA/SCL pair atomically, with exclusive role ownership
  and no simultaneously allocated direct RF-output GPIO.
- Define supported device/reference, bus/address, RF clock output, drive level
  and calibration settings. Validate electrical compatibility and reserve
  unsupported choices as unavailable. Exact defaults remain open.
- Implement local preparation, frequency/symbol updates, output enable/disable,
  completion and stop/abort/failure cleanup under the existing execution owner.
  Handle I²C failures and unconfirmed output shutdown explicitly; never claim
  inactivity solely because a disable write was attempted.
- Apply the [solid transmit LED requirement](transmit-led-backlog.md) whenever
  this engine is hot, including RF-producing warmup and cleanup intervals.
- Add hardware-free behavior/failure checks and the pinned Pico cross-build;
  then separately authorize inhibited target integration and conducted RF
  verification. Verify update timing/transients, frequency accuracy, supported
  mode/band combinations and shutdown using independent evidence. Record exact
  board, firmware, Si5351/reference, bus, output, drive, mode, clock, RF path and
  restoration state. Host tests and cross-linking do not qualify RF behavior.

This selects the future engine feature; detailed hardware choices and supported
capabilities remain to be established in a bounded implementation tranche.
