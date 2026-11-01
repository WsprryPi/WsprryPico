# Fixed CLK0 tone diagnostic

This opt-in Pico 2 W diagnostic runs from RAM, outside the production application. It uses I²C0 on GP4/GP5 at 100 kHz and address `0x60`. A 25 MHz reference, integer PLLA multiplier 36 and integer MultiSynth0 divisor 72 produce a nominal 12.5 MHz CLK0 tone at the 2 mA drive setting. CLK1/CLK2 remain powered down. It does not implement a production Si5351 engine or change settings in flash.

The original MIT implementation follows the register definitions and equations in [Skyworks AN619, revision 0.8](https://www.skyworksinc.com/-/media/Skyworks/SL/documents/public/application-notes/AN619.pdf). No upstream implementation is incorporated.

Use the retained Pico SDK 2.3.1 and Arm GCC 15.3.1 described in the [development guide](../../../engineering/development/README.md), with `-DPICO_NO_FLASH=1`. The target refuses a flash build. Supply the existing SDK and pinned picotool source paths explicitly; do not fetch dependencies for a bench run. The built UF2 must contain only SRAM-addressed payloads.

USB commands are `INFO`, `TONE`, and `STOP`. One `TONE` is admitted per boot; it requires CLK0/1/2 to be masked off or powered down, saves touched registers, checks PLLA lock, enables only CLK0 for five seconds, then verifies output disable and restoration of the touched writable registers. USB disconnect or an `S` byte during the tone requests early shutdown. Each I²C transaction has a 10 ms deadline. Failed writes or readbacks cannot establish RF inactivity.

Before loading, identify the exact board and USB parent, verify idle state and disabled schedules, save its full flash privately, and confirm GP4/GP5 are free. Enter BOOTSEL through the application's guarded Console command. Load only the verified SRAM image. Capture quiet intervals before and after the tone through the operator-confirmed attenuator/SDR path. Finally verify the full flash against the saved bytes, reboot the original application and check identity, settings, idle state and inactive output. Flash backups can contain credentials and must remain outside Git and served documentation.

The test establishes only its measured board, reference, output and RF path. It does not qualify WSPR timing, emissions, absolute power or calibrated frequency accuracy.
