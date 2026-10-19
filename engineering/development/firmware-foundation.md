# Pico 2 W firmware foundation

The firmware foundation builds the portable WTP job service for Pico 2 W and
RP2350 Arm Secure. It exposes three USB CDC interfaces and uses the existing 138 MHz PIO/DMA
RF application by default. `WsprryPico-Inhibited` explicitly selects the local
lifecycle simulator without a physical RF engine. Both retain the same USB,
Wi-Fi, storage and application services. RF capability preserves saved
enablement, timing, ownership, frequency policy and output-admission controls. See the
[standalone guide](standalone.md) for current configuration and timing behavior.

## Pinned build inputs

- Raspberry Pi Pico SDK 2.3.1 at
  `079c6f39023649b154152db30f1d781e884879bc`.
- Arm GNU Toolchain 15.3.Rel1, compiler version 15.3.1.
- picotool 2.3.0 at
  `6f6458d792b93685a11423b244a585eaa99eafcf`.
- CMake project minimum 3.24; the checked-in version-6 presets require CMake
  3.25 or later. Ninja, Python 3, Git and the host compiler needed by picotool
  must already be available.
- Owned C++ uses required C++20 without extensions. Application C sources use
  required C11 with GNU extensions enabled for SDK assembly integration; this
  is set on firmware targets, not as a global C standard for every dependency.

CMake rejects a different SDK commit or compiler version. Set `PICO_SDK_PATH`
to the pinned checkout. A sibling checkout at `../pico-sdk` is also detected.
Required SDK submodules must already be populated and clean at their pinned
revisions. Linked lwIP, CYW43 and Mbed TLS overrides are checked too. The SDK
import does not download an SDK. CMake forces its pinned picotool Git source
even when another picotool is installed; a direct configure can fetch that
source if no retained local source is supplied.

For an offline local build, set `PICO_SDK_PATH` to the retained SDK and
`PICOTOOL_FETCH_FROM_GIT_PATH` to a populated directory containing
`picotool-src` at the pinned commit, then use the helper below. These are local
inputs, not prescribed developer-specific paths. It uses that local Git source
with private dependency build outputs under the selected build directory.
On macOS the helper sources `scripts/xcode_env.sh` and requires full Xcode for
host helper compilation, as the [development guide](README.md) describes.

SDK 2.3.1 includes upstream RP2350 synchronization and alarm-wait repairs.
Use a fresh build directory when upgrading from 2.3.0; existing caches retain
SDK paths and generated files. Preserve previous qualification artifacts. The
project does not override the SDK synchronization defaults.

Configure and build from the repository root:

```sh
cmake --preset pico2-w
cmake --build --preset pico2-w
```

For an explicit inhibited build in that configured directory:

```sh
cmake --build build/pico2-w --target WsprryPico-Inhibited
```

It produces `firmware/WsprryPico-Inhibited.uf2` and the matching ELF/map.
`WsprryPico-StandaloneRF` remains an explicit compatibility target with its
existing artifact basename and the same RF application wiring as `WsprryPico`.
Ordinary firmware `all`, the `pico2-w` preset and `bash scripts/build_pico.sh`
select `WsprryPico`. The helper also accepts `WsprryPico-Inhibited` or
`WsprryPico-StandaloneRF` as its first argument and an optional fresh build
directory as its second. Host builds still default to no SDK dependency.
Inhibited-only fixture options refuse RF target/all builds; use the explicit
inhibited target. Candidate manifests and inhibited live dispatchers require the explicit
inhibited target name. Artifact basenames identify the actual selected target.

Helper invocation from the repository root, after setting the two local
dependency variables above:

```sh
# Each example uses a fresh output directory; choose unused names locally.
bash scripts/build_pico.sh WsprryPico build/local-normal
bash scripts/build_pico.sh WsprryPico-Inhibited build/local-inhibited
bash scripts/build_pico.sh WsprryPico-StandaloneRF build/local-compat-rf
```

With no arguments the helper selects `WsprryPico` and `build/pico2-w-local`.
Target-only inhibited and compatibility selections default to
`build/pico2-w-local-inhibited` and `build/pico2-w-local-standalone-rf`.
It accepts at most a supported target and build directory, uses Ninja/Release,
disables host tests, selects `pico2_w` and builds that target with four jobs.
Its local picotool source defaults to `build/pico2-w/_deps/picotool-src` if the
environment override is absent; missing SDK/source inputs refuse before build.
Outputs are under `<build-directory>/firmware/<target>.*`. Preserve retained
evidence directories rather than reconfiguring them for another variant.

`WsprryPico-RFBench` and legacy USB-time `WsprryPico-RFWTP` are separate explicit
diagnostic targets, not application variants. Bench/fixture definitions and
historical image names must be interpreted with their recorded source/role;
they do not select the normal application or establish release qualification.

The normal build produces `build/pico2-w/firmware/WsprryPico.elf`, `.bin`, `.hex`,
`.dis`, `.elf.map` and `.uf2`. Generated artifacts are ignored. The UF2 metadata
contains the product, development version, source revision, SDK, board and
target. The SDK build-date field is disabled so wall-clock time does not enter
that metadata.

## Firmware identity

The firmware reports product `WsprryPico`, version `0.0.0-devel`, and the
12-character Git revision. A dirty source tree adds `-dirty`. This version is a
development identity and does not assign a release.

On RP2350, the SDK reads the stable 64-bit unique identifier from OTP. The
firmware hashes a WsprryPico namespace and that identifier, then uses the first
128 bits as the lowercase WTP `device_id`. It uses the SDK `pico_rand`
128-bit generator for each `boot_id`; an all-zero entropy result fails service
initialization. These values identify protocol state; they are not credentials
or proof of device authenticity.

The target clock reports monotonic microsecond hardware time converted to
nanoseconds. UTC starts `unsynchronized`, so the service rejects `ARM` until
the configured Wi-Fi SNTP source or qualified USB-time source supplies a usable observation. The portable
discipline ages its uncertainty; no wall-clock state survives reboot.

See the [USB CDC roles guide](usb-cdc.md) for transport bounds, connection
semantics, descriptor identity, Linux/macOS validation and focused tests.

## USB interfaces and monitoring

The development USB identity uses TinyUSB's shared development VID `0xcafe`
and PID `0x4012`. It is not a production USB allocation. The composite device
has three CDC interfaces:

1. `WsprryPico Console` carries standalone configuration commands and JSON diagnostics.
2. `WsprryPico WTP` accepts binary WTP frames only.
3. `WsprryPico Management` carries separately framed management/time transactions.

On macOS, list ports after connecting the board:

```sh
python3 scripts/wtp_monitor.py --list
ls /dev/cu.usbmodem*
```

Open the console port with the system `screen` command:

```sh
screen /dev/cu.usbmodemXXXX 115200
```

Exit with Control-A, backslash, then `y`. Inspect the WTP port with:

```sh
python3 scripts/wtp_monitor.py /dev/cu.usbmodemYYYY
```

The monitor validates framing, length, CRC-32C, UTF-8 and strict JSON before
printing a message. Only one process can own a serial device at a time.

## Implemented boundary

The firmware instantiates and polls the same portable `JobService` used by host
tests. The normal target connects the existing RF worker and engine. In the
explicit inhibited target, `DryRunEngine` models local job lifecycles but always reports output
inactive and accesses no hardware. The inhibited firmware entry point requires the
`WSPRRY_PICO_RF_OUTPUT_DISABLED=1` compile definition.

The WTP CDC path now implements strict JSON request decoding, response/event
encoding, typed dispatch and logical session handling through the
[WTP endpoint](wtp-endpoint.md). Both variants enforce the existing timing and ownership admission; only the
explicit inhibited variant simulates execution without physical RF. Endpoint host tests do not establish target USB conformance.

Building the image is hardware-free. No target execution was recorded unless a
report explicitly names the board, firmware digest, connection and observed
output. A build does not establish USB behavior, target timing, electrical
safety, RF behavior or WTP conformance.

Build authority: [root CMake](../../CMakeLists.txt),
[presets](../../CMakePresets.json),
[application wiring](../../firmware/CMakeLists.txt),
[dependency verification](../../cmake/verify_pico_dependencies.cmake) and
[local helper](../../scripts/build_pico.sh). Existing
[image-selection checks](../../tests/application_image_tests.py) exercise
role selection and refusal behavior; their passes do not qualify physical RF.
