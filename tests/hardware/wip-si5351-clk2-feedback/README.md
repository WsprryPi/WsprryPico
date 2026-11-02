# CLK2 to GP7 feedback diagnostic

This opt-in RAM-only Pico 2 W diagnostic checks a physical connection from QRP Labs CLK2 (module header pin 19) to GP7 (Pico physical pin 10), with common ground. GP7 is held input-only using the GPIO output-enable override. I²C0 uses GP4/GP5 at 100 kHz and address `0x60`. The module outputs 3.3 V logic.

A nominal 25 MHz TCXO, PLLA multiplier 36 and integer MultiSynth2 divide-by-900 produce 1 MHz on CLK2 at the 2 mA drive setting. CLK0/CLK1 stay powered down. Original MIT implementation follows the register equations in Skyworks AN619 revision 0.8; no upstream implementation is incorporated.

GP7 is PWM channel B. Its hardware counter counts input rising or falling edges, rather than counting software GPIO polls. Three 10 ms rising-edge measurements with CLK2 disabled must each count zero. Six enabled measurements (three rising, three falling) must each indicate 0.95–1.05 MHz with no counter wrap. Three post-disable rising-edge measurements must again count zero. The short gate checks detection; it does not establish calibrated frequency or duty cycle.

USB `INFO` identifies the sketch and board. One explicit `TEST` is allowed per boot. The bounded local test snapshots touched registers, checks PLLA lock, counts the off/on/off sequence, verifies output disable and restores registers. I²C transactions have 10 ms deadlines; failed writes cannot establish inactivity. `STOP` independently requests output disable. The external TX LED is not driven, consistent with the user's direction to leave the diagnostic LED behavior alone.

Use retained Pico SDK 2.3.1 and Arm GCC 15.3.1 with `-DPICO_NO_FLASH=1`, the existing pinned SDK and picotool sources, and a separate private build directory. The CMake target refuses flash builds. See the [development guide](../../../engineering/development/README.md).

Before loading, verify exact USB identity, idle application state, disabled schedules and free GP4/GP5/GP7 assignments. Retain full flash privately, validate all UF2 payloads as SRAM addresses and use guarded BOOTSEL entry. After testing, compare all flash bytes, reboot the original application and check settings, identity and inactive output. This diagnostic adds no production feedback, calibration or Si5351 engine capability.
