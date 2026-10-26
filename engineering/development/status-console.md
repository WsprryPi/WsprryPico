# Contextual transmitter status

The shared Transmitter status section presents the current accepted job separately from future standalone work. It uses native controls, system fonts and the embedded page's flat section design. Station/Transmission and Wi-Fi/Host share the same observation and Reset Pico operation.

## Observations and disclosure

Capabilities negotiate `operations_status:{schema:"transmitter-operations/1",path:"/api/v1/operations"}`. The authenticated GET returns one bounded operations projection. Legacy `/api/v1/status` and `/api/v1/jobs` keep their existing shapes; clients without the capability use basic status and label contextual details unavailable. The unauthenticated consumer endpoint remains the closed `transmitter-public-status/1` projection. It discloses no accepted message, nominal frequencies, saved schedule, correction or owner identifier.

The operations resource has exactly `schema`, `target`, `job`, `accepted`, `standalone`, `message_schedule`, `next_wspr_start_utc_ns`, `correction`, `reset_allowed`, `network` and `transport`. `target` is the existing member device/boot envelope. `job` uses the existing status shape with an empty `terminal_records` array; history is available through the legacy status resource. `standalone` uses the existing scheduler status shape, with its duplicated job fields taken from the same captured ServiceStatus. `message_schedule` is the existing schedule body without the separate resource envelope. `correction` is the existing calibration selection or null. `network` on Pico contains only `enabled`, `link_status`, `ipv4`, `configured_hostname`, `mdns_state` and `mdns_reason`; bulk NTP and transport diagnostics stay in their existing resources. `transport` is null. The resource's ETag is the existing opaque management revision.

`accepted` is null without a retained job. Otherwise it contains `mode`, decimal-string `duration_ns`, nullable decimal-string `start_utc_ns`, integer `event_count`, at most four distinct decimal-string `frequencies_nhz`, boolean `frequencies_truncated` and nullable `message`. Message compiler provenance contains `text` (at most 32 characters), decimal-string `frequency_nhz`, `space_frequency_nhz`, `dot_ns`, `dash_ns`, `repeat_gap_ns` and integer `repeat_count`. For DFCW, the supplied primary frequency is Dot and the secondary is Dash, in either orientation; both durations are the accepted element duration. This internal provenance is excluded from the WTP wire format and job digest. Raw RF-event LOAD never supplies it. Frequency summaries are captured once during successful LOAD and survive release of execution event pages. No event walk, execution cursor or new RF-core request is added to status polling.

Engineering station HTTPS, authenticated Consumer-Radio station/AP and physical USB management admit this resource. Engineering field HTTPS omits its capability and refuses the route, retaining its existing basic status and configuration admission rules before clock qualification. No management schema or public shape is extended implicitly. Consumer encrypted requests retain their existing origin, interface, generation, session and delivery bindings.

The page uses one serialized five-second polling loop, at most one application action in flight, existing transport deadlines, request epochs and exact device/boot validation. New-boot engineering observations rebind only after authenticated same-device hostname readback, invalidate old job estimates and require saved-state review; a consumer rebind requires a new login. Failed or malformed reads clear live console values. After 15 seconds without a confirmed observation, the page marks state/output unavailable and disables controls. Session loss clears privileged rendered readbacks while preserving form drafts. Polling never copies observed data into edited forms, writes journals, claims ownership or submits jobs.

Browser-local time includes its locale and timezone. Pico UTC is explicitly the time at observation, and is unavailable when the device clock is unsynchronized. Observation time is labelled separately. The browser clock is never substituted for synchronized device UTC. Only headline transitions use the console live announcement; clock ticks are ordinary text.

## State interpretation

Output/storage faults take headline precedence. Accepted loaded, armed or running work follows, independently of incomplete standalone configuration or future-schedule blockers. Running RF-off observations remain active jobs, including keyed gaps. Future context distinguishes recovery barriers, pending durable pause, reset requirements, suspension, paused/expired schedules, clock admission, incomplete WSPR configuration, reserved ownership and an eligible future occurrence. A disabled saved message schedule does not mask enabled WSPR.

The displayed WSPR candidate is derived without mutation from current UTC, configured schedules, consumed-start watermark, clock admission, complete plan duration and expiry. It is an eligibility prediction, not an accepted job or promised launch. Busy or blocked states report no eligible candidate. Standalone USB dial and nominal RF center are separate: 14095600 Hz maps to center 14097100 Hz, with four tones spaced by 1.46484375 Hz. The console never adds that offset to an externally accepted absolute-frequency job.

QRSS labels Carrier, FSKCW labels Space and Mark, and DFCW labels Dot and Dash using accepted compiler values. Saved recurring message context is explicitly labelled separately from accepted work. Message copies and their gap belong to one finite job; recurrence interval, first UTC anchor, optional expiry and next eligible occurrence describe separate jobs. Generic externally loaded jobs report nominal RF events and unavailable original text. WSPR frame counters appear only for the matching scheduler job.

Elapsed duration and percentages use the device UTC at observation and the accepted start/duration. They are estimates, including at 100 percent, and never replace a running state with completion. Character progression remains an unimplemented enhancement; an authoritative event cursor is unavailable. Selected manual correction applies at the next preparation; accepted-job correction comes only from the engine's frozen preparation selection. Missing values remain unavailable. μChrony disciplines UTC and supplies no RF calibration measurement.

## Reset Pico

Both buttons invoke one shared operation with a product confirmation. Reset is a normal restart retaining saved settings; enabled schedules may resume after readiness checks, while consumed occurrences remain skipped. It does not erase credentials or perform a factory reset, and introduces no new reboot policy.

The request remains `POST /api/v1/restart` with the closed empty body `{}`, current If-Match and `features.restart` negotiation. Authentication, target/boot readback, revision consumption, response acknowledgement, transaction token and deferred restart remain the existing authority. Eligibility is checked on receipt and again at delivery: no loaded/armed/running/faulted job, owner, active/unknown output, maintenance, unhealthy storage, hardware-application failure, pending message pause or recurring recovery barrier is permitted. A newly acquired owner or active job cancels the deferred effect. RF-off keyed gaps cannot make reset eligible.

The browser revalidates the same fresh observation after confirmation and after hostname/configuration readback. Expiry cancels before submission with explicit guidance. It submits once, including an ambiguous response, and monitors for at most 90 seconds. Page reachability or a public boot change cannot confirm success. Confirmation requires authenticated readback of the same device and a new boot, with the intended saved hostname applied. Cancellation, logout, timeout, stale revisions and lost replies never trigger an automatic retry. An unconfirmed reset stays unconfirmed until that readback.

## Reference behavior and validation

The information hierarchy follows WsprryPi devel `5bc24e893646140d44f0bf9a20d61115d0eadda9`, inspected through `WsprryPi-UI/data/views/operation.php`, `operation.js`, shared `site.js` runtime snapshots and `src/scheduling.cpp`. The implementation is original MIT code within Pico's architecture; no Pi implementation, PHP, Bootstrap or Linux lifecycle code is copied.

| Pi behavior | Pico presentation |
| --- | --- |
| Prominent runtime state and explanation | Accepted job, actual output observation and separate future blockers |
| Mode/frequency panels | Accepted compiler semantics or nominal RF-event values; standalone dial/center labelled separately |
| WSPR plan and message progress | Matching frame counters and estimated accepted-job duration; no invented character cursor |
| Transmit/stop controls | Existing save/apply, recurring pause, owner-scoped Abort and Release |
| Local/UTC clocks | Browser-local time, Pico UTC at observation and observation timestamp |
| Candidate/committed correction | Manual selection versus frozen preparation; no NTP RF estimate |
| Reboot policy and shutdown | Existing restart semantics and guarded Reset Pico; Pi policy choices/shutdown unavailable |

Deterministic coverage is in `operations_browser_tests.js`, source/shipped `network_browser_tests.js`, `network_tests.cpp`, consumer session/crypto tests and the existing reset/hostname browser fixture. The production adapter, memory/stack/flash and image-integrity checks remain enabled. Browser fixtures are software evidence; they do not qualify physical RF timing, decoding or emissions.
