# USB installer

The shared installer is `scripts/usb_installer.py` (version 0.2.0). It runs with
Python 3.10 or newer and its standard library on macOS and Linux. Windows and
WSL USB operation are unsupported. The [acceptance record](usb-installer-results.md)
distinguishes software checks, published downloads and recorded board tests.

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


Output directories must be new. `--bundle DIRECTORY` revalidates a previously
saved public bundle without another download. It cannot accompany another
image selector. `--version 1.0.0-beta.1` or `--version 1.0.0` selects that exact
semantic tag independently of the CI branch selector. `--stable` selects GitHub's
latest full release and requires a final semantic version; absence or invalid
provenance causes refusal without substituting CI. These selectors require a
published compatible bundle and do not publish or create one. Main and devel each have a verified permanent CI
download index. `recent_ci` reports additional run status separately from the
immutable selected image. Missing or invalid downloads still cause refusal.

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

Hardware-free publication checks run the core, tool-download and publication
suites from the repository root.

```sh
python3 -B tests/usb_installer_tests.py
python3 -B tests/usb_tool_download_tests.py
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
