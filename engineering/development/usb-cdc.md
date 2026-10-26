# USB CDC transport roles

Console = bounded line administration and UTF-8/JSON diagnostics. WTP = WTP frame stream only.
Never send logging, debug output, prompts or unframed JSON through WTP. The
transport accepts binary bytes; the [strict WTP endpoint](wtp-endpoint.md)
supplies valid WTP/1 frames, performs JSON dispatch and serializes responses and
events. No unsolicited diagnostics are emitted on WTP.

USB JSON administration is independently defined by [USB-Management/1](../protocol/USB-Management.md).
A third management CDC role carries framed shared-API requests and qualified
UTC observations. Console and WTP roles and byte streams remain unchanged.
The [local configuration contract](usb-local-configuration.md) defines no-network
profiles, hostname and saved Wi-Fi lifecycle. Network authentication is unchanged.

## Identity and ownership

`src/usb/roles.h` defines the mapping:

| Role | CDC instance | USB control interface | USB data interface |
| --- | --- | --- | --- |
| WsprryPico Console | 0 | 0 | 1 |
| WsprryPico WTP | 1 | 2 | 3 |
| WsprryPico Management | 2 | 4 | 5 |

`firmware/usb_descriptors.c` retains manufacturer `WsprryPi`, product
`WsprryPico`, the board-derived USB serial, and development identity
`cafe:4012`. This is not a production VID/PID allocation. Separate endpoint
addresses are Console `81/02/82`, WTP `83/04/84` and management `85/06/86`
(notification/OUT/IN).
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

- Console has an 8192-byte output ring. Each write queues its entire diagnostic or returns
  false and drops it if disconnected or full. Callers supply valid UTF-8; the
  adapter does not transcode or validate text. Pressure never drops part of an
  accepted diagnostic, though a disconnect may truncate a stream in flight.
- The main loop reads at most 64 Console bytes per iteration through
  `console_transport_read`; the bounded line parser dispatches standalone and
  physical administration commands. Service submits at most 64 Console TX
  bytes per iteration, retaining a short-write suffix.
  The bounded startup text fits in the empty queue on each open. Later logs may
  be dropped under pressure; no delivery guarantee is made for diagnostics.
- TinyUSB has independent 64-byte RX/TX FIFOs per function. Each WTP read/write
  call handles at most 64 bytes and returns the actual count. A zero write means
  no progress, not success. The caller owns the frame and must retain the suffix,
  resume on a later iteration and serialize complete frames without interleaving.
  Never spin until a write succeeds. The main loop reads one chunk per iteration.
- The USB byte adapter has no extra WTP TX queue; the endpoint has its own
  bounded frame queue. Accepted bytes retain FIFO order while
  the DTR-active USB connection is healthy; no application-level acknowledgment
  or endpoint compliance is implied. TinyUSB disables FIFO overwrite with DTR.
- All three functions must assert DTR. DTR deassertion aborts that port's stream and
  clears queued software RX/TX; Console also clears its ring. Mount/unmount
  callbacks reset all three sessions. Reset notifications survive close/open transitions
  between main-loop polls, so the parser resets and the Console banner repeats.
  Disconnected RX is discarded. RTS and nominal baud rate do not select behavior;
  1200 baud does not invoke an application reset-to-bootloader handler.
- Clearing a FIFO cannot retract a packet already submitted to a USB endpoint or
  delivered to a host buffer. A host must discard its old stream when reconnecting;
  the endpoint requires a fresh HELLO exchange and clients must handle framing
  resynchronization. This foundation does not promise seamless frame delivery
  across disconnect, suspend, reset or host failure.
- A parser closed by invalid input or timeout remains closed until a session reset.
  It does not take down Console or block the job-service poll. Closing the
  transport does not abort already accepted work; RF lifecycle and ownership
  remain in JobService. The fatal-error loop continues USB/console servicing.

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
receive no banners or diagnostic bytes; WTP responses require a negotiated
request. Use the [opt-in probe](wtp-endpoint.md) for a read-only exchange.
Close/reopen Console while leaving WTP open: the banner repeats only on Console.
Close/reopen WTP: Console remains usable. The monitor rejects malformed input;
its silence alone is not proof of raw-byte silence, so also capture raw WTP bytes
with an authorized serial capture tool configured for DTR and a bounded timeout.
Do not let the monitor and capture tool own the same port simultaneously.

With an authorized bounded serial test driver, negotiate HELLO and send existing
valid requests from the protocol vectors to WTP. Verify framed, schema-valid
responses and continued Console isolation. Bytes sent to Console must not enter
the WTP parser. After a partial frame and WTP close/open, negotiate again before
sending another request. Keep any mutation tests separately scoped and RF
inhibited. Pause WTP reads and confirm Console remains usable; after the bounded
TX timeout reopen WTP and use HELLO/STATUS to establish state. Pressure and
reconnect are covered in host tests; record actual board observations separately.

## macOS port identification

Use `python3 scripts/wtp_monitor.py --list`, `ls /dev/cu.usbmodem*`, and
`ioreg -p IOUSB -l -w 0` to correlate device serial and interface identity.
Generated filenames vary. Substitute the identified Console port in `screen`
and WTP port in the monitor. A normal terminal should assert DTR; a custom client
must do so explicitly. Exit screen with Control-A, backslash, then `y`.

The strict WTP endpoint provides JSON decoding, response/event encoding,
serialized frame-send ownership and logical session handling. This original
endpoint record does not establish physical USB/timing/RF qualification.
Later results retain their exact source/image applicability; current work is
selected only in the [Consolidated backlog](consolidated-backlog.md).

## Console INFO and WTP STATUS are different interfaces

Console INFO is implementation diagnostic JSON from the standalone scheduler.
It is not a WTP STATUS response. Its nested `status.last_job` identifies the
scheduler's last job and can be empty during an externally owned job. Use WTP
STATUS `job_id` and `owner_id` with a fresh matching boot for job authority;
do not infer unowned output from missing Console fields. HTTP status exposes
service `job` and scheduler `standalone` objects separately. Console resource
counters require their actual launch epoch and observation time for correlation.

## Windows browser Console validation, 2026-10-26

The Windows portion used native desktop Chrome through an RDP session to `ecm-mule`; the AP portion used the spare `wlan0` adapter on `wspr5`, as directed by the operator. This is bounded Console and setup-network evidence for the installed image. It does not qualify the Windows command-line installer, RF output, target timing or a direct Windows Wi-Fi association.

| Item | Observed identity |
| --- | --- |
| Windows | Windows 11 Pro, DisplayVersion 26H2, build 26300.9711 |
| Chrome at the USB test | 155.0.8059.85 |
| Board | Pico 2 W, USB serial `1545B6EFBF78028C` |
| Device ID | `c2a3a2a314c948b50a8562a1aeb69669` |
| Firmware | `0.0.0-devel`, revision `03e0df4d7875` |
| Matching source | `03e0df4d7875ec505631e563fa2fe4f5b4834ec4` |
| Boot ID throughout the accepted AP observations | `fc2ff9fa82a2f79fafdac569a0ffbffd` |
| Engine and system clock reported by INFO | `pio-dma-gp2`, 138000000 Hz |
| Console / WTP / management | COM6 / COM9 / COM10, interfaces MI_00 / MI_02 / MI_04 |

Device Manager displayed generic **USB Serial Device (COMn)** entries. Its Hardware Ids identified COM6 as MI_00. Chrome's chooser displayed **WsprryPico - WsprryPico Console (COM6)** separately from WTP and management. With DTR on, RTS and flow control off, 115200 baud, Advanced terminal, **send with /n** on and **send with /r** off, the command box and **Send** returned successful uppercase `INFO` and `ACCESS SOFTAP` replies. Scrolling inside the terminal retained the INFO identity fields, network fields and final closing JSON. Closing the terminal tab released COM6 for a subsequent native .NET SerialPort reader. The [operator walkthrough](../../docs/usb.md) contains cropped Windows screenshots of port identity, chooser, signal settings, INFO and the successful setup request.

`ACCESS SOFTAP c2a3a2a314c948b50a8562a1aeb69669` returned `ok:true` and `join_grace_ms:120000`. On wspr5, the temporary AP connection used `wlan0` with automatic default routes and DNS disabled; the existing `wlan1` uplink remained in use. Two HTTP reads of `http://192.168.4.1/`, separated by 181396 ms of monotonic time, returned HTTP 200 and the same 291917-byte document with SHA-256 `47ab9bbc75cb7cccbbced43e91cbb25a1a184c0ded505e420bdd78dfbfcd1dbf`. Both presentation-API replies matched the device and boot IDs above, and NetworkManager reported the AP client connected. This establishes page delivery beyond the initial two-minute join window with a connected client.

The controlled final client disconnect occurred at approximately 21:45:12 UTC. USB INFO then reported the decreasing inactivity countdown while the AP remained ready. At 21:55:09.132 UTC it reported 3320 ms remaining, AP service ready and the AP interface up. At 21:55:14.653 UTC it reported zero remaining, expiry true, adapter running false, service ready false and the AP interface down with address `0.0.0.0`. These samples bracket the expected ten-minute expiry by a 5.522-second observation interval. All 121 samples retained the same boot ID and inactive output; the reader closed the Console after the final sample. This verifies the firmware-reported AP shutdown after real client disconnection; no independent radio capture was made.

After the Windows reboot, native Chrome opened the Pico's reported station address over ecm-mule's existing LAN connection and displayed the Radio access login form. No login, saved-profile change or transmission was performed. The accepted AP retention and expiry observations used wspr5; the earlier Windows Wi-Fi automation did not establish a reliable direct-association result. An earlier temporary Windows DNS override was restored to DHCP, and the operator rebooted Windows after the failed network automation. Following the operator's restriction, no further Windows Wi-Fi, DNS, route, firewall or proxy changes were made. The temporary wspr5 AP profile and disconnect watchdogs were removed or collected; its original adapter and route state was verified.

No firmware was loaded, settings erased or RF job submitted. All sampled USB status objects reported inactive output, disabled scheduling, empty state and no owner. Standalone Console `STATUS` returned `profile_runtime_unavailable` in this `consumer_preclock` setup; this run therefore does not verify the walkthrough's separate ABORT/STATUS procedure or every Console command.
