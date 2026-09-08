# Architecture baseline

Status: accepted architecture.

## Product and ownership

WsprryPico is a first-class standalone application, in its own repository, within the WsprryPi family. WsprryPi is not required for standalone operation. The same firmware must also support use as a WsprryPi hardware transmitter backend.

Target the Raspberry Pi Pico family, with Pico 2 W / RP2350 as the defined hardware target. This does not promise support for other Pico boards or RP2040.

Use WsprryPico for project, repository and application naming; firmware artifacts may be named WsprryPico-x.y.z.uf2.

## Transport and timing

- USB CDC serial is the canonical/reference control transport.
- Wi-Fi/TCP provides network control; Wi-Fi also supports the embedded web UI.
- BLE is primarily for provisioning and local management.
- SoftAP provides a provisioning fallback.
- All RF timing is local on RP2350. USB and network connections load and arm complete jobs; packet arrival never sets symbol boundaries.

Preserve WsprryPi encoder and scheduler concepts while adapting platform dependencies. RP1 DKMS, kernel interfaces and RP1 register programming are not ported.

## RF generation

The [RF feasibility study](rf-feasibility.md) selects PIO/DMA packed-bit GPIO
synthesis for experimental implementation, with Si5351 as an alternative.
No production engine or band range is qualified. The experimental driver fixes
GP2 and a build-selected 132, 138 or 150 MHz sample clock (138 MHz default); the standard firmware remains RF-inhibited. The
[portable stream library](development/rf-stream.md) implements planning, waveform
generation and an abstract-sink adapter separately from the firmware. The
[PIO/DMA sink and local timer launch](development/pio-dma-driver.md) are
implemented and integrated in the separate [RF bench](development/rf-bench.md).
That runner accepts finite relative-time tones, synthetic frames, portable Type 1
encoded WSPR messages and CPU benchmarks over a named Commands CDC interface. It provides neither a WTP endpoint nor UTC synchronization.
Bounded target results exist; calibrated timing and spectral validation remain pending.

## Browser UI

Reuse as much WsprryPi browser UI and UX as practical through a shared browser-facing JSON API. Pico firmware supplies lightweight HTTP handlers and static assets, not Apache/PHP. The browser API and WTP have distinct responsibilities but share application behavior and capability semantics.

## Protocol

WTP means WsprryPi Transmitter Protocol. It is device-neutral and versioned independently of firmware. WTP/1 is defined by the normative protocol contract.

The authoritative specification lives at docs/protocol/WTP.md in WsprryPico. WsprryPico is the reference implementation; implementation accidents do not define the protocol. WTP does not have a separate protocol repository.

## Internal boundary

Browser handlers, standalone scheduler, USB WTP and TCP WTP submit work to one application job service. That service owns validation, transmitter ownership and state. A local execution layer controls interchangeable RF engines. Time synchronization estimates UTC relative to a monotonic device clock; RF frequency calibration is tracked separately.

The portable frame parser and job service implement the transport-independent
part of this boundary. The Pico 2 W standard image runs that service with autonomous Wi-Fi SNTP and
an RF-inhibited local lifecycle simulator; boot time remains unsynchronized
until a usable observation arrives. Its dual CDC device separates
console diagnostics from WTP framing. The [USB adapter contract](development/usb-cdc.md)
defines bounded servicing and connection semantics; logging must never enter WTP.
The [strict WTP endpoint](development/wtp-endpoint.md) performs JSON validation,
request dispatch and ordered response/event transmission. The [standalone scheduler](development/standalone.md) now shares this service
with USB WTP and the [HTTPS browser API](browser-api.md). Optional TLS 1.3
network control uses certificate principals and ALPN dispatch above raw lwIP
callbacks. Core 0 retains application/USB/network/storage ownership. The physical
standalone image dedicates core 1 to the RF engine/sink/peripheral and local launch
interrupts, using a one-command synchronous ownership-transfer mailbox. Two TLS
contexts on core 0 allow a persistent WTP owner plus an independent HTTPS browser.
An independently owned UTC discipline copy ages on the RF core; idle-only flash
writes coordinate both cores using SDK lockout. See the
[11.2 ownership and acceptance record](development/phase11-2-review.md). USB, WTP/TCP, browser jobs and standalone
schedules retain one ownership and execution authority. Network control defaults
off; physical TLS/RF coexistence and production RF qualification remain open.

Standalone execution uses local Type 1 encoding, versioned persistent station
and schedule records, and Wi-Fi SNTP acquisition without WsprryPi. Host
operation accepts already encoded jobs. Both paths converge before engine
preparation. [Bounded physical validation](development/standalone-rf-power-validation.md)
now demonstrates recurring decoded frames after a separate-power boot without
a USB host on the recorded setup.

## Open design choices

The initial autonomous UTC source is a configured unicast SNTPv4 server with
bounded uncertainty and an explicit age policy. Physical acquisition and
standalone execution have bounded bench evidence; calibrated UTC accuracy,
source authentication and long-duration reliability remain unqualified.
Alternate UTC sources, clock calibration, production RF engine/pins, runtime
credential provisioning and shared WsprryPi adoption of browser API v1 remain open.
The current Pico browser schemas and bounds are documented in the API contract. WTP/1 defines the interoperable protocol limits and policies
without selecting those implementations.

Estimates of reusable code and expected spectral behavior remain hypotheses until verified.
