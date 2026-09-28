# Immediate Safari setup source review

## 2026-09-28 AP lifetime and replacement-save review

Status: **SOURCE REVIEWED; CLEAN IMAGE BOOTED; PHONE ACCEPTANCE OPEN**. The
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
