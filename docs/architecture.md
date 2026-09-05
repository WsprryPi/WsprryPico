# Architecture baseline

Status: accepted architecture.

## Product and ownership

WsprryPico is a first-class standalone application, in its own repository, within the WsprryPi family. WsprryPi is not required for standalone operation. The same firmware must also support use as a WsprryPi hardware transmitter backend.

Target the Raspberry Pi Pico family, beginning with Pico 2 W / RP2350. This does not promise immediate support for other Pico boards or RP2040.

Use WsprryPico for project, repository and application naming; firmware artifacts may be named WsprryPico-x.y.z.uf2.

## Transport and timing

- USB CDC serial is the canonical/reference control transport.
- Wi-Fi/TCP provides network control; Wi-Fi also supports the embedded web UI.
- BLE is primarily for provisioning and local management.
- SoftAP provides a provisioning fallback.
- All RF timing is local on RP2350. USB and network connections load and arm complete jobs; packet arrival never sets symbol boundaries.

Preserve WsprryPi encoder and scheduler concepts while adapting platform dependencies. RP1 DKMS, kernel interfaces and RP1 register programming are not ported.

## RF generation

Investigate RP2350 PIO, PLL and direct-RF generation against an optional Si5351 engine. No engine, band range, pin assignment, spectral performance or clock arrangement has yet been selected or qualified.

## Browser UI

Reuse as much WsprryPi browser UI and UX as practical through a shared browser-facing JSON API. Pico firmware supplies lightweight HTTP handlers and static assets, not Apache/PHP. The browser API and WTP have distinct responsibilities but share application behavior and capability semantics.

## Protocol

WTP means WsprryPi Transmitter Protocol. It is device-neutral and versioned independently of firmware, starting with a prospective WTP/1.

The authoritative specification lives initially at docs/protocol/WTP.md in WsprryPico. WsprryPico is the reference implementation; implementation accidents do not define the protocol. Do not create a third protocol repository now.

## Proposed internal boundary

This decomposition is a design proposal:

Browser handlers, standalone scheduler, USB WTP and TCP WTP submit work to one application job service. That service owns validation, transmitter ownership and state. A local execution layer controls interchangeable RF engines. Time synchronization estimates UTC relative to a monotonic device clock; RF frequency calibration is tracked separately.

Standalone execution needs local encoding, persistent station/schedule configuration and time acquisition without WsprryPi. Host operation may accept already encoded jobs. Both paths converge before engine preparation.

## Open design choices

WTP encoding/framing, limits, authentication, ownership and disconnect policy; UTC source and acceptable uncertainty; clock calibration; RF engine and pins; SDK/toolchain versions; supported modulation profiles; licensing and exact source reuse; browser API schemas and storage limits remain to be designed.

Estimates of reusable code and expected spectral behavior remain hypotheses until verified.
