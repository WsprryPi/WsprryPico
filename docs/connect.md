# Connect to your Pico

## First Wi-Fi connection

1. Power the Pico. Without saved Wi-Fi it starts a temporary **open** setup network named **WsprryPico-** followed by six hexadecimal characters. It needs no Wi-Fi join password. Select the intended Pico's network and keep that connection if your phone or computer reports no Internet.
2. Your phone or computer may open the Pico's setup page automatically after joining its Wi-Fi. If no page opens, launch your browser and type **http://192.168.4.1/** directly into the address bar. If the automatic setup window reports that it cannot run encrypted setup, open the same address in your regular browser.
3. Enter your **Wi-Fi network name** and **Wi-Fi password** in the form shown below. Keep the suggested **Time server**, **pool.ntp.org**, unless you need a different one. Select **Connect to Wi-Fi**.

   ```{image} _static/images/wifi-setup.jpg
   :alt: Pico Wi-Fi setup form showing an example network name, a masked Wi-Fi password, the suggested pool.ntp.org time server and the Connect to Wi-Fi button. Enter your own network details.
   ```

4. Keep the page open while the Pico connects and saves the settings. Look for the heading **Wi-Fi connected** and the message **Wi-Fi saved and connected.** Both are shown below. If the page loses contact, reconnect to the Pico's setup Wi-Fi and return to the same tab so it can check again. Wait for confirmation before submitting the settings again.

   ```{image} _static/images/wifi-connected.jpg
   :alt: Pico setup page headed Wi-Fi connected, confirming Wi-Fi saved and connected, with a Station settings link and instructions for finding the Pico after setup.
   ```

5. Reconnect your phone or computer to your home network. Open the Pico's control page at its home-network address as described below. You can enter station details later; they are not needed to connect or sign in.
6. The default **Pico password** is the **home Wi-Fi password entered during setup**. Select the lock beside the hostname, enter it in **Pico password**, then choose **Unlock controls**. You can [set a separate Pico password](maintain.md#change-the-pico-password) under **Wi-Fi/Host → Pico password**. Check the hostname in the page heading and the full device ID under **About this Pico / Diagnostics** against your Pico, then continue to [Configure your station](configure.md) when you are ready to set up transmissions.

Setup Wi-Fi stays available while your phone or computer is connected to it. After the last device disconnects, it closes after **ten minutes** without a connection. If nobody joins, the initial setup window also lasts ten minutes. Saving settings that restart the Pico can interrupt the connection; do not assume a lost reply means the save failed. If needed, use [USB recovery](usb.md) or request setup Wi-Fi again with the external button.

## Open the control page

Once the Pico has joined your home network, use its **home-network IP address** or its reported **`.local` hostname**. An IP address is a numeric network address such as `192.168.1.123`; a hostname is a name such as `wsprrypico-0a60df.local`. The setup address **192.168.4.1** works only while you are connected to the Pico's own setup Wi-Fi.

1. Connect your phone or computer to the same home network as the Pico. A wired computer on that network also works. Avoid a guest network that prevents devices from reaching each other.
2. Find the Pico in your router's connected-device list, or use the hostname reported by the setup page. A default name looks like `wsprrypico-0a60df.local`; your Pico's suffix will differ.
3. Type the complete address into the browser's address bar, starting with **http://**. For example, if your router lists the Pico at **192.168.1.123**, open **http://192.168.1.123/**. Replace that example IP with your Pico's actual address. You can also use **http://wsprrypico-0a60df.local/** with your Pico's actual hostname.
4. The Station Control view shows **Transmitter status** and loads saved settings without opening a login prompt. Select the lock immediately before the hostname to open **Pico password**, then choose **Unlock controls**. Its default is the home Wi-Fi password saved during setup. Use your separate Pico password if you changed it. To change the Pico password without changing Wi-Fi, follow [Change the Pico password](maintain.md#change-the-pico-password).

   ```{image} _static/images/station-control.png
   :alt: Station Control with header view navigation, the hostname lock and public read-only transmitter observations before unlocking.
   ```

The control page uses **HTTP on port 80**. If your browser automatically changes the address to **https://**, allow HTTP for this Pico address and retry. The page can open before the Pico has synchronized its clock; a time-server problem does not by itself prevent browser access.

If the Pico answers ping but the page does not open, follow [Pico answers ping but the browser cannot open its page](troubleshoot.md#pico-answers-ping-but-the-browser-cannot-open-its-page). Ping confirms a response at that address; it does not check the web service.

Use a current desktop or mobile browser with JavaScript enabled. The Pico serves its own page.

Use the header links **Station Control** and **Wi-Fi/Host** to switch views; the active view is underlined. Selecting either opens the page at the top and keeps the same browser session and drafts. Station Control starts with **Transmitter status**, followed by **WSPR Configuration** (including station identity), **Time and calibration**, **Radio pins** and **CW Modes**. **About this Pico / Diagnostics** is at the bottom of Station Control. **Review saved settings** appears when a save needs reconciliation; its link opens the recovery comparison. Pending Wi-Fi or station setup results appear beside the corresponding form. Wi-Fi/Host contains network, Pico password, hostname and **Logging** settings. Open sections by selecting their headings. **Top** closes the settings disclosures and returns to the hostname while preserving entries and the selected job file. Direct section bookmarks and pending-save continuations reveal their target.

Status, accepted job details, schedules, frequencies and saved settings load without signing in. Locked settings stay dimmed and cannot be edited. Saved passwords, keys and certificates are not displayed. Use the hostname lock to authorize saves, job controls or **Reset Pico**; reading settings does not occupy or renew a login.

The unlocked icon locks this browser through logout. It preserves drafts, accepted transmissions and schedules; other logins keep their own access. If logout cannot be confirmed, the page reports local locking and any occupied-login uncertainty. Closing or cancelling the password dialog clears its password fields. The icon describes application access, not transport security or transmitter ownership.

The hostname identifies the running device; a saved rename takes effect only after restart. The **full stable device ID** is the Pico's permanent 32-character hexadecimal identifier. It distinguishes Picos sharing a name and differs from the USB serial used by the installer. An IP address can change after reconnecting to the network. If `.local` fails, use the current IP in your router. After signing in, check the full device ID in **About this Pico / Diagnostics** and record it for later identification.

## Request setup Wi-Fi with the external button

This route needs a fitted external push button. The factory runtime button connects **GP14, physical pin 19, to GND**. It is separate from the onboard BOOTSEL button. A saved custom or disabled assignment takes precedence. If no external button is fitted, use [USB recovery](usb.md).

| Gesture | Requested action |
| --- | --- |
| Brief click (release in under 0.4 seconds) | Reset |
| Hold briefly (hold to 0.9 seconds, or release between 0.4 and 0.9 seconds) | Transmission shutdown |
| Hold for over 10 seconds (setup request begins at 9 seconds) | Setup Wi-Fi after shutdown is confirmed |

After setup Wi-Fi appears, [join the setup network](usb.md#join-the-setup-network-again) and open **http://192.168.4.1/**. Setup Wi-Fi is open, including on a configured Pico; the configured control page still requires the Pico password. An unavailable saved network requests fallback setup after 60 seconds; activation may be deferred while a job runs. A connection timeout is not proof that RF has stopped.

## USB access without Wi-Fi

**For a standalone Pico:** follow [Recover browser access over USB](usb.md), starting with its computer requirements. It includes a Chrome browser terminal route for Windows, macOS and Linux, plus command-line instructions for macOS and native Linux. The walkthrough explains how to find the Console connection, read the Pico's current IP address and request setup Wi-Fi without an external button. WsprryPi is not required for those steps. Connecting the cable alone does not open a browser page or create a USB network connection.

**If you already run WsprryPi on a Raspberry Pi:** connect the Pico's USB data cable to that Raspberry Pi. In WsprryPi's browser interface, open **Setup → Fleet**, select the attached USB Pico and open **Pico standalone settings and Wi-Fi**. Choose **Load saved Pico settings** to read its configuration. A “member” means a transmitter listed in Fleet; its USB entry is the row for your attached Pico. Follow [the WsprryPi settings instructions](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#pico-standalone-settings-and-wi-fi) to change the saved network or password. This USB route needs no Pico browser login or Pico Wi-Fi connection and does not take over an existing job.
