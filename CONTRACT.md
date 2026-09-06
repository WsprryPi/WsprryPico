# Project contract

## Identity and scope

WsprryPico is a first-class application in the WsprryPi family, maintained in a
separate repository. It must operate standalone and as a WsprryPi transmitter
backend. The defined hardware target is Pico 2 W / RP2350.

The accepted architectural record is [docs/architecture.md](docs/architecture.md).
This contract summarizes durable boundaries. The normative WTP/1 contract is
[docs/protocol/WTP.md](docs/protocol/WTP.md); other draft APIs remain unfrozen.

## Timing and interoperability

- USB CDC is the canonical WTP transport; Wi-Fi/TCP adds network control.
- BLE primarily serves provisioning/local management, with SoftAP fallback.
- Transport loads and arms complete jobs. RP2350 owns execution and symbol timing.
- WTP is device-neutral and independently versioned. Its specification is
  maintained in WsprryPico, with WsprryPico as the reference implementation.
- The browser uses a shared JSON API implemented by the relevant application.
- Preserve WsprryPi scheduler/encoder concepts without porting RP1 DKMS.

## Evidence and implementation status

The hardware-free RF study selects PIO/DMA GPIO synthesis for experimental
implementation; an optional Si5351 engine remains an alternative. A portable
generator, PIO/DMA driver and local launch integration are host-tested and
Arm-cross-linked, but are not selected by the standard Pico firmware. The
separate [bench image](docs/development/rf-bench.md) has bounded CPU and conducted
tone evidence from the Pico and the SDR on wspr5. Its relative monotonic timer
is explicitly unsynchronized; it does not claim WTP timing conformance.
No band coverage, RF performance or WTP compliance is currently established.
The Pico 2 W firmware provides an RF-inhibited WTP USB endpoint with separate
Console and WTP CDC interfaces. Its protocol, service, transport and descriptor
behavior is hardware-free host-tested. [Bounded target USB checks](docs/development/usb-target-validation.md)
pass for the recorded board, firmware and host; general USB/WTP conformance,
timing and RF behavior remain unqualified.

The [standalone layer](docs/development/standalone.md) now persists station and
schedule configuration and acquires UTC through Wi-Fi SNTP, with complete jobs
submitted through the same service as USB WTP. The standard image simulates
local job lifecycles with RF inhibited; the explicitly built standalone RF image
uses the experimental engine. [Inhibited target Wi-Fi validation](docs/development/standalone-physical-validation.md)
covers configuration retention, autonomous SNTP and outage/reconnection.
Conducted standalone RF, separate-power operation and calibrated timing remain
unqualified.

Host tests, target execution and RF qualification are distinct evidence classes.
A successful compile or simulated transmission establishes neither on-device
symbol timing nor spectral performance.

## Licensing and release identity

Original contributions use the MIT License in LICENSE.md. Dependencies and
reused source retain their own notices and obligations. Firmware version and
protocol version remain separate; release artifacts may use
WsprryPico-x.y.z.uf2. No release number is assigned by this scaffold.
