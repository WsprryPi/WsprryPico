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

Adversarial review found two additional edge cases and repaired both before
reassessment. A diagnostic image with a core-1 flash reader must not run the
background BOOTSEL sampler; the automatic hold code is now excluded from that
image as well as the StandaloneRF worker image. A connected station on a
different SSID must not satisfy the reuse path; the active station SSID is now
checked. The second source assessment found no further actionable issue in
this slice. Physical long-hold, AP withdrawal/return, failed replacement and
phone save remain target gates.

Four browser tests, the host C++ build and all 98 host tests passed with the
installed Xcode SDK/compiler selected. The first host run used the broken
Command Line Tools `.tbd` linker and failed three unrelated compiler/link
fixtures; the Xcode rerun passed 98/98. The Pico 2 W Release target built with
the pinned SDK 2.3.1; the final clean-commit image and live result are recorded
separately in the [flash record](phase12-wifi-first-flash.md). Candidate A booted
the clean image with its saved profile and station address intact; two isolated
Pi scans did not see its AP while station Wi-Fi was healthy. These are bounded
source, build and target checks, not phone or manual-button acceptance.

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
