# Dual USB CDC foundation

Console = human-readable UTF-8 diagnostics only. WTP = WTP frame stream only.
Never send logging, debug output, prompts or unframed JSON through WTP. The
transport accepts binary bytes; the future protocol sender must supply valid
WTP/1 frames. This image deliberately sends no WTP responses or events. It
uses the existing portable frame parser and leaves JSON dispatch unimplemented.

## Identity and ownership

`src/usb/roles.h` defines the mapping:

| Role | CDC instance | USB control interface | USB data interface |
| --- | --- | --- | --- |
| WsprryPico Console | 0 | 0 | 1 |
| WsprryPico WTP | 1 | 2 | 3 |

`firmware/usb_descriptors.c` retains manufacturer `WsprryPi`, product
`WsprryPico`, the board-derived USB serial, and development identity
`cafe:4012`. This is not a production VID/PID allocation. Separate endpoint
addresses are Console `81/02/82` and WTP `83/04/84` (notification/OUT/IN).
The pinned TinyUSB macro places role strings on the control interfaces;
association descriptors and data interfaces have no string. Operating systems
and serial libraries may show only the device product or generated filenames.
Identify a role using VID/PID, USB serial and control-interface number, consulting
USB descriptors as needed. Neither tty ordering nor a displayed friendly name
is a discovery contract. USB serial and the hashed WTP device_id are distinct.

The USB adapter is `src/usb/transport.{hpp,cpp}`. Application code uses
`console_write`, `wtp_transport_read` and `wtp_transport_write`, without CDC
indices. `main.cpp` owns `tud_task`, adapter servicing, parser dispatch and job
service polling. Generic USB and UART stdio remain disabled; `snprintf` only
formats console text. No second USB stack or interrupt logging is introduced.

## Bounds and failure semantics

All adapter APIs and TinyUSB callbacks belong to the single main-loop owner.
They must not be called from another core, IRQ, PPS, modulation or timing-critical
path. The adapter adds no locks, waits, host polling loops or dynamic allocation.
This is not a target timing guarantee: TinyUSB services its own event queue and
the existing portable parser can allocate and perform frame-sized work.

- Console has a 2048-byte ring. Each write queues its entire diagnostic or returns
  false and drops it if disconnected or full. Callers supply valid UTF-8; the
  adapter does not transcode or validate text. Pressure never drops part of an
  accepted diagnostic, though a disconnect may truncate a stream in flight.
- Service drains at most 64 Console RX bytes and submits at most 64 Console TX
  bytes per iteration, retaining a short-write suffix. Console input is discarded.
  The bounded startup text fits in the empty queue on each open. Later logs may
  be dropped under pressure; no delivery guarantee is made for diagnostics.
- TinyUSB has independent 64-byte RX/TX FIFOs per function. Each WTP read/write
  call handles at most 64 bytes and returns the actual count. A zero write means
  no progress, not success. The caller owns the frame and must retain the suffix,
  resume on a later iteration, and serialize complete frames without interleaving.
  Never spin until a write succeeds. The main loop reads one chunk per iteration.
- WTP has no extra application TX queue. Accepted bytes retain FIFO order while
  the DTR-active USB connection is healthy; no application-level acknowledgment
  or endpoint compliance is implied. TinyUSB disables FIFO overwrite with DTR.
- Both terminals must assert DTR. DTR deassertion aborts that port's stream and
  clears queued software RX/TX; Console also clears its ring. Mount/unmount
  callbacks reset both sessions. Reset notifications survive close/open transitions
  between main-loop polls, so the parser resets and the Console banner repeats.
  Disconnected RX is discarded. RTS and nominal baud rate do not select behavior;
  1200 baud does not invoke an application reset-to-bootloader handler.
- Clearing a FIFO cannot retract a packet already submitted to a USB endpoint or
  delivered to a host buffer. A host must discard its old stream when reconnecting;
  a future protocol adapter must establish a fresh session and handle framing
  resynchronization. This foundation does not promise seamless frame delivery
  across disconnect, suspend, reset or host failure.
- A parser closed by invalid input or timeout remains closed until a session reset.
  It does not take down Console or block the job-service poll. The RF engine stays
  inhibited. The fatal-error loop continues USB/console servicing.

## Hardware-free checks

Run the normal build and tests from the repository root:

```sh
cmake --preset host-debug
cmake --build --preset host-debug
ctest --preset host-debug
python3 scripts/validate_wtp_contract.py
cmake --preset pico2-w
cmake --build --preset pico2-w
```

`usb_transport_tests` compiles the real adapter against bounded TinyUSB mocks.
It tests short writes, startup-sized UTF-8 text, saturation, independent RX/TX,
binary preservation, parser input, DTR transitions and USB reconfiguration.
Existing portable-core and monitor tests remain enabled.

To also inspect the actual descriptors expanded with a locally available pinned
TinyUSB checkout, configure the optional descriptor test (no download is made):

```sh
cmake --preset host-debug \
  -DWSPRRY_PICO_TEST_TINYUSB_PATH="$PICO_SDK_PATH/lib/tinyusb"
cmake --build --preset host-debug
ctest --preset host-debug
```

Use the SDK checkout specified in the firmware-foundation guide. The descriptor
test checks configuration lengths, four interfaces/two associations, distinct
endpoints, role strings, development VID/PID and the serial callback. Only the
board-ID function is mocked. It is not a host enumeration test.

## Opt-in Linux validation

The following procedure requires separate authorization for the intended USB
operations and an already authorized, loaded image. Do not flash or enable RF
as part of this procedure. Record board, image SHA-256, source revision, inhibited
engine, unsynchronized clock, no transmission mode, host OS and physical setup.

Inspect the device and candidate ports:

```sh
lsusb -d cafe:4012
lsusb -v -d cafe:4012
ls -l /dev/serial/by-id/ /dev/serial/by-path/
udevadm info --query=property --name=/dev/ttyACM0
udevadm info --attribute-walk --name=/dev/ttyACM0
```

Repeat `udevadm` for each candidate. `/dev/ttyACM0` is only an example. Match the
serial and `ID_USB_INTERFACE_NUM` (`00` Console, `02` WTP), or inspect the USB
parent's `bInterfaceNumber` if that property is unavailable. Confirm two CDC ACM
functions and the named control interfaces in `lsusb -v`.

After identification, substitute the actual ports and open both concurrently:

```sh
screen /dev/ttyACM_CONSOLE 115200
# In another terminal:
python3 scripts/wtp_monitor.py /dev/ttyACM_WTP
```

Console should show the complete startup diagnostics. The WTP monitor should
receive no banners or diagnostic bytes; the foundation has no response encoder.
Close/reopen Console while leaving WTP open: the banner repeats only on Console.
Close/reopen WTP: Console remains usable. The monitor rejects malformed input;
its silence alone is not proof of raw-byte silence, so also capture raw WTP bytes
with an authorized serial capture tool configured for DTR and a bounded timeout.
Do not let the monitor and capture tool own the same port simultaneously.

With an authorized bounded serial test driver, send an existing valid frame
from the protocol vectors to WTP. Console should report frame receipt; WTP should
remain silent. Send the same bytes to Console and confirm they do not enter the
parser. Send a partial frame, close/reopen WTP, then send a complete frame; confirm
fresh parsing. Pause Console reads while exercising bounded WTP RX, then resume;
WTP parsing should progress and Console may lose later diagnostics under pressure.
Record observed results rather than assuming hardware success from host tests.
WTP TX pressure is covered by mocks; live TX validation needs a future valid-frame
sender or a separately scoped test image, not an arbitrary echo protocol.

Future udev aliases may use the imported VID/PID, exact USB serial and interface
properties to distinguish roles and boards. Such rules are host configuration,
not a firmware dependency; no aliases are installed by this work.

## macOS and remaining work

Use `python3 scripts/wtp_monitor.py --list`, `ls /dev/cu.usbmodem*`, and
`ioreg -p IOUSB -l -w 0` to correlate device serial and interface identity.
Generated filenames vary. Substitute the identified Console port in `screen`
and WTP port in the monitor. A normal terminal should assert DTR; a custom client
must do so explicitly. Exit screen with Control-A, backslash, then `y`.

Future work is strict target JSON decoding, WTP response/event encoding, serialized
frame-send ownership and reconnect/session handling, typed dispatch and host
discovery. This change neither implements a full WTP endpoint nor qualifies USB,
timing or RF on hardware.
