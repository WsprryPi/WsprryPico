# Factory defaults

These values describe a new installation and untouched browser editors. Opening the control page does not enable schedules or start a transmission. Replace the station placeholders, review the RF setup, and explicitly save and apply settings before transmitting.

Settings-preserving firmware upgrades retain existing selections. This includes an unset WSPR dial, an empty schedule list, a previously saved drive strength or amplifier polarity, and custom hostnames. Missing fields in older saved records retain their original meanings; they are not replaced with new-installation defaults. A provisioning-only reset also preserves operating settings. See [Recovery and reset](../maintain.md#recovery-and-reset) before clearing settings.

## Station, WSPR and time

| Setting | Initial value |
| --- | --- |
| Callsign | `N0CALL`; replace before applying station settings |
| Grid locator | `ZZ99`; replace before applying station settings |
| Reported WSPR power | **0 dBm**; a message field, not a physical power setting |
| WSPR USB dial | **14,095,600 Hz**; enter `14095600` in the frequency field |
| Automatic WSPR schedules | **Disabled** |
| WSPR schedule interval / offset | **600 / 0 seconds**: every ten minutes, aligned to UTC :00, :10, :20, :30, :40 and :50 |
| WSPR schedule expiry | No end date |
| Time server | `pool.ntp.org` |
| NTP update timeout | **60 minutes** |
| Manual RF correction | **0.000 ppm** |
| Experimental frequency permissions | Unqualified-frequency and non-amateur-frequency permissions are both **off**; advanced configuration only |

Standalone WSPR places its RF center 1,500 Hz above the dial, so the default dial gives a **14,097,100 Hz** center. A scheduled WSPR transmission starts one second after its selected two-minute window begins. The ten-minute schedule remains inactive until explicitly enabled and applied. See [Frequency and schedules](../configure.md#frequency-and-schedules) and [Time and calibration](../configure.md#time-and-calibration).

## Radio pins and filtering

| Setting | Initial value |
| --- | --- |
| RF output | **GP2**, physical header pin **4**, using the direct GPIO engine |
| GPIO drive strength | **12 mA**; independent of reported WSPR power |
| Transmit indicator | **Onboard LED** |
| External indicator polarity | **Active-high** if an external LED is selected |
| External control button | **GP14**, physical pin **19**; active-low input |
| Amplifier-enable GPIO | **Disabled**, with **Active-low** polarity preselected |
| Amplifier lead / tail | **200 ms / 200 ms**; unused while the amplifier pin is disabled |
| LPF / band selection | **Fixed / manual filtering**, with no selector outputs or ranges configured |
| Filter release / settle delays | **20 ms / 20 ms** when configured selection is used |

Pin, drive, amplifier and selector changes require an explicit restart before they become active. Saving them does not measure RF power or verify external circuitry. See [Pins and drive](../configure.md#pins-and-drive) for controls and [Hardware connections](../start.md#hardware-connections) for wiring.

## Connections and diagnostic logging

| Setting | Initial value |
| --- | --- |
| Home Wi-Fi | No saved network or password |
| Setup Wi-Fi | Open network named `WsprryPico-` followed by six hardware-derived hexadecimal characters |
| Local hostname | `wpico-xxxx.local`, using the last four hexadecimal characters of the station Wi-Fi MAC address; for example, `wpico-60df.local` |
| Pico browser password | Follows the Wi-Fi password saved during setup until a separate Pico password is saved |
| USB diagnostic export | **Disabled**, with **Info and higher** as the saved maximum-severity selection |
| USB collection on WsprryPi | **Disabled**; enabled separately for the selected Pico |
| Direct Pico UDP diagnostic export | **Disabled**; no destination address, port **5514**, **Info and higher**, rate **4 events/second**, burst **8** |
| UDP event filter | Empty: includes all approved export-safe event classes when export is enabled |

Setup Wi-Fi is available for initial configuration when no home network is saved. Read the Pico's reported hostname rather than copying an example address. The setup Wi-Fi name, device identity and saved custom hostname are separate values. See [Connect to your Pico](../connect.md).

To collect USB diagnostics, enable **USB log export** on the Pico and **Collect this Pico's USB logs** on WsprryPi. Routine USB WTP/Management port open/close events and routine synchronized/holdover transitions require **All levels, including debug** on the Pico and a Pi view filter that includes Debug. USB export has an enable control and a severity selection; individual event-code filters belong to UDP export. See [USB diagnostic logging](../usb.md#usb-diagnostic-logging) and [UDP diagnostic logging](../udp.md).

## CW message editor

These are browser draft values, not an enabled or saved message schedule. An existing saved message schedule or an edited draft takes precedence.

| Setting | Initial value |
| --- | --- |
| Mode | **QRSS** |
| Message | `73 DE ` followed by the applied station callsign, or `73 DE N0CALL` before station setup |
| Direct RF frequency | Blank; enter the desired carrier, space or dot frequency |
| FSKCW / DFCW frequency shift | **5 Hz**; unused by QRSS |
| Dot length | **3 seconds** |
| Timing multipliers: dash / within character / between characters / between words | **3 / 1 / 3 / 7**; DFCW uses equal-length dots and dashes |
| Message copies per job | **1** |
| Gap between repeated copies | **3 seconds** |
| Delivery | **Repeat on a schedule** |
| Repeat interval | **10 minutes** |
| First start | Next ten-minute UTC boundary |
| End date | None |

The suggested message follows the applied callsign until the message is manually edited. `N0CALL` is refused before transmission. WSPR dial settings do not fill the CW frequency field. See [Send QRSS, FSKCW or DFCW](../operate.md#send-qrss-fskcw-or-dfcw) and [Repeat a message on a schedule](../operate.md#repeat-a-message-on-a-schedule) for saving and starting a job or schedule.
