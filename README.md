# WsprryPico

WsprryPico turns a **Raspberry Pi Pico 2 W**, with its RP2350 processor, into a radio beacon. It can run independently, using settings saved on the Pico and its browser controls, or accept transmissions from **WsprryPi**, a controller running on a Raspberry Pi.

It supports **WSPR**, **QRSS**, **FSKCW**, and **DFCW**, plus finite test tones submitted by controllers or prepared job files. Complete transmission jobs run locally on the Pico, so their timing does not depend on continuous USB or Wi-Fi delivery.

The normal RF engine uses a direct GPIO output. Si5351 settings can be saved through Pico and WsprryPi controls; Si5351 output requires an explicit engineering build while hardware qualification is incomplete. GPS/PPS input and automatic RF calibration are unavailable.

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

For build instructions and contributor information, see:

- [Development guide](engineering/development/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

The [MIT License](LICENSE.md) applies to original contributions.
