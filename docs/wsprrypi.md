# Use with WsprryPi

WsprryPi is the controller running on a Raspberry Pi. It sends complete transmission jobs to the Pico, which runs them with its own local timing. Start with the companion manual's [Add a WsprryPico](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html).

## Set up the Pi controller

Open **Setup → Fleet** in WsprryPi's browser interface. **Fleet** lists transmitters; a **member** is one listed device, and a saved **profile** records how the Pi connects to it. Choose **Use this device** to make a Pico the Pi's single selected output, or assign an independent **output schedule** to have the Pi run jobs on it. Saving a profile alone does not select the output or start a schedule.

The WsprryPi manual gives the detailed controller workflows:

- [Connect, identify and select a Pico](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#add-a-pico-and-manage-outputs) over USB or a supported network transport.
- [Assign independent output schedules](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/index.html#assign-an-output-schedule) and distinguish them from the Pi's single selected output.
- [Update Pico firmware through Fleet](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#install-or-update-pico-firmware-over-usb) and [reconcile an unresolved job](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#pico-status-and-recovery).
- [Configure command-line and INI-file connections](https://wsprry-pi.readthedocs.io/en/devel/Advanced_Operations/ini_configuration/transmitter_backends.html#pico-wtp). The command-line interface, or **CLI**, runs in a terminal; the **INI file** is WsprryPi's text configuration file. Follow the [Pi connection changes after a Pico rename](https://wsprry-pi.readthedocs.io/en/devel/Advanced_Operations/ini_configuration/transmitter_backends.html#after-a-pico-hostname-change) when changing a network address.

USB provides configuration and controller time without Wi-Fi. Administrative USB access does not take over an existing RF job. Plain LAN control and browser login have different [access boundaries](reference/security.md).

For device-side work, use this manual's [firmware installer](install.md), [connections](connect.md), [configuration](configure.md), [output limits](reference/output.md), [manual RF correction](reference/time.md) and [maintenance and recovery](maintain.md). Complete jobs execute locally; disconnecting the Pi does not convert or cancel them.

## Standalone installer on a WsprryPi host

Fleet handles its own selected-device maintenance when updating from the web page. To use the standalone command line on that same Pi, first give it exclusive access to the USB connection:

1. Finish or abort any job through its owning controller, release ownership and confirm output inactive. Disable the Pico's saved standalone schedule. Stopping the Pi service alone does not stop an accepted Pico job or schedule.
2. Pause WsprryPi:

   ```sh
   sudo systemctl stop wsprrypi
   ```

3. Run the [settings-preserving standalone update](install.md#preserve-settings-during-an-update) as your ordinary user. Select the intended USB serial and keep the cable connected through verification. The installer can use an existing compatible picotool or offer its own verified download and cleanup.
4. After a verified completed update, restart WsprryPi:

   ```sh
   sudo systemctl restart wsprrypi
   ```

5. Return to **Setup → Fleet**. Confirm the same full device ID and USB serial, the new installed version under **Pico firmware over USB**, an idle device and inactive output. Review readiness before starting another job.

If the installer reports an uncertain update or requires recovery, keep WsprryPi paused and complete the printed same-board recovery procedure before returning the Pico to host control. A downloaded-tool cleanup prompt does not remove the firmware backup.

## Ownership and schedules

Only one controller can hold the Pico's transmitter at a time. A job's **owner** is the browser, Pi controller or Pico scheduler that reserved it. Connection loss does not release control or stop an accepted job. Use the owning controller to abort and release, then confirm output inactive.

Before switching to a Pi-run schedule, disable the Pico's **Enable standalone schedules**, save and apply the change, then confirm it is disabled. Finish or abort any existing job and release control before starting the Pi schedule. The Pi's schedule and the Pico's saved schedule are separate; stopping one does not disable the other.

When returning to standalone use, pause and stop the Pi's output schedule, confirm inactive output and released control, then review and enable the Pico's schedule deliberately. See [standalone schedule settings](configure.md#frequency-and-schedules) and [stop controls](operate.md#status-stop-and-connection-loss).

Experimental-frequency permissions are also separate on the Pi and Pico; both must permit the requested frequency. See [Output and band limits](reference/output.md) before enabling an experimental range.
