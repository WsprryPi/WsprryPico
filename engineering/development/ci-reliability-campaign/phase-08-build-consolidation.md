# Phase 08 Consolidate demonstrably redundant build work

Execute only phase 08 when explicitly invoked. Read the complete
[shared execution contract](README.md#shared-execution-contract),
[orientation](orientation.md), and accepted baseline, reliability, coverage, and
source-pair evidence through phase 07. Reverify current build interfaces and pins.

## Objective and scope

Remove equivalent compilation/orchestration while preserving every distinct build
and validation obligation. Inspect cmake/host_client_interop.cmake,
network_client_interop.cmake, network_host_tests.cmake, CMakeLists.txt,
firmware/CMakeLists.txt, scripts/ci/run.py, setup.py, bundle.py, dependency checks,
image checkers, and source-selection regressions. Phase 09 owns parallel scheduling;
this phase establishes safe work reuse first.

## Work

1. Freeze the actual graph: configuration contexts, sources, include paths,
   definitions, flags, generated inputs, dependencies, compiler/tool identities,
   output identities, and validation owners. Separate compile_commands entries
   for declared targets from compilation/link invocations that actually occurred.
2. Compare the selected host-client libraries. Reuse one target only if source
   selection, language/ABI, flags, includes, definitions, and linked consumers
   remain correct. Retain edited-selected-source execution, missing-source
   refusal, and genuine compiler-error propagation. Do not substitute prebuilt
   objects from a different selected peer or suppress warnings to unify targets.
3. Investigate consumer/inhibited shared configuration work. The earlier 175
   overlapping object paths are a ceiling, not equivalence proof. Share only
   proven identical inputs; retain per-image engine macros, metadata, generated
   files, resource reservations, overlays, linker wiring, target-specific output,
   and every required linked-image check. Preserve compatibility target behavior.
4. Keep two independently fresh normal reproducibility builds. Neither build may
   reuse the other's compiled objects, generated image, or trusted pass report.
   Fresh output directories alone are insufficient if a hidden compiler/object
   cache restores the same prior work into both builds.
5. Consider dependency-source caching only if existing measurements justify it.
   Cache immutable verified source/archive inputs, never replace source/hash/
   submodule checks with a cache hit. Bind keys to actual inputs, verify restored
   bytes and ownership, reject partial/corrupt/wrong-input entries, and preserve
   an independently cold validation route. Do not add downloads/installations
   without separate authority or broaden this into a dependency migration.
6. Preserve validation at independent trust boundaries. Reusing one parsed report
   inside an unchanged-image operation may be considered with evidence; creation,
   post-download inspection, and publication must not trust a prior pass flag in
   place of required independent verification. No validator is removed merely
   because its name resembles another checker.

## Validation and adversarial assessment

Exercise clean and incremental builds. Deliberately change a selected client
source/header, compiler input, generated contract/asset, and image-specific
definition; prove correct consumers rebuild and wrong/stale inputs fail. Preserve
existing genuine compiler-failure tests. Verify both normal/inhibited engine
identities, inhibition, current flash/UF2/ELF boundaries, overlays, heap/stack/
pool/renderer guards, and compatibility target. Prove the fresh reproducibility
builds still compare equal and a deliberately changed output is rejected.
Run incremental invalidation checks without clearing their build directories;
an unconditional clean rebuild cannot prove the dependency graph is correct.

Run affected host/build/bundle regressions and both actual production network and
USB suites for the intended pair. Review shared mutable directories, stale cache
reuse, differing flags, bypassed post-link checks, and lost expected values;
fix findings, rerun affected checks, and reassess.

## Acceptance and handoff

Report actual compilation/link/configuration counts, cold/warm times where
comparable, retained build/validation contexts, and full replacement costs.
Distinguish measured savings, ceilings, and estimates. If a proposed reuse is
unsafe or yields no justified benefit, retain that work with the supported
decision rather than forcing a quota. Phase 09 receives the accepted build graph
and resource constraints. Update phase status after required gates pass and stop.
