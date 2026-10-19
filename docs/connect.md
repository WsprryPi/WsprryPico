# Connect to your Pico

## First Wi-Fi connection

1. Power the Pico with normal firmware. Without saved Wi-Fi it starts a
   temporary **open** setup network named **WsprryPico-** followed by six
   hexadecimal characters. It needs no Wi-Fi join password. Select the intended
   Pico's network and keep that connection if your phone or computer reports
   no Internet. This setup-network join is separate from signing in to the
   configured control page with the saved infrastructure Wi-Fi password.
2. Open **http://192.168.4.1/** explicitly. Do not wait for a captive portal or
   use a search engine. Enter the Wi-Fi SSID, password and time server on the
   setup page. Follow its trial and save steps.
3. Check the saved result. Return to your normal Wi-Fi, then open the Pico's
   reported `.local` hostname or current IP address using **http://**.
4. Sign in with the **Wi-Fi password saved on the Pico**. Check the heading
   and **About this Pico / Diagnostics** before making changes.

The setup network closes **ten minutes after activation**. Keeping a page
open or holding a button does not extend it. If it closes before a confirmed
save, reconnect through USB or deliberately request another setup window.
Do not assume a lost reply means the save failed.

## Open the control page

Use a current desktop or mobile browser with JavaScript enabled. Consumer
control needs no client certificate or special iPhone browser. The Pico serves
its own page; the former hosted Bluefy URL is retired. Offline Bluefy reuse is
unsupported.

**Station/Transmission** holds station identity, schedules, radio pins and job
controls. **Wi-Fi/Host** holds Wi-Fi, time server, hostname and restart controls.
The shared status and recovery controls stay available when switching areas.
Use the page links to retain current browser drafts.

```{figure} _static/images/radio-login.jpg
:alt: Pico control page with its reported hostname, Station/Transmission and Wi-Fi/Host links, and the empty Saved Wi-Fi password login field.
:width: 960px
:target: _static/images/radio-login.jpg

Current consumer login page with a synthetic hostname. The password field is
empty; status remains unknown until authenticated readback. Software preview.
Select the image to open it at full size.
```

The hostname identifies the running device; a saved rename takes effect only
after restart. The full stable device ID distinguishes Picos sharing a name.
An IP address can change after reconnecting to the network. If `.local` fails,
look up the current IP in your router and compare the full device ID.

## Request setup Wi-Fi with the external button

The factory runtime button connects **GP14, physical pin 19, to GND**. It is
separate from the onboard BOOTSEL button. A saved custom or disabled assignment
takes precedence.

| Gesture | Requested action |
| --- | --- |
| Release in under 0.4 seconds | Reset |
| Hold to 0.9 seconds, or release between 0.4 and 0.9 seconds | Transmission shutdown |
| Hold for nine seconds | Setup Wi-Fi after shutdown is confirmed |

After setup Wi-Fi appears, join it and open **http://192.168.4.1/**. An unavailable
saved network requests fallback setup after 60 seconds; activation may be
deferred while a job runs. A connection timeout is not proof that RF has stopped.

## USB access without Wi-Fi

USB supports WsprryPi configuration, time and job control without a network.
Use WsprryPi's verified USB member entry to read or change the Pico. Console,
WTP and management are different USB interfaces; selecting a random serial
port by suffix is unreliable. Firmware discovery identifies their roles.

If a password or network is unavailable, use that local USB route. It does not
require a browser login and does not grant ownership of an existing job.
