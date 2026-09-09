# Phase 11.4 packet-boundary investigation

The new trace narrowed a failed ARP exchange to loss after successful Pico
linkoutput submission, and reproduced the watchdog in the station-disable
section. Neither result establishes the internal radio/AP cause or a completed
firmware repair. B2/D2 remain open. The campaign stopped at the observed watchdog
failure point rather than continuing link cycles or changing the host SSID.

## Implementation and identity

The [execution prompt](phase11-4-packet-trace-prompt.md) starts from clean Pico
`devel` at `7cbf6387f2be1ddf7ffc92aa05e9fed39ecfde3f`. Changes belong only to this
repository. Pinned SDK/CYW43/lwIP sources remain unmodified.

A project-owned `NetTrace` wraps the station's actual `input` and `linkoutput`
callbacks. It forwards each call once, preserves results and pbuf ownership,
records RX before ownership transfer and records the actual TX return. The
callback path uses fixed arrays, no allocation/printf, and bounds packet inspection
to 1,518 bytes. The 256-record ring retains Ethernet/ARP metadata, IPv4 and
transport header fields, a noncryptographic mDNS payload fingerprint, sequence,
generation, interface, monotonic start/end time and result. Other application
payloads and credentials are not retained. A driver success remains submission,
not proof of a radio transmission or remote receipt. RX means arrival at the lwIP
input boundary; the trace cannot observe earlier driver drops.

The standard inhibited image exposes `NETTRACE <after-sequence>` on Console.
Responses carry device, revision and boot identity and up to eight records.
Reads are non-destructive, making repeated reads safe after a lost response.
`oldest`, `latest`, `overwritten`, hook integrity and installation errors expose
coverage limitations. Initial pre-observer overwrite is retained; gaps during
the measured interval invalidate absence claims. Lifecycle codes are 1 install,
2 before goodbye, 3 after goodbye, 4 before station disable and 5 after disable.
The standard application's primary stack remains 16 KiB. Tracing is excluded
from the separately linked physical RF image; symbol inspection confirms this.

The coordinator/target support an explicit candidate revision and optional trace
collection under the Console lock, independent of blocking DNS/TLS work. The
new read-only `--diagnose` mode allows captures when a client baseline already
fails; it performs no WIFI OFF/ON and cannot earn a B2/D2 pass. A separate offline
auditor validates complete cursor sequences, hook/identity metadata, and compares
mDNS fingerprint plus packet header and length. ARP correlation additionally
matches exact request bytes, timing and reply addresses against Linux capture.

Deployed standard inhibited UF2 SHA-256:
`0483dbee2063b57c0f2564d991a3bbf2f465e24d48daae57fe2daed3143edb3c`.
Revision is `7cbf6387f2be-dirty`; exact source inputs and image are privately
retained. Deployment used only serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, engine `inhibited-standalone-simulator`,
MAC `88:a2:9e:0a:60:df`, hostname `wsprrypico-0a60df.local`, port 18443 and
address `192.168.1.47`. Existing CA/server/operator credentials were reused.
No journal erase, schedule enablement, jobs, GPIO or RF operation occurred.

## Retained physical attempts

| Attempt | Outcome | Evidence |
| --- | --- | --- |
| Post-flash campaign 1 | Baseline failure; no cycle dispatched | Mac native DNS and direct-address authenticated HTTPS could not reach the Pico; no WIFI command |
| Read-only startup diagnostic | Failed ARP/TCP/NSS observations; later recovery | Three broadcast probes got zero replies; three explicit unicast probes followed; USB and NTP continued |
| Campaign 2, first orderly cycle | Watchdog after WIFI OFF | Goodbye captured and native Mac removal observed; new recovery boot records stage 16; no completed 150-second cycle |

### ARP failure boundary

The read-only diagnostic ran on boot `12f96bd25115d4b1ce8a4868a2c01c3a` with the
Mac and wspr5 on Bohica and the Pico on Bohica-IoT. The host stayed on USB wlan1,
original profile `921301fe-cdfd-4965-8ac7-c96e9d908ea6`, BSSID
`6c:cd:d6:f2:f6:c6`, address `.117`, with its recovery timer active/enabled.
The independent Console observer recorded 190 INFO samples; its largest active
sampling gap was 0.433 seconds. Both Linux captures reported zero kernel drops.
The diagnostic is retained as failed observations, not an acceptance pass.

At 23:45:45.611607 UTC the bounded broadcast probe window began. Linux captured
three broadcast ARP requests and reported zero responses. Trace sequence 727
records one matching request reaching Pico input at device time 217,393,179 us.
Sequence 728 records the correct unicast ARP reply addressed to wspr5, submitted
112 us later, with linkoutput returning success after 83 us. No matching reply
appears in the client capture during that probe window. USB-to-Linux clock
alignment spread was 1.150 ms, below the auditor's 100 ms bound. Exact request
bytes, reply addresses, timing and original PCAP are retained in private evidence.

This exchange therefore passed the Pico's ARP reply generation and driver
submission boundary. The remaining delivery path includes radio firmware,
over-air/mesh/AP forwarding and client reception. This does not prove which
component lost the reply. The three unicast diagnostic requests were also
captured at Linux; they did not establish working connectivity. Accepted NTP
increased from four to five during this same boot. Linux NSS initially failed,
then HTTPS and cleanup DNS/HTTPS succeeded without a Pico reset or WIFI cycle.
Later recovery does not erase the earlier failed exchange.

### Watchdog boundary and goodbye evidence

The next campaign began with positive Mac/Linux baselines. WIFI OFF was issued
on the same trace boot. Sequence 1259 records a 132-byte multicast mDNS packet
between the before/after-goodbye markers. The driver returned success in 185 us.
Its fingerprint `3870990583`, complete recorded header and length match the
Linux-captured goodbye. Native Mac removal occurred at 23:47:26.988 UTC. Thus
this attempt delivered the goodbye; it does not close the earlier intermittent
missing-goodbye failures.

USB stopped responding during subsequent shutdown. The watchdog rebooted into
recovery boot `f992163507d5f231b9467426a70b4868`, retaining stage **16**, with zero
fault PC/hash/status. That marker follows final mDNS removal and precedes
`cyw43_arch_disable_sta_mode()`; stage 17 would follow its return. The new ring
append between marker and call is bounded, but its final records were lost on
reset. The evidence localizes the stall to this station-disable section, not to
an individual instruction inside the SDK. Source review shows the SDK operation
performs netif deinitialization and may then issue radio disassociation. Further
breadcrumbs around those boundaries are needed to distinguish them. No change
to watchdog timing or speculative driver workaround was made.

The failed attempt contains 31 INFO samples, 14 raw WTP frames, six mDNS and
24 diagnostic packets. Both captures report zero kernel drops; the largest
pre-fault independent USB gap is 0.423 seconds. No sampled TLS or pool allocation
error precedes the reset. Trace has 287 consecutive records, sequences 976–1262;
there is no post-reset recovery trace for the old boot. This is partial target
failure evidence, never a completed B2/D2 cycle.

## Adversarial review and corrections

The first new trace auditor expected every cycle to contain station-disable and
re-enable records. It consequently called the real watchdog interruption an
observer failure. The original assessment is preserved. The auditor now permits
partial lifecycle evidence only with a recorded case failure and USB interruption,
and makes missing recovery explicit. Reassessment preserves the independently
identity-bound stage-16 watchdog finding. No retry replaces the failed attempt.

The review also strengthened mDNS matching from fingerprint alone to fingerprint,
header and length, and added a bounded read-only diagnostic path after the first
Mac baseline failure. Neither changes target firmware or retroactively creates
missing baseline/cycle evidence. Final firmware inputs still match the deployed
candidate; later changes affect tests, audit/reporting and harness support only.

Validation completed:

- All 28 configured host tests pass, including pinned lwIP lifecycle/responder,
  trace ownership/forwarding/recreation/wrap, harness and evidence-refusal tests.
- Address/undefined-behavior sanitizer runs pass for the adapter and trace tests.
  The trace test additionally exercises 1–1,518-byte malformed chained packets.
- Five corruptions of real ARP evidence are refused: wrong identity, removed
  sequence, bad clock alignment, wrong reply MAC and missing request capture.
  A simulated driver error remains an error; the watchdog record remains partial.
- Exact standard inhibited ELF/UF2 checks pass for stack/heap separation and
  reserved journals/boot sector. The physical RF target links with no NetTrace
  symbols; it was not deployed or executed.

## Final state and remaining work

After saving the watchdog and authoritative WTP identity/output evidence, one
bounded Console reboot restored normal inhibited boot
`76171daf67c246e22b66441a30294936` on the same diagnostic image. Saved station,
schedules, watermark, expiry and healthy journals are preserved; schedules remain
disabled, and authoritative status is empty/inactive/unowned. Recovery suspension
was volatile and cleared on normal boot. Final native Mac and Linux DNS and
certificate/hostname-verified HTTPS pass. No test capture/controller remains.
The original wspr5 USB Wi-Fi profile, power setting and active boot-enabled
recovery remain intact, as do its installed transmitter binary/configuration
and disabled provider output.

| Item | Remaining work |
| --- | --- |
| B2/D2 | Diagnose station-disable internals; repair a supported cause and repeat complete acceptance cycles |
| LAN delivery loss | Distinguish radio/AP/mesh/client loss after successful reply submission; controlled same-SSID or over-air capture remains useful |
| Missing goodbye | Retain earlier intermittent failures; this new goodbye success is one attempt |
| Memory stability | No sustained leak established; an overnight soak after a repair remains unexecuted |
| Other Phase 11.4 gates | D1 actual DHCP reassignment and E1 second-board identity/trust remain separate |

The predeclared failure-point stop was reached. No same-SSID move or overnight
soak was performed after the watchdog; repeating the same shutdown or calling a
short diagnostic a soak would not establish a repair. Private captures, logs,
source/image bundles and replay inputs are indexed by
[the evidence manifest](phase11-4-packet-trace-evidence.json).
