# INFO formatting lifetime checkpoint

**Phase 11.5 OPEN, 2/6 families closed.** [Result](phase11-5-completion-info-lifetime-result.json).

A's 0001a3625832 image returned three complete maximum LOAD replies under the
native observer. The next replay wrote only 49,152 of 52,105 bytes before INFO's
resource gate stopped it. The active replay decoder therefore did not receive
that complete request; its target acceptance remains open. Native traffic
contains 23 complete STATUS replies on one connection. No RF occurred.

The failed peak is 187,304 of 218,984 heap bytes: 31,680 bytes of headroom against
the unchanged 32,768-byte gate. Before the last INFO formatting pass, allocated
heap was 177,488 bytes. The snapshot partway through formatting reports 183,640
live bytes and a peak of 187,304. Source review identifies overlap between the
6 KiB outer INFO string and the network formatter's temporary strings. This is
an allocation-lifetime diagnosis; the exact historical allocation instruction
was not instrumented.

The repair builds the network snapshot before allocating the outer INFO buffer,
appends it without another concatenation, then frees it before later diagnostics.
Fields, framing, polling rates, reserve and advertised limits remain unchanged.
Its target benefit remains unmeasured until a fresh affected packet passes.

The first cleanup repair successfully sent one physical ABORT followed by one
HELLO/CLAIM/RELEASE sequence. A separate final candidate resource gate then
prevented reservation release despite inactive final inventories. That check is
now evaluated after identity, configuration and both-board authority reconciliation
releases the reservation. Failure still marks the packet FAILED. Eight offline
reservation/cleanup tests pass, including a failed peak that permits release and
changed boot, active output or enabled scheduling that prohibits it.

Fresh raw inventories independently reconciled this failed packet and released
its original reservation without extra mutation commands. Both boards are Empty,
inactive, unowned and scheduling disabled, with preserved configurations. The
new fixture remains active within its fixed one-hour window and independently
supervised cleanup allowance. No restoration is claimed for that active session.
A retains boot 6213cc6b8d7694082fb804fdf5b121fc; B is unchanged. Task charges are
four A flashes/BOOTSEL transitions, three RF jobs / 384 planned seconds, two
Wi-Fi cycles and zero configuration writes.

Independent local auditing preserves the partial replay and failure. Two private
audit tests pass and reject altered reply bytes, peak summaries and reservation
identity. The success auditor's missing import was repaired before further use;
no success had been claimed from that auditor. Review found no remaining source
issue in this small lifetime/cleanup change. Exact candidate builds and the same
finite three-LOAD/replay target check are required next; no family closes here.

Automatic review rejected capture retrieval because authenticated traffic could
be sensitive. The user then explicitly authorized authenticated laboratory traffic
and payload retrieval. The named files were retrieved under that authorization,
with standalone credentials/INI contents excluded and all captures kept out of Git.
