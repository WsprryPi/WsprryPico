# Development baseline

The defined hardware target is Pico 2 W / RP2350. The repository contains a
portable WTP/1 core, deterministic host tests and an RF-inhibited firmware
target with persistent standalone configuration and Wi-Fi SNTP, plus separately
built experimental RF bench, USB-time RFWTP and standalone RF images.

Current Phase 11.4 acceptance: [B2 and D2 pass the eight-case controlled native
Linux campaign](phase11-4-three-radio-results.md), using one onboard AP and two
independent USB Wi-Fi clients. The [eight-hour soak](phase11-4-controlled-soak-run.md)
passed, closing Phase 11.4 within its bounded inhibited matrix. This result
supersedes the open B2/D2 status in earlier investigation records below. The
[execution prompt](phase11-4-three-radio-prompt.md) describes the opt-in fixture;
`phase11_4_three_radio_campaign_audit.py` checks a complete private series, and
`phase11_4_three_radio_adversarial.py` checks per-case evidence mutations offline.

Current [Phase 11.5 plan](phase11-5-plan.md) and [review](phase11-5-review.md),
[metric definitions](phase11-5-metrics.md) and the bounded
[instrumentation pilot](phase11-5-pilot.md)
track resource/contention acceptance for the selected 138 MHz PIO candidate.
132/150 MHz physical configurations are untested in 11.5. Selecting another
clock during 11.6 requires affected 11.5 acceptance before using its results.
The [remediation execution and adversarial review](phase11-5-remediation-review.md)
records the SRAM candidate and the remaining physical failure gates.
The [current continuation](phase11-5-closure-work.md) records the later allocator,
stack guard and production-session fixes. [N0 is restored](phase11-5-network-fixture-result.json);
[N1 diagnostic results](phase11-5-n1-progress.md) preserve the earlier failures.
N1t closed exact-image A2 for `8fb3894`; A3 failed browser cadence under RF load.
[The final restored state](phase11-5-n1t-result.json) records **2 of 20 cases
closed**, with no accepted configuration.
The [activity candidate retest](phase11-5-activity-run.md) has four checked images.
Its authorized N1u run failed inhibited conditioning at the production STATUS
cadence gate and restored the setup; its full A2/A3 cases remain unrun.
The [STATUS investigation](phase11-5-status-stall-review.md) records corrected
request-start auditing, Console integer decoding, bounded internal trace reads
and evidence of packet delivery loss. The original N1u STATUS stall remains open.

## Build direction

The portable core uses C++20 and CMake 3.24 or later. The firmware build pins
the Pico SDK, picotool and Arm toolchain and selects `pico2_w` explicitly. The
SDK 2.3.1 (`079c6f39023649b154152db30f1d781e884879bc`) includes the
upstream RP2350 synchronization fixes; use a fresh build directory after an
SDK update. The SDK fetches the pinned picotool build dependency. The
[bounded target USB record](usb-target-validation.md) supplies the separately
authorized BOOTSEL and read-only validation procedure.

Keep builds out of the source tree, normally under build/. Keep local SDK and
toolchain paths in environment settings or ignored CMakeUserPresets.json.
Firmware artifacts belong in build/ or dist/, not beside maintained source.

## Repository layout

- src/: project-owned firmware and portable application code, when introduced.
- tests/: deterministic host tests and separately opt-in target tests.
- cmake/ and scripts/: build helpers when needed.
- docs/: architecture, protocols, development and hardware documentation.
- .github/: contribution templates and future workflows for actual targets.

Generated .pio.h headers are ignored; maintain the corresponding .pio source.
Do not store Wi-Fi credentials in maintained headers. Use ignored local config
or device provisioning; sanitized configuration examples should be trackable.

The [dual USB CDC guide](usb-cdc.md) documents the adapter and optional
descriptor test using the pinned local TinyUSB headers. The
[strict WTP endpoint guide](wtp-endpoint.md) adds wire tests, sanitizer commands,
image memory-layout checks and an opt-in read-only USB probe.

The [portable RF stream guide](rf-stream.md) covers the experimental generator,
streaming adapter, host benchmark, sanitizers and Arm library cross-build.
The [PIO/DMA driver guide](pio-dma-driver.md) covers the SDK port, local launch,
resource ownership, host fault tests and the link-only target.
The [RF bench guide](rf-bench.md) covers measured target refill, software BOOTSEL,
and bounded reception using the Harness helper on wspr5.
The [full-frame record](rf-frame-validation.md) adds synthetic frame, abort/rearm,
simultaneous GPSDO comparison and optional offline measurement tests.
The [output/inhibit design](rf-output-design.md) remains a hardware proposal.

The [Phase 11.3 plan and joint checklist](phase11-3-plan.md) records DHCP/mDNS,
hostname deployment certificates, HTTP authority and companion integration.
The [shared identity contract](phase11-3-identity.md) is authoritative for both
applications; [inhibited acceptance](phase11-4-acceptance.md) remains opt-in.
The [G4–G7 recovery acceptance record](phase11-4-g4-g7-results.md) includes
single-board physical evidence, retained failures and the offline-only
`scripts/audit_phase11_4_recovery.py` checker. The checker reads private evidence
directories and performs no device or network operations.
The [E1 two-board record](phase11-4-e1-results.md) adds independent physical
identities/CAs, bidirectional Mac/Linux trust checks and the boot-derived
MAC-suffix naming default. It retains bootstrap/discovery failures and the
unimplemented end-user provisioning flow.
The [B2 association and delivery record](phase11-4-b2-delivery-results.md) retains
the diagnostic watchdog, observer failures and exact AP association evidence.
Standard inhibited images expose opt-in USB `NETLINK` for the current BSSID;
ordinary INFO and polling do not query it. The failed RSSI query was removed.
The read-only target diagnostic accepts `--iot-profile <current-uuid>` with
active boot-enabled recovery and `--controller <private-client-directory>`;
it cannot run a reconnection cycle through that override. B2 remains open.
The [E2/E3 conflict record](phase11-4-e2-e3-results.md) adds the controlled-host
alias conflict and same-name recovery observations. Its companion
`scripts/audit_phase11_4_mdns_conflict.py` also operates only on private files.
The [shutdown-marker investigation](phase11-4-shutdown-results.md) adds verified
nested reset breadcrumbs, idle/normal client trials and a read-only host SSID
comparison. `scripts/check_shutdown_image.py <standard-inhibited.elf>` verifies
actual linked call interception. `--idle-clients` controls the opt-in loop's
status traffic; its packet-baseline gate must pass before WIFI OFF. Diagnostic
`--diagnostic-iot-profile` is read-only, requires externally supervised host
restoration and cannot be used to qualify a shutdown control case.
The [packet-boundary investigation](phase11-4-packet-trace-results.md) adds a fixed
USB trace, locates a failed ARP exchange after successful driver submission, and
reproduces the station-disable watchdog. Both acceptance items remain open.
The [repeated B2/D2 harness](phase11-4-loop-plan.md) defines opt-in independent
USB/packet/native-client observation and bounded stop rules. Its
[execution/review record](phase11-4-loop-results.md) reproduces both original
faults, distinguishes a clock-gated TLS reset and retains localization limits.
`python3 -B tests/phase11_4_loop_tests.py` is hardware-free; the coordinator and
target runners require explicit `--run` authorization and are never run by CI.
The [withdrawal investigation](phase11-4-network-withdrawal-results.md) records
the reviewed lifecycle repair, deterministic/mutation checks, a target watchdog
failure and diagnostic repetitions; acceptance remains open.
The [controlled same-SSID comparison](phase11-4-same-ssid-results.md) retains
a goodbye failure with the host recovery service paused and verifies restoration
of its active and boot-enabled state.
The [second B2/D2 series](phase11-4-b2-d2-repeat-results.md) reproduces actual
ARP/TCP/NSS and goodbye failures and retains the invalidated SSID comparison.
The [B2/D2 repeat record](phase11-4-b2-d2-results.md) retains passing and
incomplete packet/peer cases and the goodbye-grace test repair. Its offline
`scripts/audit_phase11_4_discovery_recovery.py` adds identity-bound HTTPS,
recovery/stability bounds, decoded USB consistency and strict failure retention.
The [released-SDK D2 assessment](phase11-4-d2-sdk231-results.md) separates
shutdown completion from goodbye/cache delivery and recovery. It retains failed
cases, fixes clock-readiness admission in the observer and adds the offline
`scripts/audit_phase11_4_d2_shutdown.py` sub-assessment; D2 remains open.
The [D1–D3 record](phase11-4-d1-d3-results.md) adds orderly goodbye/cache evidence
and retained reconnection failures. `scripts/audit_phase11_4_mdns_withdrawal.py`
checks its private packet, USB and native resolver evidence offline; D1/D3
physical prerequisites and D2 repeatability remain open. The later
[D1 execution](phase11-4-d1-results.md) records the router HTTP 400 blocker,
production baseline, removal of the temporary reservation and ordinary DHCP
cleanup; its [prompt](phase11-4-d1-prompt.md) defines the remaining new-address case.
The [SDK 2.3.1 D1 assessment](phase11-4-d1-sdk231-results.md) adds automatic
adapter address-change coverage after a current-code review. Native Chrome
reproduced the router Apply failure in two form contexts; cleanup was verified
without cycling either Pico, and the physical new-address gate remains open.
The [controlled-hotspot D1 record](phase11-4-hotspot-results.md) captures two real
DHCP changes independent of Orbi and a later production-client success, while
retaining immediate client failures and the post-cleanup management outage.
The follow-up records verified Wi-Fi restoration, the saved AP/ARP correction
and an explicit assessment of the client ARP timing. Its
[sanitized manifest](phase11-4-hotspot-evidence.json) identifies private evidence.
`scripts/phase11_4_hotspot.py` is an opt-in, wspr5-specific engineering fixture;
`scripts/audit_phase11_4_hotspot.py` audits local evidence without device access.
Run its refusal tests with `python3 tests/phase11_4_hotspot_audit_tests.py`.
The [working three-radio setup](phase11-4-radio-results.md) adds independent
radio observation and the DHCP `NOIP` reconnect correction, with a regression
against the actual adapter. It records the verified management power setting,
approved inhibited A flash, and passing same-boot DHCP recovery with native
Linux WTP/HTTPS and the actual production client. That record left native
browser acceptance for the completion below; broader repeatability remains open
and radio association coverage is explicitly bounded.
Run `python3 tests/phase11_4_radio_diagnostic_tests.py` for its hardware-free
capture/refusal/restoration checks.
The [native Chromium completion](phase11-4-browser-d1-results.md) closes D1 for
the user-selected Linux browser scope: same-tab secure status reload after a
real same-boot DHCP change, alongside reference and actual production passes.
It records the working onboard-AP/USB-client arrangement, restoration and
explicit macOS/configuration-form coverage limits.
[D3 execution](phase11-4-d3-results.md) passes bounded actual link loss, native
cache removal, inhibited-job continuity and automatic recovery, with timing gaps
and Chrome failure retained. Its [Orbi report](phase11-4-d3-orbi-research.md)
compares future fault-testing options.

## Current checks

The [Phase 11 network guide](network-control.md) documents optional TLS WTP/TCP,
HTTPS/browser tests, device-specific certificate tooling, build inputs and
recovery. The [review record](phase11-review.md) distinguishes hardware-free
validation from the pending physical network acceptance gate. The
[11.2 plan](phase11-2-plan.md) and [concurrent-management review](phase11-2-review.md)
record the two-core RF ownership design, bounded clients, actual TLS/11.1-client
acceptance, sanitizers, browser checks and remaining target measurements.

The [Phase 10 host acceptance guide](phase10-host-acceptance.md) describes the
SNTP-enabled five-mode images, optional actual-WsprryPi-client interoperability
test and the separately authorized joint target acceptance procedure.

Reproduce and check the hardware-free RF study with:

```sh
python3 scripts/analyze_rf_feasibility.py
python3 tests/rf_feasibility_tests.py
```

The first command prints [the maintained calculation report](../rf-calculations.md).
The second checks report freshness, tone representability, register arithmetic,
absolute timing and analytical spectral coefficients against a direct DFT.
These checks neither access hardware nor qualify RF. See the
[proposed measurement plan](rf-measurement-plan.md) before planning target work.

Build and run the hardware-free core tests with:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

Validate the WTP/1 contract with:

```sh
python3 scripts/validate_wtp_contract.py
```

The command uses only the Python standard library. It checks the schema,
normative vectors, raw JSON rejection cases, framing bytes and checksums,
semantic job invariants, state transitions, and agreement among the protocol
artifacts. It is a contract-artifact check, not an implementation conformance
test.

Review Markdown links and formatting for documentation changes. Once files are
tracked, `git diff --check` checks whitespace in changes; it does not inspect
untracked files. `clang-format` can check C/C++ files when they are introduced.
Build the target firmware with:

```sh
cmake --preset pico2-w
cmake --build --preset pico2-w
```

VS Code recognizes the root through `CMakePresets.json` and the checked-in
extension recommendations. Select the `pico2-w` configure preset. Configure
local SDK paths in the environment or ignored `CMakeUserPresets.json`.

See the [portable-core guide](portable-core.md) and
[firmware-foundation guide](firmware-foundation.md) for boundaries and
limitations.

See the [implementation plan](../implementation-plan.md) and
[WTP/1 contract](../protocol/WTP.md) for the next boundary.

The [frequency correction and alias investigation](rf-correction-validation.md) records the
`CORRECTION` bench command, corrected measurements, remaining frame settling
and identified sampled-square-wave alias.

The [clock comparison](rf-clock-validation.md) records build-selected sample
clocks, carrier-translation and Pi GPIO4 controls, remaining sidebands and
settling, and disk-backed capture storage.

The [encoded WSPR record](rf-wspr-validation.md) documents portable Type 1
encoding, independent decoding of received RF, and an optional complete-frame
RF warmup comparison.

The [UTC and RF job integration record](utc-rf-job-validation.md) documents the
sampled USB time source, explicit RF WTP image, scheduled local execution,
complete conducted capture and independent decode.

The [standalone guide](standalone.md) documents one-time Console configuration,
recurring UTC schedules, CRC32 flash journals, autonomous SNTP policy, new
hardware-free failure tests and the separately selected standalone RF image.

The [inhibited standalone bench record](standalone-physical-validation.md) adds
physical Wi-Fi/SNTP acquisition, configuration/watermark retention, outage
recovery and the repaired journal/boot-sector layout. The later
[standalone RF and wall-power record](standalone-rf-power-validation.md) adds
complete recurring frames, independent decoding without a USB host, and retained
configuration/watermark across power changes.

The [PIO band campaign](band-campaign.md) adds generalized frequency planning,
five-mode WTP jobs and conducted qualification tooling using the Harness WTP
controller and independent receiver/analysis capabilities.

The [conducted campaign results](band-campaign-results.md) retain the complete
75-entry disposition matrix, including failed measurements, interrupted-run
cleanup blockage and the final verified return to RF inhibition.

The [focused 2200 m investigation](2200m-investigation.md) records the later
five-mode 138 MHz pass with QRSS3, repeated clock screens, and an unfiltered
wspr5 GPIO4 tone/QRSS comparison with documented signal-quality criteria.

The [connectivity, memory and remote settings record](connectivity-memory-remote-settings.md)
tracks sandbox-separated observations, USB network-pool diagnostics, DNS time
servers and authenticated browser restart acceptance.
