# Software/build CI and consumer firmware

The maintained workflow is `.github/workflows/software-build.yml`, named **Software and firmware**. It checks portable software and SDK-backed host adapters on Linux, then cross-builds one generic, uninhibited `WsprryPico` consumer image for Pico 2 W at the normal 138 MHz clock. There are no per-band deployment builds. `WsprryPico-Inhibited` and compatibility RF targets are regression builds; their UF2s are excluded from the deployment bundle.

Images contain no selected transmit frequency, station identity, device credentials or enabled schedule. Standalone WSPR frequency is explicitly saved at runtime. An absent frequency blocks ownership, watermark reservation, preparation and arming. A first frequency save leaves schedules disabled until explicitly enabled. A Type 2/3 pair freezes its chosen frequency for both frames. Generic upgrades preserve explicitly saved settings; no whole-flash erase is required. Downgrade preservation of the extended stored configuration is unqualified. Full-board boot, USB, RF and timing acceptance remain separate.

## Triggers and identity

Every push to `devel`, `main` or a semantic `v<version>` tag, including a merge or documentation-only change, runs checks and builds firmware. Pull requests targeting either branch build preview images when opened, updated or reopened. Merging a PR into `main` therefore builds the resulting `main` commit as well. There are no path filters or build cancellation groups. Publication is serialized separately per branch, with up to 100 waiting jobs retained using GitHub's `queue: max` setting. Both branches contain the canonical workflow. Branch downloads require an explicitly published bookmark; an absent bookmark refuses selection. Tagged firmware can be selected explicitly, including `--version 1.0.0-beta.1`.

Manual dispatch, where available, accepts only the enumerated `consumer` profile. Ordinary embedded versions are generated before building as `0.1.0-ci.<run-id>.<attempt>`. Different attempts have different identities. Explicitly published trusted branch builds preserve those exact bytes under unique `v<version>` prerelease tags. They remain CI testing images; `main` does not automatically become a stable product release. Publication does not mark a prerelease as GitHub's latest stable release.

**Verification does not publish.** Firmware publication jobs require a manual `workflow_dispatch` with `publish=true`; the default is false. Pushes, pull requests, tag pushes and ordinary manual checks leave existing releases, assets and main/devel bookmarks untouched. The firmware publisher entry points enforce the same authorization. Existing downloads remain available until an explicit publication advances their channel.

### Beta and final firmware tags

Firmware tags use `v` followed by [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html), for example `v1.0.0-beta.1` or `v1.0.0`. The version without `v` is embedded in the image and its filename. Valid build metadata is supported; the bounded version string is at most 128 ASCII characters. Numeric identifiers obey SemVer leading-zero rules. `ci` and `testing` prefixes retain their historical reserved identities. Major version does not select protocol or storage compatibility.

A release tag must peel to the checked-out source on maintained main/devel history. Its build uses the `release` artifact stream, manifest channel `prerelease` or `stable`, exact tag workflow ref and the same complete software, linked-image and reproducibility checks as CI. Beta/final assets retain the existing six-file deployment bundle, two original archives and `ci-publication.json` verification receipt. They do not advance CI bookmarks.

After a tag exists, check its exact source without publishing:

```sh
gh workflow run software-build.yml --repo WsprryPi/WsprryPico \
  --ref v1.0.0-beta.1 -f publish=false
```

Publication is a separate deliberate manual dispatch at that tag with `-f publish=true`. This runs the full checks again before publishing. Beta releases set GitHub `prerelease:true`; final releases set `prerelease:false`. `make_latest` defaults false. Only an explicitly published final tag can use `-f make_latest=true` to select GitHub's latest stable release. Existing tag targets and published bytes cannot be replaced. Original draft receipts must remain identical when resuming an interrupted upload; a rebuild/run/attempt cannot replace a draft's previously uploaded assets.

Main/devel CI publication uses a manual dispatch on that branch with `-f publish=true`. The [installer client](usb-installer.md#installer-source-distribution) uses verified immutable source and needs no separate release. A successful build alone does not authorize firmware publication.

An explicit manual `devel` dispatch may select `testing_version` with the strict form `0.1.0-testing.N` (positive N, at most six digits). That dispatch runs the same complete checks and fresh builds, but skips the automatic publication job. Publication requires independent review, a new annotated tag at the checked source, a complete verified draft and a public download audit. The version must be unused; an interrupted candidate never permits moving a tag or replacing published assets. Pushes, pull requests and main cannot select this override. Ordinary generated CI identities remain unchanged.

Testing candidates include the `testing_release` extension of manifest schema 1: nominal drive, protocol/API/storage compatibility, exact software-tested Pi revision, historical drive-acceptance pair, reproducible recipe and pinned references. They explicitly set `deployment_candidate:false` and installer default eligibility false. Existing installer CI receipt/version checks refuse this manual testing series. Normal main/devel CI images remain eligible through their independently verified branch bookmarks; publication of a testing version does not update either bookmark or create a stable release.

The actual checked-out full source SHA is recorded. PR head, synthetic merge commit and trusted branch commits are distinct identities. PR artifacts are test outputs and cannot be selected as the trusted consumer deployment candidate.


## Inputs and checks

[`scripts/ci/inputs.json`](../../scripts/ci/inputs.json) pins SDK, all linked SDK submodules, picotool, the read-only qualification Harness, the Arm Linux archive and actual Wi-Fi/Bluetooth resources. SDK 2.3.1 and Arm compiler 15.3.1 remain unchanged. The official Arm archive's SHA-256 is checked before extraction; dependency Git identities and clean submodules are checked before use. No dependency cache substitutes for verification. SDK/firmware/host build directories are separate and fresh.

[`scripts/ci/requirements.txt`](../../scripts/ci/requirements.txt) contains exact host-tool/test versions and official PyPI artifact hashes. Python/Node versions are pinned; npm uses the checked-in lockfile. Runner image/version, host compiler, OpenSSL, Chrome, CMake/Ninja, Python/Node and installed package versions are recorded. Host/compiler/system libraries supplied by the named runner image are inventoried rather than claimed to be a byte-reproducible container.

[`scripts/ci/run.py`](../../scripts/ci/run.py) is the executable recipe. It supplies TinyUSB, BTstack, lwIP, CYW43, Mbed TLS and the exact reviewed companion source to optional SDK-backed host tests, supplies the pinned Harness source for offline analysis, installs npm dependencies before CTest, and checks that the expected source test inventory was registered. Missing Node/Python modules or the compiled endpoint fixture fail CI. All registered CTest cases must execute successfully. WTP contract validation, npm browser tests, real consumer frequency UI checks and packaging failure tests are additional required gates.

Current CI rejects skipped CTest cases and internally skipped Python assertions. The verifier retains the exact [`legacy test skip reasons`](../../scripts/ci/legacy-test-skip-reasons.json) only to verify already-published images whose frozen source registered private historical evidence tests. Current builds record an empty legacy skip inventory. Hardware acceptance remains separate from these software checks.

Firmware builds retain linked engine, heap, stack/guard, pool, renderer, GP14/BOOTSEL, flash and UF2 checks. The deployment verifier checks the current contract-2 application flash boundary `0x103ec000`, the exact pinned RP2350-E10 workaround, UF2 numbering/family/payload correspondence with the linked ARM ELF, generated and embedded identities, actual target/clock/consumer flags and generic inputs. Two fresh normal builds must produce identical UF2s for the same declared source/version/inputs. This check does not promise reproducibility across every runner image or toolchain revision.

The update boundary is checked against the linker reservation in the exact frozen source revision. New bundles reserve the final 72 KiB, including the separate NTP-learning journal. Verification also accepts historical `0x103f0000` bundles when their source revision requires that layout. Their integrity does not qualify downgrades to preserve the new cache.

Local checks remain documented in [the development commands](README.md#deterministic-validation). Use a fresh build directory after removal of build-time frequency selection; stale caches containing that removed option refuse explicitly. The normal firmware recipe is documented in [firmware foundation](firmware-foundation.md). CI's Linux dependency setup is explicit; it never installs a toolchain on macOS.

## Canonical bundle and retention

Schema version 1 is [`release-manifest-1.schema.json`](../../scripts/ci/release-manifest-1.schema.json). The canonical `release-manifest.json` describes the deployment payload for CI and preserved testing-prerelease bundles. It is independent of WTP and API versions. The inhibited candidate-fixture manifest is a different contract.

The deployment allowlist is exactly:

- `WsprryPico-<version>-pico2_w.uf2`
- `release-manifest.json`
- `SHA256SUMS`
- `LICENSE.md`, `THIRD_PARTY_NOTICES.md`, `DEPENDENCY-LICENSES.txt`

The manifest lists payload and required notice hashes, plus the separately downloadable audit inventory. It does not hash itself. `SHA256SUMS` covers the UF2, manifest and notices, and excludes itself. Checksums establish byte integrity; they are not signatures or independent physical qualification. The audit includes linked ELF/map, generated identity, compile commands, configuration, picotool identity, generated overlays, logs and actual test reports. It contains no device keys or private capture packets.

The artifact pair is named `WsprryPico-firmware-<branch>-<run>-<attempt>-consumer` and `WsprryPico-audit-<branch>-<run>-<attempt>-consumer`, retained for 90 days. PR previews use `pull-request` in place of the branch. The downloader also recognizes the original branchless devel artifact names. Failed builds may retain separately named diagnostic logs for 14 days.

Successful trusted builds also preserve all six deployment files, the original `deployment.zip` and `audit.zip`, and a `ci-publication.json` receipt as public GitHub prerelease assets. These downloads have no Actions retention deadline. No timer rebuild is needed. The receipt binds original artifact IDs/archive hashes, successful verification job, branch/source/run/attempt and manifest hash; it does not rewrite the archived manifest after upload.

The permanent download pages are [devel](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-devel) and [main](https://github.com/WsprryPi/WsprryPico/releases/tag/ci-main). Each page links to that branch's latest successfully verified and published version. The first successful publication creates the corresponding page. Failed builds leave its previous version available. An absent branch bookmark causes refusal; explicit beta/final selectors use their own verified release.

[`scripts/ci/publish.py`](../../scripts/ci/publish.py) downloads the exact artifact pair after the read-only verification job passes, checks provenance/checksums and UF2/ELF payload association again, and uploads a draft version release. It publishes only after all nine remote assets have matching sizes and SHA-256 digests. Interrupted drafts resume without overwriting assets. Existing version tags and published assets cannot be replaced by this helper. This is an enforced append-only publishing policy, not a claim that repository-wide GitHub release immutability has been enabled.

After successful tag creation, missing tag readbacks receive up to five retries with 1, 2, 4, 8 and 16 second delays. Exhaustion reports a visibility timeout; a visible tag pointing to another commit or an API error fails immediately. The helper creates the tag only once and never moves it during recovery.

The `ci-devel` and `ci-main` releases are bookmarks. Their tags are created once and never moved. Only the release body changes, atomically pointing at a complete version release. Main and devel indexes are independent. Source ancestry prevents an old-source rerun from displacing a newer branch version; a diverged history requires resolution rather than silently rolling back. The index is a locator, not sufficient firmware identity. PR jobs have no write token and never publish.

## Retrieval and installer discovery contract

[`scripts/ci/download.py`](../../scripts/ci/download.py) retrieves an explicitly selected run/attempt. It requires the actual GitHub run to be a completed successful canonical `devel`, `main` or `release` push/manual run with the expected source and workflow path/ID. It checks every required job, both immutable artifact IDs, expiry and archive digests, safely extracts each archive, then independently validates the manifest, all file sizes/hashes, actual test reports, source and dependency identity, linked ELF and UF2. `verified-download.json` records the post-upload artifact IDs/archive digests separately from the archived manifest.

Run it from this repository with the Python dependencies, Arm inspection tools and a locally built pinned picotool on `PATH`, substituting the recorded immutable identities. Verification re-reads the ELF's program name, description, version, board, SDK and build type with picotool and compares the retained report:

```sh
python scripts/ci/download.py --branch devel --run RUN_ID --attempt ATTEMPT \
  --source FULL_SOURCE_SHA --version FIRMWARE_VERSION \
  --destination build/verified-ci-UNIQUE_DIRECTORY
```

Use the selected bundle's immutable identities. Local inspection tools are trusted inputs: build picotool from the pinned source in `inputs.json`. The verifier requires v2.3.0 and records its resolved path, executable hash and version in the download receipt; a version string alone does not authenticate a locally supplied executable. A mutable latest-successful label or manifest `deployment_candidate` flag is only a locator/hint. Selection from Actions storage must independently require the canonical repository/workflow/source, successful **whole run**, required successful job and complete matching artifact pair. A partially uploaded, failed, cancelled, expired or PR run is ineligible for Actions retrieval even if one artifact exists. An intentionally skipped publisher in a workflow with explicit publication opt-in is allowed for read-only retrieval. A failed or cancelled publisher is ineligible. Published installer bundles still require successful publication.

For beta/final artifacts, use `--branch release` and the exact semantic version without `v`; source/run/attempt remain mandatory. This works before publication and, with `--published`, from preserved release assets after Actions expiry. The downloader checks the current tag target against the exact source as well as the workflow ref, manifest, release classification and receipt. Tag builds do not inherit the source branch's CI image identity.

For preserved release archives use the same explicit identity and add `--published`. This path verifies the public release/tag, preserved verification receipt, original archive hashes, canonical manifest and actual linked image without requiring expired Actions storage. It cannot infer later physical qualification from the preserved software evidence. The public web download links need no end-user GitHub token; the developer verification CLI uses `gh`.

Read a branch bookmark without publishing anything:

```sh
python scripts/ci/publish.py --resolve devel
python scripts/ci/publish.py --resolve main
```

Latest means newest accepted source along the selected branch's ancestry, not the latest run timestamp. An older-source rerun or release re-upload cannot overtake a newer accepted source. Resolve one complete immutable normal bundle per installation; retain source/run/attempt, profile, manifest and UF2 hashes.

Useful upstream references are [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch), [secure workflow use](https://docs.github.com/en/actions/reference/security/secure-use) and [artifact storage](https://docs.github.com/en/actions/tutorials/store-and-share-data).
