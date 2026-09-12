# R1 time.local execution and adversarial review

**R1 CLOSED: 5 of 5 assertions passed. Phase 11.5 remains OPEN: 1 of 6 revised
families closed; the full accepted-configuration list is empty.** The
[result](phase11-5-r1-result.json) binds the raw audits, packet hashes, clocks,
boards, configuration, observer and restoration. No RF job ran.

## Exact scope and assertions

Frozen firmware source is `e20ae8bea2d5237af017dbd5f73bfe9332ce144e`.
The physical resource result covers Pico A USB `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, boot `af7ff450b2d9218c787efdc5c0d40c05`,
138 MHz system/PIO clock, divider 1, RAM renderer and network control listener
port 18443. Inhibited boot `a70c0c290d172d2ccd3a5bf8f71a427d` ran at 150 MHz;
it supplies shared-path regression only. Physical 132/150 MHz remain untested.
R1 alone does not accept this clock for all of Phase 11.5. Phase 11.6 owns
per-band/mode conducted acceptance; Phase 13 owns the systematic clock/band/mode,
filter, spectral and release matrix.

| Assertion | Result | Evidence |
| --- | --- | --- |
| R1.1 layout/instrumentation | PASS | Rehashed all four frozen ELF/UF2 pairs and reused their identity-bound linked layout/hook/guard checks; no firmware rebuild. |
| R1.2 inhibited regression | PASS | N180/USB240, 179 nominal STATUS responses, eight actions/fourteen GETs, synchronized target time.local before admission. |
| R1.3 allocation feasibility/recovery | PASS | Physical warm N180/USB240; idle probes 18,364 success → 218,381 NULL → 18,364 success; exactly one intentional failure, no TLS failure or reset; allocations released. Later demand never exceeded the successful probe. |
| R1.4 same-boot retention | PASS | Q360 → controller180/USB240 → N300/USB360 → Q360. Same physical boot and persistent logical observer session; terminal histories empty. Final heap 16,836 versus 16,844 bytes: −8 bytes, within 1,024. |
| R1.5 measurement cost/stacks | PASS | Raw request deadlines, allocation sampling, stack scan/probe costs, host load and both guards reviewed across all six intervals. All declared service/resource gates coexist with instrumentation. |

The successful probe demonstrates an **18,364-byte lower bound on allocatable
block size**, not an exact largest-block or fragmentation measurement. The
capacity-plus-one failure is intentional and retained. No other allocation
failure occurred. Heap peaks reached 121,780 bytes on the physical image,
leaving at least 96,600 bytes against the required 32,768-byte reserve.
TLS is a subset of the general heap; static lwIP storage is accounted separately.

## Workload and observer evidence

Both N profiles used the frozen initialization, six refreshes and reload:
eight actions and fourteen sequential GETs. No legacy S CSS/JS cadence or
browser configuration write was introduced. Production used source
`6f65d5c7d202569102459ab68d7c9ea079b96f35` and executable SHA-256
`122ed0e4bd752e457419c4df5433c3fca1a4a88677a3db3ebd7e60e783ba5d1c`,
separately verified from the Mac checkout and installed service. Each load
interval used one actual production persistent connection and logical session.

| Interval | USB seconds | Nominal STATUS count | Final allocated bytes | Peak bytes | Allocator sampling / observed time |
| --- | ---: | ---: | ---: | ---: | ---: |
| r1-inhibited | 240 | 179 | 26,408 | 118,544 | 14.316% |
| r1-warm | 240 | 180 | 26,348 | 118,500 | 13.845% |
| r1-quiet-before | 360 | — | 16,844 | 118,500 | 13.622% |
| r1-controller | 240 | 180 | 24,636 | 118,500 | 13.253% |
| r1-normal | 360 | 300 | 21,764 | 121,780 | 13.748% |
| r1-quiet-after | 360 | — | 16,836 | 121,780 | 13.608% |

Physical allocation sampling consumed 13.253–13.845% of each observed interval.
Its maximum single sample/entry costs were 56/153 µs; core-0 scan cost was at
most 124 µs and core-1 probing at most 316 µs. These are overlapping observations,
not independently additive elapsed times or a full CPU profile. Both physical
16 KiB stack allocations retained valid 4 KiB MSPLIM reserves and zero stack
faults. Canary touched extents peaked at 8,248/544 bytes; they are lower bounds,
not exact maximum stack-pointer use. The pinned CYW43 linked frame remains
2,120 bytes. TX credit wait/preservation/timeout counts stayed zero.

The maximum USB round trip was 1.165 seconds, below five seconds. Production
STATUS gaps and native-write-to-response times passed the frozen 2/5-second
limits; HTTPS and complete page actions passed 15/60-second bounds. INFO,
USB STATUS and host-health coverage passed their count and gap requirements.
Maximum observed host one-minute load average was 1.53 and temperature 56.75°C;
load average is not CPU utilization. No host throttling was reported.

The 138 MHz full-block reference remains 3,799,188.406 ns and its 75% deadline
2,849,391 ns. These R1 idle measurements do not qualify refill/launch timing.

## Native time.local admission and retained failures

The permanent wspr5 installation was inspected before mutation. Its files,
chrony/GPSD/Avahi processes, LAN ACL and DHCP-refresh dispatcher were preserved.
A temporary, ownership-checked systemd runtime override restricted the permanent
alias publisher to eth0/wlan1; a separate Avahi entry advertised 10.77.15.1 only
on wlan0. The original publisher was restored after radio teardown. No NAT,
routing, hosts-file alias or synthetic unicast `.local` DNS was introduced.
The Pico saved field was `wifi.ntp_ipv4: "time.local"`.

Before each candidate flash, the independent wlan2 namespace performed native
NSS/Avahi resolution, an mDNS query/response and a fresh matched-origin NTPv4
exchange. Both AP/client captures bind these checks to 10.77.15.1 and normal
leap, stratum 1/PPS replies. AP captures also contain Pico A's own mDNS and
matched NTP exchanges on both candidate boots; target INFO and GET_CLOCK show
resolved time.local and synchronized clocks before workload admission.

Preserved attempts:

1. The [historical DNS result](phase11-5-r1-dns-failure-result.json) and
   [review](phase11-5-r1-dns-failure-review.md) retain both earlier failures and
   their original packets. The old intermittent UDP/53 failure remains unexplained.
2. The [first time.local packet](phase11-5-r1-time-local-packet.json) stopped
   before any device mutation: the wire mDNS query returned 10.77.15.1, but
   `avahi-resolve-host-name` required D-Bus, disabled in the existing client
   namespace. Buffered captures omitted that short exchange; its raw probe
   response is retained and is not credited as complete admission.
3. The [second packet](phase11-5-r1-time-local-b-packet.json) was frozen but
   never launched: its normal-LAN resolver check failed. An initial cleanup
   success snapshot had been followed by alias-resolution failure after radio
   teardown. Refreshing the verified original publisher restored resolution.
4. The [completed packet](phase11-5-r1-time-local-c-packet.json) uses native
   `getent -s mdns4 ahostsv4`, immediate capture delivery and publisher restoration
   after radio teardown. All R1 intervals and final audits passed. The previous
   directories, packet bytes and failures were not overwritten.

A later Mac LAN NTP verification timed out once. Its resolved address and wire
packets were not recorded for that failed request. A subsequent bounded check
resolved 192.168.1.54 and received valid stratum-1/PPS NTP. Delayed wspr5 checks
also passed. This retained timeout remains unlocalized; no loss-free LAN,
GPS-loss fallback, oscillator or SDR frequency-calibration claim is made.

## Bounds and restoration

The original host lifetime began conservatively at 16:30:29 UTC and retained
its 80-minute absolute bound. The completed fixture ran approximately
16:36:30–17:08:49 UTC; it used a shortened 3,819-second host work allowance and
2,400-second device work allowance, each retaining its cleanup reserve. No
deadline was extended. The device sequence and subsequent final read-only
inventories completed within those bounds.

Fresh final reconstructed USB records confirm:

- A: original inhibited `802c91a7b86e-dirty`, boot
  `a4e5c91e63bf3a3e40e8e311d378a076`, empty/inactive/unowned; original configuration
  matches and restoration image SHA-256 remains
  `25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`.
- B: unchanged inhibited `dbf1d86f0885-dirty`, boot
  `feffcd075ab6cb0b74e7e0c2fde6c87f`, empty/inactive/unowned with matching configuration.
- Configuration writes: **26/32**; Wi-Fi OFF/ON: **0/0**; heap probes: **3**.
  Six configuration writes remain; future packets must reserve restoration.
- wlan0/wlan2 returned to their prior disconnected/power states; the namespace,
  AP profile, temporary chrony grant and publisher files were removed. Ethernet,
  wlan1, permanent time.local, GPS/PPS configuration and installed WsprryPi
  PID 1957 were preserved. Native LAN discovery and PPS NTP were checked during
  the fixture and after cleanup, including a delayed verification.

## Validation and adversarial review

- `python3 -m unittest discover -s tests -p 'phase11_5_*tests.py'`: **115 pass**.
- Seven affected CTest groups in a fresh hardware-free build: **all pass**.
  Initial configuration of the old build-host directory failed on expired
  ephemeral test certificates; fresh configuration resolved that test-environment issue.
- Unchanged Pi `python3 src/tests/phase115_production_load_tests.py`: **10 pass**.
- Frozen full raw audit and strengthened local raw audit: **PASS**.
- `python3 scripts/phase11_5_r1_adversarial.py <private-evidence-root>`:
  **16 corruptions rejected**, with intact evidence passing before and after.
  Mutations cover failed/incomplete intervals, false retention/probes, wrong
  image/clock, wrong mDNS/NTP peer/quality, missing client/target packet evidence,
  wrong counts, unrestored host, truncated USB/captures and changed helpers.

Review corrections also normalized offline relative paths, made image/clock
registry checks explicit, checked individual raw USB deadlines and required
host restoration for a successful new runner exit. Final capture parsing now
rejects partial trailing records; only live admission permits an in-progress
append. Legacy execution imports the mDNS helper only when explicitly selected.
Running helper files and
frozen packets were not changed. Final auditors are separately hashed in the
result. No actionable in-scope tooling finding remains; retained network failures
and untested RF families remain explicit.

Reproduce the hardware-free checks with:

```sh
python3 -m unittest discover -s tests -p 'phase11_5_*tests.py'
cmake -S . -B build/phase11-5-r1-time-local/host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
ctest --test-dir build/phase11-5-r1-time-local/host -R 'phase11_5_(r1|time_local|network_fixture|device_fixture|device_management|idle|load)' --output-on-failure
```

The raw auditor and adversarial script take the private completed evidence root;
they perform no device/network actions and require the preserved archive.

Avahi's supported interface-specific publication and native resolver behavior
were checked against its [0.8 entry implementation](https://github.com/avahi/avahi/blob/v0.8/avahi-core/entry.c)
and installed D-Bus interface definitions. The namespace uses its existing
Avahi resolver socket through NSS, preserving its D-Bus-disabled configuration.

## Artifacts and documentation impact

The result identifies the full private archive on wspr5 and filtered local
capture archive by SHA-256. Credentials, firmware and captures stay outside Git.
The durable prompt, distinct packets, current result/review, historical DNS
copies, acceptance ledger, metrics, plan and development index are updated.
No firmware, WTP/browser contract, operator UI or sibling repository was changed.
R2–R6 and per-band/mode RF acceptance remain the next separate gates.
