# Phase 12.4 portable transport contract and live-activation handoff

Execute this prompt in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Starting state and authority

Begin from clean `devel` at
`8644e60f50a796b00768a3a35c40aad9cfb38056`, initially equal to
`origin/devel`. Inspect the actual branch, status, HEAD and recent history before
editing, and preserve any later user changes. Do not reset, stash, switch
branches or discard work.

This prompt authorizes source, documentation and deterministic hardware-free
test changes in this repository, followed by one reviewed commit and push to
`origin/devel`. It does not authorize a Pico, USB, BLE or Wi-Fi radio operation;
flashing; host radio, service, trust-store or certificate installation changes;
contact with a physical endpoint; or RF output. Do not initialize or download
the absent BTstack dependency. Existing local pinned dependencies may be used
read-only for host tests and cross-builds.

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/implementation-plan.md`, `docs/development/README.md`,
`docs/development/phase12-plan.md`, `docs/development/phase12-3-review.md`,
`docs/development/network-control.md`, `docs/browser-api.md` and
`docs/protocol/WTP.md`. Preserve Phase 11 evidence as historical, assertion-bound
evidence; do not rewrite it as current-image acceptance.

## Code-review orientation

Review the portable provisioning profile, journal and manager, the runtime
profile selection, Pico flash/network/TLS integration, the Bluefy JavaScript
client and its mocked GATT tests. Inspect the actual retained SDK before making
any Bluetooth build claim.

The current boundary is:

- P12.1/P12.2 and the bounded hardware-free P12.3 infrastructure are complete.
- `bluefy.js` already emits a closed version-1 JSON command vocabulary over one
  command characteristic and expects correlated JSON notifications from one
  status characteristic.
- No owned C++ adapter currently parses that vocabulary or invokes
  `provisioning::Manager`; target BLE and SoftAP code must therefore not invent
  an independent protocol.
- `Manager::apply` validates and commits a replacement, but has no explicit
  fail-closed handoff for a later platform live activator.
- Authenticated BLE proof of possession, bonding/recovery policy, SoftAP policy,
  page-origin policy and private-key-at-rest policy remain unselected. Do not
  manufacture those policies in this tranche.
- The pinned Pico SDK records BTstack but the retained source is unpopulated, so
  an authenticated target GATT adapter cannot be built from the current inputs.

## Objective

Implement the next bounded hardware-free Phase 12 tranche: one strict,
transport-neutral C++ command adapter matching the checked-in Bluefy client and
one fail-closed live-activation handoff owned by the provisioning manager. This
must make the future BLE and SoftAP target adapters thin security/platform
adapters without enabling either radio path or claiming end-to-end provisioning.

Also repair any deterministic baseline blocker discovered during orientation
when it prevents the required checks. Do not weaken certificate, identity,
ownership or output-safety validation to make a test pass.

## A. Closed provisioning command contract

Add an owned C++ adapter under `src/provisioning/` that accepts a bounded JSON
command plus adapter-supplied `Authorization`, `Activity`, transport identity and
monotonic time, then calls the existing `Manager`.

The grammar must exactly match `src/provisioning/web/bluefy.js`:

- common fields: integer `version: 1`, string `operation`, exact 32-lowercase-hex
  `request_id`, `session_id` and `device_id`;
- `open`: no additional fields;
- `write`: nonnegative integer `offset`, boolean `final`, and canonical base64
  `payload` decoding to 1 through 64 bytes;
- `apply`: nonnegative integer `expected_generation`;
- `cancel`: no additional fields.

Objects are closed. Reject duplicate keys, unknown fields, unknown operations,
wrong scalar types, noncanonical base64, empty or over-64-byte fragments,
oversized commands, wrong device identity and values outside the implemented
integer bound. Do not accept a second spelling or silently normalize the wire
contract.

Return bounded, correlated version-1 JSON notifications. Successful and failed
responses must include `request_id`, a JSON boolean `ok`, the current committed
generation and replay indication. Include accepted byte count when useful and a
stable nonsensitive error code on failure. If no trustworthy request identifier
can be recovered, return no notification for the target adapter to spoof or
mis-correlate. Provide the exact identity-characteristic JSON expected by the
Bluefy client.

The adapter must never infer authentication from transport selection,
association or proximity. It consumes the existing `Authorization` supplied by
a future authenticated platform adapter. It must not log or return SSID,
password, certificate, key, CA or payload content. Scrub decoded fragment
buffers after dispatch.

## B. Fail-closed live-activation handoff

Add an optional portable activation interface to `Manager`. After successful
validation and transactional persistence of a genuinely new generation,
`Manager` may hand the validated profile and committed generation to that
interface while the existing idle/output checks still hold.

- No activation callback runs for rejected, interrupted or identical-profile
  no-op replacement.
- Success completes normally.
- Activation failure reports a distinct stable error, terminates the session,
  scrubs staged/profile material and invokes an explicit fail-closed hook.
- The newly committed generation remains authoritative after activation
  failure. Never restart, restore or advertise the superseded trust bundle.
- Replay of the same apply returns the original success or activation-failure
  result without invoking activation again.
- The interface may use profile data only during the callback; it must not
  retain views. Actual Pico Wi-Fi/TLS teardown/restart remains separate target
  work.

Keep the default construction path compatible with the already implemented
boot-only behavior: without an activator, persistence succeeds and activation
is deferred until boot.

## C. Deterministic tests

Extend hardware-free tests to cover:

- exact Bluefy open/write/apply/cancel commands over BLE and SoftAP labels;
- identity JSON and response correlation;
- malformed JSON, duplicate/extra/missing fields, wrong types/version/operation,
  wrong device, bad identifiers, command oversize, invalid/noncanonical base64,
  decoded empty/oversize fragments, offset/generation bounds and fragment order;
- unauthenticated/non-confidential/nonlocal/empty-principal admission and busy
  job/RF states through the adapter;
- exact duplicate replay and conflicting request-ID reuse;
- secret-free errors/status and fragment-buffer reclamation;
- activation success, identical-profile no-op, activation failure,
  fail-closed invocation, authoritative new generation after failure, replay
  without duplicate activation, and preservation of station/schedules/watermark;
- lifecycle, timeout, cancel, interrupted persistence and resource bounds already
  required by the Phase 12 matrix.

Keep the JavaScript mocked-GATT tests and C++ adapter contract mutually
consistent. Add a deterministic source-level check if needed to prevent the
fixed UUIDs, fragment bound or command spelling from drifting independently.

## D. Documentation and evidence boundary

Update the Phase 12 plan, implementation snapshot, architecture/contract or
development index where the new boundary is durable. Record a focused
`phase12-4-review.md` containing:

- exact starting source and dependency observations;
- implemented behavior and deliberately absent target behavior;
- validation results and the baseline blocker/repair, if any;
- first adversarial findings, repairs and second assessment;
- assertion-level Phase 11 impact;
- unresolved security/product decisions and remaining physical gates.

Do not describe the command adapter as authenticated transport, the activation
hook as Pico live reload, a cross-build as BLE/SoftAP evidence, or the Bluefy
page as approved for deployment. Phase 12 remains open.

## E. Validation

Use only documented commands and retained dependencies. Run:

- the focused provisioning C++ and Web Bluetooth tests;
- the complete host build/CTest suite, with the immutable Phase 11.7 drift guard
  recorded separately if it still has its documented expected failures;
- focused AddressSanitizer/UndefinedBehaviorSanitizer checks when supported;
- WTP/1 contract validation;
- all maintained Pico firmware link targets and both linked-image/layout checks;
- formatting, whitespace, secret-content and staged-inventory checks.

Any expired generated test credential must be repaired through deterministic
test-fixture lifecycle handling, not by disabling time validation or changing
deployment policy. Cross-build and host results remain hardware-free evidence.

## F. Adversarial review and publication

Review the complete attributable diff as an attacker and failure analyst. At
minimum challenge response spoofing/correlation, parser ambiguity, base64
malleability, integer truncation, secret lifetime, replay side effects,
activation-after-commit failure, superseded-trust resurrection, busy-state race
assumptions, unbounded allocations, browser/C++ drift, target overclaim and
generated-credential reproducibility.

Repair every actionable finding, rerun affected checks, then perform and record
a second adversarial assessment. Stage only attributable Phase 12 changes,
inspect the staged diff, commit once on `devel`, push to `origin/devel`, and
verify local HEAD, local `origin/devel` and remote `refs/heads/devel` agree.

Report the prompt path, code-review orientation, changes, validation, adversarial
findings/repairs, open choices, remaining target/physical gates and exact final
repository state.
