# Development baseline

Phase 11 is closed within its documented software, bounded physical and scoped
conducted-RF acceptance. The authoritative [Phase 11.7 joint review](phase11-7-review.md)
binds its source pair, assertion-level applicability, host regressions and
retained limitations. Phase 12 is current: its
frozen [Field-GATT/1 protocol and super-user guide](../protocol/Field-GATT.md)
and [conformance vectors](../protocol/Field-GATT-v1-vectors.json),
[implementation plan](phase12-plan.md),
operator-selected [field-access/security contract](phase12-field-access-contract.md)
and [portable review](phase12-review.md), the
[P12.3 hardware-free integration review](phase12-3-review.md), the
[P12.4 portable command/activation review](phase12-4-review.md), the
[P12.5 activation-safety review](phase12-5-review.md), the
[production/acceptance review](phase12-production-acceptance-review.md), the
[BLE local-control continuation](phase12-ble-local-control-review.md), the
[Raspberry Pi BLE and first-class TCP/WTP review](phase12-pi-ble-tcp-review.md),
the [RF-inhibited SoftAP review](phase12-softap-physical-review.md), plus the
separate
[RF-inhibited-first physical plan](phase12-physical-acceptance.md), distinguish
implemented infrastructure and selected product/security policy from open
physical/local-control work. Provisioning/local-control GATT and its live
activator now run in the RF-inhibited production image; candidate
identity/adoption/advertising and one online retained-bond Bluefy
application-authorization exchange are partial physical evidence. Authenticated
BLE controller time, Identify/status and unchanged WTP/1 transport are now
production-connected. Their clean committed image has verified Candidate A
load/boot, preserved state and final RF-inhibited restoration. The native
Raspberry Pi/Linux client also has an exact RF-inhibited Candidate A/wspr5 live
record for identity inspection, authenticated controller time, field status and
WTP `HELLO`/`STATUS`. A later hardware-free continuation production-connects
SoftAP DHCP/mDNS, blank read-only HTTP, provisioned pre-clock/normal HTTPS,
password/cookie admission, controller time and the existing browser/one-
`JobService` API. Its clean RF-inhibited Candidate A image now has bounded
native-Pi evidence for provisioned WPA2/DHCP/mDNS/TLS, password/cookie
admission, same-connection controller time, local status and
`HELLO`/`CLAIM`/`RELEASE`. A later bounded iPhone 17 Pro Max/iOS 27.0/
Bluefy 3.9.3 continuation accepts retained-bond authorization, one authenticated
phone-time exchange, Identify LED/field status and WTP `HELLO` plus read-only
`STATUS`. Bluefy/iOS offline reuse, fresh-password/new-pairing behavior, full
provisioning/activation, arbitrary BLE job control, broader time/LED matrices,
blank generic HTTP, stable-station AP withdrawal, reset controls and most Stage
A rows remain open. P12.3 remains CLOSED_SCOPED within its historical boundary.
Phase 13 broad hardware/release qualification remains open.

The phone-assisted continuation now has a host-tested fresh-password profile
step-up bound to the exact staged digest, apply request and generation. The
public default additionally requires exact-device USB-local confirmation before
apply, and the proof dies with the 30-second provisioning session. The
native-Pi client now implements the same bound step-up and confirmation flow.
Firmware and both clients agree on the full 7,168-byte boundary, including
one-byte fragmentation, and target enrollment expiry revokes and closes an open
provisional session. The source/host contract also has bounded RF-inhibited
native-Pi maximum-profile and Bluefy/iPhone prepared-file activation evidence
on Candidate A; see the [activation record](phase12-profile-activation-attempt.md).
The repaired Bluefy apply reached generation 3 and a normal restart with BLE
readback. Generation-3 positive mTLS and broader commissioning remain open.

The supported [Raspberry Pi/Linux BLE client](raspberry-pi-ble-client.md) adds a
native BlueZ local/bench workflow using the same production GATT contract.
Authenticated TLS 1.3/TCP remains a first-class WTP job-control transport while
USB CDC remains canonical/reference. The Pi BLE claim now has the exact bounded
live record linked above; TCP/TLS in this slice remains a source and
deterministic-host contract, not new physical interoperability evidence.

Phase 11.5 is CLOSED at 6/6 families for its recorded 138 MHz/divider-1
configuration. Its [completion matrix](phase11-5-completion-matrix.md) and
[September 15 standing authorization](phase11-5-completion-authorization-20260915.md)
remain historical evidence. Pico A now retains the Phase 11.6 status-admission
candidate `0e85ff90571c` / UF2
`9ac5a40fe6d9a44a3a0156621b82801488efecafb9f472ba601dbcbb3e138398` /
boot `cab95d7eecad05047fcb1d6806cf9e86`; Pico B remains `8921a7008183` /
boot `6684b4b197d80cfa0ce83b3aaf205cb0`. The
[Phase 11.6 matrix and closure evidence](phase11-6-plan.md) are CLOSED with
explicitly reduced scope: 13 passing rows are accepted, 52 supported
non-passing rows are excluded from acceptance, and the 10 unsupported 4 m/2 m
rows remain configuration boundaries. The final RF authorization stopped after
sequence 177 and is consumed; no further RF is authorized. Older candidate
paragraphs below retain historical evidence identities. The [memory-pressure repair](phase11-5-memory-pressure-review.md)
passes retained LOAD/replay and P1 individual WTP/HTTP capacity during RF;
the [Package 2 review](phase11-5-package2-review.md) accepts assertions 2.2a and
2.2b after paged RF event storage and direct WTP-reservation observability. The
[Package 3 review](phase11-5-package3-review.md) accepts current-image TLS,
slot, partial/stalled HTTP, failed-alert and three distinct WTP timeout paths,
plus the affected browser-resource check. The [Package 4 review](phase11-5-package4-review.md)
accepts exact maximum USB parser pressure and the repaired
[unread-output retest](phase11-5-package4-unread-retest2-result.json), including
same-session pre-DTR silence and fresh DTR recovery. The earlier failed attempts
remain retained. The [Package 5 review](phase11-5-package5-review.md) accepts all
four replay/session/terminal/reclamation rows after eight maximum-event
normalizers, three equivalent bounded-overload cycles and real terminal expiry.
A's last authoritative state is Complete/inactive in boot
`f93fe05254d1523e50b16b0ad248a44a`; the host fixture is restored and B is
Empty/inactive. Capacity/pressure and retention/reclamation execution groups are
closed. The [Package 6 review](phase11-5-package6-review.md) accepts all fourteen
R3 groups, twenty-four mandatory rows and seven features after exact source-impact
and evidence-applicability review. It closes R3 without new physical work. The
[Package 7 review](phase11-5-package7-review.md) closes all 18 R4 rows using
current-image authority, interruption and production-owner evidence. The
[Package 8 review](phase11-5-package8-review.md) closes all eight R5 rows with
repaired network recovery, journal rotation, autonomous scheduling and full
restoration evidence. The [Package 9 review](phase11-5-package9-review.md)
retains a complete 1,800-second mixed workload and all five quiet windows, but
post-N heap deltas of 12,432, 12,432 and 11,944 bytes and a 7,216-byte final-Q
delta fail the unchanged 1,024-byte gate. Cumulative Package 9 RF is 1,164.4 of
1,200 seconds, leaving too little for another complete packet. The
[Package 10 review](phase11-5-package10-review.md) selects matched replay-history
normalization without changing firmware or the limit, but the corrected packet
was blocked before RF by the mandatory independent wireless-client fixture.
Package 10 used four of 480 authorized RF seconds, all in a stopped frequency-
sequence attempt; thirteen corrected preflights used no RF and restored cleanly.
Package 11 qualified the separate two-host fixture and passed its zero-RF
admission. Its first RF attempt stopped after eight warmups and the matched
baseline when clock polling reused the transport backoff; the zero-RF
clock-poll retest passed. [Retry 1](phase11-5-package11-retry1-review.md) then
passed that repaired path, eight warmups, the matched baseline and baseline
timing, but root-run WsprryPi rejected `pi`-owned private keys before the first
production ARM. The credential-owner repair passed a Linux host-only zero-RF
retest. [Retry 2](phase11-5-package11-retry2-review.md) verified that repair but
stopped before reservation after its 360-second memory window ended 224 bytes
below the unchanged gate while prior complete terminal records were still
inside their one-hour retention. It charged zero RF. [Retry 3](phase11-5-package11-retry3-review.md)
cleared both preflight gates, completed eight warmups, the matched baseline and
the first 600-second cycle, then stopped because the host reducer ignored the
complete USB lifecycle events it had received and considered only five-second
STATUS snapshots. The repaired event-plus-STATUS reducer passed an exact-source
zero-RF replay and two adversarial assessments. [Retry 4](phase11-5-package11-retry4-review.md)
then completed the exact 16-job/356.8-second fresh campaign. Its 56,984-byte
baseline, 57,080/57,128/56,608-byte post-N windows and 57,032-byte final Q pass
the unchanged 1,024-byte limit with a 520-byte nonmonotonic post-N span. Heap,
stack, timing, fault, capture and restoration gates pass; the independent
[result](phase11-5-package11-retry4-result.json) and 67-mutation
[adversarial assessment](phase11-5-package11-retry4-adversarial.json) close R6
and Phase 11.5. Package 11 cumulative accounting is 41 jobs / 495.4 planned
seconds. All four stopped attempts remain preserved.

## Historical Phase 11.5 execution chronology

The following paragraphs retain contemporaneous states and device identities.
They do not override the current 6/6 and scoped Phase 11 closure above.

R2: [seven-job closure and review](phase11-5-r2-continuation-review.md).
R2 is **7/7 jobs**; R1 remains **5/5** through documented affected-check reuse.
The R1/R2 historical candidate is 2e43110 at physical 138 MHz/divider 1/RAM/listener on.
At R2 closure devices and host were restored with CONFIG 34/34. R3–R6 remain open and
full accepted configurations remain empty. Original failed assessments are retained.

The accepted [R3-COMPLETE-20260913-v2](phase11-5-r3-complete-authorization-prompt.md)
authorized the completed R3 implementation and finite physical campaign.
Pico `7d183978d08d` and Pi `bba4024` implement the selected 32-character and
3,600-second limits. E0a independently passed seven idle assertions; S0 passed
two finite RF jobs, including a 32-character, 384-event QRSS message lasting
143.250001 seconds. [Immutable validation checkpoints](phase11-5-acceptance-ledger.md#incremental-v2-validation)
retain scoped passes. Physical hour and saturation evidence is retained and
Package 5 reclamation and Package 6 closeout are accepted. A retains the tested
image and dedicated test configuration; see [campaign progress](phase11-5-r3-v2-progress.md)
for the closed R3 execution state.

Historical pre-v2 status: R3 was OPEN after B2 passed fourteen further transport cases and C0
confirmed a target allocation panic during idle 65,536-byte admission. A is
reconciled inactive/unowned in recovery; diagnostic firmware requires new flash
authority. The exact [D0 diagnostic packet](phase11-5-r3-allocation-d0-execution.md)
was prepared awaiting approval; accepted v2 superseded that approval boundary.
See the historical [remaining-work prompt](phase11-5-r3-final-completion-prompt.md)
and [R3 execution and adversarial review](phase11-5-r3-completion-review.md).
A1g's observation rule was approved; network admission then failed before RF.
The [network diagnosis](phase11-5-r3-network-diagnosis.md) distinguishes AP/DUT
state disagreement, normal terminal expiry and A1h's transient-state harness bug.
The user approved one additional idle Wi-Fi cycle and two conditional Tones;
[A1h2](phase11-5-r3-retained-a1h2-execution.md) continued the unused allowance.
The current review records its independently audited outcome and remaining R3
work. The retained test configuration remains the baseline.
The [comprehensive prompt](phase11-5-r3-completion-prompt.md) remains unfinished.
[Failure triage](phase11-5-failure-triage.md) separates confirmed harness defects,
observation misses, unresolved prerequisites and administrative approval history.

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

The historical [Phase 11.5 plan](phase11-5-plan.md) organizes six acceptance
families with realistic normal traffic separated from stress and overload. At
the checkpoint retained in the following paragraphs, the ledger recorded
**4 of 6 revised families closed** and an empty accepted-configuration list.
The authoritative current section at the top of this file and the
[current ledger](phase11-5-acceptance-ledger.md) now close all 6/6 families for
the recorded 138 MHz/divider-1 configuration.
The [documentation reorganization review](phase11-5-test-reorganization-review.md)
maps all 20 legacy cases without changing code, runners or historical results.
The historical e20ae8b [R1 executor and review](phase11-5-r1-review.md) close **5 of 5 assertions**:
four frozen layouts, six target intervals, three bounded idle allocation probes,
matched quiet retention, stack guards and observer costs. This covers the exact
`e20ae8b` physical 138 MHz/divider-1/RAM/listener-on candidate, with inhibited
150 MHz regression. Both boards and host were restored, including permanent
time.local. Earlier DNS failures and a later unlocalized Mac NTP timeout remain
preserved. No RF jobs ran in that historical R1 campaign; the later R2 closure
is recorded above. Package 6 and the R3–R6 closeouts were still outstanding at
that checkpoint; the current section records their later closure.

Historical [Phase 11.5 review](phase11-5-review.md),
[metric definitions](phase11-5-metrics.md) and the bounded
[instrumentation pilot](phase11-5-pilot.md)
track resource/contention acceptance for the selected 138 MHz PIO candidate.
132/150 MHz physical configurations are untested in 11.5. Selecting another
clock during 11.6 requires affected 11.5 acceptance before using its results.
The [remediation execution and adversarial review](phase11-5-remediation-review.md)
records the SRAM candidate and the remaining physical failure gates.
The [historical continuation](phase11-5-closure-work.md) records the later allocator,
stack guard and production-session fixes. [N0 is restored](phase11-5-network-fixture-result.json);
[N1 diagnostic results](phase11-5-n1-progress.md) preserve the earlier failures.
N1t closed exact-image A2 for `8fb3894`; A3 failed browser cadence under RF load.
[That attempt's final restored state](phase11-5-n1t-result.json) records **2 of
20 historical cases closed on 8fb3894**, with no accepted configuration. This
does not count current-image or revised-family acceptance.
The [activity candidate retest](phase11-5-activity-run.md) has four checked images.
Its authorized N1u run failed inhibited conditioning at the production STATUS
cadence gate and restored the setup; its full A2/A3 cases remain unrun.
The [STATUS investigation](phase11-5-status-stall-review.md) records corrected
request-start auditing, Console integer decoding, bounded internal trace reads
and evidence of packet delivery loss. The original N1u STATUS stall remains open.
The [single A2/A3 attempt](phase11-5-single-attempt.md) subsequently passed the
complete inhibited matrix, then failed 138 MHz conditioning on production STATUS
cadence. It stopped and restored both device and host; no RF jobs or new full
acceptance cases followed.
The focused [STATUS delivery repair](phase11-5-status-delivery-repair.md)
reproduces outgoing-frame corruption in the pinned CYW43 driver and preserves
frames across receive polling. Its [execution prompt](phase11-5-status-delivery-prompt.md)
and [bounded target check](phase11-5-status-delivery-check.md) cover this issue
only; they do not restart the full acceptance matrix.
The single 138 MHz RF-idle check passed 300 seconds of nominal traffic and
360 seconds of USB observation, then restored the setup. No TX credit wait
occurred, so target exercise of the repaired path and historical-stall causation
remain unproven. Phase 11.5 acceptance counts and clock status are unchanged.

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

### Historical Phase 11.4 investigation chronology

The open statements below describe intermediate investigations. The current
bounded Phase 11.4 acceptance is the closed matrix and soak summarized above.

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
recovery. The historical [review record](phase11-review.md) distinguishes its
hardware-free validation from then-pending physical work; the later
[Phase 11.7 review](phase11-7-review.md) supplies the current bounded disposition. The
[11.2 plan](phase11-2-plan.md) and [concurrent-management review](phase11-2-review.md)
record the two-core RF ownership design, bounded clients, actual TLS/11.1-client
acceptance, sanitizers, browser checks and historical target-measurement boundary.

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

See the [implementation plan](../implementation-plan.md),
[Phase 12 field-access/security contract](phase12-field-access-contract.md),
[RF-inhibited-first physical plan](phase12-physical-acceptance.md) and
[WTP/1 contract](../protocol/WTP.md) for the current boundary.

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
