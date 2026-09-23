# Phase 12 production integration and partial acceptance review

Status: **OPEN_PARTIAL**. This is not Phase 12 closure.

This review records the earlier production/physical tranche. The subsequent
[BLE local-control continuation](phase12-ble-local-control-review.md) adds
hardware-free production wiring for controller time, Identify/status and an
unchanged WTP/1 GATT stream. Its clean committed image has subsequently passed
load/boot, preservation and final RF-inhibited restoration, but none of the new
BLE operations has iPhone/Bluefy physical acceptance. A later hardware-free
SoftAP continuation now connects the production AP, blank bootstrap,
pre-clock/normal HTTPS, password/cookie admission, controller time and existing
browser/`JobService` API. That continuation was not flashed and has no physical
acceptance. The earlier results are retained below.

## Authority and evidence boundary

The tranche started from clean `devel` at
`7451a4047677cf2f91d790ea5aa9eec1a9015f38`, equal to the upstream and local
`origin/devel` references. The operator authorized the named production
integration, finite physical work on the two Picos attached to `wspr5`, a
review/repair/reassessment cycle, commit/push, and later GitHub Pages publication
from `devel:/docs`. No RF output, Stage B, host reconfiguration, trust-store
mutation, dependency download or private credential publication was authorized.

This record separates source/test evidence, the operated dirty candidate, and
unexecuted physical assertions. A linked image is not live-device evidence, BLE
advertising is not Bluefy interoperability, and a checked-in service worker is
not proof that iOS retained a usable offline cache.

## Source orientation

Before editing, the production image already had one `JobService`, scheduler,
portable provisioning manager/profile journal, delivery-safe coordinator,
access/reset journal, controller-time arbiter, fixed GATT framing, candidate Pico
GATT/SoftAP/LED adapters, station/TLS server and strict browser/WTP semantics.
The adapters cross-linked but production did not start GATT or own a live Pico
activation platform.

The retained dependency boundary is:

- Pico SDK 2.3.1 at `079c6f39023649b154152db30f1d781e884879bc`;
- clean BTstack at `eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`;
- Arm GNU Toolchain 15.3.Rel1, CMake 4.4.3 and Ninja 1.13.2;
- RP2350 Arm-S / Pico 2 W standard RF-inhibited image;
- application end `0x103f3000`, leaving access, BTstack, profile,
  standalone and E10 storage unchanged.

The pinned SDK requires CYW43 to be brought up once before its checked OTP station
MAC is populated. It does not provide an accepted RP2350 application-visible
BOOTSEL-at-boot gesture: a held BOOTSEL selects ROM mass-storage boot instead of
starting the application.

## Implemented production boundary

- `PicoNetwork` now separates one-time CYW43/radio identity initialization from
  station-profile startup. It briefly enables the station netif only for the
  checked MAC read, disables it again, and keeps one CYW43 owner for station,
  BTstack and LED service.
- The RF-inhibited standard image constructs the healthy access controller,
  provisioning manager, strict BLE command session, credential validator,
  network-only `PicoActivationPlatform`, GATT transport and indicator.
- The activation platform can close/restart only network admission. Its type has
  no abort, release or RF-owner capability. Admission closes immediately after
  profile commit; the final applying BLE indication is preserved before the
  core-0 release path runs.
- GATT requires encryption, stored peer identity and application authorization,
  admits one connection, uses fixed bounded framing, retains asynchronous
  advertisement buffers, and cleans provisional bonds on terminal paths.
  Returning authorized bonds accept the page's repeated authorize operation
  idempotently because the retained bond is already the selected principal.
- USB-local `ACCESS STATUS`, `ACCESS ADOPT <full-device-id>`,
  `ACCESS ENROLL <full-device-id>` and `IDENTIFY <full-device-id>` provide
  exact device-bound confirmation/diagnostics. They preserve idle/output checks.
- `docs/bluefy` is a deterministic release built from
  `src/provisioning/web`. The page asks Bluefy for a service-filtered system
  chooser, reads and displays the full device ID, and requires a separate
  confirmation click. It has no remote script, analytics, credential service,
  candidate identity or persistent credential storage.
- The release ID covers the raw index, application, client, manifest, stylesheet
  and service-worker templates. SHA-384 protects loaded script/style references;
  the page verifies the SHA-256 inventory before enabling selection. A
  release-keyed service worker installs a complete cache and does not mutate the
  prior cache during online navigation. This protects against corruption and
  mixed releases, not a total compromise of the trusted Pages origin.

Not implemented by this tranche: production SoftAP DHCP/mDNS/HTTP/HTTPS,
SoftAP password/browser service, BLE WTP/job management, authenticated phone
time, profile activation on the physical candidate, password/reset administration
surfaces, and an accepted physical gesture. `PicoSoftAp`, portable SoftAP
admission/time/reset logic and their tests remain source primitives only.
The hardware-free SoftAP continuation below supersedes only that source-wiring
gap; it does not rewrite this tranche's physical evidence.

## Deterministic validation

The final prepublication source assessment produced:

| Check | Result |
| --- | --- |
| Host build plus CTest excluding four separated records | 79/79 passed |
| Focused ASan/UBSan provisioning/access/web/contract/release | 5/5 passed |
| WTP/1 validator | 23 schema, 7 raw JSON, 1 framing and 8 transition cases passed |
| Pico 2 W standard plus field/provisioning linkchecks | passed |
| Image/layout/heap-hook/stack-guard checks | passed |
| Standard image size | text 1,303,984; BSS 132,760 bytes |
| Working-tree UF2 SHA-256 | `708e33c88b273ba3e2ea0a26229d4b695485b5566c9026dc4fa16cbad7e65b27` |
| Bluefy release | `51fe7c97ebe3a7a710cda89f5370923bd942f1443df17549054903c69025e56f` |
| `git diff --check` and JavaScript syntax checks | passed |

The four separated CTest results were preserved rather than hidden:

- `phase11_7_closure_tests` rejected later production-runtime drift at the time
  of this review. That behavior was subsequently identified during the active
  Phase 12 continuation as an invalid repository freeze: the audit must protect
  the fixed Phase 11 candidate-to-tested interval and retained artifacts, not
  reject authorized later-phase source evolution.
- `cyw43_tx_overlay_tests`, `network_certificate_tests`, and one compiled
  subcase inside `phase11_5_r3_tests` are blocked by the host Command Line Tools
  macOS 27 `.tbd` files containing unsupported `arm64e.x1` architecture
  entries. The broad host build, 79 unaffected tests, sanitizer checks and the
  Arm cross-build pass; this host-toolchain failure is not converted into a
  product pass.

## Partial physical evidence

Candidate A:

- Pico 2 W USB serial `0BF4B4AEC9FFB344`;
- device ID `fd6127d11d6aca42a9905fa3fb1bf1d5`;
- station MAC `88:a2:9e:0a:60:df`, suffix `0a60df`;
- public BLE controller address observed as `88:A2:9E:0A:60:E0`;
- operated source `7451a4047677-dirty`;
- operated repaired-advertisement UF2 SHA-256
  `8ea4121ebf81cccb1cdaeaae61243f092d4e0acbe1fe89f4d24c7acb8232767b`.

Before the flash, Candidate A reported the prior `0e85ff90571c` runtime,
empty/unowned/output inactive, station `AA0NT/EM18/20`, a 120-second schedule
and watermark `1789607761000000000`. After the RF-inhibited standard flash and
USB-local adoption it reported:

- engine `inhibited-standalone-simulator`;
- empty/unowned, `output_active=false`, unsynchronized;
- healthy access generation 1, public default active, enrollment closed;
- BLE running;
- station, schedule and watermark values preserved.

The first physical BLE scan failed because the advertisement payload had
temporary storage lifetime. After repair and reflash, a bounded `wspr5` scan
observed the selected service and name `WsprryPico-0a60df`. The failed attempt
is retained in this review.

Candidate B, USB serial `CDDBF8767C506C07`, was identified as the comparator
and left on its existing image without mutation.

The original candidate record above is retained as historical evidence.
Subsequent clean `devel` commits `16d8f0e`, `7ce154d` and `2a4e0e8`
integrated the BLE path, made the verified online Bluefy page usable when
Bluefy lacks a service worker, and queued ATT indications outside the write
callback. The published page release is
`909e78e8e64a3d274aa8b11886a4fdfb8964a854eccbd6629075388bb33d8e85`.
An iPhone selected Candidate A and completed first authorization: subsequent
USB-local status showed healthy access generation 2 and enrollment closed.
This proves the initial application authorization persisted. On a later
retained-bond authorization, Bluefy displayed "Authorizing" and timed out.
The unchanged access generation does not establish whether that retry reached
the Pico. The return-status path remains under investigation.

On September 22, a bounded diagnostic image from `2a4e0e83c52c-dirty`
was flashed to Candidate A only. Its UF2 SHA-256 was
`8901d844c04ba035ace02840083dce9193c7732d445dff0ac0d94b53a756b940`;
the retained picotool SHA-256 was
`4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`.
The flash verified, and the new boot ID was
`6000b7be75afa1192da394319108fe34`. USB-local postflight confirmed
`inhibited-standalone-simulator`, empty job state, inactive output, healthy
access generation 2, BLE running, station `AA0NT/EM18/20`, the 120-second
schedule and watermark `1789607761000000000` preserved. The new read-only
`BLE STATUS` command reported zero baseline events. It exposes bounded counts
for received command frames, queued responses, send callbacks, indications
started/completed and disconnections without recording credentials. On the
operator's next retained-bond retry, Bluefy again displayed "Authorizing",
timed out and showed a crossed-out Bluetooth symbol. Candidate A reported one
connection and disconnection, four command frames, one completed command, one
queued response, two successful indication starts and two indication
completions, one delivered response and no queue failure. The stack confirmed
both indications, but this does not prove delivery to page JavaScript. Access
remained healthy at generation 2. The page receive path is therefore the next
gate; no Wi-Fi profile was submitted. A subsequent page-only release adds
bounded, secret-free write/event/frame/response counters to distinguish
missing JavaScript events from malformed or unmatched responses. Release
`23ab8f69dcf3ab28186022ce818e280faa98a78b80c0e32e2552323e24f115de`
was verified on the public Pages origin by manifest and JavaScript hashes.
That retry timed out with `writes 4/4; events 0; frames 0; messages 0;
matched 0; last none`. USB-local counters advanced from one to two complete
commands, from two to four confirmed indications and from one to two confirmed
response sets, with zero queue failures and access generation still 2.
Consequently, the Pico processed the command but Bluefy dispatched no status
event to the page.

Pinned BTstack inspection found the status CCCD at ATT handle `0x0010` is
dynamic. The prior production write callback accepted only the command value
handle, so it would reject a subscription write; pinned BTstack can nevertheless
send indications without checking CCCD state and record link-level
confirmations. No Bluefy CCCD write was captured before the repair, so this
source-confirmed defect is consistent with, but not yet proven to be the sole
cause of, the zero-event timeout. A narrow adapter repair now accepts and reads only valid per-connection CCCD
values (disabled or indications enabled), resets subscription on disconnect,
and refuses command dispatch before any provisioning mutation when unsubscribed.
The adversarial pass caught and repaired the initial mutation-before-queue
ordering. Source-contract and five focused host regressions passed; the
RF-inhibited standard image and field-access linkcheck cross-built with pinned
SDK 2.3.1 and BTstack, and the image/layout check passed.

Candidate A alone was flashed with UF2 SHA-256
`9b4f2925f4294beb2cf674988d4e30752db8a3d138cba47ad045c6f7ef77fcbc`,
built from `2bb0ef93aef5-dirty`. Picotool verified the load. Postflight boot ID
was `a4083142c199d0bb3cfabfd69cedb90b`; the RF-inhibited simulator,
empty/unowned job, inactive output, healthy access generation 2, BLE running,
station `AA0NT/EM18/20`, 120-second schedule and watermark
`1789607761000000000` were preserved. CCCD and BLE counters started at zero.
On the same verified online Bluefy release, the operator's next retry
displayed `Authorized` for the explicitly selected full device ID and profile
generation 0. USB-local postflight on that boot showed one connection, two
accepted CCCD callback writes, CCCD value 2, zero CCCD rejections, four
command frames, one completed command, one queued and confirmed two-frame
response, zero queue failures, and an admitted live link. Access remained
healthy at generation 2; the factory Wi-Fi/TLS profile remained at generation
0. The RF-inhibited simulator, empty job, inactive output, station, schedule and
watermark remained unchanged. This passes the observed online retained-bond
application-authorization exchange after the CCCD repair. The adapter accepts
a repeated authorize operation idempotently for an already authenticated bond,
so this retry does not independently prove a fresh password check. Exact
iPhone/iOS/Bluefy versions, offline delivery, credential transfer, profile activation,
ordinary local management and a clean committed-image reflash were still
unaccepted in that tranche; no Wi-Fi profile was submitted.

## Clean committed-image continuation

The BLE local-control source was first committed and reflashed at `fff9e0e41528`.
A later adversarial pass found that an HCI encryption-loss event did not revoke
the application session and queued output until the asynchronous disconnect
callback. Commit `5afe7576f0016ef3e927090c15232ac5c8daeb4f` closes the
session, WTP endpoint, subscriptions and queued indications immediately, then
requests link disconnect. Its standard RF-inhibited firmware identity is
`5afe7576f001`; the final UF2 SHA-256 is
`112f798233e12f2e9b7b049412ab428346b9fb1fc734915e823d1cb84feb7c12`.
Candidate A alone was loaded by exact USB serial with picotool verification
completing `OK`; the initial clean reflash remains retained evidence rather than
being rewritten.

The final postflight boot ID was `e7e8854f51789fb1aef53281c817d588`.
Device identity and station MAC were unchanged. Access generation 2, factory
profile generation 0, station `AA0NT/EM18/20`, the 120/0 schedule, watermark
`1789607761000000000`, configuration journal sequence 72 and watermark journal
sequence 12 were preserved. The candidate again reported the RF-inhibited
simulator, healthy storage, `empty`, unowned and `output_active=false`; BLE was
running and disconnected, and all new WTP counters were zero.

This closes only the clean committed-image reflash, exact boot identity,
preservation and final RF-inhibited restoration baseline. No phone was
available to identify iPhone/iOS/Bluefy or exercise offline reuse, a fresh
password, provisioning/activation, controller time, Identify or BLE WTP. Those
rows remain `NOT_EXECUTED`, and the earlier retained-bond exchange is not
rebound to the clean source.

Offline reload, profile transfer, activation, controller-time observation,
SoftAP, LED-pattern measurement, password replacement, reset, fault injection
and soak remain unaccepted.

## Hardware-free production SoftAP continuation

This continuation started from clean `devel` at
`ae21bc7b9dd772b0b37cf52b288a2544e848ea9f`, equal to `origin/devel`. Source
was allowed to evolve through implementation and adversarial repair; no
pre-freeze drift sentinel was added.

The standard RF-inhibited image now:

- runs the selected WPA2-AES SoftAP causes through `SoftApCoordinator` and
  `PicoSoftAp`, using the station-MAC-derived SSID and current local-access
  password;
- uses the pinned CYW43 DHCP service and fixed AP address
  `192.168.4.1/24`, registers the certified `.local` hostname on the AP netif,
  and keeps station and AP service under the one CYW43 owner;
- exposes plaintext port 80 only on the AP interface and only for blank,
  read-only identity/recovery information; it accepts no password, controller
  time, provisioning or job mutation;
- starts the existing TLS listener before device UTC is available, while still
  validating its device binding, chain, key pair, SAN, purpose and accepted
  algorithms. Only certificate future/expiry flags are deferred at server boot;
  the phone validates server time. Station TLS remains clock-gated and mTLS;
  AP HTTPS is server-authenticated and rejects raw WTP ALPN;
- provides strict same-origin password login, Secure/HttpOnly/SameSite cookies,
  authenticated controller-time challenge/submit and the existing browser API
  against the one `JobService`. A cookie binds to one exact WTP session only
  after successful `HELLO`; absolute owner grace remains STATUS/ABORT/time-only;
  and
- drives the LED's SoftAP-ready state from an actually usable blank HTTP or
  provisioned HTTPS surface. Parsed request storage and response cookie/header
  copies are scrubbed on teardown.

The browser page discovers the local surface, keeps the cookie inaccessible to
script, clears the entered password, supplies bounded phone time on a pre-clock
surface and then reuses its existing status/config/job UI. A failed phone-time
submission is reported separately from login failure.

This slice does **not** expose credential provisioning through SoftAP, implement
password/bond/reset administration or select a new physical reset gesture.
Access-journal recovery remains fail closed. It also does not prove AP startup,
DHCP, mDNS, Safari certificate behavior, cookie expiry, phone time, LED timing,
coexistence or resource margins on a Pico 2 W.

Pre-freeze deterministic validation produced:

| Check | Result |
| --- | --- |
| Host debug build and aggregate CTest | 87/87 passed |
| Focused ASan/UBSan network, field-access and SoftAP API tests | 3/3 passed |
| WTP/1 validator | 23 schema, 7 raw JSON, 1 framing and 8 transition cases passed |
| Browser JavaScript syntax and behavioral test | passed |
| Pico 2 W standard image plus field/provisioning linkchecks | passed with pinned SDK 2.3.1 and BTstack |
| Linked standard image | text 1,361,328; BSS 134,396 bytes; image/layout, heap-hook and stack-guard post-link checks passed |
| Formatting/whitespace | changed C/C++ lines and new files clang-formatted; `git diff --check` passed |

The aggregate run explicitly selected the retained Xcode 26.5 SDK. The default
Command Line Tools SDK still has the previously documented malformed
`arm64e.x1` text-stub problem; no failing product test was hidden or converted
to a pass.

The first adversarial pass found and repaired:

1. AP surface selection was used before it was computed in the production
   loop.
2. A cookie could bind on first API use instead of only after a successful WTP
   `HELLO`.
3. capacity reclamation, owner-only grace and logout initially depended on a
   caller-supplied owner/session value rather than the `JobService`'s exact
   active owner session.
4. `CLAIM`, `RENEW` and `RELEASE` were initially classified as STATUS and would
   have been too permissive during owner-only grace.
5. a stale controller-time challenge could hold the single slot forever after
   a lost response.
6. repeated AP mDNS initialization could make AP name registration fail after
   station mDNS had already initialized.
7. parsed password/cookie copies survived ordinary string/buffer destruction,
   and the browser conflated phone-time rejection with login failure.
8. a page reload generated a new WTP session ID but had no authoritative way to
   recover the cookie's existing mapped session. Authenticated local status now
   returns that nonsecret mapping without rebinding it, and the page reattaches
   before making API requests.
9. an acknowledged controller-time challenge abandoned by the browser left its
   response-delivery bookkeeping slot occupied after the arbiter reaped the
   challenge. Repeated abandoned challenges could exhaust both bounded slots;
   each newly accepted challenge now retires the necessarily stale bookkeeping,
   with a three-cycle expiry/reuse regression.

The repaired paths have focused regressions. The second assessment found items
3 and 8; the third found item 9. After that repair, a fresh fourth source/diff
assessment found no further actionable issue in the hardware-free SoftAP
boundary. It did not convert the unexecuted target rows into passes.

## Adversarial findings and repairs

1. **Double CYW43 ownership risk.** The candidate GATT path could initialize and
   deinitialize BTstack independently of station ownership. Production now has
   one `PicoNetwork` CYW43 lifetime and GATT refuses to start without it.
2. **Wrong callback context for activation.** ATT completion could directly run
   disruptive activation inside the BTstack callback. Completion now records a
   flag and core-0 polling performs release exactly once.
3. **Asynchronous advertisement lifetime.** BTstack retained pointers to local
   arrays, producing an empty live advertisement. The buffers now live in
   `PicoGattTransport`; physical rescanning passed.
4. **Returning-bond page mismatch.** A retained bond was already authorized, but
   a repeated page authorize command could be rejected because it was not a new
   provisional pairing. The command is now idempotent for an already authorized
   encrypted retained bond; a regression covers it.
5. **Stale/non-atomic offline release.** Index-only or service-worker-only edits
   did not necessarily change the cache generation, and an online navigation
   could overwrite the prior cache before the new release completed. Every raw
   source asset now contributes to the release ID and navigation never mutates
   the old release cache. Deterministic tests enforce both properties.
6. **Impossible boot gesture premise.** The requested BOOTSEL-at-boot application
   gestures cannot execute on the selected board because ROM intercepts the
   hold. The plan now states USB-local confirmation is the only implemented
   route and leaves any new hardware/runtime gesture as a fresh design gate.
7. **Future SoftAP terminal-response risk.** `set_admission(false)` closes TCP
   connections. That is correct for the current applying BLE transport, but a
   future SoftAP provisioning adapter must preserve its bounded terminal reply
   separately before reusing the activation platform. This is an open design
   gate, not a claim that SoftAP activation works.

A second diff/source/test assessment found no further actionable issue within
the implemented BLE-only production boundary. It confirmed that unsupported
SoftAP/WTP/time/reset work remains explicitly unclaimed.

## Phase 11 applicability

Phase 11 closure artifacts remain immutable. The shared TLS/browser/WTP,
identity/trust, concurrent-management, image-layout, heap/stack, storage and
network-loss assertions are affected and were rerun where hardware-free. The
new live radio and memory composition requires new Phase 12 inhibited
coexistence/resource evidence. Nothing here rebinds Phase 11.4 physical or
11.5/11.6 RF evidence, expands its 138 MHz/divider-1 boundary, or constitutes
Phase 13 release qualification.

## Remaining gates

Phase 12 remains open for:

- exact iPhone model, iOS and Bluefy version and live chooser/pairing evidence;
- online install followed by verified no-Wi-Fi/no-cellular offline page reuse;
- full provisioning/activation lifecycle on the clean committed candidate;
- controller-time and Identify physical behavior;
- physical SoftAP DHCP/mDNS, blank HTTP, pre-clock/normal HTTPS, Safari
  certificate behavior, controller time and independent field-control path;
- any SoftAP credential-provisioning/activation surface, which is not exposed by
  the current browser integration;
- BLE ordinary WTP/browser local management through the one `JobService`;
- password/bond/reset recovery and safe accepted physical controls;
- fault-injection, replacement/superseded-trust, resource reclamation,
  concurrency and bounded soak rows;
- final RF-inhibited/output-off/restoration evidence after any later physical
  mutation; the current tranche ended restored.

Stage B and all RF output remain separate and unauthorized.
