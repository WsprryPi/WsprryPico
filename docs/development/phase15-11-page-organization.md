# P15.11 — Station/Transmission and Wi-Fi/Host

Status: implementation in progress; acceptance is not yet established.

## Source and selected organization

WsprryPico leads on `devel`, initially
`7cbc9374218fe5d534b067216ca2c555a20240b9`; remote `refs/heads/devel`
independently matched on 2026-10-16. Existing index/roadmap edits and the
untracked execution handoff are preserved. WsprryPi remains read-only.

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
| Shared transmitter status | Job, output, clock, owner, engine, Wi-Fi, hostname/discovery summary, Refresh, Abort/Release and recovery guidance | Read-only observations; explicit existing job controls |
| Station/Transmission | Callsign, four/six-character locator, WSPR power and saved/draft plans | One visible profile-appropriate editor: consumer transactional setup or engineering configuration |
| Station/Transmission | Schedule enable, period/phase pairs, expiry, RF/switch/indicator GPIO and polarity, unavailable amplifier/LPF/I²C help | Existing configuration journal, separate saved/active pin semantics |
| Station/Transmission | Message, mode, frequency/shift, dot/repeats/gaps, timing, start; JSON job file/start, preview/result/progress | Explicit existing Load/Arm; one JobService |
| Wi-Fi/Host | SSID, new password/visibility, time server | Consumer authenticated transactional wrapper or engineering configuration; no duplicate read-only inputs |
| Wi-Fi/Host | Saved/active/default hostname, Save/default/review, restart/cancel/countdown/continuation, Disconnect Wi-Fi and AP/button/IP guidance | Existing hostname/restart/network adapters; engineering name remains credential-bound |
| AP commissioning | Wi-Fi credentials/time server; optional station identity, Identify; trial/save/refusal/crypto fallback, recovery/reset and help links | Existing AP-only bootstrap/owner/reset; complete commissioning before control |

Status summaries can repeat saved values but are visibly observations. Recovery,
Abort/Release and receipt/readback controls remain outside area hiding. Passwords
stay volatile and retain existing clearing boundaries. Save never arms a job.
Engineering area saves preserve unrelated saved values and drafts; initial
incomplete persistent configuration remains outside this slice (P15.9).

## Routes and compatibility

`/`, `/index.html`, `/radio`, `/owner.html`, `/recovery.html` remain meaningful.
Committed consumer control aliases are admitted by the same exact Host/interface
policy; raw APIs remain AP-only. Unprovisioned/network-only `/station` aliases
station commissioning and `/wifi-host` aliases Wi-Fi commissioning. Unsupported
control entry explains commissioning/recovery rather than granting a session.
Engineering aliases use existing mTLS/local-session authority. API errors remain
JSON errors; safe foreign-Host captive GETs retain the fixed AP redirect.

## Acceptance, review and Documentation Impact

Pending: behavioral routing, real served-browser workflow, full host checks,
affected sanitizers, both firmware links, unchanged-Pi compatibility, bounded
visual inspection/detector, independent adversarial review and final reassessment.
No physical network/captive/Wi-Fi/RF acceptance is claimed.

## Execution evidence and repairs

During execution, concurrent documentation-only commit
`fa036bc13964c4a408996c8522c1b7fb09e3d82c` published the handoff and recorded the
operator's P15.8 integration closure. Its changes were inspected and preserved.
P15.11 did not close P15.8 or change P15.9's pending status. The original prompt's
older P15.8 status is historical. No other repository was edited by this work.

The control document retains its hostname-first Station control title in both
areas. Area navigation adds no identity/presentation fields and requires no
extra login. Explicit links scroll to the selected area; polling, authentication,
back/forward and fragment changes neither focus nor automatically scroll it.
A known section bookmark selects its area, while an explicit area choice can
override the bookmark. Only the two existing receipt kinds are carried through
area changes. Same-document setup receipts validate device identity before
credentials/API use and cannot submit from their retained metadata.

Engineering station/network saves validate only their own fields and use the
advertised `transmitter-config-update/1` merge with exact target and current
revision. A schedules/pins save reconstructs from authoritative saved station
and Wi-Fi, preserving extensions and ignoring unrelated drafts. Initial complete
engineering configuration retains a separate explicit creation action; it still
requires complete valid station, network and schedule dependencies. Partial
incomplete durable drafts and broader P15.9 behavior are not implemented here.

| Finding / severity | Reproducer and repair | Regression / reassessment |
| --- | --- | --- |
| P2 bookmark overrides area choice | `/wifi-host#hostname-form`, then Station; retain only receipt hashes on explicit area changes | VM and production Chrome reciprocal navigation/back/forward pass |
| P2 hidden credential in save intent | Engineering merge copied `config.wifi.password` into recovery intent; redact nested and ordinary password shapes | VM checks retained intent has null password and input is cleared |
| P2 initial engineering creation lost | Config GET null made scoped-only saves impossible; restore explicit complete initial configuration action | VM verifies one complete PUT with operator station/network fields |
| P2 Reload did not discard draft | Engineering dirty flags made fill preserve even confirmed Reload; include/clear those flags on explicit confirmation | VM verifies actual saved field restoration |
| P2 receipt/bookmark erased by poll | Setup receipt updater cleared unrelated fragments; preserve other receipt/bookmark kinds | VM retains original-boot hostname return and section bookmark after login |
| Validation-order observation | Busy handling disabled controls before native validation; validate before entering action | Invalid station field emits no merge request |
| Expected unavailable-route test mismatch | Old `/index.html` test expected 404; new compatible alias deliberately serves recovery guidance | Assert 200 with no form/password and a concrete USB recovery step |

Independent reviewer `/root/organization_review` performed initial and repaired
source/behavior assessments and independently reran VM/browser-routing checks.
Final reassessment found no remaining actionable findings in its inspected
routing, auth, field ownership, drafts, receipts, sessions and asset/CSP scope.
No production admission, ownership, deadline or safety guard was weakened.

Chrome 155.0.8059.40 ran the production PicoBootstrapServer fixture with real
Noble/Mbed TLS cryptography and explicit TCP/board/time doubles. No route
substitution supplied the document. The organization workflow verifies both
AP/LAN defaults, reciprocal links, station/network/hostname/message/schedule
drafts, history/reload, no background login, no session churn, no config/profile
write or restart from navigation, fixed focus during refresh, blank/network-only
commissioning, unavailable guidance and missing-crypto regular-browser fallback.
Desktop 1280×900 and mobile 390×844 captures use both light/dark preferences;
the shipped design remains light. The 200% zoom check reports no horizontal
overflow. Local ignored screenshots are `build/phase15-11-browser/*.png` (33)
and the retained hostname workflow's 17 captures in
`build/phase15-11-browser-hostname/`. Visual inspection covered the actual
station and Wi-Fi editors, defaults and shared status. Impeccable's single
mechanical detector pass was **degraded**: parser modules were absent, so only
regex advisories were available; computed contrast/selectors were not assessed.
The reported palette/type advisories are incumbent conventions. No detector
pass or dark-theme implementation is claimed.

The hostname workflow also passes two device-bound titles, canonical refusal,
profile-generation relogin/review, saved/active distinction, lost reply/no
replay, one-shot restart/cancel, new-boot readback and wrong-device/no-login.
Existing host/session/commissioning tests cover busy/owned/armed/running/failed/
unknown output, lost setup replies before/after commit, two-client generations,
readback/review and stale receipts. These remain software boundary tests.

## Reproduction and limits

```sh
source scripts/xcode_env.sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls
cmake --build build-host --parallel 3
ctest --test-dir build-host --output-on-failure
node tests/network_browser_tests.js
node tests/organization_routes.test.mjs build-host/consumer_bootstrap_driver
node tests/organization_browser_integration.mjs build-host/consumer_bootstrap_driver \
  build/phase15-11-browser
node tests/hostname_browser_integration.mjs build-host/consumer_bootstrap_driver \
  build/phase15-11-browser-hostname
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
python3 scripts/validate_wtp_contract.py
```

Full Xcode is required for native macOS linking. The first sandboxed browser
attempt refused loopback listening with EPERM; the isolated socket-enabled run
passed. The first full/sanitizer runs retained the unavailable-alias assertion
failure above; repaired final runs are recorded at closeout. macOS sanitizer
runs use `ASAN_OPTIONS=detect_leaks=0`, with no leak-check claim. No SDK/tool
installation or physical board, Wi-Fi, GPIO, RF, service or device-state change
was performed. Physical captive-browser/network/restart behavior, target heap/
stack high-water and RF qualification remain separate.

## Documentation Impact

Updated Pico browser API and consumer LAN guidance, setup page guide, embedded
design record, development index, roadmap and this record. README, CONTRACT,
architecture, WTP/1 and original acceptance records retain their existing
meaning and were not rewritten. P15.10 closure, concurrent operator-accepted
P15.8 state and pending P15.9 status are preserved. P15.12/P15.13/P15.14 remain
separate. The independent WsprryPi-Docs checkout was inspected read-only at
`5f539fbcac1e02b0edb58c017479105647975b27`.

P15.14 operator packet: explain LAN Station/Transmission and AP Wi-Fi/Host
landing; demonstrate reciprocal links without another login; show the single
profile-specific identity/network editors and separate schedule/pin saves;
explain saved versus active state and explicit Save/Restart; show uncertain
save read/check/review, retained drafts and departure confirmation; document
network-only commissioning and engineering initial complete configuration;
retain current IP/button/AP and missing-crypto recovery instructions. Required
product screenshots: both defaults, both task editors, shared Abort/Release and
readback/receipt recovery, saved/active rename and restart/cancel/manual return,
network-only Wi-Fi-first/refusal, engineering read-only name and initial save,
and narrow-screen layouts. Physical product screenshots/publication belong to
P15.14; the local fixture captures do not qualify those claims.

## Software matrix and final checks before compatibility

| Profile/state | Default and authority | Evidence |
| --- | --- | --- |
| Blank AP | Wi-Fi first; station link explains network commissioning; no job editor | Production dispatcher and Chrome pages |
| Network-only AP | Wi-Fi first; optional station commissioning; no job control | Fresh RAM journal/runtime in production fixture and Chrome |
| Consumer AP / LAN | AP root selects Wi-Fi/Host; LAN IP/hostname root selects Station; aliases retain the shared authenticated control document | Production dispatcher streaming/CSP plus Chrome and VM |
| Consumer TLS pending | Same page/session authority; hostname and station transactions retain pending TLS state | Production browser fixture uses a real pending profile; hostname/commissioning suites |
| Materialized consumer | Same radio availability/interface branch; certificates/trust and generation rules unchanged | Consumer runtime/TLS/session host checks; source applicability, not a new physical browser claim |
| Engineering normal / pre-clock AP | AP root redirects to Wi-Fi/Host; chosen aliases serve existing control document; Configure still unavailable before clock authorization | Expanded actual SoftApApi normal/pre-clock tests, existing local-session/time refusal suite |
| Engineering station | Existing mTLS admission precedes static alias dispatch; station root remains Station; certified hostname read-only | Existing real TLS/authority host suite plus shared served-assets/VM checks; no physical engineering browser claim |
| Reset/fault/unavailable AP | Bounded read-only guidance; no form/password; applicable existing recovery/USB step | Production unavailable fixture, bootstrap HTTP and reset/fault host suites |
| Unavailable/wrong interface | Refuse rather than fabricate an editor; Host cannot change accepted interface | Production wrong-interface/Host/raw-API/unsupported-method tests, existing listener classifier suite |

Final native suite: **204 executable groups passed**, plus the optional
`config_update_schema` check explicitly skipped (205 registered; 119.95 s).
The Python `jsonschema` dependency is absent. Affected ASan/UBSan selection:
**33 executable checks passed**, with the same optional skip (34 selected;
19.04 s). Expanded engineering page-route assertions also pass independently
in the native and sanitizer builds. All 17 locked bootstrap package tests and
bundle regeneration pass. WTP/1 validates 23 schema, 7 raw JSON, 1 framing and
8 transition cases. Full Xcode/Apple Clang is used only for Pico host checks;
no Pi C++ compilation occurs on macOS.

Firmware cross-links use retained SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1, pinned cached
picotool `6f6458d792b93685a11423b244a585eaa99eafcf`, `pico2_w` / RP2350,
138 MHz and version `0.1.0-rc.3-p1511-candidate`. No SDK/toolchain was installed.

| Image | text | delta from P15.10 | data | BSS (unchanged) |
| --- | ---: | ---: | ---: | ---: |
| Standard inhibited | 2,108,280 | +12,936 | 0 | 173,536 |
| StandaloneRF | 2,123,620 | +12,952 | 0 | 329,476 |

The main app literal is 63,807 bytes, config validation 2,114 and organization
6,324; bootstrap/owner bundles are 55,629/59,415. The unchanged radio bundle is
64,647. Generation now rejects individual literals at 65,536 bytes; no warning
suppression is used. The engineering document is 93,459 uncompressed bytes;
consumer delivery includes the existing crypto bundles. Every route test pumps
the complete static parts, checks exact Content-Length, validates all five
consumer script hashes/order and no external script dependency. No page-sized
runtime copy, thread, listener or polling task was introduced.
Linked flash/journal/BTstack/allocator/GP14/stack-guard and RAM-renderer checks
pass. The renderer remains 660 bytes in RAM, worker storage 166,176 and initialized
RAM bytes 13,976. These are link budgets, not target timing or high-water measurements.

| Local ignored artifact | SHA-256 |
| --- | --- |
| Standard ELF | `0fb53c00f054d80fd26e83d5bc9ebc2582eaea6812d15f679034f72dff8a73c8` |
| Standard UF2 | `54b1d63f794eed10a28e6145b2f1a6a25f890d606221785f4775272a8a0c63c7` |
| StandaloneRF ELF | `cd7ce0ef719f81e2b4645f4058dba94a3f0f9f7b178565f5d21901ec97300631` |
| StandaloneRF UF2 | `85bbfa81c8af23a8430ce298c962ffd6f97768e4b8e1b6df6e608b95ccb71e33` |

Final logs remain local: `/private/tmp/p1511-final-full-suite.log`,
`p1511-final-asan-tests.log`, `p1511-final-engineering-asan.log`,
`p1511-final-organization-browser.log`, `p1511-final-organization-save-browser.log`,
`p1511-hostname-browser.log`, `p1511-final-firmware-build.log`,
`p1511-final-firmware-{size,sha256}.txt`, and `p1511-impeccable.json`.
