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
The directory contained 4,715,740 bytes. There are 146 original files retained
under engineering; the seven generated `docs/bluefy` outputs, the empty obsolete
`.nojekyll` Pages marker and this completed task's execution prompt are retired.
The prompt's required evidence is consolidated here and its backlog link repaired.
Original protocols,
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
readbacks pass. Fresh Linux verification now supersedes that fixture limit:
[run 39322329643](https://github.com/WsprryPi/WsprryPico/actions/runs/39322329643)
at exact source `59fd5f4f11e1e07c1c707e35d99352d52aeb9397` passed all 160
registered tests, with zero failures, skips or historical-evidence exclusions.
WTP, browser npm, packaging failures, consumer UI, inhibited regression and
compatibility build checks passed; reproducibility was identical. The normal
consumer firmware bundle and linked-image audit artifacts uploaded successfully.
The workflow's download-index publication job also completed successfully.
These are software/build results, not physical RF qualification. The ignored
`build/operator-documentation/fresh-linux-verify.log` has SHA-256
`0b253ac26b3c35fb8a7a6e32ca626b879517db358c04624499973a090c8f1e84`.
The later full [run 39324562626](https://github.com/WsprryPi/WsprryPico/actions/runs/39324562626)
also completed successfully at `c02e5d875dfdf2aa23e2220a95dd6ea7563adb4c`,
including the independent installer update. Subsequent changes affect only
documentation CSS and engineering closeout; their affected checks are the
strict Sphinx build, link validation and live rendered review.
Packaging checks pass all 36 tests when
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
screens. Final source/HTML link checking covers 93 maintained Markdown sources,
15 HTML pages and 1,158 local targets with zero errors. The current narrow screenshot is
`build/operator-documentation/manual-mobile-viewport.jpg` (390×844), captured
with an explicit CUA viewport clip. Earlier automatic/full-surface captures had
host-pane scaling/cropping artifacts and were discarded. The current capture and
DOM widths agree. Raw rendered screenshots remain ignored under
build/operator-documentation. No broad WCAG certification
or screen-reader acceptance is inferred.

## Publication state

The existing Community project is `wsprrypico`, with repository
`https://github.com/WsprryPi/WsprryPico`. The user authenticated in the internal
browser. An old `latest` build attempt is not treated as successful publication.
Its original RTD branch override was unset, with GitHub default branch `main`.
This task configured the accepted devel source deliberately; GitHub's default
branch, main, tags and releases are outside this task.

GitHub Pages initially used legacy publication from `devel:/docs`, at the old
project URL including `/bluefy/`. The seven generated outputs are removed;
GitHub Pages was deleted through the repository Pages API, followed by a 404
readback. A push-only signed webhook (GitHub ID 700551712, RTD integration
334708) now delivers to the Pico project; its ping returned 200 OK. No GitHub
App permission/ownership expansion was used. The temporary private secret file
was removed; no credential is in Git.

The first reviewed source publication is
`59fd5f4f11e1e07c1c707e35d99352d52aeb9397`, non-force pushed with independently
matching live origin/devel. [RTD build 35253186](https://app.readthedocs.org/projects/wsprrypico/builds/35253186/)
finished successfully for that exact commit and version devel. Its raw log
confirms Ubuntu 24.04, Python 3.12.13, pinned dependencies, warnings-as-errors
and 13 source pages. Both RTD default branch and default version are deliberately
`devel`. GitHub default branch remains `main`; no release/stable claim is made.

The public [operator manual](https://wsprrypico.readthedocs.io/en/devel/) serves
the expected home/task navigation and custom chrome color rgb(64,94,122).
Both live operator images are complete at native 1280×720 with correct alt text
and full-size links. The companion Pico setup deep link and its section anchor
resolve in the browser. Live BOOTSEL search returns four operator pages. The main/devel
CI indexes and raw bootstrap download returned HTTP 200. CLI requests to RTD's
public CDN received its bot filter; the authenticated internal browser verified
the actual HTTPS pages instead of treating those responses as missing pages.
The deployed RTD version selector initially inherited 30%-opacity white text;
the final CSS explicitly gives its selector and option list readable palette
colors. The dynamically inserted native selector also receives the accessible
name “Documentation version”; its bounded observer disconnects after insertion.
These issues were discovered only after RTD added its live controls. The first
contrast rule in `c02e5d8` was weaker than the theme's full selector; live computed
style exposed the failed override. The corrected rule matches theme specificity
for normal, focus, hover and active states, including the native option list.

The push-only integration also automatically built the independently committed
installer update `e5dc075a9383fae6d8225b2e31af34e4654b5da6` successfully in
[devel build 35253314](https://app.readthedocs.org/projects/wsprrypico/builds/35253314/).

The final operator content and contrast correction are commit
`48505934aeb0c04e6d42b406341c64c163e47582`, successfully served by automatic
[devel build 35254247](https://app.readthedocs.org/projects/wsprrypico/builds/35254247/).
The public browser confirmed selector text rgb(236,241,246), option text
rgb(36,55,70) on white, and accessible name “Documentation version”. The
390-pixel viewport and document width match. The deployed menu opens with
aria-expanded=true; Escape closes it, changes the state to false and returns
focus to the menu button. Final desktop and narrow captures are saved as
`build/operator-documentation/published-manual.jpg` and
`build/operator-documentation/manual-mobile-viewport.jpg`. Both were visually
reviewed at their native 1280×720 and 390×844 sizes. RTD Community advertising
and version controls are present as expected. The closeout-only follow-up
changes engineering evidence/backlog and retires the completed prompt; the
operator content remains the reviewed 4850593 content.

## External references

- [RTD v2 configuration](https://docs.readthedocs.com/platform/stable/config-file/v2.html)
- [Community publication tutorial](https://docs.readthedocs.com/platform/stable/tutorial/index.html)
- [RTD versions](https://docs.readthedocs.com/platform/stable/versions.html)


## Concurrent work boundary

Unrelated installer work appeared after this task's clean entry. The source
commit excludes `.github/workflows/usb-installer.yml`, `scripts/install_usb.sh`,
`scripts/usb_installer.py`, `tests/usb_installer_tests.py`,
`tests/installer_release_tests.py`, `tests/usb_tool_download_tests.py` and
`engineering/development/standalone-tool-downloads.md`. Later edits to `docs/install.md` and
`engineering/development/usb-installer.md` also belong to that task. That work
was independently committed as `e5dc075a9383fae6d8225b2e31af34e4654b5da6`
while this documentation closeout remained active. This task preserves that
commit and its installation guidance. The initial published manual describes
its original committed installer source; the later download features belong
to e5dc075 and are not relabelled as original 59fd5f4 behavior.


## Independent review disposition

The reviewer rechecked all repaired operator findings, migration rows, image
hashes, the corrected 390×844 screenshot and successful RTD raw log. No actionable
source/deployment finding remained at that review. The reviewer independently
confirmed source/remote and CI identity, but its browser and independent RTD web
fetch were unavailable. Live navigation/search/assets/keyboard observations
therefore rely on the primary browser evidence, with source and stored images
reviewed independently. The reviewer also checked the corrected selector
specificity and fresh Linux log without finding an actionable issue. Final
computed-style and mobile behavior checks above close its remaining live gate.
Item 9 is complete; item 10 remains not started. No sibling repository was
modified and no hardware operation or physical RF acceptance occurred.
