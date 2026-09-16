# Phase 11.5 Package 3 review and execution

**COMPLETE — all eight Package 3 rows are accepted. Phase 11.5 remains OPEN.**

The [execution prompt](phase11-5-package3-prompt.md) bounded this package to
network TLS/HTTP pressure, three distinct WTP progress timeouts and the affected
current-image browser resource check. The [result](phase11-5-package3-result.json)
records exact identities, packet hashes, measurements, retained failures,
adversarial mutations and restoration state.

## Source review and evidence design

Pico A remained on source `ca3c5dce4036`, image
`6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59`
and boot `5e0d6bc3e383b8c1cb4b0db9ed636bf5`. Pico B remained the
unchanged comparator on `8921a7008183`, boot
`6684b4b197d80cfa0ce83b3aaf205cb0`.

The reusable pressure runner now has an exact Package 3 profile instead of
silently inheriting an older packet policy. It binds the current source, image,
boot, event-record ceiling, observer policy and final Empty/inactive/unowned
state. Runtime ceilings were extended only enough to contain the already frozen
two-job TLS and transport profiles.

The native observer previously exposed decoded summaries without a durable
wire decoder. `phase11_5_tls_observer_decoder.py` now validates the independent
TLS log format, record ordering, connection identity and decoded WTP frames.
The pressure auditor binds that decoder's SHA-256 as part of Package 3 evidence.

The new progress runner exercises each timeout mechanism separately through
authenticated TLS 1.3 with ALPN `wtp/1`. Its auditor binds source thresholds,
peer identity, raw HTTP and WTP bytes, target close rows, recovery messages,
the exact maximum LOAD, ABORT/RELEASE and final authority. It does not infer a
timeout from a disconnect alone.

## TLS and slot pressure — 2.2c and 2.2e

Packet `06c4f970…` ran two 100-second Tone jobs. Ten of ten cases passed:
positive controls, missing-certificate failure and recovery, a 10.219-second
silent activated-handshake timeout and recovery, two active slots with bounded
excess and reuse, and duplicate network-WTP refusal and reuse.

The independent native observer remained continuous, authenticated HTTP
observations bracketed both jobs, and the raw capture contained 2,244 TCP
packets with zero kernel drops. Both jobs completed, allocator peak was 164,296
bytes, and allocator/TLS-allocation failure counters did not increase.

## HTTP and failed-alert pressure — 2.2d and 2.2f

Packet `a7214e63…` ran two 150-second Tone jobs. Fourteen of fourteen cases
passed. Target-side close measurements were 15.247 seconds for a partial
header, 15.442 seconds for a partial body, 10.991 seconds for pending expiry,
2.995 seconds for acknowledged fatal-alert closure and 2.604 seconds for the
deliberately unacknowledged alert. Each failure path had a fresh authenticated
recovery.

The second job also held an authenticated `/app.js` response unread, then
proved bounded slot reclamation and reuse. The payload-free packet filter used
for the unacknowledged-alert case was removed before recovery. Raw capture had
2,569 TCP packets with zero kernel drops. Native and authenticated HTTP
observation remained continuous; both jobs completed without allocation or
authority failure.

## Distinct WTP progress timeouts — 2.3a, 2.3b and 2.3c

Packet `ac63c441…` used no RF and did not change firmware, configuration or
Wi-Fi state.

- A fully drained HELLO connection closed after 29.806788671 seconds with WTP
  reason 3 and exactly one network timeout-counter increment. Authenticated
  recovery took 3.466551786 seconds.
- An actual eight-byte partial STATUS frame closed after 5.044382719 seconds
  with WTP reason 4 and no network timeout-counter increment. Recovery took
  4.097329994 seconds.
- One complete 52,105-byte, 512-event LOAD was sent after HELLO and CLAIM with
  a constrained receive window and zero application reads. Output stopped
  progressing, the endpoint closed after 7.968642991 seconds with reason 4,
  and authenticated recovery in 4.391125269 seconds proved the job was Loaded
  exactly once. ABORT and RELEASE returned it to Empty/inactive/unowned.

Fresh named inventories bound unchanged RF counters and configuration on both
boards. Allocation failure counters did not change.

## Browser applicability — R3.BROWSER-MAX

The accepted actual-browser source `f5502cff9fa6` and current source
`ca3c5dce4036` contain the same `app.js` Git blob,
`6dd5d54a75da675f968447f785e49c44649c8ce0`. The existing actual-browser
30,000/30,001-byte, 31/32/33-character, message, progress and cancellation
evidence therefore remains applicable. The current-image stalled `/app.js`
case supplies the affected page-response allocation and reclamation check.

## Failed attempts retained

No failed packet receives acceptance credit.

- The first TLS root omitted a staged dependency and stopped before RF.
- TLS2 completed one 100-second job, then exhausted its finite packet envelope
  before job two.
- TLS3 physically completed two 100-second jobs, but an overly short inter-job
  wait expired before the second pressure profile.
- Progress1 started its stopwatch after HTTPS setup, so it could not measure the
  full inactivity interval.
- Progress2 applied the constrained receive window before HELLO and prevented
  setup from completing.
- Progress3 used a premature output predicate and required authenticated cleanup
  of the resulting Loaded job.
- Progress4 let concurrent HTTPS observation compete with the deliberately
  blocked WTP output and then encountered an expired-owner cleanup path. A fresh
  authenticated claim safely aborted and released the job.

These failures charge three RF jobs and 300 planned seconds. The accepted TLS
and transport packets charge four RF jobs and 500 planned seconds. Package 3
therefore charges seven RF jobs and 800 planned seconds in total, with zero
flashes, BOOTSEL transitions, configuration writes, controlled reboots or Pico
Wi-Fi cycles.

## Adversarial review

The first source review found that the progress auditor trusted summarized
results too heavily. It was strengthened to bind authenticated peer hashes,
raw target-close rows, raw HTTPS responses, raw WTP frames, the exact LOAD hash,
recovery messages and final ABORT/RELEASE authority. A later final pass found
that the output-timeout check still accepted only the last close sample. The
auditor now requires the raw transition from a Loaded endpoint with live TCP
segments and a non-close reason through at least 4.8 seconds to reason 4 and
reclaimed transport resources. It also binds the exact CLAIM, STATUS, ABORT and
RELEASE request/response pairs and the eight-byte prefix to a valid STATUS
frame.

The final mutation assessment rejected all 10 TLS mutations, all 11 transport
mutations and all 15 progress mutations, including five new cases aimed at the
hardened proof. Mutations covered packet identity,
source thresholds, final inventories, peer identity, timing, partial bytes,
the LOAD wire image, HTTP bytes, ACK-filter cleanup, native observation and
final authority, queued transport resources and request/response pairing. Each
intact packet then passed its independent auditor again.
These mutations are synthetic evidence-integrity challenges, not forecasts of
normal field failures. The maximum-LOAD no-read case is also an intentional
stress condition; the ordinary idle, interrupted and multi-client paths are the
realistic operating cases.
No actionable finding remains.

## Restoration and scope

The fixture cleanup recorded no failures and restored the original interfaces,
routes, permanent `time.local` service and installed WsprryPi PID 1957 on host
boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`. The shared two-Pico reservation is
released. Fresh final evidence shows A and B Empty, inactive and unowned with
configuration preserved.

Package 3 closes `2.2c`–`2.2f`, `2.3a`–`2.3c` and `R3.BROWSER-MAX` only. USB
pressure, retained capacity/eviction/expiry, three equivalent cycles and R3
closeout remain Packages 4–6. R3 and full Phase 11.5 remain OPEN with 2/6
families closed and no accepted full configuration.
