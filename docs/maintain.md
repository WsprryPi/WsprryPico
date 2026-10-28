# Maintain and recover

## Rename or change Wi-Fi

### Change the hostname

A **hostname** is the Pico's network name, such as `pico-a.local`. Choose a different name for each Pico on the same network. Changing this name does not change the permanent device ID.

Disable the Pico's standalone schedule and resolve any pending, owned or active job before editing. On a page with saved progress, save and apply the schedule change, then confirm it is disabled. Turning off WsprryPi transmission alone does not disable the Pico's schedule.

1. In **Wi-Fi/Host → Device hostname**, read **Active** and **Saved**. Enter the **Full local hostname**, such as `pico-a.local`: one label of 1–63 ASCII letters, digits or hyphens followed by `.local`, starting and ending with a letter or digit. Spaces, underscores, extra labels, IP addresses and URLs are refused. Letters are stored in lowercase; a final root dot is removed.
2. Choose **Save hostname**. **Active** belongs to this boot; **Saved** belongs to the next boot. Saving does not restart or immediately change the address. Sign in again if requested and **Refresh** to confirm the saved result.
3. Copy any unsaved drafts before leaving. Choose **Reset Pico** in **Station Control → Transmitter status** once and confirm. A lost reply never triggers an automatic second restart.
4. Follow **Continue at pico-a.local (sign in again)**, using your chosen name. Sign in and refresh. Success requires the same full device ID, a different boot and the intended name as both **Active** and **Saved**. In **About this Pico / Diagnostics**, the device ID stays the same across restarts; the **boot ID** changes each time the Pico starts.

If a save reply is lost, it may already have succeeded. Read the saved name before considering another save; use **I reviewed the saved hostname; enable a new save** only after review. **Cancel reconnect checks** stops this tab's checks; it does not undo the saved name or cancel a requested restart. Checks end after about 90 seconds. If they time out, open the saved name manually or find the current IP in your router. For a duplicate name, reconnect by IP or [setup Wi-Fi](connect.md#request-setup-wi-fi-with-the-external-button) and choose a unique name; the Pico does not add a suffix automatically. A countdown or returning page alone does not establish restart or readiness.

**Use default hostname** fills the editor with the hardware-derived name; confirm, **Save hostname** and restart to apply it. Renaming preserves the device ID, setup Wi-Fi name, Wi-Fi password, retained clients and unrelated settings. The browser title starts with the confirmed active hostname, even when opened by IP. A pending or last-confirmed name is an observation; verify the device before entering a password.

If the controls say **Complete station setup first**, complete and apply the [station details](configure.md#station-identity) before retrying the rename. Browser access and login do not require station details. A certificate-bound name is read-only in this editor; follow the displayed reason rather than resetting to retry it. If a save reports a certificate-update error, restore time synchronization and follow the reported recovery instructions.

If WsprryPi connects over the network, follow its [connection-profile update procedure](https://wsprry-pi.readthedocs.io/en/devel/Advanced_Operations/ini_configuration/transmitter_backends.html#after-a-pico-hostname-change) after verifying the rename. Renaming a Fleet profile changes only its label.

### Change the Pico password

The default **Pico password** is the home Wi-Fi password saved during setup. Set a separate Pico password in the browser without changing the network password:

1. Sign in with the current Pico password. Open **Wi-Fi/Host → Pico password**.
2. Enter the new password in **New Pico password** and **Confirm new Pico password**. Use 8–63 characters; accented letters and emoji are not supported.
3. Select **Save Pico password**. Wait for confirmation, then sign in with the new password. Saving signs out all Pico browser logins; the new password survives a restart.

```{image} _static/images/pico-password.jpg
:alt: Pico password controls showing the Wi-Fi default status, New Pico password and Confirm new Pico password fields, Save Pico password, and Use Wi-Fi password as Pico password.
```

To return to the default, select **Use Wi-Fi password as Pico password** in the same section. Sign in again with the Wi-Fi password currently saved on the Pico. A separate Pico password is preserved when Wi-Fi or station details change. When the Wi-Fi default is selected, the Pico password follows changes to the saved Wi-Fi password.

If the save result is unconfirmed, try signing in with the new Pico password, then the previous password if the new one is refused. If neither password works, restart the Pico and try again. Read the password setting after signing in; do not automatically repeat a password save. If the current Pico password is forgotten, see [Recovery and reset](#recovery-and-reset); changing Wi-Fi credentials over USB does not clear a separate Pico password.

### Recover an occupied login

The Pico supports three browser or compatible controller logins at once. Closing or reloading a tab can leave its login occupying a slot until it expires. An active tab's unlocked icon beside the hostname locks that browser and requests logout after any current request finishes. If that tab is unavailable, use login retirement:

1. Open the Pico's control page at the same IP address or hostname used by the affected login.
2. Select the lock beside the hostname to open the password dialog. Open **Recover an occupied login**, then select **Inspect occupied logins**.
3. Choose the login to retire. The listed codes identify occupied logins, but a shared Pico password cannot tell you which operator owns each one. The page identifies a retained login from this tab when available; review the selection before continuing.
4. Enter the current Pico password, select **Authenticate and retire selected login**, and confirm the selected login may belong to another operator.
5. After confirmation, sign in again. If a previous save was unconfirmed, read the saved settings and review them against your draft before making another save.

Retirement ends only the selected login. It does not stop an accepted transmission or undo saved settings. If retirement is unconfirmed, keep the same selection for an explicit check; do not repeat an unconfirmed settings save. Inspection and retirement apply to the address and Wi-Fi interface currently in use.

### Change Wi-Fi

Wi-Fi credentials let the Pico join your network. The browser uses them as its default Pico password until you [set a separate Pico password](#change-the-pico-password). To update the Pico after changing your router's password, or to move it to another network:

1. Sign in with the current **Pico password**. If the Pico can no longer join your home network, reopen [setup Wi-Fi](connect.md#request-setup-wi-fi-with-the-external-button) or use the [USB Console](usb.md#request-setup-wi-fi-from-the-console) to request it. Join setup Wi-Fi, open **http://192.168.4.1/** and sign in there.
2. Open **Wi-Fi/Host**. Under **Wi-Fi network**, enter the network name and its current password. Keep the saved time server unless it needs changing, then select **Save Wi-Fi network**. The password must match that network's actual Wi-Fi password so the Pico can connect.
3. Keep the page open while it checks and saves the connection. If the result is unconfirmed, reconnect and select **Check saved result** before submitting another save. Follow any displayed restart instruction.
4. Once the new settings are applied, reconnect to the home network and open the Pico's current address. Sign in with your separate Pico password if you set one, or with the **new Wi-Fi password** if you use the default. Previous browser logins expire when the saved network credentials change.

WsprryPi's [USB settings controls](connect.md#usb-access-without-wi-fi) can update saved network credentials without a Pico browser login. USB can save, replace or explicitly delete the Wi-Fi connection without joining it; changes require the supported restart step. Deleting Wi-Fi retains station details, pins, schedules, hostname, a separate Pico password, any shutdown suspension and the record of WSPR slots already used. **Disconnect Wi-Fi** disconnects the current network connection; it does not delete the saved credentials.

## Recovery and reset

Read saved settings and try reconnecting before resetting. If the Pico password is forgotten, request setup Wi-Fi with the [external button](connect.md#request-setup-wi-fi-with-the-external-button) or [USB Console](usb.md#request-setup-wi-fi-from-the-console), join it, then open **http://192.168.4.1/recovery.html**. The recovery page does not require the forgotten password. Reset choices remove different data; read the device's confirmation carefully:

- **Reset provisioning…:** Clears the separate Pico password, network credentials, certificates, engineering access, Bluetooth device pairings and saved progress. It preserves applied station details, schedules and the record of WSPR slots already used, called the **consumed-slot watermark**. The time-server setting returns to its default. Join setup Wi-Fi again and enter the network details before resuming normal use.
- **Erase all settings…:** Also clears station details, schedules, the consumed-slot watermark and retained clock-rate estimates learned from the time server. Firmware and protected platform boot storage remain installed. The page calls this **Full erase**; it is distinct from USB full flash erase below.
- **USB full flash erase:** Removes firmware and **all persistent data in the entire 4 MiB flash**, including Wi-Fi credentials, bonds, settings, drafts and watermarks. It creates no backup and leaves the Pico in BOOTSEL.

Recovery pages are device-served at **http://192.168.4.1/recovery.html** during an available setup window. Anyone able to access this open setup network can use these recovery actions. The two checkboxes and typed confirmation phrase prevent accidents; they do not authenticate the operator. Keep transmission stopped. BOOTSEL is an installation gesture, not a runtime password reset button.

For deliberate full erase, identify the USB serial first, then replace `USB_SERIAL` with that exact selected serial:

```sh
bash install_usb.sh discover
bash install_usb.sh erase --device USB_SERIAL --board pico2_w --yes
```

The installer requires an idle, unowned device with its saved standalone schedule disabled or unconfigured. If prompted, reconnect the same board and port in BOOTSEL and use the printed recovery command. Success requires a full blank comparison and reports **erase_verified: true** and **4194304** erased bytes. An interrupted or failed check does not prove erasure. Existing host backups remain. [Install firmware again](install.md) before normal use.

## USB update backups and recovery

The standalone installer keeps private transactions and full-flash backups under `~/.local/state/wsprrypico-usb`. WsprryPi keeps its managed update state under `/var/lib/wsprrypi/pico-usb`. These files can contain Wi-Fi credentials, keys and bonds. Keep them outside Git and web-served directories; never attach a full backup or an unsanitized transaction to an issue.

Standalone history is bounded per state directory. Before a new transaction, completed history is limited to two records and unchanged/refused history to eight; either expires after seven days. Pruning happens on invocation, and the new transaction can temporarily add one record. Unresolved recovery records are retained. Eight unresolved records block new work rather than deleting the evidence needed to recover a board. WsprryPi also bounds completed caches across installer versions while retaining unresolved work.

If an update is incomplete, keep the selected Pico connected and use the exact same-board continuation command printed by the installer, including any requested BOOTSEL reconnect on the same port. Recovery uses the retained image; the public bootstrap fetches its original installer revision. In WsprryPi, use **Continue after BOOTSEL** or **Recover this update** as shown. Do not replace recovery with a new image selection, copy a backup to another board or restore flash blindly.

Downloaded-tool cleanup keeps firmware backups and pending transactions. An unresolved operation retains its managed picotool so the continuation remains usable. Success requires a verified final result and the expected running firmware identity; preparation or a successful USB command alone is incomplete.

## Support information

Record the firmware version and source revision, full stable device ID, connection method (browser, USB or network controller), transmission mode and frequency, exact error, and whether output is inactive or unknown. **About this Pico / Diagnostics** supplies the device and boot IDs. Use the [USB Console `INFO` reply](usb.md#read-the-address-and-web-service-status) or the verified installer result for firmware version and source revision. Use the saved-settings read controls and **Transmitter status → Refresh** for configuration, engine and clock status. Share only the fields needed for the issue through the [project issue tracker](https://github.com/WsprryPi/WsprryPico/issues). Remove passwords, certificates/private keys, transaction backups, private addresses and unsanitized captures before posting. Never post a full flash backup.

## Preserve diagnostic logging settings

[USB logging](usb.md#usb-diagnostic-logging) and [UDP logging](udp.md) have independent saved settings. Ordinary restarts, unrelated saves and compatible USB-installer upgrades preserve both; factory reset clears both. Disable UDP export and read it back before a downgrade. Retain the exact current/recovery bundle, and follow the shared installer's refusal if an older image reaches the UDP reservation. Do not choose erase as an automatic rollback.
