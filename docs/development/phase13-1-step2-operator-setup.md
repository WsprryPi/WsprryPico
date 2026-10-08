# Step 2: LED operator setup is complete

Updated 2026-10-07. The operator connected one external LED to Pico B's GP15
and ground, then confirmed **“It's lit”** while a minimal GPIO15-HIGH sketch
ran on the exact B USB serial `CDDBF8767C506C07`. The sketch contained no RF
application; zero RF jobs were admitted. The source is
[the minimal GP15 sketch](../../tests/hardware/gp15-led/main.cpp).

B was then restored to ordinary inhibited firmware `f5ecdeb7cd54`, at 150 MHz,
with schedules disabled, no owner/job, inactive RF and stable settings identical
to the retained entry. Pico A was not flashed. Private wiring-check/restoration
evidence is under `/home/pi/phase13-led-stop-f5ecdeb/build/gp15-sketch-on/` on
`wspr5`.

## Current setup

- Keep the existing external LED circuit on B's GP15 and ground.
- Keep the existing GP2 conducted SDR path and button connections.
- Use actual GPIO readback and automated SDR collection for the remaining tests.

No additional operator action is pending for LED functional testing. The
previous second LED, active-low lamp wiring, bias resistors, A-to-B stimulus
wire, camera, optical recording and timed button instructions are superseded
for this selected scope. Do not request them again as LED prerequisites.

The operator's confirmation qualifies this lamp's GP15 wiring/illumination.
The remaining useful automatic check is external TX-only routing versus
onboard AP/Identify. Reuse existing timing/shutdown evidence and software
polarity coverage; another active-low target campaign is not required. The
[fixed TODO](phase13-1-closeout-steps.md) selects one existing external-high
case, followed by restoration and review. The proposed new local GP14 stimulus
is withdrawn from LED closeout. Physical button/header qualification is separate
and is not silently marked PASS.

The earlier [preparation/review record](phase13-1-step2-review.md) and prompts
remain historical evidence, not current setup requirements. All further work
follows the fixed steps 1–6 without timed operator responses or another onboard
visual check.
