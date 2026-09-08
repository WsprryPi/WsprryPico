# Phase 11.3 execution plan and joint acceptance checklist

Status: complete within the delivered software/integration scope.
Coordinator: this WsprryPico task. The
[shared identity contract](phase11-3-identity.md) is authoritative. No hardware,
services, system resolver/trust, router or third-repository writes are authorized.

## Roadmap

| Phase | Work | Repository | Status |
| --- | --- | --- | --- |
| 11.1 | Network integration | WsprryPi | Closed software scope; physical limitations retained |
| 11.2 | Concurrent browser management | WsprryPico | Closed software scope; physical limitations retained |
| 11.3 | DHCP, mDNS and certificates | Both | Closed software/integration scope; physical gates open |
| 11.4 | Inhibited device acceptance | Both | Open |
| 11.5 | Resource and contention testing | Both | Open |
| 11.6 | Conducted RF acceptance | Both | Open |
| 11.7 | Final review and closure | Both | Open |

Phase 12 retains SoftAP/BLE/runtime credentials; Phase 13 retains final hardware,
RF/filter/band qualification and reproducible public release UF2.

## Ownership and sequence

1. Review both clean devel checkouts, refresh origin, inspect required architecture,
   protocol, configuration, dependency and security sources. Initial inputs Pico
   `a34a9a4342013d41379242f1e456ca3e3760b8db`, Pi `07a7a8b`; no drift after fetch.
2. Save/review shared identity contract and this acceptance matrix before code.
3. Pico mDNS agent owns portable lifecycle, station adapter, lwIP options, narrow
   pinned-responder wrapper, resource/packet tests and firmware responder wiring.
   Certificate agent owns helper, deployment validation, credential CMake/template,
   ephemeral generator and certificate tests. Coordinator owns HTTP policy, main
   integration, Pico browser, TLS tests and shared docs. Pi agent owns only Pi
   client/config/UI/integration/tests/docs. Coordinate overlapping build files.
4. Implement and run focused deterministic checks, actual TLS and injected-resolver
   integration; preserve worker/concurrency and protocol regressions. Use Impeccable
   for existing UI refinements and inspect desktop/mobile states.
5. Cross-build inhibited and StandaloneRF images, network off/on, check ELF/UF2
   stack/heap/journals and added mDNS budget. Use separate sanitizer builds.
6. Independent adversarial reviews, repair findings, rerun affected checks, repeat
   assessment; retain failures and final dispositions in the review record.
7. Commit reviewed Pico implementation first; test clean Pico input from Pi and
   update Pi harness/CI pin. Commit reviewed Pi implementation; update optional
   Pico client pin and joint evidence in a later metadata/test-gate commit. This
   avoids cyclic latest-HEAD requirements and preserves WTP provenance pins.
8. Push authorized devel branches, verify actual local/remote parity and clean
   state, inspect remote CI; report pending/failed/skipped distinctly.

## Acceptance matrix

| ID | Required behavior/evidence | Owner | Status |
| --- | --- | --- | --- |
| I1 | Stable full-ID hostname, canonicalization/bounds, board mismatch | Pico | Pico software pass |
| I2 | Actual certificate/manifest/build agreement, DNS-only, optional IP, legacy and renewal | Pico | Pico software pass |
| M1 | Probe/announce, actual station registration and DHCP replacement | Pico | Pico software pass |
| M2 | Link loss, disable/re-enable, latched conflict, no uncertified rename | Pico | Pico software pass |
| M3 | Partial init/resource failure, repeated cleanup and actual malformed packet tests | Pico | Pico software pass |
| M4 | Static/runtime resource costs, IPv4/core ownership/network-off policy | Pico | Pico software pass |
| H1 | Host/Origin aliases, case/root dot, strict port, malformed/duplicate/cross-origin rejection | Pico + Pi | Joint software pass |
| C1 | Fresh bounded resolution, named TLS, explicit IP plus name, IP SAN pass/fail | Pi + Pico | Joint software pass |
| C2 | Changed address with unchanged identity, failed resolution/handshake reconnect | Pi | Joint software pass |
| C3 | HELLO/device/boot, finite jobs, revisions, concurrent WTP/browser | Both | Joint software pass |
| C4 | Rotation, unknown outcomes, no duplicate LOAD/ARM, ownership/recovery | Both | Joint software pass |
| U1 | Config lifecycle, inactive settings/drafts, diagnostics and desktop/mobile states | Both | Joint software pass |
| V1 | Full documented host/regression/contract commands | Both | Joint software pass |
| V2 | Separate sanitizer builds and four firmware/layout checks | Both | Joint software pass |
| R1 | Adversarial assessment, repairs and reassessment | Both | Joint software pass |
| D1 | Operator examples, Linux NSS prerequisites, third-repo exact follow-up | Both | Joint software pass |
| D2 | Executable opt-in 11.4 procedure, physical execution deferred | Pico | Prepared; physical execution deferred |
| G1 | Clean tested pair/pins, commits/push/parity and CI states | Both | Software reference gates pass; CI states recorded in review |

Local normal/sanitizer integration covers C1–C4. Linux run 34285806646 passes
the joint network job, including actual changed-IP TLS and rendered browser
checks after the independently reviewed orchestration repair. The failed first
run and each broader CI job disposition remain in the review record.

Every pass must identify its evidence class and input revision. Injected resolver
results are not system NSS/mDNS evidence; host responder packets are not physical
Wi-Fi; cross-builds are not timing/RF qualification. Keep 11.4–11.7 open.

Current detailed evidence and retained failed attempts: [joint review](phase11-3-review.md).
