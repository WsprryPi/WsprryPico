# RC.2 release checklist

Status: ✅ complete; ⏳ in progress; ▧ not started.

1. ⏳ **Add Pico RF qualification support to the Qualification Harness.** Implement the production Pico adapter and four configurations: direct GPIO and Si5351, each with and without GPS/PPS. Cover finite tones, WSPR, QRSS, FSKCW, and DFCW, bounded capture, failure handling, verified RF shutdown, and settings restoration. Complete deterministic and production-path software validation. [Phase 1 execution prompt](pico-rf-harness-phase-1-prompt.md).
2. ▧ **Prepare and qualify the exact RC.2 firmware artifact.** Retain the exact versioned firmware bundle and provenance, run Pico installation/preservation acceptance, and execute the four-configuration RF campaign against those exact bytes. Retain source, board, engine, clock, GPS/PPS, correction, receiver-path, analysis, and restoration evidence. [Phase 2 execution prompt](pico-rc2-qualification-phase-2-prompt.md).
3. ▧ **Review results and publish RC.2.** Resolve actionable findings, finalize release notes and documented limits, validate the retained publication packet, and publish the tested artifact through the owning release workflow. Verify public download and installer resolution against the published bytes. [Phase 3 execution prompt](pico-rc2-publication-phase-3-prompt.md).

Phase 1 is in progress. Phases 2 and 3 remain separate tasks.

## Final disposition of former item 21

The Si5351 automatic carrier-correction investigation is **closed as inconclusive and resolution-limited**. This is the final disposition, not an unfinished qualification requirement. The capability remains available for experimentation. A crystal reference may respond differently from the tested TCXO, but improvement has not been established for that configuration. The release work does not reopen the investigation or require automatic correction to outperform manual correction.

Retain the [bounded investigation and measurement limits](gps-pps-validation.md#bounded-investigation-closure-2026-11-08) and the approved [operator guidance](../../docs/reference/time.md#gpspps-validation-scope).
