# Phase 12 composition preparation

Status: preparation only; no physical execution or acceptance. These scripts
never configure networks, flash, reset, provision, load, arm or transmit. A
future hardware packet must separately approve USB device control and each
operator-driven pressure case. Use Candidate B only. Never run historical
Phase 11 observers with hard-coded Candidate A identity or engineering TLS
against a consumer Plain LAN image.

## Exact inputs and observer

Create a private JSON plan with schema `phase12-composition/1`, board `B`,
engine `inhibited-standalone-simulator`, full committed `source_commit` (40
lowercase hex), exact `image_sha256` (64 hex), `device_id` and fresh `boot_id`
(32 hex each), and exact INFO `firmware` version. These values come from the
approved manifest and newly authorized identity readback, never sample IDs.
Select `mode=consumer` with `carriers=[usb,plain_lan]`, or `mode=engineering`
with `carriers=[usb,ble,tls_wtp,https]`. Each composition needs its own plan,
image/profile/client evidence and authorization; passing one does not pass the
other. There is no automatic TLS fallback.

Declare `duration_s=7200`, `cadence_s=30`, `max_gap_s=45`, `quiet_s=960`,
`max_simulated_jobs=12`, `max_job_duration_s=60`, `rf_jobs=0`,
`flash_cycles=0`, `pool_return_tolerance=0`, `stack_min_margin_bytes=256`,
and `heap_return_tolerance_bytes=1024`, plus `core0_stack_capacity_bytes` from
the exact linked ELF/map, before the first observation. The
checker permits a predeclared heap allowance up to 4096 bytes, but widening it
after observing a leak is prohibited. `pressure_cases` must be exactly:
`maximum_sessions`, `maximum_framing`, `busy_mutation`, `disconnect_reclaim`,
`provisioning_close`, `flash_serialization`, in that order.

Offline validation (safe now):

```sh
python3 scripts/phase12_composition_audit.py --plan PRIVATE_PLAN.json
```

After separate approval only, use the exact B USB by-id console in the packet:

```sh
python3 scripts/phase12_composition_capture.py --run --plan PRIVATE_PLAN.json \
  --approval-packet PRIVATE_OBSERVER_APPROVAL.json \
  --console /dev/serial/by-id/usb-WsprryPi_WsprryPico_EXACT_B_SERIAL-if00 \
  --output PRIVATE_NEW_CAPTURE.jsonl
```

The output must not exist. The observer requests INFO only, creates a private
exclusive JSONL log, checks exact source revision/version/device/boot and
selected wire mode, and requires disabled inactive inhibited engine. It records
241 bounded samples over two hours. It stops immediately on identity change,
resource-schema mismatch, allocation/pool/guard/fault errors, timeout or device
loss. It neither reconnects the network nor resets the device to hide a failure.
Each sample retains exact serial JSON bytes as hexadecimal, their SHA256,
and the decoded INFO plus canonical decoded-object hash. Duplicate keys and
nonfinite values are rejected. Evidence ends as
`CAPTURE_COMPLETE_REVIEW_REQUIRED`, never acceptance.

## Directed pressure and two-hour composition procedure

Warm up and establish baseline with all clients disconnected, provisioning
closed, shared job authority empty/unowned and healthy storage. Do not restart
between baseline and final samples. Retain raw INFO throughout; independent
carrier observers must record exact HELLO/device/boot, framing, selected wire
mode and principal identity. INFO alone cannot prove these assertions.

After the warmed baseline, execute each bounded pressure case exactly once
within the approved two-hour window (minutes 0–20 and 40–100):

1. Maximum sessions: reach the actual declared capacities (network two,
   retained SoftAP four, BLE one where exposed), then exactly one excess
   connection/request per pool. Verify bounded refusal and reclamation. Do not
   mistake retained-session capacity for four simultaneous TCP clients.
2. Maximum framing: one maximum accepted frame and one boundary-exceeding
   rejection per supported carrier. Record lengths, replies and unchanged
   shared job authority. Use existing protocol limits, not invented sizes.
3. Busy mutation: one owner drives loaded, armed and running simulator states;
   each other supported principal attempts one competing mutation per state.
   Rejections must preserve owner/job/state. Up to three complete simulator
   jobs per carrier; at most 12 total, each at most 60 seconds, never RF.
4. Disconnect/reclaim: disconnect each carrier once, verify lease behavior and
   bounded buffered/session reclamation. No automatic network manipulation.
5. Provisioning close: one explicitly approved temporary setup transaction,
   cancelled before durable save, with transient keys/buffers scrubbed. This
   is not approval for credentials changes or destructive reset.
6. Flash serialization: retain proof from the separately named inhibited fault
   fixture's finite approved stages. The soak observer generates zero flash
   loops. Zero journal failures are required in the ordinary production soak;
   intentional fault outcomes belong exclusively in the fixture ledger.

During the two hours, place directed composition interactions in minutes
0–20 and 40–100. Reserve minutes 20–36 for sixteen uninterrupted minutes of
network/BLE inactivity. USB INFO sampling may continue; do not let an HTTPS
status poll, keepalive or BLE interaction refresh the session being tested.
Observe natural fifteen-minute reclamation. Reserve minutes 100–120 for
all-carrier disconnect, provisioning closure, resource return and final stable
empty/unowned/inactive state. Observe readiness/time boundaries at 30/60/90
seconds through separate declared stimuli; never change time policy or infer
RF admission from a host simulator.

Compare final heap and pool use to warmed baseline using the predeclared
allowances; require zero new allocation failures, stack guard faults, pool
errors, storage faults, reboots or active output across every sample. Preserve
peak/high-water counters (they need not return); used resources must return.
The named BTstack host API pools must report measured occupancy, zero
failures/faults and individual return to baseline. Controller-owned buffers
and largest-contiguous-allocation probes remain explicitly unmeasured;
successful allocation high water does not establish contiguous headroom. Flash attempt/byte counters describe attempts, not durable success.

## Evidence audit and remaining independent assertions

The offline `--capture` normalizer maps raw records to schema
`phase12-composition-evidence/1` accepted by `phase12_composition_audit.py`.
The evidence binds canonical sorted compact plan JSON SHA256. Each normalized
sample includes exact identity/engine, elapsed time, retained raw artifact
hash, output/guards/storage/fault status, allocation/pool errors, heap/pool use,
stack margin and sessions. Retain raw artifacts and documented mapping;
self-reported booleans or hashes alone cannot replace independent review.

Coverage must separately record each carrier's loaded/armed/running states,
wire identity, principal isolation and artifact hash. Each of six pressure
cases needs its own result and artifact hash. Record actual job count/duration,
quiet interval/network requests, final job/owner/empty state and provisioning
closure. Audit with:

```sh
python3 scripts/phase12_composition_audit.py --plan PRIVATE_PLAN.json \
  --evidence PRIVATE_NORMALIZED_EVIDENCE.json --artifact-root PRIVATE_ARTIFACT_DIRECTORY
```

A pass returns `RESOURCE_EVIDENCE_REVIEW_REQUIRED` with independent carrier/pressure
coverage review still pending. It grants no hardware,
RF, phone, timing or reliability acceptance. The twelve-hour absolute session
deadline needs a separately identified accelerated inhibited fixture (actual
reported limits 15-second inactivity/60-second absolute) plus ordinary-image
short-run behavior. That fixture must never be substituted for the ordinary
fifteen-minute/twelve-hour production candidate. A two-hour soak cannot measure
the twelve-hour deadline. Stop and restore under the exact packet after any
failure; never silently retry or extend the duration/job budget.


Adversarial repairs require actual private artifact files for every normalized
sample, carrier, pressure case and quiet observation. Hashes are checked against
file bytes; paths cannot escape the declared root. Sample resource metrics are
rederived from retained INFO, not trusted normalized booleans. The ordinary
collector rejects accelerated session limits. The quiet artifact records
continuous independent observation start/end timestamps, empty network/BLE
request lists and a bounded interval of at least 960 seconds inside the soak.
The auditor verifies completeness and binding; a reviewer still establishes
whether the independent quiet/wire artifacts are credible and exhaustive.

The INFO-only approval artifact uses schema `phase12-observer-approval/1`,
`approved=true`, `operation=composition-info-only`, canonical `plan_sha256`,
exact `source_commit`, `image_sha256`, `console` and timezone-aware
`expires_utc` covering the full declared 7200-second capture plus 45-second
deadline allowance. A prepared template has `approved=false`; creating or editing a
file does not constitute human authorization. CLI validates binding before
USB access and holds a nonblocking campaign lock next to the resolved plan
for the entire capture. Operator pressure clients hold only their short USB
lock, never the collector campaign lock. Concurrent collectors on the same
plan are refused before USB access.

The raw artifact for each normalized sample is its exported INFO capture
record (kind INFO, transport_raw true, exact raw_info_hex/raw_info_sha256,
info, elapsed_start_s/elapsed_end_s). The auditor requires the sample elapsed
value equal its raw start timestamp, checks the exact serial hash and decoded
object, then derives the resource metrics. Final authority, setup pending
flags, BLE and TCP buffers are checked against the actual final raw record.
Carrier and pressure artifacts remain independent-review pending even when
present and hash-bound; the result is RESOURCE_EVIDENCE_REVIEW_REQUIRED.


## Offline templates and normalization

Start from the [consumer plan template](phase12-composition-consumer-plan-template.json)
or [engineering plan template](phase12-composition-engineering-plan-template.json).
Their explicit replacement markers intentionally fail validation. Populate them
from the approved exact candidate manifest and fresh authorized readback; never
replace boot identity with an old historical value.

The normalizer is included in the auditor; no manual resource booleans or metric
editing is needed:

```sh
python3 scripts/phase12_composition_audit.py --plan PRIVATE_PLAN.json \
  --capture PRIVATE_CAPTURE.jsonl --metadata PRIVATE_INDEPENDENT_METADATA.json \
  --artifact-root PRIVATE_ARTIFACT_DIRECTORY --write-evidence PRIVATE_NEW_EVIDENCE.json
```

Metadata contains exactly `coverage`, `pressure`, `quiet_artifact`,
`simulated_jobs`, `longest_job_s`, `rf_jobs` and `flash_cycles`. Coverage and
pressure entries follow the audit schema above and name independently retained
artifact_path/artifact_sha256 files inside the existing private root. The quiet
artifact includes bounded start_s/end_s, network_requests, ble_requests and
continuous_observation. These observations must be supplied by independent
observers; the normalizer never invents successful jobs, carrier proof or quiet
periods. Missing, failed or partial capture is refused. It exports all 241
exact INFO records into a new `composition-info` directory, derives metrics
and final authority from actual INFO, audits those files and writes a new
private evidence file. Failed normalization retains diagnostic artifacts and
must not be silently rerun over them; the reviewer records failure disposition.
