# Connect to your Pico

## First Wi-Fi connection

1. Power the Pico. Without saved Wi-Fi it starts a temporary **open** setup network named **WsprryPico-** followed by six hexadecimal characters. It needs no Wi-Fi join password. Select the intended Pico's network and keep that connection if your phone or computer reports no Internet.
2. Your phone or computer may open the Pico's setup page automatically after joining its Wi-Fi. If no page opens, launch your browser and type **http://192.168.4.1/** directly into the address bar. If the automatic setup window reports that it cannot run encrypted setup, open the same address in your regular browser.
3. Enter your **Wi-Fi network name** and **Wi-Fi password** in the form shown below. Keep the suggested **Time server**, **pool.ntp.org**, unless you need a different one. Select **Connect to Wi-Fi**.
4. Keep the page open while the Pico connects and saves the settings. Look for the heading **Wi-Fi connected** and the message **Wi-Fi saved and connected.** Both are shown below. If the page loses contact, reconnect to the Pico's setup Wi-Fi and return to the same tab so it can check again. Wait for confirmation before submitting the settings again.
5. Reconnect your phone or computer to your home network. Open the Pico's control page at its home-network address as described below. You can enter station details later; they are not needed to connect or sign in.
6. The default **Pico password** is the **home Wi-Fi password entered during setup**. Enter it in **Pico password** and sign in. You can [set a separate Pico password](maintain.md#change-the-pico-password) under **Wi-Fi/Host → Pico password**. Check the hostname in the page heading and the full device ID under **About this Pico / Diagnostics** against your Pico, then continue to [Configure your station](configure.md) when you are ready to set up transmissions.

```{figure} _static/images/wifi-setup.jpg
:alt: Pico Wi-Fi setup form showing Wi-Fi network name, a masked Wi-Fi password, the suggested pool.ntp.org time server and the Connect to Wi-Fi button.
:target: _static/images/wifi-setup.jpg

Enter your home-network details, keep the suggested time server and select **Connect to Wi-Fi**. Example network details are shown; use your own. Select the image to enlarge it.
```

```{figure} _static/images/wifi-connected.jpg
:alt: Pico setup page headed Wi-Fi connected with the confirmation Wi-Fi saved and connected., the Station settings link and instructions for finding the Pico after setup.
:target: _static/images/wifi-connected.jpg

The **Wi-Fi connected** heading and **Wi-Fi saved and connected.** message confirm the save. These screenshots show the shipped setup page with example data in a local software preview.
```

Setup Wi-Fi stays available while your phone or computer is connected to it. After the last device disconnects, it closes after **ten minutes** without a connection. If nobody joins, the initial setup window also lasts ten minutes. Saving settings that restart the Pico can interrupt the connection; do not assume a lost reply means the save failed. If needed, use [USB recovery](usb.md) or request setup Wi-Fi again with the external button.

## Open the control page

Once the Pico has joined your home network, use its **home-network IP address** or its reported **`.local` hostname**. The setup address **192.168.4.1** works only while you are connected to the Pico's own setup Wi-Fi.

1. Connect your phone or computer to the same home network as the Pico. A wired computer on that network also works. Avoid a guest network that prevents devices from reaching each other.
2. Find the Pico in your router's connected-device list, or use the hostname reported by the setup page. A default name looks like `wsprrypico-0a60df.local`; your Pico's suffix will differ.
3. Type the complete address into the browser's address bar, starting with **http://**. For example, if your router lists the Pico at **192.168.1.123**, open **http://192.168.1.123/**. Replace that example IP with your Pico's actual address. You can also use **http://wsprrypico-0a60df.local/** with your Pico's actual hostname.
4. The control page should show a **Pico password** login field. Its default is the home Wi-Fi password saved during setup. Use your separate Pico password if you changed it. To change the Pico password without changing Wi-Fi, follow [Change the Pico password](maintain.md#change-the-pico-password).

The control page uses **HTTP on port 80**. If your browser automatically changes the address to **https://**, allow HTTP for this Pico address and retry. No extra port number, client certificate or special iPhone browser is needed. The page can open before the Pico has synchronized its clock; a time-server problem does not by itself prevent browser access.

If the Pico answers ping but the page does not open, follow [Pico answers ping but the browser cannot open its page](troubleshoot.md#pico-answers-ping-but-the-browser-cannot-open-its-page). Ping confirms a response at that address; it does not check the web service.

Use a current desktop or mobile browser with JavaScript enabled. The Pico serves its own page; the former hosted Bluefy URL is retired. Offline Bluefy reuse is unsupported.

**Station/Transmission** holds station identity, schedules, radio pins and job
controls. **Wi-Fi/Host** holds Wi-Fi, Pico password, time server, hostname and restart controls.
The shared status and recovery controls stay available when switching areas.
Use the page links to retain current browser drafts.

```{figure} _static/images/radio-login.jpg
:alt: Pico control page with its reported hostname, Station/Transmission and Wi-Fi/Host links, and the empty Pico password login field.
:target: _static/images/radio-login.jpg

Control-page login with an example hostname. The password field is
empty; status remains unknown until authenticated readback. Software preview.
Select the image to open it at full size.
```

The hostname identifies the running device; a saved rename takes effect only after restart. The full stable device ID distinguishes Picos sharing a name. An IP address can change after reconnecting to the network. If `.local` fails, use the current IP in your router. After signing in, check the full device ID in **About this Pico / Diagnostics** against your recorded identity.

## Request setup Wi-Fi with the external button

This route needs a fitted external push button. The factory runtime button connects **GP14, physical pin 19, to GND**. It is separate from the onboard BOOTSEL button. A saved custom or disabled assignment takes precedence. If no external button is fitted, use [USB recovery](usb.md).

| Gesture | Requested action |
| --- | --- |
| Release in under 0.4 seconds | Reset |
| Hold to 0.9 seconds, or release between 0.4 and 0.9 seconds | Transmission shutdown |
| Hold for nine seconds | Setup Wi-Fi after shutdown is confirmed |

After setup Wi-Fi appears, [join the setup network](usb.md#join-the-setup-network-again) and open **http://192.168.4.1/**. Setup Wi-Fi is open, including on a configured Pico; the configured control page still requires the Pico password. An unavailable saved network requests fallback setup after 60 seconds; activation may be deferred while a job runs. A connection timeout is not proof that RF has stopped.

## USB access without Wi-Fi

**For a standalone Pico:** follow [Recover browser access over USB](usb.md), starting with its computer requirements. It includes a Chrome browser terminal route for Windows, macOS and Linux, plus command-line instructions for macOS and native Linux. The walkthrough explains how to find the Console connection, read the Pico's current IP address and request setup Wi-Fi without an external button. WsprryPi is not required for those steps. Connecting the cable alone does not open a browser page or create a USB network connection.

**If you already run WsprryPi on a Raspberry Pi:** connect the Pico's USB data cable to that Raspberry Pi. In WsprryPi's browser interface, open **Setup → Fleet**, select the attached USB Pico and open **Pico standalone settings and Wi-Fi**. Choose **Load saved Pico settings** to read its configuration. A “member” means a transmitter listed in Fleet; its USB entry is the row for your attached Pico. Follow [the WsprryPi settings instructions](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/Transmitter/index.html#pico-standalone-settings-and-wi-fi) to change the saved network or password. This USB route needs no Pico browser login or Pico Wi-Fi connection and does not take over an existing job.
