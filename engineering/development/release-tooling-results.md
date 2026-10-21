# Firmware release tooling

The release pipeline supports semantic beta/final tags across build identity,
manifest verification, publication, download, preserving USB updates and
same-board recovery. The [execution prompt](release-tooling-prompt.md) defines
the bounded implementation and review scope; [current commands](software-build-ci.md)
describe operation.

Both workflows require explicit manual publication. Pushes, PRs and tag checks
have no publication effects. Existing main/devel CI selections and the
historical manual testing release retain their independent contracts.

## Software checks

The focused local checks passed on 2026-10-21:

| Check | Result |
| --- | --- |
| `docs/.venv/bin/python tests/ci_bundle_tests.py` | 51 tests passed |
| `python3 tests/usb_installer_tests.py` | 88 tests passed |
| `python3 tests/installer_release_tests.py` | 6 tests passed |
| `python3 tests/usb_tool_download_tests.py` | 35 tests passed |
| `python3 scripts/validate_wtp_contract.py` | 23 schema, 7 raw JSON, 1 framing and 8 transition cases passed |
| Strict Sphinx build | Passed with warnings treated as errors |
| `scripts/check_documentation.py` | 96 Markdown sources, 15 HTML pages, 1,224 local targets; zero errors |
| `tests/test_image_delivery.py` | Passed |
| `git diff --check` | Passed |

The release tests exercise actual manifest creation and both schema interpreters,
tagged push/manual identities, current-job publication collection, complete
mocked draft/publication/download round trips, retained archives after Actions
expiry, explicit stable selection, beta-to-final preserving upgrades and
interrupted-update recovery. They also exercise malformed versions, channel/ref/
tag/source swaps, skipped and failed publication, upload mutation, latest-stable
restrictions and publication refusal before any network mutation. The existing
bootstrap and tool-distribution checks remain included.

The current WsprryPi adapter was also checked read-only against the generated
installer manifest. It accepts installer 0.2.0 under contract 1 with the same
three distributed files. No companion source was changed.

Full portable/SDK checks, normal/inhibited/compatibility cross-builds and the
two-build UF2 comparison run in the Linux push workflow. Its exact commit/run
and terminal result are part of the accompanying completion report. No local
macOS C++ compiler was invoked.

## Adversarial self-review

The first assessment examined tag authority, all version consumers, publication
effects, archived provenance, schema compatibility and update recovery. It
identified and closed these issues:

- A tag could change during upload before the draft became public. The publisher
  now rechecks the tag and release metadata after asset audit and before public
  transition. The regression changes the tag during upload and requires the
  release to remain a draft.
- Additional CI-only checks in installed-image lookup, upgrade admission and
  same-board recovery would reject an installed beta or final version. They
  now share the semantic version policy; preserving upgrade/recovery regressions
  include beta-to-final updates.
- Valid build metadata required `+` support in archive paths and checksum
  filenames. The full retained-archive and installer paths now exercise it.
- An old substring check rejected otherwise valid prerelease identifiers
  containing `-testing.`. The shared classifier now determines the reserved
  historical testing series precisely.

The second assessment rechecked the repaired paths, both workflow permissions
and default-off publication conditions, explicit latest-stable selection,
immutable tags/assets, historical CI/testing behavior, preview isolation,
storage guards and deployed installer payload compatibility. No additional
actionable finding remained. Affected checks were rerun successfully.

## Limits and release state

These are deterministic software and mocked service/USB results. No actual beta
or final tag/release was created, no assets were uploaded, no bookmark was
advanced, no device was flashed and no RF or new physical qualification was
performed. Live tag-triggered publication and physical update acceptance remain
separate future operations. Existing historical physical evidence retains its
original source, board and setup scope.
