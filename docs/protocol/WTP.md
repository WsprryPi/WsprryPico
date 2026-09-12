# WTP/1 — WsprryPi Transmitter Protocol

Status: normative protocol contract. No implementation or compliance claim is
made by this document.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**
and **MAY** describe conformance requirements.

## 1. Scope and invariants

WTP is a device-neutral protocol for loading, arming, observing and cancelling
finite transmitter jobs. WsprryPico is the reference server and WsprryPi is the
reference client. Product and firmware versions are independent of WTP/1.

A client MUST load the complete job before arming it. After a successful `ARM`,
the server's local monotonic clock and execution engine determine every event
boundary. Transport traffic, latency and loss MUST NOT set or alter RF timing.
Every accepted job is finite and bounded by advertised capabilities.

WTP/1 does not define station configuration, stored schedules, provisioning,
firmware update, browser APIs, regulatory policy, RF filtering or a particular
RF engine. Device GPIO and register details MUST NOT appear in WTP messages.

## 2. Version and compatibility

The protocol identifier is the exact string `WTP/1`. The first valid request on
each connection MUST be `HELLO`. Its `versions` array lists supported protocol
identifiers in preference order. A WTP/1 server selects `WTP/1` or returns
`UNSUPPORTED_VERSION` and closes the connection after sending the response.
Before negotiation, the envelope `protocol` field identifies the version used
to encode that `HELLO` request.

Envelopes, operation bodies, jobs, RF events, clock snapshots and errors are
closed objects: unknown members are an `INVALID_MESSAGE`. New members or event
types therefore require a new protocol version.

## 3. Frame format

Every message uses a 16-byte header followed by one UTF-8 JSON payload:

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | magic | ASCII `WTPF` (`57 54 50 46`) |
| 4 | 1 | framing version | `1` |
| 5 | 1 | encoding | `1` for JSON |
| 6 | 2 | flags | zero, unsigned big-endian |
| 8 | 4 | payload length | 1–65,536, unsigned big-endian |
| 12 | 4 | payload CRC | CRC-32C, unsigned big-endian |

CRC-32C uses the Castagnoli polynomial in reflected form (`0x82f63b78`), an
initial value of `0xffffffff`, and a final XOR of `0xffffffff`. The CRC covers
only the payload bytes.

A transport may split or combine frames arbitrarily. A receiver MUST buffer a
partial header or payload. If the header is invalid, it MUST discard bytes up
to the next `WTPF` candidate and validate the complete candidate header before
accepting it. An invalid payload length or CRC invalidates that frame; its JSON
MUST NOT be processed. A connection MUST close after either three consecutive
invalid frames or 131,072 discarded resynchronization bytes, whichever occurs
first. Receipt of a valid frame resets both counters. A partial frame that
makes no progress for 5,000 ms MUST close the connection. End of stream with a
partial frame discards it without processing.

## 4. JSON and scalar representation

Payloads MUST be UTF-8 without a byte-order mark and contain exactly one JSON
object. Duplicate object member names, floating-point numbers and non-finite
numbers are invalid. JSON integers MUST be in the inclusive range
`-2147483648` through `2147483647`. The root object has depth 1 and nesting
MUST NOT exceed 16. A receiver MUST reject excess depth before dispatch.

Identifiers are exactly 32 lowercase hexadecimal characters. Quantities that
may exceed the JSON integer range are canonical unsigned decimal strings:
`0` or a nonzero digit followed by digits, with no sign or leading zeroes.
Names ending `_ns` are integer nanoseconds. Names ending `_nhz` are integer
nanohertz. Boolean values are JSON booleans, never integers or strings.
The schema extensions `x-maximum` and `x-maxUtf8Bytes` express constraints that
standard JSON Schema cannot apply to decimal strings or encoded byte lengths;
conformance tools MUST enforce them.

## 5. Envelopes and identities

A request contains exactly:

```json
{"type":"request","protocol":"WTP/1","session_id":"<id>","request_id":"<id>","op":"STATUS","body":{}}
```

A response repeats `session_id`, `request_id` and `op`. A success contains
`"ok":true` and `body`; a failure contains `"ok":false` and `error`. It MUST
contain exactly one of those forms.

An event contains `type`, `protocol`, `session_id`, `boot_id`, `event_id`,
`event` and `body`. `event_id` is a canonical unsigned decimal string that
increases by one within a boot, beginning at `0`. Event bodies are defined by
the schema: `JOB_STATE` reports a state change, `MISSED_START` reports a missed
job, `OWNER_RELEASED` reports loss or release of ownership, `DEVICE_FAULT`
reports a failed state, `INVALID_FRAME` reports a framing error after session
establishment, and `SESSION_REPLACED` reports connection replacement. Events
are advisory. A client that detects a gap or reconnects MUST use `STATUS` as
the authority.

The client creates a fresh `session_id` for a logical session and unique
`request_id` values within it. The server has a stable `device_id` and creates
a fresh `boot_id` on every reset. Before accepting connections after reset, it
MUST command output off and verify that the engine reports output inactive. A
boot change invalidates ownership, loaded jobs, replay entries and terminal
records. A client MUST NOT automatically reload or rearm work after observing
a different boot identity.

A server may resume a session only for the same authenticated principal. A new
connection that resumes it replaces the old connection; the old connection
receives `SESSION_REPLACED` when possible and then closes.

## 6. Operations

WTP/1 defines these operations:

| Operation | Mutation | Purpose |
|---|---|---|
| `HELLO` | no | negotiate WTP and obtain identities |
| `CAPS` | no | obtain implemented profiles, modes and limits |
| `CLAIM` | yes | obtain exclusive transmitter ownership |
| `RENEW` | yes | renew the owner's lease |
| `RELEASE` | yes | release an idle or loaded transmitter |
| `LOAD` | yes | validate and store a complete immutable job |
| `ARM` | yes | bind the loaded job to an absolute start |
| `ABORT` | yes | cancel pending or active execution safely |
| `STATUS` | no | obtain authoritative state and output status |
| `GET_CLOCK` | no | obtain clock validity and monotonic mapping |
| `PING` | no | test request/response reachability |

The exact request and success-response bodies are defined by
[`wtp-1.schema.json`](wtp-1.schema.json). `HELLO`, `CAPS`, `GET_CLOCK`,
`STATUS` and `PING` are read-only. All other operations except `CLAIM` require
the current owner. `CLAIM` requires an unowned transmitter.

## 7. Ownership and disconnects

`CLAIM` requests a lease from 5,000 through 60,000 ms. A success identifies the
owner and returns the granted lease and monotonic expiry. Ownership is bound to
the authenticated principal and resumable session, not merely to the supplied
`owner_id`. Only that session can `RENEW`, `RELEASE`, `LOAD`, `ARM` or `ABORT`.
Standalone and browser-originated jobs MUST enter the same ownership service as
host clients; they do not form a second control path.

The lease is expired when sampled monotonic time is greater than or equal to
`expires_monotonic_ns`; a `RENEW` received at that instant is too late.

When an ownership lease expires:

- in `empty`, ownership is released;
- in `loaded`, the job passes through `aborted`, records that terminal result,
  then enters `empty` and releases ownership;
- in `armed` or `running`, the lease is extended through a terminal state, so
  connection or lease loss cannot alter event timing; ownership is then
  released after the terminal result is recorded.

`RELEASE` succeeds in `empty`, `loaded`, `complete`, `aborted` or `missed`. It
clears the current job while preserving retained terminal records. It is
rejected in `armed`, `running` or `failed`. A local, trusted safety control MAY
initiate the same `ABORT` behavior without network ownership. It MUST still
produce the normal terminal record and output checks.

## 8. Job profile and limits

WTP/1 defines `rf-events/1`, an immutable sequence of RF events. A job contains
exactly `job_id`, `profile`, `mode`, `total_duration_ns`, `events`, and optional
`allow_frequency_adjustment`. `mode` is one of `wspr`, `qrss`, `fskcw`, `dfcw`,
`cw` or `tone`.

Each event contains `offset_ns`, `duration_ns`, `rf_on` and, only when `rf_on`
is true, `frequency_nhz`. Events MUST satisfy all of these rules:

1. There are 1 through 512 events, or a smaller advertised `max_events` limit.
2. The first offset is zero and every duration is positive.
3. Each later offset exactly equals the preceding offset plus duration.
4. The final offset plus duration exactly equals `total_duration_ns`.
5. Total duration is at most 86,400,000,000,000 ns (24 hours), or a smaller
   advertised `max_job_duration_ns` limit.
6. An RF-on event has positive `frequency_nhz`; an RF-off event omits it.
7. All arithmetic fits an unsigned 64-bit integer.

`LOAD` is atomic. Rejection leaves the current accepted job unchanged. Loading
the identical immutable job under the same `job_id` succeeds idempotently;
different content with that ID returns `JOB_ID_CONFLICT`. Job equality compares
parsed JSON values: object member order is insignificant and array order is
significant.

While a job or its terminal record is retained, an idempotent `LOAD` returns
the original load result without changing the current state. It does not make a
terminal job executable again. A new execution uses a new `job_id`; a
transition from a terminal state to `loaded` therefore names a different job.

The server validates requested frequencies against the selected engine. It
MUST reject unrealizable values unless the job explicitly sets
`allow_frequency_adjustment` true. Any adjustment is fixed and returned by
`LOAD`; it MUST NOT change after `ARM`.

## 9. Lifecycle and output safety

The states and permitted transitions are:

```text
empty    -> loaded
loaded   -> armed | aborted | empty
armed    -> running | aborted | missed
running  -> complete | aborted | failed
complete -> loaded | empty
aborted  -> loaded | empty
missed   -> loaded | empty
failed   -> empty
```

`LOAD` enters `loaded`. `ARM` enters `armed`. Local execution enters `running`
only at the scheduled monotonic instant, then `complete`. `ABORT` enters
`aborted` only after the engine confirms output inactive. A failure to confirm
safe output enters `failed` and returns `OUTPUT_STATE_UNKNOWN`.

At the final event boundary the server MUST command output off, even if the
last event was RF-off, and confirm it within advertised
`output_disable_timeout_ns`, which MUST be positive and no more than
5,000,000,000 ns. `ABORT` uses the same bounded confirmation. A
timeout enters `failed`, records `OUTPUT_STATE_UNKNOWN`, and continues the
implementation's local recovery procedure; it never reports successful abort
or completion.

Calling `ABORT` in `loaded`, `armed` or `running` follows the normal abort path.
Repeating it for the same job in `aborted` returns the original success. It
returns `INVALID_STATE` for `complete` or `missed`, `OUTPUT_STATE_UNKNOWN` in
`failed`, and `JOB_NOT_FOUND` when the named job is neither current nor the
current aborted result.

`STATUS` always reports `output_active` explicitly. A terminal state MUST NOT
be interpreted as proof that output is inactive. `LOAD`, `ARM` and `RELEASE`
MUST fail while `output_active` is true. Leaving `failed` requires a local
engine recovery that verifies output inactive; a remote request cannot clear it.

## 10. Clock and arming

UTC fields use POSIX Unix time in nanoseconds; leap seconds are not counted in
the epoch. Monotonic fields use an implementation-defined clock that never
steps during a boot. A clock snapshot reports:

- `state`: `unsynchronized`, `synchronized` or `holdover`;
- simultaneous `utc_now_ns` and `monotonic_now_ns` samples;
- conservative `uncertainty_ns` and `sync_age_ns`;
- `leap`: `normal`, `insert_pending`, `delete_pending` or `unknown`; and
- `leap_transition_utc_ns`, present only for a pending transition.

`ARM` supplies `job_id`, `start_utc_ns` and `max_start_uncertainty_ns`. The
server MUST reject it unless the caller owns the transmitter, the matching job
is loaded, the clock is synchronized or holdover age is no greater than
advertised `maximum_holdover_age_ns` (zero disables holdover), reported
uncertainty is no greater than both the request and advertised limit, start
lead time meets the advertised minimum, start time is no farther ahead than
advertised
`maximum_arm_ahead_ns`, arithmetic is safe, and the job interval does not
overlap the one-second exclusion window on either side of a pending leap
transition. `unknown` leap status is `LEAP_UNSAFE`.

`maximum_arm_ahead_ns` MUST be positive and no greater than
604,800,000,000,000 ns (seven days). `minimum_arm_lead_ns` MUST be no greater
than that advertised horizon.

A successful `ARM` returns the sampled clock mapping and computed
`start_monotonic_ns`. Immediately before enabling output, the server MUST
recheck clock state and uncertainty. It MUST aim for the requested instant and
MUST NOT deliberately start before it. A delayed launch is permitted only before
the end of the UTC second containing `start_utc_ns`: the exclusive deadline is
`start_utc_ns + (1,000,000,000 - start_utc_ns % 1,000,000,000)`, mapped to the
same monotonic clock at ARM. This is not a rolling one-second lateness allowance.
If the clock check fails or this deadline has been reached, it enters `missed`,
keeps output disabled and emits `MISSED_START`; it MUST NOT retry automatically.
The clock uncertainty limit remains independent of scheduling delay. Timer
quantization MUST round the requested target upward, within that same second.

The server MUST expose its target and observed launch timestamps and scheduling
delay in diagnostic telemetry; a software observation is not an electrical edge
measurement. This revision uses implementation diagnostics rather than adding
fields to WTP/1 envelopes. Pico Console INFO supplies `launch_target_ns`,
`launch_observed_ns`, `launch_delay_ns`, and `launch_epoch`; delay is the
post-enable observation minus the quantized target. No launch is represented by
zero epoch, not a measured zero delay. The unrounded requested mapping remains
in the ARM reply. The complete event sequence and its duration MUST be preserved,
anchored to the actual launch. The permitted launch window plus full job duration
MUST be safe from arithmetic overflow and pending leap exclusions. Once
`running`, UTC corrections or loss of synchronization do not alter this monotonic
event schedule.

Console INFO is not a WTP STATUS response. Its nested scheduler status does not
include WTP's job/owner identity fields. The implementation diagnostic
[field and correlation reference](../development/phase11-5-metrics.md#console-info-and-wtp-status-are-different-interfaces)
defines how to join Console launch counters with authoritative WTP job status;
this distinction does not change the WTP/1 response schema.

## 11. Retries, replay and retained results

For each resumable session, the response cache has a capacity of at least eight
entries and an expiry of at least 300 seconds. It MAY provide larger values.
An entry expires at the configured age or may be evicted earlier when the
advertised capacity is exhausted, using least-recently-used eviction.
The server retains the SHA-256 digest of each original JSON payload rather than
the payload itself. Repeating a `request_id` with the same digest returns the
cached response without executing again. Reusing it with a different digest,
including for semantically equivalent JSON with different encoding, returns
`REQUEST_ID_REUSE` and closes the connection. Resource-level idempotency for
`LOAD` and `ARM` applies even after response-cache eviction.

Repeating `ARM` with the same `job_id`, start and uncertainty returns the
original result without changing state, including while its terminal record is
retained. A different arming tuple for an already armed or running job returns
`ARM_CONFLICT`. After all records for that job expire, the server returns
`JOB_NOT_FOUND`; it MUST NOT infer that retransmission is safe.

The terminal-record store has a capacity of at least eight and an expiry of at
least 3,600 seconds. A record expires at the configured age or may be evicted
earlier when the advertised capacity is exhausted, using least-recently-used
eviction. `STATUS` returns the current record and retained records. Capability
values may exceed these WTP/1 minima but MUST NOT be smaller.

After reconnecting, a client performs `HELLO`, confirms both `device_id` and
`boot_id`, and queries `STATUS` before any mutation. It MUST treat an uncertain
mutation outcome as unknown until the authoritative status or an idempotent
retry resolves it.

## 12. Errors

An error contains exactly `code`, `message`, `retryable` and optional `detail`.
The stable codes are:

| Code | Meaning |
|---|---|
| `INVALID_FRAME` | framing, length or CRC failure |
| `INVALID_MESSAGE` | invalid UTF-8, JSON, schema or scalar |
| `UNSUPPORTED_VERSION` | no common WTP version |
| `HELLO_REQUIRED` | first valid request was not `HELLO` |
| `UNKNOWN_OPERATION` | operation is not defined by WTP/1 |
| `AUTHENTICATION_REQUIRED` | transport principal is absent or unacceptable |
| `SESSION_REPLACED` | another connection resumed the session |
| `BUSY` | another owner holds the transmitter |
| `NOT_OWNER` | caller does not hold ownership |
| `LEASE_EXPIRED` | ownership expired before the request |
| `REQUEST_ID_REUSE` | request ID was reused with different content |
| `INVALID_STATE` | operation is not permitted in the current state |
| `JOB_NOT_FOUND` | requested job is not loaded or retained |
| `JOB_ID_CONFLICT` | job ID names different immutable content |
| `JOB_LIMIT_EXCEEDED` | a frame, event, duration or device limit is exceeded |
| `UNSUPPORTED_PROFILE` | job profile is unsupported |
| `UNSUPPORTED_MODE` | requested mode is unsupported |
| `FREQUENCY_REJECTED` | frequency cannot be realized under job policy |
| `ARM_CONFLICT` | job already has a different arming tuple |
| `CLOCK_UNSYNCHRONIZED` | clock state is unacceptable |
| `CLOCK_UNCERTAIN` | uncertainty exceeds an allowed threshold |
| `LEAP_UNSAFE` | leap status or overlap is unsafe |
| `ARM_TOO_LATE` | required preparation lead time is unavailable |
| `ARM_TOO_FAR` | requested start exceeds the advertised future horizon |
| `MISSED_START` | local clock checks failed or the requested UTC second expired |
| `OUTPUT_STATE_UNKNOWN` | output could not be confirmed inactive |
| `DEVICE_FAULT` | a diagnosed device or engine fault prevents the request |
| `INTERNAL_ERROR` | bounded internal failure without a more precise code |

`retryable` describes whether repeating the same logical request might succeed
after the reported condition changes. It does not authorize blind mutation
retries. Errors MUST NOT change accepted job or state unless this specification
defines that transition. Invalid frames have no request identity; a server MAY
emit an `INVALID_FRAME` event only when a session is already established.
`detail` is diagnostic and MUST NOT change the meaning of `code` or drive client
state transitions.

For deterministic failure handling, a server evaluates a request in this
order: frame; UTF-8/JSON/scalar/envelope; transport authentication; `HELLO` and
version; session replacement and request replay; operation recognition;
operation-body schema; ownership and lease; lifecycle and job identity;
advertised limits and engine capability; clock policy; execution. It returns
the first applicable error. Local output-safety faults take precedence whenever
continuing evaluation could enable or leave output active.

## 13. Transport bindings and trust

USB uses CDC ACM and carries the frame stream unchanged. Its trust boundary is
physical access plus host operating-system device permissions.

TCP carries the identical frame stream inside TLS 1.3 or later and uses ALPN
`wtp/1`. Plaintext TCP is not conforming. Network control requires mutual
authentication with a device-specific credential; a fleet-wide shared secret
is forbidden. Provisioning and credential rotation are outside WTP/1. WTP/1
does not assign a default TCP port.

Transport adapters supply the authenticated principal to the common job
service. They MUST NOT implement separate ownership, lifecycle or timing rules.

## 14. Capabilities and conformance

`CAPS` reports profiles, modes, frequency ranges, selected engine identity,
limits, output-disable timeout and clock/arming thresholds. It reports
implemented behavior; it cannot change the fixed frame size or weaken WTP/1
minima for lease range, replay retention or terminal retention. A server MUST
reject a request it cannot execute within its reported limits.

The machine-readable contract is [`wtp-1-contract.json`](wtp-1-contract.json),
the message schema is [`wtp-1.schema.json`](wtp-1.schema.json), and normative
examples and negative cases are in
[`test-vectors/wtp-1.json`](test-vectors/wtp-1.json). Where those artifacts
conflict with this document, the conflict is a specification defect and no
conformance claim may be made until they agree.

A conforming implementation MUST pass the maintained vectors plus tests for
fragmented and combined frames, resynchronization bounds, duplicate requests,
reconnect and boot changes, ownership conflicts, clock loss, leap exclusions,
missed starts, cancellation and confirmed output shutdown. It MUST demonstrate
that no transport input is needed after `ARM` for event timing.

The repository validator is hardware-free and validates only the contract
artifacts. It does not establish firmware behavior, target timing, RF output or
WTP compliance.
