# Response generation

HTTP and USB management share owned response snapshots and bounded byte sources.
Their wire formats, schemas, resource limits, authentication and delivery rules
are unchanged. Firmware uses no HTTP worker threads or RTOS.

## Typed documents and ownership

`HttpResponse` supports small strings, paged JSON, borrowed flash assets and an
owned `ResponseSource`. Capability and application documents count frozen
fragments before allocating their final pages. The writer includes the current
control contract once, with the same field order and bytes as the string writer.
Application subdocuments are released before computing the final revision.

LOAD replies with up to 32 adjustments retain the original materialized path,
avoiding fixed generator overhead for short and empty adjustment lists. Larger
replies use bounded generation. A generated LOAD reply captures its quoted identifiers and shares the immutable
`AdjustmentList`; it does not retain a request, parser, application callback or
live configuration reference. A fixed 513-entry offset index bounds lookup for
at most 512 adjustments. Integer formatting uses checked `to_chars` operations
into a fixed local array. The source publishes exactly the existing JSON.

`ResponseSource::copy` on plaintext is replayable and allocation-free. Only the
outer source owns a 1,024-byte output window; composition releases intermediate
windows. Object and window allocation uses the existing nullable input allocator
before publication. Repeated access to the current offset returns the same
window suffix. Generation occurs in the serialized foreground owner, with no
application redispatch or mutation while rendering.

The immutable adjustment backing store can outlive the producer while a reply
is pending. Its storage is bounded by the existing job limits, independently of
the rendering window. Sharing that storage is not the same as eliminating it.

Materialized JSON still passes the existing JSON validator. Only the closed,
typed LOAD serializer declares a generated JSON document; arbitrary sources do
not. Contract composition requires that declaration. Request shape, field,
version, identity, revision and authority validation remains unchanged.

## HTTP and encryption

Port-80 and engineering HTTPS transports consume the response through
`body_size` and `body_at`. One connection's output step remains at most 1,024
bytes. Port-80 service still alternates two slots and uses an absolute ten-second
connection lifetime. Flash assets retain their borrowed-storage path.

Generated consumer replies use a response-owned ChaCha20-Poly1305 context. The
existing header, associated data, nonce, sequence and final tag are unchanged.
The cipher advances once per plaintext byte; retries retain the existing
ciphertext window. Cipher output is explicitly non-replayable. The host `wire` and `body_text`
helpers return an empty result if a source stops before its advertised length,
including a replay that needs discarded ciphertext. They never return
a partial document or spin on zero progress. Its initialized
context remains independent of session key cleanup and is securely destroyed
with the response. Plaintext scratch and released output windows are wiped.

Small materialized replies retain their existing sealing paths. Paged capability
and application replies are encrypted in place; string replies use the existing
parts interface. This avoids paying generator overhead for an already complete
small document.

Transport loss, incomplete ciphertext or an undelivered tag does not establish
delivery. Existing transaction completion, login retirement, password change,
interface withdrawal and TCP acknowledgement semantics remain authoritative.

## USB framing and preparation

USB management retains `UMP1`, the eight-byte frame header, the JSON string that
contains the resource body, the 65,536-byte payload ceiling and explicit delivery
ACK. Its existing independent authority reserve is unchanged.

For generated documents, the endpoint owns the complete source graph before
publishing bytes. Each `poll` counts at most 1,024 raw bytes with the same escaping
function used for emission. A fixed checkpoint table supports replay without a
second serialized body. No header is exposed until the escaped payload length is
known and admitted. Preparation is busy state and remains inside the existing
ten-second transaction deadline. Timeout or failure cancels the pending effect
without publishing an incomplete frame header.

Output then uses the reusable outer window, including boundaries inside escaped
characters. Draining the final byte does not complete a mutation; only the bound
USB ACK does. Disconnect, timeout and optional-buffer reclamation retain their
existing cancellation behavior.

Already materialized resources keep the existing final-frame buffer. Wrapping a
complete string in a generator would retain the string plus rendering overhead.
These paths share the escaping function but do not claim constant-memory output.

## Verification and measurements

`response_sources` checks byte equivalence, escaping, frozen snapshots, retry
views and failure of each nullable constructor allocation. HTTP server tests
cover generated output under backpressure alongside another connection. USB
management tests cover incremental preparation, no allocation during counting
or emission, exact escaping, partial drains, explicit ACK and preparation timeout.
Crypto tests compare the streaming packet with existing vectors and maximum-size
buffered sealing, including one-byte reads after session retirement.

The [measurement report](response-generation-results.md) records before/after
allocation, host processing and linked-image costs. `scripts/measure_responses.py`
compiles identical probe sources against baseline and candidate libraries and
retains every sample. Host measurements and cross-link checks do not establish
physical Pico heap high-water, service latency, USB timing or RF performance.
