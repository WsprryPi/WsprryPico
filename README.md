# WsprryPico

WsprryPico is a first-class standalone WSPR/QRSS transmitter application in the WsprryPi family. It targets Raspberry Pi Pico family hardware, with Pico 2 W / RP2350 as the defined hardware target, and also serves as a hardware transmitter backend for WsprryPi.

Status: normative WTP/1 contract, host-tested portable core, and an RF-inhibited
Pico 2 W WTP USB endpoint. [Bounded target USB validation](docs/development/usb-target-validation.md)
passes on the recorded board and Mac. The experimental GP2 PIO/DMA driver,
portable waveform generator and local launch integration are host-tested and
Arm-cross-linked. A separate [RF bench](docs/development/rf-bench.md) now runs
on the Pico. The [clock comparison](docs/development/rf-clock-validation.md)
selects a 138 MHz experimental clock with 1.530 ms measured refill. [Full synthetic frames, GPSDO
comparison and abort/rearm](docs/development/rf-frame-validation.md) have been
received on wspr5. Clock selection suppresses the original nearby alias;
[Encoded WSPR frames](docs/development/rf-wspr-validation.md) now decode
independently from wspr5 captures. Optional RF warmup improves measured settling.
The measured close-in sidebands meet the operator's better-than-WsprryPi benchmark.
An explicit [UTC/RF WTP integration image](docs/development/utc-rf-job-validation.md)
has completed a future-scheduled job and independent conducted decode. The
standard firmware retains RF inhibition. [Standalone configuration and timing](docs/development/standalone.md)
now provide persistent station/schedules, Wi-Fi SNTP and host-tested autonomous
job submission. [Inhibited Wi-Fi bench validation](docs/development/standalone-physical-validation.md)
adds device time acquisition, persistence and outage recovery.
[Standalone RF and wall-power validation](docs/development/standalone-rf-power-validation.md)
adds complete scheduled frames and independent decoding after a power-only boot,
without a USB host. The [conducted PIO band campaign](docs/development/band-campaign-results.md)
records a five-mode matrix with eight narrowly qualified operational entries,
RF failures and USB-related blockage. Calibrated timing, spectra and production
engine/mode/band qualification remain open.
The later [focused 2200 m investigation](docs/development/2200m-investigation.md)
passes all five operational modes at 138 MHz with QRSS3 workloads, compares
132/138/150 MHz clocks and retains an unfiltered Pi GPIO4 benchmark.

Authenticated TLS 1.3 WTP/TCP is a first-class job-transfer and job-control
transport alongside canonical USB CDC/WTP; it carries the identical WTP/1 byte
stream into the same `JobService`. The HTTPS browser API and operator UI are implemented
and include bounded QRSS/FSKCW/DFCW message entry: 32 characters including spaces,
up to 60 minutes per complete job, subject to the independent 512-event capacity.
The [extended-job design](docs/development/phase11-5-extended-job-design.md)
describes exact duration, repetition and local execution. These limits are
implemented; [resource and physical acceptance](docs/development/phase11-5-acceptance-ledger.md)
is closed for the recorded 138 MHz/divider-1 configuration. The subsequent
[Phase 11.6 conducted matrix](docs/development/phase11-6-plan.md) is closed with
explicitly reduced scope: 13 passing rows are accepted, 52 supported
non-passing rows are excluded from acceptance, and the 10 unsupported 4 m/2 m
rows remain configuration boundaries.

Network interfaces are implemented and host-tested. Per-device certificate
tooling, network management, concurrent controller/browser servicing, DHCP with
a stable certified mDNS hostname, optional explicit-IP identity and the shared
client/server authority contract are accepted within the documented Phase 11
software and bounded physical scopes. The authoritative
[Phase 11.7 joint review](docs/development/phase11-7-review.md) closes Phase 11
within that scope, including the 11.4 inhibited matrix/eight-hour soak, 11.5 at
138 MHz/divider 1 and the explicitly reduced 11.6 conducted matrix. Network
control still defaults off. Broader mode/band/clock, timing, spectra, filtering,
reliability and release qualification remain in Phase 13.

[Phase 12 provisioning](docs/development/phase12-plan.md) is current. Its
hardware-free P12.1-P12.5 slices retain their documented scope. The P12.6
production tranche now starts provisioning-only encrypted GATT in the standard
RF-inhibited image from healthy adopted access state, constructs a network-only
delivery-safe activator and indicator, and publishes a deterministic
repository-owned Bluefy page. A later
[BLE local-control continuation](docs/development/phase12-ble-local-control-review.md)
connects authenticated controller time, Identify/status and an unchanged WTP/1
stream to that production GATT service and extends the offline page. The
supported [Raspberry Pi/Linux BlueZ client](docs/development/raspberry-pi-ble-client.md)
adds the same identity-bound local workflow without replacing Bluefy as the
selected iPhone client. Its bounded
[execution and adversarial review](docs/development/phase12-pi-ble-tcp-review.md)
adds deterministic host evidence and exact RF-inhibited Candidate A/wspr5 live
evidence for identity inspection, authenticated controller time, field status,
and WTP `HELLO`/`STATUS`. Exact candidate identity/adoption, preserved
station/schedule/watermark state and BLE advertising have partial physical
evidence in the
[production review](docs/development/phase12-production-acceptance-review.md).

The operator-selected
[field-access/security contract](docs/development/phase12-field-access-contract.md)
remains controlling: BLE/Bluefy is primary, SoftAP/Safari is an independent
no-infrastructure fallback, Bluetooth uses Just Works plus application-password
enrollment, the public default comes from the station-MAC suffix, phone time may
seed bounded offline UTC, and the onboard LED supplies Identify and actual
SoftAP-ready patterns. The production continuation connects SoftAP
DHCP/mDNS, blank read-only HTTP, provisioned pre-clock/normal HTTPS,
password/cookie admission, controller time and the existing browser/one-
`JobService` API. Its clean RF-inhibited Candidate A image has bounded
native-Pi evidence for WPA2/DHCP/mDNS/TLS, password/cookie admission,
same-connection controller time, status and `HELLO`/`CLAIM`/`RELEASE`; see the
[SoftAP physical review](docs/development/phase12-softap-physical-review.md).
This is not phone/Safari/Bluefy or provisioning acceptance. The clean committed
BLE image has verified Candidate A load/boot
with preserved state and final RF-inhibited empty/unowned/inactive-output
restoration. A later bounded iPhone 17 Pro Max/iOS 27.0/Bluefy 3.9.3 exercise
accepts retained-bond authorization, one authenticated phone-time exchange,
Identify LED/field status and Bluefy read-only WTP `HELLO`/`STATUS`. Offline
reuse, fresh-password/new-pairing behavior, profile activation, blank generic
SoftAP HTTP, stable-station AP withdrawal, the broader physical BLE job-
control/local-management, controller-time and LED matrices, reset controls and
most of the
[RF-inhibited-first physical plan](docs/development/phase12-physical-acceptance.md)
remain open. Phase 12 is therefore active; the scoped source closeout is not
full physical or end-user acceptance.

The current Bluefy source requires a fresh password step-up for each exact
staged profile even on a retained bond. While the public default password is
active, the page also waits for an identity-bound USB-local confirmation within
the 30-second provisioning session. This is host-tested source behavior, not
yet Bluefy/iPhone acceptance; the native-Pi client has separate bounded
[target activation evidence](docs/development/phase12-profile-activation-attempt.md).
The frozen [Field-GATT/1 contract](docs/protocol/Field-GATT.md)
and [machine-readable vectors](docs/protocol/Field-GATT-v1-vectors.json) now
keep firmware, both clients and host conformance checks aligned through the
7,168-byte profile limit; physical profile activation remains open. Bluefy also
has a test-only prepared-JSON-file import for operator-assisted acceptance. It
does not create or deliver a profile and is not an end-user commissioning flow;
that flow requires a separate operator design discussion.

- [Accepted architecture](docs/architecture.md)
- [WTP/1 protocol contract](docs/protocol/WTP.md)
- [Field GATT protocol and super-user guide](docs/protocol/Field-GATT.md)
- [Browser API v1](docs/browser-api.md)
- [Network control and certificate management](docs/development/network-control.md)
- [Phase 12 provisioning plan](docs/development/phase12-plan.md)
- [Phase 12 field-access/security contract](docs/development/phase12-field-access-contract.md)
- [Phase 12.3 hardware-free integration review](docs/development/phase12-3-review.md)
- [Phase 12.4 portable command and activation review](docs/development/phase12-4-review.md)
- [Phase 12.5 activation-safety review](docs/development/phase12-5-review.md)
- [RF feasibility investigation](docs/rf-feasibility.md)
- [Phase 12 production/acceptance review](docs/development/phase12-production-acceptance-review.md)
- [Phase 12 BLE local-control continuation](docs/development/phase12-ble-local-control-review.md)
- [Bluefy field page](docs/bluefy/)
- [Raspberry Pi/Linux BLE client](docs/development/raspberry-pi-ble-client.md)
- [Raspberry Pi BLE and first-class TCP/WTP execution review](docs/development/phase12-pi-ble-tcp-review.md)
- [Implementation plan](docs/implementation-plan.md)
- [WsprryPi host acceptance prerequisites](docs/development/phase10-host-acceptance.md)
- [Experimental PIO band campaign](docs/development/band-campaign.md)
- [PIO/DMA driver](docs/development/pio-dma-driver.md)
- [Portable RF stream](docs/development/rf-stream.md)
- [UTC and RF job integration](docs/development/utc-rf-job-validation.md)
- [Standalone configuration and timing](docs/development/standalone.md)
- [Portable core development](docs/development/portable-core.md)
- [Pico 2 W firmware foundation](docs/development/firmware-foundation.md)
- [Strict WTP USB endpoint](docs/development/wtp-endpoint.md)

Firmware release names will follow `WsprryPico-x.y.z.uf2`. WTP versions are independent of firmware versions. WTP is documented here, with WsprryPico as its reference implementation; there is no separate protocol repository.

Unresolved design proposals are explicitly marked as drafts.

## Development and contribution

- [Project contract](CONTRACT.md)
- [Development baseline](docs/development/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Original contributions are licensed under [MIT](LICENSE.md). Firmware build
inputs are pinned in the firmware-foundation documentation.

The [frequency correction and alias investigation](docs/development/rf-correction-validation.md) records the
`CORRECTION` bench command, corrected measurements, remaining frame settling
and identified sampled-square-wave alias.
