# Factory reset and reflash devel from a Raspberry Pi

This procedure erases a Pico 2 W connected by USB to a Raspberry Pi, then installs the current published devel firmware. Run the shell commands in the Raspberry Pi's terminal or SSH session. Erasing removes the Pico's firmware and saved data, including Wi-Fi credentials, passwords, station settings, schedules and calibration, without making a backup.

Command output starts with two blank lines. Messages, diagnostic listings and the returning shell prompt have a blank line between them; the installer's own headings retain its terminal formatting. Copy the complete shell blocks, including both parentheses, and exclude the example output.

## 1. Enter BOOTSEL mode

1. Disconnect power from the intended Pico, including any separate GPIO/VSYS supply.
2. Press and hold the Pico's onboard **BOOTSEL** button.
3. While holding BOOTSEL, connect the Pico to the Raspberry Pi with a USB data cable.
4. Release BOOTSEL after connecting.

Connect only the Pico being reset while using the label-based erase command below. If WsprryPi uses this connection, pause its service and close other USB clients as described in [Standalone installer on a WsprryPi host](../../docs/wsprrypi.md#standalone-installer-on-a-wsprrypi-host).

Check that the Raspberry Pi sees the BOOTSEL drive:

```sh
(
printf '\n\n'
trap 'printf "\n"' EXIT
lsblk -o NAME,TRAN,SIZE,LABEL,MOUNTPOINTS
)
```

The Pico 2 W presents a drive labelled `RP2350`. If it is absent, repeat the power-off and BOOTSEL sequence and check the USB data cable. Unplugging USB alone does not reset a Pico that still receives power through GPIO/VSYS. An error such as `can't find LABEL="RP2350"` means mounting failed before the erase UF2 could be copied.

## 2. Erase with flash_nuke

This command downloads Raspberry Pi's [flash_nuke UF2](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2), mounts the BOOTSEL drive if necessary and copies the UF2 to it. It uses `curl` and standard Linux disk tools; no SDK, compiler or picotool installation is needed for this erase step.

Run the whole block in Bash, including the opening `(` and closing `)`. These parentheses keep `set -euo pipefail` inside a subshell instead of changing the SSH login shell's options. Exclude Markdown backticks and terminal prompt text when copying:

```bash
(
set -euo pipefail
trap 'printf "\n"' EXIT

printf '\n\n'
pico_device=$(sudo blkid -L RP2350 || true)
if [ -z "$pico_device" ]; then
    printf '%s\n\n' 'No RP2350 drive found. Reconnect the Pico in BOOTSEL mode.'
    lsblk -o NAME,TRAN,SIZE,LABEL,MOUNTPOINTS
    exit 1
fi

printf '%s\n\n' \
    'flash_nuke: Executing a factory reset of the attached Pico 2 W.'

curl --fail --location \
    https://datasheets.raspberrypi.com/soft/flash_nuke.uf2 \
    --output /tmp/flash_nuke.uf2
printf '\n'

pico_mount=$(findmnt -rn -S "$pico_device" -o TARGET || true)
if [ -z "$pico_mount" ]; then
    sudo mkdir -p /mnt/pico-erase
    sudo mount -o sync "$pico_device" /mnt/pico-erase
    pico_mount=/mnt/pico-erase
fi

sudo cp /tmp/flash_nuke.uf2 "$pico_mount/"
sync
printf '%s\n%s\n\n' \
    'SUCCESS: flash_nuke.uf2 was copied to the Pico and host write' \
    'synchronization completed.'
printf '%s\n%s\n' \
    'Leave the Pico connected and allow several seconds for it to return to' \
    'BOOTSEL before installing firmware.'
)
```

A normal transfer looks like this; download sizes, timings and transfer rates vary:

```text


flash_nuke: Executing a factory reset of the attached Pico 2 W.

  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:--  0:00:05 --:--:--     0
  0     0    0     0    0     0      0      0 --:--:--  0:00:10 --:--:--     0
  0     0    0     0    0     0      0      0 --:--:--  0:00:11 --:--:--     0
100  112k  100  112k    0     0   7006      0  0:00:16  0:00:16 --:--:-- 28593

SUCCESS: flash_nuke.uf2 was copied to the Pico and host write
synchronization completed.

Leave the Pico connected and allow several seconds for it to return to
BOOTSEL before installing firmware.

```

A download, mount, copy or synchronization failure stops the block before the success message. The exit trap supplies the final blank line on both success and error paths, including the missing-drive path. After a successful transfer, the Pico runs the erase program and returns to BOOTSEL. Allow several seconds for USB to reconnect, then leave it connected for installation.

An error-free transfer is consistent with success, but this command does not independently read back the flash. Raspberry Pi's [erase program](https://github.com/raspberrypi/pico-examples/blob/master/flash/nuke/nuke.c) also writes a `NUKE` marker into the first flash page, so this path does not produce an entirely `0xff` image. The project's separate [full flash erase operation](usb-installer.md#full-flash-erase-contract) verifies every byte by readback.

## 3. Install the current published devel firmware

After flash_nuke, use a first installation (`install`). The `--replace-unidentified-application` option permits replacement of the erase program's `NUKE` marker; the installer still requires erased saved-state regions. Use this option here only after deliberately erasing this Pico.

Run the following as the ordinary Raspberry Pi user, with Python 3.10 or newer and `curl` available. The public bootstrap works without a local checkout, SDK or compiler. It reuses a compatible USB-enabled picotool or offers a verified download when needed; accept that download if no compatible tool is available. See [USB installation](../../docs/install.md#run-directly-with-curl) for tool permissions, selection and cleanup details.

The command prints a start message with two blank lines before it and one after it. The bootstrap download is quiet while errors remain visible. With both output streams attached to the terminal, the installer displays spaced stage headings, progress and its final verified result. Keep the output in the terminal to retain that readable presentation.

Copy the entire block, starting with `(` and ending with `)`. Omitting the opening parenthesis applies `set -euo pipefail` to the login shell and makes the closing parenthesis a syntax error, which can end the SSH session.

```bash
(
set -euo pipefail

printf '\n\n%s\n\n' \
    'WsprryPico: Installing the current published devel firmware.'

if curl --fail --silent --show-error --location \
    --proto '=https' --proto-redir '=https' \
    --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
    https://raw.githubusercontent.com/WsprryPi/WsprryPico/devel/scripts/install_usb.sh \
    | bash -s -- install --branch devel --board pico2_w --yes \
        --replace-unidentified-application
then
    :
else
    pico_status=$?
    printf '\n%s\n%s\n\n' \
        'ERROR: Firmware installation did not complete.' \
        'Review the messages above and use any printed recovery command.'
    exit "$pico_status"
fi
)
```

Confirm the intended Pico's USB serial and port if prompted. Keep it connected through programming and verification. `--branch devel` selects the current published devel CI image at execution time; it requires a valid published `ci-devel` index and verified firmware assets. An unavailable image or failed integrity check stops installation. Record the returned firmware version and source revision; the published image can lag newer commits on the branch.

A normal installation looks like this; firmware versions, source revisions, USB identities and transaction paths vary. If the bootstrap download or installer command fails, the block prints a separated error message and returns the failure status with a blank line before the shell prompt. The installer's own verified, recovery and refusal results retain its terminal formatting.

```text


WsprryPico: Installing the current published devel firmware.


WsprryPico USB installer

  Install firmware

Select the Pico to install:

  1. USB 1545B6EFBF78028C
     BOOTSEL; USB port 3-2
     First installation or recovery

Choose 1-1, or press Enter to cancel: 1
Selected Pico 1545B6EFBF78028C.
  Pico 1545B6EFBF78028C / USB port 3-2

Check USB programming tools

  Verified retained picotool 2.3.1; reusing the private managed copy.

Check firmware

  Verify the selected image, checksums and source. This may take a moment...
  Verified firmware 0.1.0-ci.39999086602.1 / source 9b946f459e02

Install firmware

  The selected Pico is in BOOTSEL. Keep USB connected until programming and
  verification finish.

  Check existing flash before installing. Existing saved data will stop this
  installation.

  Back up flash and verify the backup...
  Program firmware. Keep USB connected...
  Verify firmware and preserved flash...
  Wait for firmware startup and verify saved settings...

Firmware verified

  Version 0.1.0-ci.39999086602.1
  Saved flash preserved; firmware startup verified.
  Pico 1545B6EFBF78028C
  Transaction:
  /home/pi/.local/state/wsprrypico-usb/1545B6EFBF78028C-8di8gduo/transaction.json

```

Completion requires the installer's verified result and expected running-firmware identity. If it reports recovery is required, use its printed same-board continuation command. After verified completion, continue with [first Wi-Fi setup](../../docs/connect.md#first-wi-fi-connection). Review pins, frequency, calibration, and schedules before transmitting. If WsprryPi was paused, follow the linked host procedure to restore its service after reviewing the reset Pico's settings.
