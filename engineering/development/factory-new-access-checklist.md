# Factory-new access checklist

Use this checklist on a Pico 2 W with firmware containing the Wi-Fi-only access, separate Pico password and connected-client setup-Wi-Fi changes from commit `3ffd65ec5c0c9856739dd5707f1df9716aace5ee`, or a reviewed descendant. Allow about 45 minutes for the main pass, including the timed checks. This is an access test; keep schedules disabled and do not start a radio job. An unchecked box is unverified, not a pass.

## 1. Prepare the Mac or Raspberry Pi

- [ ] Use native macOS or Linux with Python 3.10 or newer, curl and USB access for your ordinary user. A Raspberry Pi running 64-bit Raspberry Pi OS supports the installer's managed picotool download; other Linux architectures need an existing compatible USB-enabled picotool.
- [ ] Connect the Pico to that computer with a USB data cable. Close other programs using its serial ports and stop any owning controller from reconnecting during the test. If WsprryPi runs on this USB host, follow [Standalone installer on a WsprryPi host](../../docs/wsprrypi.md#standalone-installer-on-a-wsprrypi-host) to pause and later restore its service.
- [ ] Have a Wi-Fi-capable computer or phone for the browser checks. A headless Pi can handle USB while a phone handles Wi-Fi. Keep the Pi on Ethernet if you need continuous SSH access; switching its only Wi-Fi connection can disconnect SSH.
- [ ] Use a fresh private browser window and close old Pico tabs so previous drafts or connection receipts do not affect the factory-new pass. Keep the same window open while any save is awaiting confirmation.
- [ ] While the host still has Internet access, verify the published devel image with the plan command below. Record its returned `version`, `source` and UF2 SHA-256, plus the host OS and browser/version. Confirm the source contains the changes listed above; published Beta 1 predates them. A missing download or a failed plan is not a usable test image. Keep passwords out of the test record.

Run the following from the repository root on either host. A standalone downloaded `install_usb.sh` works with the same arguments; omit `scripts/` in that case.

```sh
bash scripts/install_usb.sh discover
bash scripts/install_usb.sh plan --branch devel
```

Record the intended board's USB serial from discovery. In the erase and install commands below, replace `USB_SERIAL` with that exact serial and `FIRMWARE_VERSION` with the version returned by the successful plan. These are placeholders, not literal arguments. The initial published build containing the changes is `0.1.0-ci.39953536554.1`, source `3ffd65ec5c0c9856739dd5707f1df9716aace5ee`.

## 2. Erase and install

- [ ] Finish or abort any transmission and release its controller. Disconnect the Pico, hold BOOTSEL while reconnecting it to the same USB port, then release BOOTSEL.
- [ ] Run discovery again. Confirm the intended USB serial and `bootsel` mode. Substitute that exact serial for `USB_SERIAL` below. This operation removes firmware and all saved data without making a backup.

```sh
bash scripts/install_usb.sh erase --device USB_SERIAL --board pico2_w --yes
```

- [ ] Accept a verified picotool download if needed. Wait for the full-erase confirmation: `erase_verified: true` and `erased_bytes: 4194304`, or the terminal message that all 4 MiB is blank. Leave the Pico connected in BOOTSEL. An interrupted operation or a recovery prompt is not a verified erase; follow its printed continuation command.
- [ ] Install the exact version recorded before erasing, using the command below on either Mac or Pi. This works from a terminal on a headless Pi and uses the installer's verified tool-download/reuse path. No SDK, compiler, desktop file manager or separate picotool command is required.

```sh
bash scripts/install_usb.sh install --branch devel --version FIRMWARE_VERSION \
  --device USB_SERIAL --board pico2_w --yes
```

- [ ] Wait for the installer's verified completion and running-firmware identity. A recovery prompt or uncertain result must be resolved with its printed continuation before starting the access checks. Use [USB INFO](../../docs/usb.md#read-the-address-and-web-service-status) to record the actual `firmware`, `revision` and full `device_id`. Confirm that the firmware is the intended test build before judging the results below.

## 3. Check the empty Pico and connected-client retention

- [ ] Join the open `WsprryPico-XXXXXX` network. No Wi-Fi join password should be required. Keep the connection when the operating system reports no Internet. Keep the client awake and prevent automatic switching to another network during timed checks.
- [ ] Open `http://192.168.4.1/`. Expect the initial Wi-Fi setup form, with no saved station or network and `pool.ntp.org` suggested as the time server. Record whether a captive-portal window opened automatically; the full browser address must also work.
- [ ] Before saving anything, close the browser but remain associated with the Pico's Wi-Fi for **12 minutes**. Do not power-cycle the Pico, send another setup request or leave another browser polling it. Confirm in the operating system that this client remains connected to the Pico.
- [ ] Reopen `http://192.168.4.1/`. The setup form must still load. A vanished setup network or inaccessible page while the client remained associated fails this check.

## 4. Save Wi-Fi only and open the home-network page

- [ ] Enter a valid home Wi-Fi network name and its actual Wi-Fi password. Leave the suggested time server unchanged. Enter no station information. Select **Connect to Wi-Fi** once.
- [ ] Wait for **Wi-Fi connected** and **Wi-Fi saved and connected.** If the result is uncertain, reconnect to setup Wi-Fi and let the same tab check the result before considering another save.
- [ ] Return the browser device to the home network. Find the Pico's current IP in the router or USB INFO. Open `http://YOUR_PICO_IP/` using that numeric address. Expect a **Pico password** field; no station form completion or clock synchronization should be required first.
- [ ] Sign in with the home Wi-Fi password saved in the previous step. Confirm that the page loads authenticated settings, Wi-Fi/Host shows the intended network, station information remains empty and no schedule is enabled.
- [ ] Power-cycle the Pico without holding BOOTSEL. Find its current IP again and repeat the home-network login. It must still work with no station information saved.

## 5. Change the Pico password independently

- [ ] Sign in from two browser tabs or windows, reading settings in each. In one, open **Wi-Fi/Host → Pico password**. Expect the status to say it uses the saved Wi-Fi password by default.
- [ ] Enter different values in **New Pico password** and **Confirm new Pico password**, then select **Save Pico password**. Expect an inline mismatch error, with no password change or sign-out.
- [ ] Enter the same new password in both fields, distinct from the Wi-Fi password, using 8–63 printable ASCII characters. Save once. Expect confirmation, cleared password fields and sign-out in the initiating tab.
- [ ] Select **Refresh** in the second tab. Its old login must be rejected and require sign-in again. Close unused test tabs so login slots do not obscure later checks.
- [ ] Try the old Wi-Fi password as the Pico login: it must fail. Wait at least one second between login attempts. The new Pico password must succeed. The Pico must remain connected to the same home Wi-Fi with the same saved network credentials.
- [ ] Power-cycle the Pico, find its current IP and sign in using the new Pico password. It must persist; station information must still be empty.
- [ ] If a second working Wi-Fi network is available, save its real credentials under **Wi-Fi network**, follow the connection instructions, then sign in at the new address using the separate Pico password. The separate password must survive the network change. Otherwise mark this network-change check unverified.

## 6. Reopen setup Wi-Fi on the configured Pico

Use the verified USB Console on either host. Discovery identifies Console under port role `"0"`; WTP is `"2"` and management is `"4"`. Follow [USB Console instructions](../../docs/usb.md#find-and-open-the-console-on-macos-or-linux), with DTR enabled and LF/newline command endings. In `screen`, send each command with **Ctrl+J**; exit with **Ctrl+A**, then **backslash**, then **y**.

```text
INFO
ACCESS SOFTAP YOUR_FULL_DEVICE_ID
```

- [ ] Replace `YOUR_FULL_DEVICE_ID` with the full 32-character `device_id` from INFO, not the USB serial. Expect `"ok":true` and `"join_grace_ms":120000`. Join the Pico's setup Wi-Fi within two minutes of its activation.
- [ ] Confirm the setup network is still open. Open `http://192.168.4.1/`: a configured Pico must present the control-page login. Sign in using the separate Pico password and confirm the same device ID and empty station information.
- [ ] Close the browser and remain associated with setup Wi-Fi for **12 minutes**, keeping the client awake. Send no additional setup request and do not restart the Pico. Keep its home network available throughout.
- [ ] Reopen the page and sign in if the browser login expired. The Wi-Fi association must remain usable even with no browser traffic or an expired login. Home-network availability must not evict the associated setup client.
- [ ] Disconnect **every** client from the Pico's setup Wi-Fi, including phones that might automatically rejoin. Record the final disconnect time. Keep the Pico powered, its home network working, and all clients off setup Wi-Fi for **11 minutes**. Scanning the network list is allowed; joining it restarts the inactivity interval.
- [ ] Confirm setup Wi-Fi has closed and the Pico's home-network page still works with the separate password. Refresh the Wi-Fi scan; an old SSID remaining in a cached list does not prove the AP is still available. If a client can still join after the interval, first check for another associated client and record that finding.

## 7. Restore and verify the password default

- [ ] On the home-network page, sign in with the separate Pico password. Select **Wi-Fi/Host → Pico password → Use Wi-Fi password as Pico password**. Expect confirmation and sign-out.
- [ ] The separate password must now fail, and the Wi-Fi password **currently saved on the Pico** must succeed. If you changed networks, use that network's password. Confirm the setting reports the Wi-Fi default.
- [ ] Power-cycle and confirm the default login still works, with station information empty and schedules disabled. Close the serial terminal and unused browser tabs when finished. If you paused WsprryPi, restore its service using the same [standalone-installer procedure](../../docs/wsprrypi.md#standalone-installer-on-a-wsprrypi-host).

## Additional timing checks

- [ ] **Rejoin resets inactivity:** Request setup Wi-Fi again, join, then disconnect all clients. Rejoin after nine minutes and remain connected until at least 12 minutes after rejoining. The AP must stay usable beyond the previous disconnect deadline. After the final disconnect, allow a fresh ten-minute inactivity interval.
- [ ] **Unanswered Console request expires:** Once setup Wi-Fi has closed and the home network is stable, send one new Console request. Do not let any device join. After more than two minutes from actual activation, the setup network should close. This is the Console join window; the initial factory-new, unjoined window is ten minutes.

## Record a failure

Record the failed checkbox, host and browser versions, USB serial, full device ID, firmware/revision and UF2 hash, exact URL or Console command, exact error, and timestamps for timed checks. Distinguish an expired browser login from a lost Wi-Fi association. Save relevant INFO fields and screenshots without passwords. A lost save reply is unconfirmed; read back the result or follow [Pico password save recovery](../../docs/maintain.md#change-the-pico-password) before another explicit save. Leave physical results marked unverified until this checklist has actually run on the identified Pico.
