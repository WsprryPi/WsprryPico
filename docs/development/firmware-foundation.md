# Pico 2 W firmware foundation

The firmware foundation builds the portable WTP job service for Pico 2 W and
RP2350 Arm Secure. It exposes two USB CDC interfaces and uses an RF-inhibited
local lifecycle simulator. The standard image now initializes Wi-Fi when
configured, but never initializes an RF output pin or synthesizer. See the
[standalone guide](standalone.md) for current configuration and timing behavior.

## Pinned build inputs

- Raspberry Pi Pico SDK 2.3.1 at
  `079c6f39023649b154152db30f1d781e884879bc`.
- Arm GNU Toolchain 15.3.Rel1, compiler version 15.3.1.
- picotool 2.3.0 at
  `6f6458d792b93685a11423b244a585eaa99eafcf`.
- CMake 3.24 or later and Ninja.

CMake rejects a different SDK commit or compiler version. Set `PICO_SDK_PATH`
to the pinned checkout. A sibling checkout at `../pico-sdk` is also detected.
The SDK fetches the pinned picotool source into the ignored build directory,
even when another picotool is installed.

SDK 2.3.1 includes upstream RP2350 synchronization and alarm-wait repairs.
Use a fresh build directory when upgrading from 2.3.0; existing caches retain
SDK paths and generated files. Preserve previous qualification artifacts. The
project does not override the SDK synchronization defaults.

Configure and build from the repository root:

```sh
cmake --preset pico2-w
cmake --build --preset pico2-w
```

The build produces `build/pico2-w/firmware/WsprryPico.elf`, `.bin`, `.hex`,
`.dis`, `.map` and `.uf2`. Generated artifacts are ignored. The UF2 metadata
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
the configured Wi-Fi SNTP source supplies a usable observation. The portable
discipline ages its uncertainty; no wall-clock state survives reboot.

See the [dual USB CDC guide](usb-cdc.md) for transport bounds, connection
semantics, descriptor identity, Linux/macOS validation and focused tests.

## USB interfaces and monitoring

The development USB identity uses TinyUSB's shared development VID `0xcafe`
and PID `0x4012`. It is not a production USB allocation. The composite device
has two CDC interfaces:

1. `WsprryPico Console` carries standalone configuration commands and JSON diagnostics.
2. `WsprryPico WTP` accepts binary WTP frames only.

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
tests. `DryRunEngine` models local job lifecycles but always reports output
inactive and accesses no hardware. The inhibited firmware entry point requires the
`WSPRRY_PICO_RF_OUTPUT_DISABLED=1` compile definition.

The WTP CDC path now implements strict JSON request decoding, response/event
encoding, typed dispatch and logical session handling through the
[WTP endpoint](wtp-endpoint.md). The firmware still has no physical RF engine
and accepts simulated jobs only when the autonomous clock meets admission
requirements. Endpoint host tests do not establish target USB conformance.

Building the image is hardware-free. No target execution was recorded unless a
report explicitly names the board, firmware digest, connection and observed
output. A build does not establish USB behavior, target timing, electrical
safety, RF behavior or WTP conformance.
