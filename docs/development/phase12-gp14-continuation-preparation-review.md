# GP14 reset and AP orchestration preparation review

Status: **B PREPARED AND INACTIVE; PAUSED FOR FRESH OPERATOR READY** (2026-10-02).

The operator answered **Execute** to the
[reset/AP continuation](phase12-gp14-reset-ap-continuation-prompt.md), after
requiring preparation to stop until they acknowledge readiness. The cumulative
authority is 17 attempts and 12 RF jobs, with each additional job at most
20 seconds. The complete wspr5 record still has **15 attempts and ten jobs**.
The initial human Ready led to a premature preflight call, not an acquisition.
That readiness is no longer used. B is now loaded and prepared as recorded
below; a fresh Ready is required immediately before the first acquisition.
There is no new RF job or physical pass. Phase 12 remains `OPEN_PARTIAL`;
GP14 default enablement remains off.

## Prepared source and operator pause

[The runner](../../scripts/phase12_gp14_rf.py) now has an explicit offline
`--prepare` action. It reads evidence and reports `WAITING_FOR_OPERATOR_READY`,
without USB, network sockets, receiver access, a Ready record or an acquisition.
The operator may return later; preparation has no response timer and launches
nothing in the background. Both remaining cases reach this checkpoint.

Only after a fresh human Ready may `--acknowledge-ready` write one row-specific
record. It binds the exact controller directory, candidate identity, packet,
runner source and cumulative accounting. `--run --led-cue --ready-file ...`
must consume that record exactly once, before hardware access, within five
minutes of acknowledgement. Missing, reused, expired, future, wrong-case,
wrong-packet, wrong-source and wrong-accounting records refuse admission.
This is an operator workflow gate, not cryptographic proof of who typed Ready.
The orchestrating agent must never issue the acknowledgement while waiting or
infer it from Execute or Done.

An exclusive nonblocking campaign lock spans admission, charging, acquisition
and receiver finalization. A concurrent invocation is refused rather than
queued to launch after the operator leaves. Only `quick_reset` and `long_ap`
are admitted by this continuation, with a local LED cue and no readiness tap.
Every acquisition remains separately charged; possibly sent ARM is charged
before writing and never replayed.

The immutable fifteen-attempt checkpoint binds all original attempts and their
assessments. A partial mirror, missing record, altered history or incomplete
acquisition cannot lower the counters. `--packet-file` explicitly selects the
reviewed `3e1337074003` packet without replacing older retained packets. The
firmware remains the already reviewed clean image, not a new dirty build.

## Review findings and repairs

1. The Mac mirror initially held only eleven attempts/eight jobs. A read-only
   wspr5 inspection confirmed fifteen/ten. Missing JSON evidence was copied
   into the existing ignored directory without overwriting existing files.
   Full checkpoint validation now refuses this undercounting failure mode.
2. The local top-level packet still selected `62ae4c2c2567`. Current admission
   requires the exact reviewed source and UF2 hash; explicit selection uses
   `packet-release-3e13370.json`. wspr5's selected image hash matches the
   [accepted image record](phase12-gp14-rf-review.md).
3. The old no-input helper accepted only `active_stop`. A separate resolver
   handles the named historical quick-reset trial 15, verifies no gesture or
   fault, exact WTP admission/finite completion, unchanged settings and the
   healthy complete receiver capture. It preserves the original artifacts,
   charges and `independent_rf_pass=false`; it grants no automatic retry.
4. An initial added check assumed INFO contained `status.job_id`. Retained
   evidence proved that field absent. The repair binds the actual WTP
   LOAD/ARM responses and terminal history instead. Fixtures use that actual
   schema and reject foreign or ambiguous admission.
5. Independent Ready records alone allowed concurrent accounting checks.
   The exclusive campaign lock closes that race. A regression proves a second
   acquisition is refused without hardware access or consuming its Ready.
6. Readiness used to be orchestration convention only. The durable one-use
   gate, explicit inert preparation and source/accounting binding now enforce
   the runner boundary. A failed start consumes its acknowledgement and
   attempt, not a job when ARM was never reached; its failed assessment stops
   later admission.

Adversarial reassessment covered these repairs, freshness and replay,
counter exhaustion, concurrent admission, legacy resolutions, actual INFO
schema, wrong identity/image, receiver integrity and the no-hardware pause.
No remaining actionable source finding was identified within preparation.
That does not close either outstanding physical row.

## Checks and build environment

- Documented baseline `bash scripts/check_host.sh`: 91/91 passed before the
  additional orchestration test registration.
- Expanded Xcode host build with retained pinned Mbed TLS/lwIP: **108/108
  passed**, including the new CTest target and the actual TLS/Plain LAN tests.
- `python3 tests/gp14_rf_orchestration_tests.py`: **15/15 passed**, also under
  `python3 -O`; assertions are not required for the runner's safety guards.
- WTP contract validator, Python compilation, changed-document relative
  links and whitespace checks pass.
- Default inhibited, GP14 opt-in inhibited, normal RF and explicit RF
  acceptance cross-builds pass with retained SDK 2.3.1
  `079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1.
  Linked BOOTSEL topology, guarded stacks, heap hooks, RAM renderer and RF
  worker checks pass. Acceptance controls are present only in the selected
  acceptance variant and absent from the normal RF variant.

Host checks used `source scripts/xcode_env.sh`, pinned local
`WSPRRY_PICO_TEST_MBEDTLS_PATH`/`WSPRRY_PICO_TEST_LWIP_PATH`, CMake/Ninja and
CTest in `build/phase12-gp14-continuation-host`. Initial socket-restricted tests
failed startup; they passed with loopback permission. A subsequent run lacking
the Xcode environment failed three compiler-dependent tests. The complete
correct-environment run passes all 108; neither failure is device evidence.

New simultaneous Pico configurations collided in the shared picotool
population cache. A serial retry attempted a network clone and failed; no
download succeeded. SDK population removed its generated cached source before
the failed clone; that source was restored from another
clean retained copy at exact pinned revision
`6f6458d792b93685a11423b244a585eaa99eafcf`. The successful new builds import
the retained picotool 2.3.0 executable through an ignored task-local CMake
include, avoiding FetchContent entirely. No SDK or tools were installed.
Development images include dirty identity and are not deployment candidates;
the retained clean `3e1337074003` image remains selected for the physical rows.

## Waiting checkpoint and remaining work

The complete local mirror passes both offline commands:

```sh
python3 scripts/phase12_gp14_rf.py build/phase12-gp14-rf-b-20260930 \
  --packet-file build/phase12-gp14-rf-b-20260930/packet-release-3e13370.json \
  --case quick_reset --prepare
python3 scripts/phase12_gp14_rf.py build/phase12-gp14-rf-b-20260930 \
  --packet-file build/phase12-gp14-rf-b-20260930/packet-release-3e13370.json \
  --case long_ap --prepare
```

These report fifteen attempts/ten jobs and no hardware access. The controller
copy was also verified and prepared on wspr5 without altering the old helper
or issuing hardware actions. No Ready record was created at that source-only
checkpoint.

At the source-only checkpoint B's last restoration was inhibited
`615888e5364b`; no USB or LAN preflight had refreshed it. The live preparation
below subsequently completed the required path/identity confirmation, fresh
backup, authorized deployment/readback and distinct synchronized boot without
an RF job. On the operator's return only a short readiness refresh and the
one acquisition remain; do not repeat deployment merely to resume waiting.

The first session is a quick tap under 400 ms at the local LED cue; the second
is a 12–15-second hold followed by AP association/read-only page proof if
needed. Independent IQ cutoff assessment, settings comparison, inactive
cleanup, inhibited restoration and final physical adversarial review remain
required. An unexpected result stops the campaign. Default enablement remains
conditional on both rows passing; the broader Phase 12 gates remain open.

The unrelated README, CONTRACT, architecture, browser API, pin-assignment and
transmitter-application work retains its original content hashes and is
excluded from the preparation commit. No Candidate A, wspr4, GPIO, USB device,
receiver or RF operation occurred in the source-only preparation. The
subsequent named B operations are recorded below.

## Live preparation completed after premature Ready

The operator replied Ready and confirmed the unchanged closed conducted
60 dB path on 2026-10-02. The agent called the operator in before completing
device preparation. The operator was then released from watching the Pico;
no acquisition or Ready record was started, and that earlier Ready must not
be reused. Future preparation must finish before requesting the physical tap.

Read-only controller ownership checks found no B USB user or WTP connection.
B was inhibited `615888e5364b`, healthy and scheduling-disabled, with saved
profile/access generations 5/1. An attempted Plain LAN HELLO was reset before
any ROM entry or image write. An alternate reference USB inventory timed out
at its first WTP exchange. B subsequently reported `lan_wtp_mode=plain`,
`lan_wtp_ready=false` and an unsynchronized clock. Using an acquisition LAN
handshake without checking the baseline readiness gate was a preparation
error; these observations do not establish a new device defect or RF finding.
The stopped preflight and failed inventory remain private evidence.

The corrected baseline preparation uses the exact inhibited firmware's
guarded USB BOOTSEL command. The reviewed source checks unowned/inactive
authority and confirmed engine disable before acknowledgement and again
before ROM entry. A refusal, uncertain reply or absent ROM device is not
forced or replayed. The resulting full flash backup also proved the exact
guarded firmware: all 6,578 baseline ARM UF2 payload blocks match.
The fresh 4 MiB backup SHA-256 is
`e77aa61396cda525c1ad2d437e69ac30ed4f52cec7cc302261839e816c8b7d99`;
it was independently retained and verified on the Mac before loading.

Serial-targeted load/verify of retained acceptance `3e1337074003` succeeded.
A full programmed-image readback matches all 6,274 ARM payload blocks;
all 57,344 reserved bytes and exact saved profile/access/scheduler settings
remain identical. The checker excludes only the exact hash-bound picotool
absolute-family ignored block, not arbitrary out-of-range payloads. Positive
baseline readback and four rejection checks passed: changed payload, shortened
flash, truncated image and removed metadata block.

One acknowledged USB REBOOT prepared distinct healthy boot
`13f36788c9f2670f1e2dd5c197653c48`. Fresh station/time readiness, exact Plain LAN
HELLO identity, GET_CLOCK admission, and empty/unowned/inactive STATUS passed.
The identity-bound cue READY check passed without flashing the action cue.
The preparation process has exited; no receiver, RF job, Ready record or
background acquisition was started. Counts remain **15 attempts/ten jobs**.

Private evidence is in `build/phase12-gp14-rf-b-20260930/` and its matching
wspr5 directory, under `preflight-continuation-16`,
`preflight-continuation-16-usb-rom` and `deployment-continuation-16`.
No old record was overwritten. Candidate A, wspr4 and unrelated services
were not changed. B is currently the acceptance image, idle and prepared;
it has **not** been restored again to the inhibited baseline. Final inhibited
restoration remains mandatory after the bounded physical campaign or its
cancellation. Both physical rows remain open. On the operator's return,
refresh readiness without another image load, and require a fresh Ready
record before the one quick-reset acquisition.

Adversarial reassessment verified the exact baseline reset guard/readback,
local backup barrier, target/image binding, reserved settings, one non-replayed
preparation reset, complete helper termination and unused Ready gate. No
remaining actionable preparation finding was identified. This establishes
prepared hardware, not an RF pass or default enablement.
