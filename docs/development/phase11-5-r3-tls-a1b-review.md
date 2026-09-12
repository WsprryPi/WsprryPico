# R3 A1b corrected packet review — September 12, 2026

The [fresh A1b execution packet](phase11-5-r3-tls-a1b-execution.md) freezes the
repaired pressure driver and audit, two new finite-job identities, and a separate
proposed CONFIG **36→38** allowance. Its [prepared record](phase11-5-r3-tls-a1b-prepared.json)
lists every staged hash. **No A1b remote staging or hardware operation has run.**
The user's prior explicit unchanged-wiring confirmation is retained.

Phase 11.5 remains **OPEN, 2/6 families closed**: R1 5/5, R2 7/7, no accepted
R3 physical assertions and no full accepted configuration. Actual cumulative
counts remain CONFIG 36 and probes six. The
[failed A1 packet and restoration evidence](phase11-5-r3-tls-failure-review.md)
remain unchanged and cannot be replayed.

## Changes and execution assumptions

The earlier repair binds Console INFO's scheduler state and top-level launch
epoch to WTP STATUS's job/owner authority. Tests use recorded Empty, Running and
Complete responses. The actual pressure loop is exercised through idle, first
Running job, the still-finishing prior job, and the second Running job, with
all ten cases and distinct launch epochs. The
[response field map](phase11-5-metrics.md) documents these separate structures.

This continuation adds only the named `R3-A1b-config-36-to-38-v1` management
scope. The original R3 scope remains 34→36, and ordinary 2e43110 management
remains capped at 34. The new scope accepts exactly the preserved failed packet,
its device/management state hashes and restored A/B boots. Before host setup,
the supervisor re-runs the raw failure/restoration audit. A changed failure,
unresolved output or different restoration cannot enter fixture setup.

The device lifecycle now selects its inherited CONFIG limit from the validated
scope. Setup consumes one write; the second is reserved for original CONFIG
restoration. Probe count remains six and Wi-Fi fault-cycle counts remain zero.
Final counts derive from the exact validated allowance. Neither old scope is
expanded, and an unknown extension, pending write or blocked state is rejected.
The supervisor also records the pressure/observation stage explicitly.

The proposed work is unchanged: two USB-owned 100-second Tones at 135,500 Hz,
200 seconds total RF allowance, twelve pressure TCP connections, six HTTPS
controls/recoveries, 300 seconds of the pinned RF-off production controller and
360 seconds of independent USB observation. Firmware source, images, selected
138 MHz/divider 1/RAM/listener configuration, fixture/restoration ceilings and
resource thresholds are unchanged. No retry is included.

The HTTP response parser was checked against `src/network/api.cpp`,
`src/wtp/codec.cpp` and `src/network/pico/server.cpp`: `/api/v1/status` places
WTP service status in `job`, scheduler status in `standalone`, and connection
counts in `transport`. These are source checks, not a new live HTTP result.
The missing-certificate alert, silent timeout, slot rejection and duplicate-WTP
mechanisms still require physical execution and raw audit.

## Validation and review

Preparation began on clean devel checkouts: Pico
`2faab1b335c30144d11227cc3604c9c3e27b08f8`, Pi
`41f708f6fd9a74a5010c7f037e5f40bd1d47261f`. These identify the starting checkouts,
not the firmware or final publication commits.

- `PHASE115_R3_FAILURE_EVIDENCE=build/phase11-5-r3-tls-a1/evidence python3 -m unittest discover -s tests -p '*phase11_5*tests.py'`:
  **174 discovered, 172 passed, two unrelated private-fixture tests skipped**.
  Sixteen R3 tooling tests include recorded response binding, actual pressure-loop
  transitions, exact scope/counter boundaries and prior-failure admission.
- The retained failed attempt passes its separate raw failure classification;
  eleven mutated evidence sets are rejected. The normal acceptance auditor still
  rejects that failed observation. No failure is converted into acceptance.
- New scope tests reject old/unknown allowances, exhausted restoration, repeated
  setup, altered source counters, pending/blocked state, changed prior hashes or
  boots, and a failed prior raw audit. They verify that original restoration
  remains available at CONFIG 37.
- Read-only SSH verified the old packet and restored-state hashes, all nine
  existing private input hashes, unchanged host boot and the presence of PID
  1957. The new root/archive/stager paths are absent. This is not a fresh USB
  inventory; serial-specific A/B and installed-process admission still occurs
  inside the approved fixture lifecycle.
- The fresh archive contains 61 files plus nine hash-bound remote copies.
  Archive membership, every staged helper/image hash, exact fixture helper sets,
  RF-off INI validation, frozen jobs and new identities were checked locally.
  Private keys remain on wspr5. The consumed archive was not regenerated.
- Pi production helper tests passed **12/12**. No firmware or Pi runtime source
  changed; C++ builds and unrelated physical cases were not repeated. JSON,
  documentation links and whitespace checks passed.

Review traced the new scope through supervisor admission, lifecycle inheritance,
management authorization and final restoration. It checked every consumed-packet
reference against the preserved artifacts, and kept RF authority in the sole USB
actor. No remaining actionable finding was identified within this changed slice.
The corrected live run remains unqualified; source and replay checks cannot
establish target TLS pressure, resource retention or RF acceptance.

## Remaining work and approval

A1b must be explicitly approved, staged once, executed once, restored and audited.
Even a passing A1b cannot close R3. Other failed TLS lifetimes, pending expiry,
partial/stalled HTTP, maximum allocation, protocol/browser/USB boundaries,
replay/session/terminal capacities, expiry/reuse and three equivalent reclamation
cycles of the measured highest-resource path remain open. R4–R6 remain unrun.
The global 110.592-second job cap and longer QRSS envelope remain unresolved.

The attached handoff requires carrying the cumulative count forward and obtaining
a concrete new allowance; the consumed packet explicitly prohibited a retry.
Only the fresh staging/fixture/RF window and CONFIG 36→38 await approval.
The existing implementation/publication authorization and unchanged-wiring
confirmation are retained.

## Documentation Impact

Added this review, the A1b execution packet and its machine-readable prepared
record. Updated the current Pico ledger/index and Pi companion report. Historical
A1 execution/preparation/failure files remain unchanged. Considered unchanged:
firmware and Pi implementation, WTP/browser contracts, the response field map,
operator UI, and separate operator manuals. The user excluded `Wsprry_Pi_Docs`.
