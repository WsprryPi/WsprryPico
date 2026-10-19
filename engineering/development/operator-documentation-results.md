# Operator documentation migration and publication

The operator manual is under `docs/`; engineering sources, contracts, schemas,
licenses, result records and the sole backlog are under `engineering/`.
The initial source was `devel` `0497a9b1ef1efc920c282202d4a0a5c61cae7fc7`, clean
and equal to the live remote tip. This task changes documentation, path
consumers and generated-publication validation, not firmware behavior.

## Coverage and preservation

The [155-row migration map](operator-documentation-migration.csv) records every
original tracked documentation file, its original SHA-256, disposition, retained
engineering destination and operator destination for meaningful mixed sections.
There were no docs symlinks, untracked files, ignored captures or environments.
The directory contained 4,715,740 bytes. All 148 nongenerated files are retained;
the seven generated `docs/bluefy` outputs are retired. Original protocols,
evidence JSON, figures and upstream license files remain byte-identical (66 files).

Current how-to content is consolidated into 13 Sphinx/MyST operator pages.
Mixed consumer access and installer records retain engineering semantics and
point to the manual. Root README provides capability orientation and manual
entry points. CMake, test/helper schema/vector consumers, source references,
notices and active saved handoffs use engineering paths. Frozen historical
source-coordinate strings in evidence continue to identify their original
`docs/` location at the recorded source; their hashes are not rewritten.
There is no compatibility symlink, archive copy or second backlog.

The canonical provisioning web source remains in `src/provisioning/web`.
Bluefy integrity/release checks generate ignored `build/bluefy-validation` or
a temporary output instead of reading the retired Pages deployment directory.
Protocol checks remain enabled and unchanged in meaning.

## Style and screenshot provenance

The read-only reference was clean WsprryPi-Docs
`c0215b6d980ae809dfacdeb9d2ef557dfc71445e`. Only its committed Sphinx/MyST/RTD
configuration, task navigation, chrome colors, spacing and keyboard methods
informed this site. Its files/environment were not modified or built.
The adapted MIT notice is included in the public credits page.

[Screenshot identities](operator-documentation-screenshots.json) bind both
1280×720 JPEGs to current production-generated consumer frontend source
`0497a9b1ef1efc920c282202d4a0a5c61cae7fc7`, the retained synthetic backend's
SHA-256, browser, scenario and image hashes. The frontend is assembled with
`scripts/generate_web_assets.py` and its current checked asset manifest.
The backend is a previously compiled RAM fixture: current source equivalence
is unverified. No board/firmware, physical network or RF acceptance is claimed.
Captions identify previews, visible values are synthetic, password fields are
empty and diagnostics containing full identity are closed. No image was edited
to imply a feature. Raw captures/preview recipe are ignored under
`build/operator-documentation/`.

The old six-scenario preview entry point failed against retained older drivers
at its profile boundary. A one-surface loopback preview uses the current
production document and retained synthetic service. It does not assert physical
origin/session qualification. This task performs no firmware load, reset,
settings change or RF operation.

## Reproduction and deterministic checks

Documentation uses Sphinx 8.2.3, MyST 4.0.1 and sphinx_rtd_theme 3.0.2 in
`docs/.venv`; the local interpreter is Python 3.15.0. RTD uses Ubuntu 24.04 /
Python 3.12 per the current official v2 configuration reference. Only HTML is
requested. Strictness is enabled locally and in RTD.

```sh
python3 -m venv docs/.venv
docs/.venv/bin/python -m pip install -r docs/requirements.txt
docs/.venv/bin/python -m sphinx -E -a -n -W --keep-going -b html docs docs/_build/html
docs/.venv/bin/python scripts/check_documentation.py
python3 scripts/validate_wtp_contract.py
python3 tests/bluefy_release_tests.py
python3 tests/provisioning_contract_tests.py
node tests/provisioning_web_tests.js
python3 tests/rf_feasibility_tests.py
python3 tests/network_transport_contract_tests.py
python3 tests/raspberry_pi_ble_client_tests.py
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
```

The initial schema-test attempt omitted required compiled-driver arguments and
had no jsonschema dependency. It is incomplete evidence and is superseded by
correct invocations recorded in ignored `build/operator-documentation/schema-checks.json`.
Those six schema checks pass using existing
`build/microchrony-retirement-20261019/host` service binaries, each SHA-256
recorded there, and jsonschema 4.25.1 (the repository-pinned test dependency).
The schema tests receive application_resource_tests, gpio_drive_tests,
amplifier_enable_tests, standalone_frequency_tests, wspr_resource_tests and
config_update_tests respectively. Retained-host checks establish relocated
source-path/service compatibility; no local C++ compilation was attempted.
The retained network fixture fails the current progress-session AP admission
scenario before collecting schema samples; its source-equivalence limit is
recorded rather than presented as a pass. The current pure schemas and service
readbacks pass. Fresh Linux CI remains separate evidence and must verify the
new source/layout before completion. Packaging checks pass all 36 tests when
run as `docs/.venv/bin/python tests/ci_bundle_tests.py`; the initial system-Python
attempt lacked YAML/jsonschema dependencies and is not a packaging failure.
An attempted nonexistent `tests/ci_manifest_tests.py` invocation performed no
check; the actual maintained packaging test above supersedes it.

## Independent review and rendered checks

An independent read-only reviewer checked operator completeness, accepted source,
path consumers, preservation, screenshots and the public source corpus.
Repairs include explicit GP2/pin-4 and GND/pin-3 wiring, schedule syntax and
save/apply actions, actual UTC/message/job-file control labels, STOP restart
recovery, explicit automatic-schedule authority, correct recovery-page choices,
separated operator/engineering prose, restored developer build/test commands,
and the occupied-login protocol's migration mapping.

Impeccable's detector found no mechanical findings in the custom CSS/JS.
The first desktop/narrow rendered pass identified an empty mobile menu icon;
the corrected button uses the theme's icon and retains delegated menu behavior,
ARIA state, Escape/focus return and skip-to-content support. The corrected menu opens/closes, aria-expanded follows state, Escape closes it
and returns focus. At a measured 390 CSS pixels, content width equals viewport
width. Search for BOOTSEL returns four operator pages and no engineering records.
Desktop typography, labels, previous/next controls and image treatment were
visually inspected. Both images link to their full-size versions for narrow
screens. Source/HTML link checking covers 94 maintained Markdown sources,
15 HTML pages and 1,171 local targets with zero errors. Raw rendered screenshots
remain ignored under build/operator-documentation. No broad WCAG certification
or screen-reader acceptance is inferred.

## Publication state

The existing Community project is `wsprrypico`, with repository
`https://github.com/WsprryPi/WsprryPico`. The user authenticated in the internal
browser. An old `latest` build attempt is not treated as successful publication.
Its original RTD branch override was unset, with GitHub default branch `main`.
This task will configure the accepted devel source deliberately; GitHub's default
branch, main, tags and releases are outside this task.

GitHub Pages initially used legacy publication from `devel:/docs`, at the old
project URL including `/bluefy/`. The seven generated outputs are removed;
actual Pages setting retirement and live RTD build verification are pending.
Item 9 remains in flight until publication, affected checks and final review pass.

## External references

- [RTD v2 configuration](https://docs.readthedocs.com/platform/stable/config-file/v2.html)
- [Community publication tutorial](https://docs.readthedocs.com/platform/stable/tutorial/index.html)
- [RTD versions](https://docs.readthedocs.com/platform/stable/versions.html)
