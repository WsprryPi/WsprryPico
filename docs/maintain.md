# Maintain and recover

## Rename or change Wi-Fi

### Change the hostname

Disable the Pico's standalone schedule and resolve any pending, owned or active
job before editing. On a page with saved progress, save and apply the schedule
change, then confirm it is disabled. Turning off WsprryPi transmission alone
does not disable the Pico's schedule.

1. In **Wi-Fi/Host → Device hostname**, read **Active** and **Saved**. Enter
   the **Full local hostname**, such as `pico-a.local`: one label of 1–63 ASCII
   letters, digits or hyphens followed by `.local`, starting and ending with
   a letter or digit. Spaces, underscores, extra labels, IP addresses and URLs
   are refused. Letters are stored in lowercase; a final root dot is removed.
2. Choose **Save hostname**. **Active** belongs to this boot; **Saved** belongs
   to the next boot. Saving does not restart or immediately change the address.
   Sign in again if requested and **Refresh** to confirm the saved result.
3. Copy any unsaved drafts before leaving. Choose **Restart device** once and
   confirm. A lost reply never triggers an automatic second restart.
4. Follow **Continue at pico-a.local (sign in again)**, using your chosen name.
   Sign in and refresh. Success requires the same full device ID, a different
   boot and the intended name as both **Active** and **Saved**.

If a save reply is lost, it may already have succeeded. Read the saved name
before considering another save; use **I reviewed the saved hostname; enable
a new save** only after review. **Cancel reconnect checks** stops this tab's
checks; it does not undo the saved name or cancel a requested restart. Checks
end after about 90 seconds. If they time out, open the saved name manually or
find the current IP in your router. For a duplicate name, reconnect by IP or
[setup Wi-Fi](connect.md#request-setup-wi-fi-with-the-external-button) and choose
a unique name; the Pico does not add a suffix automatically. A countdown or
returning page alone does not establish restart or readiness.

**Use default hostname** fills the editor with the hardware-derived name;
confirm, **Save hostname** and restart to apply it. Renaming preserves the
device ID, setup Wi-Fi name, Wi-Fi password, retained clients and unrelated
settings. The browser title starts with the confirmed active hostname, even
when opened by IP. A pending or last-confirmed name is an observation; verify
the device before entering a password.

Complete station commissioning if only Wi-Fi setup is saved. Engineering
certificate-bound names are read-only here and require matching replacement
credentials through provisioning. For consumer certificate-update refusals,
restore time synchronization and follow the reported recovery error. Keep
certificate verification enabled.

If WsprryPi connects over the network, follow its
[connection-profile update procedure](https://wsprry-pi.readthedocs.io/en/devel/Advanced_Operations/ini_configuration/transmitter_backends.html#after-a-pico-hostname-change)
after verifying the rename. Renaming a Fleet profile changes only its label.

### Change the Pico password

The default **Pico password** is the home Wi-Fi password saved during setup. Set a separate Pico password in the browser without changing the network password:

1. Sign in with the current Pico password. Open **Wi-Fi/Host → Pico password**.
2. Enter the new password in **New Pico password** and **Confirm new Pico password**. Use 8–63 characters; accented letters and emoji are not supported.
3. Select **Save Pico password**. Wait for confirmation, then sign in with the new password. Saving signs out all Pico browser logins; the new password survives a restart.

```{figure} _static/images/pico-password.jpg
:alt: Pico password controls showing the Wi-Fi default status, New Pico password and Confirm new Pico password fields, Save Pico password, and Use Wi-Fi password as Pico password.
:target: _static/images/pico-password.jpg

The **Pico password** section under **Wi-Fi/Host**. Both new-password fields are empty. Software preview; select the image to enlarge it.
```

To return to the default, select **Use Wi-Fi password as Pico password** in the same section. Sign in again with the Wi-Fi password currently saved on the Pico. A separate Pico password is preserved when Wi-Fi or station details change. When the Wi-Fi default is selected, the Pico password follows changes to the saved Wi-Fi password.

If the save result is unconfirmed, try signing in with the new Pico password, then the previous password if the new one is refused. If neither password works, restart the Pico and try again. Read the password setting after signing in; do not automatically repeat a password save. If the current Pico password is forgotten, see [Recovery and reset](#recovery-and-reset); changing Wi-Fi credentials over USB does not clear a separate Pico password.

### Change Wi-Fi

Wi-Fi credentials let the Pico join your network. The browser uses them as its default Pico password until you [set a separate Pico password](#change-the-pico-password). To update the Pico after changing your router's password, or to move it to another network:

1. Sign in with the current **Pico password**. If the Pico can no longer join your home network, reopen [setup Wi-Fi](connect.md#request-setup-wi-fi-with-the-external-button) or use the [USB Console](usb.md#request-setup-wi-fi-from-the-console) to request it. Join setup Wi-Fi, open **http://192.168.4.1/** and sign in there.
2. Open **Wi-Fi/Host**. Under **Wi-Fi network**, enter the network name and its current password. Keep the saved time server unless it needs changing, then select **Save Wi-Fi network**. The password must match that network's actual Wi-Fi password so the Pico can connect.
3. Keep the page open while it checks and saves the connection. If the result is unconfirmed, reconnect and select **Check saved result** before submitting another save. Follow any displayed restart instruction.
4. Once the new settings are applied, reconnect to the home network and open the Pico's current address. Sign in with your separate Pico password if you set one, or with the **new Wi-Fi password** if you use the default. Previous browser logins expire when the saved network credentials change.

WsprryPi's [USB settings controls](connect.md#usb-access-without-wi-fi) can update saved network credentials without a Pico browser login. USB can save, replace or explicitly delete the Wi-Fi connection without joining it; changes require the supported restart step. Deleting Wi-Fi retains station, pins, schedules, hostname, a separate Pico password, STOP and watermarks. **Disconnect Wi-Fi** changes runtime connectivity; it is not credential deletion.

## Recovery and reset

Prefer readback and reconnect before resetting. Reset choices remove different
data; read the device's confirmation carefully:

- **Reset provisioning…:** Clears the separate Pico password, network credentials, certificates, engineering access, Bluetooth bonds and saved progress. It preserves station details, schedules and the consumed-slot watermark; the retained time-server setting returns to its default.
- **Erase all settings…:** Also clears station details, schedules, the consumed-slot
  watermark and retained NTP learning. Firmware and protected platform boot
  storage remain installed. The page calls this **Full erase**; it is distinct
  from USB full flash erase below.
- **USB full flash erase:** Removes firmware and **all persistent data in the
  entire 4 MiB flash**, including Wi-Fi credentials, bonds, settings, drafts and
  watermarks. It creates no backup and leaves the Pico in BOOTSEL.

Recovery pages are device-served at **http://192.168.4.1/recovery.html** during
an available setup window. Anyone able to access this open setup network can
use these recovery actions. The two checkboxes and typed confirmation phrase
prevent accidents; they do not authenticate the operator. Keep transmission
stopped. BOOTSEL is an installation gesture, not a runtime password reset button.

For deliberate full erase, identify the USB serial first, then replace
`USB_SERIAL` with that exact selected serial:

```sh
bash install_usb.sh discover
bash install_usb.sh erase --device USB_SERIAL --board pico2_w --yes
```

The installer requires an idle, unowned device with its saved standalone
schedule disabled or unconfigured. If prompted, reconnect the same board and
port in BOOTSEL and use the printed recovery command. Success requires a full
blank comparison and reports **erase_verified: true** and **4194304** erased
bytes. An interrupted or failed check does not prove erasure. Existing host
backups remain. [Install firmware again](install.md) before normal use.

## USB update backups and recovery

The standalone installer keeps private transactions and full-flash backups
under `~/.local/state/wsprrypico-usb`. WsprryPi keeps its managed update state
under `/var/lib/wsprrypi/pico-usb`. These files can contain Wi-Fi credentials,
keys and bonds. Keep them outside Git and web-served directories; never attach
a full backup or an unsanitized transaction to an issue.

Standalone history is bounded per state directory. Before a new transaction,
completed history is limited to two records and unchanged/refused history to
eight; either expires after seven days. Pruning happens on invocation, and the
new transaction can temporarily add one record. Unresolved recovery records
are retained. Eight unresolved records block new work rather than deleting
the evidence needed to recover a board. WsprryPi also bounds completed caches
across installer versions while retaining unresolved work.

If an update is incomplete, keep the selected Pico connected and use the exact
same-board continuation command printed by the installer, including any
requested BOOTSEL reconnect on the same port. Recovery uses the retained image;
the public bootstrap fetches its original installer revision. In WsprryPi, use
**Continue after BOOTSEL** or **Recover this update** as shown. Do not replace
recovery with a new image selection, copy a
backup to another board or restore flash blindly.

Downloaded-tool cleanup keeps firmware backups and pending transactions. An
unresolved operation retains its managed picotool so the continuation remains
usable. Success requires a verified final result and the expected running
firmware identity; preparation or a successful USB command alone is incomplete.

## Support information

Record firmware/source identity, full stable device ID, transport, engine and
clock, mode/frequency, exact error, and whether output is inactive or unknown.
Use **About this Pico / Diagnostics** and authoritative saved readback. Share
only the fields needed for the issue through the
[project issue tracker](https://github.com/WsprryPi/WsprryPico/issues).
Remove passwords, certificates/private keys, transaction backups, private
addresses and unsanitized captures before posting. Never post a full flash backup.
