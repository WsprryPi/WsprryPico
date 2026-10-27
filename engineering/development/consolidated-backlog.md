# Consolidated backlog

Selected work is listed below, with completed items marked explicitly. Current product behavior is documented in the maintained guides.
The reusable [cleanup instructions](repository-cleanup-prompt.md) govern explicit
repository and harness cleanup requests.

## Operator validation

### Completed: Windows browser recovery and setup-Wi-Fi association

Native Windows Chrome Console identity, settings, complete INFO display, successful ACCESS SOFTAP and port release were verified on 2026-10-26. The [USB walkthrough](../../docs/usb.md) includes the observed Windows labels and five cropped screenshots. The operator directed AP testing to wspr5 to preserve ecm-mule's network connection; the [bounded validation record](usb-cdc.md#windows-browser-console-validation-2026-10-26) separates those results from the Windows checks. Windows support for the command-line installer remains outside this procedure.

1. [x] **Direct Windows setup-Wi-Fi association and browser recovery.** Completed, as confirmed by the operator.

## Backlog TODO

### Combined UI / backend

2. [x] **Syslog over USB.** Pico logging/export, Pi collection, both UIs, stable identity and maintenance coordination are implemented. The dedicated fourth Logging channel preserves the existing Console, WTP and Management identities. Physical simultaneous-operation tests and both required production-path integration suites passed for the paired candidate sources; see the [USB logging contract and validation bounds](usb-logging.md#validation-bounds). Delivery is on the named candidate branches, not a release or merge into devel.
3. [ ] **Syslog over UDP.** Prepare the reviewed proposal for Pico and WsprryPi senders, member-to-collector forwarding, a Pi collector, both UIs, preserved origin/relay identity, loop prevention, duplicate handling, documentation and validation. See the [UDP proposal prompt](syslog-proposals.md#udp-syslog-proposal-prompt), including its shared standing authority. Proposal and implementation not started.
4. **LPF/band-selector control**, if economically useful.

### Backend

5. **Optional amplifier settling and lead/tail timing.**

### UI

6. [x] ✅ **WsprryPi-style contextual status console with Reset Pico.** Mode-aware accepted-job and future-schedule context, public read-only status, nominal frequencies, coarse progress, manual correction, clocks and guarded authenticated reset are available. See the maintained [status-console contract](status-console.md). Character-level progression remains unimplemented.
7. [x] ✅ **Furl sections by default.** Non-status sections use native disclosures, closed on ordinary entry; Transmitter status stays visible. Explicit bookmarks and pending save continuations reveal needed content. See [browser sections](browser-pages.md#sections-and-navigation).
8. [x] ✅ **Hostname lock control and password modal.** The hostname lock opens a password dialog or logs out this browser through its admitted session adapter. Certificate access presents its browser-managed authority. See [browser access](browser-pages.md#browser-access).
9. [x] ✅ **Grouped links to furled sections.** Sections groups stable links by task area; links reveal and focus their target while preserving drafts, session context and receipt bytes. See [navigation compatibility](browser-pages.md#sections-and-navigation).
10. [x] ✅ **Top links.** Top closes every non-status section and its nested disclosures in both areas, preserves drafts and authority, and returns focus and scroll to the persistent status region. See [browser sections](browser-pages.md#sections-and-navigation).

## Possible future work

11. **Si5351**
    - Optional external-engine enhancement.
    - CLK2 calibration only if that engine is selected.
12. **Optional GPS UTC + PPS and improved holdover.**
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
13. **Advanced Pico scheduling and durable controller/member transfer**, after
    WsprryPi [issue 333](https://github.com/WsprryPi/WsprryPi/issues/333) research.
14. **Keying-envelope work.**
15. **Native iPhone consumer BLE app**, only for a need Wi-Fi does not meet.
16. **Enterprise/WPA3-only provisioning**, if a useful case emerges.
17. **Automatic NTP-server discovery and preference.**
18. **Additional LAN/page-delivery security**, if deployment needs change.
