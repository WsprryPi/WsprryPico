# Software/build CI and consumer firmware

The maintained workflow is `.github/workflows/software-build.yml`, named
**Software and firmware**. It checks portable software and SDK-backed host
adapters on Linux, then cross-builds one generic, uninhibited `WsprryPico`
consumer image for Pico 2 W at the normal 138 MHz clock. There are no per-band
deployment builds. `WsprryPico-Inhibited` and compatibility RF targets are
regression builds; their UF2s are excluded from the deployment bundle.

Images contain no selected transmit frequency, station identity, device
credentials or enabled schedule. Standalone WSPR frequency is explicitly saved
at runtime. An absent frequency blocks ownership, watermark reservation,
preparation and arming. A first frequency save leaves schedules disabled until
explicitly enabled. A Type 2/3 pair freezes its chosen frequency for both frames.
Generic upgrades preserve explicitly saved settings; no whole-flash erase is
required. Downgrade preservation of the extended stored configuration is
unqualified. Full-board boot, USB, RF and timing acceptance remain separate.

## Triggers and identity

Pushes to `devel` and pull requests targeting `devel`/`main` run checks. Only
three evidence/planning files are excluded from push triggering: the CI result
record, consolidated backlog and saved CI execution prompt. Actual source,
build inputs, schemas, browser assets, notices and product documentation remain
covered. The first workflow run bootstraps through the authorized `devel` push;
manual dispatch is not assumed available while `main` lacks this workflow.
Repository settings and the default branch are unchanged.

Manual dispatch, where available, accepts only the enumerated `consumer`
profile. Embedded versions are generated before building as
`0.1.0-ci.<run-id>.<attempt>`. There is no version override. Different attempts
have different identities; future public download tags may use `v` followed by
this exact version. No tag or release is created by CI. A later release or
installer publication retains the original version, source and UF2 bytes.

The actual checked-out full source SHA is recorded. PR head, synthetic merge
commit and trusted `devel` are distinct identities. PR artifacts are test
outputs and cannot be selected as the trusted consumer deployment candidate.
The source commit containing firmware/workflow inputs is **F**. A later
evidence-only commit **E** records acceptance without relabelling F's firmware.

## Inputs and checks

[`scripts/ci/inputs.json`](../../scripts/ci/inputs.json) pins SDK, all linked
SDK submodules, picotool, the Arm Linux archive and actual Wi-Fi/Bluetooth
resources. SDK 2.3.1 and Arm compiler 15.3.1 remain unchanged. The official Arm
archive's SHA-256 is checked before extraction; dependency Git identities and
clean submodules are checked before use. No dependency cache substitutes for
verification. SDK/firmware/host build directories are separate and fresh.

[`scripts/ci/requirements.txt`](../../scripts/ci/requirements.txt) contains exact
host-tool/test versions and official PyPI artifact hashes. Python/Node versions
are pinned; npm uses the checked-in lockfile. Runner image/version, host compiler,
OpenSSL, Chrome, CMake/Ninja, Python/Node and installed package versions are
recorded. Host/compiler/system libraries supplied by the named runner image
are inventoried rather than claimed to be a byte-reproducible container.

[`scripts/ci/run.py`](../../scripts/ci/run.py) is the executable recipe. It
supplies TinyUSB, BTstack, lwIP, CYW43, Mbed TLS and the exact reviewed companion
source to optional SDK-backed host tests, and checks that the expected source
test inventory was registered. Missing Node/Python modules or the compiled
endpoint fixture fail CI. All registered CTest cases must execute successfully.
WTP contract validation, npm browser tests, real consumer frequency UI checks
and packaging failure tests are additional required gates.

Private historical hardware/capture packets are unavailable on a fresh runner.
Only the exact reviewed historical-evidence reasons in
[`allowed-evidence-skips.json`](../../scripts/ci/allowed-evidence-skips.json)
may skip individual historical assertions. Their test IDs and reasons are
recorded separately; they are not counted as executed hardware acceptance.
A missing required compiler, module, fixture or behavior test cannot use that
disposition.

Firmware builds retain linked engine, heap, stack/guard, pool, renderer,
GP14/BOOTSEL, flash and UF2 checks. The deployment verifier checks the current
application flash boundary `0x103f0000`, the exact pinned RP2350-E10 workaround,
UF2 numbering/family/payload correspondence with the linked ARM ELF, generated
and embedded identities, actual target/clock/consumer flags and generic inputs.
Two fresh normal builds must produce identical UF2s for the same declared
source/version/inputs. This check does not promise reproducibility across every
runner image or toolchain revision.

Local checks remain documented in [the development commands](README.md#routine-checks).
Use a fresh build directory after removal of build-time frequency selection;
stale caches containing that removed option refuse explicitly. The normal
firmware recipe is documented in [firmware foundation](firmware-foundation.md).
CI's Linux dependency setup is explicit; it never installs a toolchain on macOS.

## Canonical bundle and retention

Schema version 1 is
[`release-manifest-1.schema.json`](../../scripts/ci/release-manifest-1.schema.json).
The same canonical `release-manifest.json` serves CI, future installer downloads
and later testing-prerelease publication. It is independent of WTP and API
versions. The historical Phase 12 fixture manifest is a different contract.

The deployment allowlist is exactly:

- `WsprryPico-<version>-pico2_w.uf2`
- `release-manifest.json`
- `SHA256SUMS`
- `LICENSE.md`, `THIRD_PARTY_NOTICES.md`, `DEPENDENCY-LICENSES.txt`

The manifest lists payload and required notice hashes, plus the separately
downloadable audit inventory. It does not hash itself. `SHA256SUMS` covers the
UF2, manifest and notices, and excludes itself. Checksums establish byte
integrity; they are not signatures or independent physical qualification.
The audit includes linked ELF/map, generated identity, compile commands,
configuration, picotool identity, generated overlays, logs and actual test
reports. It contains no device keys or private capture packets.

The artifact pair is named
`WsprryPico-firmware-<run>-<attempt>-consumer` and
`WsprryPico-audit-<run>-<attempt>-consumer`, retained for 90 days. Failed builds
may retain separately named diagnostic logs for 14 days. Downloads chosen for
decode, installer or publication must be retained locally before expiry.
Expired or changed candidates require explicit reassessment; silently
rebuilding is not exact-byte promotion.

## Retrieval and installer discovery contract

[`scripts/ci/download.py`](../../scripts/ci/download.py) retrieves an explicitly
selected run/attempt. It requires the actual GitHub run to be a completed
successful canonical `devel` push/manual run with the expected source and
workflow path/ID. It checks the required job, both immutable artifact IDs,
expiry and archive digests, safely extracts each archive, then independently
validates the manifest, all file sizes/hashes, actual test reports, source and
dependency identity, linked ELF and UF2. `verified-download.json` records the
post-upload artifact IDs/archive digests separately from the archived manifest.

Run it from this repository with the Python dependencies, Arm inspection tools
and a locally built pinned picotool on `PATH`, substituting the recorded immutable
identities. Verification re-reads the ELF's program name, description, version,
board, SDK and build type with picotool and compares the retained report:

```sh
python scripts/ci/download.py --run RUN_ID --attempt ATTEMPT \
  --source FULL_SOURCE_SHA --version FIRMWARE_VERSION \
  --destination build/verified-ci-UNIQUE_DIRECTORY
```

The result record supplies concrete values after acceptance. Local inspection
tools are trusted inputs: build picotool from the pinned source in
`inputs.json`. The verifier requires v2.3.0 and records its resolved
path, executable hash and version in the download receipt; a version string
alone does not authenticate a locally supplied executable. A mutable
latest-successful label or manifest `deployment_candidate` flag is only a
locator/hint. Installer selection must independently require the canonical
repository/workflow/source, successful **whole run**, required successful job
and complete matching artifact pair. A partially uploaded, failed, cancelled,
expired or PR run is ineligible even if one artifact exists.

Latest means newest accepted source along canonical `devel` ancestry, not the
latest run timestamp. An older-source rerun or release re-upload cannot
overtake a newer accepted source. Resolve one complete immutable normal bundle
per installation; retain source/run/attempt, profile, manifest and UF2 hashes.
The future installer may publish those exact verified bytes as public CI
download prereleases so its default does not require a user GitHub token.
That publication and the installer itself are outside this CI task.

Useful upstream references are [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch),
[secure workflow use](https://docs.github.com/en/actions/reference/security/secure-use)
and [artifact storage](https://docs.github.com/en/actions/tutorials/store-and-share-data).
