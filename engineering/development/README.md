# Development guide

The [project contract](../../CONTRACT.md) and [architecture](../architecture.md) define the portable application, transport and Pico adapter boundaries. The [consolidated backlog](consolidated-backlog.md) is the sole selected work list. The reusable [repository and work-harness cleanup instructions](repository-cleanup-prompt.md) define inventory, preservation, prose and validation requirements for explicit cleanup requests.

## Build inputs and layout

The portable core uses C++20 without extensions and requires CMake 3.24. Version-6 presets require CMake 3.25. Firmware C uses C11 with GNU extensions for SDK integration. The Pico target is `pico2_w` / RP2350 Arm.

The [firmware foundation](firmware-foundation.md) specifies Pico SDK 2.3.1 at `079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1 and picotool 2.3.0 at `6f6458d792b93685a11423b244a585eaa99eafcf`. SDK/submodules, compiler, Ninja, Python and picotool source must already be installed. Keep machine-specific paths in the environment or ignored `CMakeUserPresets.json`.

Owned implementation is under `src/`, deterministic tests under `tests/`, build helpers under `cmake/` and `scripts/`, and protocols/schemas/vectors under `engineering/protocol/`. Keep firmware, captures, credentials and generated headers under ignored build/private directories. Maintain `.pio` source rather than generated `.pio.h` headers. Preserve upstream licenses and source provenance.

Normal firmware `all`, the `pico2-w` preset and `scripts/build_pico.sh` select the complete RF-capable 138 MHz `WsprryPico` application. `WsprryPico-Inhibited` selects the simulator; `WsprryPico-StandaloneRF` is a compatible explicit RF target. Generic images select no transmit frequency. The [software/build CI guide](software-build-ci.md) defines Linux checks, deployment manifests, source/version identity, integrity verification and separate main/devel downloads. Installation consumes exact verified bytes.

The [release tooling guide](software-build-ci.md#beta-and-final-firmware-tags) defines beta/final tag builds and explicit publication. Pushes run verification without publishing. Firmware versions and the installer's implementation version are independent; installation downloads a compiled, verified UF2.

## Deterministic validation

Build and run the hardware-free portable core on a supported host:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

Use an unused build directory when existing outputs have another duty. On a Pi, cap parallelism to available resources, normally leaving one core free. Do not retry a known broken local macOS compiler without explicit toolchain repair or local-build authorization. `scripts/check_host.sh` and `scripts/xcode_env.sh` select installed Xcode for an available macOS host setup; they do not install or repair it. Linux CI defines the reproducible software baseline. A host test or build establishes no device timing or RF performance.

Check the WTP artifacts with the Python standard library:

```sh
python3 scripts/validate_wtp_contract.py
```

This validates schemas, normative vectors, raw-JSON rejection, framing and checksums, semantic job invariants and transitions. It is an artifact check, not general implementation or physical conformance.

The [RF calculation report](../rf-calculations.md) is reproducible without hardware:

```sh
python3 scripts/analyze_rf_feasibility.py
python3 tests/rf_feasibility_tests.py
```

The tests check report freshness, tone/register arithmetic, absolute timing and analytical spectral coefficients against a direct DFT. Target evidence is separate. Existing [network validation](network-control.md#hardware-free-validation) covers TLS, browser and production-client fixtures. The consumer browser's `src/network/bootstrap_web` package supplies `npm test` and `npm run build`.

For target cross-builds with retained dependencies:

```sh
cmake --preset pico2-w
cmake --build --preset pico2-w
```

The [firmware guide](firmware-foundation.md) also documents the helper's target and output-directory arguments. Cross-linking does not authorize flashing or RF. Inspect an opt-in script's implementation before running it, even with `--help`. Ordinary checks must not open devices or change services/configuration.

Review local Markdown links and anchors, removed-path references, build/test inputs and generated-site inputs after documentation changes. Run `git diff --check` and inspect untracked text separately; whitespace validation alone does not check links or fixtures.

### Browser interface checks

The registered host suite includes `ui_access_browser_tests` and `ui_access_shipped_tests` for cancellation, lock/request serialization, carrier discovery, response epochs and receipt History. Source and generated scripts must agree before firmware compilation.

With retained npm dependencies and a current Chrome/Chromium installation, the opt-in native browser fixture checks disclosures, modal keyboard focus, login capacity and retirement, Top, selected files, hidden validation, responsive layout and the production HTTP/crypto routes:

```sh
node tests/ui_sections_browser.mjs build-host/consumer_bootstrap_driver build/ui-sections/browser
node tests/ui_sections_browser.mjs build-host/consumer_bootstrap_driver build/ui-sections/certificate engineering
```

Set `CHROME_BIN` to the installed browser executable on hosts using another path. The consumer and engineering checks run sequentially because each owns a fixed local fixture port range. They use RAM-backed synthetic configuration, isolated browser profiles and bounded requests; they access no Pico or RF hardware. The certificate fixture supplies an authenticated principal and does not qualify browser certificate selection or TLS admission. The existing organization and session-timeout browser workflows cover setup/save reconciliation and session lifetime separately.

The shipped Station/Wi-Fi controls also have a production HTTP/AEAD fixture for public settings, lock behavior, independent WSPR/pin saves, a committed lost reply, responsive layout and keyboard navigation:

```sh
cmake -S . -B build-browser -DWSPRRY_PICO_BUILD_FIRMWARE=OFF -DWSPRRY_PICO_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/absolute/path/to/mbedtls
cmake --build build-browser --target consumer_session_driver consumer_bootstrap_driver --parallel 2
node tests/consumer_sessions.test.mjs build-browser/consumer_session_driver
node tests/operator_cleanup_browser.mjs build-browser/consumer_session_driver
PROGRESS_BROWSER_NO_CAPTURE=1 node tests/progress_browser_integration.mjs build-browser/consumer_bootstrap_driver
node tests/consumer_recovery_browser.mjs build-browser/consumer_bootstrap_driver
node tests/hostname_browser_integration.mjs build-browser/consumer_bootstrap_driver
node tests/organization_browser_integration.mjs build-browser/consumer_bootstrap_driver
node tests/wspr_browser_integration.mjs build-browser/consumer_bootstrap_driver
node tests/message_frequency_ui_integration.mjs build-browser/consumer_bootstrap_driver
```

Use the selected candidate source and MbedTLS `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` with recursive dependencies, retained bootstrap npm dependencies and current Chrome. Progress checks cover partial saves, independent drafts, interrupted replies, late edits and explicit application on consumer and engineering pages. Recovery checks use independent browser contexts for conflicts, capacity, keyboard access and selective retirement, including lost self-retirement replies. Both run in the host CI lane and the Pi network-pair workflow. An optional third argument to `operator_cleanup_browser.mjs` or `consumer_recovery_browser.mjs` captures one desktop/mobile screenshot batch from the actual fixture. It is software evidence with a synthetic board, not physical USB/network, installation, timing or RF acceptance. The Pi network-pair workflow runs these checks in addition to its production Pi client/coordinator, source-selection, routing and UI gates; the independent USB-pair workflow remains required.

The Pico host CI lane runs all ten software-only native-browser suites, including hostname identity/rename, organization/navigation, Type 2/3 planning, message-frequency requests and compiled events, operator controls, and both consumer and engineering section/modal checks. Each uses a RAM-backed production-handler fixture and an isolated browser profile. `PICO_BROWSER_NO_CAPTURE=1` suppresses PNG output for the hostname, organization, WSPR and message-frequency suites while retaining viewport, overflow and keyboard assertions; `UI_REVIEW_NO_CAPTURE=1` supplies the existing section-suite capture control. The two section carriers run sequentially because their fixture ports overlap. Physical LAN, first-WSPR and Si5351 probes remain explicit opt-in tools and are excluded from this CI lane.

The [LPF/band selector contract](lpf-band-selector.md) defines optional GPIO selection, coverage, settling, cleanup and validation applicability. Focused registered tests are `filter_selector`, `filter_selector_schema` and `filter_selector_browser`; both companion production network and USB suites remain required for management changes. The existing opt-in browser fixture accepts `--filter-ui-only` after its driver and output-directory arguments to select the shipped selector editor.

### Production Pi/Pico source-pair checks

Management changes use both `wtp-network-loopback` and `wtp-usb-management-pair` recipes from WsprryPi's checked-in `.github/workflows/debian-non-hardware.yml`. Select the intended candidate Pico and Pi sources explicitly, record both revisions and any tested uncommitted changes, and use recursive MbedTLS `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`. Reuse retained dependencies and an unused host-build directory. The core commands below run from the selected Pi checkout; the full workflow also supplies source-selection, routing, compiler-failure and UI gates.

```sh
pico_source=/absolute/path/to/candidate-WsprryPico
mbedtls_source=/absolute/path/to/pinned-mbedtls
pico_host=/absolute/path/to/unused-pico-host-build
cmake -S "$pico_source" -B "$pico_host" \
  -DWSPRRY_PICO_BUILD_FIRMWARE=OFF -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$mbedtls_source"
cmake --build "$pico_host" --target usb_management_driver --parallel 2
WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make -C src wtp-network-runtime-test \
  BACKENDS=simulated ANCILLARY_GPIO=0 SUDO=
make -C src wtp-network-interop-test wtp-config-interop-test SUDO= \
  PICO_SOURCE="$pico_source" MBEDTLS_SOURCE="$mbedtls_source"
make -C src wtp-usb-pair-client-build wtp-usb-management-test SUDO=
node WsprryPi-UI/tests/wtp_usb_settings_test.js
node WsprryPi-UI/tests/wtp_usb_pair_test.js \
  src/build/wtp-network/wtp_usb_pair_client "$pico_host/usb_management_driver"
```

Both carriers exercise production clients/coordinators, handlers, crypto, serialization, framing/ACK, journals and historical/current refusal cases. Failed, skipped, cancelled or timed-out required checks remain unresolved. Hardware-free pair checks provide software evidence; physical USB/network, installer/service operation, local timing and RF require separately identified setups.

## Host tools and analysis

`scripts/usb_inventory.py` provides a read-only, explicitly selected USB Console and WTP inventory. `scripts/console_trace.py` reads bounded diagnostic pages; `scripts/network_trace.py` validates trace framing and identity offline, and `scripts/radio_capture.py` decodes radiotap/802.11 PCAP records offline. `scripts/gp14_diagnostics.py` drives the explicit button diagnostic image. Inspect an opt-in entry point before running it; normal software checks do not open devices.

μChrony supplies UTC discipline and a persisted provisional clock rate. RF correction uses manual PPM only. The [UTC/RF contract](clock-discipline.md) defines compatibility and the independent measurement boundary. GPS/PPS input and the Pico-to-Pi GPIO pulse path are unavailable.

`src/rf_analysis/` contains offline sample-job construction, keyed-signal, reference-carrier, relative-drive, aborted-waveform and RF-presence analysis. Its deterministic regressions use synthetic samples. Enable them with the existing `WSPRRY_PICO_HARNESS_PYTHON` CMake option pointing to an installed Python with NumPy and the qualification harness modules. They establish no physical RF qualification. The same profile registers `wspr_type23_decode_tests` for exact decoder output, frequency/time association, malformed/truncated capture metadata, synthetic audio conversion and decoder failure/timeout handling. CI uses its NumPy-enabled Python for all seven cases and rejects internal skips. The regression opens no receiver or board and uses temporary fake decoder executables only for subprocess failure paths.

The `provisioning_flash_fixture` host target and `scripts/populate_flash_fixture.py` build private offline provisioning fixtures through the production journal loaders. The builder requires an explicit device ID; it does not flash a board. `scripts/firmware_payload.py` verifies that UF2 application bytes match ELF load segments. The USB installer and CI retain their current image integrity checks.

Inhibited diagnostics use `WSPRRY_PICO_JOURNAL_FAULT_STAGE`, `WSPRRY_PICO_JOURNAL_POWER_CUT_FIXTURE`, `WSPRRY_PICO_INDICATOR_FAULT_FIXTURE` and `WSPRRY_PICO_SESSION_DEADLINE_FIXTURE`. Active obsolete names cause a configuration error with the replacement option; remove the old cache selection before using the replacement. Disabled defaults in an existing cache are allowed.

## Engineering references

- [Portable core](portable-core.md), [WTP endpoint](wtp-endpoint.md) and [USB CDC roles](usb-cdc.md).
- [USB installation and preserving upgrades](usb-installer.md).
- [Factory reset and reflash devel from a Raspberry Pi](factory-reset-and-reflash.md), including BOOTSEL and flash_nuke without preinstalled Pico tools.
- [Factory-new Wi-Fi, Pico password and setup-network checklist](factory-new-access-checklist.md) for manual checks from a Mac or Raspberry Pi.
- [WTP/1](../protocol/WTP.md), [USB management/time](../protocol/USB-Management.md), [Field-GATT/1](../protocol/Field-GATT.md), [Consumer-Radio/1](../protocol/Consumer-Radio-v1.md) and the [browser API](../browser-api.md).
- [Standalone configuration, journals and scheduling](standalone.md), [configuration updates](configuration-updates.md), [saved progress](saved-progress.md) and [USB local configuration](usb-local-configuration.md).
- [Shared application resources](shared-transmitter-application.md) and the [member/controller contract](../transmitter-application-contract.md).
- [Contextual transmitter status and Reset Pico](status-console.md).
- [Consumer LAN/setup access](consumer-lan-access.md), [management carriers](management-carriers.md), [web servicing](web-service.md), [sessions](consumer-sessions.md), [session/save recovery](session-recovery.md), [hostname](hostname.md), [browser areas](browser-pages.md) and [device presentation](device-presentation.md).
- [Engineering network control and certificates](network-control.md), [network identity](network-identity.md), [mDNS](mdns-responder.md), [field access/reset policy](field-access.md) and [Linux BLE client](raspberry-pi-ble-client.md).
- [WSPR planning](wspr-planning.md), [finite keyed jobs](extended-jobs.md), [RF stream](rf-stream.md), [PIO/DMA adapter](pio-dma-driver.md), [RF bench](rf-bench.md), [clock limits](clock-support.md) and [band support](band-support.md).
- [Pin assignment](../pin-assignment-contract.md), [boot pin implementation](pin-allocation.md), [GPIO drive](gpio-drive.md), [amplifier enable](amplifier-enable.md) and [transmit indicators](transmit-led-requirements.md).
- [USB time uncertainty](usb-time-uncertainty.md) and [calibration calculation methods](gpio-time-calibration-research-methods.md).

## Operator manual and publication

Current operator instructions are in [the Sphinx manual](../../docs/index.md). Only `docs/` is a Sphinx source tree; engineering contracts, schemas and technical guides stay here and are excluded from public search.

Build with the project-local documentation environment:

```sh
python3 -m venv docs/.venv
docs/.venv/bin/python -m pip install -r docs/requirements.txt
docs/.venv/bin/python -m sphinx -E -a -n -W --keep-going -b html docs docs/_build/html
```

Run these commands from the repository root. After creating the local environment, `make -C docs html` uses that environment and enables warnings as errors. On Windows, create `docs\.venv` with `py -m venv docs\.venv`, install the same pinned requirements with `docs\.venv\Scripts\python -m pip install -r docs/requirements.txt`, then run `docs\make.bat html`.

Validate the built site's local links and the image-loading policy with:

```sh
docs/.venv/bin/python scripts/check_documentation.py
docs/.venv/bin/python tests/test_image_delivery.py
```

The shared scaffold follows WsprryPi-Docs `c0215b6d980ae809dfacdeb9d2ef557dfc71445e`: Sphinx/MyST/RTD navigation, logo/favicon, typography, search/code/table/footer styling, a native mobile menu button and HTML image-delivery hints. Pico retains its operator-only navigation, version-selector contrast/label fixes, skip link and touch targets. Pi-specific compatibility-table styles, unused autodoc/todo/viewcode extensions, the unused antenna asset, unpinned editor dependencies and non-HTML export configuration are outside this scaffold. Its dependencies stay pinned in `docs/requirements.txt`. Attribution is in the [public credits](../../docs/reference/credits.md).

The documentation dependencies do not install an SDK or toolchain. Current instructional screenshots remain under `docs/_static/images/`.

The [UDP logging contract](udp-logging.md) defines the wire profile, independent settings, finite test resources, worker packaging, storage boundaries and validation applicability. Physical logging evidence does not establish RF performance or lossless delivery.
