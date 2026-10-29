# Filter selector software validation

The candidate implements the [LPF/band selector contract](lpf-band-selector.md) on Pico 2 W/RP2350, with matching WsprryPi production USB/network management and both browser editors. The current unreleased contracts are extended in place, as requested; no new state or public-read version is introduced. WTP/1 job format is unchanged.

## Source and dependency identity

The starting Pico `devel` revision was `e2fa85e55193e2ce051629ac1787f69600620666`; The implementation checkout also includes Pico documentation-only `d8eec8167c88279835d7d9b61c03055483f42593`. Pi `devel` was `e8d10e11c155cfbb4f441e39ae2e42f5f7e08915`; operator Docs `devel` was `9dc709e4c46d8c6834a2c4471783854f0bb36819`. Tests use candidate working sources from these repositories, including new files, rather than the original clean snapshots. Final delivery is the coordinated selector commit on each branch, whose exact revision is recorded by Git and the session result.

The Linux source snapshots are `/work/filter-pico` and `/work/filter-pi` in the retained `stage2-pi` container. They are overlaid from `git ls-files -c -o --exclude-standard` tar manifests. MbedTLS is explicitly `/work/mbedtls`, pinned at `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`. The firmware uses Pico SDK 2.3.1 `079c6f39023649b154152db30f1d781e884879bc`, picotool `6f6458d792b93685a11423b244a585eaa99eafcf` and installed Arm GNU 15.3.1. Private logs, firmware and captures remain in ignored build/review directories or temporary harness areas.

## Checks

Final Linux host result: **158/158 passed**. All three required production network targets passed, and the production USB client build, management tests, UI producer tests and complete Pi/Pico USB pair passed. Pico HTTP/AEAD browser workflow and Pi rendered selector workflow passed. Both normal and inhibited firmware builds and linked audits passed. The complete Pi UI unit/manifest suite passed after installing its lockfile-pinned `ws` dependency in the task snapshot. Strict Pico and companion operator Sphinx builds and the companion image-delivery regression passed; the Pico checker verified 84 Markdown sources, 17 HTML pages and 1456 local targets with zero errors.

The candidate host suite builds with CMake Debug, `WSPRRY_PICO_BUILD_TESTS=ON` and `WSPRRY_PICO_TEST_MBEDTLS_PATH=/work/mbedtls`. The retained Debian container has Node 18, so `NODE_OPTIONS=--experimental-global-webcrypto` enables its existing WebCrypto implementation for browser crypto fixtures. Initial failures without this flag were environment failures, and the affected checks passed after enabling it. The Linux suite is the authoritative full host result; the existing macOS `event_storage_tests` allocator/headroom baseline is not relaxed.

```sh
cmake --build /work/filter-candidate-host --parallel 4
NODE_OPTIONS=--experimental-global-webcrypto ctest --test-dir /work/filter-candidate-host --output-on-failure --parallel 4
```

Focused selector tests exercise settings syntax/types and closed fields, ownership, polarity, shared resources, ambiguous and whole-job coverage, nominal/programmed bounds, production StreamEngine/FrequencyPolicyEngine admission, boot-frozen settings, persistence/corruption/failure, revision/device/boot refusals, A/B/A inhibition, zero/default/maximum delays with and without amplifier, late/interrupted preparation, output verification failures, normal amplifier tail and cleanup ordering even when amplifier, selector and DMA cleanup fail. These use production policy, adapters and sink logic with deterministic hardware boundaries.

Required Pi network commands run from `/work/filter-pi/src`, using the actual edited Pico sources and pinned MbedTLS:

```sh
WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make wtp-network-runtime-test wtp-network-interop-test wtp-config-interop-test BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= PICO_SOURCE=/work/filter-pico MBEDTLS_SOURCE=/work/mbedtls
```

The USB pair builds the actual Pico `usb_management_driver` in the candidate host build and runs the production Pi management coordinator, UMP framing/ACK, crypto/serialization, journal handlers and shared UI producer. From `/work/filter-pi`:

```sh
make -C src wtp-usb-pair-client-build wtp-usb-management-test SUDO=
node WsprryPi-UI/tests/wtp_usb_settings_test.js
WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node WsprryPi-UI/tests/wtp_usb_pair_test.js src/build/wtp-network/wtp_usb_pair_client /work/filter-candidate-host/usb_management_driver
```

Both pair paths include selector save/readback, GP/polarity, malformed/extra fields, unsupported schemas, changed timing limits, boot mismatch, conflict refusal before writes, preservation through ordinary Config saves and A/B/A restoration. Network Consumer-Radio additionally rejects hostile advertised descriptors and resource documents before journal writes.

Browser workflow commands use retained npm dependencies and current Chrome, with synthetic RAM-backed devices and no physical outputs:

```sh
node tests/operator_cleanup_browser.mjs build/filter-host/consumer_session_driver .impeccable/review --filter-ui-only
```

The Pi rendered PHP fixture runs `tests/wtp_network_ui_integration_test.js` with `WSPRRYPI_UI_FIXTURE_URL=http://127.0.0.1:18785/`, `WSPRRYPI_UI_CAPTURE=0` and `WSPRRYPI_FILTER_CAPTURE_DIR` selecting the ignored review directory. Pico desktop/mobile and Pi desktop/mobile in both existing themes were captured. The actual shared editor and protected Pi/Pico pair are also exercised independently of the rendered mock-management fixture.

## Review corrections

| Finding | Severity and correction | Closure |
| --- | --- | --- |
| Selector and RF reads could describe different worker instants | High: carry selector observation in the same locked sink/worker report as RF | Production build and coherent report tests; separate selector RPC removed |
| Selection needed a final inactive verification before make and a final launch check | High: adapter verifies every output inactive before activation; local launch verifies chosen output without rewriting it | Adapter/fault and sink tests |
| Failed cleanup could skip later outputs or return a false inactive state | High: always attempt RF, amplifier, selector and DMA cleanup in order; retain unknown/inhibition | Normal-tail and injected multi-failure tests |
| JSON key order could make equivalent Pi readback appear different | Medium: compare canonical object keys, retain array ordering and strict shape validation | Both actual source-pair editor workflows |
| Integration target omitted new production Pico compilation units | Medium: add filter settings and selector sources to the paired build | Network build and production pair |
| One invalid entry marked unrelated controls invalid | Medium: logical field paths, targeted `aria-invalid`/`aria-describedby` and a unique polite live summary | Shared editor regression test and independent verdict |
| Pi selects lacked incumbent chevrons; actions touched on narrow screens | Medium: Bootstrap `form-select`, section spacing and wrapping action gaps | All four corrected Pi captures; independent verdict resolved |

The independent Impeccable finish reviewer returned `ship` after scoring all three UI findings resolved across six valid final captures. The separate documenter recorded the built selector component in both existing DESIGN records and sidecars. The mechanical detector returned no findings with a disclosed regex-only degraded mode; it is not a full accessibility or contrast certification. Core review was an adversarial self-review, followed by regression checks; it is not labeled independent review.

## Firmware resources and evidence boundary

Both `WsprryPico` and `WsprryPico-Inhibited` build in `build/filter-firmware` with linked engine, journal separation, stack/heap, allocator, USB topology and RAM-renderer audits. The RF image retains the dedicated aligned 16 KiB worker stack and 32 KiB primary stack; no stack allocation was added for the selector model. Local alarms use the existing monotonic microsecond timer, with millisecond policy intervals and bounded preparation before the unchanged RF start. No new physical timing is claimed.

The local RF image has text 2,781,464 bytes and BSS 383,968 bytes; inhibited has text 2,747,428 and BSS 227,512 bytes. The retained local amplifier image has text 2,737,232 and BSS 381,556 bytes, making this local RF comparison +44,232 text and +2,412 BSS bytes. This is a comparison of those exact local builds, including generated browser assets, not a universal binary-size promise. Final committed build metadata can change text size slightly. Linked flash remains outside reserved journals, with no address/capacity change.

No selector/driver bank is wired. The operator directed reuse of the established GPIO switching result and software integration of selector-before-amplifier/selector-after-amplifier ordering. No new GPIO exercise, firmware installation, RF job or instrument campaign was performed for this slice; no board/settings/restoration state changed. Software fixtures do not qualify physical USB cabling, relay timing, filter response, amplifier readiness, RF power or antenna-ready emissions. Those measurements belong to the actual assembled RF path.
