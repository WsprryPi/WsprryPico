# GPIO timekeeping and frequency-calibration research plan

Recorded: 2026-10-09. Status: selected order of consideration; research only.

The operator selected improvements to the existing GPIO/PIO transmitter as the
current calibration scope. This document selects the order of investigation,
not firmware implementation, hardware testing, or new release requirements.

## Three stages

| Stage | Question and intended outcome | Decision gate |
| --- | --- | --- |
| 1. NTP observation quality, filtering and UTC discipline | Assess receive timestamps, network delay and Pico processing latency; determine whether filtering and correcting the software UTC rate improve start reliability and timekeeping. | Compare existing behavior, bounded filtering, and filtering plus rate discipline. Implement only a demonstrated improvement. |
| 2. NTP-derived Pico calibration | Estimate the Pico oscillator rate from independent raw monotonic/UTC observations, then consider applying a qualified estimate to GPIO carrier generation. | Require stability, an uncertainty bound, and independent RF agreement. Carrier correction and symbol-duration correction are separate slices. |
| 3. Optional GPS UTC + PPS | Feed validated, UTC-labelled PPS observations into the same time/rate subsystem for better calibration and holdover. | Measure capture error and source-transition behavior before applying corrections or extending holdover. |

Stage 1 and Stage 2 share observations and may share a rate estimator. Applying
that estimate to UTC and applying it to RF are separate decisions. Preserve
standalone operation, local complete-job execution, one JobService, and manual
frequency correction as a fallback. The current bench correction is volatile;
a persistent standalone manual setting remains proposed work.

The existing standalone profile has a 500 ms admission ceiling and a 90-second
maximum source age for launch. Preserve these until evidence supports a revised
policy. Keep the raw timer monotonic. A future rate-aware UTC mapping must supply
both forward time projection and inverse UTC-to-alarm conversion. Freeze each
job's selected RF calibration from preparation through completion.

## Optional local NTP source

WsprryPico must retain standalone time acquisition from its configured NTP
server; a local WsprryPi installation is optional. Where a WsprryPi host exists
and its operating-system NTP daemon is configured to serve the Pico, that host
can provide a local reference whose clock has already been filtered and
disciplined. Serving NTP is a host service, not a transmitter-application
function, and installing WsprryPi does not by itself enable that service.
Another suitably configured local Unix host can provide the same option.

The host can discipline its clock using upstream NTP alone; GPS UTC + PPS can
strengthen its reference when available. This makes a local host a useful
Stage 1 comparison source, without establishing the accuracy of any particular
host or removing LAN/Wi-Fi delay and Pico receive-timestamp/processing error.
Source quality must still be evaluated before Stage 2 calibration. GPS/PPS on
the host reaches the Pico through NTP; direct UTC-labelled PPS capture on the
Pico remains the separate, optional Stage 3.

The existing standalone configuration accepts an NTP server hostname or IPv4
address and defaults to `pool.ntp.org`. Automatic discovery, preference and
fallback between local and public servers remain unselected proposals. This
clarification authorizes no host-service, firmware or campaign changes.

## Si5351 remains conditional and deferred

The operator clarified on 2026-10-09 that Si5351 is a possible future addition
depending on the GPIO RF testing currently underway. It is not an assumed next
implementation or a prerequisite for this plan. Preserve the
[existing backlog](si5351-transmission-backlog.md) as a conditional proposal;
Si5351 transmission and CLK2 feedback remain outside this investigation. This
does not select a different Si5351 variant or add an external counter/GPSDO
requirement.

## Observe the existing campaign without changing it

First use completed Phase 14 evidence already recorded by the original runner.
Read only regular evidence files; do not contact a Pico, SDR, GPSDO or reference
service. Do not add INFO/GET_CLOCK requests, NTP polls, packet capture, firmware
logging, RF jobs, wait intervals, repairs or acceptance criteria to the campaign.
Do not stop or message its controller. Copy a bounded, explicitly selected closed
dataset to an ignored local research directory and perform analysis locally.

No added test steps or RF duration are required. File reads/transfers have
ordinary host I/O cost; literal zero runtime interference cannot be certified.
Keep them bounded and exclude actively growing logs and raw IQ captures. No
campaign completion gate depends on finishing the research report. This policy
does not certify unmeasured runtime effects from file I/O.

Existing INFO snapshots can expose UTC-to-monotonic anchor changes, age,
uncertainty, RTT, counters and peer changes. They are not a complete per-exchange
NTP history. An update may be missed between snapshots; latest RTT may describe
a rejected exchange. Diagnostic fields may be sampled at different times.
Verify exact schemas and acquisition order before reconstructing quantities.
Partition by board, boot, firmware, clock and source; preserve failures.

The immediate deliverables are the
[research execution prompt](gpio-time-calibration-research-prompt.md) and
[executed findings and adversarial review](gpio-time-calibration-research.md).
Future firmware/hardware work requires a separate bounded implementation task.
The later [review-closure prompt](gpio-time-calibration-review-closure-prompt.md)
and [executed closure](gpio-time-calibration-review-closure.md) preserve the
reproducible methods, evidence gates and separately authorized Git publication.

## Required distinctions

- UTC accuracy, offset stability, oscillator rate, carrier error and symbol
  duration are different quantities.
- An apparent slope or a smooth fitted curve is not validated PPM calibration.
- The assumed 50 ppm uncertainty-growth allowance is not a measured correction.
- Host timestamps do not independently qualify absolute UTC or GPIO onset.
- Receiver/reference corrections do not discipline the Pico.
- GPS/PPS is optional; a saved frequency estimate does not establish UTC at boot.
- The research cannot change existing pass/fail dispositions or qualify a band.

## Source anchors

- `src/time/sntp.cpp`: `Sntp::receive`, lines 32-79.
- `src/time/utc_discipline.cpp`: `observe`/`snapshot`, lines 23-92.
- `src/standalone/wtp_profile.hpp`: standalone clock/service limits, lines 7-18.
- `src/standalone/config.hpp`: default time server and configured server field, lines 12 and 24.
- `src/standalone/scheduler.cpp`: admission/occurrence construction, lines 70-139.
- `src/rf/waveform.cpp`: nominal sample counts and corrected increments, lines 9-24 and 87-115.
- `src/phase14/live.py`: existing INFO collection and event recording.

See [RFC 5905](https://www.rfc-editor.org/rfc/rfc5905.html), sections 10-12,
for filtering/clock-discipline concepts. These are design references, not a
claim that the present restricted SNTP client implements full NTP.
The [chrony FAQ](https://chrony-project.org/faq.html), sections 2.1-2.3 and 2.7,
describes host clock discipline, explicitly enabled NTP serving and the limits
of measurements affected by network delay. It is a design reference, not
evidence of the historical test host's configuration or accuracy.
