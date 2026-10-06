# Phase 12 time and indicator cases

Status: historical time specimens remain **PREPARED / NOT EXECUTED**. The current
LED execution checkpoint and authorized L4 packet below supersede this earlier
preparation boundary for LED work only. For historical time specimens use the clean
`engineering` inhibited candidate in the exact manifest, Candidate B only,
and separately approved engineering credentials/controllers. No RF, flash,
reset or system-clock alteration is authorized here. These cases use the
existing Field-GATT/1 exchange and WTP/1 simulator, not firmware fault commands.

## Current LED checkpoint — 2026-10-06

A at `6c7b143` passes the current two-flash setup cue and Identify priority/
nonextension: one accepted request, one competing busy response and one exact
accepted duplicate, with unchanged boot, profile and job state. The operator's
240 fps recording confirms five three-flash cycles, 150–158 ms pulses and
roughly two-second periods, followed by the two-flash setup cue. Only the
success summary is retained in the repository; no video or derived frames.

The operator now has GP14 buttons on both Picos and selects direct visual
observations for future LED checks. Further videos are not required. LED off after
setup withdrawal is also operator-confirmed for five seconds. The
[success record](phase12-led-physical-result.json) retains only these results.
The checked-output failure test retains its own scope. Exact GP14 edge timing
during erase/program remains a separate measurement or evidence-backed disposition.

## Reviewed repair and current exit

Repair `db7911f` propagates the checked driver's return code. Independent
adversarial review found and closed the fixture's missing successful-return
proof; source reassessment is clear. The affected Linux `field_access_tests`
passes **1/1**. Clean inhibited fixture and normal images plus the normal RF
image cross-link; stack/storage/UF2 checks pass, and normal/RF symbol checks
prove the fixture wrapper and INFO fields are absent. These builds do not
constitute a live L4 pass.

**L4 has not been executed.** A remains on the accepted `6c7b143` portal image
with generation 5; B's last readback remains inhibited `c0d2bd53e4bd`,
provisioned generation 2, healthy/empty/disabled/inactive. No B flash or fixture
boot occurred in this LED repair tranche. The one-case driver and its failure
cleanup are private preparation; finish their independent reassessment before
hardware use. At the operator's commit-and-report checkpoint, only L1–L3 are
physically accepted. No new host network fixture or board-lock holder remains.

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

The earlier proposed video/photodetector requirement was used for the accepted
2026-10-06 recording. Its pulse/period tolerances were 20/40 ms, with 4.17 ms
capture resolution and a conservative two-frame measurement allowance. The
operator has now selected live visual observation for subsequent Phase 12 LED
checks; further recordings are not required. Use the current waveform and
report only the physical behavior actually observed.

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

## L4 checked-output error packet — 2026-10-06

The normal Pico adapter now returns the CYW43 driver's result instead of the
SDK's void convenience wrapper. `IndicatorController` latches a failed write,
retries its unknown output, and retains the fault after a successful retry;
there is no distinct blinking fault pattern. The affected portable regression
passes on wspr5. Target cross-link and image/storage checks precede use.

The isolated, default-off `WSPRRY_PICO_PHASE12_INDICATOR_FAULT_FIXTURE` wraps
only the checked LED driver call in the inhibited target and returns one error.
Later writes use the real driver. Fixture-only INFO counters report calls,
injection, successful real-driver writes and the controller latch; normal and RF images omit the wrapper and
these fields. No runtime fault endpoint or memory corruption is introduced.

The operator's existing A/B operation grant and step-1 continuation cover one
B fixture boot followed by one repaired normal engineering boot. B is Pico 2 W /
RP2350, serial `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`. Preflight is inhibited `c0d2bd53e4bd`,
provisioned generation 2, healthy/empty/disabled/inactive. A stays on its accepted
portal image. Bind the clean source, both images and retained SDK/toolchain
hashes before use; keep GP14 disabled, profile fault stage zero and other fault
fixtures off.

Acquire B's exclusion/action locks; verify fresh INFO and a recoverable private
backup with onboard indicator routing. Load and verify only application pages;
reserved journals and E10 must remain exact. Within 120 seconds of fixture
boot collect two original INFO responses: injection count one, latched output
fault, at least two driver calls, at least one successful real-driver write
and recovered Off output, same boot, healthy
empty/inactive authority and unchanged configuration/profile. No jobs or saves.
A stopped or uncertain destructive action is never replayed.

Finish with the repaired normal engineering image and verify exact image pages,
reserved/E10 preservation, healthy disabled/empty/inactive state and fixture
absence. Retain that working image and release B's locks. This accepts adapter
error propagation and retry integration, not a physical failed LED or a blinking
fault waveform. The pinned lower-level CYW43 GPIO routine does not report every
IOCTL failure; acceptance covers its exposed return-code path, not complete
physical LED failure detection. No further operator video is required.

## L4 accepted result and GP14 disposition — 2026-10-06

One B fixture boot passed two same-boot INFO observations over 2.253 seconds:
one injected error, two checked calls, one subsequent successful real-driver
return, latched controller fault and recovered desired Off. The named repaired
normal exit passed 7,109 application-page comparisons, unchanged profile
generation 2, exact reserved/E10 preservation and fixture-field absence; that
image was retained at the L4 case exit. Later selected cases transitioned B to consumer/RF firmware. Independent review checked the original binaries and
protocol receipts. See the [result binding](phase12-led-physical-result.json).
The first private preflight stopped before any backup/load because a helper
expected a boolean where production emits numeric fault zero. Its corrected
strict type/value guard passes recorded-schema and cleanup controls in normal
and optimized Python; the original STOP remains retained.

The operator explicitly accepted excluding exact GP14 coincidence within the
measured 8.524–8.648 ms erase/program interval. That claim remains unmeasured;
the accepted two-second flash-safe pause remains narrower evidence. B12L is
CLOSED_SCOPED for the retained visual results, checked-driver integration and
this disposition. No complete physical LED-failure detection is claimed.
