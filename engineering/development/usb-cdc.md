# USB CDC transport roles

Console provides bounded line administration and UTF-8/JSON diagnostics. USB-Management/1 provides independent framed management/time requests. Logging has its own diagnostic stream. Application firmware leaves the Reserved allocation inactive. RFBench uses that allocation for its Commands interface.

## Identity and ownership

| Role | CDC instance | Control interface | Data interface |
| --- | --- | --- | --- |
| Console | 0 | 0 | 1 |
| Reserved (RFBench: Commands) | 1 | 2 | 3 |
| Management | 2 | 4 | 5 |
| Logging | 3 | 6 | 7 |

Manufacturer WsprryPi, product WsprryPico, board-derived serial, development VID/PID cafe:4012, and endpoint addresses remain stable. Addresses are Console 81/02/82, Reserved 83/04/84, Management 85/06/86, and Logging 87/08/88 (notification/OUT/IN). This is not a production VID/PID allocation. Role strings belong to control interfaces. Identify roles by exact physical USB parent, serial, VID/PID, control-interface number, and current management handshake; tty order and friendly names are not identity. USB serial and full control device ID are distinct. Discover Management directly using its own interface.

## Bounds and servicing

TinyUSB and adapter APIs belong to the single foreground owner, never an IRQ, PPS path, or other core. Console retains its nullable 8192-byte ring, 32 KiB allocation reserve, complete-write/drop policy, bounded 64-byte RX/TX servicing, and retained short-write suffix. Diagnostic pressure can drop output; it cannot authorize execution. Generic USB/UART stdio remains disabled.

Application firmware drains at most 64 Reserved input bytes per servicing iteration without parser, reply, or engine entry. Management retains its independent bounded UMP1 transaction, matching response ACK, cancellation, and time policy. Logging retains its own framing and pressure policy. Mount/unmount and per-role DTR reset stream state; RTS and nominal baud do not select a protocol. A disconnected stream is not an inactive-output observation.

## Validation

Host adapter and optional actual-descriptor tests check bounded draining, isolation, DTR/reset, short writes, eight interfaces/four associations, distinct endpoints, role strings, serial callback, and stable identity. Configure `WSPRRY_PICO_TEST_TINYUSB_PATH` with the pinned local SDK checkout to include actual descriptor expansion. See [firmware builds](firmware-foundation.md), [USB management](../protocol/USB-Management.md), and [native execution safety](../protocol/Native-Execution.md). Builds and mocks do not establish physical enumeration, USB timing, GPIO, or RF qualification.

## Console and authoritative status

Console INFO is scheduler diagnostic JSON. Its last_job may be empty while another native owner exists. It does not replace authenticated `/api/control/v1/status`, whose job and standalone objects remain separate. Bind launch counters to the same boot, epoch, and observation time. Missing Console fields never prove unowned or inactive output.

## Browser Console compatibility

Native Windows Chrome exposes Console through Web Serial. Device Manager can label all functions **USB Serial Device (COMn)**; the hardware interface suffix MI_00 identifies Console, while MI_02 and MI_04 identify Reserved and Management. Chrome's chooser includes the Console role string. DTR is on; RTS and flow control are off. The [operator walkthrough](../../docs/usb.md) gives the terminal settings, port-release procedure, and current Windows screenshots. A COM number is an example assigned by Windows, not a stable device role.

The bounded Windows Console scope is Windows 11 Pro 26H2 build 26300.9711, Chrome 155.0.8059.85, Pico 2 W serial `1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`, source `03e0df4d7875ec505631e563fa2fe4f5b4834ec4`, normal `pio-dma-gp2` firmware at 138 MHz, with inactive output and no RF mode. INFO, ACCESS SOFTAP, and release for another serial reader are within that scope. Associated-client AP retention beyond the 120-second join grace and reported expiry after a ten-minute disconnected interval use a separate wspr5 Wi-Fi client; those observations do not qualify direct Windows Wi-Fi association, every Console command, the command-line installer, physical RF, or target timing.

## Dedicated Logging compatibility

Logging is appended at control/data interfaces 6/7 with CDC instance 3. Existing device identity, role strings, interfaces 0 through 5, and endpoint assignments are unchanged. The USB device version remains 1.00; hosts must enumerate the updated configuration after the firmware-update disconnect. Operating-system port names can change and are never role identities. Earlier three-function firmware remains supported by Console, Management, and the installer. Missing Logging is an explicit unsupported capability; the collector never opens Console as a fallback. See [USB logging](usb-logging.md) for the independent USB-Logging/1 handshake and budgets.
