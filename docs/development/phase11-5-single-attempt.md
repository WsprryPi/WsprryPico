# Single A2/A3 attempt after STATUS diagnostics

Status: **FAILED AND RESTORED**. The complete inhibited A2 matrix passed;
138 MHz conditioning failed production STATUS cadence. Physical A2 and A3
were not run. No RF jobs were submitted. [Exact result and artifact hashes](phase11-5-single-attempt-result.json).

The frozen procedure below remains the record of the single authorized attempt.

The user accepted the proposed single bounded A2/A3 attempt with “Do that.”
This uses a fresh instance of the previously described isolated wspr5 fixture:
wlan0 AP, independent wlan2 client, temporary chrony ACL and paused Wi-Fi
recovery timer. Ethernet management, wlan1, installed WsprryPi and GPSDO settings
remain unchanged. The runtime is 6,600 seconds plus 600 seconds for host cleanup;
this is a two-hour cleanup ceiling, not a two-hour test. Device runtime is
5,100 seconds plus 600 seconds for guarded restoration. No earlier window or
completed attempt is restarted.

The [frozen packet](phase11-5-single-attempt-packet.json) binds firmware
`4058d3a4a95110326006a7db6e37eb4b562a500c`, the 138 MHz physical image with
PIO divider 1 and SRAM rendering, and the 150 MHz inhibited baseline. Physical
132/150 MHz remain untested. No configuration is accepted for Phase 11.6 yet.

Pico A is USB `0BF4B4AEC9FFB344`, initially restored boot
`bbabf4bdffb92c6bb0f04f11929c2262`. Pico B is USB `CDDBF8767C506C07`, boot
`4e2fb851c08b278dd4b977104d2c2aaa`, read-only. The confirmed conducted GP2 path
is 50 ohm, 60 dB attenuation, unfiltered through the existing combiner and SDR.

Use fresh private root `/home/pi/phase11-5-n1z-4058d3a`. Back up and verify A,
then install the exact inhibited candidate and temporary settings. Retain one
N180/USB240 conditioning interval before each image's matched A2 baseline;
these are the existing preparation steps, not additional diagnostic retries.
For each image, run Q360/controller180+USB240/N180+USB240/Q360 and independently
reconstruct the raw USB/native TLS audit before advancing. Only after both
complete A2 families pass, run three finite ten-second 135.5 kHz Tone jobs under
N180/USB240. No extra NETTRACE reads are added. Passive AP/client captures each
have a 4,500-second/100,000-packet ceiling and no additional DUT requests.

Keep all existing gates, including the production STATUS start-gap limit of
2 seconds, browser lateness limit of 1 second, heap/stack reserves and matched
quiet retained-heap limit. At 138 MHz the buffer period is 262144000/69 ns and
the 75-percent refill/service limit is 2,849,391 ns. No waveform, band or clock
sweep is included. Another clock selected during Phase 11.6 requires repeating
the affected 11.5 checks; Phase 13 retains systematic spectral qualification.

Stop at the first failed interval or audit. Preserve every earlier failure;
a passing rerun does not establish the cause or resolution of N1u's STATUS
stall. Restore A's original inhibited UF2 and configuration only after
authoritative safe admission, verify both boards, then restore host networking.
Unknown output, failed state or ambiguous transition blocks device restoration
rather than clearing evidence. Independent host cleanup remains armed.

Acceptance counts and diagnostic/tool repairs are reported separately. The
historical count before this attempt is 2/20, on older firmware. Several later
case helpers remain unimplemented; this attempt does not claim phase closure.


## Outcome and adversarial review

The inhibited 150 MHz baseline completed all four intervals with unchanged boot
`941e0abe32082ef7d303aa15e32b1d83`. Independent reconstruction of raw USB and
native TLS records passed. Quiet allocated memory changed from 16,996 to
17,012 bytes: **+16 bytes**, below the 1,024-byte limit. Controller-only and
combined-load STATUS maximum start gaps were 1.678 and 1.328 seconds.

After the exact physical switch, boot `1567d060c8c59174ab36443700517c2d`,
the single conditioning interval failed the original production cadence gate:
**177 nominal STATUS requests**, below the minimum 178, and a maximum start gap
of **2,684,961,482 ns**, above two seconds. Requests ending `6b` and `6c` bound
the worst gap. The runner stopped at this first failed audit and restored A;
it did not run the physical A2 family, submit an RF job or retry conditioning.
The completed conditioning worker is not a passed conditioning audit.

The physical interval's independent USB audit passed: 240 INFO and 48 each
STATUS/health samples, maximum INFO start gap 1.093 seconds, allocator peak
118,520 bytes and no observed allocation failure. The browser issued all 36
status requests and six each page/style/script requests, all HTTP 200. Maximum
status scheduling lateness was 2.445 ms; maximum request duration was 2.458 s.
The blocked gate is production STATUS cadence, not missing browser traffic.

The AP and client captures contain 7,307 and 7,310 packets, with zero kernel
capture drops. Every AP packet has a matching normalized client packet; three
client packets lack an AP match. On production TCP port 36888, STATUS requests
ending `6b` and `a9` took 2.581 and 2.470 seconds from native write entry to
reply. In each case a Pico ACK already used the sequence after the pending
341-byte reply before that reply's payload first appeared in either capture:

| STATUS suffix | Missing reply sequence | Early server sequence | ACK to first captured reply |
| --- | --- | --- | --- |
| `6b` | 44175 | 44516 | 1.252317 s |
| `a9` | 65317 | 65658 | 1.321845 s |

This is consistent with delayed TCP retransmission recovery. It does not prove
where the original segment was lost or held: no additional device NETTRACE
requests were made. The earlier N1u event remains unattributed. AP-relative
intervals above use a single capture clock; native response durations use the
native monotonic clock. They are not sub-millisecond cross-clock comparisons.

Offline review re-ran the load and USB audits, reproduced both failing cadence
criteria, reconstructed the complete inhibited family and checked browser
counts/deadlines separately because its production audit stops at the earlier
cadence failure. Restoration inventories independently establish A and B as
empty, inactive and unowned, with original configurations. A is back on
`802c91a7b86e-dirty`, boot `5b1ae867c8b6888a7a671b7170d66aba`; B's firmware and
boot are unchanged. The host cleanup journal records no failures, test radios
are down, the namespace is absent, the recovery timer is active and the
installed service remains PID 1957. Cumulative configuration writes are 20.

Preparation passed all 57 host tests in 19.26 seconds. Review retained the
first failure, exact clock identities and unchanged limits, and rejected any
interpretation of the partial matrix as complete A2 or phase acceptance. No
further actionable issue was found in the evidence record; STATUS delivery
remains an unresolved acceptance blocker. No firmware or production behavior
was changed by this attempt.

**Acceptance accounting: zero new full cases closed; historical 2/20 remains.**
Four of the eight planned A2 intervals passed on the inhibited image. All four
physical A2 intervals and A3 remain unrun for this candidate. No physical clock
is accepted. A passing inhibited rerun does not erase N1u or qualify 138 MHz.

The full private archive remains on wspr5; a separate local evidence archive
excludes credential files and firmware backups. Initial archive upload was
rejected by automatic approval review because it included private client keys.
The successful upload excluded credentials and firmware and reused the exact
existing wspr5 copies after hash checks. All archive and supervisor identities
are in the linked result. No private keys, raw captures or generated firmware
are committed.

Documentation Impact: development procedure, result and progress pointers only.
There are no changes to operator workflows, protocol contracts or firmware.
