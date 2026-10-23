# USB installer

The shared installer is `scripts/usb_installer.py` (version 0.2.0). It runs with
Python 3.10 or newer and its standard library on macOS and Linux. Windows and
WSL USB operation are unsupported. Integrity checks bind downloads to their
source and CI provenance; physical behavior remains scoped to identified boards.

## Operator instructions

The canonical [installation/update guide](../../docs/install.md) and
[recovery/erase guide](../../docs/maintain.md#recovery-and-reset) describe current
operator actions. This document retains installer contracts, implementation
boundaries and physical acceptance scope.

## Full flash erase contract

The explicit erase operation removes all 4 MiB of external flash, verifies every
byte against `0xff`, leaves BOOTSEL active and creates no credential backup.
Immutable ROM, chip identity and OTP are outside external flash. Same-board
serial/port/chip checks, durable intent and retry behavior remain shared with
the transaction implementation. A failed or interrupted check is unresolved.
Existing host backups remain retained.

The deterministic erase checks include identity/port, explicit confirmation,
uniform/blank flash, full-range comparison, a nonblank last byte, interruption,
recovery and preservation of existing backups. Reproduction commands remain in
[the development guide](README.md).

### Physical erase applicability

The bounded CLI/core erase observation is Pico C / Pico 2 W / RP2350 on wspr4,
USB `1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`, USB parent
`1-1.3`, USB-enabled picotool 2.3.0 and installer SHA-256
`f568a1abb1452c250ee3ffc9361005e1d9d72c8c2fd8b5a65e25f02b5a9a15f0`.
The original image is `0.1.0-ci.39155533863.1`, source `0a7c05d1c41b`, with no
configured standalone schedule. This observation covers an independently
verified 4,194,304-byte blank readback after a full `0x5a` fixture, rejection of
a nonblank final byte at `0x103fffff`, and successful repeat erase recovery.
The all-`0xff` SHA-256 is
`cd3517473707d59c3d915b52a3e16213cadce80d9ffb2b4371958fb7acb51a08`.
Restoration was verified across the original 4 MiB and saved semantics. Physical
power-cut/disconnect cases, the live Pi web route, other boards and RF behavior
are outside that observation. Current installed firmware is not asserted.

## Image selection and planning

Beta testers select the published Beta 1 firmware with `--version 1.0.0-beta.1`, independently of the checkout, bootstrap or WsprryPi branch. No `--branch` option is required. An explicit `--version` selects the exact semantic tag and bypasses the CI branch bookmarks. `--stable` selects GitHub's latest full release and requires a final semantic version; it excludes betas. These selectors require a published compatible bundle and do not publish or create one. No final release is currently published.

Without an explicit version or another image selector, the firmware branch defaults to **main**; `--branch devel` selects devel explicitly. CI resolution requires the corresponding published `ci-main` or `ci-devel` bookmark and its exact public version release. Neither bookmark is currently published. A missing bookmark, missing assets, incompatible manifest or failed provenance check causes refusal; another branch, older image or compilation is never selected implicitly.

Output directories must be new. `--bundle DIRECTORY` revalidates a previously saved public bundle without another download. It cannot accompany another image selector. `recent_ci` reports additional run status separately from the immutable selected image. Missing or invalid downloads still cause refusal.

The ordinary path uses anonymous HTTPS and needs no Git, compiler, SDK or
GitHub account. A saved successful verification receipt remains usable after
Actions retention expiry when the public release and exact hashes remain intact.
HTTPS/repository ownership is the distribution trust boundary; checksums are
integrity checks, not signatures.

Beta/final manifests use the `release` artifact stream, exact tag workflow ref
and `prerelease`/`stable` channel. The shared standard-library policy in
`usb_installer.py` is also imported by CI. The manifest schema remains version 1
and uses the existing bounded schema interpreter. The independently distributed
installer still consists of its manifest, Python core and canonical schema;
no additional runtime module or companion-repository change is required.
Firmware major version grants no new storage compatibility. Existing flash
boundaries, same-board backups, settings readback, upgrade and recovery guards
apply to CI, beta and final images. Pending transactions retain their original
installer version and immutable bootstrap revision; resume them with that
recorded installer rather than substituting a new core.

GitHub API rate limits are reported separately from a missing branch bookmark,
permission failures and connection errors. Refusals include the HTTP status and
an earliest retry time in UTC, using GitHub's `X-RateLimit-Reset` and
`Retry-After` headers. If both apply, the later time is used. Missing or invalid
retry guidance requires at least a one-minute wait, identified as a minimum
rather than a confirmed quota reset. The result includes
`error_code: github_rate_limited` and `retry_at` in Unix seconds. The installer
does not retry requests automatically or load GitHub credentials. A rate limit
on optional additional-run status leaves the verified selected image usable and
reports its reason separately in `recent_ci`.

## Installer source distribution

The standalone bootstrap fetches the Python installer and firmware-manifest
schema from one immutable source revision. WsprryPi selects the configured
main/devel branch head only after its canonical `software-build.yml` run and
verification job have succeeded. It downloads both files through GitHub's
Contents API at that SHA, checks Git blob identities, and stores their exact
sizes, SHA-256 hashes, source and verification receipt in private storage.
A pending or unavailable check retains an already verified installer; a fresh
client waits for successful verification. No separate installer releases or
release tags are required.

Installer contract 1 retains `wsprrypico-usb-result/1`,
`wsprrypico-usb-transaction/1`, firmware-manifest schema 1 and Python 3.10+.
Installer implementation versions are independent of firmware image versions.
Firmware is downloaded as a compiled UF2 from a separately verified firmware
release; the operator's machine does not compile it.

Checked image plans and transactions retain their exact installer and schema.
Recovery uses those local bytes offline, including existing contract-1 receipts,
and never substitutes the current branch implementation. Pi cache budgets span
installer versions and preserve unresolved recovery transactions.

Hardware-free checks:

```sh
python3 -B tests/usb_installer_tests.py
python3 -B tests/usb_tool_download_tests.py
```

Physical interruption/power-cut recovery, arbitrary downgrades, every board/host
combination and RF quality remain unqualified. Windows and WSL USB operation
are unsupported. Software checks do not establish physical recovery success.

## USB dependency and device selection

Programming accepts **picotool 2.3 or newer within the 2.x series**, including
the public [2.3.1 release](https://github.com/raspberrypi/picotool/releases/tag/2.3.1).
The installer checks the version, USB support and the command options needed for
identity, backup, programming, verification and erase. Older versions, prereleases,
3.x versions and builds without the required capabilities are refused. USB is a
normal picotool capability; builds without libusb cannot access a connected Pico.
The exact executable version and SHA-256 are recorded for each transaction.
It accepts an explicit `--picotool /absolute/path/to/picotool`. The standalone
entry can offer an official, size/SHA-256-verified picotool 2.3.1 download when
no compatible executable is available. Its private cache, consent, extraction,
recovery retention and cleanup contracts are described in
[standalone tool downloads](standalone-tool-downloads.md). The imported Fleet
entry never downloads or removes tools. Neither entry installs system packages
or acquires an SDK, and the bootstrap must run as an ordinary user.

Discovery binds USB serial and physical parent. Application CDC roles are
Console interface 0, WTP interface 2 and management interface 4; macOS places
serial clients under their paired data interfaces. Tty suffixes are not roles.
BOOTSEL identifies RP2350, so `--board pico2_w` explicitly confirms the board's
wireless hardware. Re-enumeration must retain the serial and physical port.

Interactive device selection and initial BOOTSEL use are documented in the
[operator guide](../../docs/install.md). The installer rechecks selected serial,
mode and port before creating a transaction and under the device lock. Only the
selected Pico is programmed.

Install/upgrade mode admission precedes picotool preparation and image resolution, including explicit-device and imported calls. BOOTSEL upgrades return `error_code: device_mode_mismatch`, the serial and expected/observed modes, with first-install, running-application and retained-transaction recovery guidance. A mode mismatch never changes the selected operation. Device identity, mode and port are checked again under the transaction lock after image resolution.

The standalone entry renders progress and results for a terminal when both output streams are terminals. Imported calls, redirected standard output and `--json-only` retain the single `wsprrypico-usb-result/1` JSON response. `--json-only` disables device-selection, tool-download and cleanup questions and BOOTSEL guidance. Progress describes actual transaction stages; completion requires the existing flash and application checks. Preflight refusals do not create recovery work; cleanup independently checks all retained transaction records before removing a managed tool.

## Preserving upgrade and recovery


An ordinary upgrade starts in the running application and takes its own fresh
USB snapshot. It refuses active, owned, uncertain, faulted or configured STOP
state. It never sends STOP, claims RF ownership or changes saved settings to
obtain admission. Firmware must provide guarded USB maintenance, and the target
manifest must declare `usb_maintenance: 1` and `postboot_verification: 1`.
For verified older CI firmware without this operation, upgrade prepares a
settings-preserving BOOTSEL migration and returns `awaiting_bootsel` with a
private transaction path. It writes no firmware and sends no reset or STOP.
The saved standalone schedule must already be disabled or unconfigured; the
installer does not change that setting. An unconfigured board's automatic
suspension remains intact.

When prompted, unplug the selected Pico, hold BOOTSEL while reconnecting it to
the same physical USB port, then release BOOTSEL. Run `recover` with the
returned transaction path (or choose **Continue after BOOTSEL** in WsprryPi).
The standalone flasher prints a ready-to-run continuation command on stderr.
Copy that command after reconnecting; it supplies the actual transaction,
selected USB serial, board confirmation, `--yes`, picotool and private state
directory. Paths are shell-quoted, including paths containing spaces or quotes.
The command uses the retained image without repeating image selection. A
failed pending continuation repeats the reconnect guidance and command;
preparation and failed continuation are not completed installation.

If programming fails after backup and compatibility checks, the flasher
identifies the incomplete installation and prints a BOOTSEL recovery command.
Leave a Pico already in BOOTSEL connected. A failure during postboot
verification instead asks to keep the Pico connected and prints a verification
retry command so an existing maintenance hold can be verified on the same boot.

For a piped `install_usb.sh` invocation, the continuation downloads the same
immutable installer revision and works after the initial temporary directory
has been removed. Its `WSPRRY_PICO_USB_INSTALLER_REVISION` value pins installer
source only; firmware selection and the cached transaction remain separate.
The bootstrap validates this value as a full lowercase commit SHA. Run the
printed command as the same ordinary user, with the same USB permissions.

Continuation revalidates the checked target, installed CI receipt, preflight,
USB serial, physical port and RP2350 chip ID. It completes a verified full-flash
backup and checks the old application bytes against the identified CI image
before authorizing programming. It applies the same reserved-storage and
postboot semantic checks as a guarded upgrade. A wrong board, changed image,
incompatible reserved storage or failed backup refuses without programming.
Ordinary updates use no 1200-baud reset, forced takeover, mass erase or settings transplant.

The pending transaction survives host and browser restarts. Keep the Pico idle
and do not edit its settings during the reconnect. Starting `recover` before
BOOTSEL is ready leaves the pending transaction available for another explicit
attempt. The Pi keeps this member paused until verification and reconnection
complete; it never treats the preparation result as a completed installation.

The acknowledged preflash hold excludes WTP admission, standalone slot/watermark
reservation, application writes and provisioning commits. A verified full-flash
same-board backup precedes programming. UF2 validation checks exact normal
RP2350 blocks, numbering, flags, contiguous ranges, sector-rounded erase extent
and the pinned E10 workaround. Picotool skips the validated workaround block;
all bytes from offset `0x3ee000` through `0x400000` must read back unchanged before
boot. This preserves the superset of saved progress, diagnostics, access/bonds,
profiles, standalone configuration/watermarks, NTP learning and boot reservation.
It does not add an OTA partition.

The verified image launches using picotool's FLASH_UPDATE boot. Supporting
firmware holds standalone scheduling and mutating admission until fresh USB
identity/version/source and public saved semantics have been verified and a
matching finish request is acknowledged. The host records release intent before
sending it. A lost acknowledgement is ambiguous; same-boot recovery can inspect
the actual hold rather than blindly replaying a reset or programming operation.
A later normal power-on can follow the device's existing saved enablement;
there is no persistent A/B rollback or guarantee of a hold across power loss.
Installation does not qualify RF or enable a disabled schedule.

Host transactions and full-flash backups contain credentials and bonds. They
stay outside Git and served roots, under owner-only
`~/.local/state/wsprrypico-usb` or `/var/lib/wsprrypi/pico-usb`. Symlink ancestors
are refused. Before a new transaction, prior successful history is pruned to
two records and unchanged/refused history to eight, dropping either after
seven days. Pruning runs only on invocation, and the new transaction can add
one record. Eight unresolved records block new work rather than deleting
recovery evidence. Device locks serialize installers and the
optional Pi runtime. Recovery revalidates the exact cached image, backup,
serial and physical parent. It does not transplant banks, blindly restore
flash, erase saved state or promise arbitrary downgrades. If backup never
completed, a record is not authority to program: inspect the unchanged image
and perform deliberate BOOTSEL recovery.

Results are JSON `wsprrypico-usb-result/1`. Exit 0 means the requested operation
completed or prepared an `awaiting_bootsel` continuation. Only `complete`
establishes finished installation. Exit 2 is refusal/failure before ambiguous programming, and 3 means a
retained transaction needs recovery. Cancellation within a transaction retains
its last durable stage. Failed transactions also retain `failure_reason` in
the private record. A successful tool process or USB appearance is
insufficient for upgrade success.

## wspr5a preserving-upgrade hardware observations

Two physical same-image upgrades passed on 2026-10-23: one with the existing unconfigured state, and one with non-default saved settings and a disabled standalone schedule. Both used the same identified Pico and the updated standalone installer. The observations describe the recorded setup and state at completion.

| Setup | Recorded identity |
| --- | --- |
| Host | `wspr5a`, user `pi`, Linux AArch64, kernel `6.18.50+rpt-rpi-2712`, Python 3.13.5 |
| Board | Pico 2 W / RP2350 |
| USB serial and physical parent | `1545B6EFBF78028C`, port `3-2` |
| Firmware device ID | `c2a3a2a314c948b50a8562a1aeb69669` |
| Installer | 0.2.0, commit `1b8d51b22365b6d183029862cad56918067a1590` |
| Installer SHA-256 | `c2d609c706b71dac9d9bb79b3e77f3adcde1daa88265ef712ca212112853d2d3` |
| Firmware before and after | `0.1.0-ci.39953536554.1`, source `3ffd65ec5c0c9856739dd5707f1df9716aace5ee` |
| Engine and image clock | `pio-dma-gp2`; 138,000,000 Hz from the verified firmware manifest |
| Programming tool | USB-enabled picotool 2.3.1, Linux GNU-12.2.0 Release |
| Picotool executable SHA-256 | `9d5543b0218323751dce3946ae3390efa69ad9fd6600030e6ba265ffb2223a35` |
| Control and terminal | USB CDC management, guarded BOOTSEL and FLASH_UPDATE verification boot; both output streams attached to a real 100-column controlling PTY |

The remote checkout remained clean at the firmware source above; the bootstrap downloaded the pinned installer without updating that checkout. Both runs used this command from `/home/pi/WsprryPico`, with no download-consent or cleanup override:

```sh
WSPRRY_PICO_USB_INSTALLER_REVISION=1b8d51b22365b6d183029862cad56918067a1590 \
bash scripts/install_usb.sh upgrade --branch devel \
  --version 0.1.0-ci.39953536554.1 --device 1545B6EFBF78028C \
  --board pico2_w --yes
```

Picotool was absent from `PATH`. Both runs automatically verified and reused the retained private 2.3.1 package, printed the reuse notice, asked neither a download nor a removal question, and left the entire cached tool package unchanged. Captured terminal output had blank lines before and after **Check USB programming tools**, **Check firmware**, **Upgrade firmware** and **Firmware verified**. Both installer transactions exited 0 and reached `complete` with `preserved:true` and `recovery_required:false`.

Saved-state hashes below use SHA-256 over the UTF-8 JSON serialization of `saved_semantics(snapshot)`, with `sort_keys=True` and `separators=(',', ':')`.

### Existing unconfigured state

The first run began with no saved standalone configuration, selected frequency or saved draft fields. All 4,194,304 bytes in the before/after programming readbacks were identical. The reserved range `0x3ee000..0x400000` contained 73,728 unchanged bytes, with SHA-256 `fac1c5d8304431c9e2eb9ea63346318c1b8fbec4895af559d6fef3d4ab093990`.

An independent postboot USB snapshot matched the separate baseline and the installer's held preflight snapshot for Config, saved progress fields and draft revision, hostname, frequency, calibration, watermark and suspension. The stable saved-state SHA-256 was `52250afb29235e7345bf66917de7a600013f9966aa8ec97a085034a30ce9e37f`. A new boot ID confirmed application restart; the same serial and physical port returned with maintenance idle, no owner and output inactive. This run alone did not exercise a populated configuration.

### Non-default settings and disabled schedule

A fresh, verified full-flash backup preceded the second test's settings changes. The following values were saved through the production USB management API and independently verified after an explicit restart before upgrading:

| Saved field | Test value |
| --- | --- |
| Hostname | `installer-preserve-test.local` |
| Station | Synthetic callsign `AA0NT`, locator `EM18`, WSPR message power 13 dBm |
| Selected frequency | 14,097,100 Hz |
| Manual correction | `1.234` ppm, manual mode |
| Stored schedule | Period 600 seconds, phase 120 seconds, global `enabled:false` |
| Saved station draft | Callsign, locator and power: three fields |

All these values survived the upgrade unchanged, including the disabled schedule and saved draft revision. Manual correction was checked through `/api/v1/rf-calibration`; the general Config response intentionally omits that separate field. The complete stable saved-state SHA-256 before and after the upgrade was `8d9c3d652d8677e7437196173f4f4604b4359a105ac51e621c804d87345c15b4`.

The installer's before/after programming readbacks matched across all 4 MiB. The reserved range was byte-for-byte identical before the verification boot, with SHA-256 `83bce4002efdc48f861204ab5dd0e9c823181176d1890fa3c7768c9fce301df4`. Fresh postboot reads matched the seeded settings and the transaction's preflight snapshot; maintenance was released after verification.

The original unconfigured state was then restored on the same identified board from the fresh backup. A pre-restoration read confirmed the application region still matched the original image. Only the original reserved flash range was written, followed by independent reserved-range and full-flash readback verification. The restored 4 MiB matched the original backup before reboot, with SHA-256 `8b659e09707c57767d38994d52de34aa887a769d9322b5f695f9968e2b760b2c`; this was also the first test's common full-flash hash.

After the verification boot, the original saved semantics matched again, with SHA-256 `52250afb29235e7345bf66917de7a600013f9966aa8ec97a085034a30ce9e37f`. Readback confirmed no saved configuration, no draft fields, no selected frequency, no saved calibration, the original saved/active hostname `wsprrypico-0a59dd.local`, and the original Wi-Fi state. The device finished idle and unowned, with output inactive, maintenance released and no outstanding restoration. The private test harness performed this bounded restoration after the installer's preserving upgrade had completed.

### Evidence and applicability

Private snapshots, terminal transcripts, tool inventories and structured verification reports are retained on `wspr5a` under `/home/pi/.local/state/wsprrypico-installer-checks/20261023T150444Z` and `/home/pi/.local/state/wsprrypico-installer-checks/20261023T171104Z-nondefault`. The corresponding installer transaction directories under `/home/pi/.local/state/wsprrypico-usb` are `1545B6EFBF78028C-w5aajp15` and `1545B6EFBF78028C-4j1fveno`. Credential-bearing flash backups remain in owner-only private state storage and are excluded from source control.

No transmit job was submitted, and no enabled schedule was saved. These observations cover ordinary completion, cached-tool reuse, terminal spacing, saved-state preservation and restoration only for the recorded host, board and same firmware image. They do not establish interrupted or power-cut recovery, cross-version migration, downgrade support, other host/board combinations, the WsprryPi web update route, physical clock accuracy or RF performance.

## Explicit developer builds

Existing pinned SDK 2.3.1 (`079c6f39023649b154152db30f1d781e884879bc`), submodules,
Arm GNU 15.3.1 and picotool sources are prerequisites. Compilation invokes the
accepted normal `scripts/build_pico.sh` target with a new build directory and
its linked engine, flash, USB, stack and heap checks. It validates generic
network-disabled, credential-free defaults and the linked USB update contract.

The explicit developer commands use the selected source revision and a new
build directory; these are separate from ordinary public-image installation:

```sh
PICO_SDK_PATH=/existing/pico-sdk \
PICOTOOL_FETCH_FROM_GIT_PATH=/existing/populated-dependencies \
python3 scripts/usb_installer.py plan --branch devel \
  --local-build /path/to/WsprryPico --source-revision FULL_SOURCE_SHA \
  --build-dir /new/private/build --allow-dirty --output /new/local-bundle
python3 scripts/usb_installer.py upgrade --branch devel --local-bundle /new/local-bundle \
  --device SERIAL --board pico2_w --yes --picotool /path/to/picotool
```


`--allow-dirty` explicitly selects a development build; omit it for a clean
checkout. Source HEAD, actual dirty identity and input digest are retained, and
source inputs must remain unchanged during compilation. Local metadata is
private developer evidence, never a public CI receipt. These bytes enter the
same image, backup, preservation and postboot transaction. A previous local
image needs its same-board compact image reference and an exact flash
match; a version string alone cannot identify it. Source ancestry/downgrade
checks still apply, so an unavailable or divergent source comparison refuses. Generic local-image references are retained separately
from expiring secret backups, with a maximum of 32 boards; retire an unused
reference explicitly before adding another board.

## Transaction retention

Completed install/upgrade histories are limited to two transactions, and
pre-programming refusals to eight, with a seven-day lifetime. Cleanup runs
before new work and after a verified completion or unchanged refusal. The
current transaction is retained even if an older record has a future timestamp.
Unresolved records and their backups are never evicted; eight unresolved
transactions block new work while explicit recovery remains available.
An explicit full erase retains other host backups and histories.

A cleanup failure adds `retention_warning` to the result. It does not replace a
verified firmware result, discard an unresolved transaction or expose private
paths. Retained records from an older installer use their original printed
continuation command, which downloads that exact installer revision.

## Bootstrap and Pi access

The bootstrap resolves its installer source revision once and retrieves the
core and schema at that immutable revision. Firmware branch selection remains
independent. Current invocation instructions live in the
[operator installation guide](../../docs/install.md).

WsprryPi's selected USB Pico controls call the identified deployed core. The
adapter verifies an independently published compatible installer and its hashes;
browser requests cannot supply commands, URLs or local paths. Only the selected
member is held, with a private persistent marker across service restart. The
marker remains until core verification and Pi USB reconnection both succeed.
Network-only selections do not offer a USB update. Local compilation remains
an explicit host command.
