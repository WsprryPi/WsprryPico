# Phase 12 Raspberry Pi BLE and first-class TCP/WTP execution prompt

## Objective

Work in the WsprryPico repository on `devel`, beginning from commit
`47ba73b3a44851aff0582bbf378cdb840007d430`, and close the two transport needs
identified during Phase 12 review:

1. provide a supported Raspberry Pi/Linux operator workflow for the existing
   authenticated BLE local-control service; and
2. preserve, document, and verify authenticated TLS/TCP as a first-class WTP
   job-transfer and job-control transport alongside canonical USB CDC/WTP.

Do not reinterpret USB CDC being the reference transport as making TCP/TLS a
diagnostic-only or second-class path. USB CDC and TLS/TCP must carry the same
WTP/1 byte stream into the same portable protocol session and `JobService`.
RF waveform timing remains wholly local to the RP2350 after a complete job has
been accepted.

This is a focused Phase 12 slice. It does not authorize claiming all of Phase
12 complete, and it does not require production SoftAP implementation. Preserve
SoftAP and any remaining physical acceptance gates as explicit open work.

## Repository and state controls

- Work only in `/Users/lbussy/GitHub/WsprryPico`.
- Use `devel`; do not create a feature branch.
- Before editing, read `README.md`, `CONTRACT.md`, `docs/architecture.md`, the
  WTP protocol contract, the Phase 12 field-interface contract, the current
  Phase 12 plan, and the latest BLE local-control review.
- Confirm the checkout is clean and that local `devel` equals `origin/devel` at
  the starting commit. Preserve unrelated user work if the state differs.
- Do not modify WsprryPi or any other WsprryPi-family repository. They may be
  inspected read-only to verify interoperability claims.
- Keep owned implementation under `src/`, host tools under `scripts/`, tests
  under `tests/`, and durable operator/development guidance under `docs/`.

## Required implementation

### Raspberry Pi/Linux BLE client

Add a supported command-line client for Raspberry Pi OS/Linux using the native
BlueZ D-Bus API and dependencies already provided by the operating system. The
client must use the existing Phase 12 GATT service and must not create another
wire protocol, scheduler, job store, or authorization model.

The client must:

- require an exact BLE address and the full 128-bit WsprryPico device identity;
- connect only to that exact device and verify the identity characteristic
  before sending privileged commands;
- support BlueZ LE pairing with the existing Just Works enrollment policy,
  preserve the resulting bond, and avoid marking the peer globally trusted;
- use the existing encrypted provisioning and WTP characteristics, with the
  existing UUIDs, frame bounds, ordering rules, timeouts, and response matching;
- accept the application password only through a non-echoing prompt, never
  command-line arguments, environment variables, logs, or status output;
- support authorization, field status, Identify, controller-time update, and
  WTP `HELLO` plus `STATUS` over the GATT WTP stream;
- support the existing atomic profile-transfer transaction with strict local
  file controls, bounded input, canonical validation, cancellation on failure,
  and no disclosure of Wi-Fi or TLS secrets;
- fail closed for wrong identity, missing encryption/authorization, malformed
  frames, unexpected responses, CRC errors, timeouts, and ambiguous device
  selection;
- leave enrollment-window opening to the existing authenticated USB access
  command and explain that prerequisite clearly; and
- never provide an RF-starting shortcut. BLE WTP job execution, where used by a
  higher-level client, remains subject to the same device authorization,
  scheduler, interlock, and output-safety rules as USB and TCP.

Bluefy remains the selected iPhone browser client and its offline acceptance
path remains unchanged. The Raspberry Pi/Linux client is an additional
supported local/bench client, not a replacement for Bluefy and not evidence for
the iPhone/Bluefy acceptance gates.

### First-class authenticated TCP/WTP

Review the production network adapter, portable protocol/session path, startup
gates, tests, and documentation. Repair any mismatch that prevents this
contract:

- TCP transports the identical WTP/1 framed byte stream used by USB CDC.
- Production TCP accepts WTP only inside TLS 1.3 with ALPN `wtp/1` and valid
  mutual device-specific authentication. Plaintext and opportunistic downgrade
  are nonconforming.
- The TLS peer identity is converted to a transport principal; transport code
  does not invent protocol authorization or a second job-control implementation.
- USB and TCP terminate in the same portable WTP session and `JobService`.
- Network listeners remain default-off/product-gated and start only when their
  existing clock, credential, profile, and policy preconditions are satisfied.
- Documentation calls USB CDC the canonical/reference transport without
  describing TCP/TLS as provisional, diagnostic-only, or subordinate for
  supported job transfer and control.
- No hard-coded default TCP port or silent plaintext fallback is introduced.

If the implementation already satisfies these requirements, add or strengthen
tests and documentation rather than rewriting working code.

## Verification

Provide deterministic, hardware-free coverage for:

- BLE frame fragmentation/reassembly bounds and ordering;
- full device-identity verification and wrong-device rejection;
- password authorization without secret leakage;
- field status, Identify, controller-time, and WTP `HELLO`/`STATUS` exchanges;
- WTP CRC, command, sequence, and malformed-response failures;
- atomic profile open/write/apply/cancel behavior and strict local profile-file
  permissions/symlink/size validation;
- UUID and protocol-bound parity among firmware, Bluefy, the Linux client, and
  the durable contracts; and
- the shared USB/TCP WTP session and `JobService`, TLS 1.3, ALPN, mutual-auth,
  default-off, and fail-closed network invariants.

Run the complete available host test suite, protocol validators, documentation
and release checks, source/link checks, and the pinned target build checks
described by `docs/development/README.md`. Do not invent passing hardware
evidence from mocks or host tests.

When Candidate A and the `wspr5` Raspberry Pi are available, a bounded,
RF-inhibited live exercise is authorized only after proving the exact device,
firmware, access state, output-inhibited state, and cleanup plan. It may open a
temporary enrollment window, pair the exact `wspr5` controller, exercise only
non-transmitting local-control commands, and then verify the retained bond and
restored safe state. Do not start a job, enable RF, alter the RF path, consume a
finite RF campaign allowance, or weaken any interlock. If those preconditions
cannot be proved, stop the live portion and report the remaining physical gate.

## Documentation and evidence

Add a Raspberry Pi/Linux BLE operator guide covering prerequisites, exact
commands, enrollment, security boundaries, retained pairing, recovery, and what
the workflow does and does not qualify. Update the README, contract,
architecture, Phase 12 plan/field-interface material, and current review only as
needed to make these facts unambiguous:

- Bluefy is the selected iPhone client;
- Raspberry Pi/Linux is an additional supported BLE client;
- authenticated TLS/TCP is a first-class WTP job-control transport;
- USB CDC remains the canonical/reference transport;
- RF timing is local; and
- unexecuted physical, clean-image, interoperability, RF, or SoftAP gates remain
  explicitly open.

Record exact commands and results. Distinguish source inspection, host tests,
target build evidence, live BLE evidence, and RF evidence.

## Review, repair, and completion

After implementation and initial validation, perform an adversarial review that
actively searches for:

- secret exposure, unsafe profile-file handling, weak identity binding, pairing
  with an unintended device, global BlueZ trust changes, stale notifications,
  response confusion, unbounded waits or allocations, and cleanup failures;
- divergence between the Bluefy and Linux BLE clients or the firmware GATT
  contract;
- TCP plaintext/downgrade paths, missing mutual authentication, ALPN bypass,
  listener startup before prerequisites, duplicate job-control logic, or USB/TCP
  semantic drift;
- documentation that overclaims hardware or RF evidence; and
- regressions outside this focused slice.

Fix every actionable finding, rerun affected and complete checks, and then
perform a second adversarial assessment. Do not declare closure until the second
assessment has no actionable findings. Record both passes and any repaired
findings in the durable review artifact.

Finally, confirm the repository state, commit the complete focused change on
`devel`, push `devel` to `origin`, and independently verify local HEAD, upstream,
and remote parity. Report the prompt artifact, implementation and documentation
changes, both adversarial assessments, exact validation results, live-hardware
evidence or its explicit absence, commit identifier, push result, and remaining
Phase 12 gates.
