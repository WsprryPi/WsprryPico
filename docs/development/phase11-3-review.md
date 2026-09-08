# Phase 11.3 joint review and acceptance record

Status: Pico implementation reviewed; joint client integration and final pins in
progress. This record is software evidence, not physical mDNS, NSS, timing or RF
acceptance. See the [one joint checklist](phase11-3-plan.md) and
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
| Fresh Debug host build | PASS, 32/32; includes pinned actual TLS/mDNS, available optional analysis and TinyUSB descriptor tests |
| Separate ASan/UBSan | PASS, final complete run 24/24 after exclusive loopback retry; C/C++ owned code and pinned Mbed TLS/lwIP instrumented, prebuilt OpenSSL not instrumented |
| WTP contract validator | PASS, 23 schema, 7 raw JSON, 1 framing, 8 transition cases; normative protocol unchanged |
| Certificate tests | PASS: DNS-only and optional IP, per-device CA/client/PKCS#12, renewal/alias/migration/legacy, actual SAN/chain/key/expiry checks, manifest mismatch and nonoverwriting/private output |
| Actual TLS server | PASS: named DNS SAN over explicit loopback, name/IP mismatches, both HTTP aliases and cross-origin rejection; retained 11.2 finite jobs, ownership, concurrent clients, revisions, rotation and recovery tests |
| Actual pinned mDNS responder | PASS: in-memory UDP payload input/output with real lwIP netif/clock, probing/A/cache flush, goodbye A/PTR TTL0, malformed/cyclic/oversized packets, failures, repeated cleanup and interface reuse |
| Browser behavior | PASS: drafts/revisions/ownership/unknown state, active/probing/conflict/failure/waiting discovery |
| Actual Chrome | PASS at 1280x900 and 390x844; hostname, owner-Armed/foreign-Running, conflict/failure/unavailable, preserved password draft, no horizontal overflow |
| Four ARM variants | PASS: inhibited/StandaloneRF, network off/on with hostname credentials; ELF/UF2 stack/heap/flash-journal checks pass |

The normal build lives in ignored `build/phase11-3-host`; logs are retained in
its CTest `Testing/Temporary/LastTest.log`. Local invocation additionally selected
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
| Inhibited, network off | 924552 /81868 | 955408 /82436 |
| StandaloneRF, network off | 946556 /267836 | 977684 /268404 |
| Inhibited, hostname network | 948232 /81912 | 980280 /82480 |
| StandaloneRF, hostname network | 970244 /267880 | 1002532 /268448 |

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
`docs/Advanced_Operations/rest_api.md` needs protected shared proxy resources;
`docs/User_Interface/Maintenance/network_safety.md` needs hostname/IP trust,
conflicts, unknown observations and authorized USB recovery. No edits/publication
were made there.

The [11.4 procedure](phase11-4-acceptance.md) is prepared but unexecuted. Real
Mac/Linux NSS/mDNS, browser trust/client selection, DHCP reassignment, multiple
boards/conflicts, renewal/mismatch and USB/output recovery require explicit
physical authorization. Phases 11.4–11.7 remain open, as do Phase 12 provisioning
and Phase 13 final qualification/release artifacts.
