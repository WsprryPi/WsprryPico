# Use with WsprryPi

WsprryPi sends complete jobs; the Pico owns their execution and symbol timing.
Use a WsprryPi version that supports the transport and management features you
need. Start with the companion manual's
[Add a WsprryPico](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html).

## Set up the Pi controller

The WsprryPi manual owns the controller workflows:

- [Connect, identify and select a Pico](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#add-a-pico-and-manage-outputs)
  over USB or a supported network transport.
- [Assign independent output schedules](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/index.html#assign-an-output-schedule)
  and distinguish them from the Pi's single selected output.
- [Update Pico firmware through Fleet](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#install-or-update-pico-firmware-over-usb)
  and [reconcile an unresolved job](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#pico-status-and-recovery).
- [Configure CLI and INI connections](https://wsprry-pi.readthedocs.io/en/devel/Advanced_Operations/ini_configuration/transmitter_backends.html#pico-wtp),
  including [Pi connection changes after a Pico rename](https://wsprry-pi.readthedocs.io/en/devel/Advanced_Operations/ini_configuration/transmitter_backends.html#after-a-pico-hostname-change).

USB provides configuration and controller time without Wi-Fi. Administrative
USB access does not take over an existing RF job. Plain LAN control and browser
login have different [access boundaries](reference/security.md).

For device-side work, use this manual's [firmware installer](install.md),
[connections](connect.md), [configuration](configure.md),
[output limits](reference/output.md), [manual RF correction](reference/time.md)
and [maintenance and recovery](maintain.md). Complete jobs execute locally;
disconnecting the Pi does not convert or cancel them.

## Standalone installer on a WsprryPi host

Fleet handles its own selected-device maintenance when updating from the web
page. To use the standalone command line on that same Pi, first give it
exclusive access to the USB connection:

1. Finish or abort any job through its owning controller, release ownership
   and confirm output inactive. Disable the Pico's saved standalone schedule.
   Stopping the Pi service alone does not stop an accepted Pico job or schedule.
2. Pause WsprryPi:

   ```sh
   sudo systemctl stop wsprrypi
   ```

3. Run the [settings-preserving standalone update](install.md#preserve-settings-during-an-update)
   as your ordinary user. Select the intended USB serial and keep the cable
   connected through verification. The installer can use an existing compatible
   picotool or offer its own verified download and cleanup.
4. After a verified completed update, restart WsprryPi:

   ```sh
   sudo systemctl restart wsprrypi
   ```

5. Return to **Setup → Fleet**. Confirm the same full device ID and USB serial,
   the new installed version under **Pico firmware over USB**, an idle device
   and inactive output. Review readiness before starting another job.

If the installer reports an uncertain update or requires recovery, keep
WsprryPi paused and complete the printed same-board recovery procedure before
returning the Pico to host control. A downloaded-tool cleanup prompt does not
remove the firmware backup.

## Ownership and schedules

One local job service owns output. A controller sends a complete job before
arming; the Pico owns symbol timing and cleanup. Connection loss does not
release ownership or stop an accepted job. Use its owning controller to abort
and release, then confirm output inactive.

Review Pico standalone schedule enablement when switching to host scheduling.
Do not expect an enabled standalone schedule and a host job to run at the same
time. Host and Pico frequency opt-ins are separate and both must allow an
experiment. Recorded member tests do not establish full fleet parity or all
transport/firmware combinations.
