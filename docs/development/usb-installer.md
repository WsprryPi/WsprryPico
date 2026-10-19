# USB installer

The shared installer is `scripts/usb_installer.py` (version 0.1.2). It runs with
Python 3.10 or newer and its standard library on macOS and Linux. Windows and
WSL USB operation are unsupported. The current implementation is under
validation; [the result record](usb-installer-results.md) defines its acceptance.

## Full flash erase

`erase` explicitly removes firmware and all saved data from all 4 MiB of the
Pico 2 W external flash. It includes profiles, credentials, certificates,
Bluetooth bonds, standalone settings, schedules, watermarks, NTP learning,
saved drafts, diagnostic scratch and the E10 sector. No flash region is
preserved. Immutable ROM, chip identity and OTP are outside the flash operation.

Select the physical USB serial and confirm both the board and destructive
operation:

```sh
python3 scripts/usb_installer.py discover
python3 scripts/usb_installer.py erase --device 1545B6EFBF78028C --board pico2_w --yes
```

If firmware is running, the installer first requires an idle, unowned Pico
with its saved standalone schedule disabled or unconfigured. It prepares an
erase transaction and prints same-port BOOTSEL reconnect instructions and an
exact `recover` continuation command. Preparation changes no flash. Reconnect
that Pico while holding BOOTSEL, then run the printed command. A Pico already
in BOOTSEL can be erased directly. Neither path forces a running device to
reset or stops a job.

The command uses the pinned picotool's
[range erase and binary verification](https://github.com/raspberrypi/picotool/blob/6f6458d792b93685a11423b244a585eaa99eafcf/main.cpp)
over `0x10000000` through exclusive `0x10400000`. The explicitly confirmed
Pico 2 W target defines the [4 MiB capacity](https://github.com/raspberrypi/pico-sdk/blob/079c6f39023649b154152db30f1d781e884879bc/src/boards/include/boards/pico2_w.h).
Picotool's flash-size estimate
depends on existing contents and is absent for uniform or blank flash; it is
not used as a geometry check. The installer checks the RP2350 chip ID,
USB serial and physical port, durably records erase intent,
erases the range and compares every byte with `0xff`. Success requires a
complete successful comparison and returns `erase_verified: true` and
`erased_bytes: 4194304`. It leaves the Pico in BOOTSEL and does not install
firmware or reconnect a runtime application.

Erase does not resolve or download a firmware image and does not create a
backup of credentials or old flash. Only a blank comparison file and transaction
metadata are retained. Existing host backups, snapshots and other devices are
untouched. On interruption, permission failure or a failed comparison, the
result remains unresolved; never assume the data is gone. The printed
same-board `recover` command repeats erase and full verification without a
firmware bundle or backup. It never restores the old data.

WsprryPi's **Pico firmware over USB** panel offers **Erase firmware and all
data…** without an image check. It requires confirmation for the selected USB
Pico, pauses that member, and shows the BOOTSEL instructions. **Erase after
BOOTSEL** requires another explicit confirmation. An interrupted erase offers
**Retry full erase**; success reports verified blank flash without attempting
an application reconnection. The Pi retains the exact installer for recovery.
It can refresh the compatible installer independently of firmware downloads;
an already cached erase-capable installer remains usable offline.

The deterministic erase tests cover identity/port checks, uniform and blank
flash, explicit confirmation, preparation, full-range comparison, a nonblank
last byte, disconnects, recovery and retention of existing host backups.

Run the hardware-free installer and publication checks from the repository root:

```sh
python3 tests/usb_installer_tests.py
python3 tests/installer_release_tests.py
```

### Physical erase check

The 2026-10-19 CLI/core check covers Pico C, a Pico 2 W / RP2350 on wspr4,
USB serial `1545B6EFBF78028C`, device ID
`c2a3a2a314c948b50a8562a1aeb69669`, USB parent `1-1.3`, and USB-enabled
picotool 2.3.0. Its original firmware is `0.1.0-ci.39155533863.1`, source
`0a7c05d1c41b`, with no configured standalone schedule. The tested installer
SHA-256 is `f568a1abb1452c250ee3ffc9361005e1d9d72c8c2fd8b5a65e25f02b5a9a15f0`.

Application-side erase preparation performs no flash write. The test fixture
uses the existing guarded USB maintenance transition to enter BOOTSEL and
keeps a separate private restoration backup. All 4,194,304 flash bytes are
populated with verified `0x5a` before the prepared erase is continued. Erase
and an independent full-flash readback confirm every byte is `0xff`, with
SHA-256 `cd3517473707d59c3d915b52a3e16213cadce80d9ffb2b4371958fb7acb51a08`.
The erase transaction contains only its blank comparison file and metadata.
The Pico remains in BOOTSEL. A deliberate nonblank byte at `0x103fffff` makes
full-range verification fail; a repeated erase recovery clears it and passes.

Restoration is verified byte-for-byte across the original 4 MiB, followed by
matching firmware/source and saved semantics after boot. The wspr4 service
returns active and ready, with the Pico unowned and output inactive. No RF jobs
or RF-clock measurements occur. This qualifies the recorded board and USB
CLI/core path; physical power-cut/disconnect cases and the live Pi web route
remain separate from the deterministic failure and browser checks.

## Image selection and planning

No firmware branch option means **main**, independently of the checkout,
bootstrap or WsprryPi branch. `--branch devel` selects devel explicitly. Latest
CI resolution uses the permanent `ci-main` or `ci-devel` bookmark and its exact
public version release. A verified CI prerelease is eligible. Missing branches,
assets, incompatible manifests and failed provenance checks cause refusal;
another branch, older image or compilation is never selected implicitly.

```sh
python3 scripts/usb_installer.py discover
python3 scripts/usb_installer.py plan --output /private/tmp/pico-main-bundle
python3 scripts/usb_installer.py plan --branch devel --output /private/tmp/pico-devel-bundle
python3 scripts/usb_installer.py plan --branch devel --version 0.1.0-ci.39084514130.1
python3 scripts/usb_installer.py plan --stable
```

Output directories must be new. `--bundle DIRECTORY` revalidates a previously
saved public bundle without another download. It cannot accompany another
image selector. Stable selection is explicit and never substitutes CI. The
current public manifest contract describes CI testing images; no compatible
stable image is available. The initial acceptance snapshot has no main image;
main therefore refuses until canonical CI publishes one there. `recent_ci`
reports additional run status separately from the immutable selected image.

The ordinary path uses anonymous HTTPS and needs no Git, compiler, SDK or
GitHub account. A saved successful verification receipt remains usable after
Actions retention expiry when the public release and exact hashes remain intact.
HTTPS/repository ownership is the distribution trust boundary; checksums are
integrity checks, not signatures.

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

## Independently published installer

The USB installer has its own lightweight CI workflow,
`.github/workflows/usb-installer.yml`. It tests the installer and publication
logic independently of firmware builds. Successful main/devel runs publish
the exact core, firmware-manifest schema and `usb-installer.json` receipt at
`usb-installer-v1-BRANCH-RUN.ATTEMPT`. The permanent
`usb-installer-v1-main` and `usb-installer-v1-devel` release bodies point to
the latest tested compatible bundle; existing version assets are never replaced.

The receipt declares installer contract 1, `wsprrypico-usb-result/1`,
`wsprrypico-usb-transaction/1`, firmware-manifest schema 1, minimum Python,
installer version, source, successful verification job, workflow identity and
exact file sizes/SHA-256. Compatible implementation fixes keep the contract.
A breaking result, transaction or deployment interface needs a new contract and
channel; it must not be published as contract 1. Firmware image versions and
firmware branch bookmarks remain independent.

WsprryPi selects by supported installer contract and channel. An explicit image
check may refresh the shared installer without a Pi source change. Its checked
image and every transaction retain their exact installer; recovery must never
resolve the current channel or substitute newer code. The Pi bounds completed
image/backup caches across installer versions while retaining unresolved recovery.

Publication checks run without an SDK, compiler, attached Pico or network:

```sh
python3 -B tests/usb_installer_tests.py
python3 -B tests/installer_release_tests.py
```

## USB dependency and device selection

Programming accepts **picotool 2.3 or newer within the 2.x series**, including
the public [2.3.1 release](https://github.com/raspberrypi/picotool/releases/tag/2.3.1).
The installer checks the version, USB support and the command options needed for
identity, backup, programming, verification and erase. Older versions, prereleases,
3.x versions and builds without the required capabilities are refused. USB is a
normal picotool capability; builds without libusb cannot access a connected Pico.
The exact executable version and SHA-256 are recorded for each transaction.
It accepts an explicit `--picotool /absolute/path/to/picotool`. It does
not install packages, acquire an SDK, bundle a local executable or run the whole
bootstrap as root. Tool acquisition/build is an administrator/developer step;
retain picotool's upstream license when redistributing it.

Discovery binds USB serial and physical parent. Application CDC roles are
Console interface 0, WTP interface 2 and management interface 4; macOS places
serial clients under their paired data interfaces. Tty suffixes are not roles.
BOOTSEL identifies RP2350, so `--board pico2_w` explicitly confirms the board's
wireless hardware. Re-enumeration must retain the serial and physical port.

For first installation, disconnect the selected Pico, hold BOOTSEL, reconnect
its data cable, release BOOTSEL and run discovery. Programming always needs an
explicit operation, device, board and `--yes`; stdin is never used for prompts,
including when the bootstrap is piped into Bash.

```sh
python3 scripts/usb_installer.py install --branch devel \
  --bundle /private/tmp/pico-devel-bundle \
  --device 1545B6EFBF78028C --board pico2_w --yes --picotool /path/to/picotool
```

Initial installation requires erased saved-state banks and an erased or exact
known RP2350 workaround boot sector. Unknown application bytes cause refusal
and a private backup. Only an explicit `--replace-unidentified-application`
initial-install choice can replace them; it still refuses existing saved-state
or unknown boot-sector data. It is not a reset or migration command.

## Terminal BOOTSEL instructions

Running `scripts/usb_installer.py` or `scripts/install_usb.sh` directly prints
BOOTSEL instructions to stderr. Stdout remains one JSON result, with the same
result schema and exit statuses used by WsprryPi. Redirect stdout separately
when saving or parsing results; do not merge stderr into the JSON stream.
`--json-only` suppresses the BOOTSEL instructions for standalone automation.
The imported `main()` entry point used by WsprryPi stays quiet by default.

Initial installation identifies the selected Pico and explains the button
sequence before checking its BOOTSEL connection. A Pico already in BOOTSEL
stays connected. Otherwise, follow the reconnect instructions and rerun the
install command. The installer does not wait for keyboard input or reconnect
automatically. Supported guarded upgrades enter BOOTSEL automatically; they
do not ask for a manual unplug during programming or verification.

## Preserving upgrade and recovery

```sh
python3 scripts/usb_installer.py upgrade --branch devel \
  --bundle /private/tmp/pico-devel-bundle \
  --device 1545B6EFBF78028C --board pico2_w --yes --picotool /path/to/picotool
python3 scripts/usb_installer.py recover --transaction /private/path/transaction.json \
  --device 1545B6EFBF78028C --board pico2_w --yes --picotool /path/to/picotool
```

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

## Explicit developer builds

Existing pinned SDK 2.3.1 (`079c6f39023649b154152db30f1d781e884879bc`), submodules,
Arm GNU 15.3.1 and picotool sources are prerequisites. Compilation invokes the
accepted normal `scripts/build_pico.sh` target with a new build directory and
its linked engine, flash, USB, stack and heap checks. It validates generic
network-disabled, credential-free defaults and the linked USB update contract.

```sh
PICO_SDK_PATH=/existing/pico-sdk \
PICOTOOL_FETCH_FROM_GIT_PATH=/existing/populated-dependencies \
python3 scripts/usb_installer.py plan --branch devel \
  --local-build /path/to/WsprryPico --source-revision FULL_SOURCE_SHA \
  --build-dir /new/private/build --allow-dirty --output /new/local-bundle
python3 scripts/usb_installer.py upgrade --branch devel --local-bundle /new/local-bundle \
  --device 1545B6EFBF78028C --board pico2_w --yes --picotool /path/to/picotool
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

`bash scripts/install_usb.sh discover` exercises the maintained bootstrap.
It resolves the installer source revision once and retrieves the core and schema
at that immutable revision. Firmware selection remains main unless changed
explicitly. The public bootstrap can also run without a repository checkout:

```sh
set -o pipefail
curl -fsSL --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh |
bash -s -- discover
```

For an existing WsprryPico application, replace `discover` with
`upgrade --branch devel --device SERIAL --board pico2_w --yes`, using the
discovered USB serial. The command selects the latest verified devel firmware
and preserves saved settings. Python, picotool and USB permissions must already
be available. The bootstrap runs as the ordinary user, not through `sudo`.

WsprryPi's selected USB Pico controls call the identified deployed core. The
adapter verifies an independently published compatible installer and its hashes;
browser requests cannot supply commands, URLs or local paths. Only the selected
member is held, with a private persistent marker across service restart. The
marker remains until core verification and Pi USB reconnection both succeed.
Network-only selections do not offer a USB update. Local compilation remains
an explicit host command.
