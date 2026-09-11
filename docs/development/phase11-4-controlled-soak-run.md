# Phase 11.4 controlled eight-hour soak

Status: **PASS — full eight-hour controlled inhibited soak reviewed**. The user requested this run on
September 10, 2026 and authorized selection of the most stable available radios.
The clock started at **2026-09-10 20:02:39.297 UTC** and ends at
**2026-09-11 04:02:39.297 UTC**: September 10, **3:02:39 PM–11:02:39 PM CDT**.
Elapsed execution alone is not a passing result.

## Setup and identity

The onboard wlan0 access point and independent USB wlan2 client repeat the
arrangement qualified in the [three-radio campaign](phase11-4-three-radio-results.md).
The client has its own network and mount namespaces, resolver and Avahi cache.
Ethernet remains the management path; USB wlan1 stays associated with Bohica-IoT.
The Mac is not a soak observer. Execution and restoration run locally on wspr5
and do not depend on an SSH connection remaining open.

| Role | Identity and configuration |
| --- | --- |
| Test AP | wlan0, MAC `2c:cf:67:62:76:66`, channel 11, WPA2 CCMP, `WsprryPico-Test`, `10.77.14.1` |
| Independent client | wlan2, MAC `e8:4e:06:ae:d7:09`, namespace `phase11-hotspot`, `10.77.14.2` |
| Ordinary Wi-Fi management | wlan1, MAC `90:de:80:47:b9:da`, Bohica-IoT, original profile `921301fe-cdfd-4965-8ac7-c96e9d908ea6`, `192.168.1.117` |
| Ethernet management | eth0, MAC `2c:cf:67:62:76:64`, `192.168.1.54` |
| wspr5 boot | `220e53ca-ca95-4206-9581-dbe28aa1eeb8` |
| Pico A | Pico 2 W / RP2350; serial `0BF4B4AEC9FFB344`; device `fd6127d11d6aca42a9905fa3fb1bf1d5` |
| Runtime and boot | `802c91a7b86e-dirty`; `d495116397e59aec311764d555ac6052` |
| Engine and clock | `inhibited-standalone-simulator`; 150 MHz; network time from wspr5 |
| Network identity | MAC `88:a2:9e:0a:60:df`; `wsprrypico-0a60df.local`; `10.77.14.10`; TLS port 18443 |
| Previously verified UF2 SHA-256 | `25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10` |
| SDK pin | 2.3.1, `079c6f39023649b154152db30f1d781e884879bc` |
| Server leaf SHA-256 | `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016` |

No firmware was flashed. Setup changed only Pico A's network configuration and
rebooted it before the measurement interval. Read-only preflight verified both
Picos; Pico B remains unchanged on Bohica-IoT, boot
`4e2fb851c08b278dd4b977104d2c2aaa`, revision `dbf1d86f0885-dirty`.
A remains empty, unowned and output-inactive, with schedules disabled, healthy
storage and station AA0NT/EM18/20. The saved watermark remains
`1788714601000000000`. No job, arm, transmit or RF operation is authorized here.

## Execution and records

The opt-in [controller](../../scripts/phase11_4_controlled_soak.py) uses an
unchanged private copy of the existing diagnostic sampler. It supplies the
current boot, revision and test address, separate bounded workers, complete
packet captures and automatic restoration. Deployed scripts remain immutable.

- USB INFO approximately every five seconds, plus WTP HELLO/CAPS/STATUS every
  twelfth observation. Intervals are delays after work, not fixed sample rates.
- Independent native DNS and pinned, hostname-verified mutual TLS 1.3 HTTPS reads
  approximately every 30 seconds during active windows. DNS failure does not
  suppress the direct-IP HTTPS observation.
- Network probes pause for the first 120 seconds of each 600-second window and
  the final 120 seconds. Quiet memory comparisons additionally require observed
  zero TCP PCB, segment and packet-pool use. USB/WTP polling continues.
- Host association, routes, services and client namespace context approximately
  every five minutes. Preflight supplies the initial host check.
- AP and client packet captures use full snap length with no ring overwrite.
  Capture integrity, coverage and final kernel drop counts require final review.
- Workers retain every failure/timeout and fsync JSONL records. No automatic
  replacement run or device recovery is allowed after unexpected boot changes.

Remote private evidence: `/home/pi/phase11-4-controlled-soak-20260910`.
Local private pointer and startup evidence: `build/phase11-4-controlled-soak/`.
The pointer includes the immutable deployed Python source hashes.

`phase11-controlled-soak.service` supervises the 28,800-second interval, with a
29,400-second service ceiling. AP/client fixture services have 33,000-second
ceilings. A separate `phase11-soak-finish` service restores the original Pico A
network configuration and radio state after observer closure. An independent
`phase11-soak-cleanup.timer`, armed for nine hours after setup, provides a bounded
fallback. Restoration is verified, not inferred from stopping a service. An
unexpected Pico boot blocks automatic device mutation and is retained for review.

The task heartbeat `review-controlled-pico-eight-hour-soak` checked periodically,
remained quiet while healthy, and completed the final evidence review. It is now
paused. The remote run did not depend on that heartbeat executing.

## Validation and final acceptance

Startup preflight passed exact USB/WTP identity and inactive-output validation,
native DNS, mutual TLS HTTPS and host-management checks. A preflight checker
initially selected a raw WTP response instead of the aggregate result; that
checker was corrected before starting the measurement interval. No failed soak
sample was discarded. Four controller tests and sixteen fixture audit tests pass.
At 167.92 seconds into the interval, 33 USB observations and the first scheduled
DNS/HTTPS observation had completed without recorded failures. All five child
processes remained alive and both captures contained packets. The five-minute
host worker had not yet reached its first scheduled sample; host preflight passed.

Final review must establish full host/Pico boot continuity, actual coverage and
maximum observation gaps; classify every DNS, transport, status, USB and observer
failure; compare equivalent quiet memory states across the interval; report
allocation-error deltas, retained TLS/lwIP memory and stack high-water marks;
check captures and saved-state drift; and verify both Picos and host restoration.
An adversarial review must challenge those calculations and closure claims before
acceptance is updated. A later successful sample does not erase an earlier fault.

This qualifies only the measured controlled Linux AP/client workload. It does
not establish browser JavaScript behavior, Windows installation, RF output or
absence of every possible memory leak. Existing historical soak and shutdown
records remain separate and unchanged. The completed result below is limited to this measured workload.


## Completed result — September 11, 2026

**PASS for the eight-hour controlled inhibited workload.** All three workers
finished the full 28,800-second interval at 04:02:39.297 UTC, retaining the original
host and Pico A boot throughout. All five child processes exited successfully.
There were no recorded DNS, TLS/TCP, status-validation, USB or observer failures.

| Observation | Reviewed result |
| --- | --- |
| USB INFO | 5,593 valid observations; unchanged device, boot, revision, saved state and inactive output |
| Read-only WTP | 467 valid HELLO/CAPS/STATUS checks; empty, unowned and inactive |
| Native Linux DNS | 740/740 returned the correct address |
| Authenticated HTTPS | 740/740 valid pinned-identity status reads; maximum combined DNS/HTTPS sample duration 3.984 seconds |
| Host observations | 95/95 passed; Ethernet, Bohica-IoT management and independent test client remained available |
| USB coverage | First sample 1.083 seconds after start; last 2.456 seconds before end; maximum gap 5.832 seconds |
| Network coverage | Maximum gap 152.440 seconds, including planned 120-second quiet periods; first/last offsets 141.083/144.648 seconds |
| Host coverage | Maximum gap 300.271 seconds; initial preflight and independent final checks supplement periodic sampling |
| Packet capture | AP 23,621 packets; client 20,750 packets; complete records, no truncated packets, zero kernel drops, clean closure |

Network quiet periods are intentional gaps in active availability measurements.
The client capture's first/last matching packets are 20:05:00.584 and
04:00:15.518 UTC, consistent with those quiet periods; capture processes remained
alive through the interval. AP matching packets span 20:02:34.331 through
04:02:34.340 UTC. Capture completeness is checked against record parsing,
reported packet totals, process lifetime and final drop statistics; packet
silence is not itself proof of availability.

### Memory result

There are **571 comparable quiet samples** across all 48 ten-minute windows and
the final quiet period. Selection uses the latter minute of each pause and
requires measured zero TCP PCB, TCP segment and packet-pool use. Application
heap rose during initial warm-up: first-window median 21,240 bytes, then
23,000–23,016 bytes in subsequent windows, ending at 23,008 bytes. The initial
rise is retained in the evidence; its allocation provenance was not instrumented.
There is no sustained growth in this run after that initial rise.

Separating the periodic USB workloads gives the same stable conclusion:
post-warm-up INFO-only window medians are 23,000–23,016 bytes, and INFO samples
immediately before WTP checks are 21,280–21,296 bytes. Final corresponding medians
are 23,008 and 21,288 bytes. This comparison avoids mistaking periodic retained
response/cache allocations for a memory trend.

Quiet TLS allocation stayed **4,396 bytes**, and lwIP heap stayed **200 bytes**.
TLS allocation failures and every observed lwIP allocation-error counter remained
zero. Final cumulative sampled peaks were 53,440 bytes application heap,
34,884 bytes TLS allocation and 8,104 bytes core-0 stack usage. Peaks are
cumulative sampled diagnostics, not proof that every transient maximum was seen.
No reset fault breadcrumbs, network identity drift, clock-state loss or saved
configuration drift occurred in the measured samples.

### Restoration and independent confirmation

Automatic restoration finished at **04:02:57.445 UTC** (11:02:57 PM CDT), about
18.15 seconds after the interval. Pico A returned to `192.168.1.47` with its
original name and saved state. Its intentional restoration reboot produced
`6dde51620f660879680d8335d8bbc71c`, after the completed soak. Independent USB
INFO and WTP reads confirmed both Picos inactive and unowned. Pico B retained its
original boot, revision, name and `192.168.1.53` address.

wspr5 retained boot `220e53ca-ca95-4206-9581-dbe28aa1eeb8`. Ethernet and original
Bohica-IoT profile/address/BSSID remained intact. The private test namespace,
access-point profile and test route were removed. wlan0/wlan2 returned down with
power saving on; wlan1 retained power saving off. The transmitter service and
Wi-Fi recovery timer remain active. All soak/fixture services and cleanup timer
are inactive. A separate SSH connection to Wi-Fi address `192.168.1.117`
succeeded after restoration. No further reset or firmware change was made.

### Adversarial review and evidence

Review independently parsed the raw records instead of relying only on observer
success flags. It checked source/evidence hashes, strict identity and ownership,
complete worker lifecycles, count reconciliation, chronological and monotonic
continuity, sampling gaps, packet integrity and final device/host restoration.
Review tightened the analysis to require independent restoration evidence and
count/coverage checks. Fourteen deliberately corrupted semantic cases were all
rejected, including changed boot, allocation errors, active output, saved-state
drift, DNS failure alongside successful HTTPS, wrong TLS identity, missing
samples/finish markers, observer death, bad child exit, second-board reboot and
false WTP success. Two subsequent clean assessments passed. No actionable
finding remains within this soak's measured scope.

The local private `build/phase11-4-controlled-soak/` contains `analysis.json`,
`analyze.py`, `adversarial.json`, `adversarial.py`, `final/` raw evidence and
`evidence-index.json`. The full remote USB/network/host/supervisor and capture
hashes match the archived files. Deployed sampler hashes match the launch
manifest. A local extraction issue with macOS metadata sidecars was corrected
by recovering their exact archived bytes; no observation was modified.
The initial final-check invocation was denied directory access before device
access; the root-owned read-only helper then completed both inspections.

This closes the remaining eight-hour soak gate and Phase 11.4 within the existing
bounded inhibited acceptance matrix. It does not close Phase 11.5 resource/timing
contention, Phase 11.6 conducted RF acceptance or Phase 11.7 final joint review.
Historical failed attempts remain preserved in their original records.


## Reproducing the offline review

The [machine-readable result](phase11-4-controlled-soak-evidence.json) preserves
measured statistics, the fourteen mutation outcomes and raw-file SHA-256 values.
Raw evidence and credentials remain private. The original private analysis is
preserved; the maintained [audit](../../scripts/audit_phase11_4_controlled_soak.py)
and [mutation checks](../../tests/phase11_4_controlled_soak_evidence_tests.py)
accept an explicit private evidence directory and a fresh output path. Neither
performs device or network operations. Python 3.9 or newer is required.

From the repository root, with the archived evidence available:

```sh
python3 -B scripts/audit_phase11_4_controlled_soak.py \
  --evidence-root build/phase11-4-controlled-soak/final \
  --output build/phase11-4-controlled-soak/review-replay.json
python3 -B tests/phase11_4_controlled_soak_evidence_tests.py \
  --evidence-root build/phase11-4-controlled-soak/final \
  --output build/phase11-4-controlled-soak/adversarial-replay.json
python3 -B tests/phase11_4_controlled_soak_tests.py
```

Keep `current.json` beside the evidence directory, as archived, and retain the
immutable `scripts/` snapshot inside it for source-hash verification. The auditor
imports maintained repository validation code, not code from the evidence.
It checks continuity, identity, sample counts/gaps, capture integrity and
restoration, and emits memory statistics. Its successful exit does not replace
the memory interpretation and bounded acceptance assessment documented above.
The snapshot's `._` metadata sidecars are also hashed; when unpacking on macOS,
retain their exact archived bytes rather than allowing automatic metadata merging.
