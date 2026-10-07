# Step 2: one untimed physical setup

Status: **onboard visual subset passed; full fixture/recording setup pending**. This sheet executes the
[step-2 prompt](phase13-1-step2-prompt.md). Take as long as needed. No transmission
is left running while waiting, and no action requires catching a timed LED cue.

The operator subsequently reported that the external LEDs have not arrived and
selected [untimed onboard visual checks](phase13-1-step2-manual-onboard.md).
Both installed-firmware onboard LEDs were visually confirmed OFF; B was then
confirmed steadily ON while A stayed OFF, followed by both OFF. B's ordinary
inhibited firmware and saved settings have been restored and verified. These
checks accept only observed optical plateaus. The remaining wiring/recording
requirements below still apply to the full autonomous RF/LED matrix.

The proposed arrangement is **Pico B as the device under test (DUT), Pico A as
the automatic stop fixture**. Software identity and saved default pin plans have
been checked, and the operator's B-ON/A-OFF observation matches the board labels.
Existing attachments and the actual RF-path details still need confirmation.
Either board can be selected instead, but swap every
board role consistently before wiring or freezing the private setup record.

| Board | USB serial | Device ID | Proposed role |
| --- | --- | --- | --- |
| A | `0BF4B4AEC9FFB344` | `fd6127d11d6aca42a9905fa3fb1bf1d5` | Inhibited automatic stop fixture |
| B | `CDDBF8767C506C07` | `29f20b7342051ef947aa56cb9d4fab42` | DUT, onboard and two external LEDs |

Receiver: **RSP1B `2404058C60`**, attached to `wspr5`. Keep the existing GP2
conducted RF/attenuation/combiner connections in place. Record which coax/path
belongs to each physical Pico and the existing attenuation. There is no
rewiring of the RF path for this setup.

## Equipment and pin map

Proposed parts: two ordinary red LEDs, three 1 kΩ resistors, three 10 kΩ
resistors, jumper wires, breadboard, multimeter and a recording camera. LED
parts/direction, available resistor values and existing accessories remain to
be confirmed. A USB camera connected to `wspr5` fits the prepared collector;
other equipment must have its actual recording path verified first.

Use the top view with the USB connector at the top, matching the official
[Pico 2 W pinout](https://datasheets.raspberrypi.com/picow/pico-2-w-pinout.pdf).
GPIO labels and physical header numbers are different:

| Signal | Physical header pin |
| --- | --- |
| GP2 RF, preserve existing connection | 4 |
| Ground used by this sheet | 18 |
| GP14 stop input on B | 19 |
| GP15 active-high LED on B / stimulus output on A | 20 |
| GP16 active-low LED on B | 21 |
| 3V3(OUT) on B | 36 |

The board GPIO supply is 3.3 V; the external fixtures use B's 3V3(OUT).
See the official [Pico 2 W datasheet, sections 2.1 and 3.2](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf).
With a typical red LED near 2 V, 1 kΩ gives about 1.3 mA. This is an estimated
fixture current, not an LED-part qualification.

## Prepare the connections together

First confirm that B's GP14/GP15/GP16 and A's GP15 have no conflicting accessory
connections. The full-flash journals showed canonical default pin plans, but
software cannot inspect attached wires. Remove power from both Picos while
building or changing connections. Keep the RF coax in its existing arrangement.

| Connection | Wiring |
| --- | --- |
| Active-high external LED H | B GP15 (pin 20) → 1 kΩ → LED anode (+); LED cathode (−) → B ground (pin 18). |
| H inactive bias | 10 kΩ between B GP15 and B ground. |
| Active-low external LED L | B 3V3(OUT) (pin 36) → 1 kΩ → LED anode (+); LED cathode (−) → B GP16 (pin 21). |
| L inactive bias | 10 kΩ between B GP16 and B 3V3(OUT). |
| Common logic ground | A ground (pin 18) ↔ B ground (pin 18). |
| Automatic stop signal | A GP15 (pin 20) → 1 kΩ series resistor → B GP14 (pin 19). |
| Stop released bias | 10 kΩ between B GP14 and B 3V3(OUT). |

The biases keep the unused LED pins inactive and hold the stop input released
while the fixture GPIO is an input. The series stop resistor limits contention;
its actual released/low levels must still be checked on the assembled setup.
Only the inhibited stimulus image may drive A GP15 in this arrangement. It
drives low for **1.2 seconds** and releases to input automatically. A 250 ms
pulse is a reset gesture and is not the prepared stop test. Keep both Picos
powered during autonomous tests; a missing/disconnected fixture is a stop and
readiness failure, not a successful stimulus.

If the LEDs need a basic polarity/brightness check, do that with their GPIO
leads disconnected, using the same 1 kΩ resistor between B's 3V3(OUT), LED and
ground. Then remove power and finish the final wiring above. This passive bench
check is neither firmware TX behavior nor RF/LED acceptance.

Restore power after checking the wiring. The released B GP14 level should be
near B's 3.3 V supply; report the actual stable meter reading. Codex will run any
finite inhibited stimulus check after transport/image/authority checks. Do not
try to time a button press or meter probe to the automatic pulse. Independent
scope/logic capture is needed to measure its low level/duration/release; a USB
acknowledgment alone cannot establish those electrical assertions.

## Recording setup

Place a real capture camera so B's onboard LED and both external LED bodies are
separately visible, sharply focused and unobstructed. Keep A's LED outside those
three measurement regions. Secure the camera and fixtures so the regions will
remain aligned while firmware is changed. Record camera identity, supported
mode and stable device/USB location. `wspr5` currently exposes only Pi processing
nodes; these are not a connected optical camera.

The initial recording proposal is 640×480 at 30 fps with declared 8-bit FFV1
output; actual camera support remains to be checked. Codex reserves the full
matrix's video/IQ/readback storage before device changes. Its clean source
checkout and private `build/` output must use persistent disk: the 2 GiB `/tmp`
inventory staging location cannot retain the full suite. This is automated
preparation, not another operator action.

Codex will inspect the actual capture modes, make a short recording, retain a
sample frame/video for review and select the three actual regions. Verify the
LEDs can be distinguished in both dark and illuminated conditions without
clipping/saturation or automatic exposure changes that obscure transitions.
All checks are finite and can be replayed afterwards; the operator may leave
while they run and respond later.

For exact RF/LED launch and shutdown ordering, prepare independent optical/RF
measurement and synchronization during this same session if that equipment is
available. Ordinary 30–120 fps video provides frame-resolution observations;
it cannot prove microsecond edge ordering. Record unavailable measurement as an
open qualification item, rather than silently accepting a timing exclusion or
requiring a surprise operator visit in step 6.

## What to confirm to finish this session

- The unchanged conducted path/attenuation and any existing accessory
  connections on the four GPIOs used here; A/B labels were matched by the
  onboard visual check.
- Actual LEDs/resistor values, both final LED circuits, common ground, stop
  connection and stable released GP14 voltage.
- Connected recording equipment and its view of the three DUT LEDs; available
  scope/logic/optical timing equipment and any limits on its unattended capture.

Codex then verifies recording, electrical evidence available from the prepared
instruments, and both devices' return to an inactive state. The private setup
packet remains non-runnable until the real inputs are confirmed. Any missing
equipment, unknown continuity, unverified pulse/release, unusable recording or
unresolved timing scope stays explicitly pending. Fresh device time and WTP
ownership are automatic preflight requirements, not timed operator actions.
Steps 3–6 are not executed as part of this setup session.
