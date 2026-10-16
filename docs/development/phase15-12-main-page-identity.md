# P15.12 — hostname as the main-page identity

Status: supported software acceptance complete on 2026-10-16. Baseline/reviewed source:
`f93f19bf5f6b8478d4428c07accf444390e4aa8c` on `devel`, 2026-10-16.
Initial changes were the prepared handoff plus development-index/roadmap links;
all are preserved. The first sandboxed remote read failed DNS; a network-enabled read independently
matched the baseline remote `refs/heads/devel`. Publication is pending. No other repository or device operation is selected.

## Source and state selection (recorded before implementation)

| Carrier/state | Name | Stable ID and boot | Freshness/trust |
| --- | --- | --- | --- |
| Consumer before login, LAN/IP/AP | Existing `device-presentation/1` boot-active hostname | Strict consumer identity/1; presentation must match full device and boot | Public presentation only; never authentication |
| Authenticated consumer | Existing `transmitter-hostname/1` active; saved/pending secondary | Resource target matched to local identity and current status boot | Authenticated readback supersedes public requests |
| Engineering station | Authenticated hostname resource active; configured network name only as legacy fallback | Authenticated member target and status boot; capabilities contain no ID | Existing mTLS authority; no new public endpoint |
| Engineering normal/pre-clock SoftAP | Local identity supplies full device only; authenticated hostname resource supplies boot/name when clock/auth gates admit | Existing local ID plus authenticated target/status | Local identity does not supply a boot field; pre-clock failures remain unavailable |
| Legacy unavailable hostname route | Canonical configured name from authenticated status, bound to authenticated application target | Existing application target and current status boot | Saved/default/advertised fields never promoted; no usable name gives IP-only/unavailable guidance |
| Failure/logout/restart/session loss | Retain same-device last-confirmed name with explicit label, otherwise unknown | Retain separately labelled last-observed stable/boot identity | Invalidate pending observations; new boot clears old name until fresh observation |

One small presentation controller will own heading, title and Diagnostics. It
will use native text/disclosure, keep login errors separate, preserve the light
incumbent layout, and add no polling, writes, session or RF authority. Request
contexts invalidate late public/old-target updates. No API schemas change.

## Delivered presentation and authority

`device-presentation.js` owns heading, title, stable ID, boot observation and
freshness. Each request captures an epoch; a new request, identity bind, logout
or failure invalidates superseded observations. Consumer public metadata uses an
exact schema/key set and exact current device/boot pair. A different full device
cannot replace a retained target. A new observed consumer boot clears the old
name until fresh readback. Authenticated names supersede public metadata; a late
public failure cannot mark a newer authenticated observation stale.

The one H1 and native About this Pico / Diagnostics disclosure are shared outside
both area-hidden containers. Opening/selecting text requires no login, permission,
clipboard API or request. Stable ID is all 32 lowercase hexadecimal characters;
boot ID is separately labelled. Native focus, 44 px summary targets, light palette
and wrapping are retained. Heading/Diagnostics are ordinary text, without polling
live announcements. Explicit recovery/retirement confirmations keep their IDs.

Save and Restart stay separate. A consumer save ends its session; the old active
name remains last-confirmed, with the accepted saved name secondary and pending.
Engineering saves retain their authenticated readback. Restart monitoring never
promotes a new name without same-device/new-boot readback. Receipt, wrong-device,
draft, read/review, area/history and one-shot restart behavior stay intact.
Discovery conflicts do not rename or erase the configured active name. No API,
protocol, carrier, session crypto, profile, RF, scheduler or JobService authority
changed; there is no new polling or transport task.

## Adversarial review and repairs

A separate in-thread source/behavior assessment was used; no independent agent
review is claimed. The review tried to falsify URL/input-derived names, saved-as-
active state, late responses, former boots, wrong targets, unsupported engineering
fields, malformed metadata, false authentication, missing IDs, live announcements,
focus/area/receipt regressions, replay, session churn and generated asset limits.

| Finding / severity | Reproducer and impact | Repair and regression |
| --- | --- | --- |
| P2 false engineering signed-out message | First shared post-save branch applied consumer logout copy to engineering, whose session remains authorized | Restrict logout/stale copy to consumer; engineering VM saves and retains authenticated active/pending state |
| P2 stale public name shown current on another failed observation | Observe valid public name, then refuse/malform the next presentation read | Current failed request marks retained name last-confirmed; superseded failures are ignored; public reads cannot downgrade authenticated observations |
| P2 expired session copy remained authenticated | Refresh internally caught session loss without updating access text | Refresh/request failure exposes login and explicit ended/unconfirmed state; real-crypto Chrome expiry and VM logout checks |
| P2 ineffective test counter | Initial Diagnostics assertion compared nonexistent `active_slots` values, both undefined | Assert exact zero emitted requests and real config/profile/restart counters; fresh real-browser reassessment |
| Test-input event mismatch | VM input uses registered listener, not `oninput`; first new regression failed | Call the actual fixture listener; production uses real input events |
| Native keyboard fixture dispatch | Initial CDP Enter lacked native text/focus synchronization and failed disclosure assertion | Bring page forward, dispatch full Enter event and await native open state; do not replace with DOM-open for the keyboard check |

Final repaired-source reassessment and affected checks found no remaining
actionable findings within the selected identity/presentation scope. The
unmodified host mailbox/listener failures remain explicit validation limits. No production guard,
timeout, assertion or admission check was weakened.

## Reproduction

Use retained dependencies; no SDK, package or tool installation is required.

```sh
source scripts/xcode_env.sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls
cmake --build build-host --parallel 3
ctest --test-dir build-host --output-on-failure
node tests/device_presentation_tests.js
node tests/network_browser_tests.js
node tests/organization_routes.test.mjs build-host/consumer_bootstrap_driver
node tests/hostname_browser_integration.mjs build-host/consumer_bootstrap_driver \
  build/phase15-12-identity-final
node tests/organization_browser_integration.mjs build-host/consumer_bootstrap_driver \
  build/phase15-12-organization-browser
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
python3 scripts/validate_wtp_contract.py
```

Chrome workflows require permitted loopback sockets. They use the actual generated
PicoBootstrapServer document, exact Content-Length/CSP/script order and real
Noble/Mbed TLS Consumer-Radio cryptography. TCP ACK delivery, board effects,
clock/journals and network listeners are deterministic host boundary doubles.
No hostname is injected into the document. The long name is persisted through
the real handler and observed after a fixture reboot. Engineering normal/preclock
and station authorities use actual SoftApApi/TLS host suites, streamed engineering
assets and the engineering VM flow; a physical engineering browser is not claimed.

Final native suite and sanitizer results are recorded below.
The cross-links below already include the repaired public-failure logic. The optional Python jsonschema check may skip.
Run socket tests without concurrent compiler load: one earlier permitted full
run aborted the unchanged TLS fixture at `WorkerEngine::call`'s 100 ms mailbox
bound (`worker.cpp:25`), observed in the macOS crash report. A subsequent isolated
TLS check is retained separately; no scheduling deadline is relaxed. The first
sandboxed full run also failed six loopback-dependent groups with EPERM. These
failed originals remain in the local logs.

## Software matrix and verification results

| Case | Exercised result and evidence |
| --- | --- |
| Consumer LAN by IP/hostname, before/after login | Real generated page/crypto workflow shows reported/active name with matching title and exact stable ID; no URL-derived identity |
| AP and both task areas | Real organization workflow covers AP/LAN defaults, reciprocal links, History/reload, drafts, focus, receipts and no new session allocation |
| Engineering station / normal / pre-clock | Actual TLS and SoftApApi gates plus engineering VM identity from member target; local identity has no fabricated boot; no capabilities ID |
| Draft/default/saved before restart | VM and real persisted rename retain active heading; saved/pending name secondary; inputs never update primary identity |
| Restart and new origin | Real crypto/profile/new-boot fixture observes same device ID and intended active/saved name; continuation needs fresh login/readback |
| Refused/lost saves, expiry/logout/disconnect | VM and real browser retain drafts, last-confirmed identity and accurate login state; no save/restart replay |
| Delayed public/old authenticated response and wrong device/boot | Controllable VM replies cannot overwrite newer authenticated/boot observations; actual wrong-device receipt refuses credential start |
| Malformed/unavailable metadata | Exact schema/IDs/boot/name checks reject Unicode, HTML, overlong/noncanonical/missing fields; unavailable public route retains functional real login; legacy engineering reads existing target/status |
| Duplicate name/discovery failure | Separate controller instances keep distinct full IDs for the same name; existing discovery conflict/failure VM cases keep configured name and independent reachability |
| Two tabs | Two genuine production fixtures/IDs keep independent names/IDs through rename/reload; no shared storage introduced |
| Long name/a11y | Real persisted 69-character name, both viewports/preferences, native keyboard disclosure, selection, 200% zoom and no horizontal overflow |
| Side effects/assets | Exact zero requests for Diagnostics/navigation; real config/profile/restart counters unchanged; all served CSP hashes and script order, static Content-Length and flash/RAM budgets checked |

Final host batch: 200 executable groups passed; five loopback groups reported
`TLS start error -1` before READY; one optional schema check skipped (206
registered). The five unchanged groups then all passed together in 18.23 s:
`network_tls_tests`, `network_tls_nagle_tests`, `network_local_wtp_tests`,
`network_plain_wtp_tests`, `network_plain_admission_tests`. Thus all **205
executable groups have passing final-source results**, with one optional skip;
there was no single all-green full-batch invocation. The transient listener
startup failures are retained, not reclassified as product passes. No listener
or test timeout was changed. The earlier mailbox abort also remains recorded.

Locked bootstrap package tests pass 17/17, bundle regeneration is unchanged, and
WTP/1 validates 23 schema, 7 raw JSON, 1 framing and 8 transition cases.
`clang-format --dry-run --Werror tests/network_tests.cpp`, whitespace and changed
Markdown local-target checks pass. The only optional skip is
`config_update_schema` because Python jsonschema is unavailable; no dependency
was installed to hide it. Source SHA-256 values are retained in ignored
`build/phase15-12-source-manifest.json` and checked before publication.

Affected ASan/UBSan final results: **32 executable checks passed**, plus the
same optional schema skip (33 selected, 17.14 s). The retained separate
`build/phase15-11-asan` build uses `-fsanitize=address,undefined
-fno-omit-frame-pointer`; it is rebuilt from P15.12 source. Selection covers the
native generated-serving, consumer/engineering adapters, sessions/recovery,
profile/config preservation and browser identity tests. macOS runs use
`ASAN_OPTIONS=detect_leaks=0`; this is not leak detection.

Reproduce the loopback reassessment with:

```sh
ctest --test-dir build-host --output-on-failure \
  -R '^network_(tls_tests|tls_nagle_tests|local_wtp_tests|plain_wtp_tests|plain_admission_tests)$'
```

Final local logs: `/private/tmp/p1512-reassessed-full-suite.log`,
`p1512-final-tls-group.log`, `p1512-tls-isolated.log`,
`p1512-reassessed-asan-tests.log`, `p1512-reassessed-identity-browser.log`,
`p1512-organization-browser.log`, `p1512-reassessed-firmware-build.log`,
`p1512-final-firmware-{size,sha256}.txt` and `p1512-impeccable.json`.
Failed originals include `p1512-initial-suite.log`, `p1512-final-suite.log` and
`p1512-identity-browser.log`. The source review and evidence distinguish failed
fixture operations from supported software behavior and physical qualification.

## Asset and firmware budgets

Both images cross-link using retained pinned SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1 and cached
picotool `6f6458d792b93685a11423b244a585eaa99eafcf`, `pico2_w` / RP2350,
138 MHz, version `0.1.0-rc.3-p1512-candidate`. CMake's generic
“Downloading Picotool” message resolves to the retained local source/executable;
no new SDK/toolchain installation was performed.

```sh
source scripts/xcode_env.sh
cmake -S . -B build/consumer-lan-pico \
  -DWSPRRY_PICO_FIRMWARE_VERSION=0.1.0-rc.3-p1512-candidate
cmake --build build/consumer-lan-pico \
  --target WsprryPico WsprryPico-StandaloneRF --parallel 3
arm-none-eabi-size build/consumer-lan-pico/firmware/WsprryPico.elf \
  build/consumer-lan-pico/firmware/WsprryPico-StandaloneRF.elf
```

| Image | text | Delta from P15.11 | data | BSS, unchanged |
| --- | ---: | ---: | ---: | ---: |
| Standard inhibited | 2,115,864 | +7,584 | 0 | 173,536 |
| StandaloneRF | 2,131,204 | +7,584 | 0 | 329,476 |

App literal is 64,777 bytes (+970); presentation helper 4,363 (new), organization
6,324 and radio bundle 64,647 (unchanged). All literals remain below 65,536.
Actual engineering document is 99,703 bytes; consumer document is
205,171, streamed uncompressed from static flash parts (+6,243 relative to the
P15.11 recorded page counts). The generator prints a 99,702-byte intermediate
engineering string; served part endings add one newline byte. Counts above
use the actual parts and production HTTP response. CMake configure
dependencies, inline script order, engineering asset route and CSP hashes all
include the helper. The actual consumer served routes check every script hash,
complete Content-Length and all six scripts; engineering host streaming checks
the helper precedes app initialization. No page-sized RAM copy was added.
Bootstrap/owner/key bundles remain 55,629 / 59,415 / 40,787 bytes.

Linked flash/journal, USB, BTstack, allocator, stack-guard, GP14 and RAM-renderer
checks pass. Renderer stays 660 bytes in RAM, initialized RAM 13,976 and worker
storage 166,176. These are link budgets, not measured target high-water marks.

| Local ignored artifact | SHA-256 |
| --- | --- |
| Standard ELF | `4020ece7cb108fb4213192ad6cd4dda0e4de5283a801b6516afdf5cc4466144f` |
| Standard UF2 | `c52296490fd40c65116731c163b431c0f03abe86f226ad1a0def38e3173ff2c9` |
| StandaloneRF ELF | `72e05f09d04ba7e97102c420c6b1ff7dcc754d68ee77ca7d52ab97f7a4252f08` |
| StandaloneRF UF2 | `8f8abacf5a6ae65ff8433d024c5fcada14336f0f7430d3af137322ec58ff5916` |

## Visual evidence and limits

The bounded final batch has 54 identity PNGs under ignored
`build/phase15-12-identity-final/`, plus the preserved organization workflow's
33 PNGs under `build/phase15-12-organization-browser/`. The identity harness's
first capture counter omitted its original zoom image; corrected accounting
includes both zoom screenshots. A subsequent no-capture reassessment reruns
behavior without another visual-polishing loop.

Desktop 1280×900 and mobile 390×844 use both light/dark preferences; the product
retains its light theme. Inspected renders include signed-out shared chrome,
expanded Diagnostics/selected full ID, active and pending names, unknown fallback,
maximum 69-character name, expired/disconnected state and 200% zoom. Full names
wrap without truncation or horizontal overflow. The native disclosure keeps visible
keyboard focus; heading/identity updates do not focus or announce periodically.

| Local ignored screenshot | State / P15.14 use |
| --- | --- |
| `signed-out-wifi-diagnostics-desktop-light.png` | Public hostname, selectable stable ID and boot observation, authorization separation |
| `authenticated-station-diagnostics-mobile-light.png` | Shared identity on Station/Transmission |
| `saved-rename-pending-mobile-light.png` | Active heading plus separately saved/pending name |
| `maximum-active-hostname-mobile-light.png` | Complete 69-character persisted active name |
| `long-name-zoom-200.png` | Maximum name and stable ID at 200% zoom |
| `unknown-name-desktop-dark.png` | Unknown name with IP/AP guidance under dark preference |
| `session-expired-mobile-light.png` | Ended login and last-confirmed identity |
| `disconnected-last-confirmed-mobile-light.png` | Connection failure retains honest same-device name |

Impeccable context allowed this narrow incumbent refinement without initializing
PRODUCT.md or repairing unrelated metadata. Its one mechanical detector pass was
**degraded**: htmlparser2/css-select/css-tree/domutils were unavailable. Seven
regex advisories concerned incumbent palette/type values in style.css; computed
contrast/selectors were not evaluated. No detector pass or dark theme is claimed.
The final functional public-failure repair changes state logic only; it does not
change the inspected visual system.

No board was flashed, restarted or controlled. No physical Wi-Fi, captive browser,
mDNS, target timing, heap/stack high-water, endurance, RF or another repository's
release acceptance is established. Link budgets are separate from measurements.

## Documentation Impact

Updated current Pico browser API guidance, consumer LAN guidance, embedded design
record, development index, roadmap and this acceptance packet. The prepared prompt
is preserved. Historical P15.10/P15.11 and Phase 14 acceptance retain their exact
scope. P15.8 closure and P15.9's pending Pi step 15 remain unchanged. P15.13 band
qualification and P15.14 operator publication remain separate. No independent
operator-document repository or Pi source was changed or published.

P15.14 instructions: find the Pico at its reported hostname, retaining current IP
and button-opened setup Wi-Fi as recovery paths; identify it using the full stable
ID under About this Pico / Diagnostics, especially for duplicate names. Explain
that public names do not authorize access. Show active versus saved/pending names,
separate Save/Restart, same-device/new-boot readback, last-confirmed and unknown
states, and accurate signed-out/expired messages. Show both task areas, expanded
Diagnostics with selected full ID, pending rename, maximum/narrow-screen layout
and IP/AP recovery. The fixture screenshot inventory above is an editorial packet;
physical product screenshots and operator publication belong to P15.14.

## Compatibility and publication

The unchanged-Pi argument is bounded to presentation: API envelopes, route
admission, identity decoders, management schemas, crypto transcripts and native
Pi-facing resources have no implementation changes. The only native serving
change is generated static content and an engineering script asset. The existing
P15.11 exact-pair acceptance is historical; no new Pi-pair or Pi-release acceptance
is claimed or required for this UI-only slice. Genuine consumer/engineering host
paths and frozen WTP artifacts are rerun here.

Publication and exact implementation/tested commit pins are pending.
