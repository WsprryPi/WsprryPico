# Software/build CI result

Status: accepted for software/build CI. The required Linux job, post-download
verification and independent artifact review passed for the exact source,
version and UF2 below. Item 6 is complete within this software-only scope.

## Consumer image contract

The deployment image is one generic `WsprryPico` application for Pico 2 W,
RP2350, normal 138 MHz PIO/DMA RF. Firmware does not select a band, transmit
frequency, station identity, credentials or enabled schedule. Operators save
their settings at runtime. Existing explicit settings survive an ordinary
application update; an older record without frequency remains readable and
nontransmitting. Its first frequency selection leaves schedules disabled until
the operator enables them. Both frames of a Type 2/3 pair use one frequency
snapshot. Downgrade preservation is unqualified.

The independently versioned frequency resource and its browser editor preserve
drafts, require fresh saved-state readback, validate target/boot identity and
ETag, and reject unsupported frequencies or permissions before saving. Legacy
configuration writes preserve this separately owned selection. There is no
build-time frequency override.

## Source and run record

The initial scoped source was `b3d2c65ccc43fc47cb00b266fd1780004f24fea9`.
[Run 39079376747](https://github.com/WsprryPi/WsprryPico/actions/runs/39079376747)
failed workflow parsing before jobs or artifacts: the pip command's `:all:`
token needed a YAML block scalar. The repair adds a YAML parsing check and
completes the design sidecar. It does not reuse a firmware identity.

The first Linux candidate source was
`bc6ef47440be244feafe707a50b770fa09c4826a`.
[Run 39079454637, attempt 1](https://github.com/WsprryPi/WsprryPico/actions/runs/39079454637)
used `0.1.0-ci.39079454637.1`. It registered 232 tests and failed 11 before
packaging: npm installation ran after dependent CTest cases, three offline
suites lacked the Harness package, and a Linux extracted-adapter fixture
lacked current product fields/routes. The repair moves npm installation before
CTest, provides a clean pinned read-only Harness source and updates the
dependency doubles and AP redirect expectation. No product behavior or test
inventory is removed. No deployment image from this failed run is accepted.

Candidate source F is
`af2698182484e858f504121a83a035452e1431a5`.
[Run 39079993419, attempt 1](https://github.com/WsprryPi/WsprryPico/actions/runs/39079993419)
completed successfully on the canonical `devel` push. Required job `verify`
is `117534812987`. Its workflow revision and actual checked-out source are F.
Embedded version is `0.1.0-ci.39079993419.1`. Source tree is
`cc8cfc0adfb56e095f8678bc64f3518800df591a`; the source inventory SHA-256 is
`02e74145938ee6c285c9afe69479b31a31e96de20b985718a018752526de0bef`.

The source commit F supplies the product/workflow/build inputs. This result and
the final backlog status are recorded separately in evidence-only E; E does not
claim that F's firmware was built from E.

## Linux checks and image verification

All 232 registered CTest cases passed, with zero failed or skipped CTest cases.
Registration is checked against the frozen source inventory. SDK-backed TLS,
lwIP, CYW43, TinyUSB, BTstack and pinned companion interoperability checks ran;
the updated Linux adapter test passed. WTP validation, npm browser checks,
twelve packaging checks and the real consumer frequency UI check also
passed. The historical evidence suite ran 235 individual test cases: 170 passed
and 65 skipped for the 49 exact reviewed private-evidence reasons. Their test
IDs/reasons are retained in `audit/evidence-skips.json`; no missing compiler,
module, required fixture or behavior check is accepted as a skip.

The normal `WsprryPico`, inhibited regression and compatibility RF targets
built successfully. Two fresh normal builds at identical source/version/inputs
produced identical UF2 bytes. Only the normal image is deployed; the inhibited
UF2 is excluded. The separate audit retains its ELF and build reports.

Post-download verification independently checked both archive digests, safe
extraction and exact file inventories; manifest schema, source/version and
whole-run/job identity; payload/notice hashes and actual test reports; generated
overlays and dependency identities; linked program name/description/version/
board/SDK/Release metadata using picotool; linked PIO/DMA engine and 138 MHz build flags;
heap, stack, pool, GP14/BOOTSEL and RAM renderer checks; and UF2 block numbering,
family, exact E10 workaround, ELF payload correspondence and flash reservation.
The image's linked payload ends at `0x1023c338`; its padded normal UF2 extent
ends at `0x1023c400`, below the current application boundary `0x103f0000`.
Reserved settings/progress journals remain outside it.

The producer used Ubuntu 24.04 image `20261012.334.1`, host GCC 13.3.0,
Python 3.12.11, Node 24.8.0, CMake 3.31.6 and Arm GCC 15.3.1. Exact SDK,
submodule, picotool, Harness, toolchain archive, resource and lockfile identities
are retained in the manifest and `audit/build-inputs.json`, together with actual
runner/tool versions. Reproducibility is established for these declared inputs
on this runner, without claiming identical output across arbitrary runner images.

## Downloaded identity and retrieval

Verified local directory: `build/verified-ci-39079993419-1/`. The normal image is
`deployment/WsprryPico-0.1.0-ci.39079993419.1-pico2_w.uf2` (4,688,384 bytes).

| Material | SHA-256 |
| --- | --- |
| Consumer UF2 | `e5380c0989a490531be1fb680421f31f8ecdfbab8b3871d36ca205d6eebba8c6` |
| `release-manifest.json` | `2f533817dadadede307b367c06e05aa6cc96f7ea3ea1f6aa805988f03910cc2c` |
| `SHA256SUMS` | `b509c53ca6bb7abb386a8374155d1cc25b6b1cc9a07c1af057b0a854b10f96fd` |
| Normal linked ELF | `f037018db0e50d9104737fc9de34a6219e42968e3345b42e59081a357852bfd4` |
| Normal linker map | `40f72e05f5d9e790bd4a8b78aa907bd0136545d0bd62917f513595d1e4dc900f` |

| Artifact | Immutable ID | Archive SHA-256 |
| --- | --- | --- |
| `WsprryPico-firmware-39079993419-1-consumer` | `12118527599` | `b689dac2d9fb47297f76f7ed834844dacc23227de2a8226213a253c8d46c942e` |
| `WsprryPico-audit-39079993419-1-consumer` | `12118328275` | `d1067b2234171443a92861ea0fd6ac159ed6e911360340d250252a0100fbbbcb` |

Both artifacts expire `2027-01-15T23:41:32Z`. Their post-upload IDs and archive
digests are in `verified-download.json`, outside the immutable archived manifest.
All five `SHA256SUMS` entries passed; notices and consolidated dependency license
materials are included. Archive digests and contained payload hashes are
different identities, and none is a signature.

With `gh` authenticated and the documented Python/Arm/pinned-picotool tools on
`PATH`, retrieve this exact run into a new directory from the repository root:

```sh
python scripts/ci/download.py --run 39079993419 --attempt 1 \
  --source af2698182484e858f504121a83a035452e1431a5 \
  --version 0.1.0-ci.39079993419.1 \
  --destination build/verified-ci-39079993419-1-new
```

To recheck the retained extraction without network or rebuilding:

```sh
python scripts/ci/bundle.py build/verified-ci-39079993419-1/deployment \
  --audit build/verified-ci-39079993419-1/audit \
  --source af2698182484e858f504121a83a035452e1431a5 \
  --version 0.1.0-ci.39079993419.1
```

The locally used picotool was built from the exact pinned commit
`6f6458d792b93685a11423b244a585eaa99eafcf`; its executable SHA-256 is
`c243c6afd7372ffb9d712914b3f9126d2b607af38f1435ba5c4be5c78ec96c2b`.
The receipt records its version and local path. Generated firmware, bulk logs,
SDK/dependency inputs and downloads remain ignored and untracked.

## Local preparation and review

The affected frequency, schema/browser, scheduler, policy, progress and
application-resource checks passed (8 CTest cases), as did the seven browser/
session cases whose first CI run lacked npm imports. Twelve packaging checks
passed with the required Python modules. The actual consumer UI passed on a
synthetic RAM-backed API in desktop and mobile Chrome, including empty initial
frequency, explicit save, disabled schedules, field label and no horizontal
overflow. These local results include the working checkout and are preparatory
evidence; clean committed Linux CI determines deployable bytes.

The separate UI finish reviewer requested consistent status after input
correction, discard and target adoption. The repair, one rebuild and matching
desktop/mobile recaptures were accepted. The detector returned no findings in
degraded regex mode; it is not a complete accessibility scan. Existing native
controls and design conventions are retained. VoiceOver testing remains outside
this task's accepted scope.

The separate CI reviewer requested frozen source-derived test expectations,
required generated overlays, run/attempt binding and actual linked picotool
program identity. Those checks are implemented. Local inspection tools are
trusted inputs; picotool must be v2.3.0 built from the recorded pin, and its
local path, hash and version are recorded by the downloader.

The final read-only reviewer independently refreshed remote run/job/artifact
identities, recomputed archive/member/manifest/payload hashes, reran the complete
bundle verifier against the downloaded bytes, inspected linked flags and
picotool identity, checked the runtime frequency contract/tests and UI captures,
and verified the exact notices/license materials. No actionable source, artifact
or completion-wording finding remains after the recorded repairs.

## Boundaries and handoff

No board was flashed or controlled and no RF was emitted. CI does not establish
physical boot, USB, RF, timing, power or receiver interoperability acceptance.
Item 2's completed 80 m decode retains its historical image and evidence.
Any later decode, installer or publication acceptance must use the exact
selected CI UF2 bytes and version, with their manifest and notices.

The workflow exports artifacts for 90 days. The maintained
[build and retrieval guide](software-build-ci.md) defines the canonical manifest,
archive verification and source-ordered discovery contract. Installer/public
download publication, tags, releases and Read the Docs remain separate work.

Concurrent NTP source, tests and documentation are preserved outside these
scoped commits. No other repository is modified by this task.
