# Software/build CI and consumer firmware

The maintained workflow is `.github/workflows/software-build.yml`, named **Software and firmware**. It checks portable software and SDK-backed host adapters on Linux, then cross-builds one generic, uninhibited `WsprryPico` consumer image for Pico 2 W at the normal 138 MHz clock. There are no per-band deployment builds. `WsprryPico-Inhibited` and compatibility RF targets are regression builds; their UF2s are excluded from the deployment bundle.

Images contain no applied station identity, device credentials, or enabled schedule. New station configurations default to a 14095600 Hz WSPR dial and a disabled ten-minute UTC-aligned schedule. Existing saved selections, including an unset frequency, survive upgrades. An absent frequency blocks ownership, watermark reservation, preparation, and arming. A first frequency save leaves schedules disabled until explicitly enabled. A Type 2/3 pair freezes its chosen frequency for both frames. Generic upgrades preserve explicitly saved settings; no whole-flash erase is required. Downgrade preservation of the extended stored configuration is unqualified. Full-board boot, USB, RF, and timing acceptance remain separate.

## Build identity

Pushes to `devel`, `main`, and semantic `v<version>` tags run checks and build
firmware. Pull requests to either branch build preview images. There are no
path filters or build cancellation groups. Manual dispatch accepts the enumerated
`consumer` profile. Ordinary embedded versions use `0.1.0-ci.<run-id>.<attempt>`;
firmware tags use `v` followed by SemVer. The embedded version omits `v`, accepts
valid build metadata, and is limited to 128 ASCII characters. Numeric identifiers
obey SemVer leading-zero rules. Firmware versions do not select control or
storage compatibility.

The full checked-out source SHA identifies each build. PR heads, synthetic
merge commits, and trusted branch commits are distinct. Preview artifacts are
not trusted installation candidates. Verification is read-only; a successful
build grants no publication authority. The installer consumes immutable,
verified bundles independently of its own implementation version.

## Inputs and checks

[`scripts/ci/inputs.json`](../../scripts/ci/inputs.json) pins SDK, all linked SDK submodules, picotool, the read-only qualification Harness, the Arm Linux archive and actual Wi-Fi/Bluetooth resources. SDK 2.3.1 and Arm compiler 15.3.1 remain unchanged. The official Arm archive's SHA-256 is checked before extraction; dependency Git identities and clean submodules are checked before use. No dependency cache substitutes for verification. SDK/firmware/host build directories are separate and fresh.

[`scripts/ci/requirements.txt`](../../scripts/ci/requirements.txt) contains exact host-tool/test versions and official PyPI artifact hashes. Python/Node versions are pinned; npm uses the checked-in lockfile. Runner image/version, host compiler, OpenSSL, Chrome, CMake/Ninja, Python/Node and installed package versions are recorded. Host/compiler/system libraries supplied by the named runner image are inventoried rather than claimed to be a byte-reproducible container.

[`scripts/ci/run.py`](../../scripts/ci/run.py) is the executable recipe. It supplies TinyUSB, BTstack, lwIP, CYW43, Mbed TLS, and the exact reviewed companion source to optional SDK-backed host tests, supplies the pinned Harness source for offline analysis, installs npm dependencies before CTest, and checks that the expected source test inventory was registered. Missing Node/Python modules or the compiled endpoint fixture fail CI. All registered CTest cases must execute successfully. WTP contract validation, npm browser tests, real consumer frequency UI checks and packaging failure tests are additional required gates.

Current CI rejects skipped CTest cases and internally skipped Python assertions. The verifier retains the exact [legacy test skip reasons](../../scripts/ci/legacy-test-skip-reasons.json) only to verify already-published images whose frozen source registered evidence-only tests. Current builds record an empty legacy skip inventory. Hardware acceptance remains separate from these software checks.

Firmware builds retain linked engine, heap, stack/guard, pool, renderer, GP14/BOOTSEL, flash, and UF2 checks. The deployment verifier checks the current contract-2 application flash boundary `0x103ec000`, the exact pinned RP2350-E10 workaround, UF2 numbering/family/payload correspondence with the linked ARM ELF, generated and embedded identities, actual target/clock/consumer flags and generic inputs. Two fresh normal builds must produce identical UF2s for the same declared source/version/inputs. This check does not promise reproducibility across every runner image or toolchain revision.

The update boundary is checked against the linker reservation in the exact frozen source revision. New bundles reserve the final 72 KiB, including the separate NTP-learning journal. Verification also accepts historical `0x103f0000` bundles when their source revision requires that layout. Their integrity does not qualify downgrades to preserve the new cache.

Local checks remain documented in [the development commands](README.md#deterministic-validation). Use a fresh build directory; caches containing unsupported build-time frequency selections refuse explicitly. The normal firmware recipe is documented in [firmware foundation](firmware-foundation.md). CI's Linux dependency setup is explicit; it never installs a toolchain on macOS.

## Canonical bundle and retention

Schema version 1 is [`release-manifest-1.schema.json`](../../scripts/ci/release-manifest-1.schema.json). The canonical `release-manifest.json` describes the deployment payload for CI and preserved firmware bundles. It is independent of WTP and API versions. The inhibited candidate-fixture manifest is a different contract.

The deployment allowlist is exactly:

- `WsprryPico-<version>-pico2_w.uf2`
- `release-manifest.json`
- `SHA256SUMS`
- `LICENSE.md`, `THIRD_PARTY_NOTICES.md`, `DEPENDENCY-LICENSES.txt`

The manifest lists payload and required notice hashes, plus the separately downloadable audit inventory. It does not hash itself. `SHA256SUMS` covers the UF2, manifest, and notices, and excludes itself. Checksums establish byte integrity; they are not signatures or independent physical qualification. The audit includes linked ELF/map, generated identity, compile commands, configuration, picotool identity, generated overlays, logs, and actual test reports. It contains no device keys or private capture packets.

The artifact pair is named `WsprryPico-firmware-<branch>-<run>-<attempt>-consumer` and `WsprryPico-audit-<branch>-<run>-<attempt>-consumer`, retained for 90 days. PR previews use `pull-request` in place of the branch. The downloader also recognizes the original branchless devel artifact names. Failed builds may retain separately named diagnostic logs for 14 days.

## Retrieval and installer discovery contract

[`scripts/ci/download.py`](../../scripts/ci/download.py) retrieves an explicitly selected run/attempt. It requires the actual GitHub run to be a completed successful canonical `devel`, `main` or `release` push/manual run with the expected source and workflow path/ID. It checks every required job, both immutable artifact IDs, expiry and archive digests, safely extracts each archive, then independently validates the manifest, all file sizes/hashes, actual test reports, source and dependency identity, linked ELF, and UF2. `verified-download.json` records the post-upload artifact IDs/archive digests separately from the archived manifest.

Run it from this repository with the Python dependencies, Arm inspection tools and a locally built pinned picotool on `PATH`, substituting the recorded immutable identities. Verification re-reads the ELF's program name, description, version, board, SDK and build type with picotool and compares the retained report:

```sh
python scripts/ci/download.py --branch devel --run RUN_ID --attempt ATTEMPT \
  --source FULL_SOURCE_SHA --version FIRMWARE_VERSION \
  --destination build/verified-ci-UNIQUE_DIRECTORY
```

Use the selected bundle's immutable identities. Local inspection tools are trusted inputs: build picotool from the pinned source in `inputs.json`. The verifier requires v2.3.0 and records its resolved path, executable hash and version in the download receipt; a version string alone does not authenticate a locally supplied executable. A mutable latest-successful label or manifest `deployment_candidate` flag is only a locator/hint. Selection from Actions storage must independently require the canonical repository/workflow/source, successful **whole run**, required successful job and complete matching artifact pair. A partially uploaded, failed, cancelled, expired, or PR run is ineligible for Actions retrieval even if one artifact exists. An intentionally skipped publisher in a workflow with explicit publication opt-in is allowed for read-only retrieval. A failed or cancelled publisher is ineligible. Published installer bundles still require successful publication.

For preserved archives, add `--published` to the explicit source/run/attempt
selection. Verification binds the public tag, receipt, original archive hashes,
manifest, and linked image without requiring expired Actions storage. Public
web downloads need no end-user GitHub token; the developer CLI uses `gh`.
Neither path establishes physical qualification.

Read a branch bookmark without changing it:

```sh
python scripts/ci/publish.py --resolve devel
python scripts/ci/publish.py --resolve main
```

A bookmark identifies the newest accepted source along the selected branch's
ancestry, independently of run timestamps. Installation uses one complete
immutable bundle with its source/run/attempt, profile, manifest, and UF2 hashes.
