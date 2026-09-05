# WTP endpoint implementation and validation

Date: 2026-09-05. Started from `devel` at `7550a3b`. This record accompanies the
Step 5 implementation commit. Tests/builds used the pre-commit working sources;
firmware identity therefore contains the preceding revision with `-dirty`.
No release image or target qualification is implied.

## Changed files

| File | Reason |
| --- | --- |
| `src/wtp/json.hpp`, `src/wtp/json.cpp` | Strict bounded UTF-8/JSON validation and non-owning value access. |
| `src/wtp/codec.hpp`, `src/wtp/codec.cpp` | Closed request schemas, typed decoding, original-payload identity and wire response encoding. |
| `src/wtp/endpoint.hpp`, `src/wtp/endpoint.cpp` | HELLO/session binding, framing, ordered bounded TX, advisory events and logical closure. |
| `src/wtp/job_service.hpp`, `src/wtp/job_service.cpp` | Preserve response snapshots, apply schema failure after replay, avoid invalid-HELLO session allocation, retain historical LOAD/ARM results and terminal LRU behavior. |
| `firmware/main.cpp` | Integrate endpoint with isolated USB adapter, retain partial input and service jobs independently of connection state. |
| `firmware/CMakeLists.txt` | Reserve a 16 KiB RP2350 stack without heap overlap using existing SDK linker controls. |
| `CMakeLists.txt` | Add codec/endpoint sources, wire/probe tests and firmware compiler stack-usage reports. |
| `tests/endpoint_driver.cpp` | Deterministic byte-stream driver using real endpoint/service and an inhibited/fault-injectable mock engine. |
| `tests/endpoint_tests.py` | Independent schema/monitor checks, normative request fixtures, syntax rejection, all operations, lifecycle/replay/session/resource tests. |
| `tests/wtp_probe_tests.py` | Verify opt-in gate and fragmented read-only probe I/O with mocked descriptors. |
| `scripts/wtp_probe.py` | Separately opt-in HELLO/CAPS/GET_CLOCK/STATUS/PING board probe; no job mutation. |
| `scripts/check_endpoint_image.py` | Inspect ELF symbols for stack/heap separation without device access. |
| `README.md` | Report implemented USB endpoint and unqualified target/RF boundary. |
| `docs/architecture.md` | Record portable endpoint integration. |
| `docs/development/README.md` | Link endpoint checks and development guide. |
| `docs/development/portable-core.md` | Update adapter status and response-snapshot description. |
| `docs/development/firmware-foundation.md` | Replace obsolete framing-only status. |
| `docs/development/usb-cdc.md` | Describe the endpoint above the existing transport and update manual expectations. |
| `docs/development/wtp-endpoint.md` | Document semantics, limits, trust, closure and opt-in validation. |
| `docs/development/wtp-endpoint-validation.md` | Record this implementation, checks and review. |
| `docs/implementation-plan.md` | Mark USB transport and Step 5 complete; identify RF feasibility as next. |

The existing `.vscode/settings.json` change is unrelated and excluded. No other
repository, normative WTP artifact, SDK source or physical RF engine was changed.
No new external library was introduced.

## Validation commands

Executed from the repository root:

```sh
cmake --build --preset host-debug
ctest --preset host-debug
cmake -S . -B build/endpoint-sanitize -G Ninja -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'
cmake --build build/endpoint-sanitize --parallel
ctest --test-dir build/endpoint-sanitize --output-on-failure
python3 scripts/validate_wtp_contract.py
cmake --build --preset pico2-w
python3 scripts/check_endpoint_image.py build/pico2-w/firmware/WsprryPico.elf
arm-none-eabi-size build/pico2-w/firmware/WsprryPico.elf
clang-format --dry-run --Werror src/wtp/json.hpp src/wtp/json.cpp src/wtp/codec.hpp src/wtp/codec.cpp src/wtp/endpoint.hpp src/wtp/endpoint.cpp src/wtp/job_service.hpp src/wtp/job_service.cpp tests/endpoint_driver.cpp firmware/main.cpp
git diff --check
```

The existing host-debug configuration includes the optional descriptor test
against the pinned local TinyUSB checkout. For a fresh equivalent configuration:

```sh
cmake --preset host-debug -DWSPRRY_PICO_TEST_TINYUSB_PATH="$PICO_SDK_PATH/lib/tinyusb"
```

Results: six host tests pass, including descriptor inspection. Five sanitizer
suite tests pass; that separate build does not enable the optional C descriptor
test. WTP artifact validation passes its 23 schema, 7 raw JSON, 1 framing and
8 transition cases. Firmware builds with the pinned toolchain and RF inhibition.
Image symbols confirm a 16 KiB primary stack excluded from the heap/core-1 stack.
Formatting, whitespace and changed Markdown links are checked.

The SDK emits the existing warning about no separately installed matching
picotool; its pinned build-directory copy builds successfully. No system tool
installation was performed.

## Adversarial review and closed findings

- Cached typed responses lacked full wire snapshots. STATUS, GET_CLOCK and ARM
  now retain their original sampled data; wire replay tests verify equality.
- Generic JSON traversal could materialize oversized invalid arrays/objects.
  Object lookup now scans views; schema arrays stop at their defined limit plus
  one. Maximum legal payload/event tests and malformed-input checks pass.
- The SDK default stack, and an initial 4 KiB reservation, were insufficient for
  the deepest parser/caller combination indicated by compiler reports. Reserve
  16 KiB in main SRAM and verify non-overlap from the linked image. Target stack
  high-water remains unmeasured.
- Invalid HELLO bodies could consume finite service sessions. Reject them before
  allocating a new session; a twenty-session negative test verifies recovery.
- Retained terminal jobs lost resource-level LOAD/ARM results after a newer job.
  Retain typed-value digests/results and refresh terminal LRU on access. Tests
  cover newer jobs, response-cache eviction, immutable identity and terminal LRU.
- Initial fixture tests conflated body-schema validity with job semantic validity.
  They now test schema decoding separately and route semantic negatives through
  the real service. Unknown operations remain rejected with the defined wire error.

After repairs, affected checks and adversarial reassessment found no remaining
actionable issues in this inhibited USB endpoint slice. No independent hardware
assessment was performed.

## Remaining evidence and work

No board flashing, USB device control/capture, GPIO, debugger or RF operation
was performed. Probe tests mock all device I/O. Target heap/stack high-water,
USB behavior, timing and RF remain unqualified. The endpoint is explicitly for
the inhibited engine; capability ranges describe simulated input acceptance,
not RF coverage. CDC closure is logical and requires a client timeout/reopen.

Next: RF feasibility/engine selection and separately scoped measurement plans;
then authorized engine work, standalone encoding/configuration/time, WsprryPi
client integration, network/browser/provisioning adapters and qualified releases.
