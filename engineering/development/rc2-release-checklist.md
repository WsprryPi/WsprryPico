# RC.2 release checklist

Status: ✅ complete; ⏳ in progress; ▧ not started.

1. ✅ **Add Pico RF qualification support to the Qualification Harness.** The production Pico USB route covers direct GPIO and Si5351, each with and without GPS/PPS, explicit correction subcases, TONE, WSPR, QRSS, FSKCW, and DFCW, bounded capture, failure handling, verified shutdown, and settings preservation. Required deterministic and production-path software validation passed. [Pico RF qualification guide](pico-rf-qualification.md). [Harness PR #19](https://github.com/WsprryPi/WsprryPi-Qualification-Harness/pull/19), [Pico PR #22](https://github.com/WsprryPi/WsprryPico/pull/22).
2. ▧ **Prepare and qualify the exact RC.2 firmware artifact.** Retain the exact versioned firmware bundle and provenance, run Pico installation/preservation acceptance, and execute the four-configuration RF campaign against those exact bytes. Retain source, board, engine, clock, GPS/PPS, correction, receiver-path, analysis, and restoration evidence. [Phase 2 execution prompt](pico-rc2-qualification-phase-2-prompt.md).
3. ▧ **Review results and publish RC.2.** Resolve actionable findings, finalize release notes and documented limits, validate the retained publication packet, and publish the tested artifact through the owning release workflow. Verify public download and installer resolution against the published bytes. [Phase 3 execution prompt](pico-rc2-publication-phase-3-prompt.md).

Phase 1 is complete on the `codex/pico-rf-harness` branches, with the two PRs unmerged. Its completed execution prompt is retired in favor of the maintained guide. Phases 2 and 3 are not started.

## Final disposition of former item 21

The Si5351 automatic carrier-correction investigation is **closed as inconclusive and resolution-limited**. This is the final disposition, not an unfinished qualification requirement. The capability remains available for experimentation. A crystal reference may respond differently from the tested TCXO, but improvement has not been established for that configuration. The release work does not reopen the investigation or require automatic correction to outperform manual correction.

Retain the [bounded investigation and measurement limits](gps-pps-validation.md#bounded-investigation-closure-2026-11-08) and the approved [operator guidance](../../docs/reference/time.md#gpspps-validation-scope).
