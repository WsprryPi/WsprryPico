# Phase 12.3 Pico field-access closeout execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state and authority

Begin from `devel` at
`cf6792258de2d2d1060a6ca9e22ac79f866ac06b`, equal to `origin/devel` at the
start of this tranche. Preserve the uncommitted operator-selected Phase 12
field-access contract and its coordinated documentation changes. Inspect the
actual branch, status, HEAD, upstream and remote-tracking reference before
editing. Do not reset, stash, switch branches, discard or overwrite later work.

This prompt authorizes source, tests, maintained documentation, deterministic
hardware-free builds, adversarial review, repair, one resulting commit and a
push to `origin/devel`. It does not authorize flashing, USB/device access,
debugger access, Bluetooth or Wi-Fi radio operation, SoftAP creation, physical
endpoints, host route/radio/service/trust-store changes, certificate
installation, RF output, dependency downloads or publication other than the
requested Git push.

## Read and orient first

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `SECURITY.md`,
`docs/architecture.md`, `docs/implementation-plan.md`,
`docs/development/README.md`, `docs/development/phase12-plan.md`,
`docs/development/phase12-field-access-contract.md`,
`docs/development/phase12-3-review.md`,
`docs/development/phase12-4-review.md`,
`docs/development/phase12-5-review.md`,
`docs/development/phase12-physical-acceptance.md`,
`docs/development/network-control.md`, `docs/browser-api.md`,
`docs/protocol/WTP.md` and `docs/development/standalone.md`. Prefer current
Phase 11 closure records over historical prose that described then-open work.

Review the profile/manager/command/activation/runtime sources, the checked-in
Bluefy page, browser API and HTTP/TLS server, Pico network lifecycle, identity,
UTC discipline, LED ownership, standalone/profile journals, every firmware
target and linker layout. Inspect actual retained Pico SDK, BTstack, CYW43,
lwIP, Mbed TLS and toolchain sources before choosing APIs. Use only already
retained pinned dependencies. Do not initialize, update, fetch or download a
submodule. If an exact recorded dependency is unavailable, fail that evidence
row explicitly rather than silently substituting another revision.

## Objective and evidence boundary

Close the P12.3 source slice against the operator-selected field-access and
security contract. Implement the portable policy and Pico target adapters,
connect them to a hardware-free cross-linkable candidate runtime, and prove the
deterministic source behaviors below. Do not infer Bluetooth, iPhone, SoftAP,
TLS-client, LED, timing, storage-on-silicon, RF or coexistence acceptance from
host tests or an Arm link.

The production image must retain the single `JobService`, WTP/browser schemas,
lease/ownership rules, output authority and local RP2350 job timing. BLE and
SoftAP are transports and principals, not a second scheduler, job protocol or
RF authority. Transport loss never proves output inactive and may not directly
abort, release or clear owned work.

## Required implementation

### Durable local-access state and layout

- Add a portable two-sector, commit-last local-access journal at a Pico adapter
  boundary. It owns the local-password verifier/material required by WPA,
  monotonically increasing access epoch, authorized bond metadata, persistent
  field-mode selection and durable `reset_pending` transaction state.
- Default password derivation is exactly `wspr-` plus the final six lowercase
  hexadecimal characters of the checked station MAC. Invalid station MAC or
  full device identity fails closed; do not substitute constants or zeros.
- Customized passwords are 8-63 supported printable characters. Password and
  epoch replacement commit atomically. Never expose a password through status,
  errors, logs, replay records or maintained evidence.
- Reserve access state at `0x3f3000`-`0x3f4fff`, retain BTstack at
  `0x3f5000`-`0x3f6fff`, profile at `0x3f7000`-`0x3fafff`, standalone at
  `0x3fb000`-`0x3fefff` and E10 at `0x3ff000`; end every maintained linked
  application at `0x3f3000`.
- Implement confirmation-gated all-erased initialization and crash-safe
  `reset_pending` coordination. Credential-only and access/provisioning reset
  preserve station, schedules and watermark; full operational erase changes
  them only under its explicit contract. Version profile selection so a
  source-mode/tombstone decision is transactional and superseded trust cannot
  revive after interruption.

### Portable access/session policy

- Implement bounded transport-neutral policy for one active encrypted BLE
  connection, one provisioning session, four retained authorized bonds and
  four SoftAP application sessions.
- BLE uses Just Works at the stack layer and the local-access password at the
  application layer. Model a 120-second enrollment window, provisional-bond
  promotion/deletion, epoch binding, fifth-bond rejection, explicit removal,
  fresh-password step-up and required physical or explicit USB-local
  confirmation while the public default is active.
- SoftAP application tokens contain at least 128 random bits, are device,
  boot-ID and epoch bound, and support 15-minute inactivity, fixed 12-hour
  absolute expiry and the exact armed/running owner-only grace from the
  canonical contract. Enforce one WTP session mapping per token and four-live-
  session admission without eviction. Expose an HTTP-cookie description only
  as `Secure; HttpOnly; SameSite=Strict` with no persistent expiry.
- Bind every step-up/confirmation to the full device ID, principal, logical
  session, exact operation, nonce, generations and canonical mutation digest;
  make it single-use with a maximum 120-second life. Cancel, logout,
  disconnect, timeout, wrong-operation, replay and reboot invalidate the
  corresponding volatile authority.
- Recheck job/RF activity for every idle-only access, bond, trust, reset and
  activation mutation. Owner, loaded, armed, running, failed, output-active and
  output-unknown states reject without adapter-specific abort/release effects.

### Offline UTC, SoftAP state and indicator policy

- Add a portable field-access coordinator that represents no-profile,
  persistent field mode, authorized 120-second join/login grace, station-
  failure fallback within 60 seconds, recovery, live token/reply retention and
  30-second stable-station withdrawal. Reboot clears transient causes only.
- Model the blank-device read-only HTTP surface separately from provisioned
  pre-clock HTTPS. A blank SoftAP accepts no password, controller time,
  profile, trust or job mutation. Provisioned pre-clock HTTPS accepts only
  identity, challenge, login, nonsensitive status and bounded controller time.
- Add controller-time admission with full-device/session/source binding,
  nonce/replay protection, bounded age and uncertainty, a forward-only
  bootstrap, source priority and an explicit large-step refusal/recovery path.
  Do not weaken the existing synchronized-UTC requirement for normal mTLS or
  scheduled work.
- Add an indicator state machine. Identify is a bounded explicit pattern;
  SoftAP slow heartbeat begins only when the AP is actually ready, stops when
  readiness/cause ends and has lower priority than fault/output safety
  indication. No LED state grants authority.

### Pico adapters and runtime integration

- Implement Pico flash media for the access journal and keep all flash writes
  at existing safe core/lockout boundaries.
- Implement a BTstack GATT adapter for fixed project UUIDs with encrypted-link
  admission, one connection, bounded bidirectional framing/reassembly,
  correlated terminal indications, disconnect cleanup and retained-bond hooks.
  Compile it only against the exact recorded BTstack revision.
- Implement a CYW43 SoftAP lifecycle adapter with WPA2-or-stronger
  configuration, bounded DHCP subnet, manual-Safari/mDNS route, blank read-only
  service separation and provisioned HTTPS/session hooks. Association alone is
  never an application principal and the captive sheet never accepts secrets.
- Extend HTTP response support only as necessary for strict cookie headers.
  Preserve Host/Origin, content type, explicit request-header and Fetch Metadata
  mutation checks. Password-cookie authority is confined to the SoftAP
  interface; station HTTPS and raw WTP remain mTLS.
- Implement the P12.5 `ActivationPlatform` for owned network-runtime
  prepare/quiesce/install/restart/fail-closed actions. Use the delivery callback
  or five-second timeout exactly once, prohibit job/RF mutation and ensure the
  committed generation immediately supersedes old admission.
- Update the checked-in Bluefy page for full-device confirmation, password
  authorization/enrollment, controller time, Identify, provisioning and bounded
  local WTP/browser operations. Keep the page runnable without a native iOS app
  and do not embed or log secrets. Bluefy release/origin integrity and exact
  iOS interoperability remain physical acceptance evidence.
- Connect the implementation to a maintained hardware-free candidate target or
  production path as appropriate. Do not enable any radio during validation.

## Deterministic acceptance

Add independent tests for default/custom password lifecycle; wrong device,
principal, transport assertions and epoch; provisional/retained/fifth-bond
behavior; login/cookie/session capacity; inactivity/absolute/owner-only grace;
malformed, oversize, duplicate, interrupted, timeout, cancel, replay and
concurrency; confirmation binding; controller-time source/nonce/uncertainty/
step rules; SoftAP causes and withdrawal; LED priority/readiness; credential
replacement and superseded-trust rejection; crash points in every journal/reset
commit stage; and byte-for-byte station/schedule/watermark preservation.

Exercise owner, loaded, armed, running, failed, output-active and output-unknown
rejection with no ownership/RF side effects. Prove fixed session, bond, frame,
payload, replay and timer bounds and resource reclamation after every terminal
path. Add layout, symbol-retention and target-source drift guards.

Run the documented host configure/build and CTest suite, the WTP/1 validator,
focused web tests, focused sanitizer tests where supported, and all affected
firmware/linkcheck targets with existing pinned dependencies. Inspect maps,
FLASH/RAM sizes and relevant retained symbols. A compile or link is not live
transport, storage or timing evidence.

## Review, records and finish

Perform an adversarial review of authorization precedence, session fixation,
credential leakage, replay, wraparound, power-loss recovery, trust rollback,
flash overlap, principal/transport confusion, ownership side effects,
connection loss, activation delivery ordering, resource exhaustion and claims.
Repair every actionable finding and rerun affected checks. Perform a second
adversarial assessment; do not declare source closure while an actionable
finding remains.

Update the Phase 12 roadmap, physical plan and maintained contracts to reflect
only evidence actually obtained. Write
`docs/development/phase12-3-review.md` with exact source/dependency/
tool identities, commands, results, sizes, findings and repairs, Phase 11
assertion-level revalidation, excluded evidence, unresolved implementation
items and remaining physical gates. P12.3 may be source-complete while physical
acceptance remains open; do not call Phase 12 complete.

Finish by checking `git diff --check`, reviewing the full diff and sensitive
content, committing all intended Phase 12.3 and previously selected contract
changes once, pushing `devel` to `origin`, and independently verifying local
HEAD, upstream and `origin/devel`. Report the commit, push/parity result,
validation, adversarial repairs, exact limitations and repository state.
