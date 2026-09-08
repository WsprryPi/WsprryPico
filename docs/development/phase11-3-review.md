# Phase 11.3 joint review and acceptance record

Status: Phase 11.3 is complete within its delivered software/integration scope.
Local checks and the repaired Linux joint network job pass. Broader remote CI
job states are recorded below. This is software evidence, not physical mDNS, NSS,
timing or RF acceptance. See the [one joint checklist](phase11-3-plan.md) and
[identity contract](phase11-3-identity.md).

## Input and ownership

Initial clean devel inputs after origin refresh: Pico
`a34a9a4342013d41379242f1e456ca3e3760b8db`; Pi `07a7a8b`. One coordinating Pico task
owns the shared contract/checklist. Bounded agents owned Pico mDNS, Pico
certificates and the Pi integration respectively; cross-slice reviewers examined
identity, authority, actual upstream responder lifecycle and client configuration.
No third repository or system/device configuration was modified.

Pico SDK 2.3.0 `98a542c1a62fb549ffb5d66a3e5892b06276b670`, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`, Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, picotool
`6f6458d792b93685a11423b244a585eaa99eafcf`, Arm GNU 15.3.1 and 138 MHz profile
are retained. Existing local dependency checkouts supplied all builds.

## Pico validation

| Check | Evidence |
| --- | --- |
| Fresh Debug host build | PASS, final 33/33; includes pinned actual TLS/mDNS, available optional analysis and TinyUSB descriptor tests |
| Separate ASan/UBSan | PASS, final client-enabled run 25/25 after exclusive loopback retry; C/C++ owned code and pinned Mbed TLS/lwIP instrumented, prebuilt OpenSSL not instrumented |
| WTP contract validator | PASS, 23 schema, 7 raw JSON, 1 framing, 8 transition cases; normative protocol unchanged |
| Certificate tests | PASS: DNS-only and optional IP, per-device CA/client/PKCS#12, renewal/alias/migration/legacy, actual SAN/chain/key/expiry checks, manifest mismatch and nonoverwriting/private output |
| Actual TLS server | PASS: named DNS SAN over explicit loopback, name/IP mismatches, both HTTP aliases and cross-origin rejection; retained 11.2 finite jobs, ownership, concurrent clients, revisions, rotation and recovery tests |
| Actual pinned mDNS responder | PASS: in-memory UDP payload input/output with real lwIP netif/clock, probing/A/cache flush, goodbye A/PTR TTL0, malformed/cyclic/oversized packets, failures, repeated cleanup and interface reuse |
| Browser behavior | PASS: drafts/revisions/ownership/unknown state, active/probing/conflict/failure/waiting discovery |
| Actual Chrome | PASS at 1280x900 and 390x844; hostname, owner-Armed/foreign-Running, conflict/failure/unavailable, preserved password draft, no horizontal overflow |
| Four ARM variants | PASS: inhibited/StandaloneRF, network off/on with hostname credentials; ELF/UF2 stack/heap/flash-journal checks pass |

The normal build lives in ignored `build/phase11-3-host`. Full-run logs are
`/tmp/phase11-3-client-ctest.log` and
`/tmp/phase11-3-client-sanitize-ctest.log`; CTest
`Testing/Temporary/LastTest.log` contains the most recent affected rerun. Local invocation additionally selected
the existing Harness Python and pinned TinyUSB path for optional analysis tests.
No Harness sources were changed or hardware opened. Generated keys, firmware,
logs and screenshots remain ignored/private. Chrome fixtures use local HTTP;
real TLS/mTLS is verified separately without importing system trust. Impeccable
preserved the incumbent surface. Its Pico mechanical detector returned no findings
in degraded regex mode (HTML parser modules unavailable); this is not computed
contrast validation. Rendered states were inspected independently.

Reproduce firmware using the network guide and already installed pins. This run
used separate `build/phase11-3-firmware-off` and `build/phase11-3-firmware-on`,
with `PICOTOOL_FETCH_FROM_GIT_PATH` selecting the existing private build's `_deps`
cache. Network-on used `build/phase11-3-host/network-test-credentials-v3`. These
credential-bearing UF2s are private test artifacts and were not flashed/published.

## Resource evidence

Compared with retained 11.2 ELF files from the same pinned toolchain/profile:

| Image | 11.2 text / BSS bytes | 11.3 text / BSS bytes |
| --- | --- | --- |
| Inhibited, network off | 924552 /81868 | 955400 /82436 |
| StandaloneRF, network off | 946556 /267836 | 977676 /268404 |
| Inhibited, hostname network | 948232 /81912 | 980272 /82480 |
| StandaloneRF, hostname network | 970244 /267880 | 1002524 /268448 |

These are linked whole-image costs, including authority/UI/manifest integration,
not isolated mDNS flash costs. BSS increases 568 bytes. The physical network image
has a 16 KiB stack per core and a linker heap span 226896 bytes (`0x200449b0` to
`0x2007c000`). The 80 KiB TLS cap and shared admission reserve are unchanged.
The mDNS wrapper reports ARM helper 192 bytes and retained packet descriptor 40
bytes; isolated 64-bit host sizes differ (224/56). Host normal mDNS lwIP heap peak
is 1744 bytes, excluding deliberately forced startup exhaustion; peak timeout
slots 9 and one boot-long UDP PCB. See [responder resource details](mdns-responder.md)
for bounds and teardown distinctions. These values do not measure target allocator
fragmentation, RF latency or physical simultaneous resource maxima.

## Adversarial findings and disposition

| Finding | Repair and review evidence |
| --- | --- |
| Upstream init asserts on resource/bind failure | Checked boot-long initialization; PCB/bind exhaustion tests |
| Upstream removal leaves delayed/retained-packet timers | Quiesce plus complete timer/chain cleanup; actual repeated registration and netif reuse tests, sanitizer coverage |
| No upstream goodbye API | Upstream A/PTR builder with zero TTL before orderly disable; packet assertions; no delivery claim |
| Established conflict may reprobe silently | Wrapper converts to latched conflict, no automatic suffix; parser/lifecycle tests |
| Netif changes permit stale delayed replies before poll | Immediate callback quiescence, foreground removal/reprobe; actual address/link tests |
| DHCP diagnostic lost old address during quiescence | Preserve prior address through explicit network-change event; counter regression |
| Wrong-board rejection hid configured name | Preserve selected name, expose mismatch, portable identity gate tests and no listener start |
| Unicode helper lowercase admitted a non-ASCII character | ASCII rejection before canonicalization; regression |
| Encrypted empty-password key passed build but not firmware loader | Explicit encrypted PEM rejection; certificate regression |
| Ephemeral key embedded in publicly traversable test binary | Protect credential-bearing host build root, in addition to key/header modes |
| Pi embedded-NUL IPv6 input truncated by libc | Full input grammar before address parsing; C++ and browser regressions and independent reproduction |
| Pi legacy hexadecimal numeric input escaped through terminal dot | Recheck numeric ambiguity after canonicalization; regressions and independent reproduction |
| Cross-alias Host/Origin could otherwise pass allowlist | Validate each, then require canonical equality for any supplied Origin; portable and actual TLS tests |

Independent certificate/authority and Pi-side reviews found no remaining actionable
identity/HTTP defect after reassessment. Remaining physical/resource gates are
explicit limitations, not software test passes.

Failed attempts retained: first new host configure rejected read-only validation
under ignored build output; validator now separates read-only input inspection
from restricted credential creation paths. Early mDNS host compilation exposed
Darwin byte-order macro conflicts and a missing UDP header; host seam repaired.
First Chrome fixture bind was sandbox-denied; authorized isolated render passed.
Initial new firmware configure attempted picotool fetch in the restricted sandbox;
existing exact pinned cache was selected instead. Concurrent/sandbox TLS startups
returned `-1`; socket suites were rerun with exclusive loopback access. No RF
acceptance threshold or ownership gate was relaxed to obtain a pass.

## Documentation Impact

Updated Pico shared identity contract, execution/checklist, browser API, certificate
and resolver workflow, responder/license/resource notes and opt-in 11.4 procedure;
README/development/implementation-plan links reflect the slice. Phase11.1/11.2
records retain their historical evidence and physical limitations; WTP/1 remains
unchanged. Pi owns host configuration/UI/resolver/integration documentation.

The unauthorized sibling `Wsprry_Pi_Docs` was inspected read-only. Follow-up:
`docs/Advanced_Operations/ini_configuration/transmitter_backends.md` and
`docs/Command_Line_Operations/transmitter_backends.md` need network settings,
DNS-vs-IP TLS examples and resolver prerequisites;
`docs/User_Interface/Setup/Transmitter/index.md` needs current target and independent
TLS identity/draft workflow;
`docs/User_Interface/Operations/index.md` needs DHCP/conflict/reconnect
diagnostics and authoritative recovery;
`docs/Advanced_Operations/rest_api.md` needs protected shared proxy resources;
`docs/User_Interface/Maintenance/network_safety.md` needs hostname/IP trust,
conflicts, unknown observations and authorized USB recovery. No edits/publication
were made there.

The [11.4 procedure](phase11-4-acceptance.md) is prepared but unexecuted. Real
Mac/Linux NSS/mDNS, browser trust/client selection, DHCP reassignment, multiple
boards/conflicts, renewal/mismatch and USB/output recovery require explicit
physical authorization. Phases 11.4–11.7 remain open, as do Phase 12 provisioning
and Phase 13 final qualification/release artifacts.

## Clean reviewed pair and companion validation

Pico runtime implementation is `d8cde03f8127b3c2aaf727f2c21c20960f658e84`;
WsprryPi implementation is `efcc792cb45780c8b87ebfa83838ecb9eb9cdf47`. Both commits
were pushed to devel and remote parity verified. Pi's network CMake/CI pins the
Pico runtime commit. Pico's optional client gate pins the reviewed test-harness repair
`2e47641f6ebdff104e32999f5194f2e0dc408e06` (Pi runtime unchanged from efcc792);
its historical target name `network_11_1_interop` is retained. The later Pico commit
updates this gate, test-only loopback address/credential seams and evidence/docs;
it does not change firmware runtime code or require Pi to chase metadata HEAD.

Both normal and ASan/UBSan Pi-to-Pico interoperability passed against clean d8cde03.
This includes configured-name resolution through an injected resolver, DNS SAN
verification, explicit IP with expected hostname, IP SAN success/mismatch,
management revisions and complete finite jobs. Failed DNS/handshake reconnects
send no duplicate LOAD/ARM or false cleanup; lost LOAD/ARM/ABORT replies retain
same-request replay, foreign-owner protection and device/boot/session recovery.
A successful named loopback connection is not operational mDNS evidence.

Pi also passed protocol/plan/USB/backend/scheduler/status/application suites,
production 1995/runtime-rotation 2012 checks, shared API/four proxy guards and the
explicit portable simulated semantics subset. Its 34-case actual TLS suite passes
normally and with ASan/UBSan. Rendered desktop/mobile management and discovery
states pass with drafts preserved; Impeccable review found no remaining issue.
Exact commands and counts are in the companion `docs/development/phase11-3-review.md`.

On this Mac, binding 127.0.0.2 is unavailable (`EADDRNOTAVAIL`). The actual second-IP
TLS rebind test is explicitly skipped locally; injected resolver results still
run. Linux CI includes the real loopback address replacement without interface,
NSS or trust changes. The initial CI run is
[34284241406](https://github.com/WsprryPi/WsprryPi/actions/runs/34284241406),
for Pi efcc792 and Pico d8cde03. Its final result is recorded below.

Four firmware images were reconfigured/rebuilt with clean embedded revision
`d8cde03f8127`; all four layout checks passed again. Their private UF2 SHA-256s:

| Image | SHA-256 |
| --- | --- |
| Inhibited/off | `a8687b7a93b821bd99c3c077d745e62c6ff29dd1f7d24688450a86b174c8a791` |
| StandaloneRF/off | `b81bf3ab160b8993258ab6fea6cdfcccac4f7e2f0f363af12ef064c6ff5e11e3` |
| Inhibited/hostname | `a95eb4d9a70767ae3ee418c780d0b9630662e212a6d263a37d351ad2bd90b09d` |
| StandaloneRF/hostname | `adc51db2da52d95584fb3897213efeef28a870a80436b77ecce9166ef280512f` |

Automatic approval review rejected a new local Git clone despite the requested
clean-reference workflow. No clone/workaround was created. Existing clean Pico
and Pi checkouts were used sequentially for their reference gates; this did not
block implementation or integration acceptance.

Final Pico client-enabled acceptance: 33/33 normal, 25/25 ASan/UBSan, including the
actual efcc792 client and restart orchestrator. The eight additional normal-only
analysis/descriptor checks retain the same optional dependency distinction as
11.2. Last source changes are test-only, independently reviewed: alternate bind
is limited to 127.0.0.1/127.0.0.2 and exact clean client gate remains enforced.
Firmware/runtime diff from d8cde03 is empty. Tests in both directions therefore
retain one reviewed runtime pair without circular latest-HEAD pins.

### Retained first Linux CI failure

Run 34284241406 at Pi efcc792 passed the actual alternate IPv4 TLS case: the log
contains `RESTART address2`, `RESTART address1` and the unchanged-DNS-identity
success. It subsequently hit the 180-second orchestration deadline. Independent
inspection identified buffered text `readline()` prefetched an informational
line and a following `RESTART` line, while the selector waited only for fresh OS
pipe bytes; the child then waited for an acknowledgement held in Python's buffer.
This is a test-orchestrator defect, not a TLS/address acceptance failure. The
repair drains bounded complete lines from unbuffered pipe reads and adds an
isolated coalesced-line subprocess regression. Timeout and identity assertions
remain unchanged. The original network job failed and browser step was skipped;
the rerun and other job dispositions are recorded separately below.

The first run completed with four other jobs passing: `non-hardware-validation`,
`macos-simulated-profile`, `strict-i2c-profile` and `ubuntu-gcc13-release`.
Independent repair review also found partial startup lines could block readiness
and EOF could wait without progress. The repaired bounded reader applies the
existing 15-second startup deadline, explicit EOF and child cleanup. Five isolated
subprocess regressions pass; final reassessment reports no remaining actionable
finding. The overall first run remains failed; its browser step remains skipped.

### Reviewed harness repair and final client reference

Pi repair `2e47641f6ebdff104e32999f5194f2e0dc408e06` is committed/pushed with
clean origin parity. Its runtime diff from efcc792 is empty. Five deterministic
subprocess regressions and normal/ASan actual integration passed after repair;
independent reassessment closed all findings. Pico's clean optional client gate
now pins this revision, preserving Pi's clean Pico runtime pin d8cde03.
The new remote run is
[34285806646](https://github.com/WsprryPi/WsprryPi/actions/runs/34285806646).

After repinning, Pico's affected `network_11_1_interop` test passed normally
(23.76 s) and with ASan/UBSan (23.90 s); the five subprocess regressions also
passed again. Logs: `/tmp/phase11-3-final-pin-interop.log` and
`/tmp/phase11-3-final-pin-sanitize-interop.log`. These affected reruns supplement
the full 33/33 normal and 25/25 sanitizer runs above; application code did not
change between them.

### Final remote evidence and publication boundary

Run 34285806646 at Pi 2e47641 and clean Pico d8cde03 passes
`wtp-network-loopback`, including every parent TLS/shared-API/actual-interoperability
step and `Render network controls with mocked responses`. The Linux log records
`RESTART address2`, `RESTART address1` and at 2026-09-08 22:29:46 UTC,
`Actual changed IPv4 loopback address with unchanged DNS TLS identity passed`.
This closes actual socket address replacement and the repaired orchestration gate;
it still does not test operational LAN multicast or system NSS. Log retained at
`/tmp/phase11-3-ci-repair-network.log`.

At this record's publication preparation, `macos-simulated-profile` and
`strict-i2c-profile` also pass; `non-hardware-validation` and
`ubuntu-gcc13-release` remain running. Their previous efcc792 run passed, but that
is separate evidence and does not replace current results. The final task report
records a fresh status observation after pushing this metadata/test-only Pico
commit. There is no configured Pico remote workflow to claim as passing.

The final Pico commit contains only reference/test support and documentation;
`git diff d8cde03 -- src firmware` is empty. Both runtime inputs and clean-reference
pins above remain the exact tested pair. Publication uses authorized devel commits
and pushes, with working-tree/remote parity verified again after the final push.
Phase 11.4–11.7, Phase 12 provisioning and Phase 13 qualification/release remain open.
