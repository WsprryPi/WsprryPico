# Strict WTP USB endpoint

The Pico 2 W image implements WTP/1 request decoding, job-service dispatch,
response/event encoding and ordered USB frame transmission. It remains an
**RF-inhibited, unsynchronized development endpoint**. Host tests and a firmware
build do not qualify USB on a board, target timing, or RF.

## Architecture and trust

`src/wtp/json.*` validates bounded UTF-8 JSON and exposes non-owning value views.
`codec.*` maps closed WTP envelopes/bodies to typed requests and serializes
responses. `endpoint.*` owns the connection and frame queues. All are portable
C++20. `firmware/main.cpp` supplies the existing USB adapter, device identity and
clock. Console remains independent; generic USB stdio is disabled.

USB supplies principal `usb-physical`: access to this CDC function is the trust
boundary, enforced by physical access and host device permissions. Firmware
cannot identify individual host users or processes. Session/owner IDs are not
credentials. A client with the same physical access can resume the same session;
a different adapter principal is rejected by JobService. No TLS, network
principal, new authentication protocol or host production integration is added.

Every connection starts unnegotiated and requires HELLO. Subsequent requests
must use that connection's session. A session switch receives SESSION_REPLACED
when possible and closes the old logical connection. USB provides only one active
WTP connection; reconnect replaces the previous stream. The job service, leases,
loaded jobs, replay cache and terminal results survive a transport disconnect.
A boot change clears the connection and event sequence; the service resets its
own state and verifies output inhibition separately.

All eleven operations are connected: HELLO, CAPS, CLAIM, RENEW, RELEASE, LOAD,
ARM, ABORT, STATUS, GET_CLOCK and PING. The adapter supplies the SHA-256 of the
original payload, including its whitespace/escaping. Typed JobService responses
now retain STATUS and clock snapshots and the ARM start mapping, so replay and
idempotent ARM responses do not accidentally serialize current state. Retained
terminal jobs keep a compact typed-value digest and their LOAD/ARM results, so
retrying an older retained job does not reload or rearm it after a newer job.
Access to those retained results refreshes terminal LRU order without extending TTL.

## Validation and errors

Before dispatch, reject invalid UTF-8, BOM, duplicate decoded member names,
unpaired surrogates, non-JSON/floating/non-finite numbers, integers outside signed
32-bit range, trailing content, non-object roots and container depth above 16.
Body validation enforces closed members, exact types, canonical u64 decimal
strings, identifiers, array limits and UTF-8 byte limits. Job arithmetic,
ownership, engine and clock policy remain in JobService.

The adapter records body-schema validity on Request; JobService applies it after
negotiation/replay/operation recognition and before ownership/mutation. Thus an
unknown operation returns UNKNOWN_OPERATION, while a conflicting replay returns
REQUEST_ID_REUSE even when its new body is invalid. Unsupported protocol
negotiation produces UNSUPPORTED_VERSION and logical closure.

When valid framing carries invalid JSON or an envelope without safely echoable
WTP identity, close without inventing IDs or sending an invalid error envelope.
A recognized request with an invalid body receives INVALID_MESSAGE. Framing
errors may produce INVALID_FRAME events after negotiation; the existing parser
owns its three-error/resynchronization/partial-timeout limits.

## USB closure and backpressure

CDC has no independent socket EOF. Closure here means stop accepting WTP input,
send any queued final response, and stay closed until DTR close/open or USB
reconfiguration. Console remains connected. A client must use bounded response
timeouts and reopen WTP to recover; it must not interpret terminal silence as
mutation success. Neither the device nor this adapter disconnects the composite
USB device. Queued endpoint/host packets cannot be recalled, so clients must
discard the old byte stream on reopen and query STATUS after HELLO.

The main loop stages at most 64 RX bytes and retains unconsumed bytes. Endpoint
receive consumes at most 64 bytes per call and stops when output is queued.
Frames never interleave; output offsets advance only by the transport's actual
accepted byte count. Requests wait behind pending responses instead of allowing
an unbounded response backlog. JobService polling continues under backpressure
and when disconnected. No USB callback delivers symbol timing.

At most eight output frames and 131,072 queued bytes are retained. A response is
queued before events for that operation. Advisory events may be dropped at the
bound, consuming an event ID so clients can detect gaps. Five seconds without
TX acceptance aborts the logical connection; a client must resolve an uncertain
mutation by STATUS/replay after reconnect. Acceptance into TinyUSB is not proof
of host receipt. No delivery guarantee is made across connection loss.

JOB_STATE, MISSED_START, OWNER_RELEASED, DEVICE_FAULT, INVALID_FRAME and
SESSION_REPLACED are serialized with monotonic per-boot IDs. Observation includes
intermediate terminal records, such as lease expiry passing loaded -> aborted ->
empty. Events are advisory; STATUS remains authoritative.

## Capabilities and resource bounds

CAPS identifies `inhibited-no-rf`. Its frequency range describes the unsigned
numeric inputs accepted by that simulation engine, **not physical RF coverage**.
All six mode labels are accepted for finite event jobs; no encoder or RF engine
is thereby implemented. The firmware clock is unsynchronized, so ARM is rejected.
Do not reuse this endpoint's capability serializer for a new RF engine without
providing that engine's actual limits.

Payloads remain limited to 65,536 bytes and valid jobs to 512 events. JSON stores
views, not a DOM; duplicate-key validation retains key views for active objects,
and schema extraction bounds arrays before constructing jobs. Heap allocation
remains in the portable parser, strings, jobs and replay cache; target heap
high-water and failure behavior still need opt-in hardware characterization.
The firmware reserves a 16 KiB primary stack in main RP2350 SRAM through the
pinned SDK linker symbols, excluding that region from the heap. Long-lived
service objects use static storage. Compiler `.su` files are generated for
inspection. These measures are not target stack/timing qualification.

## Deterministic validation

```sh
cmake --preset host-debug
cmake --build --preset host-debug
ctest --preset host-debug
python3 scripts/validate_wtp_contract.py
cmake --preset pico2-w
cmake --build --preset pico2-w
python3 scripts/check_endpoint_image.py build/pico2-w/firmware/WsprryPico.elf
```

The endpoint test runs the real C++ implementation against an independent Python
schema validator and the existing monitor decoder. It covers all operations,
request fixtures, raw negative vectors, lifecycle, snapshots/replay, reconnect,
boot changes, Unicode/JSON rejection, fragmented/combined frames, partial TX,
pressure, maximum payloads/events and deterministic syntax mutation cases.
Existing core, USB adapter, descriptor and monitor tests remain in place.

For address/undefined-behavior checks on a supporting host compiler:

```sh
cmake -S . -B build/endpoint-sanitize -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'
cmake --build build/endpoint-sanitize --parallel
ctest --test-dir build/endpoint-sanitize --output-on-failure
```

## Opt-in board smoke test

Only with explicit authorization for this USB test, identify the WTP port by
serial/interface using the [USB guide](usb-cdc.md), leave Console open in screen,
and run:

```sh
python3 scripts/wtp_probe.py /dev/IDENTIFIED_WTP_PORT --run
```

The probe asserts DTR and performs only HELLO, CAPS, GET_CLOCK, STATUS and PING,
with five-second timeouts and schema/identity checks. It neither LOADs nor ARMs a
job. Do not run a second monitor on the same WTP port. Record board, firmware
SHA-256/revision, host OS, physical setup, inhibited engine, unsynchronized clock,
no transmitting mode, and actual results. Flashing and RF operations are outside
this procedure. This implementation turn performed no USB device operations.

Next work is RF feasibility/engine selection and separately authorized hardware
validation, then standalone encoding/configuration/time, WsprryPi integration,
network/browser/provisioning adapters and qualified releases.
