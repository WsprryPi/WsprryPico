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
| Shared access; contextual recovery | Login/logout, password visibility, occupied login inspection/explicit retirement, notices, discard/reload, review and saved configuration comparison; pending setup receipt/check/continuation beside its form | Existing session and readback adapters; no navigation login |
| Station status | [Contextual job/schedule console](status-console.md), mode/frequency/progress/correction, clocks, Reset Pico, detailed output/owner/connection observations and existing Abort/Release | Read-only observations; explicit existing job controls |
| Station Control | Callsign, four/six-character locator, WSPR power and saved/draft plans | One visible profile-appropriate editor: consumer transactional setup or engineering configuration |
| Station Control | WSPR enable, period/phase pairs and expiry; independent Radio pins section with RF/button/LED GPIO, amplifier control, LPF/I²C help and drive | WSPR progress save/scoped apply excludes pins; independent hardware PUT preserves schedules; saved pins require restart |
| Station Control | Message, mode, frequency/shift, dot/repeats/gaps, timing, start; JSON job file/start, preview/result/progress | Explicit existing Load/Arm; one JobService |
| Wi-Fi/Host | SSID, new password/visibility, time server | Consumer authenticated transactional wrapper or engineering configuration; no duplicate read-only inputs |
| Wi-Fi/Host | Saved/active/default hostname, Save/default/review, restart/cancel/countdown/continuation, explicit restart continuation | Existing hostname/restart/network adapters; engineering name remains credential-bound |
| AP commissioning | Wi-Fi credentials/time server; optional station identity, Identify; trial/save/refusal/crypto fallback, recovery/reset and help links | Existing AP-only bootstrap/owner/reset; complete commissioning before control |

Disclosure headings name their control groups through `aria-labelledby` where a separate legend would repeat the same title: Radio pins, both profile-specific Wi-Fi editors, Pico password and USB logging. Distinct subgroup legends such as Station identity, Amplifier control and LPF / band selector remain visible.

Amplifier control groups enable GPIO, polarity, lead and tail. Save amplifier config uses the existing hardware and timing resources in sequence, verifies pin readback before timing, and refreshes the shared settings revision after confirmation. It preserves unrelated pin drafts. An interrupted or partial save retains readback/review requirements; the two resources do not form an atomic transaction. The footer embeds the selected firmware build version for both views. Password access uses a red lock border while locked and green while unlocked; certificate access retains its separate information state.

Status summaries can repeat saved values but are visibly observations. The conditional Review saved settings comparison is at the bottom of Station, immediately above About this Pico / Diagnostics. Discard edits and reload is a shared signed-in action above the task areas. Pending setup checks and reconnection instructions are mounted beside the matching Wi-Fi or station form. Abort/Release and Reset Pico belong to Station status. Wi-Fi/Host contains no transmitter status, reset, Wi-Fi-disconnect or temporary-setup panel. Passwords
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
| Review saved settings | `saved-settings` | Station; hidden until review is needed or explicitly bookmarked | Hidden; revealed on recovery | Shared / `top` |
| Time and calibration | `time-calibration` | Station; NTP timeout and RF correction for every mode | Closed | Station Control / `top` |
| WSPR Configuration | `radio-settings` | Station; identity, saved message type, frequency and schedules | Closed | Station Control / `top` |
| Radio pins | `radio-pins` | Station; independent hardware save and drive settings | Closed | Station Control / `top` |
| CW Modes | `message-section` | Station; capability-gated message/file controls | Closed | Station Control / `top` |
| Wi-Fi network | `wifi-settings` | Wi-Fi/Host; one profile-appropriate editor | Closed | Wi-Fi/Host / `top` |
| Pico password | `pico-password-section` | Wi-Fi/Host; consumer setting when supported | Closed | Wi-Fi/Host / `top` |
| Device hostname | `hostname-section` | Wi-Fi/Host; credential-bound engineering names remain read-only | Closed | Wi-Fi/Host / `top` |
| Logging | `connection-section` | Wi-Fi/Host; existing carrier capabilities | Closed | Wi-Fi/Host / `top` |

A valid explicit bookmark reveals its target on entry. Legacy form, area and heading fragments map to their containing section. Unknown, overlong and malformed fragments select no section. Validation reveals a field's task area and containing disclosures before browser focus. Closing a managed section closes UTC popovers and moves hidden focus to its summary. Global errors, transmitter/reset outcomes and save-recovery reveal links remain outside collapsed bodies. Radio-editor refusals and malformed or unconfirmed results also provide a persistent global notice and Review radio settings result link, including after Top; drafts remain intact.

Every managed section has a Top link. Deliberate activation closes UTC popovers, focuses the persistent hostname heading, closes all managed sections and their nested technical disclosures in both areas, then scrolls to `top`. Status details are merged into the single flat Station status section. Top preserves authentication, drafts, selected files, mutation state and uncertain-save evidence. Scrolling is immediate and does not add motion.

Navigation preserves `#save=...` and `#hostname-return=...` byte-for-byte. While a receipt occupies the fragment, only an allowlisted section/area is stored under `history.state.wsprrypicoPresentation`; existing History fields are preserved; a prior primitive or array is retained under `wsprrypicoPreviousState`. Same-document Back/Forward restores section or Top intent. Reload exposes a pending setup receipt beside its Wi-Fi or station form, and a hostname return receipt at Device hostname, including after Top. Receipt fragments and unrelated History data remain intact. Modified clicks or copied ordinary section links open a fresh page at that section without transferring the current tab's receipt or authority. No credentials, proofs or session keys enter History or storage. Receipt navigation never confirms a save.

## Browser access

A 44 px native lock button precedes the hostname text node. Its action/state labels describe this browser's application access. It does not describe HTTP security, RF state or JobService ownership. Ordinary signed-out entry keeps the password dialog closed and public consumer status polling active. Deliberate activation opens a native modal with password focus, Enter submission, Escape/Close cancellation, an eye control and secondary occupied-login recovery. Backdrop clicks leave it open. Closing scrubs password fields and returns focus to the lock; observations never open it automatically.

Consumer station/AP uses the existing Consumer-Radio login/logout; password SoftAP uses `/local/v1/login` and `/local/v1/logout`. Login attempts bind an epoch and intended device/boot. Cancellation prevents late authentication from enabling controls; a late successful login is logged out through the serialized client before another login can start. Refused or ambiguous attempts remain locked with a dialog error and require an explicit attempt. Successful login alone cannot satisfy saved-state review.

Lock gates privileged controls immediately, invalidates observation epochs, invalidates in-flight observations and clears passwords, and waits for the current bounded application action before logout. Editor operations share that action authority. Chained setup requests are refused once locking starts; an unsubmitted preparation is discarded without creating a save receipt. Accepted jobs and durable writes survive. Lost logout clears local authority and reports remote uncertainty; explicit selected-session recovery remains available. Consumer public observations and redacted settings reload without a login through the independently versioned [public read descriptor](../protocol/Consumer-Radio-v1.md#public-settings-discovery). All editable settings remain disabled and dimmed while locked. Password SoftAP cannot read private status while locally locked.

Engineering certificate HTTPS instead offers Certificate access information with the observed certificate authority retained. The page cannot revoke the browser's client certificate, so it provides no cosmetic password lock or unsupported logout. TLS admission remains independently tested; the browser fixture supplies the authenticated principal.

## Contextual saved-state review

Normal public settings reads and confirmed saves show no recovery panel or stale-readback placeholder. A required comparison exposes one Review saved settings workflow and a persistent reveal link. Reading preserves edits and remains distinct from explicit confirmation. Confirmation rechecks both device/boot target and the exact reviewed revision; concurrent changes invalidate the comparison without a write. Normal refresh, login and Discard edits and reload cannot acknowledge an uncertain save. Confirmed saves close the panel only after the existing exact-revision/target reconciliation succeeds. Saved/active pin details stay inside the comparison disclosure. Top can close disclosures while preserving required review and its reveal link.

Setup receipt controls appear only for a pending request, beside the matching form. A completed result can retain a brief inline status, while Check saved result and reconnection instructions disappear. Receipt checking never resubmits the request. Moving the presentation nodes changes no API, crypto, profile, carrier or journal contract.

Station identity is inside WSPR Configuration; its legacy bookmark remains an alias. The saved draft summary carries the authoritative Type 1/2/3 plan. Time and calibration is a separate managed section. Timeout, calibration and amplifier timing load with the page; their read actions are conditional recovery controls. Selector readback keeps its concise saved/active status and omits raw boot JSON.

## Submission authority and feedback

The control page, Wi-Fi commissioning, station commissioning and recovery pages use `WsprrySubmission`. An accepted explicit asynchronous action acquires one token synchronously, before rendering or dispatch. A native top-layer modal dims the complete visible page, including an existing password dialog, and announces an operation message. The main region exposes `aria-busy`; the live message is outside that region. The foreground has no animation and adapts to light/dark preferences and narrow screens. Native modal inertness and capture guards block pointer, touch, keyboard and synthetic events; the action token also refuses direct handler reentry. Conflicting intents are refused, never queued. Local disclosures, password visibility and navigation do not start a network action.

Editor read/save helpers, USB/UDP logging, login, selected-login retirement, save reconciliation, setup receipt checks and reset share the outer action. Internal reads and multi-resource operations retain that ownership without reacquiring it. Routine polling displays no modal and leaves explicit controls eligible. A foreground intent acquires presentation immediately, invalidates the poll continuation and waits only for its current bounded exchange to drain before dispatch. The old token cannot clear the newer action. Further foreground intents are refused; this is not an operator-action queue. Setup polls discard observations that overlap a new intent. The automatic Wi-Fi receipt acknowledgement uses the same authority without presenting an operator submission. It cannot clear a newer preparation. The original encrypted request and receipt are never resent by this coordinator.

Every settled outcome releases presentation in `finally`, including readiness-refresh exceptions. Eligibility is recomputed from the current authentication, target, revision and resource observations; controls are not enabled indiscriminately. The transport adapters retain their bounded deadlines. Uncertain requests retain the existing receipt or saved-state review workflow after the modal closes. An abort signal, closed page or released overlay does not establish that a durable save or accepted job was cancelled. Page suspension retains operation ownership, blocks later setup dispatch and gates in-flight control continuations; restoration drains locking before admitting another action. Intentional post-action focus, including saved-review completion and login cancellation, is restored only after modal inertness ends.

The foreground preserves Cancel login, Lock controls and Abort this browser’s job when that browser has the corresponding authority. Lock gates the session immediately and logs out after its bounded request drains. Abort invalidates old response/continuation epochs, refuses further ordinary API steps, drains the current exchange and reads current ownership before sending one ABORT for a job owned by this browser. It does not allocate a session, borrow another controller's ownership or change either automatic schedule. A polling read leaves the ordinary Abort button available. An unavailable connection reports an unconfirmed result and retains the USB Console ABORT instruction. Deliberately locking while abort is pending reports that abort remains unconfirmed.

Browser serialization is local to one document. Firmware target/revision checks, sent-once commissioning, delivery receipts, replay protection and JobService ownership remain authoritative across tabs, controllers and carriers. The AP station progress read and acknowledgement use the complete current control representation while retaining station-only mutation authority. Saved-field validation therefore accepts the same current shape as the control page.

Deterministic tests demonstrate overlapping-intent refusal, cleanup-error recovery, uncertain committed replies and preemption of an undispatched ARM. They identify browser action-lifecycle hazards; they do not establish the cause of an unobserved physical-controller lockup, RF responsiveness or availability under competing network traffic. Pi member management and firmware/disconnect paths retain their separate coordinator and device-selection authority; this Pico presentation layer grants them no new bypass. The separate engineering Bluefy provisioning surface retains its existing device-bound active-operation and cancellation rules.
