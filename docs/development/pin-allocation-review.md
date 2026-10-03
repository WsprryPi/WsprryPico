# Pin allocation review and validation

## Scope and orientation

Branch `codex/pin-allocation` starts at
`1dab547e17cd01e0562bab5b6b2ee4d652fd7b3a`. Work is isolated from the
shared checkout containing concurrent Phase 12 acceptance changes. The initial
review covered README, CONTRACT, architecture, development commands, current
configuration/journal validation, browser authentication and revision checks,
JobService ownership, the RF worker, button sampler and indicator controller.
The execution prompt records the resulting implementation scope.

Direct RF, switch input and indicator assignments now have supported adapters.
The candidate contract includes amplifier, LPF and all twelve I2C pairs, but
operational saves reject those unavailable adapters. Si5351 remains unavailable
as explicitly requested. No physical pin or RF qualification is claimed.

## Adversarial assessment and repairs

The assessment exercised malformed plans, every external GPIO, reserved pins,
all twelve I2C pairs, cross-role conflicts, duplicate LPF allocations, unsupported
adapters, journal reload, authenticated candidate validation, stale revisions,
nonmutating rejection and saved versus active configuration.

Review findings were closed as follows:

- Unhealthy storage must not allow default RF output: boot storage health now
  inhibits the worker, and stored plans undergo operational validation.
- Pending pin changes must also prevent WTP admissions: the scheduler latches
  JobService output inhibition until reboot. Subsequent configuration edits or
  restoring the original plan cannot clear that latch.
- The existing LED controller must remain the sole output authority: TX-active
  takes priority over provisioning cues; disabled indicators suppress output
  and reject Identify; external outputs initialize inactive before direction.
- Browser choices must not introduce conflicts when roles change: ownership
  lockouts update together, external LED selection picks an available pin,
  and disabled optional roles release their GPIO.
- Conflict errors must identify the contested role and owner: configuration
  errors now return structured allocation details and the browser renders them.
- Default configuration compatibility must be retained: default assignments
  preserve legacy canonical serialization; nondefault assignments persist the
  complete pin plan and are explicitly documented as a downgrade boundary.

A second assessment of the repaired paths found no remaining actionable findings
within this implemented scope. Physical GPIO timing and RF behavior remain
unqualified; host tests and cross-linking do not establish hardware acceptance.

## Validation disposition

Host C++ validation ran on the explicitly authorized Linux host `wspr5`, using
source-only snapshots. No native macOS C++ compiler retries were used after the
validation boundary was corrected. No device was flashed or controlled.

- Linux build and selected CTest suite: **96/96 passed**. Command:
  `ctest --test-dir /tmp/wsprrypico-pin-feature/build --output-on-failure -E
  "phase11_5_package[678]_tests|phase11_7_closure_tests|bluefy_release_tests|recovery_web_tests|load_reply_tests"`.
- The four excluded Git-history suites passed locally against the feature
  repository: package 6 (4 tests), package 7 (7), package 8 (8), closure (4).
- Bluefy release checks and recovery-web checks passed locally using existing
  pinned dependencies. Browser allocation behavior tests and JavaScript syntax
  checks passed. No dependencies were installed.
- `load_reply_tests` has the same three failures on this branch and the unchanged
  baseline: maximum status with loaded job/terminal retention, reserve refusal
  preserving an inactive loaded job, and uncalibrated TLS sensitivity preserving
  refusal. Both runs pass the other four tests. These pre-existing failures are
  recorded rather than claimed resolved by this feature.
- Existing Arm cross-toolchain and pinned SDK cross-linked both `WsprryPico` and
  `WsprryPico-StandaloneRF`. Existing prebuilt pioasm avoided native SDK helper
  compilation. Heap, pool, stack and renderer build gates passed.
- Desktop and phone browser previews verified the added controls and lockouts
  against a local mock API. This is interface evidence, not device evidence.
- Formatting and `git diff --check` passed.

The complete 103-test Linux snapshot suite is not claimed green: six tests need
repository/dependency context absent from the source-only snapshot, and the
seventh is the baseline-failing load-reply suite. Separate checks cover the six
prerequisite-dependent suites. Phase 12 acceptance remains the other chat's work.
