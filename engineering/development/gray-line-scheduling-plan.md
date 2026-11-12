# Gray-line propagation research and scheduling proposal

This report retains the research and original scheduling proposal. Current behavior and limits are described in the [operator manual](../../docs/configure.md#gray-line-scheduling) and [standalone engineering guide](standalone.md#gray-line-selection). The proposal does not establish RF qualification or a propagation guarantee.

## Recommendation

Use the Sun's calculated elevation at the station to select a separate gray-line schedule, with a default window of −6° to +6°. Treat this as a practical propagation opportunity window. Morning and evening schedules, windows, and frequencies are independently configurable.

Allow any otherwise supported frequency, with no gray-line band restriction. 40 m and 80 m are useful starting points for evaluation, and 160 m is another candidate where supported; these are evaluation suggestions, not limits on available frequencies. Existing RF engine and frequency-policy limits remain independent of scheduling.

## Research findings

Gray-line opportunities arise because ionospheric absorption and refraction change differently around twilight. The absorbing D region weakens while higher regions can still support long-distance propagation. ARRL describes the phenomenon primarily in terms of twilight communication below 15 MHz. See the [ARRL Extra Class study guide](https://www.arrl.org/files/file/Extra%20Class%20License%20Manual/ECLM%2010th%20edition/Studyguide%20%20FINAL.pdf).

Lo et al.'s 2022 paper, *A Systematic Study of 7 MHz Greyline Propagation Using Amateur Radio Beacon Signals*, examines WSPR observations between the UK and New Zealand, among other paths. Reception differed by direction: UK-to-New Zealand links appeared around both UK sunrise and sunset, while New Zealand-to-UK links occurred mainly around UK sunrise. This supports treating morning and evening independently rather than assuming identical performance or one universally optimal window. See the [published study](https://www.mdpi.com/2073-4433/13/8/1340).

RSGB distinguishes propagation along the terminator from broader sunrise and sunset enhancements into darkness. Its guidance includes useful 40 m openings before sunset and after sunrise. Restricting scheduling to times when the Sun is below the horizon would therefore miss plausible opportunities. See the [RSGB Propagation Studies Committee guide](https://rsgb.org/main/files/2012/10/Understanding_LF_and_HF_propagation.pdf).

There is no universally established solar angle marking a radio opening. Civil twilight's −6° boundary is an astronomical lighting convention. VOACAP Online uses −6° and +6° transition markers, describing the positive-angle cutoff as a practical, empirical choice. The proposed defaults follow that planning practice; they are not scientifically validated optimum limits for every band and path. See the [U.S. Naval Observatory definitions](https://aa.usno.navy.mil/faq/RST_defs) and [VOACAP Online manual](https://www.voacap.com/2023/documents/VOACAP_Online_User_Manual_16_July_2024.pdf).

The original feature reference remains [Ham Radio Base: Grey Line Propagation](https://www.hamradiobase.com/ham-radio-propagation-grey-line/). The primary and specialist sources above provide the basis for this proposal.

## Proposed scheduling method

### Time and station location

Use valid UTC and an explicit station location source: a fresh valid GPS position or the configured Maidenhead locator's center, matching the existing day/night location choices described in the [GPS/PPS guide](gps-pps.md). Unusable time or missing required position prevents gray-line admission and produces an understandable status. Do not silently substitute a different location source.

### Solar calculation and default windows

Calculate geometric Sun-center elevation locally. Reuse the existing solar calculation foundation, with an explicit geometric elevation definition and without double-applying refraction corrections. NOAA publishes suitable [solar calculation equations](https://www.gml.noaa.gov/grad/solcalc/solareqns.PDF). Its conventional sunrise/sunset threshold is approximately −0.833°, distinct from the proposed gray-line boundaries.

| Period | Default entry | Default exit |
| --- | --- | --- |
| Morning | Sun rises through −6° | Sun rises through +6° |
| Evening | Sun descends through +6° | Sun descends through −6° |

Solar elevation accommodates seasonal and latitude-dependent changes in window duration. No local time zone, daylight-saving adjustment, destination database, or Internet service is needed for local scheduling. Calculate solar geometry rather than using observed light levels, weather, or a terrain horizon.

### Independent configuration and precedence

Allow morning and evening schedules to be independently enabled and configured, including their solar-elevation boundaries and frequency selections. Permit any otherwise supported frequency; do not enforce a low-band-only list.

An enabled gray-line schedule takes precedence over ordinary day/night scheduling inside its window. Outside that window, or when gray-line scheduling is disabled, ordinary day/night selection applies. A missing required location or unusable UTC prevents gray-line admission rather than establishing a valid alternative gray-line selection.

### Complete-occurrence admission

Evaluate scheduled transmission times at complete-occurrence admission rather than the time at which the scheduler happens to poll. For a paired WSPR occurrence, require both frame starts to qualify before admitting the pair. Accepted occurrences retain their local lifecycle and may finish across a window boundary. Do not interrupt an accepted transmission at a solar boundary or catch up missed occurrences.

### Polar conditions

Calculate actual solar elevation even when sunrise or sunset does not occur. If the Sun remains within the configured window for an extended period, report that prolonged condition rather than inventing two daily events. The implemented solar-hour-angle branch assignment and prolonged-window status are defined in the [standalone guide](standalone.md#gray-line-selection), without relying on nonexistent sunrise/sunset crossings.

## Local scheduling and destination targeting

For a general WSPR beacon, the local solar window determines when to try the gray-line schedule. It does not establish a particular usable propagation path.

Optionally accept a target locator and calculate destination solar elevation. Overlapping transition windows provide an additional planning indicator; a destination in darkness can identify broader sunrise/sunset opportunities. Neither condition proves a usable path. Simultaneous twilight at both endpoints is not mandatory for general beacon operation.

Space-weather information can supplement the indicator. NOAA's D-RAP estimates HF absorption associated with solar X-rays and energetic particles; it does not predict gray-line enhancement. Keep it advisory and preserve offline scheduling. See [NOAA D-RAP](https://www.swpc.noaa.gov/products/d-region-absorption-predictions-d-rap).

## Propagation evaluation

Compare WSPR reception success and signal reports against solar elevation, separately by band, morning/evening period, and destination region. Normalize by actual transmissions and account for receiver availability; raw spot totals alone can mislead. Use observations to refine defaults without presenting the initial window as a measured optimum.

Exact boundary limits, endpoint inclusion, solar-extremum behavior, admission snapshots, fallback, and complete-pair selection are specified in the standalone guide. The current shared control contract coordinates Pi/Pico configuration, descriptors, validation, and browser controls. Production network and USB source-pair checks establish software interoperability; physical RF and propagation evaluation remain separate.
