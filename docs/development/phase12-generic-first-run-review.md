# Phase 12 generic first-run: adversarial review and reassessment

Status: **bounded source and Candidate A first-run acceptance passed**. This
review covers the [execution prompt](phase12-generic-first-run-execution-prompt.md)
and [exact physical result](phase12-generic-first-run-physical-result.md).
Phase 12 and the Wi-Fi-only credential flow remain open.

## Findings and repairs

| Adversarial finding | Repair and verification |
| --- | --- |
| An erased profile journal selected `Factory` even when the generic image had no compiled device bundle. | Runtime source selection now treats an exactly erased generic journal as unprovisioned generation zero. Host coverage and the full-erase Candidate A check passed. |
| A first source write interrupted after programming payload, before header/commit, could look like an erased slot. | Journal scanning checks the entire payload area when both markers are erased. A partial first write fails closed; an older valid record remains eligible after an incomplete inactive write. Failure-injection tests passed. |
| Merely checking a bundle's port or the permissive deployment helper could classify incomplete, IP-only or wrong-device build metadata as matching. | A portable classifier requires a full device ID, local hostname, bounded port and nonempty certificate, key and CA. Generic, matching, partial and wrong-device cases are tested. |
| The activation adapter reloaded a profile using the old runtime signature. | It explicitly supplies the no-bundle value for the already committed runtime profile. The Pico 2 W image and field-access linkcheck linked. |
| Empty TLS metadata could make the generic diagnostic report a matching deployment; a runtime profile fault could still request an unusable provisioned AP. | The boot path requires nonempty device/hostname/port for deployment match and a successfully loaded runtime source before starting the provisioned AP. Target readback reports no deployment match or TLS listener. |
| Concurrent serial reads after the final flash produced one host-side timeout and one nonblocking read error. | The reads were repeated serially through the identity-bound Console helper and passed. The concurrent reads are discarded as a test-harness error, not device evidence. |

## Verification and second assessment

- `provisioning_tests`, `field_access_tests` and `bootstrap_http_tests` passed
  (3/3 focused CTest cases). The provisioning and network transport contract
  scripts passed. The standard RF-inhibited `WsprryPico` and
  `field_access_pico_linkcheck` linked against the pinned SDK and Arm toolchain.
- The selected Pi observed a true full-erase generation-zero boot, open AP,
  DHCP, AP DNS, redirect, read-only page, POST rejection and preserved
  generation-zero state after reboot. The comparator was untouched and the
  isolated host Wi-Fi profile was removed.
- Source and documentation were reassessed after the last repair. There is no
  remaining actionable defect in the bounded generic first-run/read-only path.
  A matching compiled bundle, wrong-device compiled bundle and power-cut cases
  have deterministic source tests; they were not exercised as separate live
  builds. The new browser credential and AP/STA path still requires the
  separately approved design and target acceptance.

The prior `build-host` cache pointed at Apple's Command Line Tools SDK, whose
TAPI linker rejected `arm64e.x1` entries. Focused host checks used the existing
Xcode 26.5 SDK build directory. The prior Pico target cache pointed at a
removed SDK directory; a fresh target directory used the pinned SDK checkout.
These build-environment issues did not change source or target evidence.
