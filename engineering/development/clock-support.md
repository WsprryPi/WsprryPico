# RF clock and frequency limits

`WSPRRY_PICO_RF_SAMPLE_RATE_HZ` selects one image clock. StandaloneRF applies it
once at boot using `set_sys_clock_khz`; the PIO adapter requires that clock.
There is no automatic per-band selection or runtime clock-switch operation.
Changing the clock requires a separately built image and reflash. Never change
the clock inside an active job.

| Image sample clock | Native direct engine range, inclusive | 4 m at 70.0925 MHz | Native 2 m |
| --- | --- | --- | --- |
| 132 MHz | 100,000–65,999,999 Hz | Unavailable | Unavailable |
| **138 MHz, normal** | **100,000–68,999,999 Hz** | **Unavailable** | **Unavailable** |
| 150 MHz | 100,000–74,999,999 Hz | Representable; Unqualified | Unavailable |

These are arithmetic/admission limits, not band qualification. Every requested
and adjusted RF-on state must satisfy the active image's limits and application
frequency policy. WTP CAPS and the browser API's `wtp` capabilities come from
that same `ServiceConfig`; the one policy wrapper admits all job sources.
The UI reads those capabilities and submits complete jobs through that authority.
Its frequency entry remains free text; authoritative LOAD admission enforces the
active limits. It does not implement clock selection or promise that an admitted
frequency is measured/qualified.
The `pico2-w` preset and ordinary firmware build select the normal RF-capable
`WsprryPico` application at 138 MHz. Explicit `WsprryPico-Inhibited` selects
the RF-free simulator; `WsprryPico-StandaloneRF` remains compatible. This target
selection does not qualify a new image or refresh conducted results.

The default-off experimental `allow_unqualified_frequency` flag is required
for the 8 m and 5 m correlation envelopes. Keep it explicit even if the exact
representative measured points pass: one point does not qualify 40–45 MHz or
54.000001–68 MHz as complete intervals. These tests need no
`allow_non_amateur_frequency` permission. Neither permission grants national
legal availability or extends native synthesis limits.

Measured 8 m/5 m and receiver-translation conditions are specified in
[band support](band-support.md). The unfiltered GP2 path establishes no LPF,
antenna operation, calibrated watts or absolute RF precision. An admitted
frequency is not evidence that it has been measured or qualified.
