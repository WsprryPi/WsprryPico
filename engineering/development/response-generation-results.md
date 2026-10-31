# Response generation measurements

Measured 2026-10-31. Bounded generation removes complete LOAD response copies from HTTP and USB. The largest tested encrypted HTTP response used 87.1% less peak response allocation; the largest USB LOAD fixture used 95.3% less. Total host processing time increased for these generated replies. These are software measurements, not physical Pico heap or timing measurements.

## Sources and method

- Pico baseline: `408c0865db7d543ba9ffdc3ac4db45b3c97053b5`.
- Pico candidate: the implementation accompanying this report on `codex/bounded-response-generation`, tested as uncommitted changes over that baseline. The raw measurement file records the candidate input SHA-256.
- Pi baseline: `25c55133bf6cf80c563b16497acadd90007651ff`, plus the accompanying 16-line production-crypto test-adapter update on the matching feature branch. No production Pi implementation changed.
- Host: AppleClang 21.0.0, macOS ARM64, Debug libraries; identical candidate probe sources compiled against each version. Each reported number is the median of 21 separate process runs after warmup.
- TLS dependency: Mbed TLS `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` with its pinned framework submodule.

Allocation instrumentation counts requested C++ and nullable-buffer bytes during response construction and drain. It excludes allocator metadata, preexisting job/adjustment storage, sockets, TLS transport buffers, incoming requests and unrelated application state. Sharing an immutable adjustment list extends its lifetime; it does not eliminate that storage. The measurements cannot be added directly to a whole-device heap estimate.

The fixtures hold inputs, output chunking, identities, keys, nonces and sequences constant. Every baseline/candidate response length and digest matched. Separate tests compare complete JSON strings and complete encrypted packets, including existing cryptographic vectors. The 512-adjustment plaintext/USB fixture exceeds the existing encrypted consumer response limit and is not claimed as an admissible encrypted response.

## Peak response allocation

All figures are bytes. Generated rows identify the number of adjustments. USB figures include the escaped management envelope; encrypted HTTP includes the consumer packet.

| Fixture | Before | After | Saved | Reduction |
| --- | ---: | ---: | ---: | ---: |
| `capabilities` | 10,008 | 7,407 | 2,601 | 26.0% |
| `application` | 8,024 | 6,795 | 1,229 | 15.3% |
| `http-load-162` | 18,547 | 3,360 | 15,187 | 81.9% |
| `http-load-256` | 28,981 | 3,360 | 25,621 | 88.4% |
| `http-load-512` | 57,397 | 3,360 | 54,037 | 94.1% |
| `encrypted-http-load-162` | 19,834 | 4,184 | 15,650 | 78.9% |
| `encrypted-http-load-256` | 32,510 | 4,184 | 28,326 | 87.1% |
| `usb-load-162` | 38,751 | 5,664 | 33,087 | 85.4% |
| `usb-load-256` | 60,559 | 5,664 | 54,895 | 90.6% |
| `usb-load-512` | 119,951 | 5,664 | 114,287 | 95.3% |
| `usb-512` | 2,130 | 2,130 | 0 | 0.0% |
| `usb-18000` | 37,106 | 37,106 | 0 | 0.0% |
| `usb-28000` | 57,106 | 57,106 | 0 | 0.0% |

Progress, hardware, status, operations, config, station, pins and filter-selector fixtures had identical allocation counts and peaks before and after. Already materialized USB replies retain their existing frame buffer; no constant-memory claim applies to them. Capability/application documents use counted fragments, while large LOAD replies use the owned generator.

## Retention and allocation pressure

| Fixture | Retained before → after | Largest request before → after | Allocation calls before → after |
| --- | ---: | ---: | ---: |
| `capabilities` | 5,056 → 3,983 | 5,056 → 3,983 | 114 → 87 |
| `application` | 2,640 → 2,331 | 2,544 → 2,235 | 212 → 206 |
| `http-load-256` | 28,453 → 3,360 | 4,096 → 2,176 | 782 → 9 |
| `encrypted-http-load-256` | 28,634 → 4,184 | 4,096 → 2,176 | 788 → 22 |
| `usb-load-512` | 0 → 0 | 4,096 → 2,176 | 1595 → 37 |

Retained means live allocation at the probe checkpoint. USB is measured after the frame drains, so its zero retained value is not a claim that pending output uses no storage. HTTP pending generated bodies retain a fixed rendering window and source/index ownership rather than all serialized bytes.

## Processing tradeoff

Microseconds on the host; these are observations rather than real-time guarantees. “Longest call” is the largest instrumented preparation/count/render call within a run; it excludes network scheduling and is not maximum end-to-end latency.

| Fixture | Total before → after (µs) | Longest call before → after (µs) |
| --- | ---: | ---: |
| `http-load-162` | 148.1 → 199.9 | 100.2 → 11.0 |
| `http-load-256` | 224.5 → 307.9 | 147.4 → 12.5 |
| `encrypted-http-load-162` | 458.1 → 543.7 | 411.5 → 35.2 |
| `encrypted-http-load-256` | 670.4 → 826.6 | 598.5 → 33.8 |
| `usb-load-162` | 1084.6 → 1177.3 | 965.8 → 107.6 |
| `usb-load-256` | 1631.0 → 1784.0 | 1446.1 → 112.8 |
| `usb-load-512` | 3164.6 → 3525.8 | 2790.8 → 123.2 |

The generated paths trade repeated integer formatting and checkpoint lookup for lower memory retention and shorter foreground steps. USB still traverses the source to count escaped bytes and again to emit them. Counting advances by at most 1,024 raw bytes per poll, using exactly the emission escaping rules. No frame header is visible until the exact escaped length is admitted. This work does not establish higher throughput or measured physical USB responsiveness.

## Linked Pico image cost

Normal 138 MHz Pico 2 W cross-builds used Pico SDK `079c6f39023649b154152db30f1d781e884879bc` (2.3.1), Arm GNU 15.3.1 and picotool `6f6458d792b93685a11423b244a585eaa99eafcf`.

| ELF accounting | Before | After | Change |
| --- | ---: | ---: | ---: |
| text | 2,914,024 | 2,925,472 | +11,448 bytes |
| data | 0 | 0 | 0 |
| bss | 383,992 | 384,032 | +40 bytes |
| Linker heap capacity | 91,432 | 91,392 | −40 bytes |
| Core 0 reserved stack | 32,768 | 32,768 | 0 |
| Core 1 reserved stack | 16,384 | 16,384 | 0 |

The baseline archive has unknown Git metadata and the candidate identifies a dirty source tree; linked-image deltas therefore include differing provenance strings. Heap capacity is a linker reservation, not measured free heap or peak use. Fixed scratch arrays and cipher state also use stack/owned storage. Compiler frame reports and linker guards do not establish runtime stack high-water.

## Reproduction

Build the baseline and candidate host libraries in separate directories with
Debug settings and the pinned TLS source. The selected Python environment needs
`jsonschema` for the contract checks. Install the pinned browser dependencies
through the existing project recipes before browser checks.

```sh
cmake -S "$BASELINE_SOURCE" -B "$BASELINE_BUILD" \
  -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$MBEDTLS_SOURCE" \
  -DPython3_EXECUTABLE="$TEST_PYTHON"
cmake --build "$BASELINE_BUILD" --parallel 4
cmake -S . -B "$CANDIDATE_BUILD" \
  -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$MBEDTLS_SOURCE" \
  -DPython3_EXECUTABLE="$TEST_PYTHON"
cmake --build "$CANDIDATE_BUILD" --parallel 4
ctest --test-dir "$CANDIDATE_BUILD" --output-on-failure
```

Run the same probes against both:

```sh
python3 scripts/measure_responses.py \
  --baseline-source "$BASELINE_SOURCE" \
  --baseline-revision 408c0865db7d543ba9ffdc3ac4db45b3c97053b5 \
  --baseline-build "$BASELINE_BUILD" \
  --candidate-build "$CANDIDATE_BUILD" \
  --mbedtls-source "$MBEDTLS_SOURCE" --runs 21 \
  --output build/response-generation-evidence/metrics.json
```

The ignored evidence directory retains raw samples, digests and a compact summary. The checked-in probes make the comparison reproducible; timing varies by host and load.

## Behavior and integration checks

The final macOS host run passed **170/170** tests. Six selected checks passed
under AddressSanitizer and UndefinedBehaviorSanitizer: generated sources, the
full USB generated-response path, HTTP server backpressure, USB management,
USB vectors and consumer crypto. Ten native Chrome suites passed through the
final production HTTP/crypto drivers: operator cleanup, progress, consumer
recovery, submission, hostname, organization, WSPR, message frequency and both
consumer/engineering section layouts.

New tests exercise exact old/new bytes at zero, one, 162, 256 and 512 adjustments,
maximum-width integers, frozen ownership, one-byte retries, escaping across
windows, nullable allocation failures, no allocation during emission, HTTP
backpressure with a second connection, USB incremental preparation and deadline,
and explicit USB ACK authority. The full USB regression uses LocalUsbApi,
BrowserApi, JobService and the production StreamEngine preparation path; its
sink refuses any RF launch.

A full host run initially had two fixed-port TLS startup failures while another
checkout was running tests on the same port. Both passed immediately in an
isolated retry, followed by the complete 170-test successful run. A sanitizer
selection initially included USB vectors without building their driver; building
that target and rerunning all six checks passed. These failures were resolved,
not counted as successful checks.

The Pico 2 W cross-build passed its linker memory, stack, USB, RF image and journal
audits. No board was flashed, no physical USB operation or RF test was performed,
and no host service was changed. Software fixtures do not qualify device timing,
installation, physical heap high-water or RF behavior.

### Paired Linux integration

The isolated wspr5 harness uses the Pi and Pico revisions above with their stated
uncommitted changes and the pinned Mbed TLS source. SHA-256 comparison confirmed
all 384 candidate production/build files matched the local isolated worktree.
The measurement input manifest is
`8b6d73ea8c55c08c9709ebe19927d54d0214f508b1e8c5fba746ef8c0076537f`.

Commands use the checked-in Pi `debian-non-hardware.yml` recipes with explicit
candidate source selection:

```sh
export WSPRRYPI_DISABLE_HARDWARE_ACCESS=1
python3 "$PI/scripts/generate_control_contract.py" --source "$PICO" --check
make -C "$PI/src" wtp-network-runtime-test \
  BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= -j2
make -C "$PI/src" wtp-network-interop-test wtp-config-interop-test \
  SUDO= PICO_SOURCE="$PICO" MBEDTLS_SOURCE="$MBEDTLS"
cmake -S "$PICO" -B "$PICO_HOST" \
  -DWSPRRY_PICO_BUILD_FIRMWARE=OFF -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DCMAKE_BUILD_TYPE=Debug
cmake --build "$PICO_HOST" --target usb_management_driver --parallel 2
make -C "$PI/src" wtp-usb-pair-client-build wtp-usb-management-test SUDO= -j2
node "$PI/WsprryPi-UI/tests/wtp_usb_settings_test.js"
WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node "$PI/WsprryPi-UI/tests/wtp_usb_pair_test.js" \
  "$PI/src/build/wtp-network/wtp_usb_pair_client" "$PICO_HOST/usb_management_driver"
```

The network runtime check passed 910 production WTP assertions. Actual network
interoperability passed named/explicit-IP TLS identity, recovery, partial I/O,
lost LOAD/ARM/ABORT same-request replay, ownership, boot/device binding and the
60-second scheduled-wait case. Configuration interoperability passed the current
contract, strict negative cases, persistence/journals, consumer station/AP and
engineering carriers, shipped browser producers, shared resources, amplifier
and GPIO policies, and same-session recovery.

Supplemental network checks passed UDP worker/logging checks, 11 filesystem
logging lifecycle tests, production finite browser-load and INI round-trip,
TLS observer, catalog, selected-interface replies under route changes in private
namespaces, and rollback. The filesystem logging tests require `umask 022`;
wspr5's group-writable default initially caused the intended policy-safety
refusal. No validator was relaxed.

Run logs are retained in `build/response-generation-evidence/`. These are local
workflow-recipe results, not a claim that a GitHub Actions run completed.

The required USB pair passed production Pi client build and negative checks,
UI settings serialization, UMP framing and explicit ACK, schema/identity/replay
refusal, deadlines/cancellation, advertised policy refusal before writes,
blank-name/Wi-Fi lifecycle, station progress, configuration preservation and UTC
synchronization. The added full generated-LOAD USB path also passed on Linux.
Both required actual production-carrier suites completed successfully.

Source-selection verification passed: both client and TLS fixtures executed an
edited production-source marker, and missing source/compiler errors failed
closed. Its initial attempt collided with the still-running TLS suite's fixed
port; the sequential retry passed. Supplemental logging-browser checks passed
on retry after the competing builds/browser work subsided. Initial failures
and successful retries are retained separately in the evidence directory.

### Documentation impact

The response architecture and measurement report are new; the web-service
reference links the shared generation paths and states the static task bound
without a stale host-specific size. Operator instructions and protocol schemas
remain unchanged because resource bytes, limits, authentication, job semantics
and delivery authority are preserved. Pi operator documentation needs no change
for its test-adapter-only update. No documentation follow-up is required for the
implemented behavior.

### Supplemental browser limitation

The unchanged Pi rendered USB-profile fixture
`wtp_usb_ui_integration_test.js` timed out on wspr5 waiting for application
scripts. A temporary diagnostic showed it had selected `about:blank`, with no
scripts or application document loaded. Retrying the direct Chromium binary
produced the same timeout. The preceding USB Logs browser fixture passed. The
later mocked network/fleet/recovery browser steps were not reached in that
supplemental sequence. A native macOS attempt could not start PHP because PHP
is unavailable there. No application assertions were weakened and no additional
Pi UI changes were made. The complete GitHub workflow job is therefore not
claimed green; the required actual network and USB source-pair suites, ten Pico
native browser suites and 170-test host suite did pass as recorded above.
