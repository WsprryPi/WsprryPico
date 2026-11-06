# WsprryPico

WsprryPico turns a **Raspberry Pi Pico 2 W**, with its RP2350 processor, into a radio beacon. It can run independently, using settings saved on the Pico and its browser controls, or accept transmissions from **WsprryPi**, a controller running on a Raspberry Pi.

It supports **WSPR**, **QRSS**, **FSKCW**, and **DFCW**, plus finite test tones submitted by controllers or prepared job files. Complete transmission jobs run locally on the Pico, so their timing does not depend on continuous USB or Wi-Fi delivery.

One normal firmware image supports direct GPIO output and a qualified QRP Labs Rev. 6 Si5351 setup with a 25 MHz TCXO. Select and configure the RF engine through the Pico or WsprryPi controls. Loopback can measure the clock ratio or, with explicit reference trust and uncertainty, help maintain phone-set time. Other Si5351 configurations require an engineering build. An optional GPS receiver supplies offline UTC and location through separate serial/PPS inputs. Qualified PPS measurements can correct the Pico oscillator or, with CLK2 loopback, the independent Si5351 reference. Configure GPS and automatic correction under Radio pins; receiver association and physical accuracy require independent validation.

## Getting started

The [operator manual on Read the Docs](https://wsprrypico.readthedocs.io/en/devel/) covers hardware, installation, configuration, and operation.

You need a **Pico 2 W**, a USB **data** cable, a reliable USB power supply, and a suitable RF path. Other Pico models are not supported. The USB firmware installer requires **macOS or native Linux**. Standalone browser control uses a compatible personal **2.4 GHz Wi-Fi network** or the Pico’s protected field Wi-Fi; an authenticated AP browser can supply time without Internet. WsprryPi can configure and control the Pico over USB without Pico Wi-Fi.

**The RF output is unfiltered.** Read the [output and band limits](https://wsprrypico.readthedocs.io/en/devel/reference/output.html) before connecting an antenna, and use appropriate filtering, attenuation, and a suitable load.

- [Prepare the hardware](https://wsprrypico.readthedocs.io/en/devel/start.html).
- [Install or update firmware](https://wsprrypico.readthedocs.io/en/devel/install.html).
- [Connect to the Pico](https://wsprrypico.readthedocs.io/en/devel/connect.html), [configure the station](https://wsprrypico.readthedocs.io/en/devel/configure.html), and [make a first transmission](https://wsprrypico.readthedocs.io/en/devel/operate.html#your-first-wspr-transmission).
- [Use with WsprryPi](https://wsprrypico.readthedocs.io/en/devel/wsprrypi.html), including switching between Pi-controlled and standalone schedules.
- [Get support or report a bug](https://wsprrypico.readthedocs.io/en/devel/support.html).
- [Troubleshoot a problem](https://wsprrypico.readthedocs.io/en/devel/troubleshoot.html) or [maintain and recover the Pico](https://wsprrypico.readthedocs.io/en/devel/maintain.html).

## Development and contribution

`devel` is the default branch for active development and prereleases. `main` is
absent during prerelease development and can be recreated when stable `1.0.0`
is ready. Release tags identify exact released versions.

For build instructions and contributor information, see:

- [Development guide](engineering/development/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

The [MIT License](LICENSE.md) applies to original contributions.
