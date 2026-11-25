# Transmitter members and controllers

WsprryPico operates as a standalone transmitter managed locally or through WsprryPi. Each member owns its hardware, admission, execution timing, cleanup, ownership, and persistence. A controller configures supported resources on the selected member. Pico targets Pico 2 W / RP2350. Pi-specific Linux services, RP1, and DKMS hardware adapters stay on Pi.

## Shared application resources

The [control contract](browser-api.md) and [canonical schema](protocol/control-1.schema.json) define `Wsprry-Control/1` under `/api/control/v1`. Application, station, hardware, progress, and settings updates use one current representation. Pi consumes that representation through its production management adapters. Full application parity and physical fleet interoperability are not claimed.

Application state binds device and boot identity and composes station, hardware, recurrence, capabilities, and WSPR planning observations. Station supports Type 1/2/3 planning. Hardware includes pin roles, amplifier enable and polarity, and GPIO drive, with distinct saved and boot-active values. Amplifier timing and filter settings retain their authoritative domain resources. Aggregate readback does not combine separate journals or profile transactions into one atomic write.

Updates preserve omitted settings, validate the complete candidate, and require exact device/boot/profile bindings, the current contract, and If-Match revision. Drafts require explicit application. Uncertain writes require authoritative readback and review before another save. Unknown output, storage faults, nullable readback, and pending restart remain explicit. Hardware changes latch restart and output inhibition through A/B/A saves. Settings authority grants no transmitter ownership.

## Recurrence and execution

A schedule has one recurrence authority. The device with the saved schedule compiles and runs its complete jobs on its local transmitter. Managing a schedule on another device preserves that device's admission and explicit enablement. Pico's standalone `enabled` and Pi's local transmit reservation have distinct meanings. An idle interval does not establish availability for another owner.

Individual jobs fit the member's advertised limits even when recurrence has no expiry. Packet arrival never determines symbol boundaries. Lease expiry while loaded aborts the unarmed job and relinquishes ownership. Armed or running jobs retain the finite-job terminal extension. Controller loss does not prove inactive output, select another endpoint, replay work, or start a replacement schedule. Uncertain outcomes require reconciliation. Durable controller/member schedule transfer is unavailable; advanced scheduling is handled by WsprryPi.

## Hardware and RF authority

Pico direct GPIO uses PIO/DMA. Its build-selected clock and numerical limits are defined by [clock support](development/clock-support.md). Si5351 has separate settings and a qualified ordinary profile, with other profiles limited to engineering builds. See the [Si5351 evidence and limits](development/si5351.md). GPIO assignments use device-specific numbering and exclusive roles under the [pin contract](pin-assignment-contract.md).

Pico supports manual RF correction, GPIO drive, optional amplifier enable and [timing](development/amplifier-enable.md), and [LPF/band selection](development/lpf-band-selector.md). WSPR reported dBm is message content; it is independent of pad drive and does not measure antenna power. UTC discipline and RF correction remain separate. A controller's clock estimate does not calibrate its member.

Required filter selection covers every nominal and programmed RF-on frequency in the complete job with one selector. Local preparation clamps RF, confirms amplifier inactivity, deactivates selectors, waits the configured relay interval, selects the filter, and allows settling before amplifier lead. RF executes in the scheduled window; normal amplifier tail precedes selector cleanup. Abort, missed launch, reset, and faults use the same local cleanup authority. Attempted writes and GPIO readback do not prove relay position, amplifier readiness, or RF silence. Unconfirmed cleanup inhibits reuse.

## Transport boundaries

[WTP/1](protocol/WTP.md) remains an independent format reference for complete `rf-events/1` jobs. Its closed objects contain no hardware settings, arbitrary filter identifiers, or envelope events. Its CAPS format is independent of the current management capability document.

The [management carrier contract](development/management-carriers.md) defines engineering mTLS HTTPS, authenticated consumer station/AP control, and local USB management through UMP1. All use the same current management shape with explicit selected-carrier and device/boot/profile bindings. Dedicated provisioning retains its separate authority. Current firmware has retired external WTP execution and refuses unsupported carriers and control versions.

## Validation boundaries

Both production Pi/Pico network and USB source-pair suites are required for coordinated control changes. The [development guide](development/README.md#production-pipico-source-pair-checks) defines the checked-in recipes, explicit candidate selection, dependency pins, and reporting requirements.

Host tests, cross-linking, physical device observations, and conducted RF measurements establish different things. Physical claims require the exact board, source/image, engine, clock, mode, pins, amplifier/filter state, receiver/reference, and RF path. Software checks and numerical capabilities do not qualify target timing, electrical behavior, filtering, or RF output.

## Pi device-owned recurrence

The shared Control/1 Pi scheduling capability reports `next_occurrence`. The Pi owns validation, explicit native enablement, complete-occurrence solar admission, progress, and runtime observations. `stored_only` is not a current activation value. This descriptor adds no Pico RF or scheduling feature.

Pi enable binds the complete saved candidate digest and revision after positive retirement/reconciliation. Disable admits no new recurrence and allows accepted complete work to drain; Stop remains a separate observed-output operation. Neither action changes the independent WTP transmission contract or adds a Pico master scheduling switch. Missing healthy target-local UTC/location holds new Pi solar occurrences. Saved/active revisions, observation age, selected tones, and bounded next-start forecasts remain distinct from output execution evidence. A known forecast includes a start; an unknown forecast has a null start.
