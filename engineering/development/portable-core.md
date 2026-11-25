# Portable WTP/1 core

The host-tested core under `src/wtp/` implements transport-independent WTP/1 framing and transmitter job behavior. It has no Pico SDK, operating-system, network, storage, or hardware dependency.

## Boundaries

`FrameParser` accepts arbitrary byte chunks and produces complete payloads, invalid-frame notifications, or a closed state. It bounds input buffering, validates the 16-byte WTP header and CRC-32C, resynchronizes after noise, and enforces invalid-frame, discard, and partial-frame limits.

`JobService` accepts typed requests and owns replay handling, sessions, ownership, immutable jobs, arming, terminal retention, reset, and safe cancellation. The retained WTP format fixtures exercise frame and document validation independently.

Native schedulers and authenticated Test Tone compile work inside the Pico and enter the same typed request boundary. USB and HTTP management validate their own control documents and have separate [management authority](management-carriers.md).

`Clock`, `IdentitySource`, and `RfEngine` are injected interfaces. A target clock must provide a simultaneous UTC/monotonic snapshot. An identity source must return a valid, fresh 128-bit boot identifier across resets and device boots. An RF engine receives the complete immutable job before execution. Its local execution loop owns event timing after `begin`; no transport callback supplies events.

The service commands and verifies output off during construction and reset. It rejects requests if that check fails. Engine start, runtime, completion, and abort failures use the same bounded output-disable path; uncertain output enters `failed` and cannot be cleared remotely.

## Host build and tests

Configure and run the deterministic suite from the repository root:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py
```

The CMake project requires CMake 3.24 or later, disables compiler language extensions, and pins the portable code to C++20. The tests use a virtual clock and mock RF engine. They do not establish firmware behavior, target timing, electrical output, or RF performance.

## Current limitations

The [native execution service](wtp-endpoint.md) uses the portable core without exposing a WTP endpoint. Cached core responses retain their original STATUS and clock snapshots, including the ARM mapping.

The mock engine demonstrates that an armed job executes without further requests. It does not prove that a target alarm, interrupt, or RF engine meets the scheduled nanosecond values. Target adapters require separate tests and authorization before hardware or RF activity.
