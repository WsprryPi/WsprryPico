# Code review orientation

Reviewed on November 5, 2026, before preparing the campaign. This is source review
and planning evidence, not execution qualification. Refresh it against current
candidate sources when phase 01 runs.

## Source identity

The clean WsprryPico devel checkout and server tip were
`c9fd28ef57265c942900bdfe0595f90a31926ff9`. The read-only Pi companion tip was
`1e15b2485ac6e1b9cbb6ff435afc0f0232528804`. Existing unrelated worktrees were left
untouched. The campaign worktree branches from the Pico tip above.

## Current capabilities to preserve

The product remains a standalone Pico 2 W / RP2350 application and a WsprryPi
backend. Complete WSPR, QRSS, FSKCW, DFCW, and finite tone jobs execute locally.
USB roles, network transports, browser control, settings journals, credential
authority, inhibition, and independently versioned protocols retain their current
contracts. Host fixtures do not qualify physical timing, installation, or RF.

The software workflow has a verification job and explicitly manual publication.
It verifies required CTest registration/results and internal Python skips, uses
pinned inputs, runs source and shipped browser paths, builds normal/inhibited/
compatibility images, and compares two independently fresh normal UF2 builds.
Bundle/download verification independently binds sources, inputs, reports, and
linked images. These obligations are protected, not presumed redundant.

## Recent changes

- `61fff51c` and `3a7515b0` improved bounded Chrome startup and its failure tests.
- `1c307091` waits for observed fault state before advancing injected startup
  deadlines and retains a real watchdog and deliberate 21-second cold stimulus.
- `37eb063a` added browser_deadline.mjs and fixture_process.mjs, adopted them in
  selected browser fixtures, and expanded owned-process/cleanup regressions.
- `c9fd28ef` bounds observation in the EOF regression.

These improvements must survive the campaign. Shared tools should be reused or
extended where appropriate, with all callers inspected before interface changes.

## Remaining review leads

| Lead | Current owning sources | Campaign owner |
| --- | --- | --- |
| Verify complete denominator, contexts, and historical evidence | scripts/ci/run.py, bundle.py, CMake owners | 01 |
| Recheck remote merge enforcement; strengthen suite result evidence | workflow, runner, bundle verifier | 02 |
| Late fixture failure, initialization ownership, partial reads, final exit and cleanup handling need focused reproduction | fixture_process.mjs, ui_review_fixture.mjs, endpoint_tests.py, network Python fixtures | 03 |
| Session browser still has Date.now polling, separate CDP timers, and unbounded opening stages | session_timeout_browser.mjs | 04 |
| Nine browser entry files retain separate lifecycle implementations | native browser runners and shared helpers | 05 |
| Fixed TLS control sleeps and accelerated host time remain; hostname cancellation waits 2.2 seconds | network_tls_tests.py, network clock adapter, hostname runner | 06 |
| Tool-download tests are documented but absent from ordinary registration; companion pin is older than devel | usb_tool_download_tests.py, inputs.json | 07 |
| Two companion-client libraries compile the same five sources; separate firmware configurations may repeat equivalent work | host/network interop CMake, firmware recipe | 08 |
| Sequential CTest/build/browser scheduling has isolation constraints | run.py, CMake serial properties, fixed fixture ports | 09 |
| Historical pair/producer fixtures have no maintained local callers found | ntp_timeout_pair.mjs, legacy_pi_config_request.js and provenance fixtures | 10 |
| Final assurance needs intended-pair and adversarial evidence | complete campaign result | 11 |

The UI fixture server currently creates ten definitions on every invocation.
The earlier audit identified seven invocations consuming eight profiles in total;
70-to-8 is a source-derived candidate count to reverify, not a measured whole-CI
speedup. Selection must retain original profile/port identity and opt-in contexts.

Earlier audit observations of unprotected devel and successful CI runs are
historical. Phase 02 must re-read settings. Runs 42033174494 (Pico) and 42033231271
(Pi) do not qualify future edits. No behavioral tests or firmware builds were run
to prepare these prompts; suspected code paths remain hypotheses until reproduced.
