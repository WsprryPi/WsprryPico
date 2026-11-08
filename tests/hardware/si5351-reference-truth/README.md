# Independent Si5351 reference measurement

This opt-in, RAM-only fixture measures a fitted 25 MHz reference independently against QLG3 PPS. It is test equipment, excluded from ordinary firmware; its default mode implements no production GPS ingestion, UTC-second pairing or automatic RF calibration. The optional production-capture mode compares the actual GPS/PPS and reference-counter adapters against independent electrical-edge brackets.

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


## Production capture comparison

Build with `-DTRUTH_PRODUCTION_CAPTURE=ON` to run the actual
`PicoGpsInput` and `PicoReferenceCapture` adapters on the fixed existing
GP3 PPS / GP7 CLK2 allocation. Core 0 handles production GPS pairing and
counter-at-PPS snapshots. Core 1 owns production reference capture and also
brackets each electrical PPS edge independently by polling the same counter.
The counter is continuous for 301 edges; this diagnostic does not reproduce
the normal application's twelve-second reference-monitor restarts or an RF job.
CLK0 and CLK1 remain disabled. The diagnostic CLK2 plan is the existing
integer PLLA 900 MHz / MS2 900 plan, rather than the production PLLB plan.

After the identity-checked `INFO` reply, `TEST` and `TEST LOAD` each run one
finite 301-edge capture. USB output load alternates every sixty captured PPS
edges. `TEST` starts quiet; `TEST LOAD` starts loaded, reversing the pattern
for the second capture. Load consists of a 64-byte line at most every 10 ms,
only when the USB queue has capacity. A missing reader never authorizes an
unbounded wait. No other output is printed during capture. The final transcript
retains load-write counts, all independent brackets, all production observations,
and capture health. The independent count-extension gap limit remains 400 us.

Analyze the private transcript with:

```sh
python3 tests/hardware/si5351-reference-truth/analyze_production.py private/transcript.txt
```

The analyzer refuses incomplete captures, missing USB load, wrong pin/source
bindings, UART/capture loss, incoherent snapshots, and failed register restoration.
It compares nonoverlapping 10-, 30-, and 60-second production reconstructions
against independent counts spanning the *same* electrical edges. Actual oscillator
movement and physical PPS jitter are common to both measurements and cancel in
this acquisition difference; both methods' count/edge brackets remain. Windows
crossing a load transition are retained and labeled separately. Independent
10/30/60/300-second frequency intervals retain the explicit conditional 10 us
per-PPS allowance. The report omits position; the original private transcript
can contain a position-bearing GPS status record.

## External known-ratio inputs

The later external-input diagnostic is selected explicitly with:

```sh
cmake -S tests/hardware/si5351-reference-truth -B build/si5351-known-ratio \
  -G Ninja -DPICO_NO_FLASH=1 -DCMAKE_BUILD_TYPE=Release \
  -DTRUTH_PRODUCTION_CAPTURE=ON -DTRUTH_EXTERNAL_REFERENCE=ON \
  -DTRUTH_INPUT_GP=9 -DTRUTH_PPS_GP=11
```

GP9 (physical pin 12) receives the known 1 MHz clock; GP11 (physical pin 15)
receives PPS from the same source, with common ground and verified input levels.
Original Si5351 CLK2-to-GP7 and QLG3 PPS-to-GP3 leads can remain connected.
The external variant performs no Si5351 I2C setup or writes. QLG3 serial on
GP1 remains available for consecutive UTC labels; this test does not qualify
association of the substituted PPS for normal UTC operation. A zero independent
PPS allowance applies only to the known clock-to-PPS ratio of the common source,
not to absolute UTC accuracy. Only one input pair is selected per build.
Disconnect the GPIO leads before changing the reference outputs to RF test
frequencies. This mode is test equipment, not an ordinary firmware upgrade.

Select retained pinned picotool source explicitly when configuring either build;
the SDK's default tool discovery must not substitute another revision. Check every
UF2 payload address lies in RP2350 SRAM before loading, retain and verify the
current installed-image bundle and complete same-board flash backup, and follow
the preserving RAM-test/restoration transaction above. A successful host test or
cross-build does not qualify either physical input arrangement.
