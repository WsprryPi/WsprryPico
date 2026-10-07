# Project contract

## Identity and scope

WsprryPico is a first-class application in the WsprryPi family, maintained in a
separate repository. It must operate standalone and as a WsprryPi transmitter
backend. The defined hardware target is Pico 2 W / RP2350.

The accepted architectural record is [docs/architecture.md](docs/architecture.md).
This contract summarizes durable boundaries. The normative WTP/1 contract is
[docs/protocol/WTP.md](docs/protocol/WTP.md). The versioned engineering
[Field-GATT/1 contract](docs/protocol/Field-GATT.md) and
[conformance vectors](docs/protocol/Field-GATT-v1-vectors.json) define the
custom BLE wire surface without changing WTP/1. Incompatible changes require a
new Field-GATT protocol version. The selected Phase 12 acceptance scope is
[closed with explicit dispositions](docs/development/phase12-closure-matrix.md);
broader physical interoperability remains unqualified.
The independently versioned [browser API v1](docs/browser-api.md) records the
implemented Pico surface. WsprryPi's compatible adapter is independently
maintained; full shared application/configuration parity remains future work.
The [shared transmitter application and fleet contract](docs/transmitter-application-contract.md)
defines the selected member/controller arrangement, configuration domains,
scheduling authority and implementation path. The
[Pico foundation](docs/development/shared-transmitter-application.md) freezes
bounded member/station/hardware resources using the existing configuration
authority. Expanded adapters remain future work; WTP/1 is unchanged and full
application parity is not claimed.

## Timing and interoperability

- USB CDC is the canonical/reference WTP transport. Network WTP/TCP is a
  first-class job-transfer and job-control transport carrying the identical
  WTP/1 stream to the same `JobService`. Engineering profiles retain TLS 1.3,
  ALPN `wtp/1` and mutual certificate authentication. The standard consumer
  image defaults to Plain LAN on station TCP port 31417 after infrastructure
  Wi-Fi and accepted SNTP; build-time `off` and `tls` selections remain. Plain
  LAN has no automatic TLS fallback and no browser API. Any client that can
  reach the local port can submit WTP commands under the shared LAN principal.
  WsprryPi supports an explicit Plain LAN connection; one installed fleet
  member/application path has bounded Phase 12 acceptance. Full fleet
  interoperability remains unqualified.
- The implemented engineering provisioning and field-control path uses
  BLE/Bluefy under the
  [Phase 12 field-access contract](docs/development/phase12-field-access-contract.md).
  The later [open setup revision](docs/development/phase12-safari-open-setup-revision.md)
  selects an open SoftAP portal with Wi-Fi first and optional station settings
  later. Saving settings requires no button or retained phone owner. A blank
  Pico starts its open AP automatically; a saved Pico normally keeps it off
  while station Wi-Fi is healthy. Station loss brings the AP back. The operator
  selected a separate active-low GP14 button (physical pin 19): a debounced
  release under 0.4 seconds requests reset; reaching 0.9 seconds held requests
  transmission shutdown; reaching 9 seconds held requests setup AP after
  shutdown is confirmed. A held jumper must not repeat actions or impair AP.
  A release from 0.4 to under 0.9 seconds requests shutdown. These
  actions have bounded acceptance in the opt-in RF-inhibited B runtime; see
  the [integrated closeout](docs/development/phase12-gp14-integrated-acceptance.md).
  Production RF cutoff integration has five accepted strict rows and a scoped
  final long-hold disposition; strict final 50 ms/90 s assertions remain
  unqualified and GP14 default enablement is deferred. The
  runtime BOOTSEL sampler failed a physical long-hold check and remains
  withdrawn. The earlier
  [P12.7 physical-owner decision](docs/development/phase12-7-decision.md) is
  historical; selected phone/iPad commissioning is accepted within the
  [current matrix](docs/development/phase12-closure-matrix.md).
  The native [Raspberry Pi/Linux BlueZ client](docs/development/raspberry-pi-ble-client.md)
  is an additional supported local/bench client; it does not qualify the
  consumer iOS-browser acceptance path. Its profile-apply command is
  source/host conforming to Field-GATT/1. Bounded native-Pi profile activation
  is recorded in the [automatic closeout](docs/development/phase12-orchestratable-closeout-results.md).
  Specified peer/capacity exclusions and broader unqualified interoperability
  are retained in that matrix.
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
engineering mTLS WTP/TCP and HTTPS handlers, plus the consumer LAN WTP mode,
to the existing job service.
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
provisioning, reset administration, gestures and offline-page qualification
have selected acceptance in the current Phase 12 matrix. The earlier
provisioned SoftAP checkpoint had
bounded native-Pi Candidate A evidence for WPA2/DHCP/mDNS/TLS,
password/cookie admission, controller time and basic local ownership, but no
phone/Safari/Bluefy or provisioning acceptance. BLE provisioning,
controller-time, Identify/status, unchanged WTP/1 and the network-only live
activator are also wired. BLE profile apply now requires a fresh password proof
bound to the exact staged bytes, applying request and generation; the public
default additionally requires an identity-bound USB-local confirmation within
the 30-second staging session. Those profile controls were initially host-tested;
subsequent bounded activation evidence is recorded in the current matrix.
A separate iPhone 17 Pro
Max/iOS 27.0/Bluefy 3.9.3 exercise accepts retained-bond authorization, one
authenticated controller-time exchange, Identify LED/field status and WTP
`HELLO` plus read-only `STATUS`. It does not accept offline reuse, fresh pairing,
profile activation, arbitrary WTP job control or the broader time/LED matrices.
P12.3 is
closed only for its documented hardware-free
source/cross-link boundary; final selected end-user acceptance is bounded by
the current matrix and its explicit exclusions.

The operator separately approved a
[Wi-Fi-only blank-device bootstrap](docs/development/phase12-wifi-only-bootstrap-proposal.md)
that would save station credentials without owner or RF authority. It is an
explicit exception to the blank-AP read-only policy for that bounded first
join, contingent on the documented physical BOOTSEL and transaction gates.
The `fb091f8` RF-inhibited image admits the bounded encrypted transaction on a
blank AP. Candidate A passed selected-iPhone submission and post-reboot
network-only generation-1/station-address readback within the
[recorded setup](docs/development/phase12-wifi-only-physical-result.md). The
final phone page and AP return after station loss were open at that checkpoint;
later selected consumer acceptance is in the current matrix. This grants no
owner, station API, TLS, job or RF authority.

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

The [pin assignment contract](docs/pin-assignment-contract.md) selects exclusive
GP ownership and one direct RF GPIO or one fixed I²C pair. The
[implementation guide](docs/development/pin-allocation.md) records the supported
boot-applied subset and unavailable amplifier/LPF/Si5351 adapters.
