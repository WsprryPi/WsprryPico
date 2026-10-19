# Project contract

## Identity and scope

WsprryPico is a standalone application and a WsprryPi transmitter backend,
maintained in its own repository. The defined hardware target is Pico 2 W /
RP2350. The [architecture](engineering/architecture.md) defines implementation
boundaries; [WTP/1](engineering/protocol/WTP.md) is the device-neutral job protocol.
Firmware and protocol versions are independent. There is no separate protocol
repository and no RP1 DKMS or Linux hardware-access port.

## Execution and timing

All job producers converge on one `JobService`, ownership state machine and
local execution authority. USB, TCP, browser and standalone paths validate,
load and arm complete jobs. RP2350 owns execution and symbol timing; packet
arrival never sets symbol boundaries. Transport loss does not prove output
inactive or grant a replacement controller ownership.

Standalone operation retains station details, schedules, manual PPM and
no-repeat watermarks. WSPR planning supports automatic Type 1/2/3 selection
and bounded adjacent-window pairs. QRSS, FSKCW and DFCW message inputs accept
at most 32 characters including spaces. Complete jobs independently fit 512
events and 3,600 seconds, including repeats, gaps and tails. The browser compiles
messages before LOAD/ARM; WTP carries complete encoded jobs. See
[finite jobs](engineering/development/extended-jobs.md) and
[WSPR planning](engineering/development/wspr-planning.md).

μChrony supplies UTC discipline; RF carrier correction uses the persistent manual
PPM value. NTP-derived RF calibration and Pico-to-Pi GPIO timing pulses are not
supported. GPS/PPS input is future work in the consolidated backlog. Job launch
retains clock uncertainty, age, ownership, frequency, hardware and output
inhibition checks. A compile or simulated job establishes neither physical
symbol timing nor RF performance.

## Control and authority

USB CDC is the reference WTP transport. Console diagnostics, WTP framing and
[USB management/time](engineering/protocol/USB-Management.md) use separate CDC
interfaces. Logging must not enter either protocol stream. USB management uses
local physical authority, supports no-network configuration and does not grant
transmitter ownership. Network callers cannot select USB authority.

Network WTP/TCP carries the identical WTP/1 stream to the same service.
The consumer image defaults to Plain LAN on station TCP port 31417 after
infrastructure Wi-Fi and accepted network time. Any client that can reach
that port can submit commands under its shared LAN principal. Build-time
`off` and `tls` selections remain explicit; TLS has no automatic downgrade.
Engineering control uses TLS 1.3, ALPN `wtp/1` and device-specific mutual
certificate authentication. Full fleet interoperability is not qualified.

The browser uses the shared, independently versioned
[JSON API](engineering/browser-api.md). Firmware supplies lightweight HTTP handlers
and static assets. It does not host Apache or PHP. Resource schema versions
are independent of the `/api/v1/` namespace. Legacy closed views, explicit
capability negotiation, omission preservation and atomic replacement remain
part of the configuration contract. Saved drafts do not establish complete
configuration, applied hardware or transmit readiness.

Consumer control is available at the station IP/hostname and an available AP's
`/radio` path under [Consumer-Radio/1](engineering/protocol/Consumer-Radio-v1.md).
The saved Wi-Fi password authenticates encrypted, volatile application
sessions. HTTP page delivery is unauthenticated and retains page-substitution
risk. Public setup mutations stay AP-only; LAN setup uses authenticated
wrappers around the same trial/commit authority. Profile-owned Wi-Fi and
station identity retain their transactional setup paths. Lost replies require
authoritative readback and explicit review before another save.

Engineering BLE uses the separately versioned
[Field-GATT/1 contract](engineering/protocol/Field-GATT.md) and its conformance vectors.
It carries unchanged WTP bytes to the same service. Just Works pairing,
application-password enrollment, retained bond epochs and request-bound
step-up protect their respective operations. The public MAC-derived default
is not a secret; ordinary flash offers no confidentiality guarantee.
[Field access](engineering/development/field-access.md) defines trust/reset and
controller-time boundaries. Bluefy offline reuse is unsupported; the
device-served SoftAP portal provides offline consumer setup.

## Setup, storage and hardware

A blank consumer starts setup Wi-Fi. Saved consumers normally keep the AP off.
Every AP activation has a non-sliding ten-minute lifetime from actual
activation, including blank, manual, fallback, field and recovery paths.
Holding/releasing a button, traffic and retries cannot extend the window.
Expiry stays latched until a new deliberate request or a new outage after
stable recovery. A 60-second outage requests fallback; 30 seconds of stable
station recovery rearms a later outage. RF guards defer AP activation without
aborting an accepted job; expiry removes AP clients while preserving station
service. See [consumer access](engineering/development/consumer-lan-access.md).

The default active-low button is GP14, physical pin 19. A debounced release
under 0.4 seconds requests reset; reaching 0.9 seconds held requests shutdown;
reaching nine seconds requests AP after confirmed shutdown. A release between
0.4 and 0.9 seconds requests shutdown. Saved custom or disabled assignments
win. BOOTSEL is not a runtime setup gesture. Strict physical 50 ms/90 s cutoff
assertions remain unqualified.

Versioned journals keep profiles, access authority, standalone configuration,
watermarks and saved progress separate. Interrupted/corrupt selections fail
closed rather than resurrecting superseded credentials or enabled settings.
Reset levels preserve only their defined domains. Upgrade/rollback support
must account for the actual on-flash record versions.

The [pin contract](engineering/pin-assignment-contract.md) requires exclusive GPIO
roles and a validated boot pin plan. Pin/drive changes latch restart and output
inhibition for the boot, including A/B/A saves. GPIO drive is 2/4/8/12 mA,
default 4 mA, independent of reported WSPR dBm. Saved selection, immutable
boot selection and nullable cached ARM-time SDK pad verification are distinct.
A save never programs the pad or proves RF power. Optional amplifier enable
uses the same local sink authority, initializes inactive, asserts before local
RF and deasserts before fallible cleanup. LPF and Si5351 adapters are unavailable.

## Implementation and qualification

The normal `WsprryPico` application uses the 138 MHz PIO/DMA engine.
`WsprryPico-Inhibited` explicitly selects the RF-free simulator;
`WsprryPico-StandaloneRF` remains a compatible explicit RF target. RF capability
preserves saved enablement and all admission guards. Generic deployment images
select no transmit frequency; the operator saves one before enabling schedules.

Native engine limits and [band support](engineering/development/band-support.md) are
separate. Conducted results apply only to their recorded board, source/image,
clock, mode, receiver and RF path. They establish no calibrated transmitter
power, antenna-ready emissions, general USB/WTP compliance or release
reliability. Nondefault drive strengths inherit no all-band qualification.
Experimental frequency consent cannot override physical limits or change a
qualification disposition.

The [shared transmitter/fleet contract](engineering/transmitter-application-contract.md)
defines member/controller domains and recurrence authority. Each member owns
local hardware, validation, timing, cleanup, ownership and persistence. Current
Pico resources implement a bounded foundation; full cross-application parity
is not claimed. Selected work is maintained only in the
[consolidated backlog](engineering/development/consolidated-backlog.md).

## Licensing

Original contributions use [MIT](LICENSE.md). Reused code and dependencies
retain their licenses, attribution and exact source provenance. Credentials,
local SDK paths, captures and generated firmware stay out of maintained source.
Build inputs and release integrity procedures are defined in the
[development guide](engineering/development/README.md).
