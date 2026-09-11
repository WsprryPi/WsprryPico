# Prepared F1 finite-mode resource case

F1 is NOT RUN. It accepts resource and contention behavior only. It does not
qualify per-band RF, filters, spectra or other clocks. The selected image is
clean `8fb3894253ef45adc3aad28f25a684168487490f`, physical PIO at 138 MHz,
divider 1, SRAM renderer, UF2 SHA-256
`75b26e3fa2fc74e517fbfe9cdbe8ee7b9c0e6eabfc13708827d48d978ea0ba9f`.
Pico A remains USB `0BF4B4AEC9FFB344`, WTP
`fd6127d11d6aca42a9905fa3fb1bf1d5`. The conducted 50-ohm, 60 dB, unfiltered
path and unchanged Pico B/GPSDO/installed service requirements remain in force.

After both reviewed A2 families and reviewed A3 on that same physical boot,
`phase11_5_a3.py --family F1` constructs exactly fifteen finite jobs: three each
of Tone, QRSS, FSKCW, DFCW and WSPR, in that order. Tone lasts ten seconds.
Keyed modes use the canonical ETE pattern with three-second dots. The carrier
is 135,500 Hz; FSKCW/DFCW use the declared 5 Hz lower offset, and WSPR uses
375/256 Hz spacing. WSPR encodes AA0NT EM18 37; the encoded power field is not
a measurement of output power. The exact total job duration is 622.776 seconds
and total RF-on duration is 532.776 seconds. Current CAPS must admit every mode,
profile, event count, duration and frequency before execution.

One normal-load interval lasts 1,500 seconds, with 1,560 seconds of independent
USB/host observation. All 1 Hz production STATUS, 0.2 Hz browser STATUS and
three-asset reloads every thirty seconds remain required. The lifecycle must
have at least 1,800 seconds remaining. A separately hashed helper/production
manifest and at-most-1,800-second supervisor are required; existing lifecycle
and host deadlines are not extended. The helper supplement must include the
pure `src/campaign/plan.py` and its package initializer. It does not run the
general band/clock campaign.

Each job uses CLAIM/LOAD/ARM/observed completion/RELEASE. Long jobs renew the
same owner's sixty-second lease with forty seconds remaining, using at most
sixty RENEW requests for the whole family. Each renewal must grant the exact
requested owner and duration. No retries, automatic aborts, fault clearing,
configuration writes or additional RF jobs are included. An unexpected failure
stops dependent work and preserves the state for authoritative reconciliation.

All fifteen jobs need independent Loaded, Armed, Running and Complete coverage,
including observed active output and final release. The final eight retained
records must match the final eight jobs; this bounded history does not replace
the complete fifteen-job observations. Hardware counter deltas must be exactly
163,947 DMA IRQs, fifteen launches, fifteen zero tails and 163,917 successor
links. Existing 138 MHz refill/service deadlines, stack guards, heap reserve and
allocation-failure checks remain unchanged. The entire actor lifecycle must
fit inside the measured nominal interval.

Adversarial preparation found that thirty renewals were insufficient before
execution; fifteen deterministic scenarios against the actual Pi browser
scheduler require up to forty-five. The frozen cap is sixty. With all normal
requests retained, the latest modeled final observation is 1,262 seconds,
inside N1500. Wrong host/clock/owner, altered emissions, incompatible CAPS,
shortened leases and missing/extra hardware counters are rejected by regression
tests. Both A3 and F1 scheduling models pass. The 55-test host suite passed;
affected tests passed again after the final admission changes. These checks
establish software behavior and feasibility only; F1 remains physically unrun.


The follow-up source review added actual-CAPS admission, exact granted lease
validation and explicit request-body limits. It also checked a renewal crossing
finite completion: the actor continues consuming the independent STATUS
snapshots while awaiting a browser permit and allows bounded time to observe
completion after a renewal. The RF duration, independent sampling deadlines and
nominal end remain unchanged. The full raw audit still requires every state for
every job. No remaining actionable issue was found in this bounded source review;
physical admission and execution are still required. The running A2 and staged
A3 supplements retain their earlier hashes and are not changed by F1 preparation.
