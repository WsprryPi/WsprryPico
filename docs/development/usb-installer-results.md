# USB installer acceptance

Status: **accepted for the bounded USB installer slice**. Main and devel images,
public installer 0.1.3, anonymous bootstrap planning and cached Pi-adapter
planning pass. Recorded Pico C installation, preserving migration, recovery
and erase paths retain their stated source-specific limits. This closeout loads
no firmware, operates no Pico, changes no host service and performs no RF tests.

## Delivered behavior

The standalone bootstrap and local CLI use the same Python installer as
WsprryPi's selected-USB-Pico controls. Firmware selection defaults to main;
devel, a specific CI version and developer builds require explicit selection.
A missing or incompatible image refuses without branch substitution or a build.
The canonical manifest, exact public assets, hashes, source tag and successful
CI provenance are checked before a programming transaction.

Installer 0.1.3 adds deliberate numbered device selection for interactive
install/upgrade commands. Piped bootstrap input stays separate from `/dev/tty`;
stdout remains one JSON result. Explicit serials bypass the menu. Imported Pi
execution and unattended/JSON-only commands still require a serial and never
prompt. The selected serial, mode and physical port are rechecked under the
device lock after image resolution, before creating a transaction.

Upgrades retain every byte from flash offset `0x3ee000` through `0x400000`
before reboot and compare public saved semantics afterward. Guarded maintenance,
verified same-board backups, FLASH_UPDATE boot admission and acknowledged finish
prevent an installer from silently taking ownership or releasing an uncertain
update. Verified older CI images have a disabled/unconfigured-schedule BOOTSEL
migration path. Recovery reuses the retained image and identity. Pi also retains
the exact installer; bootstrap recovery downloads its pinned original revision.
Full erase is a separate explicit operation covering all 4 MiB, with complete
blank comparison and no new credential backup. The [installer guide](usb-installer.md)
defines commands, privacy, retention and recovery limits.

WsprryPi's policy is installer contract 1 on the devel installer channel;
firmware selection remains independently main by default. Compatible installers
are resolved from published receipts rather than a Pi source pin. Checked images
and transactions retain their exact verified installer for offline recovery.
The companion source at `7d92c83a1517ef44b8b8b02c466ba0ba33daa405` includes this
integration, the recorded live web erase and reconciled documentation. Its
complete [non-hardware CI](https://github.com/WsprryPi/WsprryPi/actions/runs/39311888533)
passes. No companion implementation change is needed for installer 0.1.3.

## Recorded physical acceptance

These are existing board-specific observations, not new tests of every later
source or image. Raw flash backups and credentials remain private, outside Git
and served roots.

| Path | Identity and result |
| --- | --- |
| macOS initial CLI installation and verification recovery | Pico C, Pico 2 W / RP2350 A2 QFN60, USB serial `1545B6EFBF78028C`, device ID `c2a3a2a314c948b50a8562a1aeb69669`, USB location `34603008`. CI image `0.1.0-ci.39084514130.1`, source `582b7221b78537813e997b1be0c880dbadab0697`. Application programming, independent picotool verification, full readback, reserved-byte equality and postboot unconfigured state passed. Read-only recovery verified the programmed image without another write. |
| Linux/Pi preserving BOOTSEL migration and reconnection recovery | The [companion acceptance](https://github.com/WsprryPi/WsprryPi/blob/7b01762/docs/pico-usb-installer.md#validation-and-documentation-impact) records Pico C on wspr4 upgraded to `0.1.0-ci.39145255987.1`, source `f6ed8a208e2919a00b7ced044349fd45336f8760`. The full backup, reserved bytes, public saved state and exact new boot passed; the host maintenance hold cleared. Connection-only recovery retained that boot without reflashing. |
| Linux CLI/core full erase and repeated recovery | The [physical erase check](usb-installer.md#physical-erase-check) records Pico C on wspr4 USB parent `1-1.3`, picotool 2.3.0, original image `0.1.0-ci.39155533863.1` / source prefix `0a7c05d1c41b`. All 4,194,304 bytes populated with `0x5a` were erased and independently read back blank. A nonblank final byte failed verification; repeated erase recovery passed. Original full flash and saved semantics were restored and verified. |
| Deployed Pi web erase and restoration | The [2026-10-19 record](https://github.com/WsprryPi/WsprryPi/blob/8bfa1672a41098dba68c0ef60f23d042977d63a3/docs/development/pico-usb-erase-web-test-20261019.md) binds wspr4, Pico C, application/UI `8b7b7fee5dc334f753ec06b1b635108893967670`, published installer 0.1.1 / source `90bb95ebd054fa9084185e5ef9ed79528609c014`, and release `usb-installer-v1-devel-39249064224.1`. Production web preparation and continuation passed. Independent full-flash blank comparison and byte-identical restoration passed; the service returned ready, idle, unowned and output inactive. |

No RF jobs were part of these installer observations. The full erase test's
private restoration image was a separate test fixture; erase itself created
no backup. The recorded web BOOTSEL handoff used the guarded USB fixture rather
than a physical unplug/hold/replug sequence.

## Validation so far

The final-source focused checks on 2026-10-19 pass:

- 85 installer behavioral tests, including initial installation, guarded and
  legacy preserving paths, recovery, privacy/retention, rate limits, full erase,
  picotool compatibility, interactive selection and piped-terminal execution.
- Six independently published installer bundle/contract tests.
- WTP artifact validation: 23 schema, seven raw-JSON, one framing and eight
  transition cases.
- Pi deployment: nine tests; compatible distribution and retained recovery:
  19 tests. Firmware UI unit, polling, maintenance-safety and rendered browser
  integration checks pass. Desktop/mobile light/dark render checks report no
  overflow and pass button/recovery gating.
- Bootstrap Bash syntax, ShellCheck and both repositories' whitespace checks.

Commands from the Pico root:

```sh
python3 -B tests/usb_installer_tests.py
python3 -B tests/installer_release_tests.py
python3 -B scripts/validate_wtp_contract.py
bash -n scripts/install_usb.sh
shellcheck scripts/install_usb.sh
git diff --check
```

Commands from the Pi root:

```sh
python3 -B scripts/tests/pico_usb_deploy_test.py
python3 -B scripts/tests/pico_usb_bundle_test.py
node WsprryPi-UI/tests/wtp_firmware_test.js
node WsprryPi-UI/tests/wtp_firmware_polling_test.js
node WsprryPi-UI/tests/pico_firmware_safety_test.js
node WsprryPi-UI/tests/wtp_firmware_ui_integration_test.js
php -l WsprryPi-UI/data/views/wtp-controls.php
git diff --check
```

The local default Python lacks PyYAML and jsonschema, so its attempted
`tests/ci_bundle_tests.py` run did not pass. Both completed canonical Linux runs
pass that packaging suite with the hash-pinned dependencies, all 160 registered
CTest suites with zero failures/skips, WTP/browser checks, normal/inhibited/
compatibility firmware builds and identical-UF2 reproducibility. The public
manifests retain these results. No local macOS C++ compilation was attempted.

## Independent review

The independent read-only reviewer found that the initial menu patch discarded
the physical-port binding after selection. Image resolution could then admit
the same serial on another port. The repair retains the selected parent and
checks it under the device lock before transaction creation. New real-transaction
regressions cover movement, disappearance and mode change during resolution for
both install and upgrade, including a change from an unsuitable menu mode into
the operation's required mode. The original selected mode is retained as well
as the port. The reviewer independently reran all 85 installer and six
publication tests and confirmed that the port-binding finding is closed.

The reviewer also identified a lightweight-workflow coverage gap: bootstrap-only
changes were absent from its path filters. Both filters now include
`scripts/install_usb.sh`. The unfiltered canonical firmware workflow already
covered the installer through CTest. Review of the complete reconciled diff and
the mode/retention wording repairs cleared the implementation commit
`7b77485f92d02061016075552984ee7dd72f02ba` with no remaining actionable findings.
The reviewed full-diff SHA-256 values were
`04e1550d0bad3ebe358fdbbc5db874f5c626d7dd652e3c8ea3c24b4ff919e581` for Pico
and `964b8550b00444da79abd8fd0546930698ef08fc8d69c0c394963b7b8dc262cd` for Pi.

## Published acceptance

The operator-authorized fast-forward brought the canonical workflows into main.
Both branches built and published genuine branch-bound images from reviewed
source `7b77485f92d02061016075552984ee7dd72f02ba`:

| Channel | Accepted firmware | Complete canonical run |
| --- | --- | --- |
| main | `0.1.0-ci.39311922564.1` | [39311922564](https://github.com/WsprryPi/WsprryPico/actions/runs/39311922564) |
| devel | `0.1.0-ci.39311887375.1` | [39311887375](https://github.com/WsprryPi/WsprryPico/actions/runs/39311887375) |

Installer 0.1.3 was published independently from the same source for
[main](https://github.com/WsprryPi/WsprryPico/releases/tag/usb-installer-v1-main-39311922589.1)
and [devel](https://github.com/WsprryPi/WsprryPico/releases/tag/usb-installer-v1-devel-39311887550.1).
WsprryPi's production distribution verifier anonymously checked both receipts,
source tags, successful installer CI, complete assets and exact core/schema
bytes against the reviewed Git objects.

The public `curl | bash` bootstrap was checked against its committed source,
then run anonymously with `plan` and no branch option, and again with
`--branch devel`. Both returned installer 0.1.3, the intended branch/image and
successful exact-asset/provenance verification. WsprryPi's imported entry point
then revalidated both saved bundles offline using its verified devel-channel
0.1.3 installer. Both returned contract 1 and the same image identity.
These operations performed no device discovery, programming or settings write.

The [publication evidence](usb-installer-publication.json) retains immutable
release/run/source identities, receipt/manifest/UF2 hashes, test counts and
bootstrap/adapter results. These identify the accepted source and downloads;
later successful builds may advance the permanent branch bookmarks. The
evidence-only closeout does not relabel those firmware bytes.

## Acceptance limits

Acceptance covers the implemented installer contract, verified downloads and
the recorded physical paths. It does not qualify physical interruption or
power-cut recovery, every board/host combination, arbitrary downgrades, a
physical two-board menu/programming campaign, automatic A/B rollback or RF
quality. Current manifests admit CI testing images; no compatible stable image
is claimed. Windows and WSL USB operation remain unsupported. The current work
adds no new physical qualification and performs no live package deployment.
