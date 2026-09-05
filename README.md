# WsprryPico

WsprryPico is a first-class standalone WSPR/QRSS transmitter application in the WsprryPi family. It targets Raspberry Pi Pico family hardware, with Pico 2 W / RP2350 as the defined hardware target, and also serves as a hardware transmitter backend for WsprryPi.

Status: normative WTP/1 contract, host-tested portable core, and an RF-inhibited
Pico 2 W WTP USB endpoint. No physical RF engine is implemented; target USB,
timing and RF behavior remain unqualified.

- [Accepted architecture](docs/architecture.md)
- [WTP/1 protocol contract](docs/protocol/WTP.md)
- [Browser API direction](docs/browser-api.md)
- [RF feasibility investigation](docs/rf-feasibility.md)
- [Implementation plan](docs/implementation-plan.md)
- [Portable core development](docs/development/portable-core.md)
- [Pico 2 W firmware foundation](docs/development/firmware-foundation.md)
- [Strict WTP USB endpoint](docs/development/wtp-endpoint.md)

Firmware release names will follow `WsprryPico-x.y.z.uf2`. WTP versions are independent of firmware versions. WTP is documented here, with WsprryPico as its reference implementation; there is no separate protocol repository.

Unresolved design proposals are explicitly marked as drafts.

## Development and contribution

- [Project contract](CONTRACT.md)
- [Development baseline](docs/development/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Original contributions are licensed under [MIT](LICENSE.md). Firmware build
inputs are pinned in the firmware-foundation documentation.
