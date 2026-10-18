# USB-Management/1

This versioned local USB adapter is separate from WTP/1. Normal RF-capable, explicit inhibited and compatibility
StandaloneRF images expose Console CDC instance/control interface 0/0, WTP 1/2
and management 2/4. Console/WTP endpoint numbers and framing are unchanged.
Management uses notification/OUT/IN endpoints `85/06/86`. The existing
`cafe:4012` remains a development identity, not an allocated production VID/PID.

Access to the selected physical device is local administrative authority.
Linux permissions/exclusive opening and physical-parent/serial/role checks are
host responsibilities. Every transaction binds the exact immutable device,
boot and connection session. Those identifiers are not cryptographic proof.
No network request can select this internal principal. USB access alone grants
no transmitter ownership; an explicit job CLAIM must pass the same JobService
used by WTP, browsers and standalone.

## Framing and negotiation

Every frame consists of ASCII `UMP1`, a four-byte unsigned big-endian JSON
payload length, and that many UTF-8 bytes. JSON payload requests are at most
32768 bytes; responses at most 65536, excluding the eight-byte frame prefix.
Zero/oversized length, bad magic/JSON, duplicate keys,
unknown members, wrong binding or stale IDs close the logical connection.
Reconnect requires a new physical transport session; no mutation is retried.

All envelopes have `schema:"usb-management/1"`. IDs are positive JSON integers
through 2147483647. New request IDs strictly increase; ACK repeats its covered
request ID. Exactly one resource request/response/ACK transaction is live.
The absolute ten-second transaction deadline cannot be renewed by trickling
input, partial output or ACK traffic. Idle paged buffers are returned and
credential-bearing input pages are wiped on release. Resource memory refusal
preserves the existing authoritative control reserve. WTP can close this
optional management session and reclaim its pages before retrying its original
input/workspace admission checks. This cancels undelivered deferred effects,
retains durable saves and accepted UTC, and requires a new management session
plus authoritative readback before another configuration write. WTP capacity
and timing checks are not reduced to keep management connected.

The first request has exactly `schema,id,operation`, operation `hello`. It does
not require UTC, Wi-Fi, an AP, a saved network or certificate. The hello response
has the standard response shape below and `delivery_required:false`; its body
contains `schema:"usb-management-discovery/1"`, `product`, `firmware`,
`max_request_bytes` and `max_response_bytes`. A new session is 32 lowercase hex
characters generated for that connection. Unknown protocol versions refuse.

Every response has exactly:

| Field | Meaning |
| --- | --- |
| `schema` | `usb-management/1`. |
| `id` | Covered request ID. |
| `status` | Actual application status; outer framing alone is not success. |
| `session` | Current connection token. |
| `target` | Existing `{scope:"member",device_id,boot_id}` object. |
| `body` | String containing the actual resource JSON; empty only when allowed. |
| `etag` | Exact application revision, or empty when inapplicable. |
| `delivery_required` | Whether the host must ACK before another operation. |

## Shared resources and delivery

A resource request has exactly `schema,id,operation,session,target,method,path,
body,if_match`, with operation `request`. Body is a JSON string or an empty
string for no body. Method, path and If-Match strings are bounded to 8, 128 and
256 bytes respectively. Resource bodies retain their smaller independent
limits; the outer JSON string encoding must also fit the envelope maximum.
The adapter dispatches typed requests to the shared
application handlers under the internal `usb-physical` principal. Mutations
retain target/revision checks, idle/safety admission, validators and journals.
See [local configuration](../development/usb-local-configuration.md) for
hostname, Wi-Fi, profile versions and migration. Ordinary `/api/v1/` resources
retain their independently versioned schemas and semantics.
USB-selected application/capability views identify `usb_physical`, remove USB
JSON from the unavailable list and select `transmitter-management/3` discovery.
The shared base-operation inventory is not an exhaustive list of USB-specific
resources; the explicit resources and their independent contracts below apply.
Network projections and their previous carrier schema versions are unchanged.

Every resource response requires ACK, including errors. ACK has exactly
`schema,id,operation,session,target`, operation `ack`. The adapter accepts ACK
only for the current response after all its output was submitted. An ACK's
response has status 200, body `{"acknowledged":true}` and
`delivery_required:false`. Only the matching transaction's deferred restart or
network effects are completed. Disconnect/deadline cancels undelivered effects;
an already durable journal write is never rolled back. Ambiguous mutations
require authoritative readback and explicit review before another write.

USB transaction tokens occupy a namespace disjoint from the HTTP task tokens.
AP withdrawal closes only AP HTTP clients and their matching delivery tokens;
it does not close station clients or USB transactions.

POST `/api/usb/v1/ap` uses `{schema:"transmitter-ap-request/1",target}` and the
current If-Match. It requests a new bounded manual AP window after ACK, subject
to existing idle/output/radio availability checks. It never renews an active
window or a continuously held button. All actual AP activations have the same
non-sliding ten-minute maximum; repeated unchanged conditions do not reopen an
expired AP. New deliberate requests or a new outage after stable station
recovery can rearm it. USB stays usable with AP off.

## UTC exchange

GET `/api/usb/v1/time/sample` returns `sample` (one-use string token) and
`monotonic_ns` (decimal string). POST `/api/usb/v1/time/submit` body has exactly
`sample,utc_ns,uncertainty_ns,leap`; the nanoseconds are decimal strings and
`leap` must be `normal` under the existing production source policy. Each
submission consumes the sample, including a refused submission. Sample age
must not exceed two seconds; future/regressed/stale samples refuse.

The host requires a synchronized, normal-leap system clock. It brackets the
device capture between the host timestamps immediately before the sample
request and after its response, before the delivery ACK. UTC at the captured
device monotonic instant is the midpoint of that interval. A conservative
error bound includes host error, the rounded-up half-width of the measured
sample interval, realtime/monotonic discrepancy and processing/drift margin.
This interval bound covers fully asymmetric delays; it assumes no symmetric
path. The later delivery ACK remains mandatory, but does not move the capture
instant. Firmware still ages uncertainty from its actual capture time.
The host rejects clock steps/unqualified observations and never clamps error
to make admission pass. Accepted observations enter the existing
controller/SNTP arbiter under `usb-physical`; uncertainty remains at most
500000000 ns. Existing clock aging, disagreement, ARM and launch checks remain.

Successful submit reports actual `accepted`, `selected`, `source`,
`uncertainty_ns` and `age_ns`. Healthy SNTP retains priority, so status 200 with
`accepted:false,selected:false,source:"sntp"` reports available but unselected
USB input. Invalid observations still refuse before source arbitration.
Disconnect clears the pending USB sample without invalidating unrelated SNTP.
UTC refresh does not control RF symbols or calibrate an RF oscillator.

The [USB uncertainty investigation](../development/usb-time-uncertainty.md)
separates measured transfer uncertainty, host clock quality and job admission
policy. An accepted USB time update does not establish readiness for a job's
configured uncertainty limit. WsprryPi's ordinary default for new/missing
settings is 100000000 ns (100 ms), with explicit saved limits preserved; this
is controller policy, not a new protocol requirement. Pico retains its 500 ms
maximum and enforces each job's requested bound at ARM and local launch.


## Compatibility and evidence

Old firmware without management interface 4 is explicitly unsupported for the
new workflow; no Console probing or network fallback occurs. Existing WTP/1
clients retain their byte stream. New profile versions require supporting
firmware for rollback. Network authentication/discovery shapes remain unchanged
on existing carriers; USB advertises its separately versioned management view.

Portable endpoint/local-management/time tests, production Pi/Pico wire fixtures
and normal firmware builds qualify software behavior only. Physical USB enumeration, AP behavior, target UTC accuracy and RF remain
independent qualification boundaries.

Current shared resources include the independently negotiated
[GPIO-drive extension](../development/gpio-drive.md), Type 1/2/3 admission,
hostname and saved progress. Their descriptors and exact method/path inventory
are in the [browser API](../browser-api.md#resources). Config remains version 1;
the URL namespace does not set every resource schema version. An accepted
progress save creates only a draft, not a complete or applied configuration.

Source: [UMP1 endpoint](../../src/usb/management_endpoint.cpp),
[local dispatch](../../src/network/local_usb_api.hpp),
[USB owner integration](../../src/standalone/pico/main.cpp), and existing
[endpoint](../../tests/usb_management_tests.cpp) and
[local authority tests](../../tests/usb_local_management_tests.cpp).
