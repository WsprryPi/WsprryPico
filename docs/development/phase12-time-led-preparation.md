# Phase 12 time and indicator cases

Status: **PREPARED SPECIMENS / NOT AUTHORIZED / NOT EXECUTED**. Use the clean
`engineering` inhibited candidate in the exact manifest, Candidate B only,
and separately approved engineering credentials/controllers. No RF, flash,
reset or system-clock alteration is authorized here. These cases use the
existing Field-GATT/1 exchange and WTP/1 simulator, not firmware fault commands.

## Verified surfaces and constants

The source contracts are [Field-GATT controller time](../protocol/Field-GATT.md#controller-time-time_challenge-and-time_submit),
[Identify/status](../protocol/Field-GATT.md#identify),
[WTP clock admission](../protocol/WTP.md#10-clock-and-arming),
[arbiter](../../src/time/controller_time.cpp),
[clock profile](../../src/standalone/wtp_profile.hpp), and
[indicator](../../src/provisioning/field_runtime.cpp).

Existing authenticated BlueZ client entry points are in
[`scripts/wsprrypico_ble.py`](../../scripts/wsprrypico_ble.py):
`Client._field`, `Client.field_status`, `Client.synchronize_time(milliseconds)`,
`Client.identify`, and `Client.wtp_exchange`. CLI `status`, `identify`,
`sync-time` and `wtp-status` already exist. There is **no** CLI offset/fault
flag. Directed specimens below require an already authorized, same-connection
case driver using the existing API or equivalent protocol-valid Bluefy frames;
record that driver's exact source/hash and its request/reply transcript in the
approval packet. Repeated CLI invocations reconnect and cannot substitute for
same-principal/session tests. Do not invent a nonexistent command or reuse a
historical session/nonce.

Controller lifetime is 90 seconds; a challenge expires at 10 seconds and also
must meet the stricter 500 ms uncertainty bound. The submission is charged
250 ms plus target-observed reply-delivery latency and 1,050,999 ns local
margin. Clock discipline is synchronized through 90 seconds and holdover
through 180 seconds; WTP admission permits maximum holdover age **90 seconds**.
These are distinct limits. Use actual HELLO limits and simultaneous STATUS
clock fields, not a host timer alone, to interpret boundaries.

Record every request/reply and INFO/STATUS/field-status before/after, including
source, age, uncertainty, disagreement, UTC/monotonic mapping, job/owner/state,
boot identity and inactive output. No candidate source/boot change within a
case. Between cases restore an accepted real SNTP observation and healthy,
empty/unowned state; separately approved fixture isolation may suppress SNTP
only during controller cases. Never contact a router or change management
connectivity. Failed prerequisites mean stop, not a fabricated pass.

## Protocol specimens

For each exchange generate fresh 32-lowercase-hex `request_id` and `nonce`.
Use current authorized field session and exact B ID
`29f20b7342051ef947aa56cb9d4fab42`. Never copy these placeholder token values:

```json
{"version":1,"operation":"time_challenge","request_id":"FRESH_REQUEST_HEX","session_id":"CURRENT_FIELD_SESSION","device_id":"29f20b7342051ef947aa56cb9d4fab42","nonce":"FRESH_NONCE_HEX"}
```

After the **complete** matching challenge reply, sample current host UTC,
without changing host clock. Immediately submit:

```json
{"version":1,"operation":"time_submit","request_id":"ANOTHER_FRESH_REQUEST_HEX","session_id":"CURRENT_FIELD_SESSION","device_id":"29f20b7342051ef947aa56cb9d4fab42","nonce":"SAME_FRESH_NONCE_HEX","utc_ns":"CANONICAL_DECIMAL_HOST_UTC_NS_PLUS_CASE_OFFSET"}
```

The specimen driver computes `utc_ns = time.time_ns() + offset_ns` only after
the reply. `offset_ns` is a test message value, never a system clock change.
A successful `accepted=true` is required for the initial baseline. If the
round trip exceeds uncertainty limits, record failure and stop without retry.
For an expected rejection retain the raw error code; a timeout is not an
expected disagreement or busy response. Challenge and submit are two complete
Field-GATT messages with canonical framing and complete-message ordering.

| Case | Exact bounded stimuli | Required observations |
| --- | --- | --- |
| T1 disagreement | No valid SNTP/browser source; same authenticated principal sends offset0 accepted baseline, then a new challenge/submit with **+5,000,000,000 ns** offset within 10 s. Two exchanges only, <=5 min. | Second wire response `conflict` (controller disagreement maps to this Field-GATT code); field source disagreement, usable UTC invalid, output inactive. Record actual uncertainty intervals proving nonoverlap rather than relying only on nominal5s offset. Different principal is a separate busy case, not disagreement. |
| T2 two-sample recovery | From T1 latch, same principal sends two fresh offset0 exchanges separated by **1 s**, each sampling host UTC after its reply. Two exchanges, <=5 min. | First is not accepted and disagreement remains; second accepted only if its projected interval overlaps the first. No intervening source/principal change or SNTP observation. Source controller, disagreementfalse. Neither response may create a job or owner. |
| T3 age | One offset0 accepted observation, then no time refresh from any source. Read status at target-reported age approximately **89 s,91 s,181 s** (bound each host observation bracket). One exchange plus three observations, <=5 min. | At89s report actual admissibility/uncertainty; do not assume uncertain clock can arm. Beyond90s controller source is no longer valid and new ARM is refused under unchanged90s admission age. Beyond180s discipline is unsynchronized. Read-only status does not refresh source age. Use WTP clock `sync_age_ns` after90s; field-status age can return0 when its source interval is invalid. If freshSNTP appears the aging case is invalid, not passed. |
| T4 SNTP priority | With actual valid SNTP baseline, same principal sends one fresh **+5 s** controller exchange. <=5 min. | `busy`/source-busy rejection; source remainsSNTP and disagreementfalse. No comparison-driven latch or mutation of SNTP clock by this request. |
| T5 job-state distinction | Three predetermined simulator jobs, one loaded-only, one armed with futurestart, one running; each <=60s, three jobs total. Inject the T1 same-principal nonoverlap once in each state using a newly accepted controller baseline and noSNTP. <=5min per state. | Loaded job retains its identity/owner and ARM refuses unusable time. Armed job never launches under invalid time: at its original deadline expect missed-start/terminal result and no enginebegin/output. Already-running complete local job follows its admitted monotonic lifecycle; verify actual terminal result rather than claiming UTC changes abort it. End each case empty/unowned. |

T5 uses this complete LOAD body, with fresh lowercase-hex job ID replacing
`FRESH_JOB_HEX`. Mode is lowercase; nanohertz fields are decimal strings.
Verify3570100Hz is within actual HELLO frequency ranges before approval:

```json
{"job_id":"FRESH_JOB_HEX","profile":"rf-events/1","mode":"tone","total_duration_ns":"5000000000","events":[{"offset_ns":"0","duration_ns":"5000000000","rf_on":true,"frequency_nhz":"3570100000000000"}]}
```

The event's `rf_on=true` drives only the explicitly inhibited simulator, never
physical output. Record exact canonical payload and digest. CLAIM uses fresh
`owner_id` and `lease_ms=60000`, subject to actual advertised limits. ABORT, supported RELEASE with empty body (subject to actual state rules),
and natural lease expiry are separately bound cleanup operations. Use current HELLO→CLAIM→LOAD→ARM fields from
[`wtp-1.schema.json`](../protocol/wtp-1.schema.json) and current STATUS mapping.
For armed/running cases compute start from simultaneous target UTC/monotonic
snapshot with **5-second lead**, subject to actual advertised minimum lead and
horizon; request `max_start_uncertainty_ns="500000000"` only if advertised
limits admit it. For loaded-only case attempt ARM once after disagreement.
No RF LOAD/ARM is allowed: confirm inhibited engine and disabled/inactive
output before every job. A predetermined approved case driver must retain
request/session/job IDs, poll times and exact result; no invented wire fields.
The twelve-job composition budget and these separate three jobs must be
explicitly accounted separately in the final approval, never silently combined.

## Browser hint has no operator/job authority

On a separately approved healthy inhibited consumer/AP case, the existing
`GET http://192.168.4.1/api/bootstrap/v1/time` supplies `challenge_ns`.
Within200ms send one same-origin JSON POST with fields exactly
`version=1`, current `device_id`, decimal `utc_ms` sampled after GET and echoed
decimal `challenge_ns`; retain Origin/Host and response `accepted` or `ignored`.
The [parser](../../src/network/bootstrap_wire.cpp) defines admitted request
headers/fields. Do not spoof arbitrary browser authentication headers.

A browser hint may seed an initially unusable clock; this is **not** an
operator principal, CLAIM, LOAD, ARM or permission for RF. Compare job/owner,
network readiness and inactive output before/after. With accepted SNTP, the
hint must not displace it. An ignored hint or clock-readiness change alone is
not job admission evidence. A separate approved WTP admission request remains
subject to ownership and all clock bounds. No RF authority is inferred here.
Limit to one GET/POST pair per unsynchronized and synchronized state, <=5min
per state. These requests belong to consumer time preparation, not engineering
TLS field transport or an ordinary quiet-soak interval.

## Independent indicator timing

Use one independently timed video/photodetector record at **>=100 samples/s**,
with a recorded uncertainty budget of at most20ms for each edge. The target
pattern constants are desired timings, not already qualified physical timing.
Propose acceptance: each150ms pulse within20ms and two-second repetition within
40ms, separately report actual error and capture resolution. Changing these
proposed tolerances needs explicit review before measurement.

| Case | Finite stimulus and expected desired waveform |
| --- | --- |
| L1 AP ready | Healthy local APready state, no Identify; observe **10s**. Two150ms flashes per2000ms: on offsets0–150 and300–450ms of device phase. No job/owner change; do not synchronize phase to host wall clock. |
| L2 Identify priority/nonextension | One authenticated Identify while APready; fresh request at t≈1s expectsbusy, exact duplicate originalrequest at t≈2s expects success without extension. Observe15s. Identify has150ms pulses at0–150,300–450,600–750ms every2000ms relative to its start, lasts10000ms, then returns APcue. Two new requests plus one duplicate, no reconnect or secondacceptedIdentify. |
| L3 AP withdrawal/off | One approved stable-station withdrawal observation with no Identify; at desiredOff observe5s with no pulses. Coupled R11A fixture action must be approved; this does not independently authorize networkloss. |

Identify request has only common Field-GATT fields and `operation="identify"`;
use the authorized field session/currentBID. `field_status` reports `indicator`
and `indicator_fault`. INFO/status before/after prove no jobs or leases changed.
Each case <=5min; ordinary Identify CLI can demonstrate L1/L2 onset but a
same-session protocol driver is required for exact duplicate/nonextension.

**Fault cue remains a separate preparation gate.** `IndicatorController`
exposes an output-fault latch, not a distinct blinking fault pattern; the
current Pico adapter calls CYW43 LED write and returns success. None of the ten
reset/profile interruption stages injects a checked LED-write failure. Do not
label a journal fault, intentional watchdog reboot or APready blinking as LED
output-fault acceptance. A separately reviewed inhibited adapter-error fixture,
exact affected cue/status contract, healthy/fault comparison, hashes and finite
approval are required before L4 can be executed. No runtime fault endpoint or
memory corruption is proposed here. This honest gap remains B12L open.
