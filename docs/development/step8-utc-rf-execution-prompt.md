# Step 8 UTC and RF job-service execution prompt

Work on `devel` without disturbing unrelated work. Read the repository contract,
architecture, development guide and WTP/1 contract before changing code.

Implement the next bounded Step 8 slice:

1. Add a portable UTC discipline that maps an externally observed UTC instant to
   the RP2350 monotonic clock. It must expose explicit uncertainty, aging and
   synchronized/holdover/unsynchronized states; reject stale, future, overflowing
   or internally inconsistent observations; and grow uncertainty conservatively
   with configured oscillator drift.
2. Add a Pico USB time-source adapter on the diagnostic CDC. Use a two-step
   exchange: return a Pico monotonic sample, then accept the host UTC estimate,
   uncertainty and leap state for that exact sample. Keep this source protocol
   separate from WTP/1 and document its trust and precision limits.
3. Add an explicitly selected `WsprryPico-RFWTP` firmware target that joins the
   disciplined clock, WTP job service, existing PIO/DMA sink and stream engine.
   Preserve the normal `WsprryPico` image as RF inhibited. The RF target must boot
   inactive, require valid WTP ownership/LOAD/ARM, honor the local launch guard,
   and stop safely on USB session loss or clock rejection.
4. Add a host client that performs the time exchange, frames strict WTP/1
   requests, loads an encoded Type 1 WSPR job, arms a future UTC start, observes
   terminal events and can request BOOTSEL only while output is inactive.
5. Add deterministic tests for clock boundaries, USB source parsing and client
   framing. Build the portable tests and all firmware targets. Run the contract
   validator and formatting/whitespace checks.
6. With the already authorized conducted GP2/GND path and wspr5 RSP1B setup,
   flash only the explicit RF WTP image, schedule one finite encoded WSPR frame,
   capture it on wspr5 and independently decode it. Record exact source, image
   digest, device, receiver, attenuation, requested and observed UTC timing, clock
   uncertainty, RF settings and teardown state. Leave RF inactive and the GPSDO
   output disabled.

Do not add autonomous transmission, frequency policy or operator rules. Do not
claim standalone UTC, GNSS/NTP support or production qualification from a USB
host-source validation.

After implementation, perform an adversarial review against the WTP state
machine, time arithmetic, session-loss behavior, RF inhibit boundary, parser
limits, test value and evidence claims. Repair every actionable finding and run
a second assessment. Commit only attributable files, push `devel`, and verify
HEAD, upstream and `origin/devel` are equal and the checkout is clean.
