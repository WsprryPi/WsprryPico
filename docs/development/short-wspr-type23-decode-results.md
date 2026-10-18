# Conducted WSPR Type 2/3 decode scope

The demonstrated pair is `PJ4/AA0NT`, `EM18IG`, 20 dBm at **3.570100 MHz** on
Pico A: USB `0BF4B4AEC9FFB344`, WTP `fd6127d11d6aca42a9905fa3fb1bf1d5`.
The normal `WsprryPico` image uses GP2 PIO/DMA, 138 MHz and 4 mA drive, from
source `14698ca1dba32914959530a3b5a0cf41f74caf8f`, build identity
`14698ca1dba3-dirty`, UF2 SHA-256
`6cbe319e996b4a935dc7ba311583832e68228177cb2b7434573776ab19284528`.
The build identity's dirty suffix comes from enclosing documentation changes;
its archived compilation inputs match that source. This is not an assertion
about currently installed firmware or a CI-produced image.

The conducted path is GP2/GND, 20 dB attenuation, combiner and 40 dB attenuation
into wspr5 RSP1B `2404058C60`, without an antenna, amplifier, filter or enabled
GPSDO output. Capture settings are CF32, channel 0, 250000 sample/s, 200000 Hz
bandwidth, 3545100 Hz tuning, 20 dB gain, AGC/bias tee off.

| Frame | Independent expected-message decode |
| --- | --- |
| Type 2 | `PJ4/AA0NT 20` |
| Type 3 | `<PJ4/AA0NT> EM18IG 20`, full callsign resolved from the preceding Type 2 |

The independent decoder is Debian WSJT-X `wsjtx 2.7.0+repack-1` `wsprd`, SHA-256
`3e1f562239d86c2deb08b237cef9fcb8511d4dd7579fee33c969abb784465be3`.
It starts with an empty hash directory; Type 2 supplies context for Type 3.
Cold Type 3 still decodes its grid/power with an unresolved `<...>` callsign.
No known callsign, symbol or hash entry is injected. The
[offline decoder helper](../../scripts/decode_wspr_type23_pair.py) separates
frame matching, preserves that context ordering and rejects wrong identity,
missing halves, stale state and decoder failures.

Two complete local jobs use adjacent UTC windows. The 480-second capture has
120000000 complex samples and no reported overflow, timeout or clipping.
Receiver sample-axis durations are 110.593/110.592 seconds with a 120.024-second
onset separation. Without hardware timestamps these do not qualify calibrated
duration or launch timing. The workflow's original terminal-state checker
reports `FAILED` because it expects persistent `complete` after the scheduler
releases the second job. Independent completion assessment requires both
ordered running jobs, complete associated sample intervals and frame-2/2
terminal readback with no pending pair, owner, output, error or DMA fault.
That distinguishes controller-checker failure from the demonstrated decode.

Restoration preserves settings, disabled/STOP state and the consumed second-slot
watermark; it restores executable flash only and does not roll back operational
journals. These are bounded test dispositions, not current device observations.
The result qualifies only this board/image/frequency/payload/path. It establishes
no general compound-call/hash-collision guarantee, other-board/band/clock support,
calibrated power/frequency/timing or release qualification.
