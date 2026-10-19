# WsprryPico

WsprryPico transmits WSPR, QRSS, FSKCW and DFCW on a Raspberry Pi Pico 2 W.
It operates as a standalone transmitter or as a WsprryPi transmitter backend.
It also provides finite test tones. Each complete job runs locally on the Pico;
its timing does not depend on a continuous USB or Wi-Fi connection.

Standalone WSPR schedules retain station details, frequencies and settings
across power cycles. WSPR planning selects Type 1, Type 2 or Type 3 from the
callsign and locator; supported compound calls with a six-character locator
use an adjacent-window Type 2/3 pair. QRSS, FSKCW and DFCW messages accept up
to 32 characters, including spaces. Jobs are bounded by 60 minutes and 512
events, so some message, speed and repeat combinations exceed those limits.

## Connect and configure

A Pico without saved Wi-Fi starts temporary setup Wi-Fi. Join that network
and open `http://192.168.4.1/`. Save the Wi-Fi connection, then return to your
normal network and open the Pico's reported `.local` hostname or current IP
address. The setup network closes after ten minutes; USB remains available.

On the normal network, sign in with the Wi-Fi password saved on the Pico.
**Station/Transmission** contains station details, schedules, output pins and
job controls. **Wi-Fi/Host** contains network settings, the time server,
hostname and restart controls. The page identifies the Pico by its active
hostname; **About this Pico / Diagnostics** also shows its full stable device
ID. Use that ID to distinguish devices with the same name.

Set and save a transmit frequency before enabling a schedule. Generic firmware
images select no transmit frequency. Saved schedules without one remain
nontransmitting until a frequency is selected and they are deliberately enabled.
UTC comes from a network time server or a connected controller. A job that
requires UTC refuses to start when the clock is insufficiently reliable.

USB provides local configuration, time and WsprryPi job control without Wi-Fi.
Saved settings survive supported upgrades. Changed output pins or drive require
an explicit restart before transmission. If a save reply is lost, reconnect,
check the saved result and review it before saving again.

USB firmware updates use a verified CI image and retain saved settings. Older
firmware may request a one-time BOOTSEL reconnect: follow the installer prompt,
reconnect to the same USB port and continue the prepared update. Its saved
standalone schedule must be disabled or unconfigured first. Keep USB connected
during programming and verification.

The factory button connects **GP14 (physical pin 19) to GND**:

- Release in under 0.4 seconds to request a reset.
- Hold for 0.9 seconds to request transmission shutdown. Releasing between
  0.4 and 0.9 seconds also requests shutdown.
- Hold for nine seconds to request setup Wi-Fi after shutdown is confirmed.

A saved custom or disabled button assignment takes precedence. Every setup
Wi-Fi activation has a ten-minute limit; holding the button or keeping a page
open does not extend it. An unavailable saved network requests fallback setup
Wi-Fi after 60 seconds. A new deliberate request can open another window.

## Output and operating limits

The normal firmware uses the Pico's direct GPIO output at a fixed 138 MHz
system clock. Its native frequency range is 100 kHz through 68,999,999 Hz;
admission alone does not establish RF quality across that range. Direct 2 m
output is unavailable. A separate 150 MHz build can represent 4 m, but 4 m
does not meet the required reliable-WSPR support criterion. The 8 m and 5 m
experimental ranges require an explicit opt-in; tested points do not establish
coverage of the entire ranges.

The GPIO output is unfiltered. Choose suitable output filtering, attenuation
and any amplifier for the frequency and load. Conducted bench results do not
establish antenna-ready emissions, calibrated RF power or general band/mode
qualification. Reported WSPR dBm is message content, not measured output power.
The selectable 2/4/8/12 mA GPIO drive defaults to 4 mA and is independent of that
reported power. Optional amplifier enable covers each finite job and returns
inactive when output stops. LPF control and an external Si5351 engine are
unavailable.

Network time synchronization and RF frequency correction are separate.
Manual PPM correction is retained; automatic NTP-derived RF calibration is
not qualified. The explicitly selected `WsprryPico-Inhibited` firmware simulates
jobs without generating RF.

Consumer web pages use HTTP with password-authenticated encrypted application
traffic. HTTP page delivery is unauthenticated: a substituted page can steal
an entered password. Plain LAN WTP on TCP port 31417 admits clients that can
reach that port after the Pico has station connectivity and accepted network
time. Use a trusted network. Engineering certificate authentication is a
separate profile. USB control relies on physical access.

## Development and contribution

- [Project contract](CONTRACT.md)
- [Architecture](docs/architecture.md)
- [Development guide](docs/development/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

The defined hardware target is **Pico 2 W / RP2350**. Other Pico boards are not
supported. Original contributions use the [MIT License](LICENSE.md).
