# Install or update firmware

## Before you begin

Use native macOS or Linux, Python **3.10 or newer**, and `curl`. The installer reports missing or unsupported Python with instructions before downloading its code. Windows, Git Bash and WSL are unsupported. Run as your ordinary user. On Linux, arrange access to the USB device first.

Programming also needs a USB-enabled **picotool 2.3 or newer within the 2.x series**. An existing compatible picotool is used without replacement. If it is missing or incompatible, the installer offers to download a verified official package for macOS, Linux ARM64 or Linux x86-64. Other architectures need an existing compatible picotool. No SDK or compiler is needed.

Use the normal **WsprryPico** image. **WsprryPico-Inhibited** simulates jobs without RF and is for diagnostics. Do not substitute a bench or compatibility image for the normal download.

## Select Beta 1 firmware

Use the published [Beta 1 firmware, version **1.0.0-beta.1**](https://github.com/WsprryPi/WsprryPico/releases/tag/v1.0.0-beta.1), for Beta testing. The installation, update and image-check commands below include `--version 1.0.0-beta.1` to select that exact release. The version argument omits the tag's `v` prefix. The installer verifies image identity, source, workflow and SHA-256 checksums before programming; it stops if the selected release is unavailable or fails verification.

No `--branch` option is needed for Beta 1. The firmware version is independent of the installer source and any WsprryPi branch. The `devel` segment in the installer download URL below selects the installer source, while `--version 1.0.0-beta.1` selects the firmware.

## Get the installer and identify the Pico

Download the project bootstrap into a local file, inspect it, and run it as your ordinary user:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  --output install_usb.sh
bash install_usb.sh discover
```

Discovery shows physical USB serials and ports. Select the intended board; the USB serial is different from the full stable device ID shown by firmware. If discovery finds nothing, check the data cable and USB permissions.

### Run directly with curl

You can also run the public bootstrap without keeping a local script. For a first installation, hold **BOOTSEL** while connecting the Pico, release it, then run this from a Bash terminal as your ordinary user:

```sh
set -o pipefail
curl --fail --silent --show-error --location \
  --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  | bash -s -- install --board pico2_w --yes --version 1.0.0-beta.1
```

This installs the exact Beta 1 firmware after checking the existing flash. Installation refuses existing saved data. Keep `--version 1.0.0-beta.1` in the command; `--branch devel` does not select the Beta release.

For an existing WsprryPico, complete [the update preparation below](#preserve-settings-during-an-update), leave its firmware running, and replace `install` with `upgrade` in the command. Starting an upgrade in BOOTSEL stops before tool or firmware downloads. Reconnect without holding BOOTSEL before retrying. If an update already has a retained transaction, use its printed recovery command.

The installer can still ask to download picotool, select a Pico and remove downloaded tools: these prompts use the terminal rather than the piped script input. With several boards attached, compare the listed USB serial and port before choosing. For unattended use, supply `--device SERIAL` and the explicit download/cleanup options below. Resolve reported network or DNS errors before retrying. If an installer transaction was created, follow its status and recovery guidance before starting another update.

Terminal runs show progress and a readable result. Add `--json-only` for JSON without questions or terminal guidance; this requires `--device SERIAL` for programming. Redirecting standard output also retains the JSON result while terminal questions and guidance stay on standard error.

## Picotool download and cleanup

Accept the picotool download prompt when installing or updating if you want the installer to supply it. The download uses the reviewed **2.3.1** package from [Raspberry Pi's SDK tools release](https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.3.1-0), checks its size and SHA-256 before execution, and keeps its support files alongside the executable. It does not change system tools or `PATH`. To use your own executable, add `--picotool /absolute/path/to/picotool`.

After the operation, the installer offers to remove its downloaded picotool and support files. Declining keeps one reusable private package under `~/.cache/wsprrypico-usb/tools`. Cleanup keeps firmware backups and transaction records. An unfinished update or uncertain recovery record retains the tool even if removal was requested, so the printed recovery command can still run.

For unattended use, provide `--device SERIAL` and explicitly allow downloading with `--download-picotool`. `--yes` confirms programming; it does not approve tool downloads. Choose `--tool-cleanup keep` or `--tool-cleanup remove` to skip the cleanup question. Without a terminal, or with `--json-only`, the default keeps downloaded tools. For example:

```sh
bash install_usb.sh upgrade --version 1.0.0-beta.1 --device SERIAL \
  --board pico2_w --yes --download-picotool --tool-cleanup remove
```

The bootstrap removes its temporary files on exit. A deliberately downloaded `install_usb.sh`, saved image bundles and private firmware backups remain yours to retain; tool cleanup does not remove them. Firmware transactions and backups follow the separate [retention and recovery policy](maintain.md#usb-update-backups-and-recovery).

## First installation

1. Disconnect the selected Pico. Hold its onboard **BOOTSEL** button while reconnecting the data cable, then release it.

2. Run the installer. Confirm that the numbered selection is your **Pico 2 W**:

   ```sh
   bash install_usb.sh install --board pico2_w --yes --version 1.0.0-beta.1
   ```

3. Keep USB connected through programming and verification. A final verified result, followed by the running firmware identity, confirms completion.

The command selects Beta 1 explicitly. If an existing application cannot be identified, stop and inspect the refusal; do not assume that replacing it can preserve its settings.

## Preserve settings during an update

1. Finish or abort any job through its owning controller, release control and leave the Pico idle. Disable its standalone schedule. Resolve STOP/fault states through the normal controls before updating. If WsprryPi uses this USB connection, follow [the standalone-on-Pi procedure](wsprrypi.md#standalone-installer-on-a-wsprrypi-host) to pause its service while the standalone installer runs.

2. Run:

   ```sh
   bash install_usb.sh upgrade --board pico2_w --yes --version 1.0.0-beta.1
   ```

3. Choose the intended Pico from the list. The installer binds the transaction to its serial and physical port, checks compatibility, backs up flash and verifies retained settings after programming.

4. Older firmware may display **awaiting_bootsel**. Reconnect that same Pico to the same USB port while holding BOOTSEL. Run the exact continuation command printed by the installer. WsprryPi offers **Continue after BOOTSEL**.

5. After success, read back station settings, frequency, pins and firmware/source identity. Enable a schedule deliberately only after reviewing readiness.

Preparation or a BOOTSEL prompt is not a completed update. If interrupted, keep the private transaction and backup directories and use the printed same-board recovery command. Do not start a new image selection in place of that transaction. Backups contain credentials; keep them private.

## Check an image without programming

```sh
bash install_usb.sh plan --version 1.0.0-beta.1 --output ./pico-beta1-bundle
```

The output directory must be new. Confirm the returned version is `1.0.0-beta.1` and review the full source revision and manifest. The saved verified bundle can be used offline with `--bundle ./pico-beta1-bundle` in place of `--version 1.0.0-beta.1`. A checksum verifies integrity; it is not a signature. The ordinary download uses anonymous HTTPS. If GitHub reports a rate limit, wait until the reported UTC retry time; the installer does not silently choose an older image or another branch.

## Other firmware selectors

Without an explicit version or another image selector, the installer tries the **main CI channel**. `--branch devel` selects the **devel CI channel**. These channels require separately published CI indexes; neither index is currently published, so either selection stops with a missing-download error. Use `--version 1.0.0-beta.1` for the current Beta.

`--version` selects an exact published release independently of the CI channels. `--stable` selects the latest published final release and excludes betas; no final release is currently published. If a requested image is unavailable or fails verification, the installer stops without substituting another image.

For destructive erase, see [Recovery and reset](maintain.md#recovery-and-reset).
