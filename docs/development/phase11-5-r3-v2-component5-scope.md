# Component 5: bounded target LOAD-reply validation

The user authorized execution of the rendered `R3-G2-LOAD-TARGET-v1` prompt on
2026-09-14, including adversarial review, repairs within scope, reassessment,
commit and push. This is a new one-hour allowance; earlier hardware budgets are
not reused. The last 15 minutes are reserved for cleanup. The clock begins with
the first remote host/device preflight and is not restarted by later stages.

Candidate source: `e256633304e03ab85998fde947360ccbaab6c68e`, built from a clean
detached worktree. Target: Pico A, USB serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, Pico 2 W / RP2350 Arm, GP2 PIO/DMA,
138 MHz, RAM rendering. Pico B receives read-only before/final inventories only.
The existing conducted setup and equipment settings remain unchanged.

The allowance is one candidate, one BOOTSEL, one flash, one E6 retained-job
preparation, one exact C7 primary LOAD, and two replay checks only after a
successful primary response. No ARM or RF execution, additional candidate,
reflash, discretionary reboot, Pico configuration write, Pico Wi-Fi command or
allocation-failure injection is authorized. The new runner permits only HELLO,
STATUS, CLAIM, LOAD, ABORT and RELEASE; independent cleanup may use Console INFO
and ABORT. No failed exchange is retried as a test. Cleanup commands are recorded
separately from test exchanges.

The preserved host fixture had been torn down after C7. Reestablishing the same
temporary AP/client fixture with its retained credentials is necessary for the
specified TLS workload. This uses the existing host-only Fixture implementation
and its separately armed cleanup service. It does not rewrite Pico credentials,
station configuration, schedules or Wi-Fi settings, and does not change the
installed WsprryPi application. Temporary host resources, including the runtime
time.local publication override, are restored within the original allowance.
Permanent host files are hashed and compared. The fixture's 1,200-second runtime
and 600-second restoration maximum fit inside the original absolute deadline.

The fixture uses the existing client namespace and authenticated TLS identities.
The test observer is a bounded Python TLS/WTP client, not the historical native
WsprryPi executable. One persistent TLS 1.3 WTP connection issues read-only
requests at five-second intervals. A second worker sends at most four ordinary
HTTPS status GETs, at least 20 seconds apart, with no overlapping HTTPS requests.
This difference in client implementation is recorded; physical comparability
requires examining actual target TLS allocation as well as connection topology.
No client or traffic is added to obtain a desired allocation number.

The E6 job has 512 alternating 135500/135495-Hz events, 3,600 seconds total and
job ID `c339ee30075d458ccc3047bb3d8f8b18`. LOAD must reply successfully before
ABORT/RELEASE. Wait at least 310 seconds after those exchanges complete, then
verify Empty/inactive/unowned state and exactly that retained Aborted record.

The primary request is byte-identical to the offered C7 LOAD frame: 52,105 bytes,
SHA-256 `e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670`.
It uses the original session, request and job IDs and the 512-event, 128-second
FSKCW job. Seven STATUS exchanges precede CLAIM and LOAD. The five-second total
exchange deadline includes writing the request and receiving its complete reply.
Log actual write counts, raw received bytes, monotonic timestamps and decoded
summaries. Require valid framing/CRC/schema, all identities, exactly 512 expected
adjustments and a 54,916-byte successful response payload.

After primary success, submit one byte-identical replay and one same-job LOAD
with a frozen fresh request ID. Require identical results apart from the fresh
request ID, then verify Loaded/inactive ownership, ABORT and RELEASE. Response
equality alone does not prove the engine preparation count. No ARM follows.

Single-flight Console INFO runs approximately once per second from 30 seconds
before primary LOAD until at least 30 seconds afterward. Record actual TLS
allocation around the exchange and compare with historical C7's 31,384 bytes;
lower or noncomparable pressure limits the result. Preserve sampling gaps and
separate allocator live/peak, sampled mallinfo usage, static memory and TLS costs.
Neither sampled free-space estimates nor a passing exchange establish largest
available blocks or every transient peak. The existing 32-KiB heap reserve and stack guard/usage
thresholds remain unchanged.

Stop new workload on the first unexpected timeout, refusal, disconnect, malformed
response, identity change, allocation failure, stack fault or output discrepancy.
Preserve the failure. Within the cleanup allowance, reconcile state and use
necessary abort/release controls; a disconnect is not proof of inactive output.
No additional physical test is authorized to repair a failed attempt.

The frozen packet, helper hashes, candidate hashes, immutable raw journals and
independent auditor establish the evidence chain. Review the runner and auditor
before deployment, then adversarially review results; fix analysis/tooling defects
and rerun hardware-free checks without silently repeating physical work. Publish
an evidence-bound result and affected source-impact assessment, retaining C7 and
all earlier failures. A pass closes only this exact idle LOAD-reply regression;
Group 2 RF, capacity, timeout, USB-pressure and reclamation gates remain separate.
