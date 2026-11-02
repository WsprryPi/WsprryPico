# Experimental Si5351 bench diagnostics

These opt-in Pico 2 W tools run outside the production application. They use a candidate Si5351A at I²C address `0x60`, GP4 SDA, GP5 SCL, and a nominal 25 MHz reference. They implement no production engine, WTP transport, browser control, scheduling, or persistent settings. The selected integration requirements remain in the [consolidated backlog](../../engineering/development/consolidated-backlog.md#possible-future-work).

| Tool | Command | Scope |
| --- | --- | --- |
| [Connection probe](wip-si5351-i2c/README.md) | `PROBE` | Address acknowledgements and bounded register reads. |
| [Fixed tone](wip-si5351-tone/README.md) | `TONE` | One nominal 12.5 MHz CLK0 tone, at most five seconds per boot. |
| [Band sweep](wip-si5351-sweep/README.md) | `TONE N` | One finite CLK0 tone per selected plan per boot; no modulation. |
| [Feedback diagnostic](wip-si5351-clk2-feedback/README.md) | `TEST` | Bounded CLK2 off/on/off edge counts through input-only GP7. |

The three output-producing tools require SDK 2.3.1, Arm GNU 15.3.1, C11/C++20, and `PICO_NO_FLASH=1`. Their CMake targets reject flash builds. Source pins and retained dependencies are defined in the [development guide](../../engineering/development/README.md#build-inputs-and-layout). They are not included by the root application build or its ordinary CI target.

For a cross-build, supply retained SDK and picotool checkouts explicitly. The following example compiles only; it does not load a board. Select `tone`, `sweep`, or `clk2-feedback` and a distinct build directory for each.

```sh
diagnostic=tone
cmake -S "tests/hardware/wip-si5351-$diagnostic" \
  -B "/absolute/private/build/si5351-$diagnostic" -G Ninja \
  -DPICO_SDK_PATH=/absolute/path/to/pinned-pico-sdk \
  -DPICOTOOL_FETCH_FROM_GIT_PATH=/absolute/path/to/retained-picotool-parent \
  -Dpicotool_DIR=/absolute/path/to/retained-picotool-parent/picotool \
  -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DPICO_NO_FLASH=1
cmake --build "/absolute/private/build/si5351-$diagnostic" --parallel 2
```

The picotool parent contains `picotool-src` at the pinned revision and an existing `picotool/picotoolConfig.cmake` for its retained host executable. Reuse retained sources and tools rather than fetching dependencies as part of a bench run. Reproduce the sweep plans with its documented generator and clang-format; compare both generated files before using a rebuilt image.

## Wiring reference and provenance

The manual's [Pico Validation Platform](../../docs/reference/pico-validation-platform.md) records the base and optional module wiring, module revisions, supply connections and parts sources.

The [annotated wiring image](../../docs/_static/images/wiring/qrp-labs-si5351-pico2w-wiring.png) adapts user-supplied QRP Labs Rev. 5 reference artwork. The fitted platform board is Rev. 6 with a 25 MHz TCXO; the Rev. 5 documentation remains applicable to its connections and supply arrangement. The underlying board artwork and product names belong to QRP Labs; this reference does not relicense that artwork as original MIT project code. Use the manufacturer's [module information and revision-specific manuals](https://qrp-labs.com/synth.html) to identify the actual board. These wiring illustrations do not establish production firmware support.

The image records the reported bench connections: module pin 10 to Pico VBUS (physical pin 40), module pin 1 to ground (physical pin 38), module pin 13 SCL to GP5 (physical pin 7), module pin 14 SDA to GP4 (physical pin 6), module pin 17 CLK0 as RF output, and module pin 19 CLK2 to GP7 (physical pin 10). Module pin 11 is unconnected in this setup; there is no Pico 3V3 supply wire to the Si5351. Check the actual module revision, supply arrangement, voltage levels, reference, pin numbering, and exclusive pin ownership before connecting or loading anything. The drawing records wiring, not independent electrical validation.

The [Si5351-only flipped Pico wiring reference](../../docs/_static/images/wiring/pico2w-si5351-flipped-wiring.svg) includes the synthesizer supply, I²C and CLK2 feedback connections. It incorporates the [Gadgetoid Pico 2 W pinout](https://pico2w.pinout.xyz/) underside artwork, with USB at the top, physical pin 40 at upper left and physical pin 1 at upper right. Header assignments were checked against the [Pico 2 W pinout](https://pico2w.pinout.xyz/). The pinout artwork and product names retain their original ownership; the annotations do not relicense them as original MIT project code.

The [QLG3 connector image](../../docs/_static/images/wiring/qrp-labs-qlg3-pico2w-wiring.png) annotates user-supplied QRP Labs board artwork. The [QLG3 module information](https://qrp-labs.com/qlg3) and [QMX+ assembly manual, pages 62–63](https://www.qrp-labs.com/images/qmxp/manuals/assembly_2_00.pdf) define its 3.3 V supply and powered VBAT requirement. GPS VDD and VBAT share Pico 3V3 OUT, physical pin 36, through the joined GPS supply lead. This connection does not supply the Si5351 module. Physical pin 37 is regulator enable, not a supply output. GPS TX uses GP1 (physical pin 2), PPS uses GP3 (physical pin 5), and GPS ground uses physical pin 3. The selected GPS harness uses black for TX, white for PPS and brown for ground; its orange VDD and red VBAT wires join into one red supply lead. The QLG3 header exposes no receiver RX input, so GP0 is unused by GPS. GPS/PPS ingestion is not implemented.

The diagnostic C++ and Python sources are original MIT project work using the register equations identified in Skyworks AN619 revision 0.8. They do not incorporate the manufacturer's example driver. Exact register arithmetic assumes the stated reference; it does not establish its physical frequency.

## Limits and hardware use

These are experimental conducted-bench tools, not production drivers or general hardware qualification. Cross-linking, exact arithmetic, and register readback do not establish electrical compatibility, physical RF inactivity, calibrated frequency, modulation quality, power, or emissions. Failed bus transactions cannot establish safe output state. Do not reuse these sketches as the application's execution or cleanup authority.

Before a hardware run, identify the board and current application, verify the intended RF termination and exclusive pin assignments, retain its exact image and settings, and check the RAM-only UF2 payload addresses. Use the finite command limits and restoration procedure in the selected tool's README. After testing, verify the original flash bytes and restore the application, settings, identity, and inactive output. Ordinary development deployments continue to use the shared installer transaction.
