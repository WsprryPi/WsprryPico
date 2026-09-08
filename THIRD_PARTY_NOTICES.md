# Third-party notices

Original WsprryPico code and documentation are covered by [MIT](LICENSE.md).
Third-party material retains its own license and attribution requirements.

The optional Phase 10 host interoperability test compiles unmodified WTP-Client
sources from [WsprryPi](https://github.com/WsprryPi/WsprryPi) at
`2819f0b8ccb05f12d7f978a4cee2cac830997bbf`. The external component is MIT,
copyright 2026 Lee Bussy; its notice remains in `src/WTP-Client/LICENSE.md`
and source headers in that checkout. No client source is vendored here, no
production dependency is added and no client code enters the firmware. Preserve
the component's MIT notice if distributing the optional test executable.

The firmware build uses these external components without vendoring them:

- Raspberry Pi Pico SDK 2.3.0, commit
  `98a542c1a62fb549ffb5d66a3e5892b06276b670`, BSD-3-Clause. The SDK retains
  its license and component notices in its own checkout.
- TinyUSB 0.18.0, SDK submodule commit
  `86ad6e56c1700e85f1c5678607a762cfe3aa2f47`, MIT. The dual-CDC descriptor
  source is adapted from TinyUSB's `cdc_dual_ports` example and retains its
  license header.
- picotool 2.3.0, commit
  `6f6458d792b93685a11423b244a585eaa99eafcf`, BSD-3-Clause. Pico SDK fetches
  and builds this pinned host tool in the ignored build directory to
  produce RP2350 UF2 artifacts; it is not linked into firmware.

Before importing source, assets or dependencies, record the component, upstream
URL, exact version/revision, license, retained notice location, modifications
and distribution requirements here. This applies to WsprryPi code, the Pico SDK,
USB/network/Bluetooth libraries and any Si5351 implementation. Inspect the actual
dependency tree rather than assuming the SDK's license covers every component.

The portable Type 1 encoder packing and synchronization constants, and the
AA0NT/EM18/20 and /37 test vectors, are adapted from WsprryPi WSPR-Reference at
`3222b7eb7ad04cb8ddff6a012c4983164d7f206b`
(<https://github.com/WsprryPi/WsprryPi>), files
`src/WSPR-Reference/src/wspr/wspr_ref_encoder.cpp`, `wspr_constants.hpp` and
`test_vectors/wspr_golden_vectors.json`. MIT, copyright 2024 Lee Bussy; retained
notice: [WsprryPi license](src/encoding/WsprryPi-LICENSE.md). The adaptation uses
strict bounded Type 1 validation and a stateless C++20 implementation. Types 2/3
and upstream permissive normalization are not imported. Preserve this notice
and the retained MIT license when distributing the encoder.

Standalone Wi-Fi builds also link the pinned SDK's network dependencies:

- [lwIP](https://git.savannah.nongnu.org/cgit/lwip.git/), 2.2.1 at
  `77dcd25a72509eb83f72b033d219b1d40cd8eb95`, BSD-3-Clause. Retained upstream
  [COPYING](docs/licenses/lwip.txt). The project supplies `lwipopts.h`; upstream
  source is unchanged and remains in the external SDK checkout.
- [cyw43-driver](https://github.com/georgerobotics/cyw43-driver), v1.1.1 at
  `055d64274b014dd7b1c2fc94d26e8a18face7124`, including the SDK-selected
  `firmware/w43439A0_7_95_49_00_combined.h` Wi-Fi/CLM resource. Source and
  resources are unchanged, external SDK inputs. Retained upstream
  [LICENSE.RP](docs/licenses/cyw43-driver-RP.txt) covers use with Raspberry Pi
  semiconductor devices; the alternative upstream
  [LICENSE](docs/licenses/cyw43-driver.txt) is retained too. These are distinct
  from the project's MIT license. Preserve the applicable notices and
  disclaimers in documentation/materials accompanying firmware distribution.

No NTP implementation was copied from another project. The portable exchange
parser is original project code based on the published packet format.

Phase 11 links [Mbed TLS](https://github.com/Mbed-TLS/mbedtls), 3.6.6 at
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, from the pinned SDK submodule.
It is dual licensed Apache-2.0 OR GPL-2.0-or-later; this project selects
Apache-2.0. The unmodified upstream [LICENSE](docs/licenses/mbedtls.txt) is
retained. Upstream sources remain external and unchanged, including the PSA
RNG source explicitly added to the SDK target. Preserve applicable upstream
notices and the Apache license with distributed firmware/test binaries.
The HTTP adapter, browser assets and certificate scripts are original MIT
project contributions; no WsprryPi vendor browser assets are copied.

Phase 11.3 also links the exact pinned lwIP mDNS responder (`mdns.c`,
`mdns_domain.c`, `mdns_out.c`). Its retained [BSD notice](docs/licenses/lwip-mdns.txt)
and [integration record](docs/development/mdns-responder.md) describe the narrow
project-owned lifecycle wrapper. SDK source is unmodified; no DNS-SD service
registration or third-party application code is added.
