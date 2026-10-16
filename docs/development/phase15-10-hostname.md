# P15.10 — Persistent hostname and page titles

Status: supported software acceptance complete on 2026-10-16.
The [execution handoff](phase15-10-execution-prompt.md) defines the scope.
Implementation, test repairs and independent reassessment are recorded below.
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

## Validation and evidence

Native checks cover 203 executable CTest groups plus one optional schema skip.
With the controlled fragmented TLS sender described below, every executable
group passed twice (`ctest --repeat until-fail:2`, 218.41 seconds). The final
rebuilt suite after the additional reset-boundary fixture repair also passed
all 203 executable groups (136.27 seconds). Its TLS case separately passed five
consecutive runs (60.51 seconds, 100 actual reset cycles). The optional Python
`jsonschema` dependency is absent, so `config_update_schema` is explicitly
skipped. The affected sanitizer selection passed 25 executable cases with the
same optional schema skip (11.31 seconds).
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

Both 138 MHz standard-inhibited and StandaloneRF images cross-linked
against SDK 2.3.1 `079c6f39023649b154152db30f1d781e884879bc`, its pinned submodules
and Arm GNU 15.3.1. Final clean configured source is
`334ea5a3aedcb14245088a7c8cd48f2e1510428e`, version
`0.1.0-rc.3-p1510-candidate`, board `pico2_w`, processor RP2350. Subsequent probe
and documentation commits do not change firmware inputs. ELF `size` budgets:

| Image | text | data | BSS |
| --- | ---: | ---: | ---: |
| WsprryPico, standard inhibited | 2,095,344 | 0 | 173,536 |
| WsprryPico-StandaloneRF | 2,110,668 | 0 | 329,476 |

Direct compiler stack frames: hostname save 1,320, readback
1,360 and leaf rename 1,416 bytes. These are individual frames, not complete
call-chain or measured high-water bounds. Flash topology, allocator/BTstack
wrappers, stack guards, GP14 safety and RAM renderer link checks passed. The
flash application region remains `0x3f3000`, preserving all journals, the BTstack
bank and final RP2350-E10 sector. The main stack still reserves 32 KiB with
28 KiB usable above its guard. The RF renderer remains in RAM (660 bytes), with
166,176 bytes of worker storage and 13,976 initialized RAM bytes reported by its
link check. RF scheduling remains on core 1; name management stays on core 0.
The root document is 84,965 bytes served from static parts. The separate app
script is 65,139 bytes and the radio bundle 64,647 bytes; these remain below
Clang's individual 65,536-byte literal ceiling. Streaming/CSP tests cover the
combined document without a page-sized per-request copy. These bounded source/
link limits do not measure the rename's target heap peak.

Final SHA-256 (local ignored artifacts, not flashed):

| Artifact | SHA-256 |
| --- | --- |
| Standard ELF | `6e23a52c8aabb67c718de747dcee33bb3f5a0e2b396e5f5c59de176d4d2696c5` |
| Standard UF2 | `65bc41f483f3f50aecce3e1b1e5e71aec321182fdf0bccc834a56101e0bcfc22` |
| StandaloneRF ELF | `0786e2db912b9b28f956ce5feb6da7d9731faafecfb6c54400bc836668791782` |
| StandaloneRF UF2 | `ed662ae8b49cfd0d89510a48f4e8738f2ed0b7c093d76a53347a79cf3ae91d3f` |

The default scope is hardware-free: no flashing, GPIO/RF, installation or
service operation occurred.
Compile/link budgets are not measured target timing, heap/stack high-water,
operational LAN resolution or physical restart/transport qualification.

## Exact sources, commands and compatibility

| Source | Immutable identity | Scope |
| --- | --- | --- |
| Initial Pico devel | `5c7585c22f7d46e120fc4be4720c84a9e8dbecd6` | Original handoff baseline; its three preparation-document changes were preserved and completed |
| P15.10 production implementation | `556f19b53688f803d4228cdcdacbd2992489639a` | Persistence, TLS, boot/admission, UI and regressions |
| TLS test-boundary repair / firmware source | `334ea5a3aedcb14245088a7c8cd48f2e1510428e` | Test-only reset barrier and private probe include; production inputs identical to implementation |
| Final compatibility harness | `ecbe2c40fc07aea2f0ea4d8bfc32a4e8770dad5e` | Test-only Pi public-header precedence repair; clean exact Pico pin for all three native pairs |
| Unchanged release Pi | `a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1` | Preserved clean release checkout; PASS |
| Accepted P15.8 Pi companion | `6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb` | Preserved clean accepted companion; PASS |
| Current integrated Pi devel | `a84010d6c16ac416d52989053ac1f273390a8ab5` | Concurrent integration `f6b5158` plus acceptance/test documentation; PASS |
| Mbed TLS | `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` | Clean retained SDK submodule, actual crypto |
| lwIP | `77dcd25a72509eb83f72b033d219b1d40cd8eb95` | Clean retained SDK submodule, actual mDNS packet tests |

Pi advanced independently from the handoff's `af4ce31` while execution ran.
No Pi checkout was changed, reset, branched, committed, pushed or messaged by
this work. Its P15.8/P15.9 release status is owned by that separate work; no
historical compatibility pin or expectation was retargeted here.

Each new native probe compiled the exact unchanged Pi product files and its
original interoperability suite with the production Pico core, journal and real
OpenSSL/Mbed TLS Consumer-Radio cryptography. Original fixed vectors and
station/AP/coordinator/management-only cases pass. Additional station/AP cases
prove that native hostname GET/PUT and resource-adapter PUT refuse with 404
before any HTTP exchange. A Pico-owned coordinator rename then invalidates the
old generation; native relogin, existing reads and ordinary configuration saves
preserve the hostname and watermark with zero WTP I/O. This is compatibility,
not new native Pi hostname-editing capability. Authenticated hostname PUTs are
covered separately by the real served-page/session tests. Transport, clock and
board boundaries remain doubles; this is not a physical routing or TLS-LAN
connection qualification.

The guarded Pico-owned [probe](../../tests/hostname_pi_compatibility/CMakeLists.txt)
requires Linux, clean trees and exact 40-character Pi/Pico/Mbed TLS pins. The
identified environment is Debian 13.6/aarch64, GCC 14.2.0, CMake 3.31.6,
OpenSSL 3.5.6, retained image `wsprrypico-p153-env:local`, image ID
`sha256:c7f2a891a6fff72e84bd1f2130b934881565f8b9ab489b20f35071f321ad219a`.
All sources were mounted read-only at their host absolute paths, with a separate
`/out` build mount and `--network none`. Exact trusted mount paths supplied
container-local `safe.directory` values; no user's Git configuration changed.

Inside that environment, run the following for each Pi root/pin in the table
(release `/private/tmp/wsprrypi-p158/release`, accepted
`/private/tmp/wsprrypi-p158/source`, current `/Users/lbussy/GitHub/WsprryPi`):

```sh
pico_root=/Users/lbussy/GitHub/WsprryPico
pico_pin=ecbe2c40fc07aea2f0ea4d8bfc32a4e8770dad5e
cmake -S "$pico_root/tests/hostname_pi_compatibility" -B "/out/$pair" \
  -DPI_SOURCE="$pi_root" -DEXPECTED_PI="$pi_pin" \
  -DPICO_SOURCE="$pico_root" -DEXPECTED_PICO="$pico_pin" \
  -DMBEDTLS_SOURCE=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls
cmake --build "/out/$pair" --parallel 3
"/out/$pair/hostname_pi_compatibility" \
  "$pico_root/docs/protocol/Consumer-Radio-v1-vectors.json"
```

Post-run HEAD and clean-tree checks also passed for each source pair. Native
Pi C++ was compiled only in the identified Linux environment. No Pico Actions
workflow exists; CI was not run or claimed for this source. Pi CI/pin changes
are outside this authorized scope.

Host reproduction, from the Pico root (full Xcode/Apple Clang 21 on macOS):

```sh
source scripts/xcode_env.sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls
cmake --build build-host --parallel 3
ctest --test-dir build-host --output-on-failure
ctest --test-dir build-host --output-on-failure --repeat until-fail:2
python3 scripts/validate_wtp_contract.py
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
node tests/network_browser_tests.js
node tests/hostname_browser_integration.mjs build-host/consumer_bootstrap_driver \
  build/phase15-10-browser
HOSTNAME_BROWSER_NO_CAPTURE=1 node tests/hostname_browser_integration.mjs \
  build-host/consumer_bootstrap_driver build/phase15-10-browser
```

The Mbed TLS sibling lwIP path is inferred and its exact pin/clean state is
checked by CMake. The 204-group enumeration includes `mdns_tests`,
`mdns_lwip_tests`, `network_adapter_tests` and genuine TLS/crypto/bootstrap cases.
Loopback access is required. Shell Node was 26.12.0; CTest selected Python
3.14.8. The affected sanitizer build adds C/C++ and executable link flags
`-fsanitize=address,undefined -fno-omit-frame-pointer` and runs:

```sh
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
ctest --test-dir build/phase15-10-asan --output-on-failure \
  -R 'hostname|consumer_(profile|storage|tls_generator|radio|sessions|recovery)|network_tests|mdns|network_adapter|wspr_(plan|resource)|config_update|reset_storage|bootstrap_http|softap_api'
```

Firmware commands used retained SDK 2.3.1, Arm GNU 15.3.1 and cached pinned
picotool `6f6458d792b93685a11423b244a585eaa99eafcf`; no SDK/tool installation:

```sh
cmake -S . -B build/consumer-lan-pico \
  -DWSPRRY_PICO_FIRMWARE_VERSION=0.1.0-rc.3-p1510-candidate
cmake --build build/consumer-lan-pico \
  --target WsprryPico WsprryPico-StandaloneRF --parallel 3
arm-none-eabi-size build/consumer-lan-pico/firmware/WsprryPico.elf \
  build/consumer-lan-pico/firmware/WsprryPico-StandaloneRF.elf
```

The cache supplied `PICO_SDK_PATH=build/local-sdk-079c6f3`, Release,
`PICO_BOARD=pico2_w`, and the already retained picotool paths. The standard
candidate is RF inhibited; neither candidate was loaded onto a board.

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
Retained failure logs and this record preserve the failed attempts; the repaired
checks above passed. The probe's first strict Linux builds also caught a missing
private client include and public-header precedence collision. Both were fixed
in the Pico-owned harness using the existing Pi build's include requirements;
all three exact source pairs subsequently compiled with warnings as errors.

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

A later diagnostic run completed the fragmented upload but reset a fresh
connection during the twenty immediate raw-RST/reconnect cycles. Its presence
on the unchanged baseline was not established. Independent review approved a
single `NETWORK DRAIN` fixture barrier: normal `mock_tcp_poll` followed by normal
`server.poll`, then an assertion of zero active/pending connections and buffered
bytes, before exactly one HTTP attempt. It retains all twenty actual loopback
zero-linger resets, performs no state clearing or HTTP retry, and changes no
production deadline/code. Coverage is slot reuse **after servicing the reset**,
not guaranteed immediate reconnect before the adapter observes RST. Five TLS
runs and the final full suite passed. The controlled 32,934-byte upload measured
24–25 ms in those five runs. The old failed originals were not reclassified as
passes.

Independent reviewer `/root/hostname_review` inspected the production changes,
R1–R7 repairs, same-iteration admission closure, strict probe guards and bounded
test repairs. Final reassessment found no remaining actionable findings within
the inspected software scope. This execution did not perform the separately
requested originating post-execution assessment or message another chat.

Evidence remains local/ignored: `build/phase15-10-linux/*ecbe2c40*-{configure,build,test}.log`,
`build/phase15-10-browser/*.png`, and `/private/tmp/p1510-*` logs. Principal final
logs are `p1510-final-acceptance-suite.log`, `p1510-tls-barrier-repeat.log`,
`p1510-controlled-full-suite.log`, `p1510-asan-repaired.log`,
`p1510-browser-bootstrap-pinned-final.log`, and `p1510-firmware-334ea5a.log`. The prior
`p1510-final-suite.log` and `p1510-controlled-tls-verbose.log` retain the two
distinct TLS failure sites; baseline/current three-repeat isolate logs retain
their successful comparisons. The baseline source archive required only
`-Wno-error=overlength-strings` to build its already oversized generated literal;
no baseline source was edited. Initial sandbox socket denial, incomplete CLT
linking, unavailable macOS leak detection and degraded Impeccable parsing were
environment limitations; socket/full-Xcode runs and supported sanitizer checks
were repeated as reported. Credentials/captures/generated firmware are not in
Git. An extra final browser refresh first used the session-only driver, which
correctly refused the root page with 403; the corrected
`consumer_bootstrap_driver` invocation passed.

The pre-publication repository audit found Pico clean at `ecbe2c4` before this
record/index/roadmap update. All read-only references were clean: primary Pi
devel and its concurrent step-14 worktree at `a84010d`, accepted companion
`6d5e734`, preserved release `a2437d1`, and WsprryPi-Docs devel at
`ee689f0c7f5bbbb4f961ec81fd1b1cfbf98f9a79`. The final execution reply records the
documentation commit, push outcome, independently checked remote hash and final
working-tree state. No release, tag, PR or other-repository publication is part
of this execution.

## Documentation Impact and P15.14 packet

Updated: this record, browser API, configuration-update, standalone, identity,
mDNS, consumer LAN guidance, development index and current roadmap. Historical
contracts/results retain explicit supersession notes. README, CONTRACT and
architecture were reviewed; their application/carrier/timing authority remains
valid without a schema change. WTP/1, pin assignment, RF qualification and
P15.8/P15.9 release status are considered unchanged.

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
