# Production USB control implementation plan

Status: implemented, independently reviewed and published within the supported
software and bounded USB/AP scope. See [execution/results](usb-control-results.md)
for exact checks, repaired physical memory finding, restoration and source
identities. No new transmitter RF or absolute timing acceptance is claimed.

The coordinated slice starts at Pico `45f3367c89db00c20f06f119c58a06cc696f5fb5`
and Pi `da0ef083644d30c800e6f7d421aecf96e764c735`, both initially clean.
It adds normal-firmware USB management and UTC synchronization, consumer USB
WTP, shared-hostname presentation, saved Wi-Fi create/replace/remove, and a
nonrenewable ten-minute AP window for every production AP entry path.

## Invariants and acceptance

WTP/1 and its Console/WTP CDC roles remain unchanged. A third CDC management
role uses a separately versioned framed JSON protocol. All adapters retain one
JobService, scheduler, configuration validator and persistence authority. USB
is local physical authority; device/boot/session binding is not cryptographic
authentication. Network authentication is unchanged.

No smaller job, event, duration, mode, schedule, session or configuration limit
is accepted. No timing, uncertainty, holdover, launch or RF reserve is relaxed.
Existing standalone and station Wi-Fi behavior remains available. The AP
lifetime change deliberately supersedes indefinite blank/fallback/held leases.

Record baseline constants and final build/resource comparisons before acceptance.
Changes are implemented first through portable services, then Pico adapters and
the real Pi runtime/UI. Deterministic production-pair interoperability, both
normal firmware builds, existing regressions, UI verification and an independent
adversarial review precede publication. Physical checks require an available,
identified, safely preservable device; no current SDR setup is presumed.

## USB-Management/1 selected wire contract

The new CDC control interface is 4 (instance 2), leaving Console 0 and WTP 2.
Each frame is ASCII `UMP1`, a four-byte big-endian payload length, then a strict
UTF-8 JSON object (maximum 32768 request bytes, 65536 response bytes). One
request/response/ack transaction is live per connection; idle buffers are
released. Bad framing, duplicate keys, oversized input, stale IDs or binding
failures close the logical connection without mutation. Absolute transaction
deadline is ten seconds. IDs are positive JSON integers up to 2147483647,
strictly increasing for new operations; ACK repeats its covered ID.

Hello request has exactly `schema`, `id`, `operation`, with schema
`usb-management/1`, operation `hello`. Response has `schema`, `id`, `status`,
`session`, `target`, `body`, `etag`, `delivery_required`. Target is the existing
member/device_id/boot_id object. Session is a new 32-lowercase-hex connection
token. Body is a JSON string containing the actual resource JSON, never an
implicit success indication. Hello body describes product/firmware and bounds.
Hello requires no ACK. Non-200 status is a failure even if outer framing passes.

Resource request has exactly `schema`, `id`, `operation`, `session`, `target`,
`method`, `path`, `body`, `if_match`; operation is `request`. Body is a UTF-8
JSON string (empty for no body). The adapter constructs the existing typed
request and dispatches only supported API paths with the local USB principal.
Response has the same shape as hello; status/body/etag come from the shared
application. Every resource response requires ACK. ACK has exactly `schema`,
`id`, `operation`, `session`, `target`, operation `ack`. ACK only succeeds after
the complete covered response has left the adapter; only then can matching
deferred effects apply. Its response has delivery_required false. Disconnect
or timeout cancels that transaction's undelivered effects, never durable writes.
No new operation may overtake the ACK. Ambiguous mutations require readback.

USB time sample is GET `/api/usb/v1/time/sample`, returning a one-use `sample`
token and decimal-string `monotonic_ns`. Submit is POST
`/api/usb/v1/time/submit`, body exactly `sample`, `utc_ns`, `uncertainty_ns`,
`leap` (`normal` only under existing source policy). The host associates the
sample with the midpoint of a qualified wall-clock exchange, charges host
error plus the full observed roundtrip conservatively, and rejects clock steps.
Pico binds/consumes the sample, rejects age over two seconds, and observes it
through the existing controller/SNTP arbiter under principal `usb-physical`.
No admission limit changes. Time refresh is bounded and independent of symbol
delivery; healthy SNTP is neither overwritten nor invalidated by USB loss.

## Work order

1. Capture baseline limits and extend local profile/application authority.
2. Implement protocol/transport, time exchange, bounded AP lifecycle.
3. Integrate Pi runtime, common-name UI, Wi-Fi lifecycle and actual-pair tests.
4. Validate normal firmware, capacity/timing preservation and compatibility.
5. Repair independent review findings, document exact remaining physical gates,
   commit and push each repository as explicitly requested by the user.
