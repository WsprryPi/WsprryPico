# Development baseline

The defined hardware target is Pico 2 W / RP2350. This repository currently contains
architecture and repository support files, with no firmware or test targets.

## Build direction

Use C/C++ with the Raspberry Pi Pico SDK and CMake. The first implementation
slice will pin SDK, compiler and language-standard versions, select the board
explicitly, and add documented build/test commands. No dependency download,
flashing command or build workflow is supplied by this scaffold.

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

## Current checks

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
There is no build/test command that validates firmware yet.

Hardware-free job-service behavior is the next planned slice. See the
[implementation plan](../implementation-plan.md) and [WTP/1 contract](../protocol/WTP.md).
