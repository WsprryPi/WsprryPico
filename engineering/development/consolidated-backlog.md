# Consolidated backlog

Selected unfinished work is listed below. Current product behavior is documented
in the maintained guides; completed execution records are not an active work list.
The reusable [cleanup instructions](repository-cleanup-prompt.md) govern explicit
repository and harness cleanup requests.

## Remain in backlog for future

- **Si5351**
  - Optional external-engine enhancement.
  - CLK2 calibration only if that engine is selected.
- **Optional amplifier settling and lead/tail timing.**
- **LPF/band-selector control**, if economically useful.
- **Optional GPS UTC + PPS and improved holdover.**
  - Reuse the original MIT [μChrony engine](../../src/microchrony/README.md):
    bounded source histories, adaptive frequency estimation, source selection
    and combination, uncertainty propagation, and separate phase slewing and
    frequency correction. Add a reference-clock input path; GPS/PPS
    ingestion is not implemented today. Keep one clock-control loop rather than
    adding a second GPS servo or fabricating NTP packets for PPS.
  - Add a portable, timestamped reference-observation interface and a Pico SDK
    adapter that captures PPS against the raw monotonic clock. Pair each edge
    with a GPS message identifying its UTC second; PPS alone does not supply
    the date or second number. Qualify capture latency, cable delay, receiver
    time validity, GPS-to-UTC conversion and leap handling. Preserve the
    portable engine's separation from hardware and transport.
  - Admit reference-clock observations using source-specific validity and error
    bounds, including missing, duplicate, mispaired and implausible pulses.
    Keep network packet/delay filtering specific to NTP. Define GPS/PPS versus
    NTP disagreement, source selection, loss of lock, fallback and reacquisition
    without weakening existing clock, launch or RF quality gates. During
    holdover, propagate increasing uncertainty from the last valid observation;
    status reads and rejected pulses must not refresh its age.
  - Reuse and extend the Pico correction journal with source provenance.
    Restore a learned frequency only as a provisional restart seed, never as
    restored UTC, synchronization or freshness. Keep the operator's persistent
    manual PPM separate from learned UTC and RF corrections.
  - Use qualified PPS frequency estimates as potential RF correction inputs
    only where the measured timer and selected RF engine have a verified common
    clock relationship. Independently qualify actual carrier error before
    claiming RF accuracy; improved UTC timing or narrower statistical bounds
    alone do not establish RF accuracy. Preserve manual correction and existing
    RF qualification requirements. See the [independent measurement
    boundaries](microchrony-independent-measurement.md).
  - Extend known-error tests and the external Chrony 4.9 reference comparison
    to paired GPS/PPS observations, drift, holdover, restart, source conflict
    and reacquisition. Follow its documented [reference-clock
    rules](https://chrony-project.org/doc/4.9/chrony.conf.html#refclock) using
    original MIT code. Validate UTC timing and RF frequency separately against
    independent physical references, with measured path errors and explicit
    acceptance bounds. The retired Pico-to-Pi GPIO measurement path is not a
    prerequisite or input for this future GPS/PPS work; use a qualified reference
    source connected through the proposed input adapter.
- **Advanced Pico scheduling and durable controller/member transfer**, after
  WsprryPi [issue 333](https://github.com/WsprryPi/WsprryPi/issues/333) research.
- **Keying-envelope work.**
- **Native iPhone consumer BLE app**, only for a need Wi-Fi does not meet.
- **Enterprise/WPA3-only provisioning**, if a useful case emerges.
- **Automatic NTP-server discovery and preference.**
- **Additional LAN/page-delivery security**, if deployment needs change.
