# Development baseline

The defined hardware target is Pico 2 W / RP2350. The repository contains a
portable WTP/1 core, deterministic host tests and an RF-inhibited firmware
target.

## Build direction

The portable core uses C++20 and CMake 3.24 or later. The firmware build pins
the Pico SDK, picotool and Arm toolchain and selects `pico2_w` explicitly. The
SDK fetches the pinned picotool build dependency. The
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
The [output/inhibit design](rf-output-design.md) remains a hardware proposal.

## Current checks

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
