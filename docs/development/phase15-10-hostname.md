# P15.10 — Persistent hostname and page titles

Status: implementation and software acceptance in progress on 2026-10-16.
The [execution handoff](phase15-10-execution-prompt.md) defines the scope.
This record will retain the exact implementation/source pair and final results.
P15.8/P15.9 Pi release integration, P15.11/P15.12 page organization/identity,
P15.13 RF work and P15.14 operator publication remain separate.

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

`GET/PUT /api/v1/hostname` implements `transmitter-hostname/1`. Existing Config,
application, capabilities and consumer identity v1 shapes are unchanged. Ordinary
legacy/configuration saves omit this separate profile authority and preserve it.
The strict PUT contains exactly `schema`, a full member/device/boot `target`,
and `hostname` (full name or `null` for the hardware-derived default). It requires
a current `If-Match` revision and the existing authenticated same-origin carrier.
There is no hostname reset inferred from omission. Canonical no-ops consume
neither entropy nor a profile generation. Actual changes consume a journal
generation; A/B/A never revives an old revision.

The PUT body is limited to 512 bytes. Example (use the actual target and ETag):

```json
{"schema":"transmitter-hostname/1","target":{"scope":"member","device_id":"11111111111111111111111111111111","boot_id":"00000000000000000000000000000001"},"hostname":"pico-a.local"}
```

Readback contains exactly `schema`, `target`, `saved`, `active`, `default`,
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
request digest, so prior P15.7 commissioning receipts remain meaningful. Storage
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
callback/final idle/output checks. Reconnect checks use a 90-second observation window and cap the final identity
request to the remaining time. A bounded countdown already in flight may finish
at the window boundary. There is a visible two-second countdown, cancellation,
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

## Validation and evidence

The implementation is ready for an immutable source pin and exact paired Pi
checks; final acceptance remains pending their results. Native checks cover
203 executable CTest groups plus one optional schema skip. With the controlled
fragmented TLS sender described below, every executable group passed twice
(`ctest --repeat until-fail:2`, 218.41 seconds); no failed group remains. The
optional Python `jsonschema` dependency is absent, so `config_update_schema`
is explicitly skipped. The affected sanitizer
selection passed 25 executable cases with the same optional schema skip.
macOS ASan does not support leak detection; the first requested leak run aborted
before tests, and the ASan/UBSan rerun uses `detect_leaks=0`. No leak-check claim
is made. Noble tests pass 17/17; WTP contract validation passes 23 schema,
7 raw-JSON, 1 framing and 8 transition cases.

Actual Chrome 155.0.8059.40 served-page checks passed with production HTTP/AEAD,
17 desktop/mobile/light/dark captures, keyboard focus, 200% zoom, two different
full device IDs/titles, IP and hostname navigation, Kelvin refusal, generation
save/relogin/review, pending state, one-shot restart/cancel, new-boot readback,
draft preservation, dropped save/no replay and wrong returning identity/no login.
A final functional-only browser pass also passed after receipt/deadline repairs.
Screenshots remain in ignored `build/phase15-10-browser`; this is software
browser evidence, not physical LAN acceptance. The Impeccable context/setup and
one detector pass were run. Its parser dependencies were unavailable, so the
fallback detector cannot assess computed contrast/selectors; reported advisories
refer to incumbent colors/type. Visual inspection retained that established
light design under both browser preferences, with no overflow observed.

Both repaired 138 MHz standard-inhibited and StandaloneRF images cross-linked
against SDK 2.3.1 `079c6f39023649b154152db30f1d781e884879bc`, its pinned submodules
and Arm GNU 15.3.1. Preliminary repaired budgets (before final clean identity
relink): standard text 2,095,352 / BSS 173,536 bytes; RF text 2,110,684 / BSS
329,476 bytes. Direct compiler stack frames: hostname save 1,320, readback
1,360 and leaf rename 1,416 bytes. These are individual frames, not complete
call-chain or measured high-water bounds. Flash topology, allocator/BTstack
wrappers, stack guards, GP14 safety and RAM renderer link checks passed.
Final clean-image identities/budgets and paired source outcomes follow after
source-pinned verification. The default scope
is hardware-free: no flashing, GPIO/RF, installation or service operation occurred.
Compile/link budgets are not measured target timing, heap/stack high-water,
operational LAN resolution or physical restart/transport qualification.

## Adversarial review and repairs

| Finding | Trigger | Repair and regression |
| --- | --- | --- |
| R1 P1, reconcile admission | Profile verify/read fails and source resets during reload | Always reload runtime; consumer latch and dynamic healthy/generation admission; true read-failure test asserts no legacy/consumer authority |
| R2 P2, Unicode folding | Kelvin sign normalized by JavaScript | ASCII precheck; actual served-page invalid-name/no-mutation case |
| R3 P2, title freshness | Lost encrypted reply ends authentication | Mark last-confirmed title in API failure; actual dropped-reply assertion before relogin |
| R4 P2, stale link | Another client reverts a pending rename | Fresh read cancels stale checks and clears destination; A/B/A unit regression |
| R6 P2, engineering local login | Wrong-device receipt reaches non-radio local login | Fresh identity and shared local-request guard before credentials; non-radio wrong-receipt/no-login regression |
| R5 P2, URL credentials | Page URL has userinfo/query | Strip user/password/query before continuation; explicit credential-bearing URL regression |
| R7 P2, compatibility fixture | New probe expected an unsupported unchanged native Pi hostname route to work | Assert bare-resource/adapter refusal without exchange; establish rename through Pico's production coordinator, then test native old-session refusal and relogin/read/save preservation; actual authenticated rename stays covered separately |

Additional implementation checks repaired streamed assets exceeding a single
64 KiB literal, journal refusal of same-receipt hostname changes, nondeterministic
maximum-name TLS serialized sizes, and same-document return-receipt changes.
These failures remain in private build logs; final checks must assess repairs.

The full native suite twice reset the maximum concurrent TLS upload while its
unchanged-baseline and current isolated cases each passed three consecutive
runs. This does not establish a baseline defect or TCP/Nagle causation. The
fixture sends roughly 4,700 seven-byte TLS writes against a 5x accelerated
absolute request deadline (15 seconds device time, roughly 3 seconds wall time).
Independent review approved setting `TCP_NODELAY` only on that fragmented test
client: the bytes, TLS writes, concurrent maximum WTP frame, expected HTTP 400
and production deadlines stay unchanged. Upload duration is reported for this
controlled sender. The separate Nagle test covers server first-flight behavior,
not this client's upload buffering. The repeated full suite passed every
executable group twice after this change; original failures and isolated
comparisons remain retained.

## Documentation Impact and P15.14 packet

Updated: this record, browser API, configuration-update, standalone, identity,
mDNS, consumer LAN guidance, development index and current roadmap. Historical
contracts/results retain explicit supersession notes. WTP/1, pin assignment,
RF qualification and P15.8/P15.9 release status are considered unchanged.

Read-only operator-document review covered WsprryPi-Docs
`docs/User_Interface/Setup/Transmitter/index.md` (Pico settings, saved/restart and
management access), `docs/Advanced_Operations/configuration_troubleshooting.md`
and `docs/User_Interface/Maintenance/network_safety.md`. That independent repo
is not edited/published here. P15.14 must place the following operator material
there, with final product screenshots rather than development repair narration:

> In Pico Station control, sign in and enter a full local hostname such as
> pico-a.local. Choose Save hostname. Read Active and Saved separately: a saved
> name needs Restart device before the new address applies. Sign in again and
> check the saved result before repeating a save. Restart once; the countdown
> schedules connection checks and does not guarantee that the Pico is ready.
> Cancel checks to keep working in this tab, or use Continue at the saved hostname
> and sign in again. Copy unsaved drafts before leaving. Success requires the
> same Pico, a new boot and the applied name. If checks time out, try the current
> IP or the Pico's setup Wi-Fi at 192.168.4.1. For a duplicate name, choose another
> name. Engineering deployments require matching replacement certificates.

Required screenshots: canonical/max name editor; active versus saved/pending;
restart countdown/cancel/manual link; fresh-login/new-boot verification; unknown
save/readback/review; timeout/duplicate-name/IP/AP recovery; engineering read-only
certificate guidance. Pi connection docs must distinguish destination hostname,
expected TLS name and full WTP device ID after a rename. Final operator docs
publication and physical screenshots remain P15.14 work.
