# Immediate Safari setup source review

## 2026-09-28 long-hold incident and source repair

Status: **UNSAFE MANUAL BOOTSEL OPENER REMOVED; TARGET ROLL-FORWARD VERIFIED;
SAFE CONNECTED-STATION OPENING OPEN**. The operator reported holding BOOTSEL
for about 11 seconds without seeing the AP. A read-only `wspr5` check found
Candidate A's application USB serial absent, no answer at its previous station
address `192.168.1.47`, and one RP2350 USB bootloader enumerated. The later
serial-targeted ROM read bound it to Candidate A. This is consistent with a
reset while BOOTSEL was held, but the exact reset cause is unproven.

Source review found that the 100 ms background sampler returned from its
flash-safe callback after a short button sample, potentially resuming XIP
while the physical BOOTSEL button still grounded flash chip select. The
sampler, its manual-AP hold state, the single-sample USB diagnostic and its
obsolete probe script are removed. The linked-image topology check now
rejects a runtime sampler in both standard and core-1 diagnostic images.
Blank-profile startup and station-loss fallback are unchanged. A safe way to
open the AP while station Wi-Fi is healthy remains a product/target gate.

After this repair, the full Xcode host run passed 89/89 tests and the pinned
SDK 2.3.1 Pico 2 W RF-inhibited target linked with no runtime sampler or
core-1 reader. The clean committed image was then flashed as recorded below.

### Candidate A roll-forward after the long hold

The operator explicitly requested this reflash. Source `42ff62f832cd` on
`devel` produced UF2 SHA-256
`2c4319ad5c23645141617645d2a45059390b84627d21ad4efe524a597e4e9a4b`.
The same hash was checked after transfer to `wspr5`; the existing picotool
binary matched SHA-256
`4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`.
Serial-targeted ROM `picotool info -d` identified RP2350 QFN60 chip ID
`0x0bf4b4aec9ffb344`, binding the bootloader to Candidate A. A serial-targeted
`picotool load -v -x` loaded and verified the UF2 with `OK`, then rebooted the
application. Candidate B was not addressed.

The application USB serial `0BF4B4AEC9FFB344` returned. `INFO` reported
device ID `fd6127d11d6aca42a9905fa3fb1bf1d5`, revision `42ff62f832cd`,
consumer pre-clock profile generation 2, access generation 1, 150 MHz system
clock, RF-inhibited standalone simulator, Empty job state, inactive output,
no recovery boot and zero fault stage/PC/status. The station address
`192.168.1.47` answered from `wspr5`; `INFO` read it back with
`pool.ntp.org`. No physical button retry or AP-opening acceptance is claimed.
The newer image remains installed. With healthy station Wi-Fi, the AP is
normally withdrawn; a safe connected-station opening action is still open.

## 2026-09-28 AP lifetime and replacement-save review

Historical status: **SOURCE REVIEWED; CLEAN IMAGE BOOTED; PHONE ACCEPTANCE OPEN**. The
current [setup contract](phase12-safari-open-setup-revision.md) now starts the
open AP immediately only for an erased network profile. Saved network-only or
consumer profiles keep it off during a healthy station connection, return it
after 60 seconds without a usable station address, and withdraw it after 30
seconds of stable service once transactions and replies are clear. A 10-second
runtime BOOTSEL hold opens it until reboot in the idle, RF-inhibited,
core-1-absent image. The ready LED gives two short flashes every two seconds;
the Identify pattern gives three.

The previous replacement path called `start_network_only` while the existing
STA adapter still owned a UDP PCB. That returned failure before a new Wi-Fi
trial, explaining the reported unsuccessful save on a connected Pico. The
repaired path reuses a live station only when the submitted SSID/password,
current journal and active station SSID agree. Different credentials stop the
old station before trial and restore its credentials on a failed start, failed
join, cancellation or expiry. A repeated same-network save commits a distinct
request-bound journal generation without dropping the connection. The page
reports a missing terminal result as unverified, not as a proven failed save.

Adversarial review found two additional edge cases. A connected station on a
different SSID must not satisfy the reuse path; the active station SSID is now
checked. A diagnostic image with a core-1 flash reader must not run the
background BOOTSEL sampler. A subsequent source inspection found that the
first diagnostic exclusion guarded the claim platform declaration instead of
the background sampler. The guard now encloses the sampler, while claim
platform initialization remains available in every RF-inhibited build.
The standard and core-1 diagnostic target builds now both pass the BOOTSEL
topology check, which requires the runtime sampler only in the standard image
and rejects it in the diagnostic image.
Physical long-hold, station-loss AP return, failed replacement and phone save
remain target gates.

Four browser tests, the host C++ build and all 98 host tests passed with the
installed Xcode SDK/compiler selected. The first host run used the broken
Command Line Tools `.tbd` linker and failed three unrelated compiler/link
fixtures; the Xcode rerun passed 98/98. The Pico 2 W Release target built with
the pinned SDK 2.3.1; the final clean-commit image and live result are recorded
separately in the [flash record](phase12-wifi-first-flash.md). Candidate A booted
the clean image with its saved profile and station address intact; two isolated
Pi scans did not see its AP while station Wi-Fi was healthy. These are bounded
source, build and target checks, not phone or manual-button acceptance.

## Browser time and Wi-Fi time-server continuation (2026-09-28)

The Wi-Fi form now shows `pool.ntp.org` as an editable time server. The value
is included in the sealed setup payload, used for the station trial and saved
with the network profile. Existing version-1 network profiles load with that
default; new profiles serialize as version 2. A later station-details commit
preserves the chosen server. The 351-byte maximum plaintext and 745-byte
maximum JSON submit fit the new 768-byte route limit. The target rejects an
invalid server before it writes a profile.

The browser clock now uses `GET /api/bootstrap/v1/time` for a fresh Pico
monotonic challenge, then sends its UTC sample and challenge in the POST. A
challenge older than 200 ms is ignored. The 250 ms phone-clock allowance plus
the measured challenge age stays below the 500 ms job-clock admission limit;
another hint arrives about every 30 seconds while the page remains open.
SNTP and authenticated controller time still supersede browser time, and a
large browser-clock jump is rejected. This is an operator-selected clock
assumption, not a measurement of the phone's UTC error. The operational
SoftAP browser page and job controls are a later slice.

The repeatable `scripts/check_host.sh` and `scripts/build_pico.sh` source
`scripts/xcode_env.sh`, which selects the full Xcode compiler and SDK for
host fixtures and nested target-build tools. This removes dependence on the
broken Command Line Tools linker on this Mac. Field-GATT/1 remains a versioned
engineering interface; Bluefy is a historical client, and any resumed
consumer BLE client will be a dedicated iPhone app.

The first adversarial pass found two size paths left at the prior 512-byte
envelope: the shared HTTP parser would reject a valid long server name before
route validation, and the target receive callback assumed every pbuf fit a
1 KiB stack buffer. The parser now gives only the submit route 768 bytes, and
the callback feeds larger pbuf chains in bounded chunks. A streamed maximum
submit and 769-byte rejection are covered by host tests. The second pass also
found that the time-only POST inherited the idle credential-save gate. It now
accepts fresh clock observations while credential writes remain gated. The
SoftAP service lifetime during an operational job belongs to the later
offline browser-control slice.

The final source checks passed: four bootstrap browser tests, all 89 host
CTest cases through the Xcode wrapper, the pinned SDK 2.3.1 / Arm GCC 15.3.1
RF-inhibited Pico 2 W link, `git diff --check`, shell syntax, changed C++
formatting and changed-document relative links. The earlier failed host test
was its retained 513-byte rejection expectation; the updated parser boundary
and streamed maximum request passed before the final full run. These results
establish source and build behavior; no new phone or RF acceptance is claimed.

### Candidate A roll-forward (2026-09-28)

After source commit `f452044ac913` was pushed to `origin/devel`, a clean
RF-inhibited Pico 2 W build used the pinned SDK 2.3.1 checkout and Arm GNU
15.3.1. The UF2 SHA-256 was
`7325d639a2f35564009bfef34dcaeda0372ed0833cd6ab6bb769179252c442b9`.
The exact Candidate A USB serial `0BF4B4AEC9FFB344` and device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5` matched preflight. Its old revision
was `b14022c77319`; job state was Empty and output inactive. `picotool` found
the same RP2350 chip ID in BOOTSEL, loaded and verified the UF2, and rebooted
it. Candidate B (`CDDBF8767C506C07`) was not used.

Post-boot USB `INFO` reported revision `f452044ac913`, consumer pre-clock
profile generation 2, access generation 1, valid radio identity, 150 MHz
system clock, inhibited standalone simulator, Empty job, no schedules, no
active output and healthy storage. Station Wi-Fi had address `192.168.1.47`
and `pool.ntp.org`; UTC was synchronized from the station path. The newer
image remains installed. The captive time-server field, phone browser clock
exchange and infrastructure-free job operation have no new physical acceptance
in this record.

## Earlier automatic SoftAP browser time hint (2026-09-28)

The Wi-Fi and station pages now submit the browser's current UTC after their
first status read and about every 30 seconds while open. A busy/lost AP
connection retries the hint after five seconds. The AP-local endpoint accepts
only the exact identity-bound JSON request and uses a distinct provisional
browser time source. The review found that treating browser time like a trusted
observation could block or invalidate a later, correct SNTP sample. The
arbiter now gives fresh SNTP and authenticated controller observations priority
even when they disagree with the browser, and rejects a large jump between
browser hints. Browser time carries one second of uncertainty, exceeding the
job-arm limit, while consumer TLS generation still requires fresh SNTP.
Opening the page is required; AP association alone carries no client clock.

The browser tests cover first and periodic hints plus a lost-request retry;
host wire tests cover malformed and foreign-origin requests. The clock host
test covers bad dates, repeated hints, a bad jump, SNTP replacement and the
browser's inability to replace fresh SNTP. A target/browser time exchange is
still open and is not implied by the firmware build or later flash.

The first full host run found that mapping the new provisional source to a new
Field-GATT wire string would have changed the historical Bluefy artifact. The
field APIs now report that provisional source as `none`; their existing wire
values remain intact. The other failures in that first run came from the
Command Line Tools `.tbd` linker used by fixture subprocesses. With the
installed Xcode compiler/SDK selected and the field mapping repaired, all
98 host tests passed. The four bootstrap browser tests and the RF-inhibited
Pico 2 W Release cross-build also passed. This second adversarial assessment
found no remaining source issue in the browser-time slice.

## Later Wi-Fi-first revision (2026-09-27)

The earlier review below describes the superseded single-screen source. The
current source serves Wi-Fi fields and a password reveal control at
`/`, saves the network in its own encrypted transaction, and offers optional
station settings at `/owner.html` after Wi-Fi is saved. The captive window is
used when it supports the required cryptography; any capable regular browser
can use the Pico address. The current implementation does not require Safari.
The firmware trial restores the saved network on failure or slot expiry.
Browser requests have bounded timeouts, and a committed result with the wrong
request digest is reported as unverified rather than as this attempt's save.
An explicit repeat save of the same network now advances the journal
generation so it can be verified as a distinct transaction.
The browser and host checks for this revision must be read separately from the
older 111-test and physical-image results below; no new phone/target acceptance
is claimed by this note.

For this revision, four browser tests, all 103 host tests, the host build, and
a Pico 2 W target build with the pinned complete SDK passed. The host TLS case
needs localhost socket access: it failed at bind with `TLS start error -1`
under the restricted sandbox and passed in an isolated run with localhost
access. An older target build cache missing BTstack could not compile and was
superseded by the complete pinned SDK build. The resulting UF2 was later
[flashed and boot-verified on Candidate A](phase12-wifi-first-flash.md); no phone
flow was accepted by that delivery check.

Status: **SOURCE CANDIDATE REVIEWED; PHYSICAL ACCEPTANCE OPEN** (2026-09-27).
The current contract and execution brief are in the
[setup revision](phase12-safari-open-setup-revision.md). This review does not
close P12.8–P12.12 or authorize flashing Candidate A.

## Changed behavior

- The captive root and old page alias serve one form with Wi-Fi and station
  fields already visible. Optional Identify flashes the onboard LED. Save
  uses a fresh sealed request and shows a result only after exact generation
  and request-digest readback. Browser storage is not used.
- The same AP route accepts a later source-5 settings update from another
  phone. New profiles write owner epoch zero and no owners. Valid existing
  device TLS and station clients are carried forward. A failed station trial
  restarts the latest saved network configuration.
- The consumer image no longer admits the older BOOTSEL-gated network-only
  mutation. The open setup AP is requested while a network-only or source-5
  profile is selected, including after station loss. Local identity/status
  and the page do not depend on station association.

## Adversarial review and repairs

The first pass found a compressed P-256 browser key where the device expects
the canonical 65-byte uncompressed point; the browser now explicitly derives
that encoding and the test checks it. It also found a stale owner indicator
after a no-owner commit; status now checks the boot snapshot generation. The
older blank network-only POST still offered a separate BOOTSEL path; the
consumer image now refuses it and maps its page alias to the new form.

The second pass checked competing and expired slots, wrong source/generation,
one-use submit, station rollback and result reconciliation. It found that a
second source-5 save before restart could restore the boot-time network on
failure instead of the most recently saved network; rollback now reads the
current journal. It also found `claim_available` could stay true while a slot
or reconciliation was busy; status now reports availability only when those
states are clear. A further pass over these repairs found no additional
actionable source issue in this slice. The open-AP active substitution/relay
risk is an explicit operator choice, not an unresolved defect.

## Validation

- Browser bundle build and four Node browser/crypto tests passed, including
  immediate fields, optional LED, no phone storage, sealed submission,
  lost-reply polling and different-phone source-5 update.
- Host C++ build passed. The full serial `ctest` suite passed **111/111** after
  selecting Xcode's SDK/compiler and permitting the host-only TLS loopback
  bind. A configure-only certificate fixture was updated for its already
  required `x509write.c` source. Eight focused setup tests passed again after
  the final C++ changes.
- Pico 2 W/RP2350 Arm `WsprryPico` and `field_access_pico_linkcheck` linked
  with the retained SDK 2.3.1 and GNU Arm 15.3.1. This is a build result;
  no new image was flashed or run on a Pico in this revision.
- `clang-format --dry-run --Werror`, `git diff --check` and changed-document
  relative-link checks passed. The UI detector fell back to regex matching
  because its HTML parser packages are absent; it reported no findings under
  that reduced check.

## Remaining gates

The new image still needs a real iPhone captive-page save, optional LED
check, reboot/readback, different-phone update and station-loss field test.
A full consumer save currently requires fresh SNTP time after association;
a field network without time service can open the portal but cannot complete
that save. Resolve this before crediting field-day reconfiguration. Broader
TLS/client enrollment, resets, resource/concurrency/soak and restoration rows
remain open in the [Phase 12 roadmap](phase12-plan.md).

## Captive Wi-Fi result repair and two-board delivery (2026-09-28)

An iPhone captive page showed both “Could not start Wi-Fi setup” and
“Connection not saved” after the Pico joined infrastructure Wi-Fi and withdrew
its setup AP. Source commit `9693c59c19245d510e1f75811861b37cc6616b41`
separates an accepted `/api/bootstrap/v1/submit` reply from the later durable
save. An accepted reply now displays “Wi-Fi settings accepted,” explains that
setup Wi-Fi will close and the captive window should close, and keeps that
result visible when the AP disappears. A lost submit reply reports an
unconfirmed result;
an interrupted start no longer claims the connection was not saved. A status
poll started before the POST cannot clear the pending attempt. Exact request
digest and generation readback still control the saved/connected result, and
an explicit failed reply still reports failure.

The adversarial reassessment found that “Back to Wi-Fi settings” after a
failed initial identity read could open a form unable to submit. Commit
`2bde30bd1128197c66f84bcef4b9cc0116016c08` makes the interrupted-page
action reload setup, allowing a fresh identity and generation read. The
affected browser and host tests passed again after this repair.

The four browser/crypto tests passed, including AP withdrawal, lost reply,
stale poll, confirmed failure and exact saved readback. Five affected host
bootstrap tests passed; the Pico 2 W/RP2350 Arm secure Release image built
from a clean worktree at the final commit using pinned SDK 2.3.1 and GNU Arm
15.3.1.

The standard image is RF-inhibited and reports the
`inhibited-standalone-simulator` engine. The first `9693c59` image (UF2
SHA-256 `6d10d58605a416897e99953c96714d81f12c06ab5af98622c2030dcb8c85dee7`)
was flashed and verified on both boards, then superseded by the final clean
`2bde30b` image. The final 3,317,760-byte UF2 SHA-256 was
`f2b8dd678ecee11b69f72eeb6bfc707feb302bc3d6ce76b0f67ad591b8632a47`;
the copy on `wspr5` matched. The existing Linux picotool SHA-256 was
`4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921`.

Both boards were USB idle with output inactive before the flash. Candidate A
had USB serial/ROM chip ID `0BF4B4AEC9FFB344`, device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`; Candidate B had USB serial/ROM chip
ID `CDDBF8767C506C07`, device ID
`29f20b7342051ef947aa56cb9d4fab42`. Each serial-targeted
`picotool load -v -x` verified `OK`, rebooted, and returned USB `INFO` with
final revision `2bde30bd1128`, a new boot ID, 150 MHz system clock, empty job
state, inactive output, valid core-0 stack guard and no fault. A retained its
consumer pre-clock generation-2 profile, synchronized UTC, station address
`192.168.1.47`, and Plain LAN listener on TCP 31417; a TCP connection passed.
B remained unprovisioned at generation 0 without a station address or LAN
listener, and its UTC clock was unsynchronized. Final boot IDs were
`669f7ce38fe85857711f146336b4bab3` for A and
`140ee5b5b32127246771130af007675d` for B. The final image remains on
both boards.

This delivery verifies the image and readback. The updated iPhone result page
has not yet been retested physically; an accepted POST is not itself proof of
a durable save, and the captive window is controlled by iOS after AP withdrawal.

## First blank Candidate A iPhone save attempt and stack repair (2026-09-28)

The operator joined Candidate A's open setup AP, opened `192.168.4.1` manually
after iOS did not open a captive window, and verified the password reveal
control. After Save, the page showed “Could not start Wi-Fi setup” and “Setup
interrupted”; the AP disconnected. USB readback on Candidate A
(`0BF4B4AEC9FFB344`, device ID ending `1bf1d5`) showed source
`unprovisioned`, profile generation 0, no station address and unsynchronized
time. The Wi-Fi settings were not saved. Its new boot reported recovery mode,
watchdog stage 13 (network poll) and CFSR `0x00100000` (stack overflow). The
access journal had reached generation 1 during `/api/bootstrap/v1/start`.
The recorded fault proves a stack overflow in that network-poll interval; it
does not identify one exact C++ instruction.

The access journal's slot scan previously placed a 4096-byte image on the
primary stack during the HTTP callback. It now reads 256-byte pages and
preserves detection of a partially written middle page. The standard
RF-inhibited image reserves a 32 KiB primary stack (28 KiB above the existing
4 KiB guard), and the ELF memory-layout check enforces that bound. The host
suite passed 89/89 tests, including the access-journal interrupted-write and
read-size assertions. The pinned Pico SDK 2.3.1 cross-build, linked-image
memory and flash checks, and `git diff --check` passed.

The repair candidate is a source-dirty `c13fc1681974-dirty` RF-inhibited
image, UF2 SHA-256
`7e7bbbfe6b868f022310f27590cc95c14068c7e4cad92392086e491cd59804f5`.
Serial-targeted picotool verification loaded it on erased Candidate B
(`CDDBF8767C506C07`) first. From isolated `wspr5` `wlan2`, B returned an
Apple captive redirect, the immediate Wi-Fi form, and a 200 response to a
credential-free `/api/bootstrap/v1/start`. USB then showed the same boot ID,
no recovery fault, healthy access generation 1, unprovisioned profile
generation 0 and inactive output. The first Pi HTTP attempt was invalid
because another process deactivated `wlan2`; NetworkManager recorded a
`user-requested` disconnect, and the immediate connected retry passed.

The same image was then verified on Candidate A. It booted out of recovery
with its prior healthy access generation 1, still unprovisioned at profile
generation 0, no station address, no fault and inactive output. A separate
isolated-Pi check received a captive DNS A answer of `192.168.4.1`, an Apple
probe 302 redirect to the local page, and a 200 root page containing Wi-Fi
fields, the password eye and `pool.ntp.org`. The temporary Pi Wi-Fi profiles
were removed. Neither Pi check establishes that iOS will automatically open
the captive window. A new iPhone save, accepted result message, durable
generation 1, station connection and time sync remain to be verified.

## Adversarial reply-order repair and second target check (2026-09-28)

Review found that `/api/bootstrap/v1/submit` started the station connection
inside its HTTP callback, before the `checking` reply reached the browser.
That could remove the AP while the page still waited for the reply. The
station trial now starts at least three seconds after the full accepted reply
is delivered and the HTTP client has closed. A lost or partial reply cancels
the pending trial; a normal client FIN after reading the complete reply keeps
it. The initial Candidate B dummy trial exposed the latter close-path error:
its 200 `checking` reply reached the Pi, but its slot was immediately cleared.
The close handler was repaired and retested.

The final source-dirty RF-inhibited candidate UF2 SHA-256 is
`866661bcb1b008a0bca03bb12e6dabfcbfe0d5711ffb44215d2f86bf7076524b`.
It passed the pinned Pico 2 W cross-build, linked stack and flash checks,
89/89 host tests, 4/4 browser tests, formatting of the changed server files
and `git diff --check`. Serial-targeted picotool loaded and verified this image
on Candidate B before Candidate A. The second B dummy encrypted transaction
used a deliberately nonexistent SSID and temporary password. It returned a
200 `checking` reply with the matching request digest in 239 ms. The AP
returned status immediately and one second later, both with a trial slot and
profile generation 0. After the three-second display interval, USB showed
station activation, unchanged boot ID, no recovery fault and inactive output.
After the failed network trial timed out, both boards remained unprovisioned
at profile generation 0 with no station address, no fault and unsynchronized
time. Their access journals were healthy at generation 1 from the setup-start
probes. Candidate A final boot ID was `4ab68d160ffa92a0b3fe981ce39c0085`;
Candidate B was `93c28d1d67bdec5ca8784a9ef094599f`. Isolated `wspr5`
`wlan2` was disconnected and its temporary AP profiles removed.

This proves an accepted HTTP reply can reach a client before a station trial
starts on the final image. The dummy SSID cannot qualify a successful Wi-Fi
save or time sync. The iPhone captive auto-open, page acceptance message,
generation-1 commit, station join and SNTP readback remain open until a fresh
phone run on Candidate A.

An optional `WsprryPico-StandaloneRF` cross-build was attempted separately.
It stopped while compiling that target's `main.cpp` because `btstack.h` was
not found, before the changed bootstrap server compiled for that target. The
standard RF-inhibited image used above built and linked successfully.

## Candidate A iPhone retry and station readback (2026-09-28)

The operator reported that the iPhone retry appeared to work, but thought the
SoftAP remained up. A serial-bound USB readback on Candidate A
(`0BF4B4AEC9FFB344`) showed the final image booted without a recovery fault,
source `network_only`, durable profile generation 1, healthy access generation
1, station link up at `192.168.1.47`, `pool.ntp.org` selected, one accepted NTP
observation, a synchronized clock and inactive output. Candidate B
(`CDDBF8767C506C07`) remained unprovisioned at profile generation 0 with no
station address. An isolated `wspr5` Wi-Fi scan saw only
`WsprryPico-0a9d89`, Candidate B's AP; Candidate A's
`WsprryPico-0a60df` AP was absent. The apparent remaining AP is therefore
consistent with B still being blank. The operator's exact iPhone SSID and
post-Save page message are being confirmed. The earlier report that the
captive page did not open automatically remains an unpassed phone gate.

## Candidate B iPhone failed join and retry (2026-09-28)

The operator joined blank Candidate B's `WsprryPico-0a9d89` AP, submitted the
home SSID with a deliberately wrong password, saw “Wi-Fi settings accepted,”
and found the AP still available. Serial-bound USB `INFO` then reported device
`29f20b7342051ef947aa56cb9d4fab42`, revision `c13fc1681974-dirty`,
source `unprovisioned`, profile generation 0, no station address, no recovery
boot and zero provisioning/fault status. This bounds the negative result: the
accepted HTTP reply was not a durable save.

The operator's next attempt used the correct password but displayed “Setup
interrupted” on a page whose styling had not loaded. A subsequent retry
worked. Candidate B then rebooted to boot ID
`03d7e43e3859aa743830f1881141cfb2`; USB `INFO` reported source
`network_only`, durable profile generation 1, station address
`192.168.1.53`, `pool.ntp.org` resolved with one accepted NTP sample, a
synchronized clock, Plain LAN WTP ready, inactive output and zero reported
provisioning/fault status. This is the first real-phone failed-join/retry and
successful network save on B. The operator has not confirmed automatic captive
opening on B or the exact final success page.

Source inspection found a plausible cause for the second-attempt interruption:
an active trial or the failed trial's retained terminal slot makes
`/api/bootstrap/v1/start` return HTTP 409, which the page formerly rendered
as a generic interruption. The phone session has no HTTP capture, so the
precise cause is not proven. The staged repair automatically retries a busy
start for up to about two minutes while keeping the submitted form active.
It preserves the previous attempt's terminal result for its original page.
It also embeds the setup
CSS in the HTML response with a matching CSP hash, so a separately dropped
stylesheet request cannot leave that page unstyled. Four browser tests and
89/89 host tests pass, including a busy-start retry and the inline style/CSP
checks. A clean target directory built the standard RF-inhibited Pico 2 W
image against pinned SDK 2.3.1 and GNU Arm 15.3.1; UF2 SHA-256 is
`be35c3001de223adfef9d711d39d43edc371ec71f74d6ba37a9075371b66cd11`.
The first target build attempt used a stale cache that mixed SDK paths, and
a subsequent build without the Xcode environment failed in the nested host
linker. The clean pinned configuration with the repository's Xcode wrapper
built successfully. This new image has not been flashed; B's physical result
remains evidence for the preceding `c13fc1681974-dirty` image.

Adversarial review rejected an initial source change that would have cleared
the failed terminal slot immediately: another open page could then lose its
failure result. That change was removed. The final browser retry waits for
the retained slot to expire; the four browser tests, affected bootstrap HTTP
host test, pinned target rebuild, C++ formatting check and `git diff --check`
passed again after the correction.
