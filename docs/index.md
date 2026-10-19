# WsprryPico

WsprryPico turns a **Raspberry Pi Pico 2 W** into a standalone beacon or a
transmitter controlled by WsprryPi. It sends WSPR, QRSS, FSKCW, DFCW and finite
test tones. Complete jobs run on the Pico, so their timing does not depend on
continuous USB or Wi-Fi delivery.

Start with [Prepare your Pico](start.md), then install firmware, connect and
save your station settings. Already configured? Go to [Operate](operate.md).

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
