# Install or update firmware

## Before you begin

Firmware is the application stored on the Pico. Installing or updating it uses a USB data cable and a **Terminal application on your computer**, not the Pico's text Console or a browser address bar.

Use native macOS or Linux, Python **3.10 or newer**, and `curl`. The installer reports missing or unsupported Python with instructions before downloading its code. Windows, Git Bash and WSL are unsupported. Run the installer as your ordinary user. On Linux, that user needs permission to access the USB device; see picotool's [USB permission instructions](https://github.com/raspberrypi/picotool/blob/master/BUILDING.md#linux--macos) if programming is refused for insufficient permissions.

Programming also needs **picotool**, Raspberry Pi's USB programming utility, at **version 2.3 or newer within the 2.x series**, with USB support. The installer checks for an existing compatible executable and a previously retained private copy before offering a download. Existing tools are reused without download or cleanup questions. If neither is available, the installer offers a verified official package for macOS, Linux ARM64 or Linux x86-64. Other architectures need an existing compatible picotool. No SDK or compiler is needed.

Install the **WsprryPico** firmware using the commands below.

## Select Beta 2 firmware

Use the published [Beta 2 firmware, version **1.0.0-beta.2**](https://github.com/WsprryPi/WsprryPico/releases/tag/v1.0.0-beta.2), for Beta testing. The Beta installation, update and image-check commands below include `--version 1.0.0-beta.2` to select that exact release. The version argument omits the tag's `v` prefix. The installer verifies image identity, source, workflow and SHA-256 checksums before programming; it stops if the selected release is unavailable or fails verification.

No `--branch` option is needed for Beta 2. The firmware version is independent of the installer source and any WsprryPi branch. The `devel` segment in the installer download URL below selects the installer source, while `--version 1.0.0-beta.2` selects the firmware.

For development firmware, use the [published devel download](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-devel) and the [devel upgrade command](#upgrade-to-devel-firmware).

## Get the installer and identify the Pico

Open a terminal in a folder where you can keep the installer. Download the small launcher script as `install_usb.sh`, inspect it in a text editor, and run it as your ordinary user. Keep using this folder for subsequent commands that begin with `bash install_usb.sh`:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  --output install_usb.sh
bash install_usb.sh discover
```

Discovery lists connected boards with their USB serial numbers and ports. Record the serial for the intended board; wherever a command below contains `SERIAL`, replace that word with this exact USB serial. It differs from the full stable device ID shown by firmware. If discovery finds nothing, check the data cable and USB permissions.

### Run directly with curl

You can also run the public bootstrap without keeping a local script. For a first installation, hold **BOOTSEL** while connecting the Pico, release it, then run this from a Bash terminal as your ordinary user:

```sh
set -o pipefail
curl --fail --silent --show-error --location \
  --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  | bash -s -- install --board pico2_w --yes --version 1.0.0-beta.2
```

This installs the exact Beta 2 firmware after checking the existing flash. Installation refuses existing saved data. Keep `--version 1.0.0-beta.2` in the command; `--branch devel` does not select the Beta release.

For an existing WsprryPico, complete [the update preparation below](#preserve-settings-during-an-update), leave its firmware running, and replace `install` with `upgrade` in the command. Starting an upgrade in BOOTSEL stops before tool or firmware downloads. Reconnect without holding BOOTSEL before retrying. If an update already has a retained transaction, use its printed recovery command.

The installer can still ask to download picotool, select a Pico and remove downloaded tools: these prompts use the terminal rather than the piped script input. With several boards attached, compare the listed USB serial and port before choosing. For unattended use, supply `--device SERIAL` and the explicit download/cleanup options below. Resolve reported network or DNS errors before retrying. If an installer transaction was created, follow its status and recovery guidance before starting another update.

Terminal runs show progress and a readable result. Add `--json-only` for JSON without questions or terminal guidance; this requires `--device SERIAL` for programming. Redirecting standard output also retains the JSON result while terminal questions and guidance stay on standard error.

## Picotool download and cleanup

Accept the picotool download prompt when installing or updating if you want the installer to supply it. The download uses the reviewed **2.3.1** package from [Raspberry Pi's SDK tools release](https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.3.1-0), checks its size and SHA-256 before execution, and keeps its support files alongside the executable. It does not change system tools or `PATH`. To use your own executable, add `--picotool /absolute/path/to/picotool`.

After the operation, the installer offers cleanup only if it downloaded picotool during that run. Declining keeps one reusable private package under `~/.cache/wsprrypico-usb/tools`; later runs reuse it without download or cleanup questions. Cleanup keeps firmware backups and transaction records. An unfinished update or uncertain recovery record retains the tool even if removal was requested, so the printed recovery command can still run.

For unattended use, provide `--device SERIAL` and explicitly allow downloading with `--download-picotool`. `--yes` confirms programming; it does not approve tool downloads. Choose `--tool-cleanup keep` or `--tool-cleanup remove` to skip the cleanup question. Without a terminal, or with `--json-only`, the default keeps downloaded tools. For example:

```sh
bash install_usb.sh upgrade --version 1.0.0-beta.2 --device SERIAL \
  --board pico2_w --yes --download-picotool --tool-cleanup remove
```

The bootstrap removes its temporary files on exit. A deliberately downloaded `install_usb.sh`, saved image bundles and private firmware backups remain yours to retain; tool cleanup does not remove them. Firmware transactions and backups follow the separate [retention and recovery policy](maintain.md#usb-update-backups-and-recovery).

## First installation

1. Disconnect the selected Pico. Hold its onboard **BOOTSEL** button while reconnecting the data cable, then release it.
2. Run the installer. Confirm that the numbered selection is your **Pico 2 W**:

   ```sh
   bash install_usb.sh install --board pico2_w --yes --version 1.0.0-beta.2
   ```

3. Keep USB connected through programming and verification. A final verified result, followed by the running firmware identity, confirms completion.

After successful installation, leave the Pico powered and continue to [Connect to your Pico](connect.md). Its setup Wi-Fi lets you save the network details and open the control page.

The command selects Beta 2 explicitly. If an existing application cannot be identified, stop and inspect the refusal; do not assume that replacing it can preserve its settings.

## Preserve settings during an update

1. Finish or abort any job through its owning controller, release control and leave the Pico idle. Disable its standalone schedule. Resolve STOP/fault states through the normal controls before updating. If WsprryPi uses this USB connection, follow [the standalone-on-Pi procedure](wsprrypi.md#standalone-installer-on-a-wsprrypi-host) to pause its service while the standalone installer runs.
2. Run:

   ```sh
   bash install_usb.sh upgrade --board pico2_w --yes --version 1.0.0-beta.2
   ```

3. Choose the intended Pico from the list. The installer binds the transaction to its serial and physical port, checks compatibility, backs up flash and verifies retained settings after programming.
4. If the installer displays **awaiting_bootsel**, reconnect that same Pico to the same USB port while holding BOOTSEL. Run the exact continuation command printed by the installer. WsprryPi offers **Continue after BOOTSEL**.
5. After success, open the control page and unlock controls. Saved station details and pins load automatically; check them, then use **Read saved frequency** to check the WSPR frequency. Reload the page only when you want to replace browser edits with saved values. Check the firmware version and source revision in the installer's result; the [USB Console `INFO` reply](usb.md#read-the-address-and-web-service-status) can read them again. Review [transmit readiness](operate.md#before-transmitting) before enabling and applying a schedule again.

Preparation or a BOOTSEL prompt is not a completed update. If interrupted, keep the private transaction and backup directories and use the printed same-board recovery command. Do not start a new image selection in place of that transaction. Backups contain credentials; keep them private.

### Upgrade to devel firmware

To upgrade to the latest published `devel` firmware, finish or abort any job, release control and disable standalone scheduling. Leave the Pico idle and running normally over USB. If WsprryPi uses this connection, follow [the standalone-on-Pi procedure](wsprrypi.md#standalone-installer-on-a-wsprrypi-host) to pause its service. Run this command from a Bash terminal as your ordinary user:

```sh
set -o pipefail
curl --fail --silent --show-error --location \
  --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  | bash -s -- upgrade --branch devel --board pico2_w --yes
```

Select the intended Pico when prompted. The installer checks compatibility, backs up flash and verifies retained settings through the same update process described above. Start with the firmware running normally; if the installer requests BOOTSEL, follow its printed continuation command for the same board and USB port. After success, review saved settings and transmit readiness before enabling a schedule.

### Update a Pico with development firmware

If an earlier development deployment or a different installer computer left no matching local-image reference, obtain the original developer bundle from whoever deployed that firmware. Add `--installed-bundle /path/to/original-bundle` to the upgrade command. This identifies the firmware already on the Pico; `--branch devel` still selects the new public firmware. The installer validates the bundle, checks source compatibility, backs up this Pico and compares its application flash with the supplied image before repairing the reference and programming the update. Saved settings receive the same preservation and postboot checks as an ordinary upgrade.

Do not delete the reference, edit its source identity or erase the Pico to get past a refusal. If the original bundle is unavailable or does not match, stop and retain the reported transaction for support. A firmware version or source string alone is insufficient to preserve settings safely.

## Check an image without programming

```sh
bash install_usb.sh plan --version 1.0.0-beta.2 --output ./pico-beta2-bundle
```

The output directory must be new. Confirm the returned version is `1.0.0-beta.2` and review the full source revision and manifest. The saved verified bundle can be used offline with `--bundle ./pico-beta2-bundle` in place of `--version 1.0.0-beta.2`. A checksum verifies integrity; it is not a signature. The ordinary download uses anonymous HTTPS. If GitHub reports a rate limit, wait until the reported UTC retry time; the installer does not silently choose an older image or another branch.

## Other firmware selectors

`--branch devel` selects the latest [published devel firmware](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-devel). Its download page identifies the firmware version and source revision.

Without an explicit version or another image selector, the installer selects the **main CI channel**, also selected by `--branch main`. That channel has no published download, so the installer stops with a missing-download error. Select `--branch devel` or `--version 1.0.0-beta.2` instead.

`--version` selects an exact published release independently of the CI channels. `--stable` selects the latest published final release and excludes betas; no final release is currently published. If a requested image is unavailable or fails verification, the installer stops without substituting another image.

For destructive erase, see [Recovery and reset](maintain.md#recovery-and-reset).
