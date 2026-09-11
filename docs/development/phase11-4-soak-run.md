# Phase 11.4 eight-hour diagnostic soak

Status: **REVIEWED — interrupted memory/USB soak; Mac observation finished**.
The eight-hour memory/USB soak did not complete. The Mac observer ran through
the original deadline and closed. Neither the elapsed window nor later recovery
closes B2/D2 or establishes a firmware repair.

The user confirmed on September 10 that a brief power outage occurred during
the night. The soak interruption is attributed to that reported outage; further
diagnosis of this host/device power-loss event is closed and removed from the
Phase 11.4 remaining work. A new uninterrupted eight-hour soak remains required.

The user explicitly requested this run on September 9, 2026. The earlier
post-repair prerequisite is superseded for this diagnostic run only. No device
reset, firmware deployment, Wi-Fi change, job, trust import or RF operation is
part of the soak. The second Pico remains untouched.

## Run identity

- Planned interval: **2026-09-10 01:26:14 through 09:26:14 UTC**, eight hours.
  Local America/Chicago: September 9 at 8:26:14 PM through September 10 at
  4:26:14 AM CDT. Observer startup precedes the measurement interval.
- Original Pico serial: `0BF4B4AEC9FFB344`.
- Device: `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Expected boot: `3b1e15c0a2bb7c29cabd31a1b1ab2597`.
- Reported revision: `677ec7fde236-dirty`; engine:
  `inhibited-standalone-simulator`.
- Deployed UF2 SHA-256:
  `b1921701ccffee8ca630cbf719f8328ddfa417c86e707f960ea84148862b79b3`.
- Hostname: `wsprrypico-0a60df.local`, IP `192.168.1.47`, HTTPS port `18443`.
- Pico on Bohica-IoT. wspr5 remains on Bohica using USB wlan1, original profile
  `921301fe-cdfd-4965-8ac7-c96e9d908ea6`, BSSID `6c:cd:d6:f2:f6:c6`, frequency
  5200 MHz, power save on. Onboard wlan0 remains untouched.
- Mac remains on its existing network via en0.

Preflight USB INFO and WTP HELLO/CAPS/STATUS confirm the expected device,
revision and boot, inactive output, empty/unowned state, disabled scheduling,
healthy storage, and no recorded allocator errors or reset fault breadcrumbs.
Both hosts' native DNS and certificate/hostname-verified TLS 1.3 HTTPS checks
pass. wspr5's installed transmitter and Wi-Fi recovery timer are active; recovery
remains boot-enabled. No service configuration was changed.

## Observers and storage

[The opt-in observer](../../scripts/phase11_4_soak.py) has independent USB,
network and host-state workers. Subprocess deadlines keep a stalled network
request from blocking USB memory samples. Wall-clock timestamps coordinate the
quiet windows; monotonic bounds prevent a backward clock adjustment from
extending execution indefinitely. Clock changes and actual gaps must be reviewed.

- USB INFO approximately every five seconds, plus read-only WTP HELLO/CAPS/STATUS
  approximately every minute. Intervals are delays after bounded work, not exact
  fixed-rate sampling. All raw JSON, errors and child timeouts are retained.
- Native DNS and direct-IP HTTPS with certified hostname/SNI, pinned leaf,
  existing mTLS identity and strict status validation approximately every 30
  seconds on each host during active periods. DNS failure does not skip HTTPS.
- The first two minutes of every ten-minute window and the final two minutes
  suppress this harness's network probes. Only samples with zero TCP PCB,
  segment and packet-pool use qualify as quiet resource candidates. Actual
  traffic may cross a window boundary; scheduled quietness alone is insufficient.
- Host association/recovery context approximately every five minutes.
- wspr5 captures traffic for the Pico MAC or IP on wlan1, snap length 128,
  maximum 500,000 packets, no ring overwrite. Capture exit/drop counts and actual
  coverage must be checked. Truncated packets do not establish complete payloads.
- Mac BPF access failed outside the sandbox and noninteractive sudo requires a
  password. Its packet capture is explicitly omitted; native DNS/HTTPS and host
  logs run outside the sandbox. This limits cross-host packet attribution.
- JSONL samples are flushed and fsynced locally. A management connection loss
  cannot terminate the wspr5 service. Mac logs are independent of SSH, and a
  bounded caffeinate assertion inhibits idle sleep. Closing the laptop lid or
  power loss may still interrupt Mac coverage.

Private local run directory:
`build/phase11-4-soak/20260910T012256Z/`.
The pointer `build/phase11-4-soak/current.json` records exact paths, timestamps,
source hashes and the Mac supervisor PID. Immutable execution copies are in the
run's `sources/` directory; do not edit these while running.

Private wspr5 directory:
`/home/pi/phase11-4-acceptance/soak-20260910T012256Z/`.
Its system unit is `phase11-4-soak-20260910T012256Z.service`, with a 29,000-second
runtime ceiling and bounded child cleanup. It is transient and does not enable
anything on reboot. The source and evidence directories are owner-only.

Follow-up heartbeat: `review-pico-eight-hour-diagnostic-soak`, every 15 minutes.
It reports meaningful new failures or observer loss and performs the final review
after closure, then pauses itself. It must not launch a replacement run or reset
an unresponsive Pico.

## Review requirements

Retain every failed sample, timeout, boot change and observer interruption.
Separate DNS, TLS/TCP, authoritative state validation, USB and observer failure.
A successful later sample does not remove an earlier failure. Reset/fault INFO
must be preserved before any separately requested recovery action.

Compare application heap, retained TLS allocation and lwIP heap at comparable
quiet states and equivalent positions in the periodic USB/WTP workload. TLS's
persistent server configuration and bounded WTP response caching can retain
allocations; neither all-time peaks nor nonzero retained TLS alone proves a leak.
Report per-window ranges/trends, allocation error deltas, stack high-water marks,
uptime/boot continuity and maximum observation gaps. Record state/configuration
drift, including NTP and network identity, rather than assuming preflight held.

This workload repeatedly opens authenticated connections and polls USB. It does
not reproduce an entirely idle, power-only device or browser JavaScript behavior.
An eight-hour completion marker establishes elapsed execution only. Final USB
identity/ownership/output, host state, capture health and complete evidence review
are required before reporting results. An uninterrupted clean run still would not
prove absence of all memory leaks or repair the historical shutdown watchdog.

## Startup validation and limitations

Python compilation and quiet-window boundary checks pass. Live preflight and
initial scheduled USB/WTP samples pass; the Linux packet capture is listening.
Both supervisors report their workers alive. The initial remote launch command
had a Python quoting error before execution and launched nothing; the corrected
launch succeeded. No failed physical attempt was hidden by that correction.

Current source changes are the observer and this run record. No new firmware
was built or deployed, and no eight-hour outcome is claimed yet.

## Interim finding at 02:49 UTC

The Linux observer recorded HTTPS failures at 02:45:10 UTC (TLS handshake
timeout) and 02:48:47 UTC (timeout without a more specific phase). Native DNS
resolved the expected address in both samples. These are retained failures,
even if later probes succeed.

At this inspection, the Mac had 125 successful scheduled DNS/HTTPS observations
and no failed samples. The USB observer had 964 samples with no reported
identity/output/reset/allocator anomalies, a single unchanged boot ID, and a
maximum sample gap of 5.566 seconds. All observers and the Linux packet capture
remained running. This does not identify the cause or establish absence of a
memory leak. The experiment continues unchanged to preserve later recovery and
the complete eight-hour interval.

## Interim finding at 03:06 UTC

Both hosts subsequently recorded connection resets: Mac at 02:52:44 and
02:53:14 UTC; Linux at 02:52:58 and 02:53:28 UTC. DNS succeeded throughout these
failed samples. USB diagnostics record the clock transitioning from holdover
(178.787-second sync age at 02:52:43) to unsynchronized (183.950 seconds at
02:52:48), then synchronized again by 02:53:44 after a new accepted NTP sample.
The reset cluster overlaps this clock-loss interval. The server's accept and
handshake paths reject an unsynchronized clock in `src/network/pico/server.cpp`;
this is evidence consistent with the clock gate, not evidence of a device reboot.
Exact per-request attribution and the cause of the missed NTP samples remain for
final review. The earlier Linux-only timeouts remain separate failures.

Both hosts subsequently resumed successful HTTPS reads. At the heartbeat,
Linux had four failed network samples total and Mac two; USB had 1,156 samples
without the monitored identity/output/reset/allocator anomalies. All observers
remained alive and the experiment continued unchanged.

## Host and device restart detected at 03:55 UTC

The Linux logs stopped at approximately 03:41 UTC after about 2 hours 15 minutes
of observation. Read-only inspection confirms wspr5 rebooted: its current host
boot ID is `77094c3f-ca60-475d-b6aa-6090f73ba269`, and the transient soak unit is
absent (`LoadState=not-found`). The displayed default `Result=success` for that
missing unit is not a successful soak result. No graceful observer closure or
packet-capture drop statistics were recorded. The previous host journal ends
without a captured orderly shutdown; this alone does not prove a power failure.

Mac logs record network-unreachable/DNS failures beginning at 03:42:08 UTC, then
timeouts, followed by restored DNS and authenticated HTTP status responses from
03:45:45 UTC. Those responses fail the original-boot validator because the Pico
boot has changed to `fce01d70d37fea213202037759ef682c`. These later identity
failures must not be counted as continued inability to establish HTTPS.

A separately logged bounded USB INFO/HELLO/CAPS/STATUS inspection confirms the
same original Pico and inhibited engine, new boot, no recovery-boot indication
or fault-stage breadcrumb, and empty/unowned/inactive output. The original
wspr5 network profile and active, boot-enabled recovery timer are restored by
the host's existing startup behavior. The observer did not restore or alter them.
At this inspection the reboot cause was unknown. The user subsequently confirmed
a brief overnight power outage, resolving this interruption's cause for the
roadmap. Neither Pico was reset by this task.

All stopped Linux evidence was copied into the private local run directory as
`interruption/wspr5-interrupted.tar`; read-only host/USB inspection is preserved
as `interruption/inspection.json`. Linux had 1,571 USB samples without reported
identity/output/reset/allocator anomalies before logging stopped and 205 network
samples with five retained failures. Mac has additional interruption and
changed-boot observations, which remain live until the original deadline.

Do not restart the Linux service or begin another soak. Keep the existing Mac
observer and heartbeat through the original end for final review. Repeated
original-boot validation failures against the same new boot are the known
consequence of this interruption, not a new alert on every heartbeat. A new boot,
new failure class, actual loss of HTTP availability or observer loss still matters.

## Final results

The planned interval ended at 09:26:14 UTC. The Mac workers recorded their
interval-finished markers and the supervisor closed after child cleanup.
The Linux service was not restarted. Final read-only checks after the deadline
confirm the original device, expected revision and inhibited engine, new boot
`fce01d70d37fea213202037759ef682c`, and empty/unowned/inactive state.
Both hosts resolve the expected address and complete authenticated HTTPS status
reads for that new boot. wspr5 is on its original Bohica/wlan1 profile and BSSID,
power save remains on, onboard wlan0 is disconnected, and Wi-Fi recovery is
active and boot-enabled. The installed transmitter service is active; executable
and configuration hashes match preflight. No device or host configuration was
changed by the soak or final checks.

| Evidence | Result |
| --- | --- |
| USB INFO | 1,571 samples from 01:26:15.112 to 03:41:36.088 UTC; 2 h 15 m 20.977 s between first/last samples |
| USB WTP | 131 HELLO/CAPS/STATUS checks, all matching original boot and empty/unowned/inactive state before interruption |
| USB sampling gaps | Maximum 5.566 seconds before the host restart; continuous coverage ends at the interruption |
| Linux DNS | 205/205 successful scheduled observations |
| Linux HTTPS | 200/205 successful original-boot status reads; three timeouts and two connection resets retained |
| Mac DNS | 725/731 successful scheduled observations; six failures during the restart/network interruption |
| Mac HTTPS | 722/731 authenticated status responses: 205 original boot and 517 new boot; nine transport failures retained |
| Mac transport failures | Two resets near clock loss, six failures during the restart/network interruption, and one later TLS handshake timeout at 05:23:19 UTC |
| Original-boot continuity | Failed: host and Pico restarted after about 2 h 15 m; cause unconfirmed |
| Eight-hour memory result | Incomplete; no USB memory measurements after the host restart except separate read-only inspections |

The 517 valid new-boot HTTP responses remain failures of original-boot continuity,
but are not transport failures. The original observer output is preserved; final
analysis separately validates each response against its observed boot and the
full existing status/identity contract. No failed sample was removed or retried
into a passing result. Network sample gaps of up to 154.276 seconds on Linux and
152.670 seconds on Mac include intentional two-minute quiet periods and are not
continuous availability measurements.

### Memory observations

Fourteen scheduled quiet windows provided 156 candidate samples with zero TCP
PCB, segment and packet-pool use, restricted to the latter minute of each
two-minute pause. Initial application-heap median was 19,180 bytes; subsequent
window medians stayed between 22,932 and 22,956 bytes, ending at 22,940 bytes.
Retained TLS allocation was 4,396 bytes and lwIP heap usage 200 bytes throughout
these candidate samples. No sustained growth is apparent after the initial rise
within the available 2 h 15 m observation. The initial rise is retained rather
than silently excluded; its exact allocation provenance was not instrumented.

TLS allocation failures and all four observed lwIP allocation-error counters
remained zero. The final pre-interruption cumulative peaks were application heap
75,916 bytes, TLS 55,928 bytes and core-0 stack usage 7,960 bytes. These are
cumulative diagnostic values, not allocations first caused by this soak.
Sampling does not detect every short-lived peak. USB polling and periodic WTP
sessions remain part of the workload and can affect allocation/cache state.
There is no eight-hour no-leak conclusion, and no inference about the cause of
the simultaneous host/device restart from the absence of prior allocator errors.

### Evidence quality and review

The interrupted packet file contains 5,209 complete plausible packet records
through 03:41:25.830 UTC, followed by 1,638 bytes beginning with an invalid zero
record header. The original file is retained unchanged. The first offline parser
rejected the incomplete tail; review then tightened record length/timestamp checks
so zero-filled bytes are not mistaken for captured packets. The valid prefix is
usable for positive observations; the tail and missing final kernel drop
statistics prevent any full-capture or zero-loss claim. Of the valid records,
1,746 exceed the configured 128-byte captured prefix. Mac packet capture was
unavailable, as recorded at startup.

Reviewed classifications distinguish elapsed completion, lost monitoring,
changed-boot status, clock-gated rejection, transport failures and memory
observations. The original-boot validator intentionally continued to flag the
new boot after the restart; it was not weakened mid-run. The clock-reset cluster
is consistent with the source's time-validity gate; these observations do not
establish why NTP samples were missed or explain the separate handshake timeouts.

Private `analysis.json`, `analyze.py`, `final/` checks and `evidence-index.json`
record the calculations and file hashes in the local run directory. Archived
Linux USB and packet hashes match the final remote files. The Mac observer and
its sleep-prevention child have closed. The heartbeat is paused after final
review. Source artifacts are saved locally; this run did not commit or push.

The next full memory soak still requires a new uninterrupted run. Clock-related
HTTPS availability and the separate handshake timeouts are findings within the
existing connectivity/soak investigation, not new acceptance cases or independent
closure gates. Further investigation of the outage-induced restart is closed by the
user's confirmation and is not a prerequisite for repeating the soak.

## Follow-up host restart investigation

Disposition: **CLOSED — user-confirmed overnight power outage**. The observations
below preserve the investigation before that confirmation; no further diagnosis
of this loss is planned.

Read-only investigation on September 10 confirmed that both the bootloader's
`rsts` property and `vcgencmd get_rsts` report `0x1000`, the power-on-reset bit.
The preceding journal has no recorded reboot/shutdown request, panic, OOM,
watchdog or voltage event in its final 40 minutes. The new boot explicitly reports
an unclean/corrupted journal. No pstore crash record is present. This supports an
abrupt power/reset event, but does not identify the external cause.

The host's runtime watchdog is configured for 60 seconds; its existence alone
does not establish that it fired. The existing Wi-Fi recovery script contains no
reboot/shutdown/poweroff operation. Current PMIC `power_reset` is zero and current
`get_throttled` is zero; these do not rule out a prior interruption that cleared
state. The bootloader reports `max_current=900` mA and
`usb_max_current_enable=0`; these describe the reported power arrangement, not a
measurement of actual supply capacity or proof of the restart cause.

Raspberry Pi's [power-reset documentation](https://www.raspberrypi.com/documentation/computers/configuration.html)
defines the PMIC flags. A Raspberry Pi engineer's
[reset-register explanation](https://forums.raspberrypi.com/viewtopic.php?t=342429)
identifies `0x1000` as a power-on reset and also cautions that firmware-induced
PMIC resets can produce that indication. These machine observations alone did
not prove an AC outage or a particular faulty part. The later user report
supplies the outage confirmation; no faulty component is inferred.
