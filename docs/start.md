# Prepare your Pico

Use a **Pico 2 W / RP2350**. The original Pico, Pico W and non-wireless Pico 2 are not supported targets. You need a USB data cable, a reliable USB supply and a macOS or Linux computer for the USB installer. Windows and WSL USB installation are unsupported.

For browser control, have the name and password of a compatible **2.4 GHz Wi-Fi network** available. The consumer setup supports password-protected personal networks; enterprise and WPA3-only provisioning are unavailable. Use a trusted network on which your computer or phone can reach the Pico.

## Hardware connections

The transmit LED is built in. An external LED and control button are optional. Disconnect USB and any other power before adding or changing wiring. Confirm board orientation against the official [Pico 2 W pinout](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html#wireless-board-layout). **GPIO** means general-purpose input/output. GPIO names such as **GP14** differ from physical header pin numbers; settings use the **GPIO number**.

| Connection | Factory default | Available selections |
| --- | --- | --- |
| RF output | **GP2**, physical header pin **4** | One GPIO from **GP0–GP22** or **GP26–GP28** |
| Transmit LED | **Onboard LED**, already fitted; no header pin needed | Onboard LED, one external GPIO from **GP0–GP22** or **GP26–GP28**, or Disabled |
| External control button | **GP14**, physical header pin **19**, connected to GND when pressed | One GPIO from **GP0–GP22** or **GP26–GP28**, or Disabled |

Each external GPIO can serve only one role. With factory assignments, **GP2** is occupied by RF and **GP14** by the button input; the other GPIOs in the listed ranges are available for an external LED or another supported role. Saved custom assignments can occupy different pins. The settings menu marks pins already assigned to another role as unavailable. **GP23–GP25 and GP29** are reserved for onboard hardware.

### RF output

Before connecting RF output, choose filtering, attenuation, any amplifier and a load suitable for the operating frequency. The GPIO output is unfiltered. The reported WSPR power setting does not limit or measure that output.

Connect the RF path to **GP2, physical header pin 4**, and its ground to a Pico **GND**, such as physical pin **3**. A saved custom RF pin takes precedence; read the active pin assignment before connecting output.

### Transmit LED

The **onboard LED** is the default transmit indicator. It lights steadily while RF output is active. At other times, it can blink for setup Wi-Fi or device identification. It needs no additional wiring.

For an optional external LED, choose **External GPIO** under **TX LED** in **Station Control → Radio pins**. Select an unused **External LED Pin** and the matching **LED Polarity**. External polarity defaults to **Active-high**. See [LED and button settings](configure.md#led-and-button-settings) for saving and applying the selection.

For example, with the factory RF and button assignments, **GP15, physical pin 20**, is available. Select **GP15** and **Active-high**. With power disconnected, connect **GP15 → 1 kΩ resistor → LED anode (+)**, then connect the **LED cathode (−) → GND**, such as physical pin **18**. Keep the resistor in series with the LED.

An external LED indicates transmission only; setup Wi-Fi and identification blinks continue on the onboard LED. The indicator reports the Pico's RF-output state rather than measuring RF power.

### Optional external control button

The **runtime button input** is for an optional **normally open momentary push button** that you fit externally. Connect it between **GP14, physical pin 19**, and **GND**, such as physical pin **18**. Pressing the button joins GP14 to ground. The firmware supplies the pull-up internally, so this simple switch needs no external pull-up resistor.

A **brief click** resets the Pico, **holding briefly** requests transmission shutdown, and **holding for over 10 seconds** requests setup Wi-Fi after shutdown is confirmed. See [button gestures and exact timings](connect.md#request-setup-wi-fi-with-the-external-button). The onboard **BOOTSEL** button is used when loading firmware; use the fitted external button for these runtime controls.

The **Button** setting in **Radio pins** selects the button's GPIO. Its default is **GP14**; choose another unused GPIO in the listed ranges or **Disabled**. A saved selection takes precedence over the factory wiring. Browser and [USB controls](usb.md) are available without an external button.

## Choose how to operate

- **Standalone:** Save your station, frequency and WSPR schedule on the Pico, or send individual messages from its browser page. A network time server supplies UTC when connected.
- **WsprryPi member:** Follow [Add a WsprryPico in the WsprryPi manual](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html) to connect, identify and schedule the device from the Pi. USB supports configuration, controller time and jobs without Wi-Fi; you do not need to set up the Pico's Wi-Fi for that route.

Install the [firmware](install.md) next. A new installation has no selected transmit frequency. Enter and apply the [station and schedule settings](configure.md) before enabling automatic transmissions.
