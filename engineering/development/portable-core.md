# Portable execution core

The portable RF execution service lives in `src/rf/`. Shared JSON, storage buffers, response sources, memory budgeting, and hashing live in `src/runtime/`. The portable code has no Pico SDK or operating-system dependency.

## Boundaries

`JobService` accepts typed requests and owns replay handling, sessions, ownership, immutable jobs, arming, terminal retention, reset, and safe cancellation.

Native schedulers and authenticated Test Tone compile work inside the Pico and enter the same typed request boundary. USB and HTTP management validate their own control documents and have separate [management authority](management-carriers.md).

`Clock`, `IdentitySource`, and `RfEngine` are injected interfaces. A target clock must provide a simultaneous UTC/monotonic snapshot. An identity source must return a valid, fresh 128-bit boot identifier across resets and device boots. An RF engine receives the complete immutable job before execution. Its local execution loop owns event timing after `begin`; no transport callback supplies events.

The service commands and verifies output off during construction and reset. It rejects requests if that check fails. Engine start, runtime, completion, and abort failures use the same bounded output-disable path; uncertain output enters `failed` and cannot be cleared remotely.

## Host build and tests

Configure and run the deterministic suite from the repository root:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

The CMake project requires CMake 3.24 or later, disables compiler language extensions, and pins the portable code to C++20. The tests use a virtual clock and mock RF engine. They do not establish firmware behavior, target timing, electrical output, or RF performance.

## Current limitations

The [native execution contract](../protocol/Native-Execution.md) defines the application boundaries. Cached core responses retain their original STATUS and clock snapshots, including the ARM mapping.

The mock engine demonstrates that an armed job executes without further requests. It does not prove that a target alarm, interrupt, or RF engine meets the scheduled nanosecond values. Target adapters require separate tests and authorization before hardware or RF activity.
