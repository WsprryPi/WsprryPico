# Phase 11.4 C4 deferred network-change acceptance

The remaining C4 transaction cases passed on the inhibited Pico on 2026-09-09:
a response reset before its complete ACK canceled the pending Wi-Fi change,
a newly acquired USB owner canceled it at the final idle check, and the same
change applied while idle after the covering ACK. An unrelated HTTPS close did
not complete the pending transaction. Final packet captures had zero kernel
capture drops and were independently checked against USB state.

C4's bounded transaction scope is complete. The final apply run encountered the
previously observed connectivity problem after WIFI ON: USB showed restored
Wi-Fi and inactive/unowned state, but Linux and Mac TCP connections timed out.
One additional bounded Console Wi-Fi cycle restored authenticated HTTPS on both
clients without reboot. That failure remains evidence; intermittent connectivity
is not resolved or qualified by C4.

The [execution prompt](phase11-4-c4-prompt.md) was prepared and executed under the
user's existing test, USB, Pico Wi-Fi and Pico-related capture grants. The
[joint matrix](phase11-4-plan.md) changes only C4. No runtime source repair was
needed; the changes in this continuation are evidence and documentation.

## Identity and scope

- Pico 2 W / RP2350 on wspr5, serial `0BF4B4AEC9FFB344`, full WTP device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, Console `-if00`, WTP `-if02`.
- Installed standard runtime `23ac5b1aee66`, engine
  `inhibited-standalone-simulator`, normal boot
  `1c4730e38aa4e6f8549cbc8c475846bd`, unchanged throughout all attempts/recovery.
  Deployment identity matched and storage remained healthy.
- Git base `d1db0f0` is later documentation; the prior deployed source-input
  manifest still matches runtime sources. Deployed UF2 provenance SHA-256:
  `a7013feccf36abb9c9da17db057d4d12158942a019d74d787f56336f64a6c8f2`.
  No flash or new image readback occurred.
- Linux source address `192.168.1.117`, interface `wlan1`; fresh USB-reported Pico
  address `192.168.1.47`, TCP port 18443. Expected DNS identity and HTTP authority:
  `wsprrypico-0a60df.local:18443`. Existing controller credentials authenticated
  the direct Linux TLS tests; the existing separate browser identity authenticated
  the final Mac read. No trust bypass/import, proxy or certificate change.
- TLS 1.3 with ALPN `http/1.1`; server certificate SHA-256:
  `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
- Six Wi-Fi-off PUTs total, two per transaction case. Every PUT used a fresh ETag
  and was sent once. Two apply cases actually disabled Wi-Fi; cancellation and
  ownership-race cases did not. Recovery included one additional Console off/on.
  Two temporary USB leases were explicitly released. No LOAD/ARM/RF job, clock
  write, saved configuration write, reboot, GPIO operation, router/firewall
  configuration, package installation or installed-service change occurred.

## Physical ACK mechanism

The existing Linux socket-filter facility allowed a filter on only the temporary
TCP socket. A second AF_PACKET socket captured only that connection's exact
four-tuple. The authenticated TLS MemoryBIO consumed ordered captured ciphertext;
it did not modify packets or manufacture a server response. Socket filters are
local to their sockets and are removed on close. See the
[Linux kernel socket-filter documentation](https://kernel.org/doc/html/latest/networking/filter.html).

An initial all-packet hold revealed that the peer required prefix ACKs to send
later response chunks. The corrected helper allowed ACKs for already authenticated
incomplete prefixes, while withholding the segment completing the HTTP response.
Thus reading the complete plaintext did not imply the kernel had acknowledged
all response bytes. Packet sequence evidence, not the client read or its exit
code, supplied that oracle. TCP_NODELAY on the test socket ensured its HTTP
request was not held behind the deliberately unacknowledged final handshake data.

The read-only GET control passed before any PUT. Final mutation captures recorded
kernel receive timestamps, all matched packets and zero drops; independent PCAP
parsing and tcpdump agreed with the recorded sequence/ACK fields. Held intervals
from filter attachment to reset/detach were 3.003 s (cancel), 1.845 s (owner race)
and 1.761 s (apply), within the server's HTTP lifetime. There was no sequence wrap
in these bounded flows. These are direct physical TLS/USB observations, not
Chrome interaction or a production-client invocation.

## Final transaction evidence

All times below are UTC. Every held response was HTTP 200 with complete
Content-Length-delimited JSON, `enabled:true`, `requested_enabled:false` and a
new ETag. USB independently confirmed the same pending state before reset/detach.
The consumed transaction revision was not rolled back after cancellation;
unchanged saved settings do not imply unchanged ETag.

| Case | Wire and USB observation |
| --- | --- |
| Reset before complete ACK | Client port 46367. At 14:33:55.744, the captured encrypted response suffix ended at server sequence 39006. The kernel acknowledged only the incomplete prefix through 38212. An unrelated authenticated GET/close left the original change pending. At 14:33:56.965733, client RST carried ACK 38212, still short of 39006; no covering ACK appeared. At 14:33:57.106, USB showed Wi-Fi enabled and pending cleared. Final capture: 26 packets, zero drops. |
| Idle recheck after new owner | Client port 55721, encrypted response-suffix end 44797. At 14:34:35.554, USB CLAIM acquired owner `5140e76544ba4ad783c92da863327f5b`, verified with inactive output and no job. The filter detached only afterward. Wire ACK 44797 arrived at 14:34:37.037227; USB then showed pending cleared while Wi-Fi stayed enabled. RELEASE followed that observation, not before it. Final capture: 34 packets, zero drops. |
| Apply after covering ACK | Client port 46335. At 14:36:09.635, the response-containing suffix through 49170 was fully received but not completely acknowledged; USB still showed enabled/pending. After filter detach, wire ACK 49170 appeared at 14:36:11.144241. At 14:36:11.284, USB showed `enabled:false`, empty advertised hostname and no pending request. This proves observed disable independently of the subsequent network disconnect. Final capture: 30 packets, zero drops. |

No early application was inferred from packet loss or connection closure. The
cancel case's reset did not carry a complete-response ACK. The owner-race lease
spanned ACK delivery and cancellation. The apply case retained pending state
before the ACK and observed actual disable afterward. This does not independently
qualify every FIN/reset ordering or the exclusion of TLS close-notify bytes;
those additional orderings remain covered by the existing deterministic TLS tests.

## Original attempts, findings and adversarial assessments

**Preparation and read-only controls.** Existing iptables/nft tools were absent;
no installation or global filtering was attempted. Two initial USB preconditions
failed with session mismatch and then HELLO timeout before network mutation.
No concurrent USB user was found. Draining pre-HELLO input alone did not repair
it; explicit DTR low/high reestablished the reference connection. The helper now
clears DTR on all exit paths and retains pre-HELLO bytes without discarding
mismatched responses after a request. The original mismatch's exact cause is not
claimed proven.

The third control held the final TLS-handshake ACK; Nagle delayed the short GET.
TCP_NODELAY corrected that socket behavior. The fourth reached a partial HTTP
response but withholding every ACK prevented its remaining chunks. Permitting
only incomplete-prefix ACKs corrected the harness. The fifth read-only control
passed. All four failed controls remain separate from accepted mutations.

**Round 1 — implementation and first physical cases.** Reviewed
[server ACK accounting](../../src/network/pico/server.cpp),
[transaction ownership and idle recheck](../../src/network/api.hpp), and actual
adapter pending-state handling. First cancel/race/apply runs passed. Review found
an evidence gap: the helper did not record capture-drop statistics, so absence of
a captured ACK was insufficiently audited. Added mandatory kernel statistics,
required zero drops and equality of kernel/recorded packet counts, then repeated
all three physical cases. No runtime code or test threshold was weakened.

**Round 2 — independent trace and cleanup review.** Independently parsed the
final PCAPs, compared every packet with the structured trace and tcpdump, checked
full response boundaries, absence/presence of covering ACKs, timestamps, same-boot
USB pending/actual states, owner acquisition/release order and zero LOAD/ARM.
The audit initially selected the last pending observation, which could correctly
occur after filter detach while retransmission/ACK delivery was still pending.
Corrected the oracle to require an independently observed pending state before
detach, then verify the transition against the actual wire ACK. The final audit
passed all three transaction cases.

The second apply run's own final HTTPS connect timed out after USB had already
verified WIFI ON, link up and inactive/unowned state. An independent unsandboxed
Mac connect also timed out. Its helper additionally tried to open a response
artifact that had not been created; the follow-up helper now reports the original
connection error directly. These are retained failures, not reclassified passes.
The already recorded transaction was not repeated. One separate bounded Console
Wi-Fi recovery cycle restored both clients, with distinct final read evidence.
The audit explicitly records failed initial HTTPS cleanup and later restoration.

**Final assessment.** No remaining C4 transaction or evidence finding was found.
The known intermittent post-reconnection reachability problem remains open in
[connectivity/reliability work](connectivity-memory-remote-settings.md), with this
new occurrence retained here. No calibrated timing, DHCP reassignment, peer
cache/goodbye reception, unexpected AP loss, general availability, target-resource
or RF claim follows from these results.

## Validation, restoration and retained evidence

Rebuilt `network_tests` and `network_tls_driver`. CTest `network_tests`,
`network_tls_tests` and `network_11_1_interop` passed **3/3**, 33.22 seconds.
Actual TLS tests ran outside sandbox restrictions and sequentially on their
shared loopback port. The existing tests exercise held ACK callbacks, unrelated
closes, disconnect cancellation, ownership races and ACK/FIN/reset ordering;
the physical cases above remain separately identified. No source change required
additional runtime builds or firmware deployment.

Final authenticated Mac HTTPS returned HTTP 200 at 14:39:31.791, and Linux HTTPS
plus USB verification completed at 14:39:38.325. Same boot, empty state, null
owner/job, output false, Wi-Fi enabled, no pending request, synchronized clock,
`pool.ntp.org`, healthy storage, AA0NT/EM18/power20, disabled 120/0 schedules,
expiry zero and watermark `1788714601000000000` were preserved. Existing terminal
records were not cleared. All temporary sockets/filters and USB handles closed;
WsprryPi and its installed service were untouched.

Private artifacts remain ignored under `build/phase11-4-c4/`: all eleven primary
attempt directories, packet captures, request/response/USB logs, helpers, tests,
source identity and independent audits. Primary archive `remote-evidence.tar.gz`
SHA-256: `62852e9db68992d8a53180742982ae7ce389915a06f8ea46ae736013694bc804`.
Separate successful Linux recovery archive `final-read-evidence.tar.gz` SHA-256:
`6ebfa7444c18090aa02cb1df3633c73c9163e82558cc0c4bcb893d432a610e12`.
Final executed main helper SHA-256:
`4ba54ecfff49caab1a1217637dc0222157822316284a730bcc6198393702fa5d`.
No credentials, captures or generated firmware are committed.

## Documentation Impact

Added this execution/review record and the comprehensive prompt; updated only C4
in the joint matrix. The historical failed `http-wifi-capture-1` GET/capture and
all other phase evidence remain unchanged. No operator control, protocol or
runtime behavior changed, and no companion repository modification is required.
