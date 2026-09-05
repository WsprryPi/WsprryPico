# Bounded Pico 2 W USB validation

## Image and setup

The tested firmware source is clean commit
`1605a684b02e18055fab1f121c49ec873a10e54c`. Documentation and the opt-in
capture driver added alongside this record do not change that firmware image.

- UF2 SHA-256: `bf87ae61e3c461c81aea995c65f1e725f5dba6c3b00eb4edd32d62eb840aa1de`.
- Product/version/revision: `WsprryPico`, `0.0.0-devel`, `1605a684b02e`.
- Build metadata: `pico2_w`, RP2350 ARM Secure, Release, SDK 2.3.0,
  `boot2_w25q080`; no fixed pins reported by picotool.
- SDK commit: `98a542c1a62fb549ffb5d66a3e5892b06276b670`.
- TinyUSB commit: `86ad6e56c1700e85f1c5678607a762cfe3aa2f47`.
- Arm GNU compiler: 15.3.1 (pinned 15.3.Rel1 toolchain).
- picotool: 2.3.0, commit `6f6458d792b93685a11423b244a585eaa99eafcf`.
- Host: `Lees-MacBook-Pro`, macOS 26.6.2 build 25G83, arm64.
- Attached board: user-identified Pico 2 W; BOOTSEL reports RP2350,
  USB serial `0BF4B4AEC9FFB344`, initial location `0x02100000`.
- WTP device ID: `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Initial boot ID: `3392bafd154cab802c3ecc585b9179c6`.
- Engine: `inhibited-no-rf`; clock: `unsynchronized`; no job or transmitting mode.
- Setup: board connected to the named Mac over USB. External wiring was not
  inspected; no electrical or RF measurement was performed.

The initial BOOTSEL device was `2e8a:000f` at `/Volumes/RP2350`. Copying the
UF2 caused that volume to disappear and the application to enumerate. macOS
`cp` returned an extended-attribute copy error; subsequent Console revision,
USB identity and successful protocol exchanges established application startup.
Flash contents were not read back, so the digest identifies the supplied UF2,
not an independently measured flash digest. For subsequent BOOTSEL copies use
`cp -X` to avoid extended attributes.

## Observed USB identity

macOS IORegistry showed one `WsprryPico` device, manufacturer `WsprryPi`,
VID/PID `cafe:4012`, USB 2.00, device class/subclass/protocol `ef/02/01`, one
configuration, 64-byte endpoint zero, full speed (12 Mbit/s), and the same
board serial. The CDC composite driver attached both ACM functions.

| Role | Control interface | Data interface | Observed callout path |
| --- | --- | --- | --- |
| WsprryPico Console | 0, class/subclass 02/02, string 4 | 1, class 0a | `/dev/cu.usbmodem2101` |
| WsprryPico WTP | 2, class/subclass 02/02, string 5 | 3, class 0a | `/dev/cu.usbmodem2103` |

Control interfaces each report one endpoint; data interfaces each report two.
The identity mapping comes from the device serial and IORegistry interface
parentage, not filename ordering. Exact endpoint addresses are covered by the
host descriptor test; this record does not claim a raw USB bus capture.

## Target observations

The repository read-only probe completed HELLO, CAPS, GET_CLOCK, STATUS and
PING successfully while Console was open. Responses passed its schema and
request/session identity checks. Console was complete readable UTF-8, reporting
matching device/boot identity and source revision, `job_service: ready`,
`clock: unsynchronized`, `engine: inhibited`, and `rf_output: false`.

CAPS returned `inhibited-no-rf`. GET_CLOCK returned `unsynchronized`, UTC zero,
unknown leap state and maximum unsigned 64-bit uncertainty/sync age. STATUS
returned `empty`, `output_active: false`, null owner/job and no terminal records.
The advertised numeric frequency range is simulated input acceptance, not RF coverage.

The additional opt-in driver captured request/response bytes and rejected any
unframed prefix/suffix, invalid header, length, CRC-32C, UTF-8, schema or response
identity. All observed exchanges passed. WTP remained silent before HELLO and
when Console reopened. Console showed no bytes from the WTP exchanges; reopening
Console repeated the same complete banner only on Console.

DTR close/open required fresh HELLO negotiation: a PING first received
`HELLO_REQUIRED`. Repeating this after leaving 19 bytes of an incomplete PING
frame produced the same result, with no stale response bytes. Reopening and
negotiating HELLO restored successful PING/STATUS. Fresh negotiation does not
mean the contract requires a new session ID: service sessions may survive a
transport disconnect. The driver also exercised new session IDs.

## Physical reconnect

After the ports were closed, the user unplugged and reconnected USB without
BOOTSEL. The serial nodes were observed absent during disconnection. IORegistry
then showed the same composite device, interface mapping and serial paths.
Console still reported revision `1605a684b02e` and the same device ID, with new
boot ID `e82cf65412edfc3edeb78d8d0d8448c8`. The complete maintained driver passed
after reconnect, including its unchanged five-operation probe and ten strict
raw exchanges (eight successes and two expected `HELLO_REQUIRED` errors).
The clock remained unsynchronized and output inactive.

Local raw evidence is under `build/usb-target-evidence/`: `ioreg.txt`,
`ioreg-reconnected.txt`, the initial `console.txt`/`probe.jsonl`, and
`reconnect-1`/`reconnect-2` captures with corresponding `.txt` command outputs.
The second run includes the final Console/WTP cross-identity checks. These
captures are intentionally ignored; the observed identities, results and
reproducible driver are maintained here.

## Reproduction

Run from the repository root. Target commands require explicit authorization,
an identified board and the exact RF-inhibited image. Preserve generated images
and raw captures under ignored `build/`, not source control. Use a new capture
output directory for each run; the driver refuses to overwrite one.

```sh
cmake --preset host-debug -DWSPRRY_PICO_TEST_TINYUSB_PATH="$PICO_SDK_PATH/lib/tinyusb"
cmake --build --preset host-debug
ctest --preset host-debug
python3 scripts/validate_wtp_contract.py
cmake --preset pico2-w
cmake --build --preset pico2-w
python3 scripts/check_endpoint_image.py build/pico2-w/firmware/WsprryPico.elf
shasum -a 256 build/pico2-w/firmware/WsprryPico.uf2
build/pico2-w/_deps/picotool/picotool info -a build/pico2-w/firmware/WsprryPico.uf2
# Only with the intended board identified and mounted in BOOTSEL:
cp -X build/pico2-w/firmware/WsprryPico.uf2 /Volumes/RP2350/WsprryPico.uf2
# Wait for enumeration; rediscover paths on each host/connection:
ioreg -p IOUSB -w 0
ioreg -p IOService -r -n 'WsprryPico@02100000' -l -w 0
python3 scripts/wtp_monitor.py --list
python3 scripts/check_usb_target.py --console /dev/cu.usbmodem2101 \
  --wtp /dev/cu.usbmodem2103 --output build/usb-target-evidence/new-run --run
```

The initial flash command was `cp` without `-X`. The initial standalone probe
was `python3 scripts/wtp_probe.py /dev/cu.usbmodem2103 --run`, with Console
opened concurrently using `configure_raw`, explicit DTR and a bounded read.
The maintained capture driver repeats that probe unchanged and supplies the
additional bounded read-only reconnect checks. It does not flash or send any
job/ownership mutation. Close all other applications using these ports first.

## Host checks and adversarial review

- Six host tests passed, including actual TinyUSB descriptor expansion.
- Five address/undefined-behavior sanitizer tests passed using the documented
  endpoint sanitizer configuration.
- Contract artifacts passed 23 schema, 7 raw JSON, 1 framing and 8 transition cases.
- Pinned firmware build passed. ELF inspection confirmed a 16 KiB primary stack
  excluded from heap/core-1 stack.
- Capture driver syntax and missing-`--run` gate passed without device I/O.

Review found that the existing monitor decoder resynchronizes past stray bytes;
a successful probe alone cannot establish absence of Console leakage. The
additional target driver therefore validates the entire raw response with no
resynchronization. It also cross-checks Console/WTP device and boot identities,
checks inactive STATUS, retains incomplete-frame evidence and refuses capture
overwrite. These checks passed on target. No firmware defect was exposed.

Source and linked-symbol review found no GPIO, PIO, PWM, clock-output,
CYW43, SPI or I2C driver functions in the image. The application initializes
USB and the inhibited service; no RF output path is configured. **This does not
mean every potentially RF-capable peripheral remains untouched:** pinned SDK
startup initializes system clocks and resets/releases peripheral blocks.
No SDK changes or target register inspection were performed. This is source
and image evidence for inhibition, supported by reported inactive output;
it is not an electrical measurement.

## Limits

This is bounded target USB evidence for the identified board, image and Mac.
It is not general WTP conformance, timing, electrical safety or RF qualification.
Target memory high-water, resource exhaustion, long-duration USB pressure,
other hosts/cables/hubs and RF engines remain unqualified. No GPIO, PIO, PWM,
clock output, synthesizer, debugger, job loading/arming or RF operation was
performed. The next development slice remains RF feasibility and engine
selection; implementation or measurement involving outputs needs separate
explicit authorization.
