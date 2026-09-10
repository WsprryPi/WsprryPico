# D1: current-code review and actual DHCP address-change acceptance

Start at WsprryPico devel `f11e2166e8de79d77540ec3e59df110f0e76d892`.
Review AGENTS.md, README, CONTRACT, architecture, development commands, networking
adapter, mDNS wrapper/state machine, identity/TLS code, tests and the E1/B2/D2
commits. Record findings before implementation. Preserve the existing modified
shutdown-results document and untracked soak document/script byte-for-byte.
Read sibling WsprryPi code when needed; do not change that repository.

## Objective and evidence boundaries

D1 requires an actual DHCP-assigned address different from the original, followed
by same-hostname discovery, authenticated WTP/HTTPS, actual Chrome reload and
actual WsprryPi production-client reconnection. Preserve certificate/CA, WTP
identity, saved configuration and authoritative inactive/unowned state. A local
registration, mocked address change, reservation row or successful retry alone
cannot establish this result. Retain prior failures and new failures individually.
Do not infer all network failures are bridge faults or change timeouts merely to
make a case pass. Packet-loss resilience and B2/D2 repeatability remain separate.

The former attempt was blocked by Orbi HTTP 400 before any new lease. Establish
a usable Pico-only reassignment mechanism first. Never issue repeated Wi-Fi
cycles when the required router operation has failed.

## Exact setup and authority

All testing uses Bohica-IoT, the user's simple 2.4 GHz bridge. wspr5 stays on USB
wlan1, profile `921301fe-cdfd-4965-8ac7-c96e9d908ea6`, MAC
`90:de:80:47:b9:da`, address `192.168.1.117`; preserve active/enabled
`pi-wifi-recover.timer` and active `wsprrypi.service`. Mac association was
user-confirmed. Sample current BSSIDs; do not assume a common radio from SSID.

A: Pico 2 W/RP2350, serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, hostname
`wsprrypico-0a60df.local`, prior address `.47`, TLS port 18443. B is a read-only
comparator: serial `CDDBF8767C506C07`, device `29f20b7342051ef947aa56cb9d4fab42`,
MAC `88:a2:9e:0a:9d:89`, hostname `wsprrypico-0a9d89.local`, prior address `.53`.
Use serial-specific Console/WTP endpoints. Verify current boots independently.
Both deployed standard inhibited images use SDK 2.3.1
`079c6f39023649b154152db30f1d781e884879bc`, runtime `dbf1d86f0885-dirty`,
150 MHz default system clock, GCC 15.3.1. Bind images to the latest B2 manifest's
per-board UF2/ELF hashes, not the shared runtime revision alone.

This D1 request continues the earlier narrow authorization for a temporary
A-only DHCP reservation on Orbi `192.168.1.1`, solely to force a lease change,
then removal. It also covers bounded inactive A WIFI OFF/ON, read-only exact-device
USB/LAN/captures and a supervised isolated production-client check. No RF, jobs,
LOAD/ARM, GPIO, trust import, certificate bypass, firmware flash, router restart,
DHCP pool/subnet change, global lease flush, second DHCP server, MAC impersonation,
radio reassociation or network-security change is authorized by this slice.

## Ordered execution

1. Save initial repository/user-file hashes, code-review findings and this prompt.
   Extend meaningful deterministic coverage if review finds a gap, especially the
   actual adapter joining address-change callbacks to mDNS reprobe. Existing
   component tests alone do not prove that integration. Repair concrete in-scope
   defects with tests; keep hardware-free evidence labeled accurately.
2. Verify fresh A/B INFO and WTP HELLO/CAPS/STATUS, boot/device/engine, inactive
   output, no owner/job, empty state, healthy storage, disabled schedules, station,
   expiry and watermark. Check current host profile/services and read-only native
   peer/TLS baselines. Never overlap independent USB readers.
3. Inspect the signed-in router's current LAN/DHCP/reservation/attached-device
   state. The temporary target `.247` must be in the unchanged pool and absent
   from current assignments/reservations, with bounded duplicate-address probes
   as additional evidence. Snapshot original table. Stage only A's MAC with a
   short test label, verify exact values, and attempt the normal documented Apply
   from a fresh page. A saved row is not proof of effective reassignment.
4. If Apply again returns HTTP 400, preserve the outcome and remove only the
   temporary row, verifying the original table. Do not cycle A. A single alternate
   browser attempt is allowed only if a fresh already-authenticated session is
   available and provides a concrete different execution path; preserve both
   outcomes. Do not guess backend endpoints, replay hidden browser requests,
   bypass authentication or repeat unchanged failing submissions. If no usable
   mechanism remains, stop dependent physical work and report the exact blocker.
5. Only after effective router admission and valid peer baselines, start bounded
   independent USB/NETTRACE, DHCP/mDNS/TCP capture and native Mac observers. Use
   independent timed restoration before the A controller. Perform one idle
   OFF/ON transition and allow up to 120 seconds for same-name authenticated
   recovery, preserving each failed attempt and its latency. Do not reset this
   deadline when clock synchronization arrives. Require actual new lease/USB
   address, captured transaction/client identity where observable, new-address
   mDNS probe/cache-flush records and no new old-address advertisements. Missing
   unicast DHCP replies must remain an explicit evidence limit.
6. Reconnect the actual isolated WsprryPi production binary by unchanged hostname
   and trust configuration; record source/binary/config hashes, resolved address,
   certificate and device/boot. Use Transmit false/Enable on Boot Never and prove
   zero LOAD/ARM with strict frame evidence. A bounded service pause requires
   independent restoration and final unchanged installed binary/config plus
   authoritative provider output checks. Reload actual Chrome at the same URL;
   preserve browser failures separately from Python HTTPS.
7. Remove the temporary reservation and verify original router state. With the
   same supervision, reacquire ordinary DHCP without forcing the old IP. Verify
   actual resulting address, identity, native clients and output authority. Stop
   on a watchdog, unknown output/identity or unsafe cleanup; preserve breadcrumbs.
   One transition and one ordinary-DHCP cleanup cycle are the planned maximum.
   Additional mutations require a specific repaired defect and a documented
   amendment, never an attempt to accumulate eventual passes.

## Adversarial review and delivery

Challenge DHCP origin versus static assignment, exact MAC/device/boot/image,
old/new distinction, packet provenance and timestamps, raw USB framing, no hidden
commands/jobs, certificate/hostname continuity, native versus literal-IP reads,
actual production/Chrome evidence, failed-attempt retention, capture loss,
independent supervision and original-router/provider restoration. Test evidence
rejection paths and rerun affected deterministic checks after fixes. Reassess
until no actionable finding remains in the delivered changes; keep external and
physical acceptance blockers open rather than claiming closure.

Save a code review, executed results and sanitized evidence/hash manifest in
this repository. No credentials/captures/generated firmware enter Git. Update the
development entry point and report D1, B2, D2, bounded E1 and incomplete soak with
ownership and remaining work. Commit only reviewed owned files, push origin/devel,
verify actual remote parity and report remaining preexisting user changes.

## Execution refinement

The first fresh router request needed authentication. The user supplied explicit
sign-in authority; credentials are excluded from files and evidence. After
authentication, the attached table shows A's existing router label as
`phase11-4-d1-temporary`. Reuse that exact label for the temporary reservation
instead of changing persistent device-name metadata. The reservation table is
empty and `.247` is absent from the attached-client table.

The native Chrome Add saved A's exact temporary row, but Apply from the returned
reservation page produced HTTP 400. One targeted fresh-LAN-page Apply is allowed
before cleanup, because it tests the different form context returned by Add
versus a fresh direct LAN GET. Preserve both outcomes and do not infer a stale
form cause from this hypothesis alone. No Pico cycle follows a failed Apply.
