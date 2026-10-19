# WsprryPico

WsprryPico transmits WSPR, QRSS, FSKCW and DFCW on a **Raspberry Pi Pico 2 W /
RP2350**. It runs standalone schedules and finite jobs, or serves as a WsprryPi
transmitter backend. Complete jobs execute locally; symbol timing does not
depend on continuous USB or network delivery.

The [published operator manual](https://wsprrypico.readthedocs.io/en/devel/)
covers preparation, installation, connection,
configuration, operation and recovery. Start with [Prepare your Pico](docs/start.md).
The [manual source](docs/index.md) is maintained in this repository.
A blank consumer starts temporary setup Wi-Fi; configured devices use their
saved network and the device-served browser interface. USB provides local
configuration, controller time and job control without Wi-Fi. Supported upgrades
preserve saved settings.

Normal firmware uses direct GPIO PIO/DMA output at 138 MHz. The output is
unfiltered and needs suitable filtering, attenuation, load and any amplifier.
Reported WSPR dBm is message content, not measured RF power. Generic images
select no transmit frequency. Save and review a frequency before deliberately
enabling schedules. Network UTC discipline and manual RF PPM correction are
separate. Read the [output limits](docs/reference/output.md) and
[access/security boundaries](docs/reference/security.md) before operating.

## Development and contribution

Engineering material lives in `engineering/`, outside the operator site:

- [Project contract](CONTRACT.md)
- [Architecture](engineering/architecture.md)
- [Development guide](engineering/development/README.md)
- [Selected work](engineering/development/consolidated-backlog.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Other Pico boards are unsupported. Original contributions use the
[MIT License](LICENSE.md).
