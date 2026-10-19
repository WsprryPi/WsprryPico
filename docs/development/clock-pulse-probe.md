# USB clock pulse instrumentation

The normal `WsprryPico` firmware provides explicit USB Console commands that
bracket a physical GP22 edge with snapshots of the application UTC clock.
The instrumentation measures that clock; it does not synchronize it. NTP
selection, filtering, rate control, persisted corrections, manual PPM and RF
quality gates retain their existing behavior. No pulse is generated at boot.

## Connections

Use one dedicated 3.3 V signal and a common ground for each Pico. The Pi lines
receive the pulses and must remain inputs. The external button connection on
Pico GP14 is separate from this measurement connection.

| Board | Pico signal | wspr5 signal | Ground |
| --- | --- | --- | --- |
| A, USB `0BF4B4AEC9FFB344` | GP22, physical pin 29 | GPIO22, physical pin 15 | Pico GND to Pi GND |
| B, USB `CDDBF8767C506C07` | GP22, physical pin 29 | GPIO23, physical pin 16 | Pico GND to Pi GND |

Pico physical pin 28 is a ground next to GP22. GP14 is physical pin 19;
RUN is physical pin 30. Confirm the labeled pin identity before connecting.
Do not connect a measurement signal to RUN or BOOTSEL contacts.

On wspr5 the installed GPS HAT uses UART GPIO14/15 and PPS GPIO17, physical
pin 11. Its kernel PPS consumer and chrony service are independent of these
two measurement inputs. Both Pico time servers remain `pool.ntp.org`; host
PPS is used to assess measurement timestamps, never submitted to a Pico.

Pin references: [Pico 2 W datasheet](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf)
and [Raspberry Pi GPIO header](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio-and-the-40-pin-header).

## Console interface

Commands include the exact device ID and current boot ID returned by `INFO`:

```text
CLOCKPROBE <device-id> <boot-id> STATUS
CLOCKPROBE <device-id> <boot-id> READ
CLOCKPROBE <device-id> <boot-id> PULSE <sequence>
```

`STATUS` is read-only and returns the last cached record. `READ` temporarily
reads GP22 as an input, disables the Pico pulls and input buffer for a 20 ms
settling window with interrupts enabled, then briefly enables the input to
sample it. It returns the settling/sampling pad registers, mux, output-enable
state and raw read window. `PULSE` emits one nominal 1 ms pulse with a rising-edge
bracket, pad readbacks and pin-restoration result. The adapter restores the
original pad, mux, output latch and direction after either operation.

New pulses require an unowned, inactive device with schedules disabled,
healthy settings, no pending reset/setup/restart and GP22 free in both the
running and saved pin plans. The pin must already be unused or an input.
These metrology conditions do not change any transmit qualification rule.
An unsynchronized device can test wiring, but its record has `clock_valid`
false and cannot support a UTC measurement.

Sequences start at 1 and increase by one, with at most 4096 attempts per boot
and at least 500 ms between attempts. A failed attempt consumes its sequence.
Repeating the latest sequence returns the identical cached record without
another edge, including after an ambiguous USB reply. Wrong device/boot IDs,
skipped sequences and noncanonical integers are rejected before touching GPIO.
Only one record is retained; there is no streaming history or automatic timer.

Snapshots include UTC, raw monotonic time, model generation, current slew
rate and its end, subsequent rate, NTP generation/source cohort, pure
frequency estimate and its uncertainty. Rising-edge bounds account for the
raw timer's 1 microsecond resolution. `clock_valid` additionally requires
successful hardware checks, normal synchronized NTP time, no source
disagreement, an unchanged clock generation and an edge bracket at most
50 microseconds. This flag describes record consistency, not independent UTC
accuracy.

Raw timer reads tightly bracket the physical edge. UTC snapshots surround
that bracket, and exact integer projection binds the edge to their unchanged
model outside the GPIO critical section. A model generation/state/leap change
or an edge outside the surrounding snapshots invalidates its clock binding.
Projection handles a finite slew ending within the bracket, and uncertainty
uses the larger surrounding value. UTC-model computation time is not part of
the physical-edge bracket. The 50 microsecond gate and one-microsecond raw
timer allowance remain unchanged.

## Finite wiring check

`scripts/clock_pulse_probe.py` is an opt-in Linux hardware tool. It requires
installed libgpiod Python bindings, `pinctrl`, `chronyc` and access to the named
USB Console and GPIO lines. Inspect it before use. A new private output file
is required; the command times out after 60 seconds and defaults to three
pulses, with a maximum of sixteen.

After verifying the physical connections and loading the instrumented normal
image, select the actual device, revision and corresponding Pi input:

```sh
sudo python3 scripts/clock_pulse_probe.py \
  --console /dev/serial/by-id/usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00 \
  --serial 0BF4B4AEC9FFB344 \
  --device-id fd6127d11d6aca42a9905fa3fb1bf1d5 \
  --revision '<revision returned by INFO>' --line 22 --count 3 \
  --pulse-only \
  --output /private/evidence/A-clock-pulses.json
```

For B use USB serial `CDDBF8767C506C07`, device ID
`29f20b7342051ef947aa56cb9d4fab42`, and `--line 23`. Both input lines are
observed together so crossed connections and extra edges fail the check.
The tool uses canonical device locks and a shared input lock, verifies USB
parent/device/boot/firmware identity and requires pool NTP with schedules off.
With `--pulse-only`, an input-only preparation clears possible A2 leakage,
records any settling transitions, and requires an idle-low input before the
measurement begins. It then verifies the intended Pico-to-Pi path directly
from commanded output pulses. Without that option, it first alternates weak input
pulls and requires Pico GP22 to follow the selected Pi input. The Pi never
drives an output in either mode. Original input mux/pull state is restored after capture unless a
foreign owner or configuration change prevents safe restoration. Failures
retain partial Console and event evidence.

Each pulse must produce exactly one rising and one falling edge on the selected
input, no events on the other input, no event-sequence gaps and a width between
0.5 and 10 ms. Retrying the sequence must produce no additional edge. The
capture retains host chrony/PPS receipts before and after and both original
Pico clock brackets.

The RP2350 A2 [E9 input-leakage erratum](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=1359)
can defeat weak pull-downs while the Pico input buffer is enabled. The probe
therefore settles with input enable clear and enables it only briefly around
an input read, following the manufacturer's workaround. Pad state is retained
in `READ` diagnostics. Pulse readbacks use a strongly driven output. The
optional reverse-bias diagnostic is not a clock-source or RF quality gate;
actual output-edge validation remains required in both capture modes.

`clock_probe_context.InputAudit` adds read-only context to an already owned RP1
measurement request. It records both input levels, control/pad/status registers
and power flags before validating idle-low state and unchanged configuration.
It does not request GPIO, drive pins, clear power history or reconfigure the
kernel. Historical power flags are retained separately from current faults.
Power reads are sampled at most once every 30 seconds and do not certify the
absence of a short supply transient. Raw unexpected events still fail the
existing edge checks; the helper never filters or requalifies them. Keep the
shared power load and wiring steady during a finite measurement.

## Measurement limits

Linux GPIO timestamps use the host real-time clock and include input/interrupt
latency. Selected GPS PPS and fresh kernel PPS assertions establish reference
health, but do not independently bound the difference between PPS and GPIO
timestamp paths. The capture therefore leaves absolute timestamp delay
unqualified. Reference offset, clock steps, edge latency, cable delay and
clock-generation changes need explicit treatment before claiming actual UTC
error. USB request/reply timing is not used as the edge timestamp.

A raw-clock frequency fit and a causal comparison of the measured UTC model
with a model holding its initial frequency can distinguish phase damping
from incremental rate benefit. Such analysis needs a finite time series and
stable reference/capture behavior; a three-pulse wiring check establishes
neither convergence nor rate-correction benefit. UTC pulses do not measure
the RF carrier. RF error still requires the separately verified SDR/GPSDO
measurement path.

See the [Linux GPIO event timestamp documentation](https://docs.kernel.org/userspace-api/gpio/gpio-v2-line-event-read.html)
and [independent measurement methodology](microchrony-independent-measurement.md).

## Validation and bench state

Portable policy and event validation tests run without hardware:

```sh
cmake --build build/microchrony-pulse-20261018/host --target clock_probe_tests
ctest --test-dir build/microchrony-pulse-20261018/host \
  -R '^(clock_probe|clock_pulse_probe|microchrony|microchrony_clock_loop|independent_clock_measurement)$' \
  --output-on-failure
```

The normal Pico 2 W image cross-build passes its flash-layout, heap and stack
checks. Deterministic checks cover identity, busy/sequence/rate limits, failed
attempt replay, bounded records, invalid clock generations and physical-event
rejection. These checks do not establish physical pulse behavior.

Both boards passed the direct Pico-to-Pi output check on October 18, 2026.
The final settings checkpoint was 16:58:15 CDT. Both run the same normal
`0.0.0-devel` image, revision `0a7c05d1c41b-dirty`, UF2 SHA-256
`6a742656d26eb32e372bdced2d1130c7447e5b33c2e93523c65c8efe3fc273f0`,
with the `pio-dma-gp2` engine and nominal 138 MHz system clock. Each installed
application and full 4 MiB flash backup was verified, and the entire 72 KiB
reserved region matched its pre-load backup. Saved configuration, Wi-Fi and
manual `0.000` PPM in manual mode were preserved. Both boards finished
unowned/inactive with schedules disabled and fresh, synchronized
`pool.ntp.org` time. No RF job or GPS time submission was performed.

| Board | Instrumented boot ID | Accepted pool samples at final check | Selected NTP age |
| --- | --- | ---: | ---: |
| A | `957cac880f81a5fa8eee535e0fbb4bbe` | 23 | 17.839 s |
| B | `98e76a283e7778ae4bc23103905fd814` | 38 | 46.381 s |

| Board | Pi input | Qualified sequences | Pulse widths (ms) | Physical edge brackets (microseconds) |
| --- | --- | --- | --- | --- |
| A | GPIO22 | 1, 2, 3 | 1.079220, 1.080664, 1.081349 | 5, 5, 5 |
| B | GPIO23 | 4, 5, 6 | 1.082757, 1.080442, 1.076553 | 6, 5, 5 |

Every qualified pulse produced exactly one rising and one falling edge on its
intended Pi input, no edge on the other input, no event-sequence gap and a
valid unchanged UTC model binding. Duplicate requests returned identical
cached records with zero additional edges. A used clock generation 6 and B
generation 10. An earlier B sequence 1 preceded its first NTP synchronization;
its wiring result is retained, but its correctly false `clock_valid` excludes
it from UTC-bound evidence. The complete synchronized series above was
captured afterward.

Both Pi measurement lines were restored to their original kernel-unowned,
disabled/no-pull state (`no pn`). The GPS HAT's GPIO17 PPS consumer was
unchanged. The Pico adapter restored its original pin configuration after
each operation. All finite tests finished. These results verify physical
routing, record binding and replay behavior; they do not qualify absolute
UTC error, RF error or interim rate-correction benefit.

The initial host checker refused the USB topology before opening the Console:
an ancestor root hub also has a serial attribute. The checker now binds the
nearest USB device and still rejects an incorrect serial, vendor or product,
including when a farther ancestor happens to match. A deterministic regression
covers that topology. Earlier weak-pull checks were inconclusive; the A2
input-leakage handling above and input-only preparation precede the direct
output validation. An initial wider physical bracket was refused; tight raw
edge bracketing with surrounding model projection now meets the unchanged
50 microsecond gate. Failed topology, passive checks and pulse receipts are
retained. All five affected CTest entries pass. No NTP or RF quality gate was
changed.

Firmware, full flash backups and raw failure receipts remain private in
`build/microchrony-pulse-20261018/` and
`/home/pi/microchrony-pulse-20261018` on wspr5. The final original captures and
settings/restoration receipts are under `tight-edge/`, `tight-edge-A/` and
`final-pulse-validation/`. The Mac's `final-hardware-receipts/` copy was
checked against capture and backup hashes, including reserved-storage byte
comparisons. Earlier candidates and all failure receipts remain separate.
B's earlier BootROM presentation cleared after the user's physical reboot;
its cause was not established. Native IPv6 SSH reached the verified wspr5
host key while IPv4 stalled before the SSH banner; no service or SSH
configuration was changed.

The subsequent finite [independent pulse/RF comparison](microchrony-pulse-rate-comparison.md) records sustained measurements and separates frequency holdouts from phase slew.
The completed [Internet-source rerun](microchrony-pulse-rate-rerun.md) retains
clock loss/recovery and compares interim frequency treatments against measured
pulse UTC offsets, with separate physical RF checkpoints and explicit limits.
