# Project contract

## Identity and scope

WsprryPico is a first-class application in the WsprryPi family, maintained in a
separate repository. It must operate standalone and as a WsprryPi transmitter
backend. The defined hardware target is Pico 2 W / RP2350.

The accepted architectural record is [docs/architecture.md](docs/architecture.md).
This contract summarizes durable boundaries. The normative WTP/1 contract is
[docs/protocol/WTP.md](docs/protocol/WTP.md); the independently versioned [browser API v1](docs/browser-api.md) records
the implemented Pico surface. Shared WsprryPi adoption remains separate work.

## Timing and interoperability

- USB CDC is the canonical/reference WTP transport. Mutually authenticated
  TLS 1.3/TCP with ALPN `wtp/1` is an implemented first-class WTP job-transfer
  and job-control transport; it carries the identical WTP/1 stream to the same
  `JobService`, has no plaintext fallback and has no protocol-assigned default
  port. Network control remains product-gated and default-off.
- BLE/Bluefy is the primary local provisioning, management and field-control
  path; SoftAP/Safari is an independent no-infrastructure fallback. Their
  selected policy is the
  [Phase 12 field-access contract](docs/development/phase12-field-access-contract.md).
  The native [Raspberry Pi/Linux BlueZ client](docs/development/raspberry-pi-ble-client.md)
  is an additional supported local/bench client; it does not replace Bluefy or
  qualify the iPhone/offline acceptance path.
- Every job-control path uses the same JobService and loads and arms complete
  jobs. RP2350 owns execution and symbol timing.
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
The [conducted PIO campaign](docs/development/band-campaign-results.md) records
bounded operational results for an exact experimental image, clock and RF path.
These do not establish production band coverage, calibrated RF performance or
general WTP compliance.
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
[Bounded standalone RF and wall-power validation](docs/development/standalone-rf-power-validation.md)
adds independent decoding of recurring frames without a USB host on the recorded
setup. Calibrated timing and general RF/reliability qualification remain open.

First-class [TLS network control](docs/development/network-control.md) supplies
mutually authenticated WTP/TCP and HTTPS handlers to the existing job service.
Network status, persistent config and schedules share the standalone adapters.
Host TLS/browser tests and cross-linking do not qualify physical network/RF
coexistence. Credential installation currently requires an explicit local build.
The [Phase 12 portable core](docs/development/phase12-plan.md) defines and
host-tests bounded profiles, transactional replacement, replay and idle-only
application. The scoped [P12.3 closeout](docs/development/phase12-3-review.md)
implements the selected access journal, source/reset recovery, session policy,
GATT framing, Bluefy client, controller-time arbitration and cross-linked Pico
BLE/SoftAP/LED candidates. Production boot consumes access health fail closed
and now starts the encrypted GATT provisioning/local-control service from a
healthy adopted access state. The Linux BlueZ client reuses that exact service.

P12.4 supplies the closed C++ command decoder. P12.5 supplies delivery-safe
activation coordination and shared PSA ownership. The operator-selected
[field-access contract](docs/development/phase12-field-access-contract.md) fixes
Just Works plus application-password enrollment, retained bonds, SoftAP field
recovery, controller-time bootstrap, LED indication, trust replacement and
reset preservation. The public MAC-derived password and ordinary flash carry no
confidentiality claim.

Production SoftAP DHCP/mDNS/HTTP/HTTPS, password/cookie admission,
controller-time and browser/local control are now wired to the same
`JobService` in the RF-inhibited standard image. SoftAP credential
provisioning, reset administration, exact gestures, offline-page qualification
and most physical acceptance remain open. The provisioned SoftAP path now has
bounded native-Pi Candidate A evidence for WPA2/DHCP/mDNS/TLS,
password/cookie admission, controller time and basic local ownership, but no
phone/Safari/Bluefy or provisioning acceptance. BLE provisioning,
controller-time, Identify/status, unchanged WTP/1 and the network-only live
activator are also wired. BLE profile apply now requires a fresh password proof
bound to the exact staged bytes, applying request and generation; the public
default additionally requires an identity-bound USB-local confirmation within
the 30-second staging session. Those controls are host-tested but their phone
and target acceptance remains open. P12.3 is
closed only for its documented hardware-free
source/cross-link boundary; Phase 12 is not yet an accepted end-user path.

Host tests, target execution and RF qualification are distinct evidence classes.
A successful compile or simulated transmission establishes neither on-device
symbol timing nor spectral performance.

The QRSS, FSKCW and DFCW message compiler accepts at most 32 characters including
spaces. Complete finite jobs are independently bounded by 3,600 seconds and
512 events, with all repeats, gaps and required tails included. WTP and HTTP
transport limits remain unchanged. The compact browser API compiles the message
before LOAD/ARM; the RP2350 executes the resulting complete job locally.
See the [extended-job design](docs/development/phase11-5-extended-job-design.md)
and [current acceptance ledger](docs/development/phase11-5-acceptance-ledger.md)
for the implemented constraints and remaining physical qualification.

## Licensing and release identity

Original contributions use the MIT License in LICENSE.md. Dependencies and
reused source retain their own notices and obligations. Firmware version and
protocol version remain separate; release artifacts may use
WsprryPico-x.y.z.uf2. No release number is assigned by this scaffold.
