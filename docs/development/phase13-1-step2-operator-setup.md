# Step 2: LED operator setup is complete

Updated 2026-10-08. The operator connected one external LED to Pico B's GP15
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
- Actual GPIO readback and automated SDR collection completed the final test.

No additional operator action is pending for LED functional testing. The
previous second LED, active-low lamp wiring, bias resistors, A-to-B stimulus
wire, camera, optical recording and timed button instructions are superseded
for this selected scope. Do not request them again as LED prerequisites.

The operator's confirmation qualifies this lamp's GP15 wiring/illumination.
The later [automatic step-4 check](phase13-1-step4-review.md) passed external
TX-only routing versus onboard AP/Identify, with verified restoration and review.
Existing timing/shutdown evidence and software polarity coverage is reused;
another active-low target campaign is not required. The
[fixed TODO](phase13-1-closeout-steps.md) is complete in the selected LED scope.
The proposed new local GP14 stimulus is withdrawn from LED closeout. Existing
button operation is recorded in the [Phase 12 closeout](phase12-closure-matrix.md);
no additional button/header test or LED calibration is required for P13.1.

The earlier [preparation/review record](phase13-1-step2-review.md) and prompts
remain historical evidence, not current setup requirements. The fixed steps
1–6 are complete; no further LED work or operator setup is pending.
