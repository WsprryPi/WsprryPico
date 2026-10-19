# NTP UTC servo and correction retention

Current disposition: [NTP work is closed](ntp-work-closeout.md). μChrony is
retained for UTC discipline and future GPS/PPS input; NTP-derived RF calibration
is rejected. The Pico-to-Pi GPIO pulse path is retired. Results below describe
their recorded images and evidence, not current operating instructions.

The normal `WsprryPico.uf2` includes bounded interim UTC steering and a separate
NTP-learning journal. Manual PPM remains in its existing configuration journal.
The strict NTP RF fit and independent physical RF gate remain unchanged.

The linked application now ends at `0x103ee000`. The independent 8 KiB learning
journal precedes the existing journals; their addresses are unchanged. CI binds
the permitted application boundary to the bundle's exact source revision. It
can inspect historical bundles using their historical boundary without claiming
that a downgrade preserves the new learning cache.

The UTC controller uses causal original observations, damped phase updates,
bounded rate steps and three consecutive requests in the same direction before
interim rate steering. A provisional rate carries a broad uncertainty covering
the supported raw oscillator range and its applied center. Original source
uncertainty, unapplied phase lag and existing aging remain charged. Statistical
stability does not establish UTC accuracy or RF qualification.

UTC and strictly qualified RF learning retain independent provenance. Cache
writes occur only while idle and unowned, outside provisioning, reset and
reboot, with a five-minute write interval and a meaningful change threshold.
A restored UTC rate is a frequency prior: fresh NTP must still establish UTC
and freshness. Historical RF learning has unknown current age and cannot
bypass the independent physical RF gate. Full operational reset clears learning;
provisioning reset preserves it.

Validation covers 13 affected host checks, 29 CI packaging cases, scoped
formatting and the normal target build with linked flash/resource checks.
Deterministic cases cover nonzero manual independence, separate UTC/RF learning,
transient RF learning during write cooldown, interrupted programming, bank
rotation, device/topology/version rejection and reset behavior.

The B-only restoration test passed on normal `0.0.0-ntp-retained-r4`, revision
`582b7221b785-dirty`, at 138 MHz with `pio-dma-gp2`. Its UF2 SHA-256 is
`80ce14d21b1db966acfc9c726cf0dc5d16dfb8fa742bcc4ca613f2858e7f2408`.
The [evidence manifest](ntp-retained-evidence.json) binds the exact source overlay,
build outputs, private originals, analysis and restart receipts.

B saved a real provisional rate of −121 ppb (−0.121 ppm), sequence 1, at its
tenth accepted sample, 586.944 seconds after boot. The warm restart restored it
before NTP, without restoring UTC/freshness. A new NTP sample then established
UTC with actual clock rate −121 ppb and provisional uncertainty 100121 ppb.

The operator subsequently removed B's USB power once. USB was absent for
15.599 seconds; the operator confirmed the action, B acquired a new boot ID,
and the saved rate/sequence were restored before NTP. Its first fresh NTP sample
again applied −121 ppb. Three post-cold samples remained synchronized with no
rejected queries or resource faults. Saved Bohica credentials, `time.local`,
manual `0.000`/manual mode and 4 mA drive were unchanged. A retained its original
boot and remained unowned through these checks.

The first runtime-pause attempt used a console command refused by the consumer
profile before mutation. Its evidence is retained. The supported USB network
API then paused Wi-Fi in RAM before each restart, freezing the exact old-boot
query count without changing saved settings. Startup reconnected normally.
The POWMAN POR bit remained set after both warm and cold starts, so the bit
alone does not distinguish them.

The original finite experiment ended after 6864.84 seconds and a conservative
126 total queries, within its 7200-second/128-query limits. A frozen collection
plan inherited an obsolete image hash; a hashed erratum binds that unchanged
input to the actual load receipt and target hash. The initial 18-query proposal
and active 19-query allowance were both respected: the new image consumed
17 queries across acquisition, warm restart and cold stability checks.

Twelve original observations supplied eleven causal next-sample comparisons,
with complete recorded originals and matching actual-clock API bindings.
Damping reduced total phase movement from 30.034 ms to 13.463 ms. Median
next-sample residual was 6.194 ms, compared with 11.950 ms for free running and
0.415 ms for immediate phase refresh. Thus this short run shows less movement
and more lag; it does not establish a general accuracy improvement. The two
nonzero-rate holdouts improved the same damped phase projection by only
7.745 µs and 14.658 µs. All predictions remained inside their full uncertainty
bounds. These are comparisons against later NTP estimates, not independent
UTC truth.

No RF jobs were started. A qualified RF value was unavailable for a live
cold-boot RF-restoration claim; deterministic RF storage tests remain separate
evidence, and independent physical RF acceptance remains unqualified. The user then
authorized the [overnight A-pool/B-local comparison](ntp-overnight-results.md),
including the subsequent A firmware load and changed time server.
