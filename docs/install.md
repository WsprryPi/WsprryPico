# Install or update firmware

## Before you begin

Firmware is the application stored on the Pico. Install or update it using a USB data cable and a **Terminal application on your computer**, not the Pico's text Console or a browser address bar.

Use native macOS or Linux, Python **3.10 or newer**, and `curl`. The installer reports missing or unsupported Python with instructions before downloading its code. Windows, Git Bash, and WSL are unsupported. **Run the installer as your ordinary user, without `sudo`.** On Linux, complete [USB permission setup](#linux-usb-permission-setup) below before installing or updating firmware.

Programming also needs **picotool**, Raspberry Pi's USB programming utility, at **version 2.3 or newer within the 2.x series**, with USB support. The installer checks for an existing compatible executable and a previously retained private copy before offering a download. The installer reuses existing tools without download or cleanup questions. If neither is available, the installer offers a verified official package for macOS, Linux ARM64, or Linux x86-64. Other architectures need an existing compatible picotool. No SDK or compiler is needed.

Install the **WsprryPico** firmware using the commands below.

## Linux USB permission setup

Complete these steps once on the Linux computer connected to the Pico, using the account that will run the installer. This includes a Raspberry Pi used as the installer computer. macOS users can skip this section.

Linux needs a USB access rule and permission for your account to use it. Installing picotool or its dependencies alone does not grant this access. The installer does not change these system settings automatically. The steps below install Raspberry Pi's [picotool USB rule](https://github.com/raspberrypi/picotool/blob/2.3.1/udev/60-picotool.rules) and add your account to its `plugdev` access group. No SDK, compiler, or picotool build is needed.

1. Open a terminal as your usual account. Run:

   ```sh
   whoami
   ```

   The result should be your login name, such as `pi` or `wsprdaemon`, rather than `root`. If it says `root`, leave that administrator session and sign in as your usual account before continuing.

2. In a folder where you can save a file, download the rule:

   ```sh
   curl -fsSL --proto '=https' --proto-redir '=https' \
     https://raw.githubusercontent.com/raspberrypi/picotool/2.3.1/udev/60-picotool.rules \
     --output 60-picotool.rules
   ```

   Wait for the download to finish successfully. If it reports an error, stop and resolve that error before continuing.

3. Run each line below in the same terminal. Copy the commands exactly; `$(id -un)` supplies your current login name automatically. `sudo` may ask for your login password; the terminal does not display characters while you type it. If your account cannot use `sudo`, ask the computer's administrator to complete this setup for your account.

   ```sh
   sudo install -m 0644 60-picotool.rules /etc/udev/rules.d/60-picotool.rules
   sudo groupadd -f plugdev
   sudo usermod -aG plugdev "$(id -un)"
   sudo udevadm control --reload-rules
   ```

   Stop if any command reports an error. These are the system setup commands that need `sudo`; the firmware installer runs as your ordinary user.

4. Log out of your Linux account and log back in so the new group membership takes effect. If connected through SSH, disconnect and reconnect. Opening another terminal in the same desktop login is insufficient. Run:

   ```sh
   id -nG
   ```

   Check that the list includes `plugdev`. If it does not, ask the administrator to check membership for the account shown by `whoami`.

5. Disconnect and reconnect the Pico so the reloaded rule applies. Use BOOTSEL for a first installation, as described below; leave existing WsprryPico firmware running normally for an upgrade.

Continue with the installer commands below **without `sudo`**. Running the installer as root uses a different private cache and recovery directory, and its managed picotool download refuses root. Membership in the serial-port group `dialout` alone does not grant BOOTSEL USB access. If programming still fails, retain the full error and follow [support instructions](support.md); do not erase the Pico to resolve a host permission error.

## Select recommended firmware

`devel` is the default source branch for active development and prereleases.
`main` is absent during prerelease development and can be recreated when stable
`1.0.0` is ready. Release tags identify exact released versions; use an explicit
firmware version to select a published release.

Use the published [recommended firmware, version **@RECOMMENDED_FIRMWARE_VERSION@**](https://github.com/WsprryPi/WsprryPico/releases/tag/v@RECOMMENDED_FIRMWARE_VERSION@). The installation, update, and image-check commands below include `--version @RECOMMENDED_FIRMWARE_VERSION@` to select that exact release. The version argument omits the tag's `v` prefix. The installer verifies image identity, source, workflow, and SHA-256 checksums before programming; it stops if the selected release is unavailable or fails verification.

No `--branch` option is needed for the recommended release. The firmware version is independent of the installer source and any WsprryPi branch. The `devel` segment in the installer download URL below selects the installer source, while `--version @RECOMMENDED_FIRMWARE_VERSION@` selects the firmware.

See the [RC.2 release notes and qualification scope](reference/releases.md) before selecting this prerelease.

For development firmware, use the [published devel download](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-devel) and the [devel upgrade command](#upgrade-to-devel-firmware).

## Get the installer and identify the Pico

Prepare the Pico **before running discovery**:

- **First WsprryPico installation, including a Pico running another program:** disconnect the Pico, hold its onboard **BOOTSEL** button while reconnecting the USB data cable, then release the button. Leave it connected in BOOTSEL for discovery and installation. Discovery recognizes BOOTSEL devices and the WsprryPico application USB identity; another running program may not appear.
- **Update existing WsprryPico firmware:** complete [update preparation](#preserve-settings-during-an-update) and leave the firmware running normally. Use `upgrade`, and enter BOOTSEL only if the installer requests it. If an interrupted update already has a retained transaction, follow its printed recovery command.

Open a terminal in a folder where you can keep the installer. Download the small launcher script as `install_usb.sh`, inspect it in a text editor, and run it as your ordinary user. Keep using this folder for subsequent commands that begin with `bash install_usb.sh`:

```sh
curl -fsSL --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  --output install_usb.sh
bash install_usb.sh discover
```

Discovery lists recognized connected boards with their USB serial numbers and ports. Record the serial for the intended board, then replace `SERIAL` in the commands below with that exact USB serial. It differs from the full stable device ID shown by firmware. If discovery finds nothing, check the preparation above and the USB data cable. Discovery can list a BOOTSEL device even when Linux permissions prevent picotool from accessing it; complete [Linux USB permission setup](#linux-usb-permission-setup) before programming.

The launcher downloads the installer from GitHub by default, even when local installer files are present. To use local files explicitly, run `bash install_usb.sh --local-installer discover`, or replace `discover` with the intended operation and its options. Place `--local-installer` before the operation. Keep `usb_installer.py` and `ci/release-manifest-2.schema.json` beside the saved launcher, from the same source revision. Missing local files stop the command with an error. The local option requires a saved launcher; commands piped directly to Bash use GitHub downloads.

### Run directly with curl

You can also run the public bootstrap without keeping a local script. For a first installation, hold **BOOTSEL** while connecting the Pico, release it, then run this from a Bash terminal as your ordinary user:

```sh
set -o pipefail
curl -fsSL \
  --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  | bash -s -- install --board pico2_w --yes --version @RECOMMENDED_FIRMWARE_VERSION@
```

This installs the exact recommended firmware release after checking the existing flash. Installation refuses existing saved data. Keep `--version @RECOMMENDED_FIRMWARE_VERSION@` in the command; `--branch devel` does not select this exact release.

For an existing WsprryPico, complete [the update preparation below](#preserve-settings-during-an-update), leave its firmware running, and replace `install` with `upgrade` in the command. Starting an upgrade in BOOTSEL stops before downloading tools or firmware. Reconnect without holding BOOTSEL before retrying. If an update already has a retained transaction, use its printed recovery command.

The installer can still ask to download picotool, select a Pico, and remove downloaded tools: these prompts use the terminal rather than the piped script input. With several boards attached, compare the listed USB serial and port before choosing. For unattended use, supply `--device SERIAL` and the explicit download/cleanup options below. Resolve reported network or DNS errors before retrying. If an installer transaction was created, follow its status and recovery guidance before starting another update.

Terminal runs show progress and a readable result. Add `--json-only` for JSON without questions or terminal guidance. Programming in this mode requires `--device SERIAL`. Redirecting standard output also retains the JSON result while terminal questions and guidance stay on standard error.

## Picotool download and cleanup

Accept the picotool download prompt when installing or updating if you want the installer to supply it. The download uses the reviewed **2.3.1** package from [Raspberry Pi's SDK tools release](https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.3.1-0), checks its size and SHA-256 before execution, and keeps its support files alongside the executable. It does not change system tools or `PATH`. To use your own executable, add `--picotool /absolute/path/to/picotool`.

After the operation, the installer offers cleanup only if it downloaded picotool during that run. Declining cleanup keeps one reusable private package under `~/.cache/wsprrypico-usb/tools`; later runs reuse it without download or cleanup questions. Cleanup keeps firmware backups and transaction records. The installer retains the tool for an unfinished update or an uncertain recovery record, even if removal was requested. This keeps the printed recovery command usable.

For unattended use, provide `--device SERIAL` and explicitly allow downloading with `--download-picotool`. `--yes` confirms programming; it does not approve tool downloads. Choose `--tool-cleanup keep` or `--tool-cleanup remove` to skip the cleanup question. Without a terminal, or with `--json-only`, the default keeps downloaded tools. For example:

```sh
bash install_usb.sh upgrade --version @RECOMMENDED_FIRMWARE_VERSION@ --device SERIAL \
  --board pico2_w --yes --download-picotool --tool-cleanup remove
```

The bootstrap removes its temporary files on exit. A deliberately downloaded `install_usb.sh`, saved image bundles, and private firmware backups remain yours to retain; tool cleanup does not remove them. Firmware transactions and backups follow the separate [retention and recovery policy](maintain.md#usb-update-backups-and-recovery).

## First installation

1. Disconnect the selected Pico. Hold its onboard **BOOTSEL** button while reconnecting the data cable, then release it.
2. Run the installer. Confirm that the numbered selection is your **Pico 2 W**:

   ```sh
   bash install_usb.sh install --board pico2_w --yes --version @RECOMMENDED_FIRMWARE_VERSION@
   ```

3. Keep USB connected through programming and verification. A final verified result, followed by the running firmware identity, confirms completion.

After successful installation, leave the Pico powered and continue to [Connect to your Pico](connect.md). Its setup Wi-Fi lets you save the network details and open the control page.

The command selects the recommended release explicitly. If an existing application cannot be identified, stop and inspect the refusal; do not assume that replacing it can preserve its settings.

## Preserve settings during an update

1. Finish or abort any job through its owning controller, release control, and leave the Pico idle. Disable its standalone schedule. Resolve STOP/fault states through the normal controls before updating. If WsprryPi uses this USB connection, follow [the standalone-on-Pi procedure](wsprrypi.md#standalone-installer-on-a-wsprrypi-host) to pause its service while the standalone installer runs.
2. Run:

   ```sh
   bash install_usb.sh upgrade --board pico2_w --yes --version @RECOMMENDED_FIRMWARE_VERSION@
   ```

3. Choose the intended Pico from the list. The installer binds the transaction to its serial and physical port, checks compatibility, backs up flash, and verifies retained settings after programming.
4. If the installer displays **awaiting_bootsel**, reconnect that same Pico to the same USB port while holding BOOTSEL. Run the exact continuation command printed by the installer. WsprryPi offers **Continue after BOOTSEL**.
5. After a successful update, open the control page and unlock controls. Saved station details and pins load automatically; check them, then use **Read saved frequency** to check the WSPR frequency. Reload the page only when you want to replace browser edits with saved values. Check the firmware version and source revision in the installer's result; the [USB Console `INFO` reply](usb.md#read-the-address-and-web-service-status) can read them again. Review [transmit readiness](operate.md#before-transmitting) before enabling and applying a schedule again.

Preparation or a BOOTSEL prompt is not a completed update. If interrupted, keep the private transaction and backup directories and use the printed same-board recovery command. Do not start a new image selection in place of that transaction. Backups contain credentials; keep them private.

### Upgrade to devel firmware

To upgrade to the latest published `devel` firmware, finish or abort any job, release control, and disable standalone scheduling. Leave the Pico idle and running normally over USB. If WsprryPi uses this connection, follow [the standalone-on-Pi procedure](wsprrypi.md#standalone-installer-on-a-wsprrypi-host) to pause its service. Run this command from a Bash terminal as your ordinary user:

```sh
set -o pipefail
curl -fsSL \
  --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  | bash -s -- upgrade --branch devel --board pico2_w --yes
```

Select the intended Pico when prompted. The installer checks compatibility, backs up flash, and verifies retained settings through the same update process described above. Start with the firmware running normally; if the installer requests BOOTSEL, follow its printed continuation command for the same board and USB port. After a successful update, review saved settings and transmit readiness before enabling a schedule.

### Update a Pico with development firmware

If the installer computer has no matching local-image reference for the firmware on the Pico, obtain the original developer bundle from whoever deployed that firmware. Add `--installed-bundle /path/to/original-bundle` to the upgrade command. This identifies the firmware already on the Pico; `--branch devel` still selects the new public firmware. The installer validates the bundle, checks source compatibility, backs up this Pico, and compares its application flash with the supplied image before repairing the reference and programming the update. Saved settings receive the same preservation and postboot checks as an ordinary upgrade.

Do not delete the reference, edit its source identity, or erase the Pico to get past a refusal. If the original bundle is unavailable or does not match, stop and retain the reported transaction for support. A firmware version or source string alone is insufficient to preserve settings safely.

## Check an image without programming

```sh
bash install_usb.sh plan --version @RECOMMENDED_FIRMWARE_VERSION@ --output ./pico-firmware-bundle
```

The output directory must be new. Confirm the returned version is `@RECOMMENDED_FIRMWARE_VERSION@` and review the full source revision and manifest. The saved verified bundle can be used offline with `--bundle ./pico-firmware-bundle` in place of `--version @RECOMMENDED_FIRMWARE_VERSION@`. A checksum verifies integrity; it is not a signature. The ordinary download uses anonymous HTTPS. If GitHub reports a rate limit, wait until the reported UTC retry time; the installer does not substitute another image or branch.

## Other firmware selectors

`--branch devel` selects the latest [published devel firmware](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-devel). Its download page identifies the firmware version and source revision.

Choose firmware explicitly with `--branch devel` or `--version @RECOMMENDED_FIRMWARE_VERSION@`. The `--version` option selects an exact published release. If the requested image is unavailable or fails verification, the installer stops without substituting another image.

For destructive erase, see [Recovery and reset](maintain.md#recovery-and-reset).
