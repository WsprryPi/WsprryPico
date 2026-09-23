# Phase 12 remaining production and RF-inhibited acceptance execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state, authority and evidence boundary

Begin from clean `devel` at
`c84fa157b93493cf0c28fa2e96c30e0beeabe7e2`, equal to `origin/devel` at the
start of this tranche on 2026-09-23. Inspect branch, status, HEAD, upstream and
the current remote-tracking reference before editing and before publication. Preserve all
later work; do not reset, stash, discard changes, rewrite history or substitute
another checkout.

Do not install a source-drift sentinel while implementation is still changing.
Complete the source work, tests and adversarial review first, then commit the
candidate to freeze its identity. Build and flash only that exact clean commit.
If an actionable later finding changes source, create a new candidate commit
and repeat only the affected physical rows against that new identity. A
post-freeze source/evidence binding may detect movement away from the committed
candidate; it must not pretend unfinished source is immutable.

This prompt authorizes source, test and maintained-documentation changes;
hardware-free builds and tests; cross-builds using the already retained pinned
dependencies; and finite RF-inhibited work on the already identified Phase 12
Pico 2 W candidate. That finite work may include a clean committed-image flash,
BLE and Wi-Fi operation, creation/removal of the candidate SoftAP, explicit
credential transfer when the required client and private profile exist,
reboots, controller-time and LED observations, bounded fault/resource checks
and final restoration. It also authorizes one temporary NetworkManager profile
on an otherwise unused `wspr5` Wi-Fi interface solely for the candidate SoftAP;
remove it and return that interface to disconnected state before closure. It
also authorizes adversarial review, repairs, traceable source/evidence commits
and a push to `origin/devel`.

It does not authorize RF output, Stage B, arbitrary endpoints, unbounded scans,
silent or permanent host/phone trust-store changes, App Store actions,
dependency downloads, credential/private-key publication, weakening an
acceptance threshold or replacing target evidence with mocks. Use only the
standard RF-inhibited image for production claims. A separately identified and
hashed inhibited fault image or hardware-free harness may prove only its named
fault branch. Disconnect, reboot, terminal state, LED state or missing ACK is
not output-off proof.

The exact iPhone model, iOS release, Bluefy App Store identity/version and page
cache state must come from the actual client. If that client or an operator-only
interaction is unavailable, retain the affected physical row as `NOT_EXECUTED`;
do not guess it or substitute another browser. Credentials, private keys, raw
access sectors, authenticated captures and private acceptance packets remain
outside Git.

## Read and review before editing

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `SECURITY.md`,
`docs/architecture.md`, `docs/implementation-plan.md`,
`docs/development/README.md`, `docs/development/phase12-plan.md`,
`docs/development/phase12-field-access-contract.md`, the P12.3-P12.5 reviews,
`docs/development/phase12-physical-acceptance.md`,
`docs/development/phase12-production-acceptance-review.md`,
`docs/development/network-control.md`, `docs/development/standalone.md`,
`docs/browser-api.md` and `docs/protocol/WTP.md`.

Review the recent `16d8f0e` through `c84fa15` changes and the complete current
production graph: access/profile/reset journals, one `JobService`, scheduler,
output authority, runtime profile overlay, CYW43 ownership, station/SNTP/TLS
server, provisioning manager, delivery-safe activation, GATT framing and CCCD
repair, controller-time arbiter, SoftAP policy/HTTP primitives, indicator and
the repository-owned Bluefy release. Record the current capabilities, gaps,
storage/layout bounds, retained dependency identities and evidence limits before
implementation.

## Current reviewed boundary

- P12.1-P12.2 and P12.4-P12.5 are accepted only in their documented
  hardware-free scopes. P12.3 is `CLOSED_SCOPED`, not physical acceptance.
- P12.6 production-wires encrypted BLE provisioning, controller time,
  Identify/status, the unchanged WTP/1 GATT stream, a network-only live
  activator, the indicator, the deterministic Bluefy artifact and the SoftAP
  DHCP/mDNS/HTTP/HTTPS browser path. SoftAP credential provisioning and reset
  administration remain source gaps. The SoftAP continuation is build/test
  evidence only at the start of this execution.
- Candidate identity/adoption, preservation, advertising and one online
  retained-bond Bluefy authorization exchange passed. That exchange proves
  neither a fresh password nor credential provisioning.
- A clean RF-inhibited `d52a2fa6a3a3` image passed Candidate A/wspr5 native-Pi
  BLE identity, controller-time, status and WTP HELLO/STATUS checks. That is not
  iPhone/Bluefy, SoftAP, job execution, credential activation, TCP physical
  interoperability or RF evidence.
- Fresh iPhone pairing/password, offline Bluefy reuse, full profile transfer,
  BLE WTP job execution, production SoftAP target control, reset/recovery,
  fault/resource/soak and most remaining Stage A rows remain open.
- The standard image must remain RF inhibited. Phase 13 remains separate.

## Objective and production requirements

Advance the selected field-access contract to the strongest evidence actually
available for its current RF-inhibited BLE and SoftAP field path without
creating a second job service, scheduler, protocol, timing owner, RF owner or
output-state authority. Correct maintained documents that still describe the
now-wired SoftAP path as a source gap. Extend the bounded USB helper only as
needed to issue the existing exact device-bound access/status commands; it must
still identify the device before mutation and must not expose credentials.

### BLE/Bluefy

- Preserve and regress the already production-wired encrypted one-connection
  GATT, retained-bond/application-password authority, four-bond policy, fixed
  provisioning framing, CCCD admission, controller time, Identify/status,
  delivery-confirmed activation and separately bounded unchanged WTP/1 stream.
- Keep the BLE endpoint backed by the one `JobService`; preserve HELLO,
  session/principal resume, replay, lease, STATUS and terminal semantics. Never
  translate WTP into a second job API or accept WTP before application
  authorization and indication subscription.
- Keep provisioning and WTP receive/output buffers separately bounded and scrub
  terminal secret-bearing data. A disconnect causes only the ordinary endpoint
  disconnect and WTP lease behavior.
- Change the checked-in Bluefy source/release only when required by an
  implemented operation. Keep it deterministic, self-contained and
  release-inventoried; clear password, profile and transient request material on
  every terminal path.

### SoftAP/Safari

- Review and regress the production connection of `SoftApCoordinator`,
  `PicoSoftAp`, `SoftApHttpAdmission` and the existing browser API. Start the AP
  only for the selected no-profile, recovery, field-mode, fallback, join-grace
  or retained-session causes. The ready LED begins only when the AP netif and
  service are usable.
- Use the station-MAC-derived SSID and current local password with WPA2-AES.
  Record the fixed DHCP subnet and manual Safari URL. Do not intercept arbitrary
  DNS and do not treat WPA association as application authority.
- Blank bootstrap HTTP is read-only identity/build/wire/status. It accepts no
  password, time, provisioning or job mutation.
- With a valid device-bound TLS identity, provide server-authenticated pre-clock
  login/time and normal cookie-authorized browser operations. Station HTTPS and
  raw TLS-WTP remain mTLS-only. Preserve exact Host/Origin/Fetch-Metadata/header/
  content-type checks and `Secure; HttpOnly; SameSite=Strict` cookies.
- Map an authorized SoftAP session to exactly one WTP session and the existing
  browser/`JobService` semantics. Enforce four sessions, inactivity/absolute
  expiry, owner-only grace, no eviction and resource reclamation.
- Preserve the applying SoftAP terminal response separately before activation
  closes network admission; never reuse the BLE delivery assumption blindly.

### Time, indicator, activation, recovery and safety

- Route authenticated BLE and provisioned pre-clock SoftAP time samples through
  the existing controller/SNTP arbiter. Preserve nonce/device/principal/session
  binding, fixed 250 ms phone allowance, age/uncertainty limits, priority,
  disagreement and recovery rules. Report source/age/uncertainty without
  overstating phone accuracy.
- Run the CYW43 LED solely from the core-0 indicator controller. Preserve Off,
  actual-ready 200/1800 ms SoftAP heartbeat and five-cycle Identify behavior,
  including priority, duplicate nonextension, busy and write-fault reporting.
- Keep profile activation network-only and delivery safe. Old/new network
  admission remains closed from commit until exactly-once activation; restart
  loads only the committed generation. Late superseded DNS/SNTP/TLS callbacks
  cannot regain authority.
- Do not claim a BOOTSEL-at-boot application gesture. Retain exact USB-local
  confirmation unless a different input is explicitly designed and accepted.
  Wire only recovery/reset operations that meet durable-intent ordering, idle/
  output-off admission and store-preservation rules; otherwise leave the exact
  gesture/reset row open.

## Deterministic validation before live work

Add focused tests for every new path and affected failure: unauthorized or
unencrypted GATT, missing CCCD, wrong principal/device/session, WTP partial/
combined/oversize/error/reconnect behavior, controller-time replay/timeout/
disagreement, SoftAP cause transitions, login/cookie/CSRF/expiry/capacity,
blank/pre-clock/normal surfaces, delivery ordering, resource return and absence
of job/RF side effects. Update target link retention and GATT handle-contract
checks.

Run the documented host build and aggregate CTest suite. If the Phase 11.7
closure audit treats authorized later-phase source evolution as historical-
evidence corruption, repair that invalid repository-freeze assumption while
keeping its fixed candidate-to-tested interval and retained artifact checks;
then run the WTP validator;
focused JS/release/contract/layout/image checks; supported focused sanitizers;
and all affected RP2350 targets using the exact clean pinned SDK, BTstack,
picotool and Arm toolchain. Inspect image bounds, FLASH/RAM, stack usage and
retained symbols. A build/link is not live BLE, Wi-Fi, timing or RF evidence.

## RF-inhibited physical execution

Use `phase12-physical-acceptance.md` as the controlling finite matrix. Before
mutation, make a private evidence directory and record exact source, dependency,
tool, UF2/hash, candidate serial/device/station-MAC/boot identities, access/
profile/config generations, authoritative empty/unowned/output-inactive state,
phone/Bluefy/page identities, admitted credentials/trust scope, finite time
budgets and restoration plan. Preserve all attempts and failures.

Execute only rows whose source support, client interaction, credentials and
restoration path are actually available. Do not turn an unavailable iPhone,
visual observer, private provisioning packet or implemented reset surface into
a failed test; record the corresponding row as `NOT_EXECUTED` with its exact
missing prerequisite. The immediate sequence is:

1. After the source/test review, commit the candidate to freeze its identity.
   Build that exact clean commit with the
   pinned Pico SDK 2.3.1 and clean BTstack revision. Use the already retained,
   ignored Candidate A device-bound network credential directory at
   `config/local/network/phase11-4-fd6127d1/server-mac-suffix` and port `18443`
   so this physical image can exercise the provisioned SoftAP HTTPS surface.
   Record public certificate identity and build inputs without printing,
   copying to Git or otherwise disclosing the private key. This is still the
   standard RF-inhibited image, not a fault or RF image.
2. Hash the image, reflash Candidate A USB serial `0BF4B4AEC9FFB344` only,
   verify the load and re-establish exact identity, inhibited engine, empty/
   unowned/inactive output and preserved station/schedule/watermark/access state.
   Do not mutate comparator `CDDBF8767C506C07`.
3. On `wspr5`, use an interface that is disconnected before the test while
   retaining SSH on Ethernet and the existing infrastructure association on
   its other Wi-Fi interface. Request SoftAP through the exact device-bound USB
   command, associate only to the station-MAC-derived SSID using the current
   local password, and verify DHCP `192.168.4.1/24`, gateway, AP-interface mDNS,
   presented certificate identity and hostname. Do not install a CA or alter a
   host trust store; use a test-process-local CA file or direct public
   certificate comparison.
4. Verify blank port 80 is read-only and rejects mutation. On HTTPS verify
   login failure and success, exact cookie attributes, Host/Origin/fetch/header
   enforcement, controller-time if the 250 ms bound is feasible, field status
   and ordinary `HELLO`/`STATUS`/ownership operations through the one
   `JobService`. Use only empty or RF-inhibited simulated state and release any
   acquired owner. Preserve failures; do not relax latency or security checks.
5. Record the exact iPhone/iOS/Bluefy/page release identity. Verify online
   install, then disable infrastructure Wi-Fi and cellular data and prove the
   accepted page/release is reused offline, but only if that actual client and
   operator interactions are available.
6. Exercise fresh-password authorization where applicable, complete credential
   transfer, committed activation, reboot, station association, DHCP/mDNS and
   new-only TLS trust. Retain private credentials outside Git.
7. Exercise BLE and SoftAP controller time, Identify and actual-ready LED
   timing; then ordinary BLE WTP and SoftAP browser/local control through the one
   `JobService` using only RF-inhibited simulated jobs.
8. Run admitted reset/recovery, storage/activation fault, busy/output-unknown
   rejection, resource-bound/reclamation and bounded soak rows. A fault harness
   never becomes candidate-image evidence.
9. Log out, delete the temporary NetworkManager connection, disconnect the
   test-only interface, reboot if needed to clear volatile SoftAP state and
   verify the AP is no longer advertised within a bounded scan.
10. End with the standard RF-inhibited image, output authoritatively inactive,
   empty/unowned state, provisioning closed, SoftAP stopped, intended station/
   trust state restored and every journal healthy.

Stop on wrong identity/image, unknown output, unexpected RF, storage ambiguity,
trust resurrection, unavailable restoration, memory/stack/DMA fault or exhausted
finite budget. Do not run Stage B.

## Adversarial review, repair and publication

Review the complete diff and evidence for authority confusion, double CYW43 or
TLS ownership, BLE/SoftAP principal crossover, session fixation, replay,
provisional-bond persistence, wrong-interface trust, indication/HTTP response
ordering, callback-generation drift, trust rollback, secret retention, flash
overlap, HTTP/cookie/CSRF errors, WTP ownership side effects, output inference,
resource exhaustion and evidence overclaiming.

Repair every actionable finding and rerun affected checks. Then perform a fresh
second adversarial assessment. Preserve original findings and failed attempts.
Do not call Phase 12 closed while any mandatory production path or required
Stage A assertion is unexecuted or failed.

Update the plan, physical plan, production result/review and high-level status
documents to the exact implemented and observed boundary. Finish with
formatting, `git diff --check`, credential/private-data hygiene and a full diff
review. Commit the intended changes, push `devel`, independently verify local
HEAD/upstream/`origin/devel`, and report the prompt path, implementation,
validation, physical disposition, adversarial findings/repairs, commit/push
parity and exact remaining gates.
