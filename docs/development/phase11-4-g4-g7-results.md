# Phase 11.4 G4–G7 acceptance results

G4, G5, G6 and G7 pass within the single-board scope below. The
[execution prompt](phase11-4-g4-g7-prompt.md) was executed on 2026-09-09.
No firmware, production application, protocol, SDK, trust-store or UI change
was needed. The acceptance harness and offline evidence audit were corrected
during repeated adversarial assessment. Failed attempts remain preserved.

## Identity and operational boundary

| Item | Tested identity |
| --- | --- |
| Board | Pico 2 W / RP2350, USB serial `0BF4B4AEC9FFB344`, attached to wspr5 |
| WTP device | `fd6127d11d6aca42a9905fa3fb1bf1d5` |
| Firmware | `5ee5bcf93c56-dirty`, reviewed F2/F3/F6 source subsequently committed as `f187555` |
| UF2 SHA-256 | `2711a54ba57b7754907a5e20dd84d6920dcb5ffe8524c69b8ff2ae569a0686e4` |
| ELF SHA-256 | `f21db5220cd403a2306122e9f121e61a6853ab04e8c1810145440363dc26ed65` |
| Engine | `inhibited-standalone-simulator`; no RF-capable image or GPIO action |
| Server identity | `wsprrypico-0a60df.local:18443`, observed IPv4 `192.168.1.47` |
| Server certificate SHA-256 | `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016` |
| Controller leaf SHA-256 | `c615a0f65d94c08bf65a776393f9d72c09f813fe59a1bfb2bd3ef4e6d023b0a1` |
| Production source | Clean isolated wspr5 checkout `923ab570fe53ef2ccca7d12e519c9dc36adf7e93` |
| Production executable SHA-256 | `993ad62def487e5f03d82a5a7a1f5f82b972b16bd36eaa5b0d9a8c13a7166323` |
| Executable | `/home/pi/wsprrypi-browser-coverage-20260909/src/build/bin/wsprrypi-browser-coverage` |
| Initial boot | `c2ed521e566499e42583d2d212540cfa` |
| Intermediate real boot | `462a11ac6d70103f2954fc87832ea534` |
| Final real boot | `cebcd4720cd9919a7cfaff492b717a85` |

The existing production executable was built with GPIO-free ancillary settings
and invoked explicitly with `--backend wtp`. It performed real mTLS/WTP work
against the inhibited Pico. Isolated INIs used QRSS `E`, three-second dot duration,
3,570,100 Hz, approximately 25-second start lead, 500 ms uncertainty budget and
ten-minute repeat interval. Processes ended before any repeat LOAD/ARM. The
real application's singleton policy was preserved: each test paused only the
authorized installed service after checking disabled transmission, boot policy
and the RP1 provider's authoritative `outputEnabled:false`. Restoration ran in
`finally`, with original installed configuration/binary hash comparisons.

## Results and evidence

Private records are under `build/phase11-4-g4-g7/`, indexed by
[SHA-256 manifest](phase11-4-g4-g7-evidence.json). Raw captures, plaintext protocol
audit records, configurations and generated instrumentation remain private.

| Case | Successful evidence directory | Result |
| --- | --- | --- |
| G4, G7 | `g4-g7-direct-20260909T153002Z` | All three lost replies and USB/Console authority checks pass |
| G5 | `g456-production-fault-20260909T153603Z` | DNS/TLS reconnect failures preserve unknown/history; explicit original-session reconciliation succeeds |
| G6 process | `g456-production-restart-20260909T154225Z` | Fresh process/session does not own, cancel or resubmit old work; old job completes |
| G6 device | `g456-production-device-20260909T154315Z` | Authenticated controlled endpoint's different WTP ID latches rejection |
| G6 boot | `g456-production-boot-20260909T154941Z` | Actual reboot changes boot ID; production rejection remains latched |

**G4:** a classic BPF `RET 0` filter was attached only to the particular test
TCP socket immediately before each selected request. An independent Linux
capture of that exact four-tuple recorded the outgoing encrypted request,
server acknowledgement and incoming encrypted response data. The filtered
socket received zero bytes and timed out; the capture audit found no subsequent
client acknowledgement of response data and zero kernel capture drops. This is
response delivery loss at the receiving socket, not disappearance before the
client's network interface and not decrypted packet-capture evidence.

Independent USB STATUS proved LOAD, ARM and ABORT took effect. Each connection
was closed, authenticated again using the original WTP session, reconciled with
STATUS and replayed with the identical request ID and exact original bytes.
All three operations used job `f464e98719c54920af2d7d5c44ac71ec`; Running was
observed before ABORT and exactly one matching aborted terminal record remained.
These are direct WTP tests; G5/G6 separately cover the production application.

**G5:** a private `LD_PRELOAD` observer recorded accepted OpenSSL plaintext I/O
without changing the production executable. A file-triggered shutdown affected
only its socket to the Pico after acknowledged ARM. The real runtime became
blocked, cleared live job/remote observations to JSON null, retained its original
job/session and failed report, and required explicit recovery. Its `uncertain`
request flag is not used as a substitute for the missing output observation.

The resolver fault returned `EAI_AGAIN` at this process's `getaddrinfo` boundary.
It tests production resolver-failure handling; it does not claim a real LAN DNS
outage. The TLS fault changed only this process's expected verification name to
`phase11-4-negative.invalid`; OpenSSL then performed and failed actual certificate
hostname verification against the real Pico. Both explicit recovery requests
returned HTTP 409 with unknown output and the identical original failed report.
Removing the faults and explicitly reconciling returned HTTP 200, confirmed
cleanup with the original session, and retained that failure history. Offline
audit found exactly one LOAD and one ARM, both acknowledged, across the run.

**G6 process:** the isolated process was killed only after acknowledged ARM.
Its replacement used an idle INI and a fresh session, observed the old job,
remained a nonowner and returned HTTP 409 to an attempt to cancel that old job.
Independent USB observed the original job's autonomous completion under the
original owner. Console cleanup followed. The combined two-process audit found
only the first process's one LOAD/ARM and no adoption or new submission.

**G6 device:** following a real Pico job and socket loss, a process-local resolver
redirect connected the same production session to a loopback-only TLS fixture.
The fixture required the existing controller certificate and served the existing
valid DNS certificate. Its HELLO returned a deliberately different device ID
`11111111111111111111111111111111`. Production latched `identity_changed` and sent
no work to that endpoint. Restoring the original route did not clear the latch.
This proves the production WTP identity check independently of TLS; it is not
evidence for two real boards or their independent CAs/default names (E1).

**G6 boot:** the controller retained its blocked original-job history while USB
independently checked output. Console REBOOT was verified to reject the owned
job with `not_idle`. Explicit Console ABORT then suspended scheduling, disabled
output, released ownership and recorded the terminal result before the permitted
reboot. The resulting new boot ID caused the production identity latch; repeated
reconciliation still returned HTTP 409 and preserved unknown output and the
original failed report. No fresh LOAD/ARM was sent. Thus this is an actual boot
change with unresolved host history, not a bypass of the idle-reset guard.

**G7:** while TLS owned a second armed job, USB CLAIM returned `BUSY`; USB ABORT
and RELEASE returned `NOT_OWNER`. TLS STATUS after each refusal showed the
same armed job and owner. Console ABORT produced the matching aborted terminal
record with `output_active:false`, null owner and `suspended:true`; saved schedule
enablement remained false. A USB connection is not an automatic ownership override.

## Adversarial findings, corrections and repeats

1. The first G5 instrumentation library was unreadable by the demoted test
   process. It completed normally, without activating the fault. That attempt
   (`153327Z`) is retained as a harness failure. Corrected file ownership and
   mandatory loader evidence prevent a missing preload from producing a pass.
2. The next G5 assertion expected an object containing null output. Actual
   unknown state is a null job and null remote observation. The `153503Z`
   records retain the correct blocked runtime and failed harness assertion.
   The corrected assertion passed DNS, TLS and restored recovery at `153603Z`.
3. Repeated standalone USB probes exhausted the firmware's bounded 16-session
   table, producing HELLO `BUSY`. The first restart attempt (`153640Z`) and
   rejected device/restart preflights (`153808Z`, `153920Z`) remain. Preflights
   made no service pause or job mutation. A separate read at `153838Z` proved
   the old job complete, output false and ownership released. The harness now
   reuses one USB session with increasing request IDs and retains pre-HELLO
   input separately. Restart repeated successfully at `154225Z`. This admission
   limit is not evidence diagnosing the earlier overnight web-page failure.
4. The initial boot attempt (`154449Z`) failed the owned-job reset admission
   rule; cleanup restored inactive/unowned state and the service. The repeat
   explicitly verified `not_idle`, aborted and verified cleanup before reboot.
5. The first successful boot-latch run (`154618Z`) initially failed reconnect
   and needed one bounded Console Wi-Fi cycle. That failure remains part of
   the separate connectivity gate. Its aggregated TLS audit also concatenated
   a partial frame from a closed connection with a later HELLO, creating an
   apparent CRC failure. The recorder now separates TLS connections. The
   final boot repeat (`154941Z`) and full strict frame audit passed without
   Wi-Fi recovery; its read streams had no incomplete suffixes.
6. The offline packet audit was strengthened to include pure ACKs, not only
   data-bearing client packets. Production audit requires one LOAD/ARM with
   received acknowledgements, retained failure history, different-session
   nonadoption, latched identity rejection and authoritative cleanup. Deliberate
   corruption checks reject a truncated request, bad CRC, duplicate LOAD,
   false inactive observation, lost history and packet-capture drops.

The final adversarial assessment rechecked scope, current versus historical
claims, exact job/session/boot bindings, authentic TLS verification, process and
socket fault isolation, capture loss, request replay, USB authority, saved-state
preservation, service restoration and secret exclusion. The repeated evidence
audit and all six refusal checks passed. No actionable in-scope finding remains;
the explicitly listed broader physical/reliability gates remain open.

## Validation and final state

`scripts/audit_phase11_4_recovery.py` is an offline-only maintained audit tool.
Its required arguments select the direct, fault, restart, boot and device
directories above. It validates WTP framing, CRC and schema, operation counts,
packet observations and the case-specific outcomes. Complete malformed frames
are always rejected; an interrupted read suffix may be retained only within
its separately recorded connection, never by scanning for a later header.
Python compilation, WTP contract validation, documentation links and whitespace
checks also passed. No unchanged full firmware/application suite or remote CI
result is claimed for this evidence/tooling slice.

Final USB and Mac/Linux authenticated HTTPS identify boot
`cebcd4720cd9919a7cfaff492b717a85`, unchanged inhibited firmware/server identity,
empty state, inactive output, null owner/job and healthy storage. Both Mac and
Linux hostname resolution passed on the final observation. Saved station
AA0NT/EM18/power 20, disabled 120/0 schedule, expiry zero and watermark
`1788714601000000000` remain. Wi-Fi is enabled, power management disabled and
`pool.ntp.org` remains the configured NTP name. Temporary Console suspension
cleared on reboot. Boot-local terminal records were captured before reboot;
they are not claimed persistent. The installed service is active with original
configuration/binary hashes and provider output disabled. Test processes and
the loopback fixture were stopped; this task's temporary fixture credential
copies were removed. No certificate import or new CA was needed.

Remaining gates are B2 resolution reliability; D1 actual DHCP reassignment;
D2 captured orderly goodbye/cache expiry; D3 unexpected link loss; E1 two real
boards; E2 conflict during a job; E3 conflict recovery; and startup/overnight
connectivity and memory investigation. Short successful checks do not establish
leak freedom. Phase 11.5 resource/contention and 11.6 RF qualification remain
separate. See the [joint matrix](phase11-4-plan.md).

## Documentation Impact

Updated the execution prompt, this result, evidence manifest, joint matrix and
review/development entry points; added the offline audit tool. Considered WTP,
browser API, architecture and companion recovery documentation: their contracts
remain unchanged. No UI asset or product behavior changed. The independent
WsprryPi checkout remains untouched at clean devel `89f23e5`.

The out-of-scope operator documentation follow-up remains
`Wsprry_Pi_Docs/docs/Advanced_Operations/ini_configuration/transmitter_backends.md`
and `docs/User_Interface/Setup/Transmitter/index.md`: describe authenticated
network selection, explicit recovery, new-process nonadoption, identity-change
latches and Console override/reset prerequisites. That repository was read only.
