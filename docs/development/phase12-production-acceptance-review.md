# Phase 12 production integration and partial acceptance review

Status: **OPEN_PARTIAL**. This is not Phase 12 closure.

This review records the earlier production/physical tranche. The subsequent
[BLE local-control continuation](phase12-ble-local-control-review.md) adds
hardware-free production wiring for controller time, Identify/status and an
unchanged WTP/1 GATT stream. Its clean committed image has subsequently passed
load/boot, preservation and final RF-inhibited restoration, but none of the new
BLE operations has iPhone/Bluefy physical acceptance. A later SoftAP
continuation now connects the production AP, blank bootstrap, pre-clock/normal
HTTPS, password/cookie admission, controller time and existing
browser/`JobService` API. A subsequent RF-inhibited native-Pi run partially
accepted the provisioned SoftAP path after three retained target failures and
repairs. It is not iPhone/Safari/Bluefy, blank-device,
provisioning/activation or broad Stage A acceptance. The earlier results are
retained below.

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
- uses a bounded project-owned DHCP service and fixed AP address
  `192.168.4.1/24`, registers the certified `.local` hostname on the AP netif,
  and keeps station and AP service under the one CYW43 owner. The server is
  derived from the MIT MicroPython implementation carried by Raspberry Pi's
  `pico-examples`, is bound to the AP netif and has checked startup;
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

The reviewed implementation was then frozen at clean source commit
`b28400e114abb68566eef2154361e7d541069ff0`. Rebuilding that exact commit
repeated the 87/87 host suite, WTP validator, browser checks, standard Pico 2 W
image and both target linkchecks. The clean linked image is text 1,361,536,
BSS 134,396 bytes, and its UF2 SHA-256 is
`d5c99b97709f547ff8b0533ab60921e069deabccac4414f74e38229e298f253b`.
It was not flashed; these are artifact results, not live-device acceptance.

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

## RF-inhibited SoftAP physical continuation

The continuation began at clean `devel`
`c84fa157b93493cf0c28fa2e96c30e0beeabe7e2`. Source was deliberately not
guarded by a pre-freeze drift sentinel. Four committed candidate revisions were
built and affected physical rows were repeated on Candidate A only. The first
three retained failures were: no DHCP service at `46e21069ac2a`; listener
refusal after DHCP repair at `9bd0d7057128`; and correct controller-time
rejection at `45d0a9215e3a` because separate TLS handshakes made the unchanged
500 ms uncertainty limit impossible. Repairs added the bounded DHCP server,
reserved the one listener for the active surface, and kept only the immediate
time challenge/submit pair on one authenticated TLS connection.

The final exact candidate is clean source
`0ecf9c170384fd2cc3ba802515e1d2c1396ab9fa`, firmware identity
`0ecf9c170384`, and UF2 SHA-256
`6261e322884a280afcd997537d6248fbbf0033b879fab1b2a661acd3a3575e23`.
Serial-targeted picotool load/verify passed. Candidate A preserved profile
generation 0, access generation 3, station/schedule/watermark values and healthy
configuration/watermark journals. The final image passed exact SSID WPA2,
DHCP, AP mDNS, process-local certificate validation, TLS 1.3, wrong-password
and cross-origin rejection, correct-password cookie admission, two accepted
same-connection controller-time exchanges of 277,132,467 ns and 277,595,784 ns,
normal status/capabilities,
`HELLO`/`CLAIM`/`RELEASE`, logout, reconnect and bounded resource return. The
clock reported synchronized with 307,049,485 ns uncertainty. No `LOAD`, `ARM`
or RF operation occurred.

All temporary NetworkManager profiles were removed, the test interface was
disconnected and Candidate A was rebooted. Final boot
`889776ed08c5da0743cfa62b224062ac` again reported the inhibited simulator,
empty/unowned state, inactive output, healthy journals, unsynchronized clock
and disconnected BLE. The AP-stop row remains unmet because the preserved
factory station configuration is unavailable and the selected contract
therefore requires automatic fallback to advertise. A later usable-station run
must prove withdrawal after 30 seconds of station stability; disabling fallback
to manufacture a stop would violate the contract.

The exact credential-free evidence, remaining rows and restoration limitation
are in the [SoftAP review](phase12-softap-physical-review.md) and
[result](phase12-softap-physical-result.json). This accepts a bounded native-Pi
control path only, not iPhone phone time, Safari/Bluefy behavior, credential
provisioning, reset/fault/soak or Stage B.

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

## Phone-assisted continuation preflight

The next acceptance prompt is
[phase12-phone-assisted-acceptance-prompt.md](phase12-phone-assisted-acceptance-prompt.md).
Its first adversarial source pass found that retained-bond `authorize` correctly
restored ordinary local authority but the Bluefy provisioning transaction did
not independently validate a fresh password. Treating that exchange as proof
of fresh-password provisioning would have overstated the earlier physical
evidence.

The repaired path now binds a one-use password proof to the final staged-profile
SHA-256 digest, profile session, apply request, principal and expected/current
generation. The public default also requires the exact device ID to be
confirmed through `ACCESS CONFIRM PROFILE` on USB. Status polling cannot extend
the 30-second manager session; cancel, disconnect, mismatch, timeout and every
terminal apply path invalidate the proof. The Bluefy client clears submitted
password and TLS material on success, transport failure and local validation
failure. These are source and deterministic-test claims only until the recorded
iPhone and Candidate A exercise completes.

## Phone-assisted BLE interoperability continuation

Candidate A remains the exact Pico 2 W with USB serial `0BF4B4AEC9FFB344`,
device ID `fd6127d11d6aca42a9905fa3fb1bf1d5`, station MAC
`88:a2:9e:0a:60:df` and public BLE address `88:A2:9E:0A:60:E0`. The clean
RF-inhibited image has firmware identity `31d1603ee834`, UF2 SHA-256
`958ebd765ac4d346da6485c25d66d9e19c8fae2c6904394a8452afd97e494fbe`
and boot ID `5b2e36e4eed555e5dc0f3b363d003817`. Candidate B was not changed.

The operator recorded an iPhone 17 Pro Max running iOS 27.0 and Bluefy 3.9.3.
Online release `91eead11ffac...` established retained-bond authorization but
also exposed that the page incorrectly required an entered password. Release
`6963416017f0...` repaired that mismatch: an empty application credential now
asks the target to resume authority only for an already-authorized retained
bond, while a new or provisional bond still fails closed. Release
`2a7d2563c0b1...` replaced the misleading separate password-visibility button
with a bounded inline eye control that disappears with the empty field. The
operator confirmed authorization without re-entering the password and the
absence of the eye control when no password was present. Authenticated phone
time and the Identify/SoftAP-ready LED observations also completed, but those
rows do not establish BLE WTP interoperability.

The subsequent single `Read WTP status` attempt failed in Bluefy with
`operation_failed` and disconnected. The preserved before/after diagnostics
showed connection/disconnection counts moving from 9/8 to 9/9 and two accepted
CCCD writes, with zero CCCD rejections, but no WTP write segment, WTP byte or
WTP indication. Candidate A remained RF-inhibited, empty and output inactive.
This localizes the observed failure before any WTP/1 `HELLO`; it is not evidence
of a WTP parser or `JobService` rejection.

The page-only repair no longer stops one indication characteristic and starts
the other within the same Bluefy GATT connection. A field/WTP channel change
now intentionally disconnects, waits a bounded interval, reconnects the same
previously selected `BluetoothDevice` without another chooser, re-reads and
verifies the full device ID, and subscribes to only the requested indication
characteristic. Returning to field control repeats empty authorization on the
retained bond to establish a fresh field-session identifier. Any reconnect,
identity, subscription or reauthorization failure clears the client and leaves
it disconnected. Host regressions cover one chooser request, exact identity
revalidation, lack of any `stopNotifications()` dependency, one active channel,
field-session renewal and fail-closed subscription failure. The deterministic
candidate page release is
`2c1c0ac2a326ab4c20393a4a6f7dda50751547c4075554d7ba4c0662e28e3b87`.
The first adversarial pass found that a failed reconnect cleared the client
correctly but could leave the page's main Connect control disabled. The page
now clears the stale selection, disables authenticated controls, re-enables the
release-gated chooser and explicitly tells the operator to select the Pico
again. The repaired client also clears stale WTP event state and rejects a link
lost during subscription setup. Focused regressions cover both repairs. A
second adversarial assessment found no further actionable issue in this
page-only boundary.

The operator then repeated the bounded attempt on that exact
`2c1c0ac2a326...` release. Before selection the target reported 9 connections
and 9 disconnections, 29 accepted CCCD writes and no WTP traffic. Selection
advanced connections to 10 without a disconnect and added two accepted CCCD
writes; both CCCD values read 2 because iOS restored the retained bond's prior
subscriptions. Blank retained-bond authorization succeeded. `Read WTP status`
then displayed `Reading WTP status failed: operation_failed. Select the Pico
again.` The final counters showed 11 connections, 11 disconnections and 34
accepted CCCD writes, but still zero WTP segments, bytes or indications and no
CCCD rejection or queue failure. The final disconnect reason was 19. The
RF-inhibited simulator remained empty and output inactive. This preserves a
second failure before WTP/1 `HELLO`: the reconnect reached the target, but
Bluefy still failed while activating the dedicated WTP indication.

The next repair removes that second notification-context dependency. An exact,
authenticated `select_wtp_status_carrier` field command now selects the
already-active field-status indication as the WTP output carrier for only the
current BLE connection. It requires the current device, retained-bond
principal and field session, rejects extra fields, is cleared by authorization,
disconnect or security loss, and disconnects the logical WTP endpoint when the
carrier changes so no byte stream can span carriers. Provisioning replies keep
priority on the same handle; after the selection reply is confirmed, Bluefy
changes only its local parser and sends an ordinary unchanged WTP/1 `HELLO` on
the existing WTP command characteristic. It makes no reconnect, no
`stopNotifications()` call and no WTP-status `startNotifications()` call.
Returning to field control still uses a deliberate reconnect and blank
retained-bond authorization. The native Raspberry Pi/BlueZ client never sends
the browser-specific selector and continues to use the dedicated WTP status
characteristic.

Focused browser regressions prove one connection, one status subscription,
zero WTP-status subscription attempts, exact authenticated carrier selection,
unchanged WTP framing, return-to-field session renewal and fail-closed carrier,
HELLO and CRC failures. C++ tests cover unauthenticated, wrong-session,
extra-field, accepted and disconnect-cleared selector states; the synchronized
wire-contract test covers carrier-aware CCCD gating and indication routing.
The deterministic candidate page release is
`4601c8a180676ff051db0839540c186ec558a25396c80712d80f04d9cd8de5a9`.
These are source/host results until the repaired firmware is flashed and the
operator's single bounded WTP status retry produces real WTP request and
indication bytes.

The first adversarial review of this repair found two fail-closed gaps. A
direct caller of the browser's channel-selection method could bypass the outer
HELLO cleanup wrapper, and a target carrier change whose reply could not be
queued could remain selected until the asynchronous link disconnect. Carrier
selection now owns its browser disconnect-on-failure behavior, while the target
immediately revokes the application session and requests link disconnect if a
changed-carrier reply cannot be queued. Focused host and sanitizer regressions,
the full 87-test host suite, WTP validator, four target links and five linked-
image checks passed after the repairs. A second adversarial assessment found no
further actionable issue within this RF-inhibited BLE transport boundary.

The subsequent physical retry used the published
`4601c8a180676ff051db0839540c186ec558a25396c80712d80f04d9cd8de5a9`
page and exact RF-inhibited firmware `47e8e39d5b49` on Candidate A. The USB
baseline was zero. Blank retained-bond authorization succeeded with one
connection, no disconnection or error, three accepted CCCD writes, both CCCDs
reading 2 and no WTP traffic. The single `Read WTP status` attempt again
displayed `operation_failed` and disconnected. The preserved post-failure
counters showed one completed carrier-selection command and delivered reply,
one disconnection with reason 19, zero queue or CCCD failures, and still zero
WTP write or indication bytes. The simulator remained RF-inhibited, empty and
output inactive. This localizes the remaining failure to the browser transition
after the selector reply and before the dedicated WTP-command write reached the
target; it does not indict WTP parsing or the shared `JobService`.

The follow-up repair removes both remaining browser context changes. One stable
event listener now dispatches field-framed or WTP-framed bytes according to the
authenticated connection mode, and the selector reply binds raw WTP input to
the already-proven field-command characteristic as well as WTP output to the
field-status indication. The target accepts raw WTP on that field command only
while the authenticated connection-scoped selector is active; reconnect,
reauthorization or security loss restores field framing. The dedicated WTP
command/status path and Raspberry Pi/BlueZ client remain unchanged. Browser
regressions make listener replacement throw if attempted, require both carrier
bindings, and prove HELLO/STATUS use no dedicated WTP write. The new
deterministic page release is
`35bd0b872dd19ff50f9d467a1437729c77d384917dae7982639ef4ca6b8d1778`.
This is source/host evidence pending a new exact-firmware flash and one bounded
physical retry.

The first adversarial pass over this follow-up found that the target selected
field-command input without rejecting the dedicated WTP-command input on that
same connection. Although the browser uses only one, a malicious or defective
client could interleave both into one endpoint stream. The repaired dispatch
now admits exactly one command characteristic: dedicated before selection,
field after selection. A second adversarial assessment found no further
actionable issue in this bounded transition.

Candidate A was then serial-targeted with exact RF-inhibited firmware
`4377d2ded8e3` (UF2 SHA-256
`048c3feef2536b7e17c74edc153d4f25a4fa1980e4910566d7d7aaba677ef22a`).
Postflight preserved access generation 3, profile generation 0, station
`AA0NT/EM18/20`, the 120/0 schedule, watermark
`1789607761000000000`, configuration/watermark journal sequences 72/12 and
reported boot ID `331e555683a5d6c6122735a07883e0a8`, healthy storage,
`empty` and `output_active:false`. The published page exactly matched release
`35bd0b872dd19ff50f9d467a1437729c77d384917dae7982639ef4ca6b8d1778`.
Blank retained-bond authorization again succeeded. Before WTP selection the
target showed one connection, no disconnection, one completed command/reply,
two completed indication fragments and zero WTP traffic. The single WTP status
attempt again displayed `operation_failed` and disconnected. Preserved final
counters showed two completed commands/replies, five completed indication
fragments, no queue/CCCD/indication errors, disconnect reason 19 and still zero
WTP write or indication bytes. Runtime remained RF-inhibited, empty and output
inactive. This proves the selector response completed but the browser again
failed before the target accepted a first raw WTP segment.

The next page-only repair addresses the remaining data-shape difference between
the proven field writes and the failing raw WTP write. Field fragments were
independently allocated 64-byte arrays, while WTP fragments were
`Uint8Array.subarray()` views whose backing buffer still held the complete WTP
frame. Although valid `BufferSource` values in the web contract, that ownership
shape crosses Bluefy's native Core Bluetooth bridge and was not represented by
the prior mocks. WTP transmission now copies each bounded fragment into a
compact, independently owned array, waits for the acknowledged write and
scrubs that array. Safe diagnostics report requested/completed WTP write counts
if the bridge still refuses an operation. A regression now requires every
submitted buffer to start at offset zero and have a backing-buffer length equal
to its submitted byte length; it fails against the previous `subarray()` path.
The deterministic candidate page release is
`e1e6caa574a0e5c75cfd8c0a168c3ec8c2b896322ec7a7acc20d555f357f0625`.
This repair is source/host evidence pending one bounded physical retry; it does
not yet prove that buffer ownership was Bluefy's root cause.

The adversarial reassessment checked compact-buffer ownership, 64-byte bounds,
ordered acknowledged writes, post-write scrubbing, pending-request cleanup,
diagnostic secrecy, deterministic release generation and the unchanged
firmware/RF boundary. The focused four-test release/contract set passed. The
95-test host suite passed except for the loopback TLS fixture while sandboxed;
that fixture passed separately with its local socket permitted. The three
initial bare-compiler failures also passed with the pinned Xcode 26.5 SDK. No
further actionable issue was found in this page-only repair.

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
- iPhone controller-time and visual Identify/ready-LED behavior;
- blank generic HTTP, Safari/Bluefy certificate behavior, cookie lifetime and
  stable-station AP withdrawal; the bounded native-Pi provisioned SoftAP path
  is accepted only as recorded above;
- any SoftAP credential-provisioning/activation surface, which is not exposed by
  the current browser integration;
- BLE ordinary WTP/browser local management through the one `JobService`;
- password/bond/reset recovery and safe accepted physical controls;
- fault-injection, replacement/superseded-trust, broader resource reclamation,
  concurrency and bounded soak rows;
- final RF-inhibited/output-off/restoration evidence after any later physical
  mutation; this tranche ended RF-inhibited with the exact fallback limitation
  recorded above.

Stage B and all RF output remain separate and unauthorized.
