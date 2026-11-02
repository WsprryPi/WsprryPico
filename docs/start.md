# Prepare your Pico

Use a **Pico 2 W / RP2350**. The original Pico, Pico W, and non-wireless Pico 2 are not supported. You need a USB data cable, a reliable USB supply, and a macOS or Linux computer for the USB installer. Windows and WSL USB installation are unsupported.

For browser control, have the name and password of a compatible **2.4 GHz Wi-Fi network** available. The consumer setup supports password-protected personal networks. Enterprise and WPA3-only provisioning are unavailable. Use a trusted network where your computer or phone can reach the Pico.

## Hardware connections

The Pico provides direct GPIO RF output and an onboard transmit LED. An external runtime control button and transmit LED are optional. The factory assignments are **GP2** for RF, **GP14** for the button, and the **onboard LED** for transmit indication. Many other pin combinations are supported; saved custom pin assignments take precedence.

The [Pico Validation Platform — Base Configuration](reference/pico-validation-platform.md#base-configuration) provides the wiring diagram, physical header pin numbers, button connection, external LED circuit and settings, and RF connector wiring. It uses GP15 for the optional external LED. Disconnect all power before changing wiring, and check the active assignments first; each GPIO can serve only one role.

**The RF output is unfiltered.** Choose filtering, attenuation and a load suitable for the operating frequency and measurement equipment. Read [RF output and band limits](reference/output.md) before connecting an antenna. The WSPR power setting does not measure or limit GPIO output power.

## Choose how to operate

- **Standalone:** Save your station, frequency, and WSPR schedule on the Pico, or send individual messages from its browser page. A network time server supplies UTC when connected.
- **WsprryPi member:** Follow [Add a WsprryPico in the WsprryPi manual](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html) to connect, identify, and schedule the device from the Pi. USB supports configuration, controller time, and jobs without Wi-Fi. You do not need to set up the Pico's Wi-Fi for that route.

Install the [firmware](install.md) next. New station settings default to a 14,095,600 Hz WSPR dial. Automatic schedules are disabled. Enter and apply the [station and schedule settings](configure.md) before enabling automatic transmissions.
