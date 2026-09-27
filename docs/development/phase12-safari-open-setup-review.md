# Immediate Safari setup source review

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
