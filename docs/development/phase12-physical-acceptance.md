# Phase 12 finite physical acceptance plan

Status: **OPEN_PARTIAL**. Stage A has been partially executed under separate
live operator authority. Candidate identity/adoption, RF-inhibited boot,
preserved operational state and BLE advertising passed on the exact device
below. The phone-assisted continuation records an iPhone 17 Pro Max, iOS 27.0
and Bluefy 3.9.3. Retained-bond authorization, one authenticated phone-time
exchange, Identify LED and field-status observation, and Bluefy WTP `HELLO`
plus read-only `STATUS` passed within their recorded limits. The final Bluefy
WTP combination used exact RF-inhibited firmware `4377d2ded8e3`, boot
`331e555683a5d6c6122735a07883e0a8` and release
`e1e6caa574a0e5c75cfd8c0a168c3ec8c2b896322ec7a7acc20d555f357f0625`,
then ended disconnected, empty, unowned and output inactive with healthy
journals.

Offline-cache reuse, fresh-password/new-pairing behavior, complete profile
provisioning/activation, arbitrary BLE job control, the broader phone-time and
LED matrices, the remaining SoftAP matrix, reset/gesture, trust/fault/resource
and soak acceptance remain open. A bounded native-Pi BLE exercise separately
passed device identity, controller time, field status and WTP
`HELLO`/`STATUS`; a later native-Pi run passed the bounded provisioned SoftAP
association/DHCP/mDNS/HTTPS/time/status/ownership/reconnect path. Stage B is
not authorized. The Field-GATT/1 source contract is now frozen and conforming
across firmware, Bluefy and the native-Pi client; that result does not replace
the open physical profile-activation and failure-cleanup rows in this plan.

## Purpose and evidence boundary

This procedure qualifies Phase 12 transport and credential behavior only after
the portable implementation, Pico adapters, the selected
[field-access/security policy](phase12-field-access-contract.md) and exact
candidate image have passed hardware-free review. It begins with RF-inhibited firmware.
It does not reopen or silently extend Phase 11.6, and it cannot establish Phase
13 timing, spectrum, band/mode/clock or release qualification.

## Current consumer portal and recovery continuation (2026-09-30)

The Wi-Fi-first consumer decision and P12.9 closure supersede the consumer
BLE/password/retained-owner rows below. Those rows remain historical engineering
acceptance. Use this section for the resumed consumer work. Phase 12 remains
**OPEN_PARTIAL**.

The [GP14 integrated closeout](phase12-gp14-integrated-acceptance.md) closes the
bounded diagnostic and opt-in RF-inhibited runtime scope: reset, shutdown
requests, long-held AP availability, release lease expiry, DMA renewal,
recovery and settings preservation. The captured real gesture overlapped the
extended flash-safe pause; exact coincidence with the shorter erase/program
operation is not established. Production GP14 work is parked: RF target
dependencies/stack checks, active/armed cutoff including busy core 0, then
default enablement after review and exact target acceptance. Do not repeat
the accepted inhibited hold/renewal campaign as a portal prerequisite.

### Source admission findings

The reviewed source baseline was clean `devel` at `9f48277` before this roadmap
reconciliation and readback change. `PicoBootstrapServer` accepts a separate
station transaction only after a same-device network-only or consumer profile
exists. Its encrypted
request omits Wi-Fi credentials; the device obtains them from the current
journal, then trials the station before creating or reusing the device TLS
identity and committing exactly the next generation. The browser verifies
generation plus request digest before saying station settings were saved.
Fresh browser keys are transient, and the new profile stores no phone owner.

The existing browser test exercises a lost submit reply, exact committed
readback, a fresh second-phone transaction, retained success and polling
timeout recovery. The portable commit tests cover source/device mismatch,
missing station/time, expiry, TLS failure, write interruption and later-update
TLS reuse. These are source/host checks, not phone acceptance.

The source still requires fresh SNTP for station-profile commits. Starting a
station trial invalidates the prior SNTP observation; the commit platform
requires a new SNTP source no older than ten seconds. Browser UTC hints do
not satisfy this admission. Network-only Wi-Fi replacement does not require
SNTP. A field network without time service therefore has a distinct open
station-save policy/acceptance gate; do not silently change that time authority
or count a successful ordinary-network test as resolving it.

USB `INFO.status.station` reads the separate standalone store and cannot
prove the saved consumer station values. This continuation adds
`INFO.saved_consumer_profile`, read from the selected journal after boot:
station callsign/grid/power, saved SSID/time server, owner count/epoch and
request SHA-256. It is `null` without an admitted consumer payload and emits
no Wi-Fi password, owner key, TLS material or client material. Its structural
readback does not claim clock or TLS readiness. Use the outer device ID,
source and generation to bind it. Keep exact credential/settings comparisons
in private journal evidence; public summaries cannot prove password equality.

### Source checks and adversarial review

The resumed source checks passed `bash scripts/check_host.sh` (91/91) and
`npm test` in `src/network/bootstrap_web` (4/4). The new runtime test reloads
the committed journal, checks separate consumer/standalone station values,
later generation selection, JSON escaping, maximum SSID/time-server/epoch
values, an exact diagnostic field allowlist and fault/wrong-device clearing.

First assessment found three actionable preparation issues:

| Finding | Repair and reassessment |
| --- | --- |
| The roadmap still called bounded GP14 reset/AP/hold/expiry acceptance open and named BOOTSEL as the current action. | Reconciled the accepted GP14 closeout and parked production RF build/cutoff/default gates. Historical BOOTSEL records stay identified as historical. |
| The next station packet could mistake `INFO.status.station` for consumer readback. | Added the redacted selected-journal view above and explicit private settings comparison after activation restart. Exact field and reload tests passed. |
| The initial readback formatter retained too many string temporaries: a 896-byte Arm stack frame. | Reused one buffer and appended fields sequentially; the frame is now 520 bytes in both inhibited builds. The affected runtime test passed again after repair. |

Both default GP14-off and opt-in GP14 runtime Pico 2 W inhibited builds passed
with the locally retained SDK 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1 and CMake 4.4.3.
No dependency was downloaded. The first default attempt found the old
temporary SDK absent, and that cache still retained its platform path; the
successful default build uses a fresh `build/pico2-w-portal-default` directory.
The opt-in build uses `build/pico2-w-gp14-robustness` with robustness/flash probe
off. Both passed `check_standalone_image.py`, `check_stack_guards.py`,
`check_bootsel_topology.py` and `check_shutdown_image.py`. FLASH ends at
`0x103f3000`, journals remain reserved, the primary stack is 32 KiB and no
runtime BOOTSEL sampler is linked. Formatting and `git diff --check` passed.

The clean default image has 1,704,352 text / 136,652 BSS bytes; the opt-in
image has 1,709,664 text / 153,040 BSS bytes. Arm compiler frames are 3,352 /
1,120 bytes for default `main` / Console handler and 3,464 / 1,160 bytes for
opt-in. These static frames are not a complete call-chain peak or target
resource qualification. The tested maximum readback stays under 768 bytes;
complete INFO delivery through the 8,192-byte queue remains a target check.

Second assessment rechecked privacy, selected-generation consistency, reload
failure clearing, unchanged boot/transport/RF admission, AP lifecycle evidence
boundaries and operator authority. No further actionable source issue remained
in this readback/acceptance preparation slice. No device operation occurred.
The RF build remains parked, and P12.8/P12.10/P12.11/P12.12 remain open.

### Exact clean candidate (prepared; not installed)

Source commit `cac1d581cfb5b835561bb5abfe84496c22f9957b` was built with a
clean tracked tree. Both images embed revision `cac1d581cfb5`, use the inhibited
simulator and passed all four linked checks again. The readback label is in
both; GP14 capture is linked only in the opt-in image. Robustness, flash probe
and BOOTSEL diagnostic options are off.

| Image | UF2 SHA-256 | Intended use |
| --- | --- | --- |
| Opt-in GP14 runtime | `d55caf49334c51af5696f1f369a8589d23a618d00be7f26c19e187b562dd12de` | The next bounded B portal packet only after scoped operator authority. |
| Default, GP14 off | `fec40698ad0719ceed0b4433b53e346e08bfdf48daaa85b46453a1d80e846fa3` | Default build comparison; not selected for the manual-GP14 packet. |

The local ignored artifacts are retained in
`build/phase12-portal-cac1d58/{gp14-runtime,default}/WsprryPico.{uf2,elf,bin,elf.map}`;
`manifest.json` records source/options and every file's size/hash. The separate
`build/gp14-integrated-b-20260930/runtime-6105f9d.uf2` restoration artifact
still matches its closeout hash. Hash verification is file evidence only;
neither candidate had been flashed at preparation. The opt-in candidate was
subsequently deployed in the B packet below; the default candidate was not.

### Bounded packet: optional station details on B

Prepare this packet completely, then obtain action-specific operator authority.
This document itself authorizes no device operation. The packet needs the
selected phone/browser, station callsign/grid/power, B USB monitoring, private
journal backup/readback, serial-targeted deployment of the reviewed inhibited
readback candidate, one manual GP14 AP opening, AP association, one encrypted
station save and its automatic activation restart, plus read-only station WTP
`HELLO`/`STATUS`.
No network replacement, erase or transmitted job is required.

1. Bind B to USB serial `CDDBF8767C506C07` and device ID
   `29f20b7342051ef947aa56cb9d4fab42`. Reverify its current image, clock,
   RF-inhibited engine, inactive output, empty/unowned state, released/fault-free
   GP14 and healthy journals. The last closeout restored runtime `6105f9d8da2e`,
   network-only generation 2, access generation 1 and station `192.168.1.53`;
   these are a recorded baseline, not a fresh device observation. Identify A
   separately and leave it outside this packet. Disable no working host route
   or device schedule merely to make an assertion pass.
2. Capture private recoverable baseline/settings evidence before the save.
   Verify the preserved restoration image against the closeout's
   `7d2df90f236a6e5d8b5626caac37a542783d50dbd0db81d3fffb4780f74f80ab`
   UF2 hash; a missing or mismatched restoration artifact stops deployment.
   Deploy only the exact reviewed opt-in inhibited image to B, verify its
   hash/revision and preserved journals, then recheck the admission in step 1.
   Record the exact phone/iOS/browser and artifact identity. With an already
   prepared bounded read-only monitor, invite one GP14 hold to open the AP,
   then release. Join B's AP and manually open
   `http://192.168.4.1/owner.html`; automatic captive launch is optional.
3. Enter the operator-approved callsign, four-character grid and power. Save
   once without re-entering Wi-Fi credentials, a code, password step-up, owner
   key, console command or certificate file. Record the phone's terminal page
   and any interruption. The retained source requires infrastructure SNTP for
   this packet; an unavailable time service leaves the result open.
4. Verify the exact device and request digest, one generation increment, a
   consumer source with no retained phone owner and expected saved station
   values using `saved_consumer_profile`. Compare the private committed
   journal to prove unchanged saved Wi-Fi/time-server values. From the recorded
   generation-2 baseline, success is generation 3; if preflight differs,
   bind assertions to its actual generation instead of manufacturing 3.
   Confirm the activation restart, healthy journals, inactive output, empty
   ownership, Wi-Fi/time return and positive station Plain LAN WTP readback.
   The effective station values are the intended change; preserve unrelated
   persistent schedules, watermark and access state.
5. Observe at least 60 seconds of post-restart continuity with a finite total
   packet budget of 20 minutes. Retain the accepted new station settings on
   success. Check complete INFO delivery, allocation/fault counters and stack
   guards throughout; any new failure leaves acceptance open.
   On loss of reply, reconcile the exact authoritative journal before
   retrying or restoring anything. A partial/corrupt commit, identity drift,
   fault or unknown output stops further mutation. Record the actual final
   image, generations, AP/network state and cleanup; a failed attempt remains
   in evidence.

### Executed B station packet and result repair (2026-09-30)

The operator authorized B deployment, USB/private journal readback, AP opening
and **one** station save on the same **iPhone 17 Pro**, with **AA0NT / EM18 /
20 dBm**. Safari is visible in the supplied screenshot; the iOS version was
not separately recorded. The operator confirmed the test path was closed.
`wspr4` was offline and was not contacted or changed. No transmitted job,
network replacement, erase, second station save or Candidate A operation
was performed.

| Identity or result | Recorded evidence |
| --- | --- |
| Exact target | B USB serial `CDDBF8767C506C07`, device `29f20b7342051ef947aa56cb9d4fab42`, Pico 2 W/RP2350, 150 MHz, `inhibited-standalone-simulator`. |
| Deployment | Clean source `cac1d581cfb5b835561bb5abfe84496c22f9957b`, opt-in UF2 `d55caf49334c51af5696f1f369a8589d23a618d00be7f26c19e187b562dd12de`. Serial-targeted load/verify passed. Network-only generation 2 and access generation 1 survived. |
| Recoverable baseline | Private full flash: 4,194,304 bytes, SHA-256 `b21f114c3c70c58c168461c9f2cb0ba2dc2314396ddb35621f1f103c88dbe1be`. All 57,344 reserved bytes read before/after deployment were identical. The separate `6105f9d8da2e` restoration image remains retained. |
| Connected-station AP opening | One recorded GP14 hold/release, 12,969,000 microseconds; one manual AP request accepted and AP service ready. The phone opened `http://192.168.4.1/owner.html`; its `Pico 4fab42` identity agrees with B. |
| Durable station save | Selected consumer journal generation **3**, station **AA0NT / EM18 / 20 dBm**, zero owners and owner epoch zero. Request SHA-256 `9690e9c57315196f999d6e7bb933be612d7580d34772ac85090863a00c94f610` agrees between the private admitted journal and USB consumer readback. |
| Settings preservation | The portable journal reader admitted both private snapshots. Saved SSID, password and time server are byte-for-byte unchanged. Reserved bytes outside the profile journal are identical; access generation 1 and the unrelated standalone store remain unchanged. |
| Activation and continuity | Automatic activation boot `4078c29dc6f59d71176c6bafd641b07c`, station `192.168.1.53`, synchronized SNTP, healthy journals, empty/unowned jobs and inactive output. **61.55 seconds** of post-restart INFO continuity passed within the 20-minute packet, with about 40 seconds remaining. One readback interruption coincided with the expected activation restart. |
| Station protocol | Read-only Plain LAN WTP `HELLO`/`STATUS` passed before and after the save, bound to B and its boot, with empty/unowned state and inactive output. The existing wired route did not reach B; individual sockets used existing `wspr5` `wlan1`, without modifying host routes or contacting `wspr4`. |
| Phone result | **Not passed.** The supplied screenshot is unstyled and still says “Checking station settings.” It is not a terminal saved result, even though the journal proves the save. |
| Final state | A separate ROM readback of reserved storage required an intentional inspection restart after the packet budget. B returned normally on boot `f5ee83e3d596e04d812e502f6daea36a`, still `cac1d581cfb5`, consumer generation 3, access generation 1, station `192.168.1.53`, synchronized clock, Plain LAN ready, AP off, GP14 released, healthy storage, inactive output and no recorded fault/allocation failure. Core-0 guard is valid; observed use was 8,568 bytes. This cleanup readback is separate from the timed continuity result. |

Private captures, firmware, backups and the screenshot remain ignored under
`build/phase12-portal-b-20260930-1511/`, with deployment/readback evidence also
retained in the corresponding private `wspr5` directory. The supplied
screenshot SHA-256 is
`4f1ac14c3d8f60ac3d3fb2a55fd47b51e243fc10cbaec741cfe1736eb420d100`.
An initial preparation check expected unavailable core-1 telemetry, and an
initial USB probe chose the wrong CDC interface. Neither reached a flash or
station save; corrected device-bound probes and deployment passed. These
preparation errors are retained rather than attributed to firmware faults.

Source inspection found two plausible contributors to the phone result:
`owner.html` still fetched its stylesheet separately, and any successful
claim-status response could advance restart, including a checking response
constructed before the commit. The screenshot and USB log do not prove the
exact Safari HTTP ordering or which request was lost.

The repair embeds the incumbent styles in station HTML under the existing
matching CSP hash. An exact committed status response must now match the
consumer generation and request digest at response construction and finish
delivery before starting a three-second display interval. Without such a
reply, the existing 60-second activation fallback remains. Its result identity
survives terminal-slot expiry; further setup admission stays blocked until
actual activation, including a scheduled restart that is later cancelled and
retried when safe.

The browser distinguishes a digest-bound accepted reply from durable saved
readback. A pending attempt cannot submit again. After three minutes without
confirmation it shows an explicit unknown result and continues checking;
reconnection must return to the **same open page**, since no browser storage
or retained phone key is introduced. Exact readback after reconnection can
still confirm the attempt. A reconciliation state cannot declare success.

Adversarial review repaired the pre-commit status/restart race, a stale poll
that could declare a new POST unsaved, pending-attempt resubmission, loss of
result identity/new setup admission during late activation, and premature
success during journal reconciliation. A subsequent assessment of these
repairs found no additional actionable issue in this slice.

Validation: **91/91** host checks and **4/4** browser checks passed. The final
affected host checks and browser checks passed again after repairs. Both
default and opt-in inhibited Pico builds passed with the retained pinned SDK
and toolchain, reserved-flash/UF2 checks, stack/BOOTSEL checks and linked
shutdown checks. The new restart helper's Arm frames are 4–8 bytes; the
existing status frame is 1,080 bytes. These static frames are not a physical
peak-stack qualification. Generated HTML/CSP rendered in isolated Chromium at
desktop/mobile sizes, in form/accepted/unknown/saved states, without horizontal
overflow at 200% text size. Every endpoint was mocked. The UI detector had no
regex findings but lacked its HTML parser dependencies; the actual browser
render verified the inline style policy separately. These software previews
are not iPhone acceptance.

At the first packet's close, the repair had **not** been deployed or phone
retested. B retained its verified station settings on `cac1d581cfb5`, and that
packet's one authorized station save had been used. The following continuation
records the separately requested retest. An exact terminal saved result and different-phone
updates, no-SNTP station policy, station-loss fallback and broader robustness
remain open. This packet does not close P12.7, P12.11 or Phase 12.

### Clean retained station repair candidates

Both inhibited targets were rebuilt from clean source
`dd49d049daf24717aa3346edf1691ac3dfc9d2b3`, then passed reserved-flash/UF2,
linked shutdown, BOOTSEL topology and stack-guard checks. The clean revision
is present in each ELF. These were undeployed when retained; the continuation
below subsequently deployed the opt-in image to B.

| Candidate | UF2 bytes | SHA-256 |
| --- | --- | --- |
| Opt-in GP14 runtime | 3,360,768 | `b604f4a365c7c117b145ca224f0131b0b0463fab036b9400d383cb2bb343ddcf` |
| Default, GP14 off | 3,350,016 | `6b0a269e587f67b998eefad8353a4c75c0863e075e6e27d6e0db02a5dbada296` |

The ignored `build/phase12-portal-repair-dd49d04/` directory retains both
UF2/ELF/BIN/map sets and their size/hash/options manifest. A future manual-GP14
phone packet must use the opt-in image and remain separate from production
RF integration and default GP14 enablement.

### B station-page startup continuation (2026-09-30)

The operator requested P12.8/P12.10 image preparation and guided actions,
continuing B's deployment/readback/AP authority and a bounded additional
station save with AA0NT / EM18 / 20 dBm. `wspr4` remained offline and untouched.
No RF job, erase or network replacement was requested or performed.

The clean opt-in `dd49d049daf2` image above loaded and verified on B serial
`CDDBF8767C506C07`, device `29f20b7342051ef947aa56cb9d4fab42`, Pico 2 W,
150 MHz, `inhibited-standalone-simulator`. A fresh private full-flash backup
contains 4,194,304 bytes, SHA-256
`ea83f008c30f4ee04494bb6300a95094ef65e782e8e60250723227a35fa98a6f`.
All 57,344 reserved bytes were identical before and after loading. Consumer
generation 3, access generation 1 and the unrelated standalone state survived.
Boot `d04d63b6e2a291553356a8e2a00ccfee` rejoined station `192.168.1.53`,
synchronized its clock and passed read-only LAN `HELLO`/`STATUS`, empty/unowned
with inactive output. Existing `wspr5` `wlan1` sockets were used without host
route changes.

One GP14 opening was recorded: 12,804,000 microseconds held, one accepted AP
request and service ready after release. The operator's supplied
`IMG_1689.PNG` shows the styled Safari page, but it remains at “Checking Pico
identity…” and “Checking this browser…” with no station form. This is a
**pre-save failure**, not a terminal station result. USB readback still shows
generation 3 and the same boot, with zero readback errors and no additional
save. The collector was stopped before preparing a replacement image. Private
captures and backups remain ignored under
`build/phase12-station-retry-b-20260930-1624/` and its corresponding `wspr5`
directory. The chat image was visible but its supplied local path was not
available for copying or hashing; no file hash is claimed.

Source review found that the one-connection AP server aborts additional
connections while a response is active. The station HTML requested two script
files in parallel; a refused script can prevent startup entirely. This mechanism
follows from server admission and HTML asset requests; no Safari HTTP trace
was captured.
The correction streams each setup document with its scripts in order from
separate flash literals, under exact CSP hashes, without a combined heap copy.
The initial identity GET permits three bounded attempts for the final document
acknowledgement; setup POSTs are not replayed. The Wi-Fi page now exposes a
visible Station settings link independently of its saved-result section.

Validation passed: 91/91 host checks, 4/4 Node browser suites, the three affected
HTTP/browser checks after formatting, exact inline-script CSP hashes and the
absence of external setup script/style requests in generated documents. The
opt-in inhibited target cross-link passed with BOOTSEL topology, allocator and
stack-guard checks. Adversarial review covered flash-view lifetime, script order,
stream boundaries/Content-Length, CSP, bounded initial reads and prevention of
POST replay; reassessment found no additional actionable source issue in this
slice. These are source/build checks, not target page acceptance.

An isolated rendered-Chromium test was prepared with all requests mocked and
one-connection refusal behavior. Its browser launch was blocked by automatic
approval-review deadline timeouts on both permitted attempts, so it did not
produce a rendered result. The precise Safari request ordering remains
unmeasured. Actual phone rendering and station save remain the next gate.

The subsequently retained clean opt-in replacement is source
`79843646e89cc2a53209f65b8cececba3b32e4ad`, UF2 **3,363,328 bytes**, SHA-256
`d8b5f6d97867f728f0a7475688b8037157e0181b736ebad99fc4bcea49e5d226`.
It passed the linked flash/UF2 reservation and shutdown interception checks
again, then loaded and verified on B. All **57,344 reserved bytes** stayed
identical; the fresh 4,194,304-byte backup SHA-256 is
`c44034bbc8ed1643c9c642ab2e29fcb67fe3cd5e7ce47f68a7d33f895e0b10c3`.
Boot `9095b1994562b7e73e0c3c2dc1f7ddc2` reports firmware `79843646e89c`,
consumer generation **3**, access generation **1**, preserved AA0NT / EM18 /
20 dBm and independent standalone state, healthy guards/storage, no recorded
fault/allocation failure, empty/unowned jobs and inactive inhibited output.
It rejoined `192.168.1.53`, acquired synchronized time and passed LAN
`HELLO`/`STATUS`; GP14 is released and AP is off at this readiness checkpoint.
The exact prior `dd49d049daf2` restoration image and private full backup remain
retained under ignored `build/phase12-owner-startup-b-7984364/` and the
corresponding `wspr5` directory. The subsequent station attempt is recorded below.

Preparation events are retained separately: the old image lacked fresh clock
readiness after the elapsed repair, so it was not credited with a new LAN pass;
fresh synchronized readiness passed after replacement/restart. An initial
runner invocation preceded completion of file staging and found no runner,
performing no hardware action. It ran only after staging completed. A managed
checkout build could not update its source timestamp under the sandbox, and
automatic approval review timed out. A clean checkout inside the permitted
workspace produced the retained image. These are preparation/readiness events,
not firmware fault or phone-success evidence.

The revised source and its next target/phone evidence are separate from the
failed `dd49d049daf2` packet. P12.8/P12.10 remain open until the repaired page
and save have target evidence; different-phone and broader acceptance gates
remain unchanged.

### B later-station rejection and repair (2026-09-30)

The operator's 1:28 screenshot shows the styled station form, correct Pico
suffix `4fab42`, and AA0NT / EM18 / 20 dBm. The following attempt reported
rejection; the 1:32 screenshot shows “Another setup is in progress” and
“Station settings not saved.” The exact browser for that failure is not
verified by the screenshot. The operator also tried returning to the form;
the count of submitted requests is not established by these images.

The finite private USB collector on firmware `79843646e89c`, boot
`9095b1994562b7e73e0c3c2dc1f7ddc2`, retained consumer generation 3 and its
original request digest throughout. At host epoch `1790793157.072441`, the
station link changed from joined `192.168.1.53` to link 0/no address without a
restart or durable update. Inhibited output remained inactive; no recorded
fault or allocation failure appeared. This attempt failed acceptance.

Review found three actionable defects, repaired in this continuation:

- The real Pico AEAD transcript rejected consumer source 5 even though the
  browser, slot and commit path support later station updates. Source 5 is
  now accepted only for a nonzero generation below UINT64_MAX; the transcript
  continues binding the exact source and generation.
- Rejection before a station trial disconnected the existing station without
  having captured its saved network. Cleanup now restores only after an actual
  station switch, with the switch recorded before stopping/starting so a
  failed start and trial expiry also restore the previous network.
- A terminal slot was mislabeled as another setup, and the retry display
  stopped further recovery polling. Busy/terminal slots now retain polling and
  disable Save until available. Returning after a definite failure rechecks
  availability before enabling a deliberate new Save; there is no POST replay.

The failed collector was stopped and B normally restarted with its saved
profile unchanged. Boot `808210c531eec40120960a83a6e6ff2f` rejoined the saved
station, synchronized time and reported healthy LAN readiness, generation 3,
AA0NT / EM18 / 20, access generation 1 and inactive inhibited output.
Private failed evidence remains under ignored
`build/phase12-station-save-b-7984364/station-monitor/` and the matching wspr5
packet directory. Screenshot attachments are operator evidence; no unavailable
local attachment bytes or hashes are claimed.

Validation passed: **91/91 host checks** (including the real Pico crypto
interop regression) and **4/4 browser tests**. Adversarial reassessment checked
source/generation/tag binding, rejection before network mutation, failed-start
and expiry restoration, committed/reconcile preservation, busy-slot recovery
and stale status before retry. It found no remaining actionable issue in this
bounded repair; target cleanup and terminal Save evidence remain separate.

The bounded next packet is: run host/browser regressions including a source-5
Noble-to-real-Pico crypto vector and tampered source/generation/tag rejection;
review cancellation, failed-start, expiry and committed/reconcile paths;
reassess after repair; build a clean-source GP14 opt-in inhibited image; retain
its artifacts and restoration image; serial-bound deploy B with all reserved
bytes preserved; verify saved profile/network/time/LAN readiness; then guide
one station-only Save and compare terminal result, generation/request digest,
activation restart and continuity. No RF job, erase, A operation, wspr4 access
or host route mutation is included. Negative target cleanup is not yet
physically requalified by this source repair. P12.8/P12.10 and Phase 12 remain
open pending the named physical and broader gates.

The repaired clean-source opt-in image is commit
`4d46a23253eed7906eec59e8a34c5cdf32250f95`, firmware `4d46a23253ee`,
UF2 **3,363,328 bytes**, SHA-256
`83f3265dea30e637bcddd9a4c6a03812f53e32cce63b9d2ac73123b24b8f98ea`.
GP14 runtime is enabled; BOOTSEL diagnostic, flash probe and robustness hooks
are disabled. Pico SDK 2.3.1 (`079c6f39023649b154152db30f1d781e884879bc`)
and Arm GNU 15.3.1 produced it. Linked stack, allocator, BOOTSEL topology,
reserved flash/UF2 and network shutdown interception checks passed.

The image loaded and verified on the same inhibited B, serial
`CDDBF8767C506C07`. All **57,344 reserved bytes** were identical before and
after loading. The fresh private 4,194,304-byte backup SHA-256 is
`895b20c903dafb6bde3d993bddf80bb422f07893ccc24ecfb7637f2017b3854e`.
Boot `9df4f4d37dc0234126cab8355ce3f390` retained generation 3, access
generation 1, AA0NT / EM18 / 20 and independent standalone state. It rejoined
`192.168.1.53`, acquired synchronized time and passed exact-device read-only
LAN HELLO/STATUS: empty, unowned and inactive. The previous `79843646e89c`
application, all four new artifacts and manifest are retained privately under
ignored `build/phase12-owner-update-b-4d46a23/` and matching wspr5 directory.
The owned clean build checkout was removed after copying the artifacts.
The five unrelated operator documentation paths remain byte-for-byte unchanged.

A fresh 20-minute read-only collector is running for the next guided GP14
opening and **one** same-iPhone station-only Save. No new successful phone
terminal result or durable generation 4 is claimed at this deployment
checkpoint. The accepted result is recorded below; the remaining physical rows are still required.

### B station update accepted in DuckDuckGo (2026-09-30)

**Accepted within this packet by the operator.** The same iPhone 17 Pro used
DuckDuckGo; its version and the exact iOS build were not recorded for this
packet. The operator's 1:59 screenshot shows the correct Pico `4fab42`,
“The Pico received your station settings. Checking the saved result” and
“Station settings accepted.” This is the accepted-request display, not an
observed terminal “saved” display. When asked to reopen the AP and return to
the original tab, the operator reported that DuckDuckGo privacy settings had
refreshed the page and explicitly accepted this run without switching
browsers or repeating Save. No further phone action or Save was requested.
The browser-refresh result is retained as a robustness observation; no final
browser confirmation is invented.

On exact inhibited firmware `4d46a23253ee`, B's first GP14 opening was
15,095,000 microseconds held and one accepted AP request. Read-only monitoring
recorded a station rejoin and fresh synchronized time, then durable consumer
generation **3 -> 4** and a single observed activation boot change from
`9df4f4d37dc0234126cab8355ce3f390` to
`f65ac883a080f8f57bf4e490b4ee9519`. The new request SHA-256 is
`e7418f3417fde09fb9288b8d15b0c9c80d1ec6b11a04f5248cf3c02676ac57b5`.
B rejoined `192.168.1.53`, with synchronized clock, LAN readiness, healthy
storage/guards, no recorded fault/allocation failure and inactive output,
for **61.6106 seconds** of post-activation continuity. One USB read failed
because the device path briefly disappeared at the activation restart; the
collector recovered. This interruption is recorded, not counted as a firmware
fault. No second generation increment or activation restart was observed.

The later AP reopening was 15,891,000 microseconds. A subsequent fresh-clock
check found holdover with a joined station and LAN readiness, and did not
recover synchronized status in its bounded 90-second read-only wait. This is
a retained clock/AP robustness gap, separate from the accepted commit and
previous 61-second continuity result. It does not qualify extended AP/time
coexistence. The cause was not established by this packet.

A separately recorded, authorized ROM **readback only** then captured all
57,344 reserved bytes, SHA-256
`155143a2740f5bf275a08ae7bf8fbe68312956142750b4ee753464d7b9fd0b80`.
The canonical read-only journal comparison proves generation 3 -> 4, the exact
new INFO request digest, AA0NT / EM18 / 20 dBm, zero retained owners/owner
epoch, byte-identical saved SSID/password/time-server and **identical TLS
material**. The existing client list also remained identical; it was empty,
so this does not qualify preservation of populated client records. Every
reserved byte outside the profile journal was identical, including access,
BTstack and the independent standalone journal. No firmware load, erase,
station Save or RF job occurred during this inspection.

The inspection's deliberate normal restart is separate from the activation
budget. Final boot `53a0f79bb8c4109d892e208d491fe161` retained generation 4
and the exact profile, rejoined its saved network, acquired synchronized time
and passed exact-device plain LAN HELLO/STATUS, empty/unowned with inactive
inhibited output. GP14 was released and AP off. All captures, parsed comparisons
and restoration artifacts are retained privately under ignored
`build/phase12-owner-update-b-4d46a23/` and the matching wspr5 directory.

Adversarial evidence reassessment verified the authoritative journal against
USB rather than treating the screenshot as a durable-save proof, separated
activation from maintenance restarts, retained the restart readback gap,
operator acceptance/browser-refresh limitation and extended AP/clock gap,
and confirmed that empty-client preservation is a bounded result. No new
source change was made in this evidence closeout. Same-phone station setup
and the later source-5 station transaction are accepted within this packet;
P12.8/P12.10 remain open for different-phone, offline, negative/concurrency,
populated-client preservation and other named physical gates. Phase 12 is
still active.

### Saved station form prefill continuation (2026-09-30)

The operator requested that `/owner.html` show the last saved station details
on opening, including after a DuckDuckGo privacy refresh. The bounded repair
adds exactly callsign, four-character grid and power to AP-local public setup
status. It uses the already parsed, matching device/generation consumer runtime
snapshot: no profile/TLS reparse or whole-profile response is introduced.
Non-consumer, faulty, wrong-device or stale-generation snapshots return null.
This explicitly revises the previous public-status exclusion for these three
station fields; Wi-Fi credentials and TLS/owner/client material remain absent.
Station changes still use the existing one-use encrypted submission.

Every fresh document fills the existing form from that readback without phone
storage or Save. Polling may refresh an untouched form after a generation
change. Input/change in any field protects the whole draft; pending Save,
retry and terminal states retain their existing behavior. The new-station
network-only form retains blank callsign/grid and its default power.

Validation covers exact three-field serialization with secret-bearing profile
fixtures, current-generation selection, stale snapshot, wrong device,
non-consumer/fault selection, fresh/private-browser refresh, draft preservation,
malformed/extra-field responses and no POST during loading. The first host run
exposed an invalid test fixture transition (its retained-owner epoch and
request digest were unchanged), corrected by using an admissible new fixture;
the storage admission contract was preserved. An initial browser assertion
incorrectly treated a fresh authoritative device identity as an identity swap;
it was corrected to test an actual later-poll swap. A local test-edit invocation
used the wrong directory and changed nothing; it was rerun from the repository.
These are retained test/preparation findings, not target firmware faults.

Adversarial review checks public field minimization, device/generation binding,
no secret serialization, browser input races, pending Save/unknown-result
handling and source-5 activation. After repairs, **91/91 host checks** and **4/4 browser tests** passed.
Adversarial reassessment found no remaining actionable finding in this slice.
The deployment packet is B only, inhibited,
with a fresh full backup and all reserved bytes preserved; no additional Save,
RF job, erase, A change or wspr4 access is included. Phone observation of the
prefilled form remains distinct from source/host and deployment evidence.

The retained clean opt-in image is source
`8d0ad7273707cda924f65b9e67fd29bf0f350739`, firmware `8d0ad7273707`,
UF2 **3,367,936 bytes**, SHA-256
`260a03a9b23eb0c6af91b33c3870964176a9d70a20be37a2d4d0f0f13b08dd02`.
The pinned SDK/toolchain and GP14-only options are unchanged from the prior
packet. Target build, linked stack/allocator/BOOTSEL topology, reserved
flash/UF2 and shutdown interception checks passed. The clean temporary source
checkout was removed after retaining all four artifacts and manifest.

It loaded and verified on B serial `CDDBF8767C506C07`; all **57,344 reserved
bytes** were identical before and after loading. The fresh 4,194,304-byte backup
SHA-256 is `f05a4697e0475992d54209c7a35499021e6476a262cfb08f652045af4d8f128a`.
Boot `ea5d36416cced917ffd3cf679d428edc` retained consumer generation 4,
access generation 1 and the exact saved-profile readback: AA0NT / EM18 / 20,
request digest `e7418f3417fde09fb9288b8d15b0c9c80d1ec6b11a04f5248cf3c02676ac57b5`,
zero owners and unchanged independent standalone state. It rejoined
`192.168.1.53`, synchronized time and passed exact-device plain LAN
HELLO/STATUS, empty/unowned with inactive output. No station Save occurred.
Artifacts, full backup and exact `4d46a23253ee` restoration image are retained
privately under ignored `build/phase12-owner-prefill-b-8d0ad72/` and the matching
wspr5 directory.

Two attempts to avoid another physical opening were unsuccessful and did not
open the AP: the retained older console CLI lacks a `softap` action, and an
identity-checked direct USB request for the source-defined `ACCESS SOFTAP`
command returned `profile_runtime_unavailable` for this consumer runtime.
The established GP14 opening path was therefore used in the phone instruction;
the USB administration guard was not changed as part of a form-prefill fix.
A finite six-minute read-only observer was started and ended before the later
phone confirmation. Its last captured state had unchanged generation 4 and
inactive output; it did not capture the successful phone visit or AP opening.

- [x] **PASSED / CLOSED SCOPED — saved station form prefill.** The operator
  confirmed "That works, cross it off" after checking the deployed page on the
  same iPhone 17 Pro in DuckDuckGo. This accepts opening the owner page with
  AA0NT / EM18 / 20 dBm filled from the saved settings. This confirms fresh-page
  prefill; a separate induced privacy refresh was not reported. The refresh
  behavior has the browser-test coverage above. This is operator-attested phone
  evidence, separate from the deployment/USB and host checks above. No
  screenshot or exact browser/iOS version was supplied for this confirmation;
  the finite observer does not establish the device state during that visit.

No additional Save was requested for this check. The accepted generation-4
Save remains the prior save evidence; this prefill pass does not close its
historical lost-tab terminal-result limitation or the wider P12.8/P12.10 gates.

### Four/six-character grids and extended callsigns (2026-09-30)

The operator requested four- or six-character grid locators and saving an
extended callsign. The [station input review](phase12-station-input-review.md)
records validation through forms, encrypted claims, storage and public prefill,
including the maximum 117-byte envelope and unchanged legacy inputs.
Six-character locators retain their full saved value and use their first four
characters for Type 1 WSPR. Extended callsigns are preserved in full; a call
unsupported by the current encoder is rejected before any scheduling claim
or watermark reservation. Type 2/3 transmission support is not added.

**10/10 affected host groups**, **4/4 setup browser groups**, the clean Pico
target and its linked safety/storage checks passed. Adversarial findings were
repaired and reassessed. The unrelated existing host adapter signed-comparison
warning prevents a full-suite pass claim for this packet.

Clean source `615888e5364be169839ae879d6bb955c84518bab`, firmware
`615888e5364b`, is deployed on B serial `CDDBF8767C506C07` in the
`inhibited-standalone-simulator` engine at 150 MHz. The fresh backup and
all 57,344 reserved bytes were verified; the complete saved consumer profile
survived unchanged. Preflight found a newer generation-5 **AA1NT / EM18 / 20**
record, which was preserved. This readback does not establish the phone's
terminal result for that intervening save. New boot
`d6f6015528fef0239c373633a4099576` synchronized time, rejoined
`192.168.1.53` and passed exact-device read-only plain LAN HELLO/STATUS,
empty/unowned and output inactive. Artifacts and the verified prior-image
restoration path are retained privately in the review's deployment directory.

No station Save was performed in this packet. The new-format phone save rows
remain open; the previously accepted saved-form prefill row remains closed
within its recorded scope. P12.8/P12.10 and Phase 12 remain open.

The operator subsequently authorized flashing **both A and B** with this exact
image. The [A/B deployment continuation](phase12-station-input-review.md#authorized-a-and-b-flashes-2026-09-30)
records each identity, prior firmware, new boot, fresh full backup and verified
restoration image. Both serial-targeted loads verified; all 57,344 reserved
bytes on each adapter and their own saved settings were preserved. A retains
network-only generation 1; B retains consumer generation 5 and AA1NT / EM18 /
20 dBm. Both now report `615888e5364b`, synchronized time, healthy storage and
inactive inhibited output. Exact-device USB and read-only plain LAN
HELLO/STATUS checks passed on each. This adds A deployment and B reflash
evidence without closing the new-format phone save rows or other Phase 12 gates.

### Following packets and closure gates

| Packet | Required outcome | Evidence still needed |
| --- | --- | --- |
| Different phone, later station and Wi-Fi changes | A fresh phone saves without a retained owner; expected generation and request digest agree after activation. Existing station/TLS data survive a Wi-Fi-only update. | Separate phone identity, exact terminal result, device readback and settings comparison. B's existing same-phone network update is already recorded. |
| Failed replacement and unknown result | Bad network credentials preserve the last committed profile and restore its usable network; lost replies never create an unsupported success/failure claim or duplicate activation. | Predetermined negative/disconnect stimulus and exact old/new generation/result evidence. |
| Station loss and field network | AP returns after 60 seconds of unusable saved station Wi-Fi; the local portal loads offline and can replace the network. Stable reconnection withdraws AP after 30 seconds when no lease or reply retains it. | Controlled network loss with approved host route restoration; phone offline capability, identity and reconnect/withdrawal observations. Station save without SNTP remains a separate decision. |
| Provisioning reset and full erase | Distinct visible actions have the selected preservation/clearing behavior and recover safely from interrupted intent. | Consumer controls/design completion, deterministic failure checks, then separately authorized destructive target cases. GP14 normal reset is already accepted in its bounded inhibited scope. |
| P12.12 robustness | Fault, trust, resource, concurrency, controller-time, LED, soak and final restoration assertions each have bounded evidence. | A finite matrix based on the accepted consumer path; no renewed BLE-owner ceremony or repetition of closed P12.9/GP14 scopes. |

P12.7, P12.8, P12.10, P12.11 and P12.12 remain open at their named gates.
The historical Stage A matrix below does not authorize these new packets.

## Current admission state

The production-integration tranche enables the GATT service, network-only
activation platform and indicator controller in the standard RF-inhibited
image. It retains one CYW43 owner and supplies the repository-owned offline
Bluefy release. Later continuations production-connect authenticated controller
time, Identify/status, an unchanged BLE WTP/1 stream and the independent
SoftAP DHCP/mDNS/HTTP/HTTPS browser/control path. The BLE subset has the bounded
native-Pi evidence described above. SoftAP has hardware-free build/test evidence
plus the bounded native-Pi physical evidence recorded in the
[SoftAP review](phase12-softap-physical-review.md). SoftAP credential
provisioning and reset administration are not production-wired. BLE profile
provisioning is wired but has not passed physical acceptance.

The operated candidate is Pico 2 W USB serial `0BF4B4AEC9FFB344`, device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`, station MAC
`88:a2:9e:0a:60:df`, suffix `0a60df`. The comparator
`CDDBF8767C506C07` was identified but not modified. The first candidate build
was based on `7451a4047677-dirty`; its UF2 SHA-256 was
`8ea4121ebf81cccb1cdaeaae61243f092d4e0acbe1fe89f4d24c7acb8232767b`.
The linked application ended exactly at `0x103f3000` with a 16 KiB primary
stack.

The earlier clean restored baseline was source commit
`5afe7576f0016ef3e927090c15232ac5c8daeb4f`, firmware identity
`5afe7576f001`, with UF2 SHA-256
`112f798233e12f2e9b7b049412ab428346b9fb1fc734915e823d1cb84feb7c12`.
Serial-targeted picotool load and verification completed `OK`. Boot ID changed
from `bb9ab0b52c02b3ddde46b5150cadd449` to
`e7e8854f51789fb1aef53281c817d588`; the device again reported
`inhibited-standalone-simulator`, empty/unowned and `output_active=false`.
Access generation 2, factory profile generation 0, station `AA0NT/EM18/20`,
the 120/0 schedule, watermark `1789607761000000000`, configuration journal
sequence 72 and watermark journal sequence 12 were preserved. Storage remained
healthy, BLE was running and disconnected, and all new WTP counters were zero.
This is clean-image identity, preservation and restoration evidence only, not
functional acceptance of controller time, Identify or WTP over BLE.

The bounded native-Pi SoftAP candidate is clean source
`0ecf9c170384fd2cc3ba802515e1d2c1396ab9fa`, firmware identity
`0ecf9c170384`, and UF2 SHA-256
`6261e322884a280afcd997537d6248fbbf0033b879fab1b2a661acd3a3575e23`.
Serial-targeted load/verify passed. This image retained factory profile
generation 0, healthy access generation 3, station `AA0NT/EM18/20`, the 120/0
schedule, watermark `1789607761000000000`, configuration sequence 72 and
watermark sequence 12. The target passed bounded WPA2, DHCP, mDNS, TLS 1.3,
password/origin/cookie, controller-time, status, `HELLO`/`CLAIM`/`RELEASE`,
logout, reconnect and resource-return checks without `LOAD`, `ARM` or RF. The
native-Pi result does not accept any phone-dependent row. After cleanup and
reboot, automatic fallback remained applicable because the preserved factory
station configuration was unavailable; stable-station AP withdrawal remains
open.

The later phone-assisted BLE continuation kept Candidate B untouched and used
Candidate A with exact RF-inhibited firmware `4377d2ded8e3`, UF2 SHA-256
`048c3feef2536b7e17c74edc153d4f25a4fa1980e4910566d7d7aaba677ef22a`
and boot `331e555683a5d6c6122735a07883e0a8`. The final bounded WTP pass used
the exact Bluefy release
`e1e6caa574a0e5c75cfd8c0a168c3ec8c2b896322ec7a7acc20d555f357f0625`.
The accepted rows and remaining limits are summarized in the status above and
recorded in detail by the production acceptance review.

On the original dirty production candidate the standard image reported
`inhibited-standalone-simulator`, empty/unowned and
`output_active=false`. USB-local adoption produced healthy access generation
1 with the public default active and enrollment closed. Station
`AA0NT/EM18/20`, the 120-second schedule, and watermark
`1789607761000000000` were preserved. A first advertisement attempt exposed
empty data because BTstack retained pointers to temporary buffers; after moving
those buffers into transport lifetime, a bounded wspr5 scan observed
`WsprryPico-0a60df` with the selected service and public BLE controller
address `88:A2:9E:0A:60:E0`. That failed attempt is retained, not replaced.

In the initial online Pages tranche, one successful application-authorization
exchange was recorded, but the exact iPhone/iOS/Bluefy versions and effective
offline cache were still unverified. The later phone-assisted continuation in
the production review records the exact versions and bounded phone-time, LED,
field-status and Bluefy read-only WTP passes summarized above. Offline reuse,
profile provisioning/activation and broader Bluefy acceptance remain open. No
Wi-Fi/TLS profile or other post-selection mutation was submitted. The
credential-free result and continuing review are
`phase12-production-acceptance-result.json` and
`phase12-production-acceptance-review.md`.

## Admission record

Before any operation, record and independently verify:

- clean source revision, pinned SDK/toolchain/submodule revisions and complete
  configure options;
- exact board/serial/device ID/station MAC, previous firmware and candidate UF2
  hashes, boot ID and flash-layout report; separately identify and hash every
  noncandidate fault-injection image or harness and its enabled injections;
- exact iPhone model/iOS version, Bluefy App Store identity/version, and the
  Web Bluetooth page origin, revision/hash, delivery mode and effective cache
  state;
- each access sector's erased/nonerased state plus redacted format, generation and
  CRC validity before initialization or reset testing; keep any raw sector hash
  private and outside the credential-free evidence because it can verify a
  guessed password offline;
- explicit authorization for the named device, BLE and Wi-Fi radio operation,
  SoftAP creation, credentials, trust-store actions, reboot/flash actions and
  finite duration;
- authoritative inactive output, empty/unowned job state, disabled schedules,
  healthy configuration/profile/watermark journals and backed-up recoverable
  nonsecret metadata;
- a credential-free evidence directory and a cleanup/restoration plan armed
  before the first mutation.

Any missing identity, unknown output state, unhealthy store, unexpected running
service, source drift or unapproved trust/radio action stops the procedure.

## Stage A: RF-inhibited-first functional matrix

Use the exact candidate standard RF-inhibited image for every claim about
production behavior. A separately built, separately hashed RF-inhibited
fault-injection image or external harness may be used only for named
unreachable storage, identity, timing, output-state and network-activation fault
branches. Record that evidence as fault-path evidence, never as candidate-image
or RF evidence.
Bound each case and retain failures rather than replacing them with retries.

1. Verify full device ID, station-MAC-derived names and the illustrative
   default on the recorded board. With the admitted fault harness, inject a
   missing/invalid MAC read and prove no substitute suffix, BLE advertisement/
   enrollment or SoftAP starts; USB reports the identity fault and a later valid
   checked read recovers. Rotate or randomize the BLE and SoftAP interface
   addresses and prove every suffix/name remains derived from the station MAC
   and an interface-address change never authorizes a mutation. With the admitted
   fault harness, use colliding synthetic suffixes and different full IDs to
   prove cross-device authentication
   and mutation fail. Prove new-bond enrollment is closed outside its 120-second
   window. Under the public default, prove every window is physically or USB
   confirmed. Under a custom password, prove deliberate device-local action or
   an already-authorized session with fresh password step-up may open the window,
   while a retained bond alone cannot. Prove sensitive password/trust/bond/reset
   operations under the public default need fresh physical/USB confirmation and
   under a custom password need fresh step-up. Returning-bond discoverability
   alone grants no principal.
   Verify both UIs and status warn while the public default is active. Accept
   custom-password lengths 8 and 63, reject 7, 64 and unsupported/control
   characters transactionally, never disclose entered/custom values, and prove
   the upstream station-network password remains unchanged.
2. Exercise LE Secure Connections Just Works, full-device display, default and
   customized passwords, returning bonds, the four-bond limit and revocation.
   Verify the same current local-access password is used for new-bond application
   authorization, SoftAP WPA access and SoftAP application login while remaining
   distinct from station Wi-Fi and TLS identities.
   Prove the one-active-GATT-connection limit returns busy without displacement
   or bond mutation. Prove no silent eviction and that wrong password, timeout,
   disconnect or cancellation deletes a provisional bond. Inject deletion/epoch-
   store failure and prove **all** BLE local control remains disabled until
   physical recovery. Through a separate authorized management path, remove the
   current idle bond and prove its next command is rejected, a bounded revocation
   result is delivered when possible, the connection closes and reconnect is
   rejected. While that bond owns loaded, armed or running work, prove removal
   returns busy with no side effect; transport closure retains ordinary WTP
   lease/lifecycle behavior.
3. Capture the negotiated ATT payload and separately exercise the bounded
   provisioning transaction and full WTP framing/reassembly through maximum
   payloads. Prove the BLE bond principal, SoftAP session-token principal and
   certificate principal remain distinct, all job operations use one JobService,
   and a path change cannot transfer/resume/release ownership without the exact
   original principal/session authority.
   Separately prove one provisioning session/staged profile, 7,168 profile bytes,
   512-byte commands, 256-byte status notifications, ordered fragments, the
   30-second no-progress timeout and eight replay digests retained five minutes.
   Verify staged secrets are scrubbed after every terminal path.
4. With station Wi-Fi and cellular data disabled, load the exact offline Bluefy
   artifact. On the client/evidence side verify its approved origin, hash and
   visible version, absence of unapproved remote scripts/analytics/credential
   services and clearing of temporary secrets; do not claim the Pico can observe
   browser provenance. On the target, reject unsupported wire-protocol versions
   plus wrong suffix/device,
   password, malformed, oversize, duplicate, replay, out-of-order, interrupted,
   timed-out, cancelled and competing requests.
5. Through authenticated BLE and, separately, provisioned pre-clock SoftAP,
   seed UTC from the phone and verify nonce/device/principal/session/monotonic
   binding, the fixed 250 ms phone allowance, full round trip, local margins,
   2025-2099 range, 500 ms maximum uncertainty, refresh no slower than 60 seconds
   and the 90-second ARM-age gate. Reject stale, replayed, wrong-device, wrong-
   session, nonmonotonic and over-budget observations. Suspend/close the page and
   prove age and uncertainty continue growing until new admission fails. Verify
   overlapping same-principal refresh, nonoverlapping same-principal disagreement,
   different-principal `time_source_busy` while the source remains valid, takeover
   only after it ages invalid and two-controller-sample recovery. Verify valid-
   overlap phone-to-SNTP promotion, lower-priority phone noninterference while
   SNTP is valid, nonoverlap disagreement latching, rejection of new ARM/launch/
   schedule admission until two-SNTP-sample recovery, reboot-unsynchronized
   behavior and large forward/backward effects on loaded/armed/running jobs and
   the watermark. Confirm phone time reports `leap=normal` plus source, sample
   age, uncertainty and disagreement state. A correction may revalidate a merely
   loaded job, must make an armed not-yet-active job `missed` with output
   disabled when its launch is no longer valid, and must never retime or stop
   an already running job.
6. From a blank generic image, provision generation A Wi-Fi, time-server and TLS
   material through authenticated BLE (and separately the documented USB-local
   path if admitted). Verify committed source mode, reboot persistence, station
   association, DHCP/mDNS identity and station-interface mTLS WTP/HTTPS. Interrupt
   every profile/source-mode journal stage and prove old-or-fail-closed behavior
   without legacy Wi-Fi, build-trust or superseded-CA resurrection. Inspect the
   admitted bundle/image and prove the per-device CA private key is absent while
   the intended server key/certificate and client CA are present. Starting with
   both access sectors erased, prove identity/MAC/output checks and new live
   physical/USB confirmation precede the first access record and radios. Verify
   the successful record contains the selected format/adoption magic, access
   epoch 1, derived default, empty authorization index, field mode false and no
   reset intent. After customization, erase both sectors and prove the identical
   all-erased state again permits no radio or default until a new confirmation.
   Interrupt each initialization erase/program/commit boundary and prove any
   non-erased invalid remainder latches recovery-only access fault rather than
   being treated as all-erased. Never record secret payloads or private keys.
7. With no infrastructure network, prove a blank generic SoftAP bootstrap exposes
   only read-only full identity, build/wire version and nonsensitive status at
   `http://wsprrypico-<suffix>.local/`; it accepts no password, controller time,
   first-profile upload or job/control mutation. Verify DHCP and mDNS reach that
   exact manual-Safari route without DNS interception; any captive sheet accepts
   no credential and only directs the operator to Safari. After a valid device-
   bound TLS identity exists and public server trust is explicitly enrolled,
   verify `https://wsprrypico-<suffix>.local/` provides provisioned pre-clock
   server authentication, password login and controller time without a client
   certificate, while station HTTPS and raw TLS-WTP still require mTLS. Reject
   wrong CA, DNS SAN, Host/Origin and every certificate warning. Prove a same-
   suffix evil twin obtains no reusable credential, WPA association alone grants
   no application status/control principal, and the provisioned pre-clock
   service rejects profile/password/bond/trust mutation and all job control
   until ordinary authenticated services admit them.
8. For the SoftAP login, prove at least 128 random token bits, Secure/HttpOnly/
   SameSite=Strict session-cookie delivery, no URL or script-readable-storage
   exposure, per-login principal separation, 15-minute inactivity and the fixed
   12-hour ordinary-authority deadline, same-token reconnect, and invalidation on
   successful logout, password change, recovery and reboot. At the deadline,
   prove an empty/loaded token expires normally; an armed/running exact session
   enters owner-only grace permitting only event delivery, STATUS, ABORT and
   same-principal controller-time observations bound to the same device/session.
   With an accelerated deadline and an already armed future launch, prove valid
   refresh no slower than 60 seconds preserves the 90-second source-age rule and
   permits the already admitted launch; reject wrong-principal, wrong-session,
   stale and replayed observations without admitting a new ARM or schedule.
   Reject LOAD, ARM, configuration, provisioning, access administration and new
   WTP sessions during grace, then invalidate immediately at terminal. After
   HELLO, prove a token maps to one exact WTP session; a refresh, including
   during owner-only grace, reattaches only after authoritative STATUS and never
   creates or chooses a replacement session. Prove valid-session
   password step-up retains its token/principal and cannot silently replace an
   owner-bearing session. Fill all four session slots, prove a fifth returns busy
   without eviction, and prove reclamation after every invalidation path. Before
   the absolute deadline, suspend the page beyond 15 minutes during an armed/
   running job and prove same-token resume; at terminal prove the inactivity
   timer restarts and expires the token after 15 minutes idle. A merely loaded
   job still expires and aborts/releases under its ordinary 5–60-second WTP lease.
   Prove logout returns busy while loaded, armed
   or running and succeeds only after ABORT or a releasable terminal state. Then
   lose the cookie and prove the job follows ordinary WTP lease/lifecycle without
   ownership transfer and only the existing local trusted safety ABORT through
   the physical Console or explicitly authorized USB-local recovery adapter can
   stop it. Repeat Host/Origin, content type, request-header, Fetch Metadata,
   wrong-token, cross-principal, CSRF and replay negatives.
9. Exercise immediate no-profile SoftAP, at-most-60-second station fallback and
   explicit field mode. From an authorized non-SoftAP session, request the AP and
   prove one 120-second ready-state join/login grace; a duplicate returns busy
   without extension, login replaces it with token retention, expiry stops the AP
   only when station is stable and no other cause remains, and reboot clears it.
   Prove fallback remains while station is unavailable and stops only after 30
   seconds of usable station service, no live ordinary/owner-grace token, join
   grace or reply, and no other AP cause. Recover station while a
   page is suspended and prove its valid owner token retains the AP through
   loaded/armed/running work; loaded work still follows its ordinary WTP lease.
   Prove the runtime fallback cause is reevaluated rather than persisted at
   reboot. Prove field mode has no inactivity expiry, persists across reboot until
   explicit exit, and other no-profile/recovery causes still control AP state.
10. Verify the slow SoftAP heartbeat (200 ms on, 1800 ms off) and authenticated
    Identify pattern (three 150 ms pulses followed by 1250 ms off, repeated five
    times). Prove Identify priority, duplicate nonextension, concurrent busy,
    core-0-only checked LED writes and error reporting without RF/job side effects.
    Prove reboot cancels Identify, requested/starting/failed SoftAP never shows the
    ready heartbeat, and completion recomputes actual AP readiness before choosing
    heartbeat or Off.
11. Replace generation A with B under fresh-password step-up. Prove every proof
    and physical/USB confirmation is device/principal/session/operation/nonce
    bound and also binds the exact canonical operation parameters, current
    profile/access generations, staged-profile digest, bond/reset/password target
    and boot ID. Prove it is single-use and at most 120 seconds. A BLE GATT
    disconnect must invalidate it. For SoftAP, prove the fresh password travels
    in the exact mutation request, a separate confirmation binds to the logical
    cookie session/request digest, routine one-request TCP close does not cancel
    an admitted mutation, and cookie loss/logout/cancel/reboot/timeout/replay or
    wrong-operation use invalidates authority. Under the public default, reject
    missing confirmation; under a custom password accept fresh entry but reject
    a retained bond alone. Hold response delivery pending after commit and prove
    the admission gate accepts no new A- or B-generation network principal,
    invalidates other existing network principals and permits only the applying
    transport's terminal response. Drop that response and prove one activation
    after the five-second timeout. After activation, prove B client credentials
    are accepted, A client credentials are rejected and the Pico serves only B's
    server certificate/key. Record separately that the iPhone may still trust
    A's public server CA until independently authorized removal, expiry or
    revocation; do not report that phone-side state as Pico dual trust. Replace
    time peer A with B, prove commit invalidates A's observation, DNS result and
    pending callback, ignore delayed A traffic, retain a valid controller source
    under its normal rules or become unsynchronized, and accept B observations
    only after activation. Interrupt B-to-C before commit and prove B remains the
    current generation while A never revives. After C commits, inject target
    prepare, final activity-recheck, quiesce, install and restart failures. For
    each failure, prove C remains the sole authoritative generation, admission
    stays closed to all network principals until idempotent recovery succeeds,
    late A/B SNTP and DNS callbacks remain rejected, staged secrets are scrubbed,
    and reboot/status recovery never revives A or B.
12. Change the local password and interrupt every password/access-epoch/bond-store
    stage. Prove pre-commit reboot retains the complete old epoch, post-commit
    reboot selects the new epoch and immediately rejects old bonds, and newest-
    record corruption fails closed. With successful delivery, prove the terminal
    response precedes exactly-once activation/erasure; drop that response and
    prove exactly-once activation follows only after the bounded five-second
    timeout. Verify the WPA key changes, every old local session closes, old-epoch
    bonds/tokens fail, and the new password works without changing the upstream
    station password. Bond-erasure failure must disable BLE. Prove password/
    profile replacement preserves the field-mode flag and a corrupt newest
    field-state record fails closed without selecting an older flag.

    Verify access recovery clears authorized/provisional bonds and the custom
    password, increments the epoch, restores the public default, sets persistent
    field mode, opens one confirmed 120-second enrollment window and forces
    SoftAP while preserving profile, station, schedules and watermark. Verify
    provisioning reset produces those access-recovery end effects and additionally
    selects either the unprovisioned tombstone or a separately confirmed valid
    build-bundle mode without legacy resurrection. Verify full operational erase
    additionally clears station, schedules, watermark and the field-mode flag
    while leaving platform-reserved
    E10 handling under its existing contract. Prove the three chosen physical
    gestures are distinct and resistant to accidental invocation.
    At every reset phase, cut power and prove one mutually exclusive outcome:
    complete pre-intent authority; recovery-only with `reset_pending`, output
    verified off and all radios/schedules/jobs disabled while idempotently
    resuming; or, after final intent-clear commit, the complete post-reset state.
    Drop the terminal response after intent clear and prove the client reconciles
    boot/source/access generations and status without replaying the destructive
    request. Cut once after intent clear but before enrollment starts and once
    during the 120-second window; after each reboot prove the complete post-reset
    state remains, the enrollment window is closed, it does not reopen
    automatically and fresh physical/USB-local confirmation is required. Prove
    source-mode/tombstone commits before public-default activation, every target
    store verifies before intent clear, no mixed old/new authority is exposed,
    E10 is untouched, and enrollment/SoftAP begins only after clear.
13. During external ownership, loaded, armed and running-simulated states in the
    exact candidate, plus failed, output-active and output-unknown states in the
    admitted fault harness, prove profile, password, epoch, bond, enrollment,
    field-mode and reset mutations return busy with no write after a final
    activity recheck. Prove status, returning-bond service, controller-time,
    Identify and transaction cancel retain their bounded nonauthoritative
    behavior. Transport loss or revocation causes no adapter-specific job
    transition: an empty session releases, a loaded job follows its 5–60-second
    lease and aborts/releases on expiry, and armed/running work continues to its
    normal terminal state. Separately prove reboot verifies output off and then
    invalidates the WTP principal mapping, ownership, loaded work, replay state
    and terminal records.
14. Run bounded concurrency and soak with BLE advertising/management, station
    association, controller time/SNTP arbitration, mTLS WTP/HTTPS, SoftAP password
    sessions and LED indication. Record heap, largest allocation, stack guards,
    lwIP/BTstack pools, TLS allocation, flash operations, session counts, timeouts
    and complete resource return. Prove one active BLE connection, four SoftAP
    sessions and deterministic rejection plus reclamation at each bound.

Before Stage A admission, confirm that the candidate reserves the selected
`0x3f3000`–`0x3f4fff` two-sector access journal, moves the linked application
end to `0x3f3000`, leaves every later reserved bank unchanged and rejects UF2
payloads in all reserved ranges. Interrupt both access-journal sectors at every
erase/program/commit boundary with the admitted fault image/harness and retain
old-or-fail-closed evidence. Those injections qualify recovery branches only;
the standard candidate must separately demonstrate normal adoption, persistence,
replacement and boot selection.

Stage A must end with RF inhibited, output authoritatively inactive, no owner,
provisioning closed, SoftAP stopped, intended network/trust state restored and
all journals healthy. A disconnect or reboot is not restoration evidence.

## Stage B: separately authorized RF coexistence

Stage B is optional and requires new explicit RF authority plus a source-impact
assessment against Phase 11.5/11.6. Use the accepted 138 MHz/divider-1/GP2
configuration first. Freeze RF path, attenuation, receiver settings, credentials,
network and clock for comparison.

- Repeat the affected Phase 11.5 admission, service-gap, poll, heap/stack,
  TLS/network-loss, storage-lockout and resource-return assertions with BLE idle,
  BLE management active, LED off/heartbeat/Identify, and the bounded SoftAP
  fallback state selected by policy.
- Exercise only predetermined finite inhibited/simulated cases before any finite
  RF job. Provisioning writes remain rejected while RF is owned/armed/running.
- If finite RF is authorized, first establish a genuinely output-active state,
  cap jobs and RF seconds in advance, use accepted rows only for coexistence
  comparison, preserve failures and stop on timing,
  underrun, output-authority, memory, trust or restoration failure.
- Do not promote excluded Phase 11.6 rows or claim a new clock/mode/band. Any
  timing-path, allocator/layout or clock change triggers the documented wider
  revalidation instead of evidence reuse.

## Pass and stop rules

Pass only when every admitted assertion has identity-bound evidence, no secret
material entered the repository/evidence, all resource limits return within the
predeclared gates, superseded trust stays rejected and final output/network/
provisioning state is authoritative. Persistent noncredential state must be
preserved except during the separately confirmed full operational erase; that
case must record the intended clearing and subsequent authorized restoration
rather than being treated as preservation evidence.

An unexpected output-unknown state stops the procedure immediately. A predeclared
fault-harness output-unknown case may record only the expected fail-closed
rejection and then stops that case before any further operation. Unexpected RF,
wrong device/boot/image, storage ambiguity, trust resurrection, memory/stack/DMA
fault, unauthorized radio/trust action or exhausted finite budget also stops the
procedure. Preserve every failed attempt and restore only through the
preauthorized path.

## Required result artifacts

Retain a credential-free machine-readable result plus adversarial review locally
with the exact source/image/dependency/board/boot/configuration identities,
authorized budget, every attempt and failure, journal generations, resource
extrema, restoration evidence and the Phase 11 assertions considered applicable
or requiring repetition. Commit, push, publish or otherwise distribute those
artifacts only under separate explicit authority. Credentials, Wi-Fi secrets,
private keys, raw authenticated traffic and trust-store exports remain private
and out of Git.
