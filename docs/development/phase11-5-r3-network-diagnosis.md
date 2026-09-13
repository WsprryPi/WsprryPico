# R3 rejoin diagnosis: evidence from both ends

A1g failed network admission before RF. A1h then exposed an additional harness
admission defect before either recovery or RF. Neither failure demonstrates a
firmware timing violation. The original failed assessments remain unchanged.
The approved A1h2 continuation is recorded in
[its packet](phase11-5-r3-retained-a1h2-execution.md); the
[current completion review](phase11-5-r3-completion-review.md) owns its outcome.

## A1g: authentication succeeded at the AP, readiness failed at the DUT

The user approved the prospective observation policy and conditional two Tones.
The frozen packet `e512fac77302ee21f6fe7f9536d5c3215dcd997565770684906d4409cbdb0ed4`
ran at `/home/pi/phase11-5-r3-retained-a1g-20260912`. Neither frozen job was
submitted, no TLS pressure ran and no Wi-Fi OFF/ON occurred. Twenty-five readiness
samples over 126.64 seconds lacked an address and synchronized clock; the final
link status was -3 (BADAUTH). Active AP input matched the retained private input.

The AP's wpa_supplicant journal recorded Pico A connected at host monotonic
210273318878000 ns and completed its four-way handshake at 210273319000000 ns,
before the first failed readiness sample. No DUT disassociation was logged until
210419248119000 ns, during cleanup. This contradicts a simple assertion that
the AP rejected the retained password. It does not isolate a driver, radio-event,
application or IP-layer cause. A later station-table query occurred after AP
cleanup and cannot establish the earlier live association. The original capture
filter included only mDNS/NTP and provides no DHCP evidence.

The pinned source in `src/standalone/pico/adapters.cpp` retries asynchronous joins
at 30-second intervals. The SDK 2.3.1 cyw43-driver checkout
`055d64274b014dd7b1c2fc94d26e8a18face7124`, `src/cyw43_ctrl.c`, can report BADAUTH
from either authentication or supplicant events; its aggregate status does not
identify the event sequence. This source inspection motivates diagnostics and
does not justify a speculative firmware patch.

Archive: 2,088,960 bytes, 145 files, SHA-256
`f98208ab4de6c2859f5d002096666178dd9e56cf63912fff2af902c6b4e8bee7`.
The separately collected 4,955-byte `supplicant-journal.json` has SHA-256
`6b1095c7c30b52596a9772f706b8916d719f716e9ae1d553d1f6bb0a951dfe65`;
it is not part of that archive hash. Both remain under ignored build evidence.
The raw auditor reconstructs all 29 inventories and pins this supplement.

## Terminal expiry is normal target behavior

During A1g, job `d27689688f2f3e519a3836b775b3092b` reached its advertised
3,600-second retention age. Its end timestamp was 4525231417000 ns; its expiry
was 8125231417000 ns on the target clock. The final INFO/GET_CLOCK bracket was
8150461255000–8150556106000 ns, after expiry. Both newer records remained exact.
The target stayed on the same boot, Empty/inactive/unowned with unchanged launch,
DMA, alarm and tail counters. This was normal expiry, not a lost job or RF fault.

`JobService::prune_terminals()` uses inclusive target age. The new shared audit
helper uses target-clock samples bracketing STATUS, advertised capacity and TTL,
exact record contents and newest-first order. It refuses a definitive claim if
expiry falls inside the observation bracket. Starting a new capture never gives
an old record a fresh lifetime. This implements the existing retention contract;
it does not relax an old failed RF acceptance criterion.

## A1h: progress was mistaken for an admission failure

The user explicitly approved one additional idle OFF/ON and two conditional Tones.
A1h packet `e59ee91202eb01622fa0185fb0cb2102612ba428edd2a616eeabd82b799e89a9`
ran at `/home/pi/phase11-5-r3-retained-a1h-20260912`. It performed zero Wi-Fi
commands and zero RF. The seven passive link samples were
`1, -3, -3, -3, -3, -3, 1`; the next recovery admission also sampled JOINING (1).
The harness rejected that transient immediately. This is a confirmed harness
admission defect; the underlying rejoin problem remains unlocalized.

The early AP capture was running before AP activation. Before recovery and before
cleanup, the AP journal showed Pico A's completed handshake and the live station
table reported authorized, authenticated and associated. No DHCP packet was
observed by the offline `tcpdump` read of the early capture. Packet absence alone
does not prove the target sent none; capture-loss statistics were not retained.

All 12 raw inventories reconstruct. The final DUT was Empty/inactive/unowned;
B and host restoration passed. Test configuration remained unchanged. Archive:
1,372,160 bytes, 115 files, SHA-256
`b0428de0daf3a2a6ad47876f77a2e659c4365702655ea890d839e4ec2abbfb23`.

A1h2 adds only a bounded read-only admission wait: at most 30 seconds and 30
samples for JOINING/NOIP. It preserves the original idle BADAUTH/NONET recovery
gates, skips the cycle if connected, and never retries an uncertain command.
A1h's zero-command/zero-RF evidence establishes that the approved one-cycle,
two-Tone allowance remained unused before A1h2. The executed A1h root is immutable.

## A1h2: the permitted cycle restored IP readiness

The early A1h2 capture contains DHCP requests/replies beginning at Unix time
1789267896.773339, after the recovery cycle, followed by ordinary lease renewals.
The AP recorded a new completed handshake; the raw DUT inventory then proved
10.77.15.10 and synchronized time before RF admission. This proves the bounded
recovery worked and that DHCP evidence was captured. It does not prove why the
preceding authenticated association failed to give the DUT an address.

## Review and validation

Adversarial review found and fixed an early-capture check that proved only file
existence; selected diagnostic runs now require the capture service active before
AP activation and after setup. Tests cover capture order, inactive capture,
credential retention, transient states, bounded admission failure, unknown states,
no-command connected success and lost-ACK non-retry. Raw A1g/A1h mutation tests
reject altered authority, boot, counters, AP identities, journal events, terminal
expiry, restoration and incomplete transcripts. The complete test count and
final disposition are in the current completion review.

No firmware or Pi runtime source changed. R3 acceptance requires the full
physical assertions; diagnostics and successful recovery alone cannot close it.
