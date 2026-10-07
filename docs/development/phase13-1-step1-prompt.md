# LED closeout step 1 execution prompt

Work in `devel` in WsprryPico. Execute **step 1 only** of the fixed
[six-step closeout](phase13-1-closeout-steps.md). Both named Picos are connected
to the SDR and may be used for preparation tests. Operator participation belongs
to step 2; do not ask for wiring, camera setup, a timed button press or redundant
RF approval while executing this preparation slice.

## Objective

Complete the finite live runner, test cases, candidate verification and automatic
evidence collection so steps 3–6 can run after one untimed operator setup session.
Retain the implemented LED contract: external selected GPIO is TX-only;
AP/Identify remain onboard. With no external selection, onboard solid TX
overrides operational blinking. Disabled selection bypasses the TX launch gate.

Read project instructions, README, CONTRACT, architecture and development guide.
Inspect branch/working tree and preserve unrelated work. Other repositories may
be read for retained tool contracts, but not edited. Use retained pinned build
dependencies. Keep captures, full-flash backups, keys and generated firmware
under private ignored `build/` paths. Do not edit historical acceptance evidence.

## Deliverables

1. A maintained six-step record, including the operator's connected-device
   authorization, plus a small memory update for this explicitly requested
   sequence. Only step 2 normally needs an operator.
2. A deterministic, device-neutral case plan for onboard warmup/all modes,
   loaded/armed/inhibited non-TX behavior, active/armed abort, AP/Identify
   arbitration, external active-high/active-low, disabled output, standalone
   STOP, GP14 cutoff and bounded LED-write/launch failures. Specify which
   assertions require independent optical/RF evidence; do not infer physical
   LED success from software telemetry.
3. A runner with offline validation by default and an explicit live invocation.
   An explicit run flag is an execution safeguard, not another operator approval.
   Bind board/USB serial/device/boot, source/image hashes, engine/clock/pins,
   fixture roles and receiver identity before mutations. Support either Pico
   as DUT; select a second named Pico as the inhibited GPIO stimulus fixture
   when needed. Keep RF execution local and complete all jobs before ARM.
4. Durable accounting before ambiguous ARM/SCHEDULE sends, no automatic retries,
   finite aggregate and per-case limits, autonomous lease renewal/status polling,
   complete failure evidence, exclusive device ownership and fail-safe cleanup.
   Preserve backups/journals and implement verified inhibited restoration.
   An uncertain cleanup is a retained STOP, never a reported pass.
5. Managed finite SDR and camera capture with readiness checks before RF,
   process-exit/timeout handling, hashes and identity-bound metadata. No operator
   response token expires while waiting. Require independent observations for
   physical claims; leave timing unresolved when recording synchronization or
   resolution is insufficient. Step 2 supplies camera/ROI/wiring inputs.
6. Actual fixture adapters for the later stages, using narrowly guarded test
   firmware where ordinary consumer commands cannot exercise a case. Fixtures
   must default off, retain one JobService/indicator owner, never invert TX
   priority, never rely on per-symbol USB, and never deliberately leave RF
   active to simulate a failed stop. The GPIO stimulus must use finite
   open-drain holds and release automatically, including on reset.
7. Reproducible candidate builds/linked-image checks and a hashed local manifest.
   Check both ordinary inhibited restoration and diagnostic/RF fixtures. Bind
   candidates to an exact clean source commit and distinguish fixture coverage
   from production network/configuration qualification.

## Validation and iterative adversarial review

Add behavioral tests against the actual runner/adapters: malformed plans,
wrong identities/hashes/pins, active/owned preflight, stale boots, capture startup
or mid-run failure, lost/ambiguous ARM response, exhausted accounting, premature
terminal state, missing inactivity confirmation, abort/lease renewal, fixture
timeouts and restoration mismatch. Exercise successful stages and failure
cleanup without hardware; do not write tests that merely match source strings.

Run the relevant documented host checks, normative job validation, changed
Python/C++ syntax/formatting, sanitizers for changed portable C++ where applicable,
candidate cross-links and linked UF2/stack/storage checks. Use read-only physical
inventory or bounded preparation checks where useful; avoid performing the full
operator-dependent physical matrix before step 2. Clearly identify untested
live adapters and the fixture/recording inputs still needed at step 2.

Perform an adversarial review of ownership, counters/crash recovery, time bounds,
subprocess cleanup, credential handling, source/image binding, selected LED
arbitration, restoration, observer independence and unattended operation. Fix
every actionable finding, rerun affected checks and perform another assessment;
iterate until no source finding remains. Keep unrelated baseline failures
explicit rather than silently broadening this slice.

Update the step record, runner guide, physical packet and development links with
the actual disposition. Commit and push the reviewed slice without force;
independently verify remote parity. Rebuild/hash final candidates after the
commit if build identity changes. Report artifacts, validation, actual hardware
actions/restoration, remaining step-2 setup inputs and final repository state.
Do not claim that physical LED acceptance is complete.
