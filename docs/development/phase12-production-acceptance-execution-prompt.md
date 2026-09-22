# Phase 12 production integration and physical acceptance execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state and authority

Begin from clean `devel` at
`7451a4047677cf2f91d790ea5aa9eec1a9015f38`, equal to `origin/devel` at the
start of this tranche. Inspect branch, status, HEAD, upstream and the current
remote-tracking reference before editing and again before publication. Preserve
all later work. Do not reset, stash, switch branches, discard changes, rewrite
history or substitute another checkout.

This prompt authorizes source and test changes, maintained documentation,
deterministic host builds, cross-builds using already retained pinned
dependencies, the finite RF-inhibited Stage A device work admitted below, an
adversarial review/repair/reassessment cycle, one resulting commit and a push to
`origin/devel`.

After this prompt was rendered, the operator separately authorized GitHub Pages
publication from `devel:/docs`. That later authorization permits the exact
credential-free Bluefy release and maintained documentation to be published; it
does not authorize any credential, capture or private acceptance packet.

The live authority is intentionally bounded. It permits operations only on an
exactly identified Pico 2 W candidate, BLE operation, creation and removal of
the candidate SoftAP, candidate firmware flash/reboot actions, and the minimum
explicit test credentials and trust changes recorded in the private acceptance
packet. It does not authorize RF output, Stage B, arbitrary physical endpoints,
unbounded radio scans, permanent host configuration changes, silent trust
installation, dependency downloads, application installation, App Store
account actions, publication other than the requested Git push, or disclosure
of credentials/private captures. Existing services, routes, radios, trust and
device firmware must be restored or their exact nonrestored state reported.

If no exact Pico 2 W, iPhone/Bluefy pair, accepted offline page origin/delivery,
credential set, trust-restoration path or authoritative output-inactive state is
available, record the missing admission item and stop the corresponding live
stage. Do not replace physical evidence with mocks, cross-links, a different BLE
client or inferred acceptance. Complete safe source work and report the gate.

## Read and orient first

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `SECURITY.md`,
`docs/architecture.md`, `docs/implementation-plan.md`,
`docs/development/README.md`, `docs/development/phase12-plan.md`,
`docs/development/phase12-field-access-contract.md`,
`docs/development/phase12-3-review.md`,
`docs/development/phase12-4-review.md`,
`docs/development/phase12-5-review.md`,
`docs/development/phase12-physical-acceptance.md`,
`docs/development/network-control.md`, `docs/development/standalone.md`,
`docs/browser-api.md` and `docs/protocol/WTP.md`. Treat the Phase 11.7 joint
review and current 11.5/11.6 closure records as authoritative over historical
then-open prose.

Review the current production main loop, target composition, Pico network/TLS
lifecycle, profile/access/reset journals, provisioning manager/activation
coordinator, access/session/field policy, controller-time arbiter, GATT framing
and transport, SoftAP HTTP admission, indicator adapter, checked-in Bluefy page,
browser API, one `JobService`, scheduler and RF/output authority. Inspect the
actual retained Pico SDK 2.3.1, BTstack, CYW43, lwIP, Mbed TLS and Arm toolchain
before using an API. Do not fetch, initialize or update a dependency.

Begin with a written source review identifying recent changes, usable
capabilities, production gaps, storage/layout constraints, SDK limitations and
the exact evidence boundary. Preserve that review in the final Phase 12 result.

## Objective

Complete the production integration needed to make the selected Phase 12 field
contract an actual RF-inhibited Pico 2 W path, then execute as much of the finite
physical acceptance plan as its admission record permits. BLE/Bluefy remains the
primary local provisioning/management path; SoftAP/Safari remains an independent
no-infrastructure fallback. Both feed the existing browser/WTP semantics and
single `JobService`. They never create a second scheduler, job protocol, timing
owner, RF owner or output-state authority.

The standard candidate remains RF-inhibited. Phase 13 and the optional Phase 12
Stage B RF coexistence work are outside this execution.

## Production integration requirements

### Composition and lifecycle

- Split CYW43 initialization from station-profile startup so a valid station MAC,
  BLE and blank/recovery SoftAP are available without a station profile while
  invalid identity or access state remains fail closed.
- Initialize the CYW43/BTstack stack exactly once using the pinned SDK ownership
  model. Start and service the candidate GATT, SoftAP, DHCP/mDNS/HTTPS and LED
  adapters on core 0 without blocking USB, network, `JobService`, watchdog or RF
  authority polling.
- Construct the access controller only from a healthy access record and checked
  full device/station-MAC identity. Both-erased adoption requires a live physical
  or explicit USB-local confirmation and authoritative idle/output-off state.
  Corrupt, pending-reset, missing-identity and failed-bond-erasure states expose
  only the selected recovery authority.
- Instantiate the provisioning manager, strict command adapter, credential
  validator and delivery-safe activation coordinator in the production image.
  Preserve fixed bounds, replay behavior, secret scrubbing and exact terminal
  response release/five-second fallback.

### Live activation

- Implement a Pico `ActivationPlatform` that owns only network runtime. Its
  `prepare -> activity recheck -> quiesce -> install -> restart` sequence must
  never abort, release, clear or infer job/RF state. It closes old admission at
  commit, rejects both generations during the delivery boundary, loads the
  committed profile, reconfigures station/SNTP/server identity and starts only
  the new generation.
- Make prepare/install/restart/fail-closed idempotent and boot-recoverable. Any
  failure leaves the committed generation authoritative and all network
  admission closed until recovery. Late superseded DNS/SNTP/TLS callbacks are
  ignored. Preserve station, schedules, watermark and E10 byte-for-byte except
  during separately confirmed full operational erase.
- Add deterministic target-independent lifecycle tests and target symbol/layout
  guards for success, acknowledgement, lost reply, five-second timeout, activity
  race, prepare/quiesce/install/restart failure, repeated callbacks, reboot and
  resource return.

### BLE field service

- Production-enable the pinned BTstack GATT service with LE Secure Connections
  Just Works, one active encrypted connection, the selected enrollment window,
  provisional-bond cleanup, four authorized bonds, epoch checks and explicit
  application-password authorization.
- Retain fixed bounded framing in both directions. Provisioning commands remain
  limited to their selected vocabulary and sizes. Add a separately identified,
  bounded WTP stream channel for ordinary local job/control operations through
  the existing `wtp::Endpoint` and `JobService`; do not translate it into a new
  job API. Require the same bond principal and exact WTP session for resume.
- Confirm ATT indication completion before releasing disruptive activation.
  Disconnect, timeout, malformed frames and revocation scrub reassembly state
  without adapter-specific job transitions.
- Expose identity, authorization, controller-time, Identify and nonsensitive
  bounded status required by the checked-in Bluefy page without logging secrets.

### SoftAP field service

- Implement deterministic AP start/stop around the selected no-profile, field
  mode, recovery, join grace, token/reply retention and station-fallback causes.
  Use the exact station-MAC-derived SSID and current local password with
  WPA2-AES or stronger target-supported mode. The ready LED begins only after
  the AP netif and service are actually usable.
- Supply the bounded implementation-recorded DHCP subnet and exact manual Safari
  route. Do not intercept arbitrary DNS. Blank generic HTTP is read-only identity,
  build/wire version and nonsensitive status; it accepts no password, time,
  profile or job mutation.
- On a provisioned device, provide server-authenticated pre-clock HTTPS for
  login and controller time only, then normal password-cookie browser control
  through the existing Browser API/`JobService`. Confine password authority to
  the AP interface. Station HTTPS and raw TLS-WTP remain mTLS-only.
- Enforce exact Host/Origin, Fetch Metadata, explicit request header and content
  type checks; `Secure`, `HttpOnly`, `SameSite=Strict` cookie properties; four
  bounded sessions; inactivity, absolute deadline and owner-only grace; one WTP
  session per token; no session eviction or ownership transfer.

### Time, indicator, gestures and reset

- Wire authenticated BLE and provisioned pre-clock SoftAP observations into the
  existing controller/SNTP arbiter. Preserve nonce/device/principal/session
  binding, uncertainty and age limits, same-principal refresh, source priority,
  disagreement latching/recovery and unsynchronized boot.
- Run the onboard CYW43 LED only through the core-0 indicator controller. Prove
  Off, actual-SoftAP-ready 200/1800 ms heartbeat and five-cycle Identify pattern,
  including priority, duplicate nonextension, busy and write-fault behavior.
- Do not claim BOOTSEL-at-boot application gestures. On Pico 2 W the ROM consumes
  a held BOOTSEL during reset and the application does not boot to observe it;
  the retained pinned SDK supplies no accepted flash-safe RP2350 runtime reader
  for this contract. This tranche therefore uses exact USB-local commands as the
  only implemented confirmation/enrollment path. Any future physical gesture
  requires a separately designed input or a proven flash-safe runtime mechanism,
  visible cancel/confirmation behavior and fresh physical acceptance.
- Complete crash-safe reset recovery, exact store preservation/clearing and
  post-intent boot suppression. A reboot never reopens an enrollment window.

### Bluefy offline artifact

- Produce a repository-owned, self-contained versioned page with no remote
  scripts, analytics or credential service. Include visible revision/protocol,
  deterministic SHA-256 inventory and a cache-first service worker/manifest for
  an HTTPS origin. Cache installation must be explicit and verifiable before
  field use; stale or mixed revisions fail closed. Temporary password/profile
  material is cleared on terminal paths and never placed in persistent browser
  storage.
- Retain the existing provisioning flow and add bounded controller time,
  Identify and local WTP/browser operations only where the target implements
  them. Unsupported wire versions and wrong full device identity fail before a
  mutation.
- Hardware-free tests must validate the asset inventory, no-remote dependency
  rule, cache manifest/version match, framing, secret clearing and offline cache
  behavior. Actual Bluefy/iOS cache and Web Bluetooth behavior remains physical
  evidence.

## Deterministic acceptance before hardware

Add or update tests for every affected lifecycle: wrong device/principal/
interface, unauthenticated or unencrypted access, malformed/oversize/out-of-
order/duplicate/interrupted input, timeout/cancel/replay/concurrency, bond and
session capacities/reclamation, credential replacement and superseded trust,
transactional journal/reset interruption, controller-time disagreement,
activation delivery/failure, station/schedules/watermark preservation,
busy/output-unknown rejection, service cause changes and exact LED patterns.

Run the documented host configure/build and aggregate CTest suite with the
immutable Phase 11.7 guard separated, the WTP validator, focused browser/web/
contract/layout/image checks, focused ASan/UBSan tests where supported and every
affected RP2350 target using the exact clean retained dependencies. Inspect map,
FLASH/RAM size, stack-usage and retained symbols. A compile/link is not target
runtime evidence.

## Physical Stage A admission and execution

Use `phase12-physical-acceptance.md` as the controlling finite matrix. Before a
device operation, create a private credential-free admission/result directory
and record source, dependency/tool, UF2/hash, board/serial/device ID/station MAC,
boot/config/profile/access generations, output-off proof, iPhone/iOS/Bluefy
version, page origin/hash/cache state, credentials/trust scope, finite durations
and restoration plan. Keep passwords, keys, raw sectors and authenticated
traffic out of Git.

Execute only the exact RF-inhibited Stage A cases whose prerequisites and
operator interactions are available. Preserve attempts and failures. Stop a case
on wrong identity/image, unknown output, unexpected RF, storage ambiguity,
resource/stack fault, trust resurrection, unavailable restoration or exhausted
budget. Do not run Stage B.

At the end, prove authoritative RF-inhibited/output-off state, no owner,
provisioning closed, intended SoftAP/station/trust restoration and healthy
journals. Disconnect or reboot alone is not restoration proof. Retain a
credential-free machine-readable result and review; record every unexecuted row
as an explicit physical gate.

## Adversarial review and repair

Review the complete diff and results adversarially for double initialization,
interface-confused authority, optional-client-certificate bypass, evil-twin and
wrong-device behavior, session fixation, provisional-bond persistence, replay,
activation ordering, callback generation binding, trust rollback, secret
retention, flash overlap, BOOTSEL/QSPI safety, HTTP/cookie/CSRF boundaries,
network/job ownership side effects, output-state inference, resource exhaustion,
evidence substitution and overclaiming.

Repair every actionable finding, rerun all affected checks, then perform a
second adversarial assessment. Preserve failed attempts and original findings.
Do not call Phase 12 physically complete if any required Stage A assertion is
unexecuted or failed.

## Records, commit and publication

Update the Phase 12 plan, physical plan, architecture/contract/README and
development commands to match actual evidence. Add a production-integration
review plus a credential-free physical result/review when live work is admitted.
State exact source/dependency/tool/device identities, commands, test counts,
sizes, findings/repairs, Phase 11 assertion-level revalidation and every open
gate. Historical Phase 11 records remain immutable.

Finish with formatting, `git diff --check`, source/credential hygiene and a full
diff review. Commit the intended changes once, push `devel` to `origin`, and
independently verify local HEAD, upstream and `origin/devel`. Report the rendered
prompt path, changes, validation, physical admission/result, adversarial
findings/repairs, commit, push/parity and exact remaining gates.
