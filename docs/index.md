# WsprryPico

WsprryPico turns a **Raspberry Pi Pico 2 W** into a standalone beacon or a
transmitter controlled by WsprryPi. It sends WSPR, QRSS, FSKCW, DFCW and finite
test tones. Complete jobs run on the Pico, so their timing does not depend on
continuous USB or Wi-Fi delivery.

For standalone use, start with [Prepare your Pico](start.md), then install
firmware, connect and save your station settings. Already configured? Go to
[Operate](operate.md).

For a WsprryPi-controlled output, start with
[Add a WsprryPico in the WsprryPi manual](https://wsprry-pi.readthedocs.io/en/devel/Install/pico.html).
It covers Pi connections, Fleet, host schedules and Pi-managed firmware updates.
This manual covers the Pico's own setup, browser controls, standalone operation,
output limits and recovery. [Use with WsprryPi](wsprrypi.md) explains the handoff.
Developers can find the architecture, protocols and implementation references in
the repository's [engineering guide](https://github.com/WsprryPi/WsprryPico/blob/devel/engineering/development/README.md).

The GPIO output needs suitable filtering and a suitable load before use on
air. Check [Output and band limits](reference/output.md) before choosing a
frequency, amplifier or antenna connection.

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
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/output
reference/time
reference/security
reference/credits
```
