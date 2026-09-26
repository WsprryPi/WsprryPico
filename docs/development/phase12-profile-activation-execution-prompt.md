# Phase 12 frozen Field-GATT profile-activation execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`.

## Objective

Close only Step 1 of the remaining Phase 12 roadmap: physically exercise the
frozen Field-GATT/1 profile-provisioning and network-only activation workflow on
Candidate A with both supported clients, the repository-owned Bluefy page on the
operator's iPhone and the native Raspberry Pi/Linux client on `wspr5`.

The accepted result must prove, on an exact clean committed RF-inhibited image:

1. fresh local-password `profile_step_up` is bound to the exact field session,
   staged profile session, apply request, device identity and current generation;
2. the public-default path additionally requires the exact identity-bound USB
   confirmation within the same bounded profile session;
3. a valid profile is committed and activated exactly once, survives reload,
   selects the new generation, associates to the intended station network and
   exposes only the newly selected TLS identity;
4. the native-Pi client physically transfers and activates a canonical profile
   of exactly 7,168 bytes, while 7,169 bytes is rejected without target mutation;
5. wrong-password, missing-confirmation, cancellation/disconnect and malformed
   or oversize attempts fail closed, clear staged authority and preserve the last
   committed generation; and
6. all terminal paths scrub client staging, reclaim target resources and leave
   the target RF-inhibited, empty, unowned and output inactive.

This is a bounded Phase 12 physical-acceptance tranche. It does not close Bluefy
offline-cache acceptance, broad BLE WTP job control, controller-time/LED/reset,
SoftAP, coexistence, TCP/TLS physical interoperability, Stage B, RF, spectral,
timing, reliability or release qualification.

## Repository and candidate controls

- Start from clean `devel` at
  `8432afd56e0df5a516cd88fd28befc91225c6ac8`, equal to `origin/devel` when
  this work was authorized. Preserve later work if the state differs.
- Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`, the
  Phase 12 plan, physical plan, production review, field-access contract,
  frozen Field-GATT/1 contract and vectors, native-Pi guide and prior Bluefy/
  native-Pi reviews before changing source or operating hardware.
- Preserve unrelated user work. Do not reset, stash, rewrite history or change
  another WsprryPi-family repository.
- Commit this prompt before producing the physical candidate. Build only from a
  clean committed revision. If a repair changes firmware or Bluefy assets,
  commit a new candidate, rebuild, rehash, reflash and repeat every affected
  physical row.
- Run the documented complete host suite, WTP validator, Bluefy release checks,
  focused sanitizers and Pico 2 W target/link builds before physical admission.
  Record exact source, SDK/toolchain/picotool revisions, build options, image
  size and UF2 SHA-256. Builds and mocks are not physical evidence.

## Authority and hard safety boundary

This prompt authorizes the requested repository changes and checks; exact-
serial Candidate A flashing; RF-inhibited BLE, USB Console, station Wi-Fi,
provisioned SoftAP status and TLS/WTP verification; temporary private profile
construction outside Git; profile journal mutation; bounded reboots; native-Pi
and operator-assisted Bluefy provisioning; credential-generation replacement;
negative/failure cases; final restoration; adversarial review and repair;
documentation; commit; and push to `origin/devel`.

It does **not** authorize RF output, `LOAD`, `ARM`, Stage B, dependency downloads,
arbitrary scans, App Store changes, permanent host/phone trust-store mutation,
local-password changes, bond removal, access reset, provisioning reset, full
operational erase, station/schedule/watermark changes, operation of Candidate B,
or disclosure of passwords, cookies, private keys or complete profile contents.

Stop immediately on wrong board/serial/device/image, active or unknown output,
nonempty/owned job state, unhealthy journal, unexpected RF, trust resurrection,
unbounded resource growth, ambiguous generation, loss of the intended station
or management path without an admitted recovery, or exhausted finite authority.
Preserve failed attempts as evidence; never replace the first result with a
silent retry.

## Exact equipment and initial boundary

- Candidate A: Pico 2 W USB serial `0BF4B4AEC9FFB344`.
- Candidate A device ID: `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Candidate A station MAC: `88:a2:9e:0a:60:df`.
- Expected BLE address: `88:A2:9E:0A:60:E0`; verify it live rather than treating
  this historical address as identity.
- Expected hostname: `wsprrypico-0a60df.local`.
- Native client host/controller: `wspr5`, using its exact recorded Bluetooth
  controller and Ethernet management path.
- Candidate B USB serial `CDDBF8767C506C07` is observation-only and must not be
  flashed, rebooted, paired, provisioned or otherwise mutated.
- The standard candidate must report `inhibited-standalone-simulator`, empty,
  unowned and `output_active=false` before and after every mutating case.

The live preflight found Candidate A on the earlier RF-inhibited firmware
`4377d2ded8e3`, boot `331e555683a5d6c6122735a07883e0a8`, profile generation
0, healthy access generation 3 with the public default active, configuration
journal sequence 72 and watermark sequence 12. Treat that as the preserved
pre-run baseline, not as current-candidate acceptance.

## Secret handling and evidence

- Keep private profile files in owner-only, nonsymlinked locations outside Git.
  Generate evidence from lengths, hashes, generations and pass/fail results,
  never from secret-bearing file contents.
- The operator enters the local password directly into Bluefy or a non-echoing
  native-client terminal. Do not place it in command arguments, environment
  variables, shell history, automation output, screenshots, chat or evidence.
- Read station credentials and TLS key material only from the already ignored
  private configuration. Do not print them. Do not copy private material into a
  repository artifact.
- Store raw credential-bearing logs only in a private temporary directory with
  owner-only permissions, if unavoidable. The committed result must be
  credential-free and use redacted stable error names.
- Before every commit, scan the complete diff and new files for SSIDs,
  passwords, PEM bodies, private-key markers, cookies and raw profile JSON.

## Admission and clean candidate preparation

1. Confirm local `devel`, upstream and `origin/devel` parity and a clean tree.
2. Record the exact host, `wspr5` boot, Bluetooth controller, USB serial links,
   candidate/comparator identity and all retained toolchain revisions.
3. Run the full hardware-free validation matrix and target builds described in
   the development baseline. Resolve failures before target mutation.
4. Build the standard RF-inhibited Pico 2 W image from clean committed HEAD,
   inspect flash/RAM/layout and retained provisioning/access/activation/GATT/
   network symbols, and hash the UF2.
5. Read Candidate A's authoritative Console `INFO`, `STATUS`, `STORAGE`,
   `ACCESS STATUS` and `BLE STATUS`. Require healthy storage/access, exact
   identity, empty/unowned state, inhibited engine and inactive output.
6. Use serial-targeted picotool load/verify on Candidate A only. Re-read the
   same authoritative state, record the changed boot ID and verify profile,
   access, station, schedules, watermark and the public-default state were
   preserved as intended.
7. Verify the deterministic Bluefy release ID displayed by the checked-in page
   exactly matches the release assets built from the candidate source.

## Private profile preparation

Prepare two valid profiles selecting the already intended Candidate A station,
time server and device-bound TLS bundle:

- an ordinary canonical profile for the Bluefy run; and
- a canonical profile of exactly 7,168 UTF-8 bytes for the native-Pi maximum
  boundary run.

The maximum profile may add only validator-accepted, semantically inert PEM
whitespace without changing keys, certificate chain, SAN, EKU, device ID,
station credentials, time server, hostname or port. Parse and validate the
result with the same client rules before use. Prove it is exactly 7,168 bytes
without printing it. Construct a corresponding 7,169-byte input and prove both
clients reject it locally before opening or mutating a target profile session.
The target-side 7,169-byte rejection remains covered by frozen conformance tests;
do not weaken a client merely to transmit a prohibited secret-bearing payload.

## Native-Pi physical sequence

Use the exact current `scripts/wsprrypico_ble.py` on `wspr5`, verify its SHA-256,
the exact adapter/address and full device ID, and never set BlueZ `Trusted`.
Use an owner-controlled interactive terminal for all non-echoing password entry.

1. Establish the baseline generation and retained/new-bond disposition with
   `inspect` and authorized `status`; open enrollment through exact-device USB
   only if a genuinely new bond requires it.
2. Stage a valid profile and deliberately enter a wrong fresh password. Require
   rejection, bounded cancel/cleanup, unchanged generation, no activation and a
   healthy reconnect.
3. Stage a valid profile with the correct fresh password but deliberately omit
   USB confirmation. Require bounded `confirmation_timeout`, cancel/cleanup,
   unchanged generation and healthy reconnect.
4. Open another valid transaction, disconnect/cancel before apply, reconnect and
   prove no staged authority or provisional generation survived.
5. Establish accepted UTC with the native client's authenticated `sync-time`
   command and verify a non-`none` field time source before certificate-validity
   admission. The unprovisioned target cannot obtain station SNTP yet; this is
   a prerequisite for profile apply, not the broader controller-time matrix.
6. Run `provision` with the exact 7,168-byte canonical profile. Confirm that the
   client reports the identity-bound USB instruction, issue
   `ACCESS CONFIRM PROFILE fd6127d11d6aca42a9905fa3fb1bf1d5` on Candidate A's
   Console within the bounded confirmation window, and require an accepted
   apply response before treating activation as committed.
7. Verify exactly one generation increment, delivery-safe exactly-once
   activation, expected BLE disconnect if activation closes the link, journal
   health and successful post-activation authorized reconnect.
8. Verify station association, DHCP, certified hostname, device-bound server
   certificate/key, client-CA authentication, controller time/SNTP behavior and
   WTP `HELLO`/read-only `STATUS` through the new runtime without starting work.
   Verify no prior credential generation is selected.

## Bluefy/iPhone physical sequence

Use the operator's already installed Bluefy application and the exact checked-in
page. Record the iPhone, iOS and Bluefy versions reported by the operator and the
visible release ID. This tranche requires online page delivery; it does not claim
offline-cache acceptance.

1. Connect only to Candidate A, verify the full device ID, record whether iOS
   reused the retained bond, and authorize. Retained-bond authorization is not
   fresh profile step-up.
2. Repeat the wrong-password negative. Require explicit rejection, no commit,
   unchanged generation and successful clean reconnect.
3. Repeat the missing-USB-confirmation timeout. Require no commit, unchanged
   generation and successful clean reconnect.
4. Cancel or disconnect one staged transfer before apply. Require no commit and
   no surviving staged authority after reconnect.
5. Enter the ordinary valid profile and the current local password directly in
   Bluefy. Issue the exact USB confirmation during the page's bounded wait.
   Require an accepted apply response and distinguish expected activation link
   closure from browser `operation_failed` before reporting success.
6. Verify exactly one additional generation increment, exactly-once activation,
   reboot/reload selection, authorized reconnection, station/TLS operation and
   rejection of superseded runtime authority.
7. Confirm the page cleared password, station password, certificates and private
   key fields after every success and failure. Close and clear the Bluefy tab at
   the end. Do not infer offline-cache acceptance from an online session.

If an operator-dependent action cannot be completed, continue independent safe
checks and record the row `NOT_EXECUTED` with the exact prerequisite. Do not
replace Bluefy evidence with native-Pi evidence or vice versa.

## Cross-client and restoration assertions

- Across both successful applies, require monotonically increasing generations,
  no duplicate activation, no fallback to generation 0 or a superseded runtime
  generation, preserved station configuration, schedules and watermark, and no
  job/RF ownership side effect.
- Re-read Console `INFO`, `STATUS`, `STORAGE`, `ACCESS STATUS` and `BLE STATUS`
  after each failure and success. Record bounded counters and resource return
  without retaining payloads.
- Verify the active profile can be read only as generation/state metadata; no
  Console, BLE or web status may disclose secrets.
- End with the clean standard candidate, intended active profile generation,
  healthy profile/access/config/watermark journals, enrollment closed, no
  provisional authority, no owner, empty job state, RF-inhibited engine,
  authoritative inactive output and no unexpected SoftAP cause. Disconnect the
  native client and Bluefy, clear the Bluefy tab and remove temporary profile/
  client copies after evidence hashes and lengths are recorded.

## Deterministic checks and result artifacts

Create a credential-free machine-readable result and a narrative review. They
must bind every attempt to source commit, UF2 hash, firmware/boot/device/serial/
MAC/client/release identity, starting and ending generations, observed stable
error/result name, journal health, target state and restoration outcome. Mark
each assertion `PASS`, `FAIL`, `NOT_EXECUTED` or `NOT_APPLICABLE`; never collapse
partial rows into a pass.

Rerun after physical work:

- complete host CTest suite;
- focused provisioning, field-access, browser, contract and native-Pi tests;
- supported sanitizer suite;
- WTP contract validator;
- Bluefy release-integrity and source/published parity checks;
- Pico 2 W standard and provisioning/field-access link builds;
- Python, JavaScript and JSON syntax checks;
- C/C++ formatting for changed source;
- Markdown links for changed documentation; and
- `git diff --check`, private-material scan and full staged-diff review.

## Adversarial review, repair and publication

Perform an attacker/failure-analyst review after the first execution. At minimum
challenge wrong-device selection, retained-bond versus fresh-proof confusion,
request/session/generation substitution, confirmation-window extension, cancel
after accepted apply, lost terminal response, duplicate callback/activation,
disconnect cleanup, provisional-bond retention, 4,096-byte regression, 7,168/
7,169 boundaries, local file/symlink/permission races, secret retention/logging,
profile rollback, superseded trust, certificate/key/SAN mismatch, resource leaks,
false output-off inference and incomplete restoration.

Repair every actionable source, client, documentation or test finding within
this tranche. Commit a new clean candidate before any repair-dependent physical
rerun. Rerun affected deterministic and physical rows, then conduct a fresh
second adversarial assessment. Stop only when no actionable finding remains or
an external prerequisite is explicitly recorded; do not call an unexecuted row
accepted.

Update the Phase 12 plan, physical plan, production review, native-Pi review and
top-level status only to the exact evidence obtained. Phase 12 remains open
unless every separate completion gate is later accepted. Commit all attributable
changes to `devel`, push `devel` to `origin`, fetch the remote and independently
verify local HEAD, upstream, remote-tracking and `ls-remote` parity. Report the
prompt path, candidate identities, every physical result and failure, repairs,
both adversarial assessments, final restoration, validation totals, commit and
push/parity state, plus remaining Phase 12 gates.
