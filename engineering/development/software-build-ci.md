# Software/build CI and consumer firmware

The maintained workflow is `.github/workflows/software-build.yml`, named **Software and firmware**. It checks portable software and SDK-backed host adapters on Linux, then cross-builds one generic, uninhibited `WsprryPico` consumer image for Pico 2 W at the normal 138 MHz clock. There are no per-band deployment builds. `WsprryPico-Inhibited` and compatibility RF targets are regression builds; their UF2s are excluded from the deployment bundle.

Images contain no applied station identity, device credentials, or enabled schedule. New station configurations default to a 14095600 Hz WSPR dial and a disabled ten-minute UTC-aligned schedule. Existing saved selections, including an unset frequency, survive upgrades. An absent frequency blocks ownership, watermark reservation, preparation, and arming. A first frequency save leaves schedules disabled until explicitly enabled. A Type 2/3 pair freezes its chosen frequency for both frames. Generic upgrades preserve explicitly saved settings; no whole-flash erase is required. Downgrade preservation of the extended stored configuration is unqualified. Full-board boot, USB, RF, and timing acceptance remain separate.

## Build identity

Pushes to `devel`, `main`, and semantic `v<version>` tags run checks and build firmware. Pull requests to either branch build preview images. There are no path filters or build cancellation groups. Manual dispatch accepts the enumerated `consumer` profile. Ordinary embedded versions use `0.1.0-ci.<run-id>.<attempt>`; firmware tags use `v` followed by SemVer. The embedded version omits `v`, accepts valid build metadata, and is limited to 128 ASCII characters. Numeric identifiers obey SemVer leading-zero rules. Firmware versions do not select control or storage compatibility.

The full checked-out source SHA identifies each build. PR heads, synthetic merge commits, and trusted branch commits are distinct. Preview artifacts are not trusted installation candidates. Verification is read-only; a successful build grants no publication authority. The installer consumes immutable, verified bundles independently of its own implementation version.

Firmware help links use the `devel` operator manual for development builds and all
prereleases, including release candidates. Stable release tags and `main` builds
use the `main` manual, reserved for stable releases starting with `1.0.0`.

## Inputs and checks

[`scripts/ci/inputs.json`](../../scripts/ci/inputs.json) pins SDK, all linked SDK submodules, picotool, the read-only qualification Harness, the Arm Linux archive, and actual Wi-Fi/Bluetooth resources. SDK 2.3.1 and Arm compiler 15.3.1 remain unchanged. The official Arm archive's SHA-256 is checked before extraction; dependency Git identities and clean submodules are checked before use. No dependency cache substitutes for verification. SDK/firmware/host build directories are separate and fresh.

[`scripts/ci/requirements.txt`](../../scripts/ci/requirements.txt) contains exact host-tool/test versions and official PyPI artifact hashes. Python/Node versions are pinned; npm uses the checked-in lockfile. Runner image/version, host compiler, OpenSSL, Chrome, CMake/Ninja, Python/Node, and installed package versions are recorded. Host/compiler/system libraries supplied by the named runner image are inventoried rather than claimed to be a byte-reproducible container.

[`scripts/ci/run.py`](../../scripts/ci/run.py) is the executable recipe. It supplies TinyUSB, BTstack, lwIP, CYW43, Mbed TLS, and the exact reviewed companion source to optional SDK-backed host tests, supplies the pinned Harness source for offline analysis, installs npm dependencies before CTest, and checks that the expected source test inventory was registered. Missing Node/Python modules or the compiled endpoint fixture fail CI. All registered CTest cases must execute successfully. WTP contract validation, npm browser tests, real consumer frequency UI checks, and packaging failure tests are additional required gates.

Current CI requires the exact registered CTest inventory and rejects failed, cancelled, skipped, empty, duplicate, truncated, or incomplete framework execution. Python assertion-based checks refuse optimized Python. The verifier retains the exact [legacy test skip reasons](../../scripts/ci/legacy-test-skip-reasons.json) only to verify already-published images whose frozen source registered evidence-only tests. Current builds record an empty legacy skip inventory. Hardware acceptance remains separate from these software checks.

Firmware builds retain linked engine, heap, stack/guard, pool, renderer, GP14/BOOTSEL, flash, and UF2 checks. The deployment verifier checks the current contract-2 application flash boundary `0x103ec000`, the exact pinned RP2350-E10 workaround, UF2 numbering/family/payload correspondence with the linked ARM ELF, generated and embedded identities, actual target/clock/consumer flags, and generic inputs. Two fresh normal builds must produce identical UF2s for the same declared source/version/inputs. This check does not promise reproducibility across every runner image or toolchain revision.

The update boundary is checked against the linker reservation in the exact frozen source revision. New bundles reserve the final 72 KiB, including the separate NTP-learning journal. Verification also accepts historical `0x103f0000` bundles when their source revision requires that layout. Their integrity does not qualify downgrades to preserve the new cache.

Local checks remain documented in [the development commands](README.md#deterministic-validation). Use a fresh build directory; caches containing unsupported build-time frequency selections refuse explicitly. The normal firmware recipe is documented in [firmware foundation](firmware-foundation.md). CI's Linux dependency setup is explicit; it never installs a toolchain on macOS.

## Canonical bundle and retention

The current deployment manifest uses [schema version 2](../../scripts/ci/release-manifest-2.schema.json). Older [version 1](../../scripts/ci/release-manifest-1.schema.json) bundles remain readable with their frozen producer rules. The canonical `release-manifest.json` describes the deployment payload for CI and preserved firmware bundles. Deployment, settings/control, WTP, transport, and storage versions are independent. The inhibited candidate-fixture manifest is a different contract.

The deployment allowlist is exactly:

- `WsprryPico-<version>-pico2_w.uf2`
- `release-manifest.json`
- `SHA256SUMS`
- `LICENSE.md`, `THIRD_PARTY_NOTICES.md`, `DEPENDENCY-LICENSES.txt`

The manifest lists payload and required notice hashes, plus the separately downloadable audit inventory. It does not hash itself. `SHA256SUMS` covers the UF2, manifest, and notices, and excludes itself. Checksums establish byte integrity; they are not signatures or independent physical qualification. The audit includes linked ELF/map, generated identity, compile commands, configuration, picotool identity, generated overlays, logs, and actual test reports. It contains no device keys or private capture packets.

The artifact pair is named `WsprryPico-firmware-<branch>-<run>-<attempt>-consumer` and `WsprryPico-audit-<branch>-<run>-<attempt>-consumer`, retained for 90 days. PR previews use `pull-request` in place of the branch. The downloader also recognizes the original branchless devel artifact names. Failed builds may retain separately named diagnostic logs for 14 days.

## Retrieval and installer discovery contract

[`scripts/ci/download.py`](../../scripts/ci/download.py) retrieves an explicitly selected run/attempt. It requires the actual GitHub run to be a completed successful canonical `devel`, `main`, or `release` push/manual run with the expected source and workflow path/ID. It binds trusted workflow/run/attempt/source/repository metadata and unique job IDs, exact run/job/check-run URIs, artifact origin, both immutable artifact IDs, expiry, and archive digests, safely extracts each archive, then independently validates the manifest, all file sizes/hashes, actual test reports, source and dependency identity, linked ELF, and UF2. `verified-download.json` records the post-upload artifact IDs/archive digests separately from the archived manifest.

Run it from this repository with the Python dependencies, Arm inspection tools, and a locally built pinned picotool on `PATH`, substituting the recorded immutable identities. Verification re-reads the ELF's program name, description, version, board, SDK, and build type with picotool and compares the retained report:

```sh
python scripts/ci/download.py --branch devel --run RUN_ID --attempt ATTEMPT \
  --source FULL_SOURCE_SHA --version FIRMWARE_VERSION \
  --destination build/verified-ci-UNIQUE_DIRECTORY
```

Use the selected bundle's immutable identities. Local inspection tools are trusted inputs: build picotool from the pinned source in `inputs.json`. The verifier requires v2.3.0 and records its resolved path, executable hash, and version in the download receipt; a version string alone does not authenticate a locally supplied executable. A mutable latest-successful label or manifest `deployment_candidate` flag is only a locator/hint. Selection from Actions storage must independently require the canonical repository/workflow/source, successful **whole run**, required successful job, and complete matching artifact pair. A partially uploaded, failed, cancelled, expired, or PR run is ineligible for Actions retrieval even if one artifact exists. An intentionally skipped publisher in a workflow with explicit publication opt-in is allowed for read-only retrieval. A failed or cancelled publisher is ineligible. Published installer bundles still require successful publication.

For preserved archives, add `--published` to the explicit source/run/attempt selection. Verification binds the public tag, receipt, original archive hashes, manifest, and linked image without requiring expired Actions storage. Public web downloads need no end-user GitHub token; the developer CLI uses `gh`. Neither path establishes physical qualification.

Read a branch bookmark without changing it:

```sh
python scripts/ci/publish.py --resolve devel
python scripts/ci/publish.py --resolve main
```

A bookmark identifies the newest accepted source along the selected branch's ancestry, independently of run timestamps. Installation uses one complete immutable bundle with its source/run/attempt, profile, manifest, and UF2 hashes.


## Execution completeness and local qualification

The canonical harness uses pinned Python 3.12.11 and Node 24.8.0. The shared Python
ownership/evidence helpers require Python 3.11 or newer; the standalone installer's
separate Python support contract is unchanged. Do not use `-O` or PYTHONOPTIMIZE
for assertion-based checks.

[`execution-policy.json`](../../scripts/ci/execution-policy.json) declares eighteen
required command contexts. Its independently versioned `ci-execution-policy/2`
requires the producer's frozen
[`ctest-completion-policy.json`](../../scripts/ci/ctest-completion-policy.json).
Every declared Python unittest and Node test entry point must report its exact
nonempty case count with no skips, TODOs, cancellations, or duplicate summaries.
CTest's successful and failed output limits are both one MiB so the required
framework footers remain available; output truncation refuses acceptance. These
policies add evidence without changing deployment or control major versions.
Older bundles use the policy selected from their own immutable source.

Each command's `execution.json` record binds source, run/attempt, command, working
directory, monotonic elapsed span, actual exit, completion evidence, and exact log
byte range/hash. Failed commands retain failed receipts. Assembly requires the
complete successful context set, registered commands, JUnit XML, framework counts,
and source-bound logs. An uploaded producer label alone cannot establish trust;
retrieval independently checks the actual GitHub Actions workflow and jobs.

A local build can omit optional SDK-backed registrations and analysis dependencies.
Its successful subset does not qualify the canonical lane. Select focused tests
from `ctest --test-dir BUILD --show-only=json-v1` and use `--no-tests=error`:

```sh
ctest --test-dir BUILD --no-tests=error --output-on-failure -R REGISTERED_NAME_REGEX
```

Reconcile the selected result inventory before reporting success. The full lane
requires all source-declared contexts and optional dependencies selected by the
canonical recipe. Linux tool-download checks execute as an ordinary user; running
their filesystem/permission assertions as root is not equivalent evidence.

## Fixture ownership, clocks, and resources

Native browser scenarios use
[`browser_harness.mjs`](../../tests/browser_harness.mjs),
[`browser_scope.mjs`](../../tests/browser_scope.mjs),
[`browser_cdp.mjs`](../../tests/browser_cdp.mjs), and
[`browser_deadline.mjs`](../../tests/browser_deadline.mjs).
[`fixture_process.mjs`](../../tests/fixture_process.mjs) and
[`fixture_process.py`](../../tests/fixture_process.py) own command/reply fixtures.
Register ownership before fallible initialization, preserve the original error
alongside cleanup errors, check late child exits, stop every owned writer, and
remove private profiles only after observed termination. Cancellation remains
visible through qualification, receipt commit, and signal-handler handoff; its
non-I/O exception cannot be swallowed as a recoverable OSError. Child/cancellation
failures remain grouped with log, storage, or handler-restoration failures.
Worker/module paths
resolve relative to their owning module; the caller's working directory does not
select another repository's worker.

Readiness requires actual protocol/state evidence. TLS control commands acknowledge
foreground polling before logical time advances; hostname cancellation holds and
executes the actual callback. Keep product timing unchanged, distinguish logical
test time from real host time, and retain finite independent hang watchdogs when a
clock is injected. A fixed delay or absent marker does not qualify readiness,
expiry, cancellation, or cleanup. Startup qualification includes a live page;
partial/malformed discovery, stalled bodies, late success, and early exits refuse.

The canonical CTest command uses two workers. Keep all existing RUN_SERIAL
exclusions: network/interop fixtures own loopback 18443/18444 and generated test
credentials, and the session pilot owns its exclusive browser fixture. Native
profile qualification uses separate 19439, 19459/19461, and 19479–19488 ports.
Standalone browser commands retain sequential ownership of 19139 (pilot 19149).
Other startup endpoints use ephemeral ports; profiles, journals, and scratch
outputs are private. The selected-source regression caps its nested compilation
at four workers. Recheck ports, files, credentials, memory, and nested process
budgets before increasing concurrency or replacing an exclusion with a lock.

The thirteen native-browser command contexts are frequency, first-use,
session-timeout, progress, recovery, submission, hostname, organization, WSPR,
message-frequency, operator, sections-consumer, and sections-engineering. The
message-frequency invocation uses two sequential browsers; recovery uses three
isolated contexts inside one browser, while hostname/organization use separate
device tabs. These are different counting units. Seven review-server invocations
select eight actual native profiles in total; direct-fixture/replacement starts
and regression processes are additional. Preserve source/shipped paths, layout
assertions, captures, real crypto, independent journals, and the explicit first-use
USB/overlay/network-backing and field-AP options. Capture suppression must not skip
behavior or layout assertions.

### Native scenario obligations

| Suite / invocation | Fixture contexts | Browser contexts and distinct obligations |
| --- | --- | --- |
| Frequency, ordinary | consumer-lan | Shipped assets, independent dial read/save/refusal, accessibility, responsive captures |
| Frequency, first-use network | first-use-network | Fresh journal, missing station, first WSPR transmission trial |
| Frequency, explicit opt-ins | engineering refusal; first-use usb/overlay/network-backing | Preserve argument mapping, original profile offsets, and separate journals; not ordinary invocations |
| Session pilot | consumer-lan | Qualified expiry/drafts/refusal, four captures, independent journal oracle |
| Submission | consumer-lan | Shipped assets, keyboard/touch/modal, held requests, cancellation, lost replies, logging, abort, suspension |
| Sections, consumer | consumer-lan | Shipped assets, help/popups, keyboard/focus, files/History, lock/logout, RF/GPS controls, captures |
| Sections, engineering | engineering | Separate command/browser/journal; certificate authority, help, Si5351/GPS controls |
| Sections, field opt-in | consumer-ap | Preserve AP port/authority and field-clock/settings checks; no hardware execution |
| Message-frequency | consumer-lan and engineering | One invocation, two sequential browsers, independent profiles, both schedule/control surfaces and captures |
| Recovery | direct production fixture | One browser, three isolated browser contexts; drafts, foreign-client saves, lost replies, session limits, recovery/retirement |
| Hostname | direct A/B fixtures | Two device tabs, reboot, identity, pending cancellation, long names, wrong-device refusal, captures |
| Organization | direct A/B and replacement fixtures | Two device tabs, commissioning/recovery, replacement/reboot, lost replies, navigation and optional axe/captures |
| WSPR | direct fixtures and replacement | Shipped bundle, Type 2/3, station/profile revisions, saved/applied distinctions and captures |
| Progress | direct fixtures and replacement | Consumer/engineering routes, held/lost replies, partial/null fields, stale/future schemas, optional axe/captures |
| Operator cleanup | direct session fixture and source/shipped assets | Preserve intentional source HTML plus minified script/bundle path, status, filters, grids, GPIO, uncertainty/recovery, captures |


The standalone lifecycle group runs cleanup, startup, and contextual-help tests.
Its source-bound completion count includes early-exit observation, initialization
cancellation, and recovery of descendants after an abrupt owner exit. The actual
companion workflow invokes these modules from its own working directory.

## Build reuse and source pairs

The selected host-client libraries share five freshly compiled objects only for
the same physical companion source root, under the common stricter warning flags.
Both consumer archives, source verifiers, and real consumers remain. Different
roots receive independent objects. Header, source, and flag edits must invalidate
and rebuild the affected code; missing sources and genuine compiler failures
refuse without falling back to another peer.

Normal and inhibited firmware targets share common objects in the first fresh
configuration. Target-specific definitions, engines, generated inputs, image
checks, and separate audit outputs remain; normal ELF/map/UF2 bytes must remain
unchanged after the inhibited build. The second normal reproducibility build uses
an independently fresh directory. Existing output directories, files, and broken
symlinks refuse instead of being reused or removed. Compiler overrides/launchers
refuse, and actual firmware compiler commands must invoke the verified Arm tools
directly. No object cache substitutes for fresh reproducibility.

Both production network and USB suites are required when shared fixtures or
protocol-facing behavior changes. Select actual candidate sources, pinned
Mbed TLS and recursive framework, and current companion consumers explicitly.
The authoritative Pi recipes are its `.github/workflows/debian-non-hardware.yml`
`wtp-network-loopback` and `wtp-usb-management-pair` jobs. With candidate host targets
already configured and retained dependencies, the required software commands are:

```sh
export WSPRRYPI_DISABLE_HARDWARE_ACCESS=1
cmake --build "$PICO_BUILD" --target usb_management_driver
make -C "$PI_SOURCE/src" wtp-network-runtime-test BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= WTP_NETWORK_BUILD_DIR="$PAIR_BUILD"
make -C "$PI_SOURCE/src" wtp-network-interop-test wtp-config-interop-test SUDO= PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE" WTP_NETWORK_BUILD_DIR="$PAIR_BUILD"
make -C "$PI_SOURCE/src" wtp-usb-pair-client-build wtp-usb-management-test SUDO=
node "$PI_SOURCE/WsprryPi-UI/tests/wtp_usb_settings_test.js"
WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node "$PI_SOURCE/WsprryPi-UI/tests/wtp_usb_pair_test.js" "$PI_SOURCE/src/build/wtp-network/wtp_usb_pair_client" "$PICO_BUILD/usb_management_driver"
```

Use distinct existing or unused build locations with identified duties. Explicitly
set WSPRRY_PICO_WSPRRYPI_SOURCE and WSPRRY_PICO_NETWORK_CLIENT_SOURCE to the intended
companion when configuring full host coverage. Record both actual revisions,
working changes/hashes, dependencies, exact commands, and results. Failed,
cancelled, timed-out, skipped, wrong-source, or missing required checks remain
unresolved. An unmerged paired branch is feature-branch delivery, not delivery on
devel/main. These fixtures exercise production handlers, crypto, serialization,
framing/ACK, and journals without physical USB or RF qualification.

## Merge gates and performance observations

Pico devel requires the current up-to-date candidate's `verify` check from GitHub
Actions, pull-request merging, and administrator enforcement. Force pushes and
branch deletion are disabled. Optional publication remains separate. Restore a
broken verifier through a tested PR; do not weaken protection to accept a failed
or absent result. A documentation commit skipped by CI cannot merge until its
current candidate is verified.

Reliability, safety, complete coverage, and independent defect detection govern
optimization. Compare identical source pairs, case inventories, tools, resource
budgets, and fresh/warm states. Predeclare bounded observations, retain every
first-attempt failure, and separate queue, setup, command spans, and whole-job
elapsed time. Different-source hosted runs are observational comparisons. Do not
infer a flake rate from a small green sample or retry until green. Physical files,
code/bytes, logical cases, commands, native processes, browsers, compilations,
links, jobs, and matrices have separate denominators; unused fixture retirement
receives no reduction-goal credit. Reduction targets cannot remove required work.
