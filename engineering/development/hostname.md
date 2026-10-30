# Hostname

## Authority and supported profiles

| Profile/carrier | Hostname source | Supported operation |
| --- | --- | --- |
| Committed consumer, infrastructure HTTP | Consumer profile `tls.hostname` | Authenticated read, save, default selection and explicit restart |
| Committed consumer, available AP `/radio` | Same profile | Same password-authenticated operation; fixed AP address/SSID stay stable |
| Consumer awaiting trusted UTC/TLS | Same pending profile | Rename preserves pending state; later materialization uses the selected name after restart |
| Network-only setup | Existing stable MAC default | Complete existing station commissioning before hostname management; no partial profile or new unauthenticated write |
| Saved engineering profile | Certified profile hostname | Read-only; replace matching credentials through established engineering workflow |
| Compiled engineering bundle/legacy deployment | Existing certified bundle hostname | Read-only; no certificate authority rotation or HTTP downgrade |
| Unprovisioned, fault, reset/recovery | Existing recovery authority | No hostname write authority; recover/commission through the existing process |

The full local hostname is required: one **1–63 character ASCII LDH label**
plus `.local`, at most 69 canonical bytes. The editor also accepts one final
root dot (70 input bytes). ASCII case is normalized and the root dot removed.
Bare labels, Unicode (including Kelvin-sign case folding), whitespace, control
bytes, IP/URL/port syntax, extra labels and edge hyphens refuse without truncation.
The UI uses the same grammar as `canonical_local_hostname`.

WTP full device ID, station MAC, MAC-derived default, saved hostname, boot-active
hostname and actually advertised hostname remain separate. The AP SSID, BLE
name, default/local password, retained owners/clients, station details, schedules,
experimental flags, pin plan, STOP state and watermark do not change in a rename.
DNS-SD remains a destination hint; it supplies neither identity nor trust.

## Durable transaction, trust and boot

`GET/PUT /api/control/v1/hostname` implements stable schema `hostname` within
`Wsprry-Control/1`. Ordinary configuration merges omit this separate profile
authority and preserve it. The strict PUT contains exactly `contract`, `schema`, a full member/device/boot `target`,
and `hostname` (full name or `null` for the hardware-derived default). It requires
a current `If-Match` revision and the existing authenticated same-origin carrier.
There is no hostname reset inferred from omission. Canonical no-ops consume
neither entropy nor a profile generation. Actual changes consume a journal
generation; A/B/A never revives an old revision.

The PUT body is limited to 512 bytes. Example (use the actual target and ETag):

```json
{"contract":"Wsprry-Control/1","schema":"hostname","target":{"scope":"member","device_id":"11111111111111111111111111111111","boot_id":"00000000000000000000000000000001"},"hostname":"pico-a.local"}
```

Readback contains exactly `contract`, `schema`, `target`, `saved`, `active`, `default`,
`source`, `writable`, `reason`, `pending_restart`, decimal-string `generation`
and `storage_healthy`; the ETag is the existing application revision extended
with current profile sequence/health. Names are canonical strings; failed
storage is explicit and never writable. Source is `consumer_profile` or
`deployment`. `reason` explains storage/profile unavailability, required station
commissioning or credential-bound engineering authority. Presentation metadata
has exactly `schema`, `device_id`, `boot_id`, `hostname`; consumer presentation
is `/api/consumer/v1/presentation`, fixed-AP setup uses `/api/presentation/v1`.
These public metadata reads grant no management or transmission authority.

The profile journal alone owns both saved name and certificates. No flash
regions or Config schema change. Committing a name preserves the last setup
request digest, so existing commissioning receipts remain meaningful. Storage
admits that digest-preserving change only when every non-TLS field is identical
and the CA, server private key and pending-state authority remain unchanged.
Ordinary setup edits still require their own receipts and authority.

For a materialized consumer, a fresh trusted SNTP observation and a valid current
identity are required. Mbed TLS reissues only the server leaf, preserving the exact
CA certificate/key, server key, retained clients and CA expiry. The leaf carries
exact DNS SAN, device OU, issuer, key, purpose and bounded validity; it cannot
outlive the CA. Failure leaves the old identity intact. The complete resulting
profile is serialized and validated before one journal selection. Torn writes
and lost flash acknowledgements reconcile the durable old/new selection; an
unreadable or contradictory result closes admission and requires recovery.

The prior 2,304-byte serialized TLS subrecord could intermittently reject the
63-character boundary as ECDSA signature length varied. Its explicit JSON limit
is now **2,560 bytes**. The full profile remains **7,168 bytes**, each certificate
buffer 1,200 bytes, private-key buffer 512 bytes, and existing flash slots/regions
are unchanged. The actual full profile, including retained clients, must fit;
otherwise saving refuses. No credentials enter public responses/logs/evidence.

The running boot retains a separate immutable TLS snapshot while saved profile
metadata/generation advance. Old boot listeners, Host/Origin authority and
certificates remain coherent until restart. Sessions from the prior generation
expire, and the operator signs in again to read the saved result. Pending TLS
materialization cannot restore the hardware default over a selected name.
A profile reconciliation fault reloads runtime state, retains the boot's consumer
selection latch, closes control admission and suspends scheduling once; it cannot
reopen USB/BLE/engineering authority. Authorized reset still completes by reboot.

On the next boot, selected credentials consistently drive station mDNS/DNS-SD,
AP mDNS/local access, consumer claim naming and HTTP/HTTPS authority. The stable
recovery SSID, fixed `192.168.4.1`, password derivation and device ID remain
independent. Responder conflict remains latched with no automatic suffix.
Advertised hostname remains empty until actual responder success.

Legacy consumer profiles retain their prior effective name and trust without a
migration write. New names remain readable by older firmware only if they fit
that older firmware's TLS subrecord limit; rename to the stable default before
rolling back. Both provisioning reset and full erase remove the profile/name
through their existing reset semantics; full erase also retains its broader
station/schedule/watermark consequences. Engineering bundle/profile precedence
and tombstones are unchanged.

## Browser behavior and recovery

Station control titles begin with the confirmed active name, followed by
` - Station control`, including IP access. Unsaved edits never alter a title.
A saved rename is explicitly pending; failed observations mark identity as last
confirmed/unknown. A separate nonsecret `device-presentation/1` response supplies
initial consumer and setup titles without changing frozen identity v1. Wi-Fi,
station setup and recovery suffixes retain their existing H1/status behavior.
HTTP presentation retains Consumer-Radio/1's existing page-substitution limits.

The editor shows active and saved names and an intentional default action.
Saving and restarting are separate. After a generation change, sign in again,
refresh/read the saved hostname and explicitly review it before another save.
A refused or uncertain save retains the draft and never retries. Other drafts
remain in the current tab; no password or draft is stored for navigation.

Restart reads fresh settings and requires the name/config revisions to agree,
sends exactly one revision-guarded request, and retains the response-delivery
callback/final idle/output checks. Reconnect checks use a 90-second observation
window. Consumer identity requests cap their timeout to the remaining window;
HTTPS hostname checks use a fixed two-second timeout. A countdown already in
flight can finish at the window boundary, and an issued HTTPS check can finish
up to its two-second request bound later. There is a visible two-second countdown, cancellation,
and a manual canonical-name
continuation link. Time describes the next check, never readiness. A new boot
alone requests fresh login/readback. Success requires the same full device ID,
a different boot ID, and both saved/active names equal to the intended name.
Discovery and browser reachability remain distinct observations.

A new-origin link carries only bounded expected device/name/boot context in its
fragment. It strips URL credentials/query, preserves the supported scheme/port,
never forwards a session/password, and requires fresh login. Full navigation and
same-document fragment changes both validate the returning device before login
or API use. Wrong-device returns cannot send credentials or mutate settings.
Unrelated drafts require an explicit choice before leaving. Editing, logout,
cancellation, target changes and page lifecycle invalidate stale checks. Fresh
readback removes obsolete continuation links after a concurrent saved-name revert.

After timeout, open the confirmed saved name manually or use the current IP.
If unavailable, use the existing configured-button setup AP and fixed AP address.
A duplicate name requires choosing another name. HTTPS still requires a matching
certificate/SAN; there is no certificate bypass or automatic downgrade. Starting
a fresh explicit restart after an uncertain one requires a fresh page/read/review;
countdowns, refresh and lost replies never replay the original mutation.
