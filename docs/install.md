# Install or update firmware

## Before you begin

Use macOS or Linux, Python **3.10 or newer**, `curl`, and a USB-enabled
**picotool 2.3 or newer within the 2.x series**. Install picotool from the
[Raspberry Pi project](https://github.com/raspberrypi/picotool/releases);
the installer checks its version and required USB capabilities. Do not run the
whole installer as root. On Linux, arrange access to the USB device first.

Use the normal **WsprryPico** image. **WsprryPico-Inhibited** simulates jobs
without RF and is for diagnostics. Do not substitute a bench or compatibility
image for the normal download.

Published testing images are available from the
[main CI index](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-main) and
[devel CI index](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-devel).
Each index points to an exact version with its manifest and SHA-256 checksums.
These are CI testing images, not a stable release. The installer verifies
image identity, source, workflow and checksums before programming.

## Get the installer and identify the Pico

Download the project bootstrap into a local file, inspect it, and run it as
your ordinary user:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
  --output install_usb.sh
bash install_usb.sh discover
```

Discovery shows physical USB serials and ports. Select the intended board;
the USB serial is different from the full stable device ID shown by firmware.
If discovery finds nothing, check the data cable and USB permissions.

## First installation

1. Disconnect the selected Pico. Hold its onboard **BOOTSEL** button while
   reconnecting the data cable, then release it.
2. Run the installer. Confirm that the numbered selection is your **Pico 2 W**:

   ```sh
   bash install_usb.sh install --board pico2_w --yes
   ```

3. Keep USB connected through programming and verification. A final verified
   result, followed by the running firmware identity, confirms completion.

The firmware channel defaults to **main**, regardless of the installer or
WsprryPi branch. To deliberately use devel, add `--branch devel` to the command.
If an existing application cannot be identified, stop and inspect the refusal;
do not assume that replacing it can preserve its settings.

## Preserve settings during an update

1. Finish or abort any job through its owning controller, release control and
   leave the Pico idle. Disable its standalone schedule. Resolve STOP/fault
   states through the normal controls before updating.
2. Run:

   ```sh
   bash install_usb.sh upgrade --board pico2_w --yes
   ```

3. Choose the intended Pico from the list. The installer binds the transaction
   to its serial and physical port, checks compatibility, backs up flash and
   verifies retained settings after programming.
4. Older firmware may display **awaiting_bootsel**. Reconnect that same Pico
   to the same USB port while holding BOOTSEL. Run the exact continuation
   command printed by the installer. WsprryPi offers **Continue after BOOTSEL**.
5. After success, read back station settings, frequency, pins and firmware/source
   identity. Enable a schedule deliberately only after reviewing readiness.

Preparation or a BOOTSEL prompt is not a completed update. If interrupted,
keep the private transaction and backup directories and use the printed
same-board recovery command. Do not start a new image selection in place of
that transaction. Backups contain credentials; keep them private.

## Check an image without programming

```sh
bash install_usb.sh plan --branch devel --output ./pico-devel-bundle
```

The output directory must be new. Review the returned version, full source
revision and manifest. The saved verified bundle can be used offline with
`--bundle ./pico-devel-bundle` and the same explicit branch. A checksum verifies
integrity; it is not a signature. The ordinary download uses anonymous HTTPS.
If GitHub reports a rate limit, wait until the reported UTC retry time; the
installer does not silently choose an older image or another branch.

For destructive erase, see [Recovery and reset](maintain.md#recovery-and-reset).
