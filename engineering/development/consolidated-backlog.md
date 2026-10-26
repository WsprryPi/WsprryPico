# Consolidated backlog

Selected unfinished work is listed below. Current product behavior is documented
in the maintained guides; completed execution records are not an active work list.
The reusable [cleanup instructions](repository-cleanup-prompt.md) govern explicit
repository and harness cleanup requests.

## Operator validation

### TODO: Lee to test USB browser recovery on Windows

Follow [Recover browser access over USB](../../docs/usb.md) on a native Windows computer using desktop Google Chrome and an installed Pico. The browser terminal has returned INFO from a connected Pico on macOS; Windows validation remains open. This test covers the browser Console route, not Windows support for the command-line installer.

- [ ] Record the Windows and Chrome versions, Pico USB serial, full device ID, firmware version and source revision.
- [ ] Confirm that Device Manager shows the Pico's serial ports and that Hardware Ids identifies the Console with **MI_00**, WTP with **MI_02** and management with **MI_04**. Record the matching Console COM number; confirm that Chrome's chooser lets the operator select that exact port.
- [ ] Follow the documented SerialTerminal.com settings: DTR on; RTS, dtrDsr and rtsCts off; Advanced terminal view; 115200 baud; **send with /n** on and **send with /r** off. Confirm that the command box and **Send** transmit `INFO` successfully.
- [ ] Confirm that the complete INFO reply remains available by scrolling inside the terminal, including its initial `ok`, `device_id`, `firmware` and `revision` fields and final closing JSON. Read the network address and web-service fields without losing the start of the reply.
- [ ] With the Pico idle, send `ACCESS SOFTAP` with that full device ID. Confirm the successful reply, join setup Wi-Fi and open `http://192.168.4.1/`. Record any refusal with firmware identity. Check connected-client retention and the ten-minute interval after the final disconnect using firmware containing that change.
- [ ] Close the browser terminal tab and confirm another serial terminal can open the Console. Capture Windows screenshots of Device Manager identity, Chrome's selected port, terminal settings and the successful INFO reply; keep credentials and private network details out of published images.
- [ ] Update the USB walkthrough with the observed Windows labels, screenshots and any required corrections. Mark Windows verified only after the real Windows/Pico procedure succeeds.

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
