# WsprryPico

WsprryPico turns a **Raspberry Pi Pico 2 W** into a radio beacon. It can run **standalone**, using settings and schedules saved on the Pico, or accept transmissions from **WsprryPi**, a controller running on a Raspberry Pi.

A **job** is one complete, finite transmission, including any message repeats and gaps. A **schedule** starts WSPR jobs automatically at selected times. The Pico runs accepted jobs locally, so their timing does not depend on continuous USB or Wi-Fi delivery.

| Transmission | What it sends |
| --- | --- |
| WSPR, Weak Signal Propagation Reporter | A digital beacon message containing station information for WSPR decoding software |
| QRSS | Slow Morse code, with the radio signal switched on for dots and dashes |
| FSKCW | Slow Morse code, with the signal shifted to a lower frequency between dots and dashes |
| DFCW | Slow Morse code, using different frequencies for dots and dashes of equal length |
| Finite test tone | A steady signal for a specified duration, submitted by a controller or a prepared job file |

For a first standalone setup, follow these pages in order:

1. [Prepare your Pico](start.md): choose the board, RF connections and any optional LED or button.
2. [Install firmware](install.md): load the Pico's operating program over USB.
3. [Connect](connect.md): join setup Wi-Fi, save your home network and open the control page.
4. [Configure your station](configure.md): enter station details and a transmit frequency, then review the schedule.
5. [Your first WSPR transmission](operate.md#your-first-wspr-transmission): save and apply the schedule, observe its first transmission and disable it after the trial. Use [Operate](operate.md) for individual message jobs.

Already configured? Go to [Operate](operate.md).

For a WsprryPi-controlled output, start with [Add a WsprryPico in the WsprryPi manual](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html). It covers Pi connections, the **Fleet** list of transmitters, schedules run by the Pi and Pi-managed firmware updates. This manual covers the Pico's own setup, browser controls, standalone operation, output limits and recovery. [Use with WsprryPi](wsprrypi.md) explains the handoff. Developers can find the architecture, protocols and implementation references in the repository's [engineering guide](https://github.com/WsprryPi/WsprryPico/blob/devel/engineering/development/README.md).

**RF** means radio-frequency output. WsprryPico generates it on a **GPIO**, a general-purpose input/output pin. That output needs suitable filtering and a suitable load before use on air. Check [Output and band limits](reference/output.md) before choosing a frequency, amplifier or antenna connection.

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
usb
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/output
reference/time
reference/security
reference/credits
```
