# μChrony control-fixes hardware rerun

The normal firmware was loaded and verified on both Picos. The new bounded
pool.ntp.org run stopped on a GPIO measurement fault before it could establish
convergence or an overall UTC/RF improvement. All gates and saved manual PPM
remained unchanged. This adverse result is retained in the
[numerical record](microchrony-control-fixes-results.json).

The [software comparison](microchrony-lead-replay-results.md) establishes the
captured-input agreement with Chrony 4.9. This physical attempt does not extend
that software result into a hardware accuracy qualification.

## Image, setup and bounds

Both boards run the normal 138 MHz `pio-dma-gp2` application, revision
`faaff81f55d0-dirty`, UF2 SHA-256
`ccd101bca3d39d72fec7541a5f0a366f466def2dd0feac9aeb43a92e0879e9ef`.
All linked owned firmware inputs match commit `faaff81`. Concurrent edits to
the USB installer, its documentation and tests caused the dirty build identity;
those changes were preserved and subsequently committed separately. The frozen
deployment helper was used. No alternate firmware target was loaded.

| Board | USB serial | New boot ID |
| --- | --- | --- |
| A | `0BF4B4AEC9FFB344` | `57b48b74d337947fcf5a435c03e1999e` |
| B | `CDDBF8767C506C07` | `fc5e54a9c3dce3414a592ec3f7bcce1a` |

Each load included a verified full 4 MiB private backup, comparison with the
known previous application, verification of the new image, and byte-for-byte
preservation of reserved saved data before reboot. Configuration, Wi-Fi and
manual correction were checked again afterward. Both joined Bohica and received
fresh pool.ntp.org time. Saved correction remained `0.000` ppm / `manual`;
schedules stayed disabled. Retained UTC frequency seeds were preserved.

A's Pico GP22 fed Pi GPIO22 and B's GP22 fed GPIO23. Host GPS HAT PPS on GPIO17
was untouched. The receiver was RSP1B `2404058C60`; GPSDO `0673ED0FA107` and
both Pico outputs used the previously confirmed conducted combiner with separate
60 dB attenuation. Host GPS/PPS and GPSDO lock passed readiness checks.

The run began **October 19, 2026, 09:45:59 CDT**, with an original hard finish
of **10:45:59 CDT** and five minutes reserved for final RF/restoration. Limits
were 512 MiB evidence, 800 new NTP queries per board, three wiring pulses plus
330 main pulses per board, and two two-second RF attempts per board. It stopped
at **09:48:19 CDT**, without restart or extension. Both initial RF jobs completed;
no final RF jobs were attempted.

## GPIO fault

The separate wiring request passed three pulses per board, twelve expected
events and duplicate suppression. Main capture then retained four valid pulses
per board, with sixteen expected events and contiguous global/per-line counters.

At 09:48:17–09:48:19 CDT, the request reported **27 uncommanded falling events**:
14 on A's input and 13 on B's. Twelve distinct cross-input pairs were separated
by only 1.148–3.648 microseconds; two A events and one B event were unpaired
within 100 microseconds. The fault events continue the sequence counters
without gaps. Every raw event and the failing observer traceback are preserved.
No event was filtered, debounced or reclassified to let collection continue.

All 44 saved input-context rows have unchanged input control/pad registers.
The reported power flags remained historical `0x50000`; no sampled current
low-four-bit fault was set. The cached power read was about ten seconds old
at the fault record, so it cannot exclude a brief power disturbance. These
observations do not establish an electrical, cross-talk, supply or kernel cause.
The earlier clean one-hour lead-layout run therefore did not establish a
permanent repair.

## UTC phase and learned rate

Only approximately thirty seconds of main pulses are available. Positive phase
means the Pico's indicated UTC was ahead of the host GPS/PPS timestamp path.
That path's delay is uncalibrated; the existing engineering allowances remain
1 ms plus root distance, with a 5 ms sensitivity calculation.

| Board | First indicated phase | Last indicated phase | Pure learned correction |
| --- | ---: | ---: | ---: |
| A | +5.459 ms | +8.132 ms | +80.408 ppm |
| B | +4.712 ms | +3.442 ms | −0.121 ppm |

A entered this short pulse segment with a transient positive frequency estimate,
well after its initial RF checkpoint. Its public frequency uncertainty was
566.659 ppm. The first three pulse snapshots had total mapping rate +99.098 ppm,
including phase slew. The clock moved farther ahead during the retained segment.
This is an adverse observation, not evidence of convergence or a qualified RF
candidate. Missing early originals prevent an exact reconstruction of the
update that produced this transient.

B's total mapping rate was −42.171 ppm while its pure frequency estimate was
only −0.121 ppm. Most of the observed phase reduction therefore came from the
−42.050 ppm phase-slew component. It cannot be credited to learned frequency.

The exact causal holdouts retain the same starting phase and finite slew and
stop before new model inputs. A has two eligible adjacent forecasts: both
worsen against zero learned frequency, and both are unresolved against the
frequency frozen at this capture's start. B has three adjacent forecasts,
all unresolved against either baseline. Including overlapping longer horizons
gives three A and six B forecasts, with the same respective outcomes. The
5 ms sensitivity retains these verdicts. These are conditional open-loop
forecasts, not independent trials or complete alternative controllers.

## Independent RF checkpoints

Both initial captures pass the unchanged simultaneous-reference fit and receiver
cleanup gates: at least 30 dB contrast, phase residual below 0.15 rad, amplitude
ratio at least 0.5 and half-window difference at most 0.1 Hz. Both outer clock
API triplets bind independently, and each checkpoint retains a stable model.

The following carrier errors are directly measured against the simultaneous
GPSDO harmonics, with the existing 0.05 Hz fit and 10 ppb GPSDO engineering
allowances. Those allowances are not a certified calibration.

| Board | RF error relative to requested 3,570,100 Hz | Native error relative to realized NCO frequency |
| --- | ---: | ---: |
| A | +4.928 to +5.243 Hz | +1.379 to +1.467 ppm |
| B | −0.475 to −0.161 Hz | −0.134 to −0.046 ppm |

Manual mode was preserved, so **no automatic RF correction was applied**. At
these exact RF checkpoints, A's pure UTC correction was −1.030 ppm and B's
was −0.121 ppm. Under the common-oscillator model, those yield inferred corrected
UTC-frequency errors of +0.349 to +0.437 ppm on A and −0.255 to −0.167 ppm on B:
A's estimate helps at that instant, while B's makes the inferred error worse.
These are UTC-frequency inferences, not measurements of corrected RF output.
A's later +80.408 ppm transient cannot be substituted into the earlier RF
checkpoint. Both RF candidates remained unqualified.

The native RF intervals overlap the corresponding initial intervals in the
[previous physical run](microchrony-lead-layout-results.md). No resolved native
carrier improvement is demonstrated. The Internet samples, startup history
and retained seeds also differ, so this before/after comparison cannot isolate
the software changes' causal effect.

## Evidence, review and restoration

All **223 retained files / 69,331,739 bytes** were retrieved privately and
hash-verified. Manifest SHA-256:
`d05c79c8f48653f7833c8bf306b4694f7b193cdae10f94309ef754747fe8e29f`.
Captures, firmware, settings and backups remain outside Git.

The retained packet records cover 43 A and 36 B offers, with an explicit earlier
packet deficit of three on A. There are 23 A and 20 B accepted originals, with
earlier deficits of 20 and 16 respectively. The aborted run has no completed
post-RF accepted frontier. Complete boot or post-baseline input visibility is
not claimed. All six retained API triplets bind independently; no saved true
binding fails recomputation.

Validation passed 17 measurement-arithmetic tests, seven physical-pulse validator
tests, ten logger loss/fault tests, and five packet tests with one platform skip.
All 36 holdout treatment/allowance calculations and both RF residual/improvement
calculations were independently recomputed with rational arithmetic. Adversarial
self-review retains the measurement failure, incomplete coverage and adverse
results. Review corrected event pairing to require distinct events, then
rechecked the resulting twelve pairs against an independent tighter timing
cluster. Reassessment found no remaining actionable analysis finding within
this partial scope; the physical measurement fault remains unresolved. No new
independent-agent review is claimed.

At **09:50:02 CDT**, independent verification acquired all canonical locks after
the observer and all guards actually exited. Both boards retained their new
boots/image identity, settings and manual PPM, were inactive/unowned with
schedules off, and had fresh pool NTP ages of approximately 48.89 s and 32.07 s.
GPIO was restored; GPSDO returned to 10 MHz with both outputs and PPS off;
receiver cleanup and host GPS/PPS selection were verified. The heartbeat is
paused. The stopped run is not restarted or extended.

The requested physical improvement remains unproven. A reliable independent
GPIO measurement path is needed before another convergence result can be
established; the short RF captures and all adverse timing evidence remain valid
only within the scope stated above.
