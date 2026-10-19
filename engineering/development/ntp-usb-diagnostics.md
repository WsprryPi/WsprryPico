# Bounded NTP USB diagnostics

Routine `INFO` and browser status contain current model summaries and bounded
source diagnostics. Complete μChrony training histories use the engineering
Console CDC interface:

```text
NTP HISTORY - 0
NTP HISTORY <token> <next_cursor>
NTP HISTORY @0 - 0
NTP HISTORY @0 <token> <next_cursor>
```

Without a source prefix, the request uses the selected source. `@0` through
`@3` explicitly select one of the four bounded source slots. Continue with the
same slot, returned 64-character token and cursor until `more` is false.
Each `microchrony-history-page/1` response contains at most four complete
original records and at most 4096 bytes including its newline. Each source
retains at most 64 original accepted measurements; there are no spread/recent
copies or averaged synthetic observations. Empty histories have an empty final
page. Byte bounds may yield fewer than four records per page.

Every page binds device, boot, firmware, revision, source slot/endpoint, source
epoch, source generation, retained count and statistical model summary.
The SHA-256 token identifies the snapshot and grants no authority. Staleness is
checked before cursor bounds: after an observation, endpoint change or reset,
a stale continuation returns `ntp_history_changed` even if its cursor exceeds
the shortened new history. Discard a partial snapshot and restart at zero.
Malformed or current-snapshot out-of-range cursors remain request errors.
Cursors are canonical unsigned decimal integers without signs or leading zeros
except `0`.

Records preserve original measurement ID, send/receive raw times, UTC estimate,
uncertainty, RTT and server reference/receive/transmit/root metadata. Frequency,
skew and residual runs describe the source fit; they do not prove application
of that fit or physical accuracy. `observed_raw_ns` is page-read time and never
rejuvenates a measurement. Check actual clock application and job readiness
separately. Reads do not claim ownership, apply corrections, alter configuration
or generate RF. Earlier images use different schemas; their evidence retains
its original image identity.
