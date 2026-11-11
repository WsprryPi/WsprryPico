# Prepare firmware now and publish it later

Use the canonical `software-build.yml` manual workflow with `publish=false` to build and verify without publication. Retain its exact source, run ID, attempt and firmware version. The verification job must pass; the optional publication job may be skipped. No tag is needed for a devel CI version. A semantic release build instead requires its exact existing version tag; pushing that tag triggers verification, so tag creation must be selected deliberately rather than treated as a harmless local preparation step.

Prepare a private packet outside Git using commands from `python scripts/ci/prepared.py --help`:

```text
python scripts/ci/prepared.py prepare --branch devel --run RUN_ID --attempt ATTEMPT --source FULL_COMMIT --version 0.1.0-ci.RUN_ID.ATTEMPT --destination /absolute/private/pico-prepared
```

The directory retains the original immutable deployment/audit archives, full extraction and validation receipts, nine exact public files and `prepared-publication.json`. Keep the entire directory and a copy of the selected tooling. Preparation makes no public release, tag, asset or bookmark. It trusts the successful canonical verification and independently checks archive/payload hashes and manifest provenance; it does not rerun the complete firmware build. Use the hash-pinned CI Python requirements in a dedicated environment.

Exit. In a later process, revalidate into a new directory:

```text
python scripts/ci/prepared.py verify /absolute/private/pico-prepared/prepared-publication.json --destination /absolute/private/pico-later-verification
```

Changed selections, packet hashes, missing/expired canonical archives or incompatible provenance refuse; return to preparation rather than rebuilding during publication. Local files do not override missing canonical proof. Publication uses the trusted manual `publish-prepared.yml` on devel with exact prepared JSON, confirmed `packet_sha256`, expected publisher source and explicit `publish=true`. Its default `publish=false` runs a separate read-only validation job. Neither route compiles firmware. The harness [retained release operator guide](https://github.com/WsprryPi/WsprryPi-Qualification-Harness/blob/devel/docs/development/prepared-releases.md) provides the durable `release-status`, later `release-publish`, exact dispatch tracking and partial-system continuation commands for Pico alone or fixed Pi/RP1 combinations.

The later trusted job re-downloads the original canonical archives and reconstructs exactly the nine tested files. It creates a missing immutable CI version tag, verifies existing tags, adds only missing draft assets and publishes only after complete checks. It never moves an existing tag or replaces an asset. The source-ordered branch bookmark release metadata may advance under the existing ancestry policy; its tag remains unchanged. Latest stable is not selected automatically.

The original build run and later publisher run have distinct identities. A release-body receipt binds the nine-file packet digest to the trusted publisher run/source/attempt, leaving all tested artifact bytes unchanged. The shared installer independently validates the later canonical workflow and successful publish job when the original publisher was skipped. Retry attempts append receipt history without replacing assets. A failed or incomplete publisher cannot satisfy public acceptance; archive or publisher metadata unavailability remains an explicit gate. Normal same-run releases retain their existing proof behavior. This changes publication provenance only, not WTP or firmware wire/storage contracts.

Publication requires current authority. This implementation's deterministic tests exercise publication transports without creating a product release. Public consumer resolution does not open USB, install firmware or qualify RF. Physical acceptance is a separately authorized operation against an identified device. No board is needed for preparing or validating a packet.

Deferred publication uses the same target branch/tag concurrency group as the ordinary canonical publisher, so simultaneous publication paths cannot race the source-ordered bookmark. Read-only validation uses its own queue and cannot block a publication behind validation work.

## RC.2 published artifact provenance

The [RC.2 prerelease](https://github.com/WsprryPi/WsprryPico/releases/tag/v1.0.0-rc.2) contains the nine verified files from canonical [build 42622652101, attempt 1](https://github.com/WsprryPi/WsprryPico/actions/runs/42622652101). Its firmware source is `971f7bf9f8075d64ff086f777356bdd06c3d8b53`, and its annotated tag object is `e34c6fb9758a1edaa664806dc194855ae92c75d5`. The 6,305,280-byte UF2 has SHA-256 `5e6c44049568c4a08e15b384c22af3b44661eb2fe120076c0befc44488bd3dd9`. The retained owner packet digest is `36df8dc23076b56e6f42ad1c1a52e43c9e383f132f086685786b66d3adeef030`.

Trusted [publisher 42625590815](https://github.com/WsprryPi/WsprryPico/actions/runs/42625590815) used tooling source `2b1b6840af8fa83ed50a19a1264a860f7a58251b` and published the retained files without rebuilding firmware or replacing prior assets. Firmware source, publisher source, and later documentation source are distinct identities. Original archives and superseded candidates remain retained. Publishing the semantic prerelease did not advance the separate `ci-devel` selector or select latest stable.

Software verification passed all 234 registered Pico tests and the browser, crypto, installer, packaging, and reproducibility gates. Production [network and USB integration](https://github.com/WsprryPi/WsprryPi/actions/runs/42619087942) passed with Pi `961411da6659027d83752a41aca34e88aac269bc` and the final Pico source. [Harness CI](https://github.com/WsprryPi/WsprryPi-Qualification-Harness/actions/runs/42620186611) passed at `4225efe18e2f65798306445c8767b8240882eb05`: 1,971 Linux tests, 766 portable macOS tests, and 755 portable Windows tests, with 11 declared unsupported production-USB cases excluded on Windows. The frozen-calibration provenance corrections are delivered through [Pico PR 27](https://github.com/WsprryPi/WsprryPico/pull/27) and [Harness PR 28](https://github.com/WsprryPi/WsprryPi-Qualification-Harness/pull/28).

Physical installation and RF qualification of this published image were not performed. See the [qualification guide](pico-rf-qualification.md#evidence-and-claims) for evidence boundaries and the [bounded GPS/PPS investigation](gps-pps-validation.md#bounded-investigation-closure-2026-11-08) for the closed, inconclusive automatic-correction result. Publication does not establish physical acceptance or reopen that investigation.
