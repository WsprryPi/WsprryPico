# GP4/GP5 Si5351 connection probe

This standalone diagnostic stays outside the normal application build. It
checks I²C communication with an attached candidate and implements no production
Si5351 RF engine. The [Si5351 design reference](../../../docs/development/si5351-engine-notes.md)
defines the engine boundary and the consolidated backlog selects unfinished work.

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

## Observed communication scope

Pico B, USB serial `CDDBF8767C506C07`, with application-only probe UF2 SHA-256
`2bd344a921314a363d9d2d26df568bbb235eb559012112f6157bf84f77ad4a4e`,
returned one address, **0x60**, with GP4/GP5 HIGH at idle. Three checked
read-pointer transactions returned these register values at 100 kHz:

| Samples | Device status (0) | Interrupt status (1) | Output-disable mask (3) |
| --- | --- | --- | --- |
| 3 | `0x11` | `0xF8` | `0x00` |

This bounded observation establishes communication on that board and wiring.
It establishes neither unique silicon identity, present wiring, configured
frequency nor RF output. The probe does not program frequencies or output
configuration. It is a separate diagnostic image; ordinary firmware and saved
settings require their own restoration/readback when a probe is deliberately run.
