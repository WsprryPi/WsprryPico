# Browser pages

Use one control document with two areas and same-document History navigation.
`/station` and `/wifi-host` are reloadable area links; fragments select allowlisted sections or retain their existing save-receipt meanings. This avoids another authentication slot,
retains all DOM drafts, and shares flash-backed document/scripts. Fresh admitted
LAN root selects Station Control. Fresh committed-consumer AP root selects
Wi-Fi/Host using the accepted connection classification. Blank/network-only AP
keeps Wi-Fi-first commissioning, with station commissioning separately linked.
No connection inference comes from a browser URL. Area selection grants no API
authority. Existing identity/presentation and cryptographic schemas stay frozen.

## Field, summary and action ownership

| Area / shared region | Fields, observations and actions | Save authority |
| --- | --- | --- |
| Shared access; Station recovery | Login/logout, password visibility, occupied login inspection/explicit retirement, notices, reload/read/review, saved configuration comparison, pending setup receipt/check/continuation | Existing session and readback adapters; no navigation login |
| Station status | [Contextual job/schedule console](status-console.md), mode/frequency/progress/correction, clocks, Reset Pico, detailed output/owner/connection observations and existing Abort/Release | Read-only observations; explicit existing job controls |
| Station Control | Callsign, four/six-character locator, WSPR power and saved/draft plans | One visible profile-appropriate editor: consumer transactional setup or engineering configuration |
| Station Control | WSPR enable, period/phase pairs and expiry; independent Radio pins section with RF/switch/indicator GPIO, amplifier polarity, LPF/I²C help and drive | WSPR progress save/scoped apply excludes pins; independent hardware PUT preserves schedules; saved pins require restart |
| Station Control | Message, mode, frequency/shift, dot/repeats/gaps, timing, start; JSON job file/start, preview/result/progress | Explicit existing Load/Arm; one JobService |
| Wi-Fi/Host | SSID, new password/visibility, time server | Consumer authenticated transactional wrapper or engineering configuration; no duplicate read-only inputs |
| Wi-Fi/Host | Saved/active/default hostname, Save/default/review, restart/cancel/countdown/continuation, explicit restart continuation | Existing hostname/restart/network adapters; engineering name remains credential-bound |
| AP commissioning | Wi-Fi credentials/time server; optional station identity, Identify; trial/save/refusal/crypto fallback, recovery/reset and help links | Existing AP-only bootstrap/owner/reset; complete commissioning before control |

Status summaries can repeat saved values but are visibly observations. Recovery and receipt/readback controls are at the bottom of Station, immediately above About this Pico / Diagnostics. Abort/Release and Reset Pico belong to Station status. Wi-Fi/Host contains no transmitter status, reset, Wi-Fi-disconnect or temporary-setup panel. Passwords
stay volatile and retain existing clearing boundaries. Save never arms a job.
Engineering area saves preserve unrelated saved values and drafts; independent incomplete fields use the separate saved-progress contract.

## Routes and compatibility

`/`, `/index.html`, `/radio`, `/owner.html`, `/recovery.html` remain meaningful.
Committed consumer control aliases are admitted by the same exact Host/interface
policy; raw APIs remain AP-only. Unprovisioned/network-only `/station` aliases
station commissioning and `/wifi-host` aliases Wi-Fi commissioning. Unsupported
control entry explains commissioning/recovery rather than granting a session.
Engineering aliases use existing mTLS/local-session authority. API errors remain
JSON errors; safe foreign-Host captive GETs retain the fixed AP redirect.

## Sections and navigation

Transmitter status leads Station Control and is hidden with that view on Wi-Fi/Host. Ordinary fresh entry leaves every managed section closed. Native disclosures retain the existing form nodes, file selection and drafts; opening a section makes no request. Header links select Station Control or Wi-Fi/Host, mark the active view with an underline and aria-current, and scroll to window top. There is no body navigation or Sections menu. Explicit allowlisted bookmarks select their area, reveal the section and ancestors, focus its summary and scroll to it. Opening one section leaves others open. Status polling, typing and authentication do not reset disclosure choices.

| Label | Stable section ID | Area / visibility | Default | Menu group / Top |
| --- | --- | --- | --- | --- |
| About this Pico / Diagnostics | `device-diagnostics` | Shared, all admitted control pages | Closed | Shared / `top` |
| Saved settings and recovery | `saved-settings` | Shared; consumer receipt tools conditional | Closed, except a save continuation | Shared / `top` |
| Station identity | `station-identity` | Station; one consumer or engineering editor | Closed | Station Control / `top` |
| WSPR Configuration | `radio-settings` | Station; capability-gated editors | Closed | Station Control / `top` |
| Radio pins | `radio-pins` | Station; independent hardware save and drive settings | Closed | Station Control / `top` |
| CW Modes | `message-section` | Station; capability-gated message/file controls | Closed | Station Control / `top` |
| Wi-Fi network | `wifi-settings` | Wi-Fi/Host; one profile-appropriate editor | Closed | Wi-Fi/Host / `top` |
| Pico password | `pico-password-section` | Wi-Fi/Host; consumer setting when supported | Closed | Wi-Fi/Host / `top` |
| Device hostname | `hostname-section` | Wi-Fi/Host; credential-bound engineering names remain read-only | Closed | Wi-Fi/Host / `top` |
| Logging | `connection-section` | Wi-Fi/Host; existing carrier capabilities | Closed | Wi-Fi/Host / `top` |

A valid explicit bookmark reveals its target on entry. Legacy form, area and heading fragments map to their containing section. Unknown, overlong and malformed fragments select no section. Validation reveals a field's task area and containing disclosures before browser focus. Closing a managed section closes UTC popovers and moves hidden focus to its summary. Global errors, transmitter/reset outcomes and save-recovery reveal links remain outside collapsed bodies. Radio-editor refusals and malformed or unconfirmed results also provide a persistent global notice and Review radio settings result link, including after Top; drafts remain intact.

Every managed section has a Top link. Deliberate activation closes UTC popovers, focuses the persistent hostname heading, closes all managed sections and their nested technical disclosures in both areas, then scrolls to `top`. Status details are merged into the single flat Station status section. Top preserves authentication, drafts, selected files, mutation state and uncertain-save evidence. Scrolling is immediate and does not add motion.

Navigation preserves `#save=...` and `#hostname-return=...` byte-for-byte. While a receipt occupies the fragment, only an allowlisted section/area is stored under `history.state.wsprrypicoPresentation`; existing History fields are preserved; a prior primitive or array is retained under `wsprrypicoPreviousState`. Same-document Back/Forward restores section or Top intent. Reload additionally exposes pending recovery, including after Top. Modified clicks or copied ordinary section links open a fresh page at that section without transferring the current tab's receipt or authority. No credentials, proofs or session keys enter History or storage. Receipt navigation never confirms a save.

## Browser access

A 44 px native lock button precedes the hostname text node. Its action/state labels describe this browser's application access. It does not describe HTTP security, RF state or JobService ownership. Ordinary signed-out entry keeps the password dialog closed and public consumer status polling active. Deliberate activation opens a native modal with password focus, Enter submission, Escape/Close cancellation, an eye control and secondary occupied-login recovery. Backdrop clicks leave it open. Closing scrubs password fields and returns focus to the lock; observations never open it automatically.

Consumer station/AP uses the existing Consumer-Radio login/logout; password SoftAP uses `/local/v1/login` and `/local/v1/logout`. Login attempts bind an epoch and intended device/boot. Cancellation prevents late authentication from enabling controls; a late successful login is logged out through the serialized client before another login can start. Refused or ambiguous attempts remain locked with a dialog error and require an explicit attempt. Successful login alone cannot satisfy saved-state review.

Lock gates privileged controls immediately, invalidates observation epochs, invalidates in-flight observations and clears passwords, and waits for the current bounded application action before logout. Editor operations share that action authority. Chained setup requests are refused once locking starts; an unsubmitted preparation is discarded without creating a save receipt. Accepted jobs and durable writes survive. Lost logout clears local authority and reports remote uncertainty; explicit selected-session recovery remains available. Consumer public observations and redacted settings reload without a login through the independently versioned [public read descriptor](../protocol/Consumer-Radio-v1.md#independent-public-settings-discovery). All editable settings remain disabled and dimmed while locked. Password SoftAP cannot read private status while locally locked.

Engineering certificate HTTPS instead offers Certificate access information with the observed certificate authority retained. The page cannot revoke the browser's client certificate, so it provides no cosmetic password lock or unsupported logout. TLS admission remains independently tested; the browser fixture supplies the authenticated principal.
