# Recover browser access over USB

## Computer requirements

You need a USB **data** cable and a computer with a serial terminal: an application that sends text commands to the Pico and displays its replies. The browser route below supplies that terminal without installing a desktop terminal application. WsprryPi is not required. Choose the route for your computer:

| Computer | USB Console route |
| --- | --- |
| Windows | Use desktop **Google Chrome** and the [browser terminal](#open-the-console-in-a-browser). This route does not use WSL or the installer script. |
| Mac or native Linux | Use the [browser terminal](#open-the-console-in-a-browser), or [find and open the Console from a terminal](#find-and-open-the-console-on-macos-or-linux). |

The browser route uses [Web Serial, which Chrome provides on Windows, macOS and Linux](https://developer.chrome.com/docs/capabilities/serial#browser_support), to give the terminal site access to the USB port you select. The command-line discovery and installer tools require **macOS or native Linux**; Windows, Git Bash and WSL are unsupported by those tools.

## When to use USB recovery

Use this procedure when a standalone Pico has joined your Wi-Fi but its browser page will not open, or when you need setup Wi-Fi and have no external button fitted. These steps read diagnostics and request temporary setup Wi-Fi; they do not reinstall firmware or erase settings.

One USB cable provides four separate serial ports on logging-capable firmware. Older firmware provides three. Identify the **Console** before connecting; a port's number or position in a list does not establish its role.

| Connection | USB interface number | Purpose |
| --- | --- | --- |
| Console | 0 | Human-readable commands such as `INFO`, `STATUS` and `ABORT` |
| WTP | 2 | Transmission jobs sent by controller software using the WsprryPi Transmitter Protocol |
| Management | 4 | Saved settings and time supplied by controller software |
| Logging | 6 | Diagnostic records collected independently of Console |

If the Pico is already controlled by WsprryPi, use [its Fleet settings controls](connect.md#usb-access-without-wi-fi). Finish or abort any existing job through its owning controller and confirm inactive output before attempting setup. Losing the browser connection does not stop a job.

## Open the Console in a browser

1. Connect the Pico with a USB **data** cable, without holding **BOOTSEL**. Close any other serial terminal using this Pico. Open [SerialTerminal.com](https://www.serialterminal.com/) in desktop **Google Chrome**. Your computer needs Internet access to load this third-party site; the Pico does not need Wi-Fi. Firefox and Safari do not support this procedure.
2. Click the **gear** button. Set **DTR on**, with **RTS**, **dtrDsr** and **rtsCts off**. If DTR is already checked on a first visit, uncheck and check it again to ensure the site saves that setting. Leave **Advanced Settings** collapsed. Click the **monitor** button to open the **Advanced terminal** view, which retains the long diagnostic reply; the basic terminal truncates it.

   ```{figure} _static/images/usb-browser-settings.jpg
   :alt: SerialTerminal.com settings with DTR checked and RTS, dtrDsr and rtsCts unchecked.

   Serial signal settings used for the connected Pico. The monitor button beside Home opens the Advanced terminal.
   ```

   ```{figure} _static/images/usb-windows-settings.png
   :alt: SerialTerminal.com on Windows with DTR checked and RTS, dtrDsr and rtsCts unchecked.
   :width: 650px

   The same signal settings in Windows Chrome: DTR is the checked box.
   ```

3. Set **Baud** to **115200**. Check **send with /n** and uncheck **send with /r**; those are the site's labels for newline and carriage return. Use the command box beside **Send**, rather than typing into the lower terminal area.
4. Identify the Console port before clicking **Connect**. On **macOS or Linux**, use the discovery steps in the next section and copy the port under **"0"**. On **Windows**, open **Device Manager → Ports (COM & LPT)**. The Pico's ports can appear as **USB Serial Device (COMn)**. Open each candidate's **Properties → Details → Hardware Ids**, and find the entry containing **MI_00**: that is the Console. **MI_02** is WTP, **MI_04** is management and **MI_06** is Logging. Record the Console's **COM** number. If several Picos are connected, also verify which USB device the port belongs to. Do not choose an arbitrary COM port if you cannot identify it.

   ```{figure} _static/images/usb-windows-console.png
   :alt: Windows Device Manager properties for USB Serial Device COM6, with Hardware Ids showing MI_00 for the Console interface.
   :width: 407px

   Windows identifies this Console as COM6 and MI_00. Your COM number can differ.
   ```

5. Click **Connect**, select that exact port in Chrome's chooser, then click the chooser's **Connect**. Windows Chrome can show a role name such as **WsprryPico - WsprryPico Console (COM6)**. Other systems may label all connections simply **WsprryPico**. In either case, match the port path or COM number you identified. The Mac example uses `cu.usbmodem101`; port names and numbers vary.

   ```{figure} _static/images/usb-browser-port.jpg
   :alt: Chrome's serial-port chooser with WsprryPico cu.usbmodem101 selected, alongside the other Pico ports.

   The Console port selected after checking USB interface identity on this Mac. Windows shows COM port names.
   ```

   ```{figure} _static/images/usb-windows-port.png
   :alt: Windows Chrome serial-port chooser with WsprryPico Console COM6 selected, distinct from Management COM10 and WTP COM9.
   :width: 450px

   The Console COM6 entry selected in Windows Chrome after checking MI_00 in Device Manager.
   ```

6. Type uppercase `INFO` in the command box and click **Send**. Console commands are case-sensitive. Wait for the JSON reply. Scroll **inside the terminal output** back to its start to find `"ok":true`, `device_id`, `revision` and `firmware`. Use the [diagnostic field guide](#read-the-address-and-web-service-status) below. Before sending another command, wait for the current reply to finish.

   ```{figure} _static/images/usb-browser-info.jpg
   :alt: Advanced browser terminal showing an INFO command and the beginning of a real Pico JSON diagnostic reply, with ok true, device_id, revision and firmware fields.

   A connected Pico answering INFO in Chrome on macOS. Settings and firmware values will differ on your Pico.
   ```

   ```{figure} _static/images/usb-windows-info.png
   :alt: Windows Chrome Advanced terminal showing uppercase INFO and a real successful Pico reply with device_id, revision and firmware.

   The start of an INFO reply in Windows Chrome. Scroll inside the terminal to read the rest of the reply, then return to these identity fields.
   ```

Enter subsequent Console commands in the same box and click **Send**. When finished, close the terminal tab to release the port. A failed connection, refused command or no reply needs a check of the selected Console port, uppercase command spelling, **DTR** (the serial connection's ready signal), newline setting and whether another program has the port open. If the terminal website itself will not load, resolve the computer's Internet or DNS problem before continuing.

## Find and open the Console on macOS or Linux

1. Use a **Mac or native Linux computer** for these commands. Connect the Pico with a USB **data** cable, without holding **BOOTSEL**. Close any other serial terminal using this Pico.
2. Open a terminal in the folder containing the `install_usb.sh` file used during installation. Run:

   ```sh
   bash install_usb.sh discover
   ```

   If you no longer have that file, follow [Get the installer and identify the Pico](install.md#get-the-installer-and-identify-the-pico), then return here. Discovery reads USB identity information without programming the Pico. The public bootstrap needs Internet access to download its tools; the Pico itself does not need Wi-Fi for USB diagnostics.
3. Find your Pico's USB serial in the result. Its mode should be **application**. Under **ports**, **"0" is the Console**, **"2" is WTP**, and **"4" is management**, and **"6" is Logging** when supported. For example, this synthetic Linux result identifies `/dev/ttyACM0` as the Console:

   ```json
   {"serial":"0123456789ABCDEF","mode":"application","parent":"1-2","ports":{"0":"/dev/ttyACM0","2":"/dev/ttyACM1","4":"/dev/ttyACM2"}}
   ```

   Your port names will differ. On macOS they usually begin `/dev/cu.usbmodem`. Copy the path reported under **"0"** for your selected Pico. If the mode is **bootsel**, reconnect without holding BOOTSEL. If no Pico appears, check the data cable and USB permissions.
4. If using the browser terminal, return to its port-selection step with the identified path. Otherwise, open that path in a serial terminal at **115200 baud, 8 data bits, no parity, 1 stop bit, no flow control**, with **DTR enabled** and commands ending in **LF (newline)**. If `screen` is available, enter the following, replacing `/dev/ttyACM0` with your actual Console path:

   ```sh
   screen -fn /dev/ttyACM0 115200
   ```

   On macOS, use the `/dev/cu.usbmodem...` path from discovery in the same command. If `screen` is missing on Debian, Ubuntu or Raspberry Pi OS, install it with `sudo apt install screen`, then retry. On other systems, use a serial terminal with the settings above. A permission-denied error on Linux needs serial-device access for your ordinary user. A busy-port error means another program has the port open.

## Read the address and web-service status

Type `INFO`, then send the command. In the browser terminal, use the command box and **Send** with **send with /n** checked. In `screen`, press **Ctrl+J** to send the required newline; Enter alone may send only a carriage return. The characters you type may not echo. In another serial terminal, use its LF/newline send setting. Send one command at a time and wait for its reply.

The Pico replies with a long line of diagnostic text in JSON format. You do not need to understand the whole line. Find these fields:

| Field | What to check |
| --- | --- |
| `ok` | `true` means the command succeeded. |
| `device_id` | The full 32-character Pico identity. Keep this for the setup command below. It is different from the USB serial. |
| `firmware`, `revision` | The installed firmware version and source revision. Include these in a problem report. |
| `network.ipv4` | The current home-network IP. Open `http://` followed by this address and `/` in your browser. An empty value or `0.0.0.0` means there is no usable home-network address. |
| `network.configured_hostname` | The hostname to try with `http://` when local name resolution works. |
| `network.consumer_web_ready` | `true` means the firmware reports its home-network web service ready. If it is `false` despite a usable IP, record that result for support. |
| `network.consumer_web_port` | `80` for the control page. |

The dotted field names above describe fields inside the `network` part of the reply. Web-service readiness is a firmware observation; it does not prove that your browser can reach the page. If it reports ready but the page still fails, return to the [browser checks](troubleshoot.md#pico-answers-ping-but-the-browser-cannot-open-its-page) and retain the exact browser error.

## Stop output from the Console

Open the identified Console as described above. Send `ABORT` with the same LF/newline ending used for `INFO`. This local USB command stops the current job even when another controller owns it, and suspends the Pico's automatic schedule for this boot. Wait for the reply, then send `STATUS` and check for `"ok":true`, `"output_active":false` and `"suspended":true`. `STATUS` remains available for read-only observation when no runtime profile is active, a consumer source is selected or an ownership claim is pending. Profile-dependent control commands remain restricted. A pending reset can still refuse Console commands; reconnect after the reset and obtain fresh status.

Saved schedule enablement is retained, so an enabled schedule can run again after a restart. To keep automatic transmission disabled across restarts, disable the schedule in the browser and save and apply that change. If the stop result is missing or output remains unknown, keep the RF path connected and follow [Status, stop and connection loss](operate.md#status-stop-and-connection-loss).

## Request setup Wi-Fi from the Console

`SOFTAP` means a software-created access point: the Pico's temporary setup Wi-Fi network. This command requests that network without changing the saved Wi-Fi credentials.

1. Copy the full **device_id** from the `INFO` reply. Type this command, replacing `YOUR_FULL_DEVICE_ID` with that value, without quotation marks or angle brackets:

   ```text
   ACCESS SOFTAP YOUR_FULL_DEVICE_ID
   ```

2. Click **Send** in the browser terminal, press **Ctrl+J** in `screen`, or use LF/newline in another serial terminal. A successful request returns `"ok":true` and `"join_grace_ms":120000`, giving you **two minutes to join** the setup network. Once your phone or computer connects, setup Wi-Fi stays available for as long as a device remains connected. After the last device disconnects, it stays available for another **ten minutes**. A successful request does not prove the network is already active; activation can be deferred while output is busy or uncertain.

   ```{figure} _static/images/usb-windows-softap.png
   :alt: Windows Chrome showing ACCESS SOFTAP with the Pico's full device ID and a successful reply containing join_grace_ms 120000.

   A successful setup Wi-Fi request in Windows Chrome. Use your own Pico's full device_id; the long reply can wrap across terminal lines.
   ```

3. Join the setup network as described below. If the reply says `wrong_device`, recheck the full `device_id`. If it says `busy`, an earlier join window may still be active; try joining it. If it says `access_unavailable`, retain the error and firmware identity for support. Do not replace a refusal with an erase or a guessed configuration command.

To close `screen`, press **Ctrl+A**, then **backslash (\\)**, then **y**. Close another serial terminal using its disconnect control. Closing the Console does not stop an accepted job or disable saved schedules.

## Join the setup network again

1. In your phone or computer's Wi-Fi list, select **WsprryPico-** followed by your Pico's six-character suffix. Keep the connection if it reports no Internet.
2. Setup Wi-Fi is **open**, even after you have saved your home-network credentials. No password is needed to join it. If your phone asks for a Wi-Fi join password, check that you selected the intended Pico.
3. In a regular browser, open **http://192.168.4.1/**. On a configured Pico, sign in to the page using the **Pico password**, which defaults to the home Wi-Fi password saved during setup. Joining the open setup network does not sign you in to the control page.
4. Use **Wi-Fi/Host** to review the saved network and [update its password if needed](maintain.md#change-wi-fi). Station details are optional for browser access. Return your computer or phone to the home network before retrying the Pico's home-network address.

The Console request does not reset the Pico password or bypass browser login. WsprryPi's [USB settings controls](connect.md#usb-access-without-wi-fi) can manage saved Wi-Fi credentials without that login, but changing Wi-Fi does not clear a separate Pico password. If the Pico password is forgotten, retain the diagnostics and review the [reset options and their consequences](maintain.md#recovery-and-reset).

## USB diagnostic logging

The Pico can export diagnostic events to WsprryPi through its dedicated Logging port. In the Pico browser controls, open **Wi-Fi/Host → Logging → USB logging**, read the saved settings, enable export, choose the maximum severity and save. Read back after an uncertain save. Logging works without Pico Wi-Fi or synchronized UTC; without origin UTC, the Pi displays the receipt time.

On WsprryPi, save the Pico in Fleet, then open **Logs**, select that Pico in **Source**, open **Log options** and enable **Collect this Pico's USB logs**. The source selector also offers **All sources** and **Local Pi**. Collection continues when the browser closes. Pause only pauses the view; export saves the records retained by that view.

Console remains available in another terminal or browser tool while collection runs. WTP transmission control and USB management also retain their separate ports. Firmware maintenance releases Logging and reconnects collection afterward; a whole-device restart or update disconnects all ports. Changed device identity requires explicit review.

For a manually started stream on Logging, send `SYSLOG STOP` to stop that stream. Console does not carry the stream. Logging settings belong to the Pico; the Pi's collection setting belongs to the Pi. Neither grants transmitter ownership or enables schedules. Older firmware without the dedicated Logging port requires an update before collection can start; the collector does not fall back to Console.

USB export and [UDP export](udp.md) use independent controls and queues. A Pi may forward already collected USB events without enabling direct Pico UDP. A USB disconnect cannot clear the UDP queue, and neither logging path grants transmitter ownership.
