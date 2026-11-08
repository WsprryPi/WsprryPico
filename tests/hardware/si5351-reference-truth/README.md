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
The linker reserves separate 16 KiB core-0 and 8 KiB core-1 stacks in main SRAM,
with the heap ending below both stacks. The counter is continuous for 301 edges; this diagnostic does not reproduce
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
bindings, UART/capture loss during the defined capture, and failed register
restoration. Core launch and a three-second UART settling interval precede the
health baseline; startup counters remain visible and no counter is reset. A
nonzero error increment during capture refuses acceptance. Production count
snapshots may legitimately refuse a concurrent publication. Those observations
remain in the report; windows with incoherent endpoints are marked unavailable
rather than fabricating counts or shifting the window. PPS sequence/UTC
continuity and coherent count-session identity remain mandatory.
It compares nonoverlapping 10-, 30-, and 60-second production reconstructions
against independent counts spanning the *same* electrical edges. Both measurements span the same observed PPS interval, so their interval-count
difference needs no receiver-to-UTC allowance. Both count/edge brackets remain.
Rapid source changes within the post-edge read delay and errors common to the
shared hardware counter are not independently resolved. Reported timestamp
differences are relative to GPIO polling brackets, not calibrated pad-edge latency. Windows
crossing or touching a load transition are retained and labeled separately. Independent
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
association of the substituted PPS for normal UTC operation. The GPSDO provides a known nominal clock-to-PPS ratio; using the same enclosure
does not establish zero relative jitter or phase coherence. Independent frequency
intervals retain the conditional 10 us PPS endpoint allowance for this source too.
The same-interval reconstruction comparison does not require
zero receiver-to-UTC jitter. This does not certify absolute UTC or source accuracy. Only one input pair is selected per build.
Disconnect the GPIO leads before changing the reference outputs to RF test
frequencies. This mode is test equipment, not an ordinary firmware upgrade.

Select retained pinned picotool source explicitly when configuring either build;
the SDK's default tool discovery must not substitute another revision. Check every
UF2 payload address lies in RP2350 SRAM before loading, retain and verify the
current installed-image bundle and complete same-board flash backup, and follow
the preserving RAM-test/restoration transaction above. A successful host test or
cross-build does not qualify either physical input arrangement.


For the later GPIO connection, power the Pico off and disable the GPSDO clock
and PPS outputs before attaching leads. Connect OUT2 to GP9 (physical pin 12),
OUT1 PPS to GP11 (physical pin 15), and common ground, for example physical pin
13. Keep the outputs disabled until the source configuration and compatible
input levels have been verified and the selected RAM diagnostic reports
`input_only=1`. OUT2 must provide 1 MHz and OUT1 must provide PPS. Existing
GP7/GP3 leads remain in place. The current installed image and exact recovery
bundle must be checked again before that session. The existing-wiring private
controller is bound to GP7/GP3 and its recorded original image; it must not be
reused unchanged for the external-input transaction. Disable the external
outputs before returning to the ordinary image, and disconnect the GPIO leads
before restoring any RF-frequency output configuration.

### Digital connection check

Before either external-reference capture, `CHECK` observes GP8 through GP13
for 2.2 seconds. All six pads are forced input-only with weak pulldowns during
the check; no test pin drives a signal. Function selection changes preserve
the forced input override. A hardware PWM counter counts GP9 rising edges;
the separate GPIO polling scan locates activity on neighbouring pins. GPIO
polling does not measure a fast signal's frequency. Missing or incoherent
signals stop the session before a long capture. This verifies digital routing,
not independent ground-lead continuity, voltage, ringing, or source metrology.

Isolated output tests are useful only after establishing the equipment's actual
gating. The `rf_analysis.wiring.analyze_wiring` isolated phases require the
inactive input and neighbouring pins to stay quiet. Do not infer physical output
state from configuration readback alone.

On LBE-1421 serial `0673ED0FA107`, firmware 1.9, requests through the retained
control utility behave as follows: the reported OUT2-only enable produces no
signal on either connected input, while the reported OUT1-only enable produces
both programmed frequencies. This was established with distinguishable 5 Hz
OUT1 and 10 Hz OUT2 signals and direct GPIO polling; both-enable also produces
both signals. This observation is specific to the tested unit, firmware, and
utility; it does not establish a general firmware defect or independent gates.

For this unit, explicitly request both frequency-enable bits and PPS mode.
Physical OUT1 must then carry PPS and physical OUT2 must carry 1 MHz. Require
an all-off check, a combined check, and another all-off check before capture.
The combined check requires GP9 hardware count divided by the measured 2.2 s
interval to fall between 995,000 and 1,005,000 Hz, GP11 to contain two or three
rising edges and one to three falling edges, and GP8/GP10/GP12/GP13 to remain
quiet. Both all-off checks require zero hardware edges and zero GPIO transitions.
Retain the commanded settings, raw counts, input-only readback, polling gaps,
and observed pin bindings together. This routing guard is not a frequency
accuracy qualification. PPS mode must be established physically because its
software flag alone does not prove that it overrides the OUT1 frequency.

Keep GPSDO frequency enables and PPS disabled before loading/restoring the
ordinary image. With GPIO leads still attached, leave the GPSDO disabled;
restore the original RF output configuration only after lead removal.

### Pairing continuity diagnostics

Production-capture mode records the existing internal GPS status at most ten
times per second into a fixed 3,200-record buffer. The 64-byte records retain
candidate UTC, original serial/PPS timestamps, observation and error counters,
validity flags, and the current pairing error. They contain no coordinates or
locator. This uses the unchanged production adapter and pairing policy; no
production resource or callback is added. Buffer exhaustion, an unexpected
status shape, or trace sampling gaps above 250 ms refuse qualification. The
maximum status decoding time is reported to account for this additional workload.
The trace's interval must cover the complete independent PPS capture.

On external-input builds, the existing QLG3 PPS on GP3 is also observed through
input-only GPIO polling. Its raw brackets permit comparison of the two receivers'
PPS phase and the RMC arrival windows without changing wiring or assuming their
relative phase. These auxiliary observations do not supply UTC labels or replace
missing production observations.

Inspect a refused capture without accepting it:

```sh
python3 tests/hardware/si5351-reference-truth/analyze_production.py \
  --pairing-diagnostics private/transcript.txt
```

This command reports state changes and observation stalls with
`qualification=not_evaluated`. The normal analysis command still requires the
original complete observation continuity and all other capture gates. A single
out-of-window RMC can cause two missing observations: its own label is refused,
and the following valid label only reacquires pairing. A host reproducer covers
that behavior; a diagnostic trace is needed to attribute an actual bench gap.

The current fixture uses a 600–1,250 ms RMC arrival profile for the tested QLG3
serial stream. The instrumented target trace measured refused labels at
1,200.39 and 1,206.912 ms under the previous 1,200 ms ceiling, followed by
pairing acquisition. Simultaneously polled QLG3/GPSDO PPS brackets agreed
within 15 us; UART/capture error counters stayed zero. The 650 ms window still
selects at most one one-second PPS edge, and the entire endpoint uncertainty
must fit inside it. Labels beyond that profile remain refused. Previous
captures retain their refusal; only fresh captures use the measured profile.
This bench setting does not change production defaults, persisted settings,
measurement allowances, or RF qualification criteria.
