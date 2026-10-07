# Architecture baseline

Status: accepted architecture.

## Product and ownership

WsprryPico is a first-class standalone application, in its own repository, within the WsprryPi family. WsprryPi is not required for standalone operation. The same firmware must also support use as a WsprryPi hardware transmitter backend.

Target the Raspberry Pi Pico family, with Pico 2 W / RP2350 as the defined hardware target. This does not promise support for other Pico boards or RP2040.

Use WsprryPico for project, repository and application naming; firmware artifacts may be named WsprryPico-x.y.z.uf2.

## Transport and timing

- USB CDC serial is the canonical/reference control transport.
- Network WTP/TCP is a first-class job-transfer and job-control transport;
  Wi-Fi also supports the embedded web UI. Engineering profiles retain TLS 1.3,
  ALPN `wtp/1` and mutual certificate authentication. The standard consumer
  image defaults to Plain LAN on station port 31417 after infrastructure Wi-Fi
  and accepted SNTP. Build-time `off` and `tls` choices remain; TLS is never an
  automatic fallback. A Wi-Fi-only profile needs no TLS identity in Plain LAN
  mode.
- BLE/Bluefy remains the implemented engineering provisioning and field-control
  path. A native Raspberry Pi/Linux BlueZ client is an additional local/bench
  controller. If consumer BLE work resumes, it will use a dedicated iPhone app.
- The [revised open setup contract](development/phase12-safari-open-setup-revision.md)
  selects a captive SoftAP Wi-Fi page followed by optional station settings.
  Saving settings requires no button, code or retained phone owner. With saved
  credentials the AP is normally off during a healthy station connection; a
  previously selected runtime BOOTSEL hold is withdrawn after a physical
  failure, and station loss brings the AP back. A separate GP14 input is now
  selected for a connected-station opening gesture: stop is requested at 0.9
  seconds held and setup AP at 9 seconds held after confirmed shutdown. A hold
  beyond 10 seconds must leave AP available. A release under 0.4 seconds
  requests reset; a release from 0.4 to under 0.9 seconds requests shutdown.
  The opt-in RF-inhibited runtime has bounded B target acceptance for reset,
  shutdown requests, AP retention/expiry, DMA renewal, recovery and settings
  preservation; see the [integrated closeout](development/phase12-gp14-integrated-acceptance.md).
  Production RF cutoff integration retains five strict accepted rows and a
  scoped final long-hold disposition. Strict final 50 ms/90 s assertions remain
  unqualified and GP14 production default enablement is deferred.
  Safari is one possible
  browser, not a required step. Source implementation and bounded target
  acceptance exist; final selected commissioning results and explicit
  interoperability/timing exclusions are recorded in the
  [current closure matrix](development/phase12-closure-matrix.md). The earlier
  [Phase 12 field-access contract](development/phase12-field-access-contract.md)
  continues to describe engineering-profile authority; consumer commissioning
  follows the revised open setup contract.
- All RF timing is local on RP2350. USB and network connections load and arm complete jobs; packet arrival never sets symbol boundaries.

Preserve WsprryPi encoder and scheduler concepts while adapting platform dependencies. RP1 DKMS, kernel interfaces and RP1 register programming are not ported.

## RF generation

The [RF feasibility study](rf-feasibility.md) selects PIO/DMA packed-bit GPIO
synthesis for experimental implementation, with Si5351 as an alternative.
No production engine or band range is qualified. The experimental bench defaults
to GP2 and a build-selected 132, 138 or 150 MHz sample clock (138 MHz default).
Standalone direct RF uses the validated boot pin plan; newly selected pins are
not thereby RF-qualified. The standard firmware remains RF-inhibited. The
[portable stream library](development/rf-stream.md) implements planning, waveform
generation and an abstract-sink adapter separately from the firmware. The
[PIO/DMA sink and local timer launch](development/pio-dma-driver.md) are
implemented and integrated in the separate [RF bench](development/rf-bench.md).
That runner accepts finite relative-time tones, synthetic frames, portable Type 1
encoded WSPR messages and CPU benchmarks over a named Commands CDC interface. It provides neither a WTP endpoint nor UTC synchronization.
Bounded target results exist; calibrated timing and spectral validation remain pending.

## Browser UI

Reuse as much WsprryPi browser UI and UX as practical through a shared browser-facing JSON API. Pico firmware supplies lightweight HTTP handlers and static assets, not Apache/PHP. The browser API and WTP have distinct responsibilities but share application behavior and capability semantics.

The [shared transmitter application and fleet contract](transmitter-application-contract.md)
extends that direction to the complete member application: hardware, station,
messages, schedules, ownership, time, status and management. Each member owns
local execution; each schedule has either controller-owned or member-owned
recurrence. The [Pico configuration foundation](development/shared-transmitter-application.md)
adds independently versioned application/station/hardware projections through
the existing coordinator, journal and authenticated HTTPS policy. Expanded
adapters and complete application parity remain future implementation work.

## Protocol

WTP means WsprryPi Transmitter Protocol. It is device-neutral and versioned independently of firmware. WTP/1 is defined by the normative protocol contract.

The authoritative specification lives at docs/protocol/WTP.md in WsprryPico. WsprryPico is the reference implementation; implementation accidents do not define the protocol. WTP does not have a separate protocol repository.

The custom BLE provisioning and local-control wire interface is the versioned
[Field-GATT/1 protocol](protocol/Field-GATT.md), with checked
[conformance vectors](protocol/Field-GATT-v1-vectors.json) shared by firmware,
Bluefy and the native-Pi client. It is an engineering baseline, not a product
release freeze. Incompatible wire changes should use a new Field-GATT protocol
version. Field commands remain outside WTP/1. When GATT
carries WTP, it transports the unchanged WTP/1 byte stream to the same
`JobService`; ATT segmentation does not define another job-control protocol.
This source contract does not claim physical interoperability or end-user
acceptance.

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
with USB WTP and the [HTTPS browser API](browser-api.md). Network WTP/TCP
dispatches above raw lwIP callbacks. Engineering TLS uses ALPN `wtp/1` and
device-specific client-certificate principals. The standard consumer Plain LAN
binding uses a shared local-network principal after station IPv4 and accepted
SNTP, without an automatic downgrade path. Core 0
retains application/USB/network/storage ownership. The physical
standalone image dedicates core 1 to the RF engine/sink/peripheral and local launch
interrupts, using a one-command synchronous ownership-transfer mailbox. Two TLS
contexts on core 0 allow a persistent WTP owner plus an independent HTTPS browser.
An independently owned UTC discipline copy ages on the RF core; idle-only flash
writes coordinate both cores using SDK lockout. See the
[11.2 ownership and acceptance record](development/phase11-2-review.md). USB, WTP/TCP, browser jobs and standalone
schedules retain one ownership and execution authority. Network control defaults
off. Phase 12 field-access contention/coexistence retains its accepted scope
and explicit exclusions in the current matrix; broader mode/band/clock and
production release qualification remain Phase 14 work.

Phase 12 keeps provisioning outside that job-control protocol. A portable
manager and access controller own bounded profile replacement, local authority
and recovery while all RF/job control remains in the one existing JobService.
The implemented engineering field contract uses BLE/Bluefy and a SoftAP
fallback. The revised consumer contract selects an open SoftAP portal with
Wi-Fi first, optional station details later, and no persistent phone owner;
selected physical acceptance and recovery are closed within the current matrix
and its explicit dispositions.

The scoped P12.3 implementation reserves the access journal at
`0x3f3000`–`0x3f4fff`, BTstack at
`0x3f5000`–`0x3f6fff`, profiles at
`0x3f7000`–`0x3fafff`, standalone state at
`0x3fb000`–`0x3fefff` and E10 at `0x3ff000`.
Access and profile journals are independent. Source-mode tombstones and durable
reset intent prevent fallback to superseded authority; unhealthy, erased or
reset-pending access state suppresses station and scheduled work until
authorized recovery.
An exactly erased profile journal in a generic image selects unprovisioned
generation zero and the bounded open SoftAP. Its accepted Wi-Fi-only path and
source-linked consumer-claim candidate have separate physical gates; no blank
mutation grants owner authority until a complete source-5 commit. A complete, matching
device-bound compiled bundle may retain factory source behavior; incomplete
or wrong-device bundles and interrupted first profile selections fail closed.
The separately approved
[Wi-Fi-only network bootstrap](development/phase12-wifi-only-bootstrap-proposal.md)
permits a one-use, physically granted encrypted credential submission
from that blank AP and commit a device-bound network-only generation 1. It
adds no owner, station API, scheduler or RF authority. The `fb091f8`
RF-inhibited image passed selected-iPhone submission and generation-one
station readback on Candidate A; the final phone page and AP-return rows were
open in that historical [target record](development/phase12-wifi-only-physical-result.md).
Later selected consumer acceptance is recorded in the current matrix.

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
`192.168.4.1/24`, AP-interface mDNS, blank captive HTTP with the bounded
encrypted Wi-Fi-only transaction, device-bound HTTPS,
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

The selected Phase 12 commissioning, recovery, time-policy, reset, resource
and indicator assertions are closed within the
[current matrix](development/phase12-closure-matrix.md). Its explicit physical
timing/peer/fleet exclusions remain unqualified; neither the closed scope nor
the one-member application check establishes broad interoperability. GP14
production default enablement is deferred. Earlier native-Pi and iPhone/Bluefy
records retain their exact source/image/evidence scope.
The [pin-assignment contract](pin-assignment-contract.md) selects the eligible
GPIO set, exclusive role allocations and fixed I²C pairs. Clock calibration and
production RF engine/pin qualification remain open. WsprryPi has an
independently implemented browser API adapter; full shared application and
hardware configuration parity follows the implementation path in the fleet
contract above. The current Pico browser schemas and bounds are documented in
the API contract. WTP/1 defines interoperable limits and policies without
selecting those implementations.

Estimates of reusable code and expected spectral behavior remain hypotheses until verified.
