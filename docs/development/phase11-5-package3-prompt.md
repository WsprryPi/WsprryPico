# Phase 11.5 Package 3 execution prompt

Status at authorization: **READY FOR BOUNDED EXECUTION**. This prompt is a
work package under the accepted `R3-COMPLETE-20260913-v2` standing authority
and the September 15 completion authorization. It does not authorize work in
another repository or expand Phase 11.5 beyond Package 3.

## Objective

Close Package 3, network timeouts and resource recovery, on Pico A's installed
`ca3c5dce40360b7eea2f9c45618232caa68cdbb6` firmware, image SHA-256
`6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59`,
boot `5e0d6bc3e383b8c1cb4b0db9ed636bf5`. Keep Pico B, source
`8921a7008183`, as an unchanged comparator. Begin and end with each board
Empty, inactive and unowned, with scheduling disabled and configuration
preserved.

Package 3 owns these acceptance rows:

1. `2.2c`: activated TLS handshake deadline and authenticated reuse;
2. `2.2d`: acknowledged and deliberately unacknowledged fatal-alert lifetime;
3. `2.2e`: two active slots, one network WTP, pending expiry, excess refusal
   and authenticated reuse;
4. `2.2f`: partial HTTP header/body, stalled HTTP output and recovery;
5. `2.3a`: a drained network-WTP exchange followed by the distinct 30-second
   established-connection inactivity deadline;
6. `2.3b`: an actual incomplete WTP frame followed by the distinct five-second
   frame-input deadline;
7. `2.3c`: a complete, accepted maximum LOAD whose response cannot make output
   progress, followed by the distinct five-second output-progress deadline;
8. `R3.BROWSER-MAX`: retain the already accepted actual-browser 30,000/30,001
   byte, 31/32/33-character, message, progress and cancellation semantics only
   if the current `app.js` bytes are unchanged; complete the affected current
   target page-response and allocation/lifetime check through authenticated
   current-image HTTP pressure.

Package 3 does not own USB parser pressure, USB unread-output pressure,
retained replay/session/terminal capacity, reclamation cycles, R4 authority
loss, R5 network disruption, or R6 autonomy. Keep those rows open.

## Evidence and source review before physical work

1. Read `README.md`, `CONTRACT.md`, `docs/architecture.md`, the development
   baseline, the completion matrix, Package 2 result/review, and the retained
   R3 TLS/transport/browser records.
2. Confirm the installed A/B source, image, boot, configuration and authoritative
   output state with fresh named USB inventories. Confirm the host boot,
   installed WsprryPi process and absence of a competing Phase 11.5 process.
3. Bind the evidence packet to these current-source limits:
   - pending TCP slot: 10,000 ms;
   - activated TLS handshake: 10,000 ms;
   - authenticated HTTP activation: 15,000 ms;
   - established connection without TLS read/write progress: 30,000 ms;
   - failed TLS alert acknowledgement: acknowledgement or 1,000 ms;
   - incomplete WTP frame: 5,000 ms;
   - pending WTP input workspace: 5,000 ms;
   - WTP output without progress: 5,000 ms;
   - browser file input: at most 30,000 bytes.
4. Retain all earlier failures and exact identities. Reuse an earlier component
   only when current source impact is explicitly resolved. A matching disconnect
   alone is never timeout evidence.

## Bounded execution

Use one fresh isolated network fixture with its cleanup timer armed before host
network mutation. Preserve management interfaces. Use the retained controller
and browser credentials only inside the private evidence directory. Do not
publish keys, captures containing credentials, or unsanitized payloads.

### Packet P3-TLS

Run the existing independently observed TLS pressure profile on current A while
two 100-second 135.500 kHz Tone jobs execute. Exercise and score, separately:

- positive authenticated HTTPS;
- missing-certificate fatal alert and authenticated recovery;
- silent activated handshake timeout and authenticated recovery;
- both active slots plus pending/excess behavior and reuse;
- duplicate network-WTP refusal and reuse.

Require current source/image/boot, fresh A/B inventories, a shared durable
two-Pico RF reservation, single-flight Console observation, production native
WTP/HTTPS observation, raw TCP capture without kernel drops, exact target
counters, RF launch epochs, continuous output authority, final A/B authority,
configuration preservation and reservation release.

### Packet P3-HTTP

Run the existing independently observed transport pressure profile on current A
while two 150-second 135.500 kHz Tone jobs execute. Exercise and score,
separately:

- partial header and recovery;
- partial body and recovery;
- pending TCP expiry while an authenticated active slot remains usable;
- stalled authenticated `GET /app.js` output and recovery;
- acknowledged fatal TLS alert and recovery;
- payload-free suppression of the final client flight, the unacknowledged
  alert's bounded lifetime, filter removal and recovery.

Require the same independent RF/native/TCP, final-authority and reservation
evidence as P3-TLS. Verify the current `app.js` source hash against the accepted
browser evidence. If the application bytes differ, do not reuse browser
semantics; schedule a fresh actual-browser subpacket within the remaining RF
budget.

### Packet P3-PROGRESS

Run with zero ARM operations and zero RF. Use authenticated TLS 1.3 with ALPN
`wtp/1`, the current peer-certificate digest, raw request/response bytes and
independent Console INFO observations.

1. For `2.3a`, complete and drain HELLO, then send and receive nothing. Require
   target closure 29.0–33.5 seconds after the last completed exchange, one
   network timeout-counter increment, WTP close reason 3, no output activity,
   and fresh authenticated HELLO/STATUS recovery within 15 seconds.
2. For `2.3b`, complete and drain HELLO, then send exactly eight bytes of an
   otherwise valid STATUS frame. Require closure 4.8–7.5 seconds later, no
   network timeout-counter increment, WTP close reason 4, no response bytes,
   and authenticated recovery within 15 seconds.
3. For `2.3c`, use a small advertised client receive window, complete HELLO and
   CLAIM, send exactly one valid 512-event/128-second LOAD, and perform zero
   application reads of its response. Require the target to reach Loaded,
   close the WTP endpoint 4.8–10 seconds after output stops progressing with
   reason 4 and no network timeout-counter increment, and show no queue-overflow
   or allocation failure. Reconnect with the same authenticated principal and
   session within 15 seconds; STATUS must prove that the LOAD applied once and
   remains Loaded/inactive/owned. ABORT and RELEASE it, then prove
   Empty/inactive/unowned.

The progress packet must independently inventory both boards before and after,
show unchanged RF launch/IRQ counters, and preserve configuration. It may add
the expected aborted terminal record; that record is evidence, not a retained
capacity result.

## Ceilings and stop rules

- Planned RF budget: five jobs and 510 seconds: two 100-second TLS Tones, two
  150-second HTTP Tones, and at most one conditional 10-second browser file job
  only if asset equality cannot support reuse.
- Absolute packet ceilings remain 16 jobs and 14,400 planned RF seconds.
- Planned flashes, BOOTSEL transitions, controlled reboots, configuration
  writes, heap probes and Wi-Fi cycles: zero.
- One conditional Wi-Fi OFF/ON recovery cycle is available only after a recorded
  current-enabled/no-link admission failure. It is not a retry for a failed
  assertion.
- Stop the affected packet on a foreign owner/job, source/boot mismatch, output
  authority loss, observer miss, allocation failure, stack/fault marker,
  unexpected reboot, unremoved network filter, cleanup-timer mismatch or
  unrecoverable final state. Preserve the failure and do not retry it as a pass.
- A TCP FIN, reset, USB disconnect, lost acknowledgement or silent observer does
  not establish inactive RF output. Obtain authoritative INFO/STATUS and, for
  RF packets, continuous independent observation.
- Serialize all A RF packets and shared network-filter changes. B remains an
  unchanged comparator.

## Audit and repair loop

1. Run the deterministic host checks for every changed validator, runner and
   auditor, then all configured host test groups before physical execution.
2. Audit each packet from raw evidence with an offline checker. Reject changed
   packet bytes, source/boot/credential hashes, time intervals, close reasons,
   counters, RF epochs, raw WTP bytes, TCP evidence, final authority, fixture
   cleanup or reservation state.
3. Perform an adversarial source and evidence review. At minimum mutate one
   identity, one interval/reason, one raw request or case ordering, one RF
   authority observation and one final-state assertion. Every mutation must be
   rejected.
4. Fix each actionable finding. Rerun the smallest affected deterministic or
   physical slice, then repeat the adversarial review against intact evidence.
   Do not erase the failed attempt or broaden its credit.
5. Publish a result JSON, a review, the updated matrix and progress table. Mark
   Package 3 complete only if all eight rows above are accepted independently.
   Keep Packages 4–9 and R3 family closure open.

## Completion and repository state

Commit only the reviewed prompt, owned implementation/tests, sanitized result,
review and status updates. Push `devel`, independently compare local HEAD with
`origin/devel`, and report exact checks, physical charges, result identities,
restoration state, remaining open packages and any limitation. Private fixture
credentials, raw captures and device paths remain on the lab host and are
referenced only by hashes and sanitized facts.
