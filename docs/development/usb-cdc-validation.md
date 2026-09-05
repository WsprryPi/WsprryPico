# Dual USB CDC validation record

Date: 2026-09-05. Scope: completion of the existing RF-inhibited USB foundation
on `devel`, starting at `9e7737e`. This record accompanies the implementation
commit. Builds tested the working source before committing; their revision
metadata therefore describes the pre-commit dirty tree, not a release image.

## Changed files and purpose

| File | Purpose |
| --- | --- |
| `src/usb/roles.h` | Central CDC instance and control/data interface mapping. |
| `src/usb/transport.hpp` | Explicit console/WTP APIs, bounds and ownership contracts. |
| `src/usb/transport.cpp` | Bounded console queue, independent WTP byte I/O and session reset handling. |
| `firmware/main.cpp` | Use adapter APIs, bounded WTP RX, reset parser/banner, service fatal diagnostics. |
| `firmware/usb_descriptors.c` | Use shared mapping and check CDC configuration consistency. |
| `firmware/CMakeLists.txt` | Compile adapter into the existing inhibited firmware target with warnings enabled. |
| `CMakeLists.txt` | Add transport tests and optional actual-TinyUSB descriptor tests. |
| `tests/usb_transport_tests.cpp` | Exercise isolation, saturation, short writes, ring wrap and connection resets. |
| `tests/usb_mock/tusb.h` | Narrow mock boundary for the real adapter's TinyUSB calls. |
| `tests/usb_descriptor_tests.c` | Inspect actual expanded descriptors and serial callback behavior. |
| `tests/descriptor_mock/pico/unique_id.h` | Supply deterministic board-ID source for descriptor testing. |
| `docs/development/usb-cdc.md` | API/identity contracts, limitations and opt-in Linux/macOS procedure. |
| `docs/development/README.md` | Link the USB development and test instructions. |
| `docs/development/firmware-foundation.md` | Link detailed USB semantics and validation. |
| `docs/architecture.md` | Record adapter boundary and no-logging-on-WTP invariant. |
| `docs/development/usb-cdc-validation.md` | Record this validation and review evidence. |

The pre-existing `.vscode/settings.json` spelling-list edit is unrelated and
excluded from this change. No SDK, other repository, protocol contract or RF
engine source was modified.

## Commands and results

Executed from `/Users/lbussy/GitHub/WsprryPico`:

```sh
cmake --preset host-debug
cmake --build --preset host-debug
ctest --preset host-debug
cmake --preset host-debug -DWSPRRY_PICO_TEST_TINYUSB_PATH=/Users/lbussy/GitHub/pico-sdk/lib/tinyusb
cmake --build --preset host-debug
ctest --preset host-debug
python3 scripts/validate_wtp_contract.py
cmake --preset pico2-w
cmake --build --preset pico2-w
clang-format --dry-run --Werror src/usb/roles.h src/usb/transport.hpp src/usb/transport.cpp tests/usb_mock/tusb.h tests/descriptor_mock/pico/unique_id.h tests/usb_transport_tests.cpp tests/usb_descriptor_tests.c firmware/main.cpp firmware/usb_descriptors.c
git diff --check
```

Final host suite: 4/4 passed (USB transport, actual descriptor expansion, portable
core, WTP monitor). Contract validation passed: 23 schema cases, 7 raw JSON
cases, 1 framing case and 8 transition cases. Firmware configured and built with
the existing pinned Pico SDK/Arm toolchain and RF inhibition. Formatting and
whitespace checks passed; changed Markdown local links were checked for existence.

The firmware configuration emitted its existing picotool warning: no separately
installed matching picotool, so the pinned build-directory source is used. This
was not a build failure and no tool was installed system-wide.

## Adversarial review and repairs

Reviewed code, TinyUSB source semantics, descriptor expansion, tests and docs.
Repairs followed by affected checks and reassessment:

- Preserve short-write suffixes so startup diagnostics are not truncated by the
  64-byte USB FIFO. Test startup-sized UTF-8 text and a wrapped full ring.
- Reset parser/banner even when DTR closes and reopens between polls, and reset
  on USB reconfiguration. Test reset notification persistence and software FIFO
  cleanup.
- Service the console queue inside the fatal-error loop; validate firmware build.
- Correct descriptor test/documentation assumptions: this TinyUSB version names
  control interfaces, not association descriptors. The actual expansion test
  now verifies that supported representation.
- Correct test-driver assumptions about final short writes and stalled-console
  delivery; rerun the complete suite successfully.

Final reassessment found no remaining actionable issues within this transport
slice. This was a source/mocked review, not independent hardware qualification.

## Limits and follow-up

No board was flashed or controlled. No hardware enumeration, USB capture, timing,
GPIO or RF checks were performed. The manual procedure remains opt-in.

Clearing TinyUSB software FIFOs cannot retract packets already in endpoints or
host buffers. Reconnect aborts the stream; future protocol/session handling must
account for this. No hard real-time bound is claimed for TinyUSB or parser work.
The separate WTP writer is tested but this firmware deliberately emits no WTP
responses: strict JSON decoding, response/event encoding, serialized frame sender,
typed dispatch and complete endpoint/session behavior remain follow-up work.
