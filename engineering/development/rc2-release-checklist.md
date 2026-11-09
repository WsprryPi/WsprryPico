# RC.2 release checklist

Publication scope: software-verified prerelease. Physical qualification is incomplete and is not claimed.

1. ✅ **Pico support and corrections delivered.** The maintained Harness supports direct GP2 and the documented Si5351 profile, GPS/PPS correction subcases, TONE, WSPR, QRSS, FSKCW, and DFCW. The frozen-calibration provenance correction is delivered through [Pico PR #27](https://github.com/WsprryPi/WsprryPico/pull/27) and [Harness PR #28](https://github.com/WsprryPi/WsprryPi-Qualification-Harness/pull/28). See the [qualification guide](pico-rf-qualification.md).
2. **Incomplete — physical acceptance of the published image was not performed.** Installation/preservation and RF results from earlier candidates remain private evidence for those images. The published source has no new physical qualification campaign. The [Phase 2 execution prompt](pico-rc2-qualification-phase-2-prompt.md) remains retained for this unfinished work and is inactive without explicit invocation.
3. ✅ **RC.2 published.** The [public prerelease](https://github.com/WsprryPi/WsprryPico/releases/tag/v1.0.0-rc.2) contains the nine verified files from the canonical build. GitHub reports a non-draft prerelease with `immutable: false`; latest stable was not selected. See the [release notes](../../docs/reference/releases.md) and maintained [publication procedure](prepared-publication.md).

## Published artifact and software evidence

Firmware source is `971f7bf9f8075d64ff086f777356bdd06c3d8b53`; the annotated tag object is `e34c6fb9758a1edaa664806dc194855ae92c75d5`. Canonical [build 42622652101, attempt 1](https://github.com/WsprryPi/WsprryPico/actions/runs/42622652101) produced version `1.0.0-rc.2`. The UF2 is 6,305,280 bytes with SHA-256 `5e6c44049568c4a08e15b384c22af3b44661eb2fe120076c0befc44488bd3dd9`. The retained owner packet digest is `36df8dc23076b56e6f42ad1c1a52e43c9e383f132f086685786b66d3adeef030`.

The trusted [publisher 42625590815](https://github.com/WsprryPi/WsprryPico/actions/runs/42625590815) used tooling source `2b1b6840af8fa83ed50a19a1264a860f7a58251b` and published the retained files without rebuilding firmware. Firmware source, publisher source, and later documentation source are distinct identities. The original archives and superseded candidates remain retained; no previous release assets were replaced.

Pico verification passed all 234 registered tests, browser/crypto/installer/packaging gates, and identical fresh reproducibility. Actual production [network and USB integration](https://github.com/WsprryPi/WsprryPi/actions/runs/42619087942) passed using the final Pico source with Pi `961411da6659027d83752a41aca34e88aac269bc`. [Harness CI](https://github.com/WsprryPi/WsprryPi-Qualification-Harness/actions/runs/42620186611) passed at `4225efe18e2f65798306445c8767b8240882eb05`: Linux 1,971 tests, macOS 766 portable tests, and Windows 755 portable tests with the declared 11 unsupported production-USB cases excluded. Both repositories contain their corrections on `devel`.

The Harness failure came from requiring before/after GPS reads to contain the generation frozen during LOAD. A valid intervening generation can be absent from both reads. Pico now retains the complete job-bound input; the Harness validates its identity, policy, correction arithmetic, freshness, uncertainty, and LOAD bounds. The correction selection/programming behavior is unchanged. No additional physical tests or device flashing followed the final software correction. Publication does not establish RF, installation, timing, power, or emissions acceptance.

GitHub repository and organization release-immutability settings remain disabled and were not modified. Explicit semantic version selection resolves RC.2; publishing a semantic prerelease does not advance the separate `ci-devel` selector.

## Final disposition of former item 21

The Si5351 automatic carrier-correction investigation is **closed as inconclusive and resolution-limited**. This is the final disposition, not an unfinished qualification requirement. The capability remains available for experimentation. A crystal reference may respond differently from the tested TCXO, but improvement has not been established for that configuration. The release work does not reopen the investigation or require automatic correction to outperform manual correction.

Retain the [bounded investigation and measurement limits](gps-pps-validation.md#bounded-investigation-closure-2026-11-08) and the approved [operator guidance](../../docs/reference/time.md#gpspps-validation-scope).
