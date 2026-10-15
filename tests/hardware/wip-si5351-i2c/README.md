# WIP: GP4/GP5 Si5351 connection probe

Status: **WIP — preserved 2026-10-15 for future Si5351 development.**
This standalone diagnostic stays outside the normal application build. The
[external Si5351 transmitter backlog](../../../docs/development/si5351-transmission-backlog.md)
remains deferred. The source and CMake target are preserved unchanged; this
archive adds no production RF engine or new qualification. The dated records
below describe the historical board/firmware state, not the current setup.

Minimal Pico 2 W sketch: I²C0, GP4 SDA (header pin 6), GP5 SCL (header pin 7),
100 kHz, internal pull-ups. An explicit USB `PROBE` command performs one finite
address scan and three register reads at responding addresses 0x60/0x61.
Transactions have 10 ms deadlines. It sets only the read pointer and never
programs frequencies, changes output controls or writes Pico settings.

The [source](main.cpp) links only Pico SDK stdlib, USB, board ID and I²C support.
Use retained SDK 2.3.1 and Arm GCC 15.3.1 with the standalone [CMake target](CMakeLists.txt).
The [Si5351 data sheet](https://www.skyworksinc.com/-/media/SkyWorks/SL/documents/public/data-sheets/Si5351-B.pdf)
documents addressing; [AN619](https://www.skyworksinc.com/-/media/Skyworks/SL/documents/public/application-notes/AN619.pdf)
documents status register 0 and output-enable register 3. An address ACK and
successful reads establish communication with the attached candidate, not
unique silicon identification or RF qualification.

## 2026-10-08 initial attempt

Built and flashed to B, serial `CDDBF8767C506C07`. Application-only UF2 SHA-256:
`2bd344a921314a363d9d2d26df568bbb235eb559012112f6157bf84f77ad4a4e`.
The USB endpoint did not start: B returned to BOOTSEL with both this sketch and
the verified ordinary firmware. Normal and explicit image-execution boot paths
were tried; slot-zero boot diagnostics were zero. No I²C response was collected,
so connection is **NOT TESTED**, not a device NACK or Si5351 failure.

A physical BOOTSEL button check was pending at that checkpoint. Ordinary inhibited firmware
`72d38d505ba2` was reloaded and its flash verification passed. The reserved
settings storage matched the retained recovery image. Successful application
startup/settings readback was then unverified. A's revision, boot and settings
were independently checked unchanged.
Zero RF jobs, no Si5351 configuration writes and no new flash backup occurred.
Private attempt/restoration evidence remains under
`/home/pi/phase13-led-step4-72d38d5/build/si5351-i2c-probe/` on `wspr5`.

## 2026-10-08 recheck: connected

After the operator confirmed BOOTSEL was released, an explicit application
reboot succeeded. The same sketch was flashed to B, and its USB/printed serial
matched `CDDBF8767C506C07`. One finite scan found only address **0x60**. GP4 SDA
and GP5 SCL both read HIGH at idle. Three checked read-pointer transactions
returned four bytes each at 100 kHz:

| Sample | Device status (register 0) | Interrupt status (register 1) | Output-disable mask (register 3) |
| --- | --- | --- | --- |
| 0 | `0x11` | `0xF8` | `0x00` |
| 1 | `0x11` | `0xF8` | `0x00` |
| 2 | `0x11` | `0xF8` | `0x00` |

Result: **CONNECTED**. No frequencies or output configuration were programmed;
zero RF jobs and zero new backups. This establishes the requested I²C connection.

B was restored to ordinary inhibited revision `72d38d505ba2`, boot
`f4e66bc26ad6eac932e8c3c627de2866`, 150 MHz, RF inactive, schedules disabled,
owner/job null, onboard GPIO known OFF/error zero, and settings identical to
entry. A's revision `6c7b14321003`, boot
`e83cac69de154245a974a3efdf5fc8af` and settings were unchanged.

The original script's final A read used a stale network connection. A separate
fresh read of both boards verified restoration and closed that disposition;
neither the original failed attempt nor that cleanup-error record was rewritten.
Private evidence is in `build/si5351-i2c-probe-recheck/` on the same host/root:
`probe.json`, `final-fresh.json` and `assessment.json`.

| Evidence | SHA-256 |
| --- | --- |
| Probe replies | `a96ff3d0730bd0cecc1fb8c9cdcf23f51956172ccdb686c2505e84eda9422d59` |
| Fresh final board readback | `55fbec67dbb3a82f4df5cb6bf7c5fb2a2a08a48a30fe9081504fb5d21533dd19` |
