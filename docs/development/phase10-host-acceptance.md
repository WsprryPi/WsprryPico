# WsprryPi host acceptance prerequisites

The standard `WsprryPico` and explicit `WsprryPico-StandaloneRF` images provide
SNTP time and the same finite host-job capability envelope. Host jobs share
ownership and the job service with autonomous schedules. USB never supplies
RF event timing. Bounded inhibited USB acceptance and host installation are
delivered; conducted acceptance of the repaired physical image remains open.
See the [joint target review](phase10-target-review.md) for exact evidence and
the remaining quiet-baseline and conducted RF gates.

## Image selection

| Image | Device UTC source | Host jobs | Output |
|---|---|---|---|
| `WsprryPico` | Configured Wi-Fi SNTP | Five-mode lifecycle simulation | Inhibited |
| `WsprryPico-StandaloneRF` | Configured Wi-Fi SNTP | Five-mode experimental PIO/DMA | GP2, explicit build only |
| `WsprryPico-RFWTP` | Diagnostic Console USB observations | Five-mode experimental PIO/DMA | GP2, explicit build only |
| `WsprryPico-RFBench` | Relative time only | Bench commands; no WTP endpoint | GP2, explicit build only |

Use the SNTP image pair for joint host acceptance. WsprryPi does not provision
Console time; the USB-time campaign image is not a drop-in independently
synchronized device.

Five-mode WTP profiles advertise `wspr`, `tone`, `qrss`, `fskcw` and `dfcw`,
162 events and 110.592 seconds maximum per complete job. Numeric frequency
bounds are 100 kHz through one Hz below half the selected 132/138/150 MHz sample
rate; 138 MHz remains the default. These are experimental input limits, not
qualified bands. Inspect CAPS for the actual running image.

The physical planner also requires representable event boundaries and at most
four distinct NCO increments. Frequency adjustment needs explicit job consent
and is acknowledged by LOAD. CW, indefinite Tone, excessive jobs and
unrepresentable physical plans are rejected. The host's continuous Test Tone
workflow is not a finite WTP test.

The inhibited simulator validates the protocol/profile bounds but does not
model NCO quantization, waveform representability, RF gating or physical launch
latency. Its `inhibited-standalone-simulator` identity differs from `pio-dma-gp2`.
Its success cannot qualify the physical engine. The standard image links neither
the physical stream engine nor the Pico RF driver. Its sample-clock setting
describes a simulated profile; it does not switch the hardware clock for RF.

Autonomous station configuration, 80 m WSPR jobs, schedule format, watermark and
expiry behavior are unchanged. Expanding host capabilities does not enable an
unconfigured device. Previously enabled schedules remain enabled: changing
firmware is not a method of disabling stored scheduling.

## Clock agreement

WsprryPi's `[WTP] Start Uncertainty ns` defaults to `1000000` (1 ms). A valid
Pico SNTP observation may exceed it. Neither side raises that budget silently.

For a separately authorized bounded functional-acceptance run, explicitly select
`500000000` (500 ms), the existing standalone admission/launch ceiling, and
retain GET_CLOCK snapshots and the requested budget. This is a proposed test
setting; this software change does not alter host configuration or device
storage. A tighter requirement needs corresponding clock evidence or a better
time source. Neither a 500 ms setting nor ARM success establishes calibrated
accuracy. The separate USB-time RFWTP image retains its 20 ms uncertainty policy.

SNTP requires usable UTC, normal leap state, source age at most 90 seconds and
uncertainty within device and request limits. Uncertainty grows using the
existing assumed 50,000 ppb drift bound. The launch guard checks it again: ARM
can succeed and later become MISSED_START. There is no late-start fallback.
Networking is deferred while armed/running. A complete WSPR job can outlast the
acquisition window without retiming its events; the next job needs an admissible
clock snapshot. Host Linux `adjtimex` readiness is a separate check. SNTP does
not calibrate RF frequency; the host WTP backend requires zero host PPM.

## Hardware-free interoperability

The optional test reads WsprryPi at the reviewed commit
`2819f0b8ccb05f12d7f978a4cee2cac830997bbf`. The verifier checks HEAD and client
files before configure/build. It neither changes the host's original Pico
provenance pin nor writes into WsprryPi. It compiles the actual client against
this checkout's endpoint, SNTP parser, UTC discipline, image profile and inhibited
engine through fragmented in-memory streams. No USB, network, application/service
or physical engine adapter is present.

With that sibling checkout, run from WsprryPico:

```sh
cmake -S . -B build/phase10-host -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_WSPRRYPI_SOURCE=/Users/lbussy/GitHub/WsprryPi
cmake --build build/phase10-host --parallel 4
ctest --test-dir build/phase10-host --output-on-failure
python3 scripts/validate_wtp_contract.py
```

Without an explicit source, the ordinary suite stays independent. A newer host
revision requires review and an explicit verifier-pin update. The WSPR fixture
is synthetic: it exercises 162 events and lifecycle, not encoding or decoding.

## Joint target procedure — not executed here

Physical USB, flashing, host installation/services and RF require authorization
for their exact scope. Use Linux for the production host USB adapter. macOS
software tests do not close Linux enumeration, permissions or deployment gates.

1. Bind host commit, executable/hash/build profile, Pico source/dirty-state
   manifest, ELF/UF2 hashes, SDK/toolchain, board/device/boot identity, engine,
   clock and USB function. Keep logs outside Git. Filenames and branch names
   alone are insufficient identity.
2. Obtain authority for any installation/service or firmware operation. Keep
   transmission disabled while configuring the endpoint. Record Linux path/by-id
   alias, exact serial including leading zeros, VID/PID and WTP CDC function.
   Console is not the WTP endpoint. Disable incompatible ancillary GPIO,
   amplifier, LED, band-selector and fade features through explicit configuration.
3. Under Console-provisioning authority, establish SNTP using the
   [standalone contract](standalone.md). Persist autonomous scheduling disabled;
   preserve unrelated station/network settings, watermark and schedule history.
   Volatile STOP alone does not disable scheduling after reboot. Verify actual
   image, scheduling state, ownership and inactive output before proceeding.
4. Start with standard inhibited firmware. Verify host clock readiness separately
   from HELLO/STATUS/CAPS/GET_CLOCK. Missing/stale status is unknown. Confirm the
   simulator identity, five modes, exact limits, no foreign owner and explicit
   uncertainty budget. Revealing host development controls is not job authority.
5. Authorize finite inhibited jobs through the real WsprryPi application/encoders.
   Exercise WSPR and keyed-mode scheduling within CAPS. Check strict clock
   rejection, then an explicitly selected admissible budget. Retain LOAD/ARM,
   returned clock mapping, job identity, terminal state and output inactivity.
6. Exercise loaded/armed/running cancellation, repeated jobs, reconnect, lost
   replies, clock loss and reboot within the inhibited scope. Require same-session
   authoritative reconciliation. Changed boot or foreign ownership must prevent
   automatic reload/rearm. Host restart does not adopt its earlier process-local
   session. USB removal does not prove cancellation on a physical RF image.
7. Resolve inhibited failures before proposing RF. Separately bind conducted
   frequency, mode/message, duration, repeat count, budget, firmware, GP2 route,
   attenuation/filter path, receiver and stop procedure. Select StandaloneRF only
   under that authority. Explicitly permit required frequency adjustment and the
   host's unqualified-frequency policy; neither grants qualification.
8. Require independent decoding or keyed-mode analysis, timing/RF criteria,
   leading/trailing quiet and confirmed shutdown. WTP completion is insufficient.
   If Pico/GPSDO share a combiner, verify reference-output state and source
   exclusion. Unknown output or cleanup failure blocks subsequent source activity.
9. Record failed/blocked/skipped cases and final verified device/output state.
   Any authorized restoration must identify actual firmware and stored scheduling
   state. Do not infer connectivity or present state from historical records.

Installation/service acceptance, host feature-branch merge, operator-manual
publication and general hardware/RF/reliability qualification remain distinct
gates. Networking, SoftAP/BLE, output-network design and release are later phases.
