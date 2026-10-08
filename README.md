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

Network WTP/TCP is a first-class job-transfer and job-control transport
alongside canonical USB CDC/WTP; it carries the identical WTP/1 byte stream
into the same `JobService`. Engineering profiles use mutual certificate
authentication. The standard consumer image defaults to Plain LAN on station
port 31417 after infrastructure Wi-Fi and accepted SNTP; no certificates are
needed for its Wi-Fi-only profile. Build-time `off` and `tls` choices remain.
Plain LAN admits any client that can reach the port on the local network.
WsprryPi has a matching explicit Plain LAN host connection with bounded
one-member application evidence; full fleet interoperability remains unqualified.
The HTTPS browser API and operator UI are implemented
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
reliability and release qualification remain in Phase 14. The
[Phase 13 feature backlog](docs/implementation-plan.md#phase-13-feature-backlog)
records P13.1 transmit LED work as complete (`CLOSED_SCOPED`): LED addressability
and external TX-only operation are verified. Existing button operation is
recorded in Phase 12. P13.2 external Si5351 implementation is deferred; no
active Phase 13 feature work remains selected. Phase 14 RF qualification and
release is next on the roadmap.

[Phase 12 provisioning](docs/development/phase12-plan.md) is `CLOSED_SCOPED`
by the operator's 2026-10-06 acceptance of the frozen matrix and documented
dispositions. The [closeout](docs/development/phase12-orchestratable-closeout-results.md)
retains all four automatic workstreams and the later selected physical results.
The [matrix](docs/development/phase12-closure-matrix.md) states the excluded
timing, peer and fleet claims. Final RF accounting is 19 acquisition attempts
and 13 charged jobs; the strict final `long_ap` STOP remains. GP14 production
default enablement is deferred. Broad RF and release qualification remain separate.
Its hardware-free P12.1-P12.5 slices retain their documented scope. The P12.6
production tranche now starts provisioning-only encrypted GATT in the standard
RF-inhibited image from healthy adopted access state, constructs a network-only
delivery-safe activator and indicator, and publishes a deterministic
repository-owned Bluefy page. A later
[BLE local-control continuation](docs/development/phase12-ble-local-control-review.md)
connects authenticated controller time, Identify/status and an unchanged WTP/1
stream to that production GATT service and extends the browser page. Bluefy
offline reuse is unsupported; the device-served SoftAP portal provides the
selected offline setup path. The
supported [Raspberry Pi/Linux BlueZ client](docs/development/raspberry-pi-ble-client.md)
adds the same identity-bound local engineering workflow. Bluefy was the
historical engineering iPhone client; the open SoftAP portal is the selected
consumer setup surface and can run in a capable captive sign-in window or
regular browser.
The Pi client's bounded
[execution and adversarial review](docs/development/phase12-pi-ble-tcp-review.md)
adds deterministic host evidence and exact RF-inhibited Candidate A/wspr5 live
evidence for identity inspection, authenticated controller time, field status,
and WTP `HELLO`/`STATUS`. Exact candidate identity/adoption, preserved
station/schedule/watermark state and BLE advertising have partial physical
evidence in the
[production review](docs/development/phase12-production-acceptance-review.md).

The operator-selected
[field-access/security contract](docs/development/phase12-field-access-contract.md)
describes the running engineering BLE/password baseline. The later
[revised open setup contract](docs/development/phase12-safari-open-setup-revision.md)
shows Wi-Fi fields immediately, with a show/hide password control, and saves
the network before optional station details on a separate page. It requires
no BOOTSEL step or retained phone owner. Another phone may change settings.
The portal starts automatically with no saved credentials or after a saved
station network is unavailable for 60 seconds. A healthy station normally
withdraws the AP after a stable connection. The selected separate GP14 button
(physical pin 19) requests a device reset on a debounced release under 0.4
seconds, transmission shutdown on reaching 0.9 seconds held, and setup AP on
reaching 9 seconds held after shutdown is confirmed. Keeping GP14 low past 10
seconds must not repeat the actions or impair the AP. A release from 0.4 to
under 0.9 seconds requests shutdown on release. An opt-in RF-inhibited
runtime candidate connects these controls in source; the default image
leaves GP14 disabled. Its first Candidate B load failed closed on a DMA
count-mode error. The repaired image passed bounded idle, short-hold and
long-hold event checks; [read-only SoftAP telemetry](docs/development/phase12-gp14-runtime-review.md)
was loaded on A and B and passed bounded idle continuity checks. On B, it also
reports AP/service readiness during a 49.557-second hold and for 60.7 seconds
after release. The operator then confirmed B's phone setup page showed
“Saved and connected”; post-reboot readback verified profile generation 2
and a station address. A 218 ms GP14 tap also verified an actual normal reset,
retained settings and Wi-Fi return. This accepts those bounded B behaviors.
The later [integrated closeout](docs/development/phase12-gp14-integrated-acceptance.md)
accepts B's bounded long-held AP availability, release lease expiry, recurring
DMA renewal, recovery and settings preservation. The later
[RF record](docs/development/phase12-gp14-rf-review.md) accepts five strict rows
and scoped final long-hold components. Strict final 50 ms/90 s assertions remain
unqualified; GP14 production default enablement is deferred.
Capture during an extended flash-safe pause passed; exact coincidence with the
short erase/program operation was not measured. The previous
runtime BOOTSEL sampler was unsafe and has been removed; do not use BOOTSEL to
request the AP on the current image. A lost station connection still brings
the AP back.
Two short LED flashes every two seconds identify an available AP. Source
and browser tests cover this revision. The
[Wi-Fi setup page](http://192.168.4.1/) and optional
[station settings page](http://192.168.4.1/owner.html) use HTTP port 80 while
connected to the Pico AP. A station DHCP address such as `192.168.1.47` has
no consumer web page in the current pre-clock image. While either setup page
is open, it supplies phone UTC about every 30 seconds through a short Pico
challenge. A fresh browser observation can satisfy the job clock limit under
the assumed 250 ms phone-clock error; station SNTP replaces it when available.
The Wi-Fi form includes a prefilled `pool.ntp.org` time-server field. The
[new image booted on Candidate A](docs/development/phase12-wifi-first-flash.md);
the later bounded B phone setup result is recorded above. The current matrix
closes selected phone/iPad commissioning with its documented limits. The
[source review](docs/development/phase12-safari-open-setup-review.md) records
the fixes and remaining target gates. The earlier
[physical-owner contract](docs/development/phase12-7-decision.md) and failed
button attempt remain historical. The production continuation connects SoftAP
DHCP/mDNS, blank captive HTTP, provisioned pre-clock/normal HTTPS,
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
Identify LED/field status and Bluefy read-only WTP `HELLO`/`STATUS`. A later
RF-inhibited Candidate A test accepted native-Pi maximum-profile activation
and repaired Bluefy prepared-file activation through generation 3, a normal
restart, and post-restart BLE readback; see the
[target activation record](docs/development/phase12-profile-activation-attempt.md).
The later generation-3 positive mTLS/WTP and HTTPS readback also passed on the
Mac. Those earlier checkpoints left consumer, recovery and physical assertions
open in the [physical plan](docs/development/phase12-physical-acceptance.md).
The current [closure matrix](docs/development/phase12-closure-matrix.md)
supersedes their historical remaining-work lists with the selected accepted
results and explicit exclusions; broader interoperability is still unqualified.

The blank SoftAP now has a source-tested
[best-effort captive landing](docs/development/phase12-blank-captive-landing-review.md)
with AP-only DNS and a fixed-address browser fallback. The selected iPhone
automatically opened an earlier open-AP test page; the full-erase generic image
has bounded native-Pi evidence only. A separate
[Wi-Fi-only network bootstrap](docs/development/phase12-wifi-only-bootstrap-proposal.md)
is approved for a code-free first station join without Bluefy. Its current
foundation includes a browser/Pico crypto vector and an RF-inhibited
[BOOTSEL gate record](docs/development/phase12-wifi-only-bootsel-gate.md). The
core-1 physical-press run failed. A later no-flash press/AP run passed on the
standard image with core 1 absent; the claim design is narrowed to that
RF-inhibited topology. Earlier devel source served the local network-only
form, admitted one physically granted encrypted submission, trialed station
join and committed a network-only generation after address readback. The
revised consumer source replaces the BOOTSEL mutation with an immediate Wi-Fi
form at the captive root. Optional station details use a separate page.
During the Wi-Fi-only physical run, Candidate A ran the exact `fb091f8`
RF-inhibited image. The selected iPhone
submitted station credentials, and a separately approved USB reboot/readback
proved network-only generation 1 and station address `192.168.1.47`; the final
phone page and AP return after station loss were still open at that historical
checkpoint. A newer source change
temporarily kept the network-only AP available after station join for later
setup upgrade. The revised candidate instead withdraws it on a healthy station
and uses station-loss fallback; the selected GP14 path and its scoped acceptance
are recorded above. That earlier candidate still needed a
repeat target acceptance run. See the
[target record](docs/development/phase12-wifi-only-physical-result.md).

The current Bluefy source requires a fresh password step-up for each exact
staged profile even on a retained bond. While the public default password is
active, the page also waits for an identity-bound USB-local confirmation within
the 30-second provisioning session. The bounded Bluefy/iPhone apply above
exercised this path; it is not full commissioning acceptance.
The versioned engineering [Field-GATT/1 contract](docs/protocol/Field-GATT.md)
and [machine-readable vectors](docs/protocol/Field-GATT-v1-vectors.json) now
keep firmware, both clients and host conformance checks aligned through the
7,168-byte profile limit; broader physical interoperability remains unqualified
beyond the current matrix. Bluefy also
has a test-only prepared-JSON-file import for operator-assisted acceptance. It
does not create or deliver a profile and is not an end-user commissioning flow;
the revised captive-portal flow is tracked in P12.7–P12.12.

- [Accepted architecture](docs/architecture.md)
- [Shared transmitter application and fleet contract](docs/transmitter-application-contract.md)
- [Shared member configuration API foundation](docs/development/shared-transmitter-application.md)
- [Selected Pico 2 W pin-assignment contract](docs/pin-assignment-contract.md)
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

Pin allocation: see the [selected contract](docs/pin-assignment-contract.md) and
[implemented subset and validation](docs/development/pin-allocation.md). Direct RF,
button and indicator pins are boot-applied settings; amplifier/LPF and Si5351
adapters remain unavailable.
