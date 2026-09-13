# R3 B1: remaining HTTP, pending-slot and failed-alert lifetimes

**Executed: FAILED, zero acceptance credit.** Both Tones completed and cleanup
passed. The ACK filter stalled the handshake before the intended fatal alert;
[raw reconstruction](phase11-5-r3-b1-failure-result.json) preserves the cause.
The frozen execution scope below is historical and its RF/recovery allowance is
consumed. This packet implements part of
[the user-requested completion prompt](phase11-5-r3-final-completion-prompt.md).
It cannot close all of R3 by itself. A1h2 remains accepted and immutable.

## Frozen execution scope

Packet SHA-256: `b5359002368fbe2ff4db1dc4b101734f40145887f03ac767e9a01d6634ce7b0b`. Staging archive SHA-256:
`676d8138230feaaeaef5aab5eb85a8aa4dd3c1e020be5df494da8c7f261c3327`; 778,240 bytes, 72
tooling/manifest files plus nine existing private inputs copied within wspr5.
Stager SHA-256: `56c81eaa89abe93d7a1e071042dc053c82d8b88fa75b94e815fb10fad0e26691`.
Fresh root: `/home/pi/phase11-5-r3-transport-b1-20260913`.
The complete machine packet is `build/phase11-5-r3-transport-b1/stage/packet.json`.

Retain the exact source/image/board/boot, installed Pi executable, 138 MHz RAM
renderer, divider 1, GP2, physical wiring and service identities in the completion
prompt. Fresh same-boot admission must prove A inactive, unowned and healthy,
B unchanged, retained configuration and current host identity before setup.

Stage and hash-check the packet. Set up only the existing isolated wlan0 AP/wlan2
client fixture, with owned independent cleanup armed first. Protect eth0/wlan1,
installed WsprryPi, chrony/GPSD/Avahi/permanent time.local, B, GPSDO, SDR and Pi
GPIO4. The fixture has 1,800 seconds plus 600 seconds cleanup; require at least
375 seconds before the observation starts. Preserve the unchanged user-confirmed
60 dB, 50-ohm conducted path. Keep the user's test configuration: zero CONFIG
saves, flashing, reboot and heap probes.

The packet includes **one new idle Wi-Fi OFF/ON cycle at most** if fresh A state
is inactive/unowned, enabled without an address and NONET/BADAUTH. This is a new
B1 allowance, not reuse of A1e/A1h2. Connected skips the cycle. JOINING/NOIP gets
the already reviewed bounded 30-second observation; unknown state, lost ACK or
readiness failure stops dependent work. Record early DHCP/ARP/mDNS/NTP capture,
AP journal/station evidence, exact write-ahead OFF/ON intent and replies. RF needs
10.77.15.10 and a synchronized clock after all admission checks pass.

Run two finite 100-second Tones at 135,500 Hz, 200 seconds total:
`c085bb2b51029e6e15819d225487bc7f` and `86e506329e09ce353abac5c2ab9ce3dc`.
Use the unchanged sole USB observer/owner, ten-second forward ARM, 500 ms maximum
clock uncertainty and twelve total 60-second renewals at most. The second job
requires successful first-job pressure and released inactive authority. This
consumes at most two of the remaining 35 jobs and 200 of 3,923.68 RF seconds.

The installed application remains untouched. The separately staged, pinned
production controller runs RF-off for 300 seconds. Observe INFO every second,
STATUS/health every five seconds, for the full 360 seconds. Preserve the approved
request-start/round-trip policy, 32 KiB heap reserve, both 4 KiB stack guards,
unchanged allocator failure counters, exact DMA/launch/tail and original timing
budgets. Capture all target-port TCP on the isolated client interface, with
start/end clock mapping and zero kernel drops required for acceptance.

## Fourteen pressure/control cases

Job one: positive HTTPS control; partial header and fresh recovery; partial body
and recovery; separate pending-slot expiry and recovery. Job two: positive
control; stalled HTTP reader and recovery; acknowledged fatal alert and recovery;
unacknowledged fatal alert and recovery. Exactly fifteen pressure TCP connections,
eight authenticated HTTPS controls, no retries or extra application operations.

Partial requests remain syntactically incomplete and cannot dispatch a mutation.
They require the target's 15-second activation lifetime, actual target TCP close,
exact timeout-counter increment and fresh authenticated recovery. Pending expiry
holds an established HTTPS connection alongside production WTP, sends no bytes on
the extra pending socket, and requires its separate ten-second target close while
the holder remains open. Admission counters distinguish pending from activated
handshakes. TLS session tickets on the holder are not mistaken for EOF.

The reader requests the pinned `/app.js` asset through verified mTLS, with its TCP
receive window constrained before connecting, then reads no response for sixteen
seconds. Raw capture must show zero-window backpressure. Keep that socket open
through successful fresh HTTPS recovery and the exact one-time timeout increment.
This proves logical slot reclamation while the old reader is stalled. It makes no
claim that client EOF times that reclamation: TCP may queue FIN behind unread data.

Both failed-alert cases require target TLS 1.3 alert 116, the pinned server peer,
and target closure before client closure. A MemoryBIO preserves the raw socket
through the fatal TLS error. Reassemble both directions from TCP capture and match
the client-recorded ciphertext, accounting for retransmission and sequence wrap.

For the unacknowledged case only, after its TCP handshake and before its TLS
handshake, create one unique `r3b1_<nonce>` nftables table **inside the owned
isolated client network namespace**. The sole drop rule matches IPv4 source
10.77.15.2, destination 10.77.15.10, that socket's ephemeral source port, destination
18443, and ACK flags without SYN/FIN/RST/PSH. No global or management rule changes.
Record write-ahead scope, rule text, counters and removal; delete in `finally`,
including when counter capture fails. Namespace cleanup independently removes the
entire owned namespace. No persistent nft configuration changes. Require dropped
ACKs, intact client payload delivery, an unacknowledged target alert, and target
closure approximately one second after the alert's **first** transmission. An
ACKed alert, retransmission timestamp or client close cannot establish this path.
The acknowledged control instead requires an actual ACK and target close under
one second. Both require fresh authenticated recovery within fifteen seconds.

## Review and completion

Before execution, deterministic tests cover old packet isolation, actual A1h2
production-log compatibility, timeout origins, premature/client closure, TCP
backpressure, counter distinctions, ACK/no-ACK, retransmission/sequence wrap,
malformed capture and filter cleanup failure. The nft rule passes check-only
validation using wspr5's existing `/usr/sbin/nft`; no rule was installed in that
validation. No additional tools or credentials were installed/exported.

Any identity, observation, traffic, resource or output-authority failure stops
later injections/jobs. Keep the observer through its original window where
possible. Preserve the failed packet and reconstruct actual output before
attributing firmware, infrastructure, harness or insufficient evidence. Reconcile
only known complete/inactive jobs. Verify final A inactive/unowned, B unchanged,
owned host fixture restored and test configuration retained. Independently audit
raw evidence, mutate acceptance-relevant fields, fix findings and repeat review.
Then continue the remaining capacity, USB, retained-state and reclamation register;
passing B1 alone is not completion of R3.
