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
