# Architecture baseline

Status: accepted architecture.

## Product and ownership

WsprryPico is a first-class standalone application, in its own repository, within the WsprryPi family. WsprryPi is not required for standalone operation. The same firmware must also support use as a WsprryPi hardware transmitter backend.

Target the Raspberry Pi Pico family, with Pico 2 W / RP2350 as the defined hardware target. This does not promise support for other Pico boards or RP2040.

Use WsprryPico for project, repository and application naming; firmware artifacts may be named WsprryPico-x.y.z.uf2.

## Transport and timing

- USB CDC serial is the canonical/reference control transport.
- Mutually authenticated TLS 1.3/TCP with ALPN `wtp/1` is a first-class WTP
  job-transfer and job-control transport; Wi-Fi also supports the embedded web
  UI. Network control remains product-gated and default-off.
- BLE/Bluefy is the primary local provisioning, management and field-control
  path. No WsprryPico-native iOS app is planned. A native Raspberry Pi/Linux
  BlueZ client is an additional supported local/bench controller.
- SoftAP/Safari is an independent provisioning, recovery and field-control
  fallback when infrastructure Wi-Fi is absent.
- The selected authentication, offline-time and indicator behavior is defined
  by the [Phase 12 field-access contract](development/phase12-field-access-contract.md).
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
with USB WTP and the [HTTPS browser API](browser-api.md). First-class TLS 1.3
WTP/TCP uses device-specific certificate principals and ALPN `wtp/1` dispatch
above raw lwIP callbacks; plaintext and downgrade are not supported. Core 0
retains application/USB/network/storage ownership. The physical
standalone image dedicates core 1 to the RF engine/sink/peripheral and local launch
interrupts, using a one-command synchronous ownership-transfer mailbox. Two TLS
contexts on core 0 allow a persistent WTP owner plus an independent HTTPS browser.
An independently owned UTC discipline copy ages on the RF core; idle-only flash
writes coordinate both cores using SDK lockout. See the
[11.2 ownership and acceptance record](development/phase11-2-review.md). USB, WTP/TCP, browser jobs and standalone
schedules retain one ownership and execution authority. Network control defaults
off. Phase 12 field-access contention/coexistence still requires its physical
plan; broader mode/band/clock and production release qualification remain Phase
13 work.

Phase 12 keeps provisioning outside that job-control protocol. A portable
manager and access controller own bounded profile replacement, local authority
and recovery while all RF/job control remains in the one existing JobService.
The selected field contract makes BLE/Bluefy primary and SoftAP/Safari an
independent no-infrastructure fallback.

The scoped P12.3 implementation reserves the access journal at
`0x3f3000`–`0x3f4fff`, BTstack at
`0x3f5000`–`0x3f6fff`, profiles at
`0x3f7000`–`0x3fafff`, standalone state at
`0x3fb000`–`0x3fefff` and E10 at `0x3ff000`.
Access and profile journals are independent. Source-mode tombstones and durable
reset intent prevent fallback to superseded authority; unhealthy, erased or
reset-pending access state suppresses station and scheduled work until
authorized recovery.

The portable access layer implements exact request-bound proofs, enrollment,
bond capacity/revocation, SoftAP cookies and expiry, field mode, reset levels,
controller-time/SNTP arbitration and LED priority. Fixed 64-byte frames bridge
the existing strict provisioning command adapter to the candidate Pico GATT
transport. Candidate Pico GATT, WPA2 SoftAP and onboard-LED adapters cross-link
against the exact clean pinned BTstack source. The Bluefy page implements the
matching authorization and framing path. Profile application over BLE adds a
fresh one-use password proof bound to the final staged digest, apply request and
generation. While the public default remains active, that same proof also needs
an exact-device USB-local confirmation and expires with the 30-second staging
session; ordinary retained-bond authority alone cannot apply credentials.

P12.6 makes the BLE path and the independent SoftAP fallback real in the
standard RF-inhibited image. One CYW43 owner supplies checked station-MAC
identity, BTstack GATT, station service, SoftAP netif and core-0 LED access. The
production graph constructs the portable access/manager state and a
network-only `PicoActivationPlatform`; neither layer can abort, release or
clear JobService/RF ownership. The SoftAP graph supplies a bounded,
AP-interface-bound DHCP service on
`192.168.4.1/24`, AP-interface mDNS, blank read-only HTTP, device-bound HTTPS,
password/cookie admission, controller time and the existing browser API backed
by that same `JobService`. The repository-owned Bluefy artifact uses a
release-keyed atomic offline cache. A bounded native-Pi Candidate A run has
accepted the provisioned SoftAP association/DHCP/mDNS/HTTPS/time/basic-control
path only. SoftAP credential provisioning, phone/Safari/Bluefy acceptance,
reset gestures and most physical coexistence/resource evidence remain Phase 12
gates. See the
[Phase 12 plan](development/phase12-plan.md),
[field contract](development/phase12-field-access-contract.md) and
[production review](development/phase12-production-acceptance-review.md).

The browser's compact `LOAD_MESSAGE` path compiles bounded QRSS, FSKCW and DFCW
messages before entering the same job service. Inputs are limited to 32 characters
including spaces; duration and expanded events independently fit the advertised
3,600-second and 512-event ceilings. Repetition is fully expanded before ARM.
Raw WTP clients continue submitting complete encoded jobs. See the
[extended-job design](development/phase11-5-extended-job-design.md) for memory
ownership and the distinction between implemented limits and physical acceptance.

Standalone execution uses local Type 1 encoding, versioned persistent station
and schedule records, and Wi-Fi SNTP acquisition without WsprryPi. Host
operation accepts already encoded jobs. Both paths converge before engine
preparation. [Bounded physical validation](development/standalone-rf-power-validation.md)
now demonstrates recurring decoded frames after a separate-power boot without
a USB host on the recorded setup.

## Remaining implementation and qualification choices

The implemented autonomous UTC source is configured unicast SNTPv4. Phase 12
adds the portable controller/SNTP arbiter and routes production SNTP, BLE and
SoftAP controller observations through it. Physical phone-time accuracy remains
unqualified.

Remaining Phase 12 details are SoftAP credential provisioning, authenticated
phone-time acceptance, accepted reset controls, blank generic HTTP,
stable-station AP withdrawal, physical Bluefy offline/interoperability
evidence, live profile activation and broader target resource/coexistence
tuning. The wired SoftAP/HTTPS and local-control surfaces have only the bounded
native-Pi target acceptance recorded above.
Clock calibration, production RF engine/pins and shared WsprryPi adoption of
browser API v1 remain open. The current Pico browser schemas and bounds are
documented in the API contract. WTP/1 defines interoperable limits and policies
without selecting those implementations.

Estimates of reusable code and expected spectral behavior remain hypotheses until verified.
