# Independent clock measurements

NTP and optional qualified GPS/PPS observations discipline UTC. RF correction selects independent manual PPM or separate PPS-derived oscillator measurements with manual residual trim; see [GPS/PPS](gps-pps.md). A synchronized host or attached GPSDO alone does not calibrate the Pico or receiver. Absolute UTC phase remains unqualified by USB round trips because transport latency and asymmetry are not independently known.

## Frequency references and clock binding

Record the exact source/image hash, board and USB/WTP identities, RF engine, clock profile, mode, requested frequency, manual correction, and RF path. Verify reference model/serial, lock, output frequency/level, routing, and attenuation. A representative coherent IQ interval needs independently verified reference lines and complete receiver identity, sample settings, timestamps, overflow, clipping, and data hashes. Two simultaneous reference lines can resolve receiver frequency offset and sample-rate scale; a single offset subtraction cannot establish both. State fit windows, rejected lines, stability tests, and propagated reference/fit uncertainty. Engineering allowances are not calibrated uncertainty.

A measured carrier error represents raw-clock error only after proving the carrier's engine, divider arithmetic, manual correction, and common oscillator relationship. For raw error r and applied UTC mapping rate c (dimensionless fractional rates), corrected UTC rate error is (1+r)(1+c)-1. Propagate intervals through that relation rather than substituting statistical skew for measured r. Measure contemporaneously across startup, changes, source loss, and holdover; a favorable checkpoint does not establish a uniform improvement.

Physical UTC phase requires an independent timestamped reference and a bounded observation path. Source identification, UTC-second pairing, latency, common-clock binding, reference errors, disagreement, and loss/recovery determine whether an observation is usable. RF correction additionally requires independent conducted carrier qualification. See [UTC discipline](clock-discipline.md).
