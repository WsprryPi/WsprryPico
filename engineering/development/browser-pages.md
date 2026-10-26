# Browser pages

Use one control document with two areas and same-document History navigation.
`/station` and `/wifi-host` are reloadable area links; fragments retain their
existing receipt/deep-link meanings. This avoids another authentication slot,
retains all DOM drafts, and shares flash-backed document/scripts. Fresh admitted
LAN root selects Station/Transmission. Fresh committed-consumer AP root selects
Wi-Fi/Host using the accepted connection classification. Blank/network-only AP
keeps Wi-Fi-first commissioning, with station commissioning separately linked.
No connection inference comes from a browser URL. Area selection grants no API
authority. Existing identity/presentation and cryptographic schemas stay frozen.

## Field, summary and action ownership

| Area / shared region | Fields, observations and actions | Save authority |
| --- | --- | --- |
| Shared access and recovery | Login/logout, password visibility, occupied login inspection/explicit retirement, notices, reload/read/review, saved configuration comparison, pending setup receipt/check/continuation | Existing session and readback adapters; no navigation login |
| Shared transmitter status | [Contextual job/schedule console](status-console.md), mode/frequency/progress/correction, clocks, shared Reset Pico, detailed output/owner/connection observations and existing Abort/Release | Read-only observations; explicit existing job controls |
| Station/Transmission | Callsign, four/six-character locator, WSPR power and saved/draft plans | One visible profile-appropriate editor: consumer transactional setup or engineering configuration |
| Station/Transmission | Schedule enable, period/phase pairs, expiry, RF/switch/indicator GPIO and polarity, amplifier enable and unavailable LPF/I²C help | Existing configuration journal, separate saved/active pin semantics |
| Station/Transmission | Message, mode, frequency/shift, dot/repeats/gaps, timing, start; JSON job file/start, preview/result/progress | Explicit existing Load/Arm; one JobService |
| Wi-Fi/Host | SSID, new password/visibility, time server | Consumer authenticated transactional wrapper or engineering configuration; no duplicate read-only inputs |
| Wi-Fi/Host | Saved/active/default hostname, Save/default/review, restart/cancel/countdown/continuation, Disconnect Wi-Fi and AP/button/IP guidance | Existing hostname/restart/network adapters; engineering name remains credential-bound |
| AP commissioning | Wi-Fi credentials/time server; optional station identity, Identify; trial/save/refusal/crypto fallback, recovery/reset and help links | Existing AP-only bootstrap/owner/reset; complete commissioning before control |

Status summaries can repeat saved values but are visibly observations. Recovery,
Abort/Release and receipt/readback controls remain outside area hiding. Passwords
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
