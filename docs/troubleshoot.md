# Troubleshoot

## Pico answers ping but the browser cannot open its page

After Wi-Fi setup, the Pico serves its control page on its home-network IP address over **HTTP, port 80**. Station details are not needed to open the page or sign in. A reply to ping does not establish that the web service is working. Try these checks in order:

1. Find the Pico's **current IP address** in your router's connected-device list. Reconnect your phone or computer to that same home network. **192.168.4.1** is the Pico's separate setup-network address; use it only when connected to the Pico's own Wi-Fi.
2. Enter the full URL in the browser's address bar. For a Pico at `192.168.1.123`, use **http://192.168.1.123/**. Substitute your actual IP. Check that the browser keeps **http://** rather than switching to **https://**. No extra port number is needed.
3. Try another current browser or another device on the same network. Check whether a VPN, proxy, guest-network rule or router client-isolation setting prevents local web access. Allow HTTP for the Pico's address if the browser enforces HTTPS.
4. If the **Pico password** field appears, the page has loaded. The default Pico password is the home Wi-Fi password saved during setup. Use your custom Pico password if you changed it in **Wi-Fi/Host → Pico password**. For a login failure, use the table below. Clock synchronization and Internet access are not required to load this page.
5. If no page loads, use [USB recovery](usb.md) to read the actual firmware version, IP address and web-service status. You can also reopen setup Wi-Fi with a [fitted external button](connect.md#request-setup-wi-fi-with-the-external-button). Neither route requires reinstalling firmware or erasing saved settings.

If access still fails, record the **exact URL**, browser and operating system, firmware version, and the full error wording: for example, connection refused, timeout, HTTPS error or a blank page. Include whether another browser or device worked and whether setup Wi-Fi still opens. Add the relevant [USB diagnostic fields](usb.md#read-the-address-and-web-service-status) if available. Report these details through the [project issue tracker](https://github.com/WsprryPi/WsprryPico/issues); remove credentials and other private information before posting.

## Other symptoms

| Symptom | Check and recovery |
| --- | --- |
| No USB drive appears | A drive appears in **BOOTSEL** mode for programming, not during normal WsprryPico operation. For browser access or Console commands, reconnect without holding BOOTSEL and use a USB data cable. See [USB Console discovery](usb.md#find-and-open-the-console-on-macos-or-linux). |
| New Pico's setup Wi-Fi is missing | Confirm it is a Pico 2 W with [WsprryPico firmware installed](install.md). Reconnect power without holding BOOTSEL. A Pico with saved Wi-Fi normally joins that network instead; use its current IP or request setup with the [external button](connect.md#request-setup-wi-fi-with-the-external-button) or [USB Console](usb.md#request-setup-wi-fi-from-the-console). |
| Setup Wi-Fi disappears | It stays up while a device is connected and closes after ten minutes with no connected devices. An unanswered USB Console request has a two-minute join window. A settings change that restarts the Pico can also disconnect it. Request setup again with the configured button or [USB Console](usb.md#request-setup-wi-fi-from-the-console), then read saved state before repeating a save. |
| `.local` does not open | Use the current router-assigned IP, verify device ID, and check for duplicate names or client isolation. |
| Login fails | Use the Pico password: the saved Wi-Fi password by default, or your separate Pico password if changed. Reconnect after a password/profile change. Check the device identity before entering it. |
| All logins occupied | Use **Recover an occupied login**, inspect entries and explicitly retire the selected login with the current Pico password. Each browser login uses a slot; retiring a login does not stop an accepted job or release transmitter ownership. |
| Save outcome uncertain | Reconnect, **Read saved settings and keep draft**, compare and explicitly review. For setup, use **Check saved result**. The change may already be stored; do not automatically repeat Save or Apply. |
| Controls are disabled | Read the message beside the control. Sign in if needed, refresh status and check for another job owner, an uncertain save awaiting review, or a restart requirement. Saved fields and active settings can differ; see [what was saved](configure.md#understand-what-was-saved). |
| Schedule does not transmit | Confirm the schedule is enabled **and applied**, a WSPR dial frequency is saved, station details are complete and the clock is usable. Check expiry, another controller's ownership, active pins and any STOP, output-inhibit or restart message. Follow [WSPR schedules](operate.md#wspr-schedules); missed windows are not replayed. |
| STOP/shutdown remains after saving | Review the saved schedule, leave it disabled unless output is intended, confirm idle/inactive, then explicitly restart. Configuration saves do not clear STOP. |
| Start refused for clock | Check the time server and network, or the controller-time connection. Allow fresh synchronization and read [Clock status](reference/time.md#read-the-clock-status). Manual frequency correction does not fix transmission start time. |
| Restart required after reverting a pin/drive edit | The restart latch persists for that boot. Review saved wiring/drive and perform an explicit restart while idle. |
| Another owner or busy | Stop and release through the controller named by **Owner**; signing in through another tab does not take over. If that controller is unavailable, use the configured external button or [USB stop command](usb.md#stop-output-from-the-console), then refresh status. |
| Frequency Save is disabled or says no station is applied | Complete station identity, save valid station fields and explicitly **Apply saved station**. A complete draft alone is insufficient. Follow any reconnect and **Check saved result** instructions, then confirm the frequency readback. Your dial entry stays in the current tab; it is not stored until **Save frequency** succeeds. See [Frequency and schedules](configure.md#frequency-and-schedules). |
| Frequency rejected | Check [output and band limits](reference/output.md), including both frequencies used by FSKCW or DFCW. Enter Hz, not MHz, in browser frequency fields. Both Pi and Pico permissions apply to Pi-submitted jobs. Experimental permission cannot expand the generator's range. |
| Message refused despite fitting 32 characters | Check the supported characters and duration preview. The complete transmission may exceed 512 timed events or 60 minutes, including repeats and gaps. Reduce repeats, gaps, dot duration or message length; see [message controls](operate.md#send-qrss-fskcw-or-dfcw). |
| Type 3 shows `<...>` | The receiving software may lack the callsign associated with the short identifier in this WSPR message. Receive the preceding Type 2; locator and power can decode without a resolved name. See [Automatic WSPR plan](operate.md#automatic-wspr-plan). |
| USB installer refuses | Check selected serial/port, Pico 2 W confirmation, picotool USB support, idle/unowned state, exact image channel and manifest. Follow its specific refusal. |
| Installer asks for BOOTSEL | Preparation is incomplete. Reconnect that same board and port, then run the printed continuation command. |
| Network drops while output may be running | Treat output as unknown. Use the owner or configured shutdown button and confirm inactive before touching the RF path. |

For reset consequences and useful diagnostic fields, see [Maintain and recover](maintain.md). For an installation problem, retain the exact transaction and its private backup until it is resolved.
