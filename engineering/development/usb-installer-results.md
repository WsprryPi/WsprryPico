# USB installer acceptance

Status: **accepted for the bounded USB installer slice**. Recorded main/devel
publication, anonymous bootstrap planning and cached Pi-adapter planning cover
installer 0.1.3. The 2026-10-19 public bootstrap upgrade additionally passes with
installer 0.1.4 on Pico C, including official picotool download, cleanup and
Fleet reconnection. Installation, preserving migration, recovery and erase
observations retain their stated source-specific limits.

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

Installer 0.1.4 adds prerequisite checks and an optional verified official
picotool download for supported native macOS/Linux hosts. Cleanup offers to
remove the managed package while retaining private backups and unresolved
recovery. Existing tools remain unchanged. The
[tool-download contract](standalone-tool-downloads.md) defines supported hosts,
consent, cache verification and retention; the physical check below qualifies
the recorded ARM64 host and board.

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
| Public Linux bootstrap upgrade, tool download/cleanup and Fleet reconnection | The [2026-10-19 end-to-end check](#public-bootstrap-upgrade-with-tool-download-and-cleanup) records installer 0.1.4 on wspr4/Pico C with an official ARM64 picotool 2.3.1 download. Upgrade to `0.1.0-ci.39324562626.1`, reserved-byte and saved-state verification, interactive cleanup and reconnection after restarting WsprryPi passed. |

No RF jobs were part of these installer observations. The full erase test's
private restoration image was a separate test fixture; erase itself created
no backup. The recorded web BOOTSEL handoff used the guarded USB fixture rather
than a physical unplug/hold/replug sequence.

## Public bootstrap upgrade with tool download and cleanup

**Passed on 2026-10-19.** This physical end-to-end check used wspr4, a Raspberry
Pi 4 running 64-bit Debian 13, Python 3.13.5 and curl 8.14.1, with 20 GiB free.
Pico C was a Pico 2 W / RP2350, USB serial `1545B6EFBF78028C`, device ID
`c2a3a2a314c948b50a8562a1aeb69669`, physical USB parent `1-1.3`. Its normal
firmware used the PIO/DMA GP2 engine; no RF job or clock measurement was run.

| Input | Tested identity |
| --- | --- |
| Public bootstrap/core source | `633228781ff85ec489d81a4e4a68a73129e7e185`, installer 0.1.4 |
| Bootstrap SHA-256 | `c6e50ab9bc26043ce7c5d72e173b35f56980aa0ab9d229f942bebde588b66614` |
| Installer core SHA-256 | `baa4585a3dda8eae030ededd24cbba395742a93f4ca747b4646d8d04e74d644b` |
| Before firmware | `0.1.0-ci.39261692018.1`, source prefix `b22549bf7370` |
| Installed devel firmware | [`0.1.0-ci.39324562626.1`](https://github.com/WsprryPi/WsprryPico/releases/tag/v0.1.0-ci.39324562626.1), source `c02e5d875dfdf2aa23e2220a95dd6ea7563adb4c`, verified [CI run 39324562626/1](https://github.com/WsprryPi/WsprryPico/actions/runs/39324562626) |
| Installed UF2 SHA-256 | `3575fb1c315557d1ffcb95d1fe4c6c9ec06338dd80f81f65389ff54ab472c261` |
| Downloaded tool | Official [`picotool-2.3.1-aarch64-lin.tar.gz`](https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.3.1-0), GNU 12.2.0 Release |
| Tool archive SHA-256 | `8cce5579c92e77c0439f34d4f49d37b1dc7d1e7c455233398f2e7b49599f67aa` |
| Tool executable SHA-256 | `9d5543b0218323751dce3946ae3390efa69ad9fd6600030e6ba265ffb2223a35` |

The tested bootstrap and core bytes match the 0.1.4 implementation published
from `e5dc075a9383fae6d8225b2e31af34e4654b5da6`; the core was independently
[verified and published by CI](https://github.com/WsprryPi/WsprryPico/actions/runs/39323109626).
Later documentation commits changed the resolved bootstrap source identity
without changing those executable bytes.

WsprryPi was confirmed ready with Pico C idle, unowned and output inactive,
then stopped for exclusive standalone USB access. Before/after snapshots and
hashes of existing private host files were retained. Pico C had no committed
standalone configuration and its unconfigured suspension was preserved.

The test ran the public pipeline below in a real terminal. The runner exported
`PATH=/usr/bin:/bin`, excluding the existing `/usr/local/bin/picotool` without
changing that executable. `TMPDIR` pointed to private test staging, and
`TEST_STATE_DIR` denotes the separate private state directory recorded below.
No `--picotool`, `--download-picotool`, `--device` or cleanup override was used:
the download, numbered selection and cleanup prompts were exercised.

```sh
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  | bash -s -- upgrade --branch devel --board pico2_w --yes \
      --state-dir "$TEST_STATE_DIR"
```

The first attempt ended with curl exit 28 during DNS resolution, before the
bootstrap started or firmware work occurred. After DNS resolution succeeded,
the repeated pipeline offered the official tool download. Accepting it verified
the archive and executable. Selecting menu entry 1 bound Pico C to USB parent
`1-1.3`. The installer resolved the latest verified devel image, entered guarded
BOOTSEL without a manual reconnect, verified a full same-board backup, programmed
and verified the image, checked retained storage and completed postboot admission.
Its final result was exit 0, `stage: complete`, `preserved: true` and
`recovery_required: false`.

Independent comparison confirmed the 4,194,304-byte backup's recorded hash and
byte equality across all 73,728 bytes at `0x3ee000..0x400000` in the pre-program
backup and programmed readback. Before/after public saved semantics matched:
configuration, progress fields/draft revision, hostname, frequency, saved
calibration, standalone watermark and suspension. All 47 pre-existing private
host files matched their original hashes.

Accepting cleanup removed the downloaded picotool, retained archive and support
files. No managed package or bootstrap temporary file remained. Only the small
private tool lock/state index remained, and the existing system picotool 2.3.0
was byte-identical. Firmware backups and transaction evidence remained private.

After `sudo systemctl restart wsprrypi`, the runtime reported the same USB
serial/device ID, the installed version, a ready USB session and management
connection, no maintenance/recovery requirement, no owner and inactive output.
The Fleet page showed the connected saved device and attached USB Pico C,
an idle device, the new installed version and automatically refreshed status.
The browser reported WsprryPi build `3.2.0-devel+8b7b7fe`. No application binary
or deployment was replaced for this test.

Private evidence remains on wspr4 at
`/home/pi/pico-public-upgrade-20261019.ZF6PyA5W/`, including the runner,
terminal transcripts, settings snapshots and verification report. The separate
state root is
`/home/pi/.local/state/wsprrypico-usb/public-curl-20261019-ZF6PyA5W/`;
transaction `1545B6EFBF78028C-zn8ua2pj` retains its valid full backup and readback.
Raw backups, snapshots, transcripts, captures and downloaded firmware/tools are
not included in Git. This check qualifies one ARM64 host/board upgrade and
reconnection; it does not exercise a configured standalone schedule, physical
power interruption, another host architecture or RF behavior.

## Validation so far

The installer 0.1.3 focused checks on 2026-10-19 pass:

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

For installer 0.1.4, 85 core, 35 prerequisite/download/cache/cleanup and six
publication tests passed on both macOS and the isolated wspr4 source snapshot.
The 126-test publication gate also passed in CI run 39323109626. The nine Pi
deployment and 19 compatible-distribution/recovery tests passed again. These
software checks are separate from the physical public-upgrade observation above.

Commands from the Pico root:

```sh
python3 -B tests/usb_installer_tests.py
python3 -B tests/usb_tool_download_tests.py
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

## Acceptance documentation verification

The end-to-end record was committed in
`a93ffcd6c9cb66f0ee967a1a4bae73019c8908de`. Its complete
[software/firmware CI run 39330079188](https://github.com/WsprryPi/WsprryPico/actions/runs/39330079188)
passed verification and publication, with 160 registered tests, zero failures
and zero skips. Read the Docs successfully built the same commit for
[devel](https://app.readthedocs.org/projects/wsprrypico/builds/35254589/) and
[latest](https://app.readthedocs.org/projects/wsprrypico/builds/35254590/).
No failure required an implementation change.

The [operator-manual publication](operator-documentation-results.md) is complete.
Current [installation](../../docs/install.md),
[backup/recovery](../../docs/maintain.md#usb-update-backups-and-recovery) and
[WsprryPi-host](../../docs/wsprrypi.md#standalone-installer-on-a-wsprrypi-host)
instructions cover public bootstrap use, interactive tool acquisition/cleanup,
bounded transaction history and service handoff. The recorded physical firmware
remains the exact `c02e5d8` image above; later documentation/CI commits do not
relabel it. Prerelease work remains a separate backlog item.

Final local documentation checks passed the strict Sphinx build, 93 Markdown
sources, 15 HTML pages and 1,174 local link/anchor targets. Ten companion
engineering-note links and anchors were checked against the current Pico
sources, built manual and existing Pi operator manual. Impeccable review of
installation, recovery and same-host handoff pages at 1280 × 720 and
390 × 844 found no layout issues. This documentation-only pass did not repeat
hardware or service operations.

## Acceptance limits

Acceptance covers the implemented installer contract, verified downloads and
the recorded physical paths. It does not qualify physical interruption or
power-cut recovery, every board/host combination, arbitrary downgrades, a
physical two-board menu/programming campaign, automatic A/B rollback or RF
quality. Current manifests admit CI testing images; no compatible stable image
is claimed. Windows and WSL USB operation remain unsupported. The 0.1.4 physical
check above qualifies its recorded standalone upgrade and Fleet reconnection;
it does not extend the other source-specific observations or replace the
application installed on the Pi.
