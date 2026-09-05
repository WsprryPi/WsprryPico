# Third-party notices

Original WsprryPico code and documentation are covered by [MIT](LICENSE.md).
Third-party material retains its own license and attribution requirements.

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
