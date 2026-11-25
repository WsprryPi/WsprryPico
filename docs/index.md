# WsprryPico

WsprryPico turns a **Raspberry Pi Pico 2 W** into a radio beacon. The Pico runs its own saved schedules. You can manage its settings and schedules in the Pico's browser controls or from **WsprryPi** on a Raspberry Pi.

A **job** is one complete, finite transmission, including any message repeats and gaps. A **schedule** starts WSPR or Morse jobs automatically at selected times. The Pico runs and times accepted jobs locally.

| Transmission | What it sends |
| --- | --- |
| WSPR, Weak Signal Propagation Reporter | A digital beacon message containing station information for WSPR decoding software |
| QRSS | Slow Morse code, with the radio signal switched on for dots and dashes |
| FSKCW | Slow Morse code, with the signal shifted to a lower frequency between dots and dashes |
| DFCW | Slow Morse code, using different frequencies for dots and dashes of equal length |
| Finite test tone | A steady signal for a specified duration, requested by an [authenticated measurement client](operate.md#conducted-test-tones-from-a-local-client) |

For a first standalone setup, follow these pages in order:

1. [Prepare your Pico](start.md): choose the board, RF connections, and any optional LED or button.
2. [Install firmware](install.md): load the Pico's operating program over USB.
3. [Connect](connect.md): join the setup Wi-Fi, save your home network, and open the control page.
4. [Configure your station](configure.md): enter station details and a transmit frequency, then review the schedule.
5. [Your first WSPR transmission](operate.md#your-first-wspr-transmission): save and apply the schedule, observe its first transmission, and turn it off after the trial. Use [Operate](operate.md) to set up a Morse schedule.

Already configured? Go to [Operate](operate.md). This manual follows development firmware. For an exact published image and its qualification scope, see the [release notes](reference/releases.md).

To manage the Pico from a Raspberry Pi, see [Use with WsprryPi](wsprrypi.md) for Fleet settings, device-owned schedules, and USB maintenance.

**RF** means radio-frequency output. WsprryPico generates it through a **GPIO** (general-purpose input/output) pin or a supported **Si5351** board. Use suitable filtering and a suitable load. Check [Output and band limits](reference/output.md) before choosing a frequency, amplifier, or antenna connection.

```{toctree}
:maxdepth: 2
:caption: Start here

start
install
connect
```

```{toctree}
:maxdepth: 2
:caption: Use your Pico

configure
operate
wsprrypi
maintain
troubleshoot
support
usb
udp
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/releases
reference/output
reference/time
reference/defaults
reference/pico-validation-platform
reference/security
reference/credits
```
