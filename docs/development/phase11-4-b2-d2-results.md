# Phase 11.4 B2/D2 execution and adversarial review

The [later repeat and diagnosis](phase11-4-b2-d2-repeat-results.md) reproduces
actual failures and supersedes the current-status conclusions below. This
record retains the earlier attempts and evidence unchanged.

B2/D2 remain **PARTIAL overall**. All three corrected physical cycles passed
peer recovery; two pass the complete independent packet/peer audit. The first
corrected capture missed one required probe. The historical intermittent TCP/NSS
failure was not reproduced or explained. Test defects were repaired without
changing firmware or substituting retries for failed acceptance evidence.

The [execution prompt](phase11-4-b2-d2-prompt.md) addresses Linux NSS discovery
and repeatable orderly Wi-Fi withdrawal/recovery. Execution began on 2026-09-09
from clean Pico devel `f58d303ddc9d8fe8b313df04f888001681f172e5`. Raw logs,
captures and private runners are under `build/phase11-4-b2-d2/`; they contain no
maintained firmware changes. Historical failures remain acceptance evidence.

## Identity and scope

The sole Pico 2 W / RP2350 on wspr5 has USB serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, name
`wsprrypico-0a60df.local` and address `192.168.1.47`. Console INFO and USB
HELLO/CAPS/STATUS identify revision `5ee5bcf93c56-dirty`, matching deployment,
standard `inhibited-standalone-simulator`, healthy storage and boot
`4a21c44244ee0c3885565bfa23e84d37`. This boot predates these tests; the older D3
boot is not substituted for it. Output remained authoritatively inactive,
owner/job absent, schedules disabled and saved station/schedules/watermark
unchanged. No jobs or resets were performed.

The historical deployment UF2 SHA-256 is
`2711a54ba57b7754907a5e20dd84d6920dcb5ffe8524c69b8ff2ae569a0686e4`; ELF is
`f21db5220cd403a2306122e9f121e61a6853ab04e8c1810145440363dc26ed65`.
These are deployment references, not a fresh flash readback. Every authenticated
read checks server SHA-256
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`, existing CA,
TLS 1.3, DNS SAN/SNI and HTTP/1.1, with the existing separate client identity.

Mac `.27`/en0 and Linux `.117`/wlan1 use Bohica; Pico uses Bohica-IoT on the
shared Orbi LAN. Linux runs kernel `6.18.34+rpt-rpi-2712`, Avahi `0.8-16` and
libnss-mdns `0.15.1-4+b1`. NSS order is
`files mdns4_minimal [NOTFOUND=return] dns`. Avahi was active and was the only
observed port-5353 owner after the bounded seed socket closed.

Existing explicit all-tests/USB/Wi-Fi/capture authorization covers these idle
Pico-only WIFI OFF/ON cases. Network operations ran outside the sandbox. The
installed service, router, DHCP reservation table, resolver configuration,
trust, extensions, GPIO and RF were not changed. Linux captured bounded Pico
mDNS and ARP/TCP/DHCP traffic with USB observations locally fsynced. Native Mac
dns-sd callbacks were recorded separately. Mac BPF capture required unavailable
noninteractive sudo privileges; no Mac packet capture is claimed. Receiver
capture loss and traffic lost elsewhere on the mesh are distinct.

## Retained attempts and test repair

The first runner (`orderly-v1.py`) completed case `185630Z`: 150.152 seconds off,
captured A/PTR TTL-zero goodbye, three same-name probes and two announcements,
53 captured packets with zero kernel drops, native Mac Add/Remove/Add and six
completed Linux negative lookups. Linux recovered at the first local-active
sample, 5.410 seconds after enabling; six authenticated recovery reads spanned
31.663 seconds. The original withdrawal audit passes this case.

The second attempt (`190001Z`) stopped at its first outage lookup and restored
Wi-Fi. Its goodbye reached the Linux capture at `19:00:07.713171Z`; the lookup
started at `19:00:08.570591Z`, only 0.857420 seconds later, and returned the
cached `.47` address. Native Mac removal and later re-add were observed.
[RFC 6762 section 10.1](https://www.rfc-editor.org/rfc/rfc6762.html#section-10.1)
allows a one-second grace after receipt of a goodbye. Requiring an immediate
negative from that query was a test defect. The aborted attempt is retained;
it is neither a full outage pass nor evidence of a firmware defect. The corrected
runner starts required negatives at three seconds, continues through 145
seconds and requires the full 150-second outage. It also verifies NSS and
authenticated HTTPS during cleanup, rather than trusting a cleanup label.

The old D2 helper retained an extra SO_REUSEADDR UDP-5353 socket alongside Avahi
throughout the test. The current runner closes its seed socket before measured
NSS calls. This removes possible observer interference, but offline inspection
of the three old captures found no unicast packets; the failed `162818Z` capture
also had no QU questions. Thus the extra socket is **not an established cause**
of the historical direct-IP TCP and NSS failure. Its later spontaneous ARP
recovery preceded another Wi-Fi cycle; that cycle cannot be credited as a fix.

## Corrected series

All three cases retained the same boot, six completed Linux negatives at offsets
3/10/40/80/125/145 seconds, native Mac Add/Remove/Add and six authenticated
Linux recovery checks. No initial peer failure was retried into a pass.

| Remote recorder suffix | Off duration | First local-active sample | Stable authenticated window | Independent packet/peer result |
| --- | --- | --- | --- | --- |
| `190242Z` | 150.15 s | 5.409 s | 31.918 s | PARTIAL: 47 packets, goodbye and announcement present, only two probes captured |
| `190611Z` | 150.151 s | 5.448 s | 33.294 s | PASS: 60 packets, matching A/PTR goodbye, three probes and two announcements |
| `190941Z` | 150.150 s | 5.414 s | 32.022 s | PASS: 45 packets, matching A/PTR goodbye, three probes and two announcements |

Each corrected mDNS capture reported zero kernel drops. That cannot establish
delivery across the radio/mesh path. The pinned responder advances from probing
only after three successful send returns, but an accepted send does not prove
delivery to either client. The incomplete capture is retained without changing
the three-probe requirement or inferring a particular mesh component failed.

## Audit and limits

`scripts/audit_phase11_4_discovery_recovery.py` builds on the existing offline
withdrawal audit. It verifies packet origin/TTL/goodbye/probes, native callbacks,
distributed completed negatives, unchanged identity and saved state, raw decoded
USB response schema/session/request correspondence, per-lookup HTTPS identity,
the original 40-second local recovery bound, at least five successful peer
checks spanning 30 seconds, allocation bounds and explicit peer cleanup.
First failures cannot be hidden by later recovery. The checker does no network
or device I/O. USB JSON is the peer's decoded record, not a retained electrical
USB trace or independent CRC remeasurement.

The source review covered portable mDNS lifecycle, the pinned-lwIP adapter's
callback/timer/retained-packet cleanup, Wi-Fi disable/reconnect and TCP listener/
connection recovery. No evidenced runtime defect was identified. Existing
behavior tests include stale-address link loss, late callbacks, probe deadlines,
150-second simulated loss and 100 adapter recovery cycles. Passing these tests
does not prove physical network delivery or overnight memory stability.

## Adversarial assessment and cleanup

The first assessment found and closed these issues:

- The one-second negative-lookup assertion raced the permitted goodbye grace.
  The original aborted attempt remains recorded and the corrected series ran.
- A cleanup event alone did not establish peer recovery. The runner now checks
  final active name/address, NSS and authenticated HTTPS; the audit requires them.
- Generic WTP numeric validation incorrectly rejected observer epoch nanoseconds.
  Observer JSON now rejects duplicates/non-finite constants while retaining its
  actual numeric domain; decoded WTP messages retain strict WTP validation.
- Runner success could conceal missing packet evidence. Independent auditing
  rejects the incomplete first corrected capture and the matrix remains partial.
- Earlier review text treated ordinary Chrome access as still broken. The user
  restored normal navigation with Anti-tracker enabled; a fresh in-page Refresh
  at 14:14:16 CDT returned current inactive/available/advertised status. No browser
  extension or trust change was made. Automated navigation remains separate.

Twenty altered-evidence cases were rejected against corrected case two, then
all twenty were rerun against corrected case three. They cover hidden first
failure, late recovery, short stability, inflated counts, missing cleanup,
unrestored peers, seed-socket overlap, wrong certificate/HTTP/boot/owner/output,
TLS/pool allocation failures, missing HTTPS, NSS timeout/alternate address,
hidden USB mutation and raw response mismatch. Both complete physical cases
passed the unaltered audit. The repeated assessment found no remaining actionable
defect in the maintained audit/report; the physical limitations above remain open.

Validation: `mdns_tests` and `mdns_lwip_tests` passed; WTP contract validation
passed 23 schema, seven raw-JSON, one framing and eight transition cases. Audit
syntax, altered-evidence refusals and repository whitespace checks passed.

Across the corrected cycles, sampled heap and TLS high-water marks stayed
72,720 and 55,031 bytes, respectively; stack high-water stayed 7,824 bytes.
TLS and network allocator error counts stayed zero. Allocated heap fluctuated;
these samples do not establish absence of leaks. At each last recorded idle
network sample, lwIP heap was 200 bytes with zero used TCP PCBs/segments and
packet-pool entries. The exact observation times and transient allocations are
retained in the private resource summary.

Final Mac native resolution and verified HTTPS passed on the same boot/name/
address. Chrome's existing page refreshed successfully. Linux cleanup reads
passed. All test runners, captures and USB handles completed/closed. Wi-Fi is
enabled, output inactive, owner/job absent and saved settings unchanged. The
installed `wsprrypi.service` remained active, provider output false and binary/
INI SHA-256 unchanged (`c19461bc…` / `e4158b2b…`). No router cleanup or reservation
edit was performed in this slice.

Private evidence and runner versions are bound by the
[artifact hash index](phase11-4-b2-d2-evidence.json). Reproduce an audit with:

```sh
python3 -B scripts/audit_phase11_4_discovery_recovery.py \
  build/phase11-4-b2-d2/b2-d2-orderly-20260909T190941Z \
  build/phase11-4-b2-d2/orderly-20260909T190940Z/mac-dns-sd.jsonl
```

| Remaining item | Required evidence |
| --- | --- |
| B2 / D2 reliability | Capture and explain a recurrence of the historical TCP/NSS failure; retain the incomplete repeat packet capture |
| D1 | Real DHCP address change and same-name/identity recovery; reservation form state and static-IP emulation do not qualify |
| E1 | Two physical boards with independent names, identities and trust rejection |
| Overnight stability | Sustained responsive web/USB operation with bounded resource use; short cycles do not close this gate |
