# Prepare your Pico

Use a **Pico 2 W / RP2350**. The original Pico, Pico W and non-wireless Pico 2
are not supported targets. You need a USB data cable, a reliable USB supply and
a macOS or Linux computer for the USB installer. Windows and WSL USB installation
are unsupported.

For browser control, have the name and password of a compatible **2.4 GHz
Wi-Fi network** available. The consumer setup supports password-protected
personal networks; enterprise and WPA3-only provisioning are unavailable.
Use a trusted network on which your computer or phone can reach the Pico.

Before connecting RF output, choose filtering, attenuation, any amplifier and
a load suitable for the operating frequency. The GPIO output is unfiltered.
The reported WSPR power setting does not limit or measure that output.

The factory RF output is **GP2, physical header pin 4**. Connect the RF path's
ground to a Pico **GND**, such as physical pin 3. Confirm board orientation
against the official
[Pico 2 W pinout](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html#wireless-board-layout).
A saved custom RF pin takes precedence; read the active pin assignment before
connecting output. GP14, physical pin 19, is the default runtime button input.

Choose how to operate:

- **Standalone:** Save your station, frequency and WSPR schedule on the Pico,
  or send individual messages from its browser page. A network time server
  supplies UTC when connected.
- **WsprryPi member:** Follow
  [Add a WsprryPico in the WsprryPi manual](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html)
  to connect, identify and schedule the device from the Pi. USB supports
  configuration, controller time and jobs without Wi-Fi; standalone Wi-Fi
  commissioning is not a prerequisite for that route.

Install the [normal firmware](install.md) next. A fresh generic image has no
selected transmit frequency. A saved draft does not run; applying enabled
schedules authorizes future automatic transmissions when ready.
