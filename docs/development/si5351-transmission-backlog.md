# Si5351 transmission backlog

Recorded: 2026-10-03. Updated: 2026-10-09. Status: conditional future feature;
implementation deferred.
Roadmap assignment: **Phase 13 / P13.2**, selected on 2026-10-05; see the
[feature backlog](../implementation-plan.md#phase-13-feature-backlog).
The original assignment placed final hardware/release qualification in Phase 14.
The active Phase 14 campaign covers the implemented PIO engine; any future
Si5351 implementation and qualification require a separately selected scope.
The operator clarified on 2026-10-09 that Si5351 is a possible future addition
depending on the GPIO RF testing underway. That conditional decision supersedes
the earlier unconditional feature selection, while retaining the historical
P13.2 assignment. The current investigation is
[GPIO timekeeping and calibration](gpio-time-calibration-plan.md): NTP filtering
and UTC discipline, then NTP-derived Pico calibration, then optional GPS/PPS.
Si5351 transmission and CLK2 feedback are outside that work.

The original request was backlog/documentation/memory only. This entry does not
authorize firmware implementation, hardware control or RF output.

If selected later, implement transmissions through an external Si5351 as an
interchangeable Pico RF engine, usable by standalone operation and WsprryPi/backend jobs through
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

This retains a conditional future engine proposal. It selects no implementation;
detailed hardware choices and supported capabilities remain to be established
if the operator selects a bounded implementation tranche after GPIO results.
