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

### Change Wi-Fi

Change Wi-Fi through its trial/save controls and check the confirmed result
before leaving the old connection. A new password becomes the consumer login
password after activation. USB can save, replace or explicitly delete the Wi-Fi
connection without joining it; changes require the supported restart step.
Deleting Wi-Fi retains station, pins, schedules, hostname, STOP and watermarks.
**Disconnect Wi-Fi** changes runtime connectivity; it is not credential deletion.

## Recovery and reset

Prefer readback and reconnect before resetting. Reset choices remove different
data; read the device's confirmation carefully:

- **Reset provisioning…:** Clears network credentials, certificates, engineering
  access, Bluetooth bonds and saved progress. It preserves station details,
  schedules and the consumed-slot watermark; the retained time-server setting
  returns to its default.
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
