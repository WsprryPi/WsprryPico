# Field access and browser time

## Access policy

Consumer field mode is an explicit journal-backed selection in AccessStore. It survives restart and keeps the AP requested without inactivity expiry. It does not enable BLE, take RF ownership, enable schedules, or clear STOP. Disabling it returns access to ordinary fallback/manual windows.

The protected AP and browser authentication share the effective credential resolver: a separately saved Pico password wins; otherwise the selected saved Wi-Fi password applies. The hash-verified CYW43 overlay maps WPA2 AES selection to WPA2 authentication alone; explicitly mixed authentication remains separate. No valid credential means no protected AP. Blank commissioning and deliberate physical/USB recovery can open commissioning without that credential. An ordinary infrastructure outage does not open an unprotected configured AP.

A credential or field-mode save has a bounded five-second reply opportunity before disruptive safe-idle AP activation. Authentication retirement remains immediate; ciphertext replies own their buffers after session retirement. A lost reply requires authoritative readback, not automatic save replay. AP credential hashes are transient comparison material; passwords are not exposed in status.

Automatic fallback requests access after 60 seconds without station association plus IPv4. Existing station retries continue at approximately 30-second intervals, with a one-second leave for latched failed/stalled joins. DHCP-only address loss does not force reassociation. An initial unjoined AP window lasts ten minutes, except two-minute Console grace. An associated Wi-Fi client retains temporary access, followed by ten minutes after the final disconnect. During a continuing outage, expired fallback reopens after five minutes closed. Stable infrastructure recovery takes 30 seconds, does not evict an associated client, and rearms later outage recovery. Internet loss alone does not trigger fallback.

An already-running consumer AP retains browser status and operation-specific control admission during RF. Starting, stopping, rekeying, and changing open/protected AP mode require known inactive output with no armed/running/failed job. Such transitions never abort accepted jobs. Commissioning still requires its stricter unowned, idle authority.

## Control/1 routes

The optional exact `field_access` capabilities descriptor advertises policy and paths. The resources are consumer-session operations; their advertisement does not grant USB or engineering callers consumer-session authority. Shared control major and namespace remain 1; Radio/1, WTP/1, transport, and journal versions remain independent.

Every response carries `contract: Wsprry-Control/1` and a member target with the current device and boot IDs. Mutation bodies carry that contract and exact target. Document shapes are closed.

| Method and resource under `/api/control/v1/` | Request payload | Result |
| --- | --- | --- |
| GET `consumer/field` | None | `field-access`: `enabled`, `storage_healthy`, ETag |
| PUT `consumer/field` | `field-access`: boolean `enabled`; exact If-Match | Durable field selection/readback |
| GET `consumer/time` | None; authenticated AP only | `browser-time`: source, clock state, age, uncertainty, disagreement |
| POST `consumer/time/challenge` | `browser-time-challenge`: 32-lowercase-hex `nonce` | Reserve bounded source/session challenge |
| POST `consumer/time/submit` | `browser-time-sample`: `sample` containing the same nonce and decimal-string `utc_ns` | Consume challenge and return time status, or refusal |

The encrypted session establishes device, boot, profile generation, interface, authority, request sequence, and session binding. The time mutation independently checks its member target. Challenge age is measured at the Pico from request receipt, conservatively including the complete challenge exchange. Browser submissions must arrive within 200 ms. The challenge is consumed before failed binding, freshness, uncertainty, or source admission can be retried. There is one bounded pending challenge, also shared with existing controller-time authority; unused challenges expire after ten seconds and close with their logical session.

Automatic status reads use public resources even in an authenticated page. Public identity polling discards local authentication when the device or boot changes. Profile changes retain their existing authenticated policy/retirement rules; it never grants or renews authority. Time reads and observations do not renew the 30-minute login inactivity timer. The eight-hour absolute session limit remains. Ordinary operator actions retain existing renewal semantics. A closed session cannot submit new samples; its accepted clock may remain in finite holdover under the original source principal. Another session waits until that source expires or participates in explicit disagreement recovery.

## UTC authority and holdover

The authenticated AP page supplies browser time automatically after login and approximately every 30 seconds while active. It checks source status before sending observations and refreshes before job preparation when due. No clock confirmation dialog is required. Public commissioning hints do not establish transmit-ready UTC.

Browser UTC is the operating-system clock read by JavaScript, not an independent UTC measurement. Its initial uncertainty includes a 250 ms device-clock assumption, target-measured exchange age, and a local serialization/timer margin. Range, freshness, and uncertainty checks remain mandatory. A valid but wrong first offline clock cannot be detected without independent evidence; it can affect future schedule reservations. Watermarks are never rolled back to compensate.

Browser holdover lasts at most 3,600 seconds and uncertainty grows conservatively at 50,000 ppb, or 180 ms/hour. An explicitly trusted Si5351 loopback can correct the timer rate while preserving the original phone epoch and source age. Its declared uncertainty must be lower than the ordinary timer allowance. The ordinary 50,000 ppb drift allowance and the trusted-reference uncertainty continue to grow the reported bound; neither learned browser rate nor RF manual PPM reduces it. Capture loss retains the learned rate center under this conservative growth. Removing trusted use returns to the uncorrected timer slope without a time step. UTC uncertainty is informational and does not shorten the one-hour browser source lifetime. These policy bounds do not qualify actual device-clock accuracy or multi-day holdover. Existing controller time retains its independent 90-second lifetime.

Usable network time and supported controller time retain higher priority. An existing valid non-browser clock cannot be overwritten by a browser sample. Browser observations are pinned to an authenticated session principal; another browser cannot replace a still-valid source. Same-source nonoverlap latches disagreement. Changing to a higher-priority source also checks overlap while the prior source remains valid. Disagreement invalidates new starts and requires two consistent independent observations from the eligible recovery source; a replay is not recovery evidence. A reboot returns to unsynchronized UTC.

NTP age/uncertainty configuration remains independent. Its explicit zero option does not extend browser time. GPS/PPS ingestion and automatic RF calibration are absent. GPSDO measurements used externally are test references, not a new firmware time source.

## Launch and UI behavior

Preparation and launch retain source age, leap, ownership, frequency, hardware, and output checks. First-party producers request the advertised WTP ceiling; explicit external per-job uncertainty limits retain their independent protocol meaning. Invalid time blocks new starts; an armed job failing its launch gate is missed, and a running job continues on its selected monotonic schedule. Refresh does not arm jobs, resume STOP, replay missed occurrences, or transfer ownership.

The UI says **Using browser time**, with **Time supplied by this device’s clock.** It reports clock state, sample age, estimated uncertainty, and failed refresh or disagreement. Browser sleep/background throttling and connection loss are normal reasons for holdover. The page does not equate an open tab with fresh accepted observations.

## Validation boundaries

`field_access_tests` exercises persistent AP intent, fallback reopening, association retention, authenticated source arbitration, freshness, disagreement, and expiry. `field_time_sessions` exercises real HTTP/parser/AEAD handlers, journal revisions, strict request validation, replay, competing sessions, and non-renewing time refresh. NTP-timeout tests retain the independent controller/browser boundaries and explicit zero behavior. The required production Pi/Pico network and USB pairs remain the integration gate.

Simulated monotonic aging verifies software boundaries; it does not measure physical oscillator drift. Cross-linking establishes build integrity, not target timing or RF. Concurrent AP/RF use and claimed elapsed holdover duration require separately identified board, image, clock, mode, source, and conducted receiver/reference evidence.
