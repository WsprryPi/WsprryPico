# Independent Si5351 reference measurement

This opt-in, RAM-only fixture measures a fitted 25 MHz reference independently against QLG3 PPS. It is test equipment, excluded from ordinary firmware; it implements no production GPS ingestion, UTC-second pairing or automatic RF calibration.

The fixed wiring is Pico 2 W at 138 MHz, I²C0 GP4/GP5 at 100 kHz, address 0x60, CLK2 into input-only GP7, QLG3 TX into UART0 RX GP1 at 9600 baud, and PPS into input-only GP3. CLK0 and CLK1 must already be disabled. An existing CLK2 measurement output is allowed. Verify actual board identity, allocation and electrical connections before use. Use a properly terminated conducted RF setup even though this fixture never enables a transmit output.

Build with retained Pico SDK 2.3.1 (`079c6f39023649b154152db30f1d781e884879bc`), Arm GNU 15.3.1 and picotool 2.3.0 (`6f6458d792b93685a11423b244a585eaa99eafcf`):

```sh
cmake -S tests/hardware/si5351-reference-truth -B build/si5351-truth \
  -G Ninja -DPICO_NO_FLASH=1 -DCMAKE_BUILD_TYPE=Release
cmake --build build/si5351-truth --parallel 4
```

`INFO` reports the physical USB serial and test allocation. One `TEST` captures 301 PPS rising edges, bounded by 310 raw seconds. A two-second pre-window UART drain removes partial characters received during peripheral setup. No output printing occurs inside the measurement loop. The extended PWM count rejects polling gaps of 400 µs or more, below one possible counter wrap at the hardware edge-rate bound. Each PPS has outward raw-time and edge-count brackets; count reads occur on both sides of the GPIO read. The result retains checksum-verifiable NMEA bytes and reports UART errors, maximum gap and register restoration. `BOOTSEL` returns to recovery mode; the idle command loop also has a 400-second limit. Capture data may contain location information and belongs in private ignored evidence directories.

Run the fixture only within a preserving recovery transaction: stop conflicting device owners, verify the original same-board image/reference and full-flash backup, verify that every UF2 payload targets RAM, execute the finite diagnostic, return to BOOTSEL, compare all 4 MiB against the backup and reboot the original application. Verify saved semantics, idle/unowned/output-inactive state and service restoration. Never replace the installer's image reference with this diagnostic or use it as an ordinary upgrade. If a reference needs reconciliation, use the actual retained bundle and the shared installer's exact same-board comparison.

Analyze a retained transcript with:

```sh
python3 tests/hardware/si5351-reference-truth/analyze.py private/transcript.txt
```

The analyzer requires 301 coherent PPS edges, brackets no wider than 100 µs, zero UART/checksum errors, at least 295 valid RMC and GGA fixes, and successful register restoration. It calculates intervals using count quantization, both capture endpoints and an explicit conditional 10 µs allowance per PPS endpoint. The Ebyte E108 manual's 30 ns timing figure is typical and statistical, not a guaranteed maximum; the engineering 10 µs allowance is deliberately larger but is not a metrology certificate. Report this condition alongside every result.

The finite observation covers the actual board, warmed supply and environment during the capture. It does not establish warmup, supply-range, temperature-range or aging guarantees, physical ordinary-image launch accuracy, a one-hour timer-drift bound, or every fitted TCXO's total error. A conditional illustrative ±500 ppb value is not an acceptance requirement. The manufacturer's [TCXO page](https://shop.qrp-labs.com/tcxo) describes temperature behavior; the [E108 manual](https://qrp-labs.com/images/qlg2/gk9501en.pdf) describes the independent test receiver.
