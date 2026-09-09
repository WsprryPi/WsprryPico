# Phase 11.4 single-board execution record

Status: **EXECUTED WITH OPEN GATES; Phase 11.4 OPEN**. This record supports the sole
[joint matrix](phase11-4-plan.md); it does not replace its case status.
The [comprehensive execution prompt](phase11-4-single-board-prompt.md) was written
and executed at the user's request. Private raw evidence is under
`build/phase11-4-single-board-evidence/`; generated credentials remain ignored.

## Authorization and target

The user subsequently authorized all tests and specifically authorized a bounded
pause of `wsprrypi.service` on wspr5 after automatic approval review rejected
service interruption under the broader grant. Mac unlock was supplied. The user
confirmed that the clients share the Wi-Fi network and its DHCP service; exact
router administration details remain unknown. Retain explicit RF inhibition,
identity, cleanup and unrelated-system boundaries from the original handoff.

Board: original Pico 2 W, USB serial `0BF4B4AEC9FFB344`, WTP ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`, separate Console/WTP interfaces if00/if02.
The installed alias image initially remained UF2
`68b617ca7efdcbea65cd7a592d93f346d560aa0aef1e8e16e65d6f2add9d3ca6`,
revision `a9662c3f8323-dirty`, with the certified alias
`wsprrypico-0a60df.local`. Reboots change boot identity; evidence binds each run.

## Prepared certificate image sequence

These are standard inhibited WsprryPico targets built from runtime unchanged
since 1db0a99, with observed embedded revision `1db0a99afb57` (no dirty suffix).
All three passed production certificate validation, build, standalone image
layout, RF_OUTPUT_DISABLED=1 and DryRunEngine checks. No physical StreamEngine
or RfWorker symbols were linked. Source, ELF/UF2 and certificate metadata are in
`*-candidate-verified.json`. All three were subsequently flashed and verified on the recorded serial;
results and restoration are recorded below.

| Candidate | UF2 SHA-256 | Server certificate SHA-256 |
| --- | --- | --- |
| renewal | `53ec61f1aec62e8363c9727d1af2a3302ecf2baf203d5b9cf1f80059803b09f5` | `fab060e1ba10dc6063cad2db6fbdc17edb4f27528b3dbcd12be54e77499ce8cf` |
| wrong-board | `e3d0f12d42cac505e23c619ff8cac272aedae3da700933f12256db77b59db182` | `1f8d5043700fe9e169d94c99bc4479032f2a0331fa57c210f7e4324ba3418042` |
| ip-san | `d6c6f34ad9daadeef6863fd0d131649c419df311875d1ae9d77b8176039503f1` | `57a7bce06be0fe0e3b11b20b9560efff108fb8ebe4f4a9d0413af16cddae1f16` |

Renewal keeps the actual full ID, same alias and CA, with new validity/fingerprint.
Wrong-board deliberately binds `eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` to that alias
under the same CA; its internally valid certificate/manifest must pass build
validation but fail actual-board deployment admission. IP-SAN includes the alias
and the observed `192.168.1.47`, which must still match at execution. The known
original inhibited image above is the intended final restoration image.

The physical sequence is: establish idle/unowned state and disabled schedule;
flash renewal and verify full identity, new fingerprint and existing clients;
flash wrong-board and verify USB still reports the actual full ID while deployment
match is false and network control/discovery fail closed; flash IP-SAN to recover
correct deployment and verify both certified URL forms; restore the original
inhibited image and verify saved configuration, watermark, output and network.
Each selected serial, staged hash, flash verification, reboot and final read must
be recorded. Preserve journals; never use full erase or an RF image.

Replacement controller/browser certificates and a same-CA expired negative client
are prepared in private new directories. Issuance alone does not import trust,
rotate a running principal or revoke the original valid client.

## Observed direct-device and browser work

`jobs-attempt-1/events.jsonl` records six direct WTP jobs, each a complete
six-second nominal 3,570,100 Hz tone with no frequency adjustment: completion,
loaded/armed/running cancellation, acknowledged ARM followed by socket loss and
same-session completion reconciliation, and CLOCK_UNCERTAIN rejection of a 1 ns
budget followed by loaded-job cleanup. Every normal ARM uses 500 ms and ten-second
lead, checked against CAPS and fresh device UTC. All six passed, with matching
terminal records, explicit inactive output and unowned cleanup. Separate browser
credentials observed the loaded owner and received NOT_OWNER for ABORT/RELEASE.
This is direct target evidence, not production-host or Chrome job-submission proof.

Chrome stale-config testing retained an unsaved EM19 grid draft after a rejected
save, explicitly discarded it through the native confirmation and reloaded the
actual EM18 saved value. Password remained blank/redacted. Direct API tests
observed 428 missing revision, 412 stale revision, 400 invalid phase and successful
change from disabled schedule 120/0 to 240/120. Chrome restored 120/0; full redacted
readback matched the original configuration and original ETag exactly.

The draft originally proposed phase 1, which source review proved invalid because
phases are multiples of 120 seconds. It was retained as a deliberate 400 test;
240/120 became the valid reversible delta. No invalid schedule was saved.

A same-image Console reboot then changed boot identity from
`efa316aecb3f7c9e29484eca66e068d3` to `88091dc74738f0070d3d7fe44744a3d4`.
USB verified full identity, deployment match, inactive/unowned state, disabled
120/0 schedule, healthy storage, unchanged watermark `1788714601000000000` and
cleared reboot-required flag. SNTP and the same hostname recovered. This first reboot proves restoration persistence. The later renewal sequence
separately proves altered-value persistence, as recorded below.

## Production host execution and retained attempts

Reviewed executable remains Pi 2e47641's isolated GPIO-free build, SHA-256
`3acd44dd6a8933cc816604a4514d8517e7586a2da40bff628378e080af5c6857`.
Installed binary is unchanged, SHA-256
`0c8d2a578a766d2b8292467a0c41babd39ae27196a707d8cc701565815f52bdf`;
installed INI SHA-256 is
`795ce11848a20e03bb82c373e93f068d65bd0630d39761ac96ca2f832a724ebd`.
Its saved transmit setting is false, boot policy Never, backend RP1 GPCLK GPIO20.
The service's rendered safety fields were Unknown. The provider's correctly
framed root-only Unix-socket query independently reported outputEnabled:false
and gpio20. That authoritative result, not an idle label, admitted the pause.

Each attempt uses a new owner-only `/home/pi/phase11-4-acceptance/single-board-host-N`
directory, a private INI, unprivileged candidate process, HTTP 31425 and loopback
WebSocket 31426, leaving the installed checkout/binary/INI intact. Stop and restore
are bounded and guarded by signal cleanup. Original service and provider output
checks were recorded after each completed attempt. A selected finite QRSS E request
uses three-second dots at 3,570,100 Hz, a scheduled start, and a process deadline
long before the ten-minute repeat. Its documented per-run unqualified-frequency
consent does not change qualification policy or imply RF authority.

Retain these failures separately from later results:

- Initial configuration inspection used strict ConfigParser and rejected the
  existing duplicate Band GPIO section; read-only inspection was corrected.
- An initial route query lacked the protocol's write-side EOF and timed out;
  the reviewed shutdown(SHUT_WR) framing produced authoritative state.
- Host attempt 1: wrapper key-case error before candidate launch; original
  service restored. Safety field validation moved before service interruption.
- Host attempt 2: hostname connection succeeded, but the wrapper wrongly expected
  a network resource envelope instead of the documented flat resource; restored.
- Host attempt 3: actual hostname and IP+DNS application/management reads passed;
  finite QRSS was rejected before job preparation by the unqualified-band policy.
- Host attempt 4: observer assumed every preparing snapshot contained a remote
  job. It stopped on the valid null/unknown observation; graceful termination
  aborted the loaded job. USB retained its aborted terminal record and proved
  inactive/unowned cleanup. Observer now retains unknown until authoritative state.

- Host attempt 5: the finite job completed, but the observer looked in the
  already-cleared current job instead of `host.last_report.job`, and exited 1.
  The saved report and independent USB terminal record establish completion;
  the observer was repaired offline without repeating the physical job.

The original failures are acceptance-wrapper/planning failures, not inferred
firmware defects. Actual runtime defects, if established, require owned repairs
and retesting; no failure is erased by a later pass.

## Reproduce the maintained driver checks

From the Pico repository root, these commands perform no device I/O:

```sh
python3 scripts/inhibited_network_acceptance.py
python3 tests/inhibited_network_acceptance_tests.py
```

The first renders the six-case plan. Physical execution requires `--run` and
every explicit identity, endpoint, credential and new evidence-directory argument
listed by `--help`, plus authorization for that exact batch. No credentials or
addresses are inferred. The raw-evidence [hash index](phase11-4-single-board-evidence.json)
binds selected retained artifacts without publishing them.

## Local review and checks

New `scripts/inhibited_network_acceptance.py` is opt-in, defaults to a no-I/O
plan, requires explicit IP/DNS/device/boot/server fingerprint and independent
controller/browser identities, validates strict WTP framing/schema, CAPS and
clock, and preserves ambiguous requests and same-session cleanup evidence.
It never resubmits an ambiguous mutation. Output unknown or a different job/boot
blocks dependent cleanup mutations.

First adversarial pass fixed total HTTP timeout enforcement and rejection of a
mismatched job during cleanup. Twelve deterministic tests cover no-I/O default,
explicit binding, complete job schema, unsafe engine/limits, authority/clock
refusals, cancellation evidence, lost LOAD reply without duplicate submission,
unknown/different-job cleanup refusal and strict framing. The suite is registered
in CTest and cannot invoke physical I/O.

First CMake refresh failed its clean Pi-source gate because the main companion
checkout had advanced to its documentation commit. The subsequent three-test
CTest run used the old generated test list and is not evidence for the new test.
A separate clean local clone at exact Pi 2e47641 fixed the input path, preserving
the gate. Reconfiguration then passed and all four affected CTest suites passed
(acceptance driver, certificate tooling, standalone Console, WTP probe).

## Documentation Impact

Updated: this record, comprehensive prompt, coordinating matrix/review and
companion host review as execution progresses. Normative WTP, browser identity,
firmware behavior and reusable WTP-Client remain unchanged. Later target resource,
RF and release qualification remain open. Operator documentation is read-only;
follow-up paths remain those listed in phase11-4-review.md. Final adversarial
assessment, exact remaining matrix and publication results are recorded at closure
of the authorized work, not assumed from preparation.

## Completed production result

Actual hostname startup and explicit IP plus expected DNS startup/management
passed in attempts 2/3. Authenticated identity was `wsprrypico-0a60df.local`,
resolved address `192.168.1.47`, full device fd6127d11d6aca42a9905fa3fb1bf1d5,
boot 88091dc74738f0070d3d7fe44744a3d4 and inhibited CAPS. These are actual
production application observations, separate from OpenSSL and NSS utilities.

Attempt 5 completed job `ea375a1be909a78d0000000000000001`, scheduled UTC ns
`1788920524000000000`. The retained report has outcome complete,
arm_handed_off:true, execution.ok:true, cleanup_attempted:true, cleanup.ok:true
and matching authoritative terminal job evidence with device_output_active:false.
History includes armed, running, empty and unknown; unknown is retained. A later
queued request did not execute: the candidate stopped before its ten-minute slot.
Independent `production-final-pico.*` confirms that exact complete terminal record
and empty/unowned/inactive cleanup. Attempt 4's aborted job
`6be6563549dd48d80000000000000001` remains in the same USB history.
`production-finite-assessment.json` checks the retained report, not a synthetic run.

## Deployment, client and persistence results

The approved single-board sequence executed renewal, wrong-board, IP-SAN and
original-image restoration, each guarded by full USB identity, inhibited CAPS,
inactive/unowned state, disabled scheduling, staged SHA-256, exact picotool serial,
verified programming and retained schedule/watermark. No full erase was used.

| Image | New boot ID | Physical result |
| --- | --- | --- |
| renewal | `ca7bf4309e6edfd634e8a78bab8c60ea` | Same DNS/CA/full ID, new pinned server fingerprint; original, replacement and original-again WTP/HTTPS clients passed |
| wrong-board | `89d4e1e1e0f4fb4055c434a4cbb8d819` | Actual ID unchanged; deployment match false, listener false, mDNS failed/device_identity_mismatch, empty advertised name, inactive output; settled link up at .47, bounded TCP connection timed out |
| IP-SAN | `dbc82fffc67336db43ec69fbe9aa9b38` | Correct deployment restored; literal-IP TLS verification and numeric HTTP Host/Origin passed for both client generations, independent WTP full ID verified |
| original restoration | `08024863915fa4470eddfb64854bc54f` | Original UF2/revision/fingerprint policy restored; original 120/0 disabled schedule and watermark retained, USB inactive/unowned |

The renewed image retained altered disabled schedule 240/120 across its boot.
Authenticated GET then verified that value and restored the full original redacted
configuration exactly. Subsequent wrong-board, IP-SAN and original boots retained
120/0, healthy storage and watermark `1788714601000000000`. Scheduling never became
enabled. Terminal records were read before resets; boot-local terminal history
clears on reboot and is not claimed to persist.

Replacement controller and browser leaf certificates were used through WTP/HTTPS
in the direct test client, followed by successful original-client reads. This
proves issuance did not revoke the original client. It does not prove a new Chrome
keychain import or production-client rotation. Existing approved Mac CA/browser
credentials remain installed; no new trust import occurred. Literal-IP HTTP/TLS
success is not an actual Chrome IP-URL observation: the Mac locked again before
file-picker work. The actual Chrome complete-job file was prepared but not loaded.

## Retained negative and network observations

Mac TLS attempt 1 timed out in the positive control; no negative ran. A bounded
Linux capture then observed approximately 7.4 seconds of SYN/ARP delay before a
successful authenticated HTTPS exchange and short-name mDNS advertisement.
Mac route/ARP subsequently showed the correct en0 MAC mapping without REJECT.
This is intermittent reachability evidence, not a proven firmware or router cause.

TLS attempt 2 passed its positive control and rejected wrong hostname and wrong CA
with the intended client verification errors. Missing-client TLS closed without
HTTP but reported `decryption failed or bad record mac`, failing the planned alert
oracle. Separate attempt 3 retained the same discrepancy for untrusted and same-CA
expired clients, passed the IP-without-SAN rejection, and passed both positive
controls. The expired leaf's offline validity check failed as expected. No WTP
mutation was sent. Rejection-with-no-HTTP is observed; the precise device rejection
reason remains unresolved and F3 is PARTIAL, not silently promoted to PASS.

On the restored original image, a direct Mac response-loss batch timed out before
WTP connection and before CLAIM/LOAD. The prepared Linux batch subsequently failed
with `No route to host`, also before CLAIM. No response-withholding case executed;
its proposed mechanism logs the received reply then withholds it at the test
application boundary, not on the network wire. Production restart and USB-versus-
Console packets were prepared but not invoked after network admission failed.

The Linux deferred-HTTP Wi-Fi packet failed its read-only GET precondition and
made no network mutation. Its Pico-specific capture recorded unanswered ARP/SYN.
A separate Console off/on cycle did execute: disabled/empty advertised state,
one goodbye attempt and zero reported send failures, then the same .47 address
and active certified name. Linux capture observed no TTL-zero goodbye; NSS timed
out before, during and after the cycle, so it cannot establish cache expiry.
No retry converts that result into reception or reliable discovery. Captures and
helper processes were bounded and stopped. No router, hosts file, DNS cache,
installed service configuration or AP setting changed.

Current blockers are reachability for further network-dependent faults, absent
router administration details for real DHCP/link faults, the locked Mac for native
Chrome work, and the missing second board for E1. Shared Wi-Fi/DHCP and broad test
authorization are recorded; approval is not falsely listed as the remaining block.
No hostile alias responder was started while baseline peer reachability was bad.

## Repeated adversarial assessment and final disposition

The first review repaired the maintained driver's total HTTP deadline and cleanup
job binding. Subsequent reviews repaired private observer assumptions about config
key case, the flat network resource, null current jobs and terminal reports; moved
safety checks before service interruption; and used valid 240/120 schedule values.
A second review identified that restoring before reboot did not prove persistence
of a changed value; the renewal sequence closed that gap. Prepared packet cleanup
was strengthened so capture shutdown and installed-service restoration remain in
independent finally blocks. Unexecuted private packets are not certified by review.

Final evidence review corrected the actual candidate revision (no dirty suffix),
distinguished wrapper exit 1 from independently proven production completion,
separated actual Chrome work from direct HTTPS clients, preserved TLS alert and
ARP/NSS failures, and replaced obsolete permission blockers in the joint matrix.
It did not relax a physical acceptance threshold or introduce a speculative runtime
fix. No remaining actionable finding was found in the maintained tooling/docs
within this reviewed slice. The operational failures and unexecuted physical gates
above remain open; this is not a claim that every Phase 11.4 issue is closed.

The four affected CTest suites passed again after review. No firmware/runtime,
protocol, shared component, CI pin, SDK or UI source changed. No remote CI result,
RF performance, physical waveform timing or release qualification is claimed.

Final read-only `final-state.*` verifies original inhibited image revision
`a9662c3f8323-dirty`, boot `08024863915fa4470eddfb64854bc54f`, full actual device,
empty/unowned/inactive WTP, disabled original settings and healthy retained
watermark. Wi-Fi enabled and device mDNS active are device observations, not proof
that peers currently resolve/reach it. The original service is active, installed
binary/INI hashes match those above, authoritative provider outputEnabled:false,
and no candidate or tcpdump process remains. Service PID may change due to the
explicitly approved pause/restoration; no PID-preservation claim is made.
