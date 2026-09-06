# Standalone physical validation

This record covers the authorized September 6, 2026 Phase 9 bench campaign.
The [execution prompt](step9-physical-execution-prompt.md) defines acceptance.
The user narrowed this turn to Wi-Fi validation and deferred conducted RF and
separate-power operation. Those deferred items do not become passes from
inhibited execution. The bounded Wi-Fi slice passed; final stability and review results follow.

## Device and setup

- Pico 2 W, RP2350 A2, 4 MiB flash; board serial `0BF4B4AEC9FFB344`.
- WTP device identity `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Mac Console `/dev/cu.usbmodem2101`; separate WTP interface `2103`.
- User-confirmed GP2/GND through the existing 60 dB conducted path to wspr5's
  RSP1B, serial `2404058C60`. No antenna or alternate RF route is implied.
- Station `AA0NT EM18 37`; encoded power is not a power measurement.
- Private 2.4 GHz credentials remain in ignored local configuration and device
  flash. Neither credentials nor full flash backups belong in this record.
- `pool.ntp.org` was resolved during provisioning; selected IPv4 `69.89.207.199`.
  The Pico itself performs SNTP. No USB TIME SET/LOAD/ARM establishes its jobs.
- Source baseline `77ecd4b1378a0d8cfc40d8b38a9933a0ca5bef89`, with this work
  performed directly in `devel`. Tested dirty builds require their image hashes;
  the short revision string alone cannot distinguish successive candidates.

## Findings and repairs

The initial full-flash backup showed the final page at `0x3fff00` filled with
`0xef`, matching the RP2350-E10 UF2 workaround. The initial journal layout included
that page. The physical image correctly reported unhealthy storage and rejected
configuration. Journals now occupy `0x3fb000` through `0x3fefff`, with the final
sector separately reserved. Application linking ends below the journals.
The image checker no longer describes the workaround page as untouched.

Review found that merely relocating the old records could lose the newest bank
of a watermark while accepting older records. The corrected journals use
`WWPSTOR2` magic and reject checksum-valid old-layout records. Only the disabled
test record created in this campaign was replaced, after a verified private
backup and comparison with its original erased sector. No pre-existing user
configuration or no-repeat history was erased.

Public pool replies exceeded the original 20 ms uncertainty policy. The user
selected 500 ms, consistent with margin against approximately one-second
[WSPR clock guidance](https://wsjt.sourceforge.io/WSPR_QST_Nov_2010.pdf).
The parser still includes the full measured RTT, server root distance, local
margin and quantization. Admission and launch enforce the same budget including
oscillator aging; neither symbol timing nor frequency calibration was relaxed.

Wi-Fi polling initially stalled after configuration. The watchdog now recovers
into a network-free boot with local scheduling suspended and diagnostic state
retained. The lwIP heap/pool alignment was explicitly set to four bytes, matching
[Raspberry Pi's configuration](https://raw.githubusercontent.com/raspberrypi/pico-examples/master/pico_w/wifi/lwipopts_examples_common.h).
Successful acquisition alone was not accepted as stability evidence: subsequent
polling failures were retained, and the processor diagnostic candidate underwent
longer observation and restart/outage tests.

## Evidence collected so far

- Disabled configuration saved and was retained across software reboot and
  firmware update. Corrected storage reported healthy; output stayed inactive.
- Watchdog recovery was physically observed at network polling stage 13, with
  retained configuration, suspended scheduling and an operational Console.
- Device SNTP accepted samples with approximately 73, 95, 69 and 211 ms estimated
  uncertainty. These are conservative device estimates, not calibrated UTC errors.
- The inhibited candidate completed the 16:22:01 UTC schedule, reacquired time,
  and started the 16:24:01 schedule in the same boot. STOP aborted the second job.
- The next boot retained the 16:24:01 watermark. With Wi-Fi explicitly disabled,
  the 16:26:01 inhibited job started from an adequately recent time sample.
- With Wi-Fi still disabled, the 16:28:01 slot was skipped. At 16:28:36 the
  clock was unsynchronized, with unchanged 16:26:01 watermark and inactive output.
- Restoring Wi-Fi at 16:30:29 yielded synchronized device time by 16:30:39 in
  the same boot, with approximately 112 ms sample uncertainty. A later 16:32:01
  occurrence was reserved, confirming that local admission resumed. STOP then
  cancelled it before launch, and scheduling was persistently disabled.
- Conducted standalone decoding and separate-power operation are deferred by
  the user. No standalone RF image was installed or transmitted during this run.

The final continuous Wi-Fi run lasted 301.238 seconds, from
`2026-09-06T16:32:37.908746+00:00` to `2026-09-06T16:37:39.147093+00:00`, with 11 observations in boot
`91dde2bd9a5d3710ce413c89e20b9ca3`. Link status stayed up and no watchdog recovery
or boot change occurred. SNTP reported 6 queries,
5 accepted replies and 1 rejected reply.
One rejected exchange produced a temporary holdover observation; the next
accepted reply restored synchronized time. The final sample uncertainty was
128.686 ms. Storage remained healthy,
configuration remained disabled and output stayed inactive. The 16:32:01
pre-launch reservation also survived reboot without another attempt.

This is a bounded functional Wi-Fi/SNTP pass on this board and network, not a
long-duration reliability qualification. Early polling stalls were not uniquely
root-caused by a retained processor PC; the final diagnostic image did not
reproduce them. Their recovery observations remain in the evidence rather than
being presented as successful uninterrupted operation.

The processor diagnostic candidate hashes are:

| Image | SHA-256 |
| --- | --- |
| RF-inhibited | `c2ef2e25c535ffd9dc2310f59e1b60454b2db93cddd065d3cef42b8e1a5c5c1c` |
| Standalone RF (built only) | `a832dcf96d8b428f9ba45c484f69e1768f00726856d8828535fbef10b3ae5a2d` |

Private local evidence is retained under `build/step9-physical-evidence/`,
including sanitized timestamped observations, image/source manifests and
separately private flash backups. Raw captures and generated firmware are ignored.

## Checks and review

The expanded host suite passed 19 tests; the sanitizer build passed 15 tests.
The WTP validator passed 23 schema, seven raw JSON, one framing and eight
transition cases. All five maintained Arm targets built; the four UF2 images
passed stack/heap, application extent and journal/boot-sector checks.

New regression coverage includes expiry admission, local STOP and external-owner
isolation, private configuration gates/redaction, checksum-valid legacy-layout
rejection, the 500 ms inclusive boundary, growth beyond that boundary before
launch, and rejection of UF2 writes into reserved journal space. Byte-interruption
testing also accepts a completely valid new watermark when an unwritten trailing
`0xff` byte already matches erased flash; it never permits replay of that record.

The adversarial review repaired the boot-page collision, unsafe interpretation
of old-layout records, missing bounded administration/recovery controls, and
network alignment. A second assessment checked source, image/source manifests,
private-data boundaries, disabled final configuration, time-budget aging,
actual outage/reconnection evidence and deferred acceptance claims. Affected
checks passed again; no further actionable change was identified in that
assessment. Full physical Phase 9 acceptance remains deferred as described above. Calibrated absolute RF onset, spectrum/filter qualification, flash
endurance and destructive brownout fault injection are separate Phase 13 work.
