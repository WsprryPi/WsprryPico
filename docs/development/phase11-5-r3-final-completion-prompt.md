# Complete the remaining R3 physical acceptance register

Execute this prompt in WsprryPico and its WsprryPi companion. The user explicitly
requested rendering, execution, repeated adversarial review and fixes, then
commit/push/report. Preserve the accepted initial A1 subset and every failed
attempt. Do not report a partial tranche as completion of R3.

## Execution update

B1 failed due to an early ACK filter; B2 passed all fourteen transport cases.
C0 then exposed a target allocation panic during idle maximum WTP admission.
A is reconciled Empty/inactive/unowned in recovery boot
`bccea7c09794539c4f64bc22b0e76c56`. Continue source work and review, but no
automatic flash/reboot/retry. A concrete diagnostic image and new approval are
required before dependent target acceptance can resume. See the
[current review](phase11-5-r3-completion-review.md). R3 remains OPEN.

## Verified starting point

Pico checkout: `/Users/lbussy/GitHub/WsprryPico`, clean `devel`,
`79498e96c6334f5bfacf81fdbe573be9ca14d72a`. Pi companion:
`/Users/lbussy/GitHub/WsprryPi`, clean `devel`,
`b83241c7e70aa324f5fa129419eb8b6312b4d8d1`. Read each applicable AGENTS.md and the
Pico README, CONTRACT and architecture. Keep Pi changes to scoped companion
qualification reporting unless a demonstrated client defect requires a separately
reviewed change. Do not modify `Wsprry_Pi_Docs`.

The accepted initial TLS/slot subset is A1h2, 10/10 pressure cases: packet
`474e315dee1d7ba7527105a8c34b572508536224be010d9133ec2aaf8998b0d3`, evidence archive
`6c6c34d81048bdd07a970899dfbff845711d3c52f924d373ae00756785fe63f3`. TLS-VALID and
TLS-SLOW are complete at their recorded scope; TLS-FAIL and SLOT are partial.
R3 is OPEN, Phase 11.5 remains 2/6 families closed, R1 5/5 and R2 7/7.
No complete configuration is accepted. Reuse only unchanged applicable evidence.

Physical source remains `2e43110f05304efdc2ae25c298baa0ef6426955b`, UF2
`7e6e732cc7a9e196609413dfe228781a725ece56bed1b4a99a96d1cc8741baf6`;
138 MHz/divider 1/RAM/listener on, GP2 PIO/DMA. Pico A serial
`0BF4B4AEC9FFB344`, WTP `fd6127d11d6aca42a9905fa3fb1bf1d5`, last boot
`9c5aec394269e0b57ca16d73ad3d12b6`. B serial `CDDBF8767C506C07`, WTP
`29f20b7342051ef947aa56cb9d4fab42`, boot `feffcd075ab6cb0b74e7e0c2fde6c87f`.
The wspr5 boot is `220e53ca-ca95-4206-9581-dbe28aa1eeb8`; installed PID 1957 and
executable SHA `c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`
are protected. Verify current device status before any mutation; the last
recorded state is Empty/inactive/unowned, not a substitute for fresh admission.

## Execution envelope

Keep the user's test configuration: zero CONFIG saves, flashing, reboot or heap
probes. Counts remain 37 saves and six cumulative heap probes. Use the unchanged
user-confirmed 60 dB, 50-ohm conducted wiring: each Pico GP2/GPSDO branch enters
the combiner through 20 dB; output passes through 20+10+10 dB to the SDR. Preserve
B output, GPSDO, receiver settings, filters/cables, Pi GPIO4 and management links.

Use only separately identified finite Tones at 135,500 Hz, each no longer than
110.592 seconds and no more than 162 events. The earlier completion envelope is
40 jobs/4,423.68 seconds including failed attempts. Nine jobs/900 seconds have
already completed in that effort, including failed B1 and passing B2; at most 31 further
jobs/3,523.68 seconds remain.
These ceilings do not authorize arbitrary traffic or an unknown-output recovery.
Each actual packet freezes its smaller job list and budget before execution.

Use the existing isolated wlan0 AP/wlan2 client namespaces and retained private
input; AP/client/DUT are 10.77.15.1/.2/.10. Preserve eth0/wlan1 management,
installed application, chrony/GPSD/Avahi and permanent time.local. Arm independent
owned cleanup before fixture mutation. Maximum declared fixture window is
14,400 seconds plus 600 seconds cleanup, never an implicit timer extension.
No Wi-Fi cycle from A1e/A1h2/B1/B2 remains unused. If a new cycle is needed, include it
explicitly in the concrete recovery packet and resolve authority before it runs.

A failed prerequisite or unknown outcome stops dependent work. Keep observation
until the declared deadline when possible. Never equate socket closure, ACK loss,
lease expiry, ordinary terminal-record expiry or a generic exception with an RF
fault. Reconstruct raw identity, output, exact trigger and consequence before
attributing cause. Preserve failed packets; repairs use a fresh root and nonce.

## Required executable subcases

1. **TLS-FAIL:** complete the distinct fatal-alert acknowledgement and one-second
   unacknowledged-alert lifetime. Retain decrypted client alert identity, exact
   TCP tuple, target counters, packet chronology and fresh authenticated recovery.
   If ACK suppression is necessary, use a named, narrowly scoped rule only inside
   the owned isolated client namespace, with write-ahead ownership and bounded
   removal. Do not confuse client close with the target's bounded failed wait.
2. **SLOT:** keep both active slots occupied by established connections long
   enough for the pending connection's separate ten-second lifetime to expire.
   Prove pending admission/expiry and fresh reuse independently of an activated
   silent handshake. Preserve the previously accepted excess/duplicate paths.
3. **HTTP-PARTIAL:** independently exercise partial headers and partial bodies.
   Measure the 15-second deadline from connection activation, not the last byte.
   Preserve incomplete request bytes and target closure/recovery evidence.
4. **PROGRESS:** stalled HTTP sender and receiver, established WTP inactivity,
   and unread WTP output/backpressure. Distinguish HTTP's 15-second activation,
   transport's 30-second progress, and endpoint/parser five-second mechanisms.
   An earlier mechanism winning cannot establish a later timeout path.
5. **JOB-MAX:** first admit a valid 162-event, 110.592-second same-frequency job
   while idle, then execute it under the declared traffic with exact DMA/launch/
   tail, resource and terminal evidence. The duration cap is global; longer QRSS
   support is separate and must not be silently added to this campaign.
6. **WTP-MAX:** valid 65,536-byte payload and correctly framed 65,537-byte rejection.
   Preserve header length, CRC, complete bytes, parser outcome, response and reuse.
   Successful idle admission is required; BUSY cannot prove supported allocation.
7. **HTTP-MAX:** valid 32,768-byte request body and 32,769-byte transport rejection.
   Distinguish parser allocation from API validity/ownership and the API's expanded
   WTP envelope. Use harmless valid operations where appropriate; no CONFIG writes.
8. **BROWSER-MAX:** actual Chromium execution of the target UI, real 30,000-byte
   file admission and 30,001-byte client rejection. Preserve DOM/UI outcome and
   browser network requests; do not replace the browser check with direct HTTP.
   Render and inspect the UI evidence. Do not change frontend behavior merely to
   make the acceptance test pass.
9. **COMBINED:** freeze supported and deliberately unsupported simultaneous
   allocations before running. A controlled rejection must occur at its intended
   layer, without unknown output, unexpected allocator failure or lost reserves.
10. **USB:** pressure the actual USB parser and unread-output path while a separate
    authoritative owner/observer watches RF. Never open the sole USB endpoint twice
    or use its blocked output as the only source of output authority.
11. **RETAINED:** exercise eight-entry replay LRU, sixteen logical sessions,
    eight terminal records, overflow, ordinary reuse and source-defined expiry.
    Use raw changed/replayed requests to distinguish cache hit, eviction, request-ID
    conflict and expired-session HELLO_REQUIRED. Keep ownership/session principals
    exact. Terminal overflow needs actual finite completions; no aborted job may
    be relabeled complete. Expiry uses target clock/CAPS, not refreshed host age.
12. **RECLAIM:** compare measured allocation/retention costs of the preceding
    paths, select the highest measured resource path, and run three equivalent
    cycles. Match terminal/session/replay cardinality and warm-up, account for
    expiry, and verify resource return within declared tolerances. Include the
    300-second and 3,600-second retention observations where required; elapsed
    time alone is not proof of expiry or equivalent state.

## Engineering, validation and review

Implement helpers in scripts/ and meaningful failure-path tests in tests/. Keep
new packet schemas distinct from consumed packets. Test actual recorded/source
producer shapes, not fabricated outputs that mirror the consumer. Make all
hardware tools opt-in, hash-bound, bounded and write-ahead accounted. Do not
install dependencies incidentally; use available tools or report a concrete gap.

Every pressure interval needs independently reconstructed INFO/STATUS showing
same boot/job/owner/launch epoch and actual Running RF. Keep the user-approved
`request-cadence-and-roundtrip-v1`: INFO starts within two seconds, STATUS within
six, individual reads within five, complete observation and causal bracketing.
Preserve 32 KiB heap reserve, both 4 KiB stack guards, expected failure counters,
2,849,391 ns full-block critical budget and each short predecessor's 25% reserve.

The old 18,364-byte demonstrated request ceiling cannot itself reject a new
advertised-capacity test. Prospectively identify each required larger allocation
from source, prove idle admission and resource reserve, and scope the resulting
measurement to affected assertions. Never relax an executed failure afterward.
Cumulative maxima retain their original epochs and are not sums or per-job maxima.

After each tranche, reconstruct all raw traffic and finite work, then adversarially
mutate raw/summary disagreement, CRC/schema, byte lengths, replay/session IDs,
principals, deadlines, authority/epochs, target counters, cleanup and resource
state equivalence. Fix actionable findings, rerun affected checks, and repeat the
assessment. Fresh hardware evidence is required when a repair invalidates a
physical assertion. No fixed number of attempts substitutes for passing evidence.

Update the machine-readable register with PASS/PARTIAL/NOT_RUN/FAILED and exact
subcase evidence, plus documentation impact and source-change reuse boundaries.
Only close R3 when every mandatory subcase and all three reclamation cycles pass.
Commit and push scoped reviewed changes in each authorized repository to
origin/devel, verify remote parity and clean state, and report completion or the
precise remaining blocker without claiming that preparation is execution.
