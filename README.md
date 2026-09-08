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

Optional TLS 1.3 WTP/TCP, the HTTPS browser API and operator UI are implemented
and host-tested. [Phase 11](docs/development/network-control.md) adds per-device
certificate tooling and network management. Network control defaults off; target
TLS/RF coexistence acceptance remains open. [Phase 11.2](docs/development/phase11-2-review.md)
isolates physical waveform servicing and permits concurrent controller/browser
connections; target timing acceptance is pending. WsprryPi's host TLS integration
is independently implemented. [Phase 11.3](docs/development/phase11-3-plan.md)
adds DHCP with a stable certified mDNS hostname, optional explicit IP identity
and a shared client/server authority contract; physical acceptance remains open.

- [Accepted architecture](docs/architecture.md)
- [WTP/1 protocol contract](docs/protocol/WTP.md)
- [Browser API v1](docs/browser-api.md)
- [Network control and certificate management](docs/development/network-control.md)
- [RF feasibility investigation](docs/rf-feasibility.md)
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
