# WTP — WsprryPi Transmitter Protocol

Status: pre-implementation design draft. Prospective protocol identity: WTP/1.
This is not a frozen wire specification and no compliance claim is made.

## Established requirements

WTP is device-neutral, independently versioned, and initially maintained in WsprryPico. WsprryPico is its reference implementation. USB CDC is the reference transport, with TCP carrying the same logical job operations. The device executes complete jobs locally; no per-symbol transport dependency is allowed.

## Proposed operation model

| Operation | Proposed meaning |
|---|---|
| HELLO | Negotiate protocol version; report product, firmware and boot identity separately |
| CAPS | Report implemented modes, engines, supported frequency ranges, job limits and timing constraints |
| LOAD | Validate and store a complete immutable job; return a device job identity |
| ARM | Reserve the engine and schedule a stored job for a device-controlled start |
| ABORT | Cancel a pending or running job and report completion only after output is stopped |
| STATUS | Report state, owner, job identity, terminal result and output state |
| GET_CLOCK | Report UTC validity, uncertainty, age and monotonic mapping |

These names describe semantics, not committed byte sequences. Earlier LOAD_WSPR and START examples were illustrative. A separate immediate-start operation needs its own timing semantics before inclusion.

Proposed lifecycle: IDLE -> LOADED -> ARMED -> RUNNING -> terminal result. Rejected requests leave the accepted job unchanged. Reset starts with output disabled and invalidates prior boot/session identities.

ARM must reject missing/incomplete jobs, conflicting ownership, unsupported plans, insufficient preparation lead time, or inadequate time confidence. At execution time the device must enforce the documented time-validity policy; ARM acknowledgement alone is not proof of execution.

Frequency requests must distinguish base frequency, modulation offsets and actual engine realization. Encode precision explicitly with bounded integer or rational units; do not rely on rounded display values. Device-specific GPIO numbers or register values must not become universal WTP requirements.

## Reliability and ownership proposals

Use correlated request identities and boot/session identity. Define bounded duplicate-response retention and payload matching before permitting retries of mutations; a repeated request must never create a second transmission accidentally. Job identities must not be reused ambiguously across resets.

One transmitter owner at a time must arbitrate standalone schedules, browsers, USB and TCP clients through the same job service. Specify claim, release, local cancellation and conflict behavior before implementing concurrent control.

Transport loss must not change symbol cadence. Whether a fully accepted job completes or is locally aborted after loss is an explicit unresolved policy. Reconnection must query authoritative state; it must not blindly reload and arm.

## Required before WTP/1 can be frozen

1. Byte framing, encoding, maximum frame/job sizes, partial-read handling, resynchronization, integrity checks and timeouts.
2. Exact request, response, error and asynchronous-event schemas.
3. Version negotiation and unknown-field/operation behavior.
4. Mode profiles, exact units, payload limits and complete test vectors.
5. UTC timescale, leap-second behavior, start offsets, lead times, clock-loss and missed-deadline policies.
6. Ownership, authenticated network control, provisioning trust and disconnect behavior.
7. Duplicate handling across reconnects, bounded retention, boot changes and terminal-result retention.
8. Transport-independent conformance fixtures run against the reference server.

The first implementation should exercise these rules with a virtual clock and a non-RF engine before hardware execution is added.
