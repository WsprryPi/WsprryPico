# RF clock and frequency limits

`WSPRRY_PICO_RF_SAMPLE_RATE_HZ` selects one image clock. The RF-capable application applies it once at boot using `set_sys_clock_khz`, and the PIO adapter requires that clock. Select a different clock by building and installing a different image.

| Image sample clock | Native direct engine range, inclusive | 4 m at 70.0925 MHz | Native 2 m |
| --- | --- | --- | --- |
| 132 MHz | 100,000–65,999,999 Hz | Unavailable | Unavailable |
| **138 MHz, normal** | **100,000–68,999,999 Hz** | **Unavailable** | **Unavailable** |
| 150 MHz | 100,000–74,999,999 Hz | Representable; Unqualified | Unavailable |

The native executor checks every nominal and adjusted RF-on frequency against the active engine's arithmetic limits and the application frequency policy. Frequency entry in the browser does not change the image clock. The `pico2-w` preset and ordinary firmware build select the normal RF-capable `WsprryPico` application at 138 MHz. `WsprryPico-Inhibited` selects the RF-free simulator, and `WsprryPico-StandaloneRF` remains a compatible explicit target. Conducted qualification applies only to the recorded conditions.

The default-off experimental `allow_unqualified_frequency` flag is required for the 8 m and 5 m correlation envelopes. Keep it explicit even if the exact representative measured points pass: one point does not qualify 40–45 MHz or 54.000001–68 MHz as complete intervals. These tests need no `allow_non_amateur_frequency` permission. Neither permission grants national legal availability or extends native synthesis limits.

Measured 8 m/5 m and receiver-translation conditions are specified in [band support](band-support.md). The unfiltered GP2 path establishes no LPF, antenna operation, calibrated watts, or absolute RF precision. An admitted frequency is not evidence that it has been measured or qualified.
