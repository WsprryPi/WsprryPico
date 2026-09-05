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
No production engine or band range is qualified. Pin and clock allocations in
the study are proposals; the firmware remains RF-inhibited.

## Browser UI

Reuse as much WsprryPi browser UI and UX as practical through a shared browser-facing JSON API. Pico firmware supplies lightweight HTTP handlers and static assets, not Apache/PHP. The browser API and WTP have distinct responsibilities but share application behavior and capability semantics.

## Protocol

WTP means WsprryPi Transmitter Protocol. It is device-neutral and versioned independently of firmware. WTP/1 is defined by the normative protocol contract.

The authoritative specification lives at docs/protocol/WTP.md in WsprryPico. WsprryPico is the reference implementation; implementation accidents do not define the protocol. WTP does not have a separate protocol repository.

## Internal boundary

Browser handlers, standalone scheduler, USB WTP and TCP WTP submit work to one application job service. That service owns validation, transmitter ownership and state. A local execution layer controls interchangeable RF engines. Time synchronization estimates UTC relative to a monotonic device clock; RF frequency calibration is tracked separately.

The portable frame parser and job service implement the transport-independent
part of this boundary. The Pico 2 W foundation runs that service with an
unsynchronized clock and RF-inhibited engine. Its dual CDC device separates
console diagnostics from WTP framing. The [USB adapter contract](development/usb-cdc.md)
defines bounded servicing and connection semantics; logging must never enter WTP.
The [strict WTP endpoint](development/wtp-endpoint.md) performs JSON validation,
request dispatch and ordered response/event transmission. Browser handlers, the
standalone scheduler and target RF engines remain to be implemented.

Standalone execution needs local encoding, persistent station/schedule configuration and time acquisition without WsprryPi. Host operation may accept already encoded jobs. Both paths converge before engine preparation.

## Open design choices

UTC source and implementation-specific acceptable uncertainty; clock
calibration; RF engine and pins; browser API schemas and storage limits remain
to be designed. WTP/1 defines the interoperable protocol limits and policies
without selecting those implementations.

Estimates of reusable code and expected spectral behavior remain hypotheses until verified.
