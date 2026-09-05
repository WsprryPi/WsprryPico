# WsprryPico

WsprryPico is a first-class standalone WSPR/QRSS transmitter application in the WsprryPi family. It targets Raspberry Pi Pico family hardware, with Pico 2 W / RP2350 as the defined hardware target, and also serves as a hardware transmitter backend for WsprryPi.

Status: architecture baseline, normative WTP/1 contract and remaining design drafts. No firmware or RF engine is implemented or qualified.

- [Accepted architecture](docs/architecture.md)
- [WTP/1 protocol contract](docs/protocol/WTP.md)
- [Browser API direction](docs/browser-api.md)
- [RF feasibility investigation](docs/rf-feasibility.md)
- [Implementation plan](docs/implementation-plan.md)

Firmware release names will follow `WsprryPico-x.y.z.uf2`. WTP versions are independent of firmware versions. WTP is documented here, with WsprryPico as its reference implementation; there is no separate protocol repository.

Unresolved design proposals are explicitly marked as drafts.

## Development and contribution

- [Project contract](CONTRACT.md)
- [Development baseline](docs/development/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Original contributions are licensed under [MIT](LICENSE.md). Firmware build
targets and SDK/toolchain versions will be established in the first implementation slice.
