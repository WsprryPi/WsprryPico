# Phase 11.4 shutdown instrumentation and delivery-path investigation

The diagnostic image adds verified reset-surviving markers inside station
shutdown. The first active-traffic campaign reproduced the separate ARP delivery
failure without a watchdog reset: three Linux requests reached Pico input and
three correctly addressed replies returned successful driver-submission results,
but none appeared in the Linux capture. This does not establish the loss inside
the radio, AP/mesh or receiving client. No supported firmware root repair has
been established; B2/D2 remain open.

## Scope and deployed identity

The [execution prompt](phase11-4-shutdown-prompt.md) starts from clean `devel`
`677ec7fde2362c36235a0fe66733811427ae3bb7`. All maintained changes belong to
WsprryPico; SDK/CYW43/lwIP remain unmodified. The standard inhibited image links
six forwarding wrappers that temporarily write watchdog scratch register 1 and
restore the enclosing marker on return. Arguments, return values, call order and
ownership are preserved. No allocation or printing occurs in the wrappers.

| Marker | Operation entered |
| --- | --- |
| 20 | CYW43 netif deinitialization |
| 21 | DHCP stop |
| 22 | netif removal |
| 23 | IGMP stop |
| 24 | CYW43 multicast-filter programming |
| 25 | CYW43 radio disassociation |

Markers are active only within station-disable stage 16 or a nested marker.
The existing eight-second watchdog is unchanged. The wrappers are linked only
into the standard inhibited application. The linked-image checker verifies each
actual call interception, not merely wrapper symbol presence; the older image
is correctly rejected. Diagnostic timing may affect intermittence, so a lack of
new resets cannot establish a repair.

Deployed revision: `677ec7fde236-dirty`.
UF2 SHA-256: `b1921701ccffee8ca630cbf719f8328ddfa417c86e707f960ea84148862b79b3`.
ELF SHA-256: `0852892029dc3aff38c18a34237c9518b0aa741a19fafd7cbdb5fc18e061670f`.
Normal boot: `3b1e15c0a2bb7c29cabd31a1b1ab2597`.

Deployment used only Pico serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, engine `inhibited-standalone-simulator`,
MAC `88:a2:9e:0a:60:df`, hostname `wsprrypico-0a60df.local`, IP `192.168.1.47`
and port 18443. Existing certificates, journals, station AA0NT/EM18/20, disabled
120/0 scheduling, expiry zero and watermark `1788714601000000000` were retained.
No jobs, RF/GPIO, router or trust changes occurred. The user reported a second
Pico attached to wspr5 for later E1 during the first active campaign; it was not
opened or programmed. Its presence is an additional peripheral-environment change.
The earlier ARP loss and watchdog already predated that second board.

## Retained attempts

| Attempt | Result | Meaning |
| --- | --- | --- |
| Initial idle cycle | INVALID for full B2/D2 | Actual quiet pre-shutdown trace, successful cycle, but no captured baseline A response |
| Initial active cycle 1 | PASS | Full packet/native-peer/USB and recovery/stability audit passed |
| Initial active cycle 2 | FAIL | Nine failed peer recovery checks; stability bound exceeded; same boot and no watchdog |
| Initial active cycle 3 | INVALID | Cycle completed, but baseline A response absent from capture |
| Corrected-gate idle cycle | FAIL | Quiet interval and baseline packet verified; eight failed recovery checks, no watchdog |
| Corrected-gate normal cycle 1 | PASS | Full B2/D2 audit passed |
| Corrected-gate normal cycle 2 | FAIL | Nine failed recovery checks, no watchdog |
| Corrected-gate normal cycle 3 | PASS | Full B2/D2 audit passed |

The first campaign stopped as `HARNESS_INEFFECTIVE` at the missing-baseline
evidence gate. Neither invalid attempt is retroactively relabeled. The target
runner's pass marker alone is insufficient for acceptance. A revised harness
now verifies the exact Pico A response in the actual capture before WIFI OFF;
it sends one multicast and at most three direct unicast questions within a
bounded preflight. Mac status polling pauses for the idle trial and resumes for
post-cycle observations. The trace auditor requires eight covered seconds without
TCP before describing the pre-shutdown interval as idle.

All eight attempts issued one OFF command and retained the same normal boot.
There are three full passes, three valid failures and two invalid attempts.
Every attempt has a matching captured goodbye; the three valid failures occur
in peer recovery. Both idle windows are trace-confirmed. The later idle failed
probe contains three matched request/reply pairs absent at Linux; the final
normal series' failed probe contains two. All valid failures retain zero sampled
allocation-error counters. Reassessment with the final audit preserves every
original classification.

The eight-attempt investigation bound is exhausted. There is no eight-clean-case
stability result. The nested marker experiment did not reproduce the prior
watchdog and therefore cannot identify its failing internal operation. No
speculative firmware workaround or watchdog extension was applied. The read-only
path experiment adds packet evidence but does not repair the delivery failure.
The planned post-repair eight-hour soak was not started because its repair and
stability prerequisites were not met.

### Reproduced delivery failure

In initial active cycle 2, the Linux probe window began at
`1788999971062657912` epoch ns. Three broadcast requests were captured at Linux
and matched byte-for-byte at Pico input (sequences 1537, 1539, 1541). Replies
1538, 1540, 1542 were correctly addressed to USB wlan1 MAC `90:de:80:47:b9:da`
and address `.117`. They were submitted 124, 119 and 111 microseconds after
receipt; the calls returned zero after 85, 84 and 85 microseconds. No matching
reply was captured at Linux during the failed window. USB/Linux clock alignment
spread was 2.736 ms. Both captures reported zero kernel drops.

The same case delivered its goodbye, including matching fingerprint/header/length,
and completed station shutdown and reactivation. Independent USB observation
continued (1,140 INFO samples, largest active gap 0.600 seconds). Pico heap returned
to 18,964 bytes; no sampled TLS or lwIP pool allocation errors occurred. These are
bounded observations, not an eight-hour leak assessment. Previous missing-goodbye
and stage-16 watchdog failures remain retained in the
[packet-boundary record](phase11-4-packet-trace-results.md).

## Read-only SSID comparison

The independent wspr5 controller performed original Bohica, temporary Bohica-IoT
and restored Bohica observations without a Pico WIFI command or reset. It used
only USB wlan1; onboard wlan0 and the second Pico were untouched. The separate
600-second restoration timer was armed before the 540-second controller. Runtime
Wi-Fi recovery was paused only during IoT association; boot enablement remained.

| Host path | Broadcast ARP replies | Native Linux NSS | Authenticated HTTPS |
| --- | --- | --- | --- |
| Bohica before | 3 of 3 | Both checks succeeded | Both reads succeeded |
| Bohica-IoT | 0 of 3 | Both checks failed | Failed, no route to host |
| Bohica after | 1 of 3; retained loss | Both checks succeeded | Both reads succeeded |

Bohica BSSID was `6c:cd:d6:f2:f6:c6`; IoT BSSID was `42:98:b5:fe:36:a1`.
All per-phase profile/association observations were consistent. The IoT host
retained `.117` and received all three gateway ping replies. The IoT probe's
three ARP requests appear in the Linux capture but none appear at Pico input in
the aligned window, including a 100 ms margin. The Pico received 41 other frames
in that window. Alignment spread was 79.278 ms, below the existing 100 ms bound;
trace sequences were continuous and both captures in every phase reported zero
kernel drops. All 56 concurrent Mac DNS/HTTPS samples succeeded on the same Pico
boot. These facts demonstrate failure on the tested IoT path, not a frozen Pico.
SSID, band/AP association and reassociation are confounded; this single sequential
comparison cannot attribute loss to one component or prove that moving SSIDs fixes it.

NETGEAR documents IoT and guest Wi-Fi as separate configurations, and permits
selecting the IoT radio band. This result must not be reclassified as expected
guest isolation without inspecting the actual configuration. See the
[RBR850/RBS850 manual, Wi-Fi settings](https://www.downloads.netgear.com/files/GDC/RBK852/RBK852_UM_EN.pdf),
pages 53–61. No isolation setting was read or changed in this attempt.

The restored-Bohica phase had 442.277 ms alignment spread, so its precise Pico RX
correlation is unqualified. Its positive native NSS/HTTPS and partial ARP receipt
are independently recorded; no packet-absence claim is made for that phase.

The controller completed all three phases at 00:36:22 UTC and completed its final
configuration restoration at 00:36:37 UTC. Mac-to-wspr5 SSH/ping then failed for
several minutes despite that local restoration result; access was confirmed again
at 00:41:56 UTC and the full local evidence archive was retrieved. A nominal
restoration result is therefore explicitly separate from external reachability.
The original Pico remained accessible from the Mac throughout. A read-only router
status navigation failed authentication; no router settings were applied.

## Adversarial review

The review identified and corrected these issues:

- Missing baseline packet evidence was detected only after otherwise successful
  physical cycles. The revised preflight refuses OFF until the required A record
  has actually been captured; earlier invalid attempts remain invalid.
- Idle absence claims needed explicit coverage. Synthetic TCP insertion and
  shortened real coverage are refused, while the original quiet trace is accepted.
  Idle mode now requires tracing before staging; a performed idle cycle without
  the trace-confirmed quiet interval becomes invalid.
- A reset marker alone could incorrectly label a recorded assertion or HardFault
  as a watchdog stall. Classification now requires the original device/candidate,
  a changed inhibited boot, inactive output and zero fault hash/PC/status.
- The initial quiet sampler incorrectly expected all TLS memory to be released.
  Source review confirms that the listening server retains its configuration,
  certificates and RNG until `PicoServer::stop()`. The corrected sampler requires
  three equal heap/TLS/lwIP samples with zero TCP-PCB, TCP-segment and packet-pool
  use. The first sampler result is retained; neither sampler establishes absence
  of a long-term leak.
- Existing marker 15 is shared by mDNS removal and Wi-Fi connect. Its label now
  preserves that ambiguity instead of claiming that every marker-15 reset occurred
  in mDNS removal. New markers 20–25 remain scoped to station-disable marker 16.
- A read-only IoT comparison must enforce its temporary profile, exact SSID,
  paused runtime recovery and retained reboot enablement. An explicit diagnostic
  override validates these values and is refused in control modes. The expected
  nonzero `systemctl is-active` result for the paused timer is handled explicitly.

The first cross-build failed because the new wrapper omitted its own `<cstdint>`
include, which the host mock had supplied indirectly. The include was added; the
failed build log is retained. The successful deployed source hashes are retained
separately from later harness/audit-only changes.

## Completion record

Final bounded USB inspection confirms revision `677ec7fde236-dirty` and normal
boot `3b1e15c0a2bb7c29cabd31a1b1ab2597`, with matching Console/HELLO identity,
inhibited CAPS and authoritative empty/inactive/unowned STATUS. Saved station,
disabled scheduling, watermark, expiry and healthy journals are unchanged.
The new diagnostic image remains deployed for subsequent investigation.

The corrected quiet sampler records three identical samples: 18,812 application
heap bytes, 4,396 retained TLS bytes and 200 lwIP heap bytes, with zero TCP-PCB,
TCP-segment and packet-pool use. No allocation error was recorded. This is a
stable final resource baseline; it does not establish an eight-hour leak result.
Final native Mac and Linux DNS and certificate/hostname-verified HTTPS succeed.

wspr5 uses original USB wlan1 MAC `90:de:80:47:b9:da`, Bohica profile
`921301fe-cdfd-4965-8ac7-c96e9d908ea6`, original BSSID, address `.117` and power
save on. Runtime recovery is active and enabled at boot. Onboard wlan0 remains
disconnected and untouched; the temporary profile is removed, comparison units
and fallback timer are inactive, and no loop controller remains. Installed
`wsprrypi.service` is active, its exact binary/configuration hashes match the
preflight, and the provider reports output disabled.

Final adversarial reassessment preserves all eight attempt classifications and
their retained evidence. All 30 configured host tests pass; actual wrapper and
adapter sanitizer checks, six linked-call checks, and stack/journal image checks
pass. The previous non-instrumented image is rejected by the call-site checker.
No further actionable code/evidence finding remains in this diagnostic slice.
The unresolved physical faults below are not declared closed by these checks.

| Remaining Phase 11.4 work | Status / next evidence needed |
| --- | --- |
| B2 delivery reliability | OPEN: distinguish radio/AP/mesh/client delivery at the recorded boundaries; map endpoint AP associations and inspect actual IoT configuration |
| D2 shutdown/goodbye reliability | OPEN: historical missing-goodbye and watchdog causes remain unexplained; nested watchdog markers are available for recurrence |
| D1 DHCP change | OPEN: actual new lease/address with unchanged identity and trust remains unexecuted |
| E1 two real boards | NOT RUN: second Pico is now reported available on wspr5; identify/provision it and test independent names and trust separately |
| Memory/connectivity soak | INCOMPLETE: the later diagnostic run collected about 2h15m of USB/memory evidence before a user-confirmed power outage; repeat an uninterrupted eight-hour run. Further outage diagnosis is closed. See [soak results](phase11-4-soak-run.md). |

There are four remaining formal acceptance cases: B2, D1, D2 and E1. The
previously requested soak is incomplete. Clock-related HTTPS failures and
separate handshake timeouts are findings within the existing connectivity/soak
investigation, not additional acceptance cases or independent closure gates.
The user-confirmed power outage requires no further diagnosis.

Private images, source snapshots, captures, failed/invalid attempts, comparison
controller/restoration logs, quiet-sampler correction and final checks are indexed
in [the evidence manifest](phase11-4-shutdown-evidence.json). Raw credentials,
firmware and captures remain outside source control.
