# Consolidated backlog

Selected unfinished work is listed below. Current product behavior is documented
in the maintained guides; completed execution records are not an active work list.
The reusable [cleanup instructions](repository-cleanup-prompt.md) govern explicit
repository and harness cleanup requests.

## Operator validation

### TODO: Direct Windows setup-Wi-Fi association

Native Windows Chrome Console identity, settings, complete INFO display, successful ACCESS SOFTAP and port release were verified on 2026-10-26. The [USB walkthrough](../../docs/usb.md) includes the observed Windows labels and five cropped screenshots. The operator directed AP testing to wspr5 to preserve ecm-mule's network connection; the [bounded validation record](usb-cdc.md#windows-browser-console-validation-2026-10-26) separates those results from the Windows checks. Windows support for the command-line installer remains outside this procedure.

- [ ] Complete the direct Windows Wi-Fi portion of [Recover browser access over USB](../../docs/usb.md) when an independent management connection is available: join the requested Pico AP, open `http://192.168.4.1/` in desktop Chrome and return to the original network. The failed Windows automation is not accepted as a verified association; do not modify ecm-mule's network for further testing under the current operator restriction.

## Backlog TODO

### Combined UI / backend

- [ ] **Syslog over USB.** Implement Pico logging/export, WsprryPi collection, both UIs, stable Pico/host identity, lifecycle handling, documentation and validation as one coordinated feature. See the [USB execution prompt](syslog-proposals.md#usb-syslog-execution-prompt), including its shared standing authority. Not started.
- [ ] **Syslog over UDP.** Prepare the reviewed proposal for Pico and WsprryPi senders, member-to-collector forwarding, a Pi collector, both UIs, preserved origin/relay identity, loop prevention, duplicate handling, documentation and validation. See the [UDP proposal prompt](syslog-proposals.md#udp-syslog-proposal-prompt), including its shared standing authority. Proposal and implementation not started.
- **LPF/band-selector control**, if economically useful.

### Backend

- **Optional amplifier settling and lead/tail timing.**

### UI

- [ ] **WsprryPi-style contextual status console with Reset Pico.** Follow the [saved execution prompt](wsprrypi-style-status-console-prompt.md) for mode-aware status, public read-only visibility, accurate schedule/progress/frequency information and a guarded authenticated reset. Include adversarial review and repeated assessment after fixes. Not started; prompt saved only.
- Collapse all sections by default except **Transmitter status**.
- Make login and takeover less obtrusive.
- Add logically grouped menu links using in-page `#anchors`, with `/wifi-host` as the navigation reference. Selecting a link should scroll to its section and expand it.
- Add a **Back to Status** link to each section that collapses all other sections and returns to **Transmitter status**, leaving it expanded.

## Possible future work

- **Si5351**
  - Optional external-engine enhancement.
  - CLK2 calibration only if that engine is selected.
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
