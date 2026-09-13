# R3 A1b HTTP-check failure and retained test baseline

The approved A1b run **failed in the test driver at its first HTTPS check**.
One 100-second Tone completed; the second job was never submitted. No R3
pressure assertion passed. This was another implementation/review failure:
the parser required `HTTP/1.1 200 OK`, while the pinned firmware's actual
`HttpResponse::wire()` emits `HTTP/1.1 200 Response`.

The previous preparation review checked the JSON producers but missed the HTTP
serializer. Its synthetic response fixtures repeated the wrong reason phrase.
The driver also validated before logging the response, so the actual failing
HTTP bytes were lost. The serializer mismatch is reproduced directly from source;
this report does not invent the missing live response or claim its status code
and body were verified. The [machine-readable result](phase11-5-r3-tls-a1b-result.json)
keeps that limitation explicit.

## Executed work and evidence

The user approved [A1b](phase11-5-r3-tls-a1b-execution.md), packet SHA-256
`590da5a47dc37c1d4c8addea4713ca0cfcb25872a3daaff46a4c9abb9702b218`,
using the previously confirmed 60 dB conducted path. Staging verified 70 files.
The prior failed A1 raw audit passed before fixture setup. The frozen A1b source,
packet, pressure trace and failed results are preserved under
`/home/pi/phase11-5-r3-tls-a1b-20260912`; no helper was patched there or replayed.

A received the inhibited candidate, test-network configuration and explicit
reboot, followed by the physical 2e43110 image. Physical boot is
`9c5aec394269e0b57ca16d73ad3d12b6`, at 138 MHz/divider 1/RAM/listener on.
The sole USB actor claimed, loaded and armed job
`91bd2c3d57e3e74f7de183203796f463`: Tone, 135,500 Hz, 100 seconds.

The pressure actor made one TCP connection, recorded a TLS 1.3/http/1.1 handshake
with the pinned peer identity, then failed at HTTP status parsing. No negative
TLS, timeout, slot, duplicate-WTP or recovery case ran. The supervisor stopped
the production load and blocked dependent job submission; no retry or ABORT ran.

Raw WTP events establish Loaded → Armed → Running → Complete, followed by
OWNER_RELEASED with reason `terminal`. The finite engine finished the Tone
despite lease expiry; the expired owner was released after completion. The
observer incorrectly rejected the resulting unowned Complete STATUS and stopped
after **125.137594288 seconds**, short of its required 360-second window.
It recorded 126 INFO, 25 published STATUS and 26 host-health samples; the 26th
STATUS response remains in raw wire/messages even though validation prevented
publishing its snapshot. The second frozen job was never loaded or armed.

The raw failure audit verifies exactly one HELLO, 26 STATUS, one CLAIM, one LOAD,
one GET_CLOCK and one ARM; zero RENEW, RELEASE or ABORT commands. It reconstructs
Console/WTP bytes, binds samples and terminal events, verifies the later raw
inventory and host restoration, and rejects altered evidence. The supervisor's
`completed_jobs=0` describes its uncompleted audited pair; raw evidence separately
establishes **one physical job completed**. Neither count grants acceptance.

The per-job timing checker also reconstructs diagnostic deltas: DMA 26,323,
alarm one, tail one, successor/refill pairs 26,321, final link one, launch epoch
one and reported post-enable delay 8,000 ns. Its short predecessor is 6,736 words
with the existing 25% reserve requirement. These are partial-run diagnostics,
not a substitute for the missing full load/observation and pressure acceptance.

## Cleanup and the user's baseline choice

Host fixture cleanup passed, preserving interfaces/routes, installed WsprryPi
and permanent time.local/chrony/GPS-PPS/Avahi. Pico restoration stopped at its
read-only admission: the helper requires Empty, but the successful job was still
retained as Complete. No restoration CONFIG or final flash occurred.

The user then explicitly chose **“Keep the test configuration”** as the baseline
between future runs. The attempt's identity-checked restoration timer was stopped
and confirmed inactive to prevent a later original-configuration restore. This
is an intentional change of baseline, not a claim that original restoration
succeeded. Cumulative CONFIG saves remain **37**, probes six, Wi-Fi fault cycles
zero. The number is a campaign write count, not a configuration version.

Fresh, raw-audited A/B inventories after that choice establish:

- A remains on physical `2e43110f0530`, boot `9c5aec394269e0b57ca16d73ad3d12b6`,
  **Complete, output inactive, unowned**, with the one completed job retained.
  Schedules are disabled and the test configuration matches its candidate baseline.
- B remains inhibited and unchanged, boot `feffcd075ab6cb0b74e7e0c2fde6c87f`.
- No new RF, CLAIM, RELEASE, CONFIG, reboot or flash was performed during this
  final verification. The physical image and test configuration are left present;
  no original-image restoration is claimed.

The failed-run archive is 3,737,600 bytes, SHA-256
`23f040d37624e5bef9d4fa9161314f47f43a87d300a36f47eb8cce0ccfc2fd77`.
The separate final-retention archive is 81,920 bytes, SHA-256
`19306a3593518f01bc0304967f41dd5cbea7c5237e0d93676cbfc1b6921f75af`.
Both remain in ignored local evidence storage. Private keys, configuration inputs,
firmware and flash backups were excluded from these transfers.

## Repairs, review and checks

The parser now checks HTTP/1.1 and status code 200 while allowing the reason
phrase to vary. It still rejects other codes/protocols, malformed status lines,
duplicate or truncated framing, and incorrect boot/job/owner/output state.
Completed response bytes are recorded before semantic validation, including
responses that fail validation. A checked-in fixture was generated by compiling
the actual unchanged C++ HTTP serializer on the host with a synthetic test body;
its source hash and generating command are recorded. This is source-generated
test data, clearly distinguished from lost live traffic.

The observer now allows an error-free, inactive, unowned Complete record for a
known R3 job **only after the load-failure marker exists**. It can therefore keep
observing to the original deadline. Normal acceptance validation remains strict;
this path does not admit another job, clear terminal state, or convert a failed
run into a pass. Completed terminal cleanup still needs to be planned before the
next execution; this repair does not perform it automatically.

Validation: **178 tests discovered, 176 passed, two unrelated private fixtures
skipped**, with both original A1 and A1b private evidence supplied. Nineteen R3
tooling tests cover the serializer output, status-code mutations, retained failed
HTTP bytes and bounded failed-load terminal observation. Ten mutations of the
actual A1b failure are rejected, and the intact evidence passes again as a failure.
The previous A1 failure's eleven mutations still pass their rejection checks.
Whitespace, JSON, links and unchanged firmware-source checks passed. No new
firmware build, flash or physical rerun validates these Python repairs.

Review traced the failure through parsing, logging, load shutdown, lease expiry,
terminal ownership, observation and restoration admission. The three local
repair points are tested. The remaining terminal cleanup and retained-baseline
fixture lifecycle are explicitly pending rather than hidden by an automatic
recovery or relaxed acceptance gate.

## Remaining work and Documentation Impact

Phase 11.5 remains **OPEN, 2/6 families closed**; R1 5/5 and R2 7/7 are unchanged.
R3 has no accepted physical pressure assertions; R4–R6 and full accepted
configurations remain open. A new execution must reconcile the retained completed
job, verify the test baseline and adapt the fixture lifecycle to retain it. Do not
replay the consumed A1b packet or assume the old original-restoration helpers fit
the user's new baseline choice. Longer QRSS support remains unresolved.

Updated the Pico plan, current ledger/index, this report/result and historical A1b
status notices. The Pi companion update is prepared as
`build/phase11-5-r3-tls-a1b/pi-companion-report.patch` but remains unapplied:
automatic approval review rejected the cross-repository edit, including after
the attached handoff's authorization was cited. Direct confirmation is now
needed for that companion edit and publication. Protocol contracts, firmware, installed
Pi application, UI and separate operator manuals are unchanged. Operator limits
still require accepted measurements; the user excluded `Wsprry_Pi_Docs`.
