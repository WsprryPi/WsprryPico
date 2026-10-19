# Operator documentation and Read the Docs publication

Execute only item 9 of the [Consolidated backlog](consolidated-backlog.md).
Create the final operator instructions and accurate screenshots, migrate the
current mixed documentation tree into an engineering source directory, build a
new operator-facing Sphinx site in /docs using WsprryPi-Docs as the configuration
and style reference, and publish it on Read the Docs Community. Record the
result and evidence closeout, perform independent adversarial review, repair
actionable findings and repeat affected checks/review, then commit and push the
scoped result.

This is an execution handoff, not a second backlog. Preparing, saving or
publishing this prompt does not authorize executing the migration now. Item 9
remains not started until execution is requested. The directory rename,
content migration, screenshots, publishing configuration and RTD publication
described below belong to that later execution.

## Entry and execution authority

Work in /Users/lbussy/GitHub/WsprryPico. Read AGENTS.md, README.md, CONTRACT.md,
engineering/architecture.md, engineering/development/README.md and the consolidated backlog
before implementation. Print the complete Finish now section in its existing
order, preserving the NTP Work grouping and using ✅ finished, ⏳ in flight and
▧ not started. Mark only item 9 ⏳ when execution begins. Preserve concurrent
status changes and completed work; this document is the sole current/future
work list.

Inspect the branch, full HEAD, upstream, live remote tip and staged, unstaged
and untracked work before editing. At preparation, devel and live origin/devel
were 14698ca1dba32914959530a3b5a0cf41f74caf8f. A concurrent unstaged item 2 status
change was subsequently present. These observations are snapshots, not reset
targets. Refresh the source and work state when executing.

Execution authorizes Pico documentation migration, necessary path repairs,
docs build dependencies in a project-local virtual environment, screenshots,
minimal Pico-only site/deployment configuration, Read the Docs Community
publication and scoped commits/non-force pushes to devel. Do not initialize,
reset, stash or discard work. Other repositories are read-only references.
Do not run the separate repository/work-harness cleanup prompt, remove
engineering evidence, change firmware behavior, merge main, create a release
or tag, implement another backlog item or operate RF equipment for this task.

The user explicitly permits removing the existing GitHub Pages/Bluefy
publication for this migration. Preserving its public URL or creating a
replacement Bluefy deployment is not an acceptance requirement. Retiring that
publication does not authorize deleting the firmware's provisioning features,
canonical web application source or engineering records.

## Establish the sources and migration boundary

Inventory the current /docs before moving anything. At preparation it held
864 tracked files, including development records, architecture, protocols,
schemas/conformance vectors, licenses, mixed operator instructions, screenshots
and a generated Bluefy web client. Recount at execution and inspect ignored
and untracked contents, symlinks and local virtual environments separately.
Move tracked documentation with Git-aware operations; do not recursively move
or delete local captures, build products or another task's work by assumption.

Rename the existing documentation directory to /engineering. That destination
was absent at preparation; if it now exists, inspect and reconcile its contents
without overwriting anything. Keep the old material available there as a source
while developing the new /docs. The engineering directory remains the home for
architecture, protocols, developer commands, contracts, test fixtures, source
provenance, reviews, result records and the canonical backlog/saved handoffs.
Do not create an archive copy, a second work list or a docs-to-engineering
compatibility symlink that prevents /docs becoming the operator site.

Read current accepted behavior from the implementation and applicable records,
including [standalone configuration](standalone.md),
[consumer LAN access](consumer-lan-access.md),
[USB local configuration](usb-local-configuration.md),
[USB management/time](../protocol/USB-Management.md),
[hostname behavior](hostname.md),
[page organization](browser-pages.md),
[main-page identity](device-presentation.md),
[support policy](clock-support.md),
[GPIO drive](gpio-drive.md),
[normal firmware selection](firmware-foundation.md),
[firmware foundation](firmware-foundation.md) and the current browser API and
protocol documents. These paths describe the preparation layout; update live
links to their engineering locations when the directory moves.

Use the [CI image contract](software-build-ci.md),
[USB installer guide](usb-installer.md),
[browser interface contracts](browser-pages.md) and
[testing prerelease handoff](phase15-17-execution-prompt.md) to understand
boundaries and consumers, not as proof those tasks have executed. Use their
actual accepted outputs if available. Document what is available now; do not
invent an installer, download URL, CI image, screenshot or acceptance result
to make the guide appear complete, and do not execute those items here.

Create a compact migration coverage record alongside this task's engineering
closeout. For each source page or meaningful mixed section, identify its new
operator destination, retained engineering destination, split disposition or
justified removal. Record assets and link/anchor mappings as needed. This is
evidence of this migration, not another pending-work tracker.

## Use WsprryPi-Docs as the reference

Read /Users/lbussy/GitHub/WsprryPi-Docs/AGENTS.md and inspect its current state.
At preparation its devel HEAD was
5f539fbcac1e02b0edb58c017479105647975b27, with uncommitted transmitter setup
text and hostname/progress screenshots. Treat those edits as drafts, record
which committed or working-tree material informed the design, and preserve
every byte. Do not install dependencies, build, stage, commit or edit there.

Inspect its root readthedocs.yaml, docs/conf.py, docs/requirements.txt,
docs/index.md, task-based toctrees, _static/css/custom.css,
_static/js/accessibility.js and relevant image-delivery helpers. Its approach
uses Sphinx, MyST Markdown and sphinx_rtd_theme, a local docs virtual environment,
responsive operator navigation, branded typography/spacing and accessible
mobile navigation. Adapt these methods to WsprryPico rather than copying its
project wholesale.

Retain useful theme behavior such as visible task navigation, search,
previous/next links, mobile controls and keyboard support. The reference's
collapse_navigation=False, navigation_depth=3, includehidden=True and
titles_only=True are useful starting points; verify the resulting Pico site.
Use compatible typography, spacing, colors and screenshot treatment with
appropriate attribution. Do not import WsprryPi-specific feature flags,
developer autodoc, old project metadata, application CSS wholesale, or
Apache/PHP/Linux hardware instructions into the Pico manual.

## Build an operator manual

Organize the new /docs around tasks an operator needs to complete, with a clear
starting page and a short route from first use to a working configuration.
Choose a simple hierarchy such as start, install/update, connect, configure,
operate, maintain/troubleshoot and reference. Avoid engineering phase numbers,
execution prompts, acceptance chronology, source manifests and developer API
catalogs in the published navigation or search corpus.

Cover the following supported tasks, using the actual current UI labels and
accepted product behavior:

- Identify the Pico 2 W target, required connections and supported operation;
  distinguish standalone use from use as a WsprryPi transmitter member.
- Obtain the appropriate normal RF-capable firmware, verify its source/version,
  manifest and checksum where delivered, install/update using a method actually
  available, preserve settings and confirm the running identity. Distinguish
  normal firmware from explicitly inhibited diagnostics. Do not offer an old
  compatibility or bench image as the normal download.
- Complete first connection, temporary setup Wi-Fi, station Wi-Fi and local
  browser access; explain the actual credentials, bounded AP window, button,
  fallback and USB recovery paths. Cover supported desktop/mobile routes,
  hostname/IP changes, reconnection and browser limitations without linking to
  a retired Bluefy deployment.
- Enter station identity, location and power, choose the supported band/mode,
  frequency and message, save configuration and understand readback. Distinguish
  a saved draft, complete configuration, active hardware and readiness to
  transmit. Explain restart-required settings and current GPIO-drive behavior.
- Configure schedules, start/stop operation, read progress/status and recover
  from aborted jobs, connection loss or restarts. Explain ownership when used
  with WsprryPi and the limits of one member's accepted interoperability.
- Understand time readiness, UTC/slot timing, supported manual PPM and other
  calibration controls as actually implemented. Do not conflate UTC discipline
  with RF calibration. Describe new NTP or amplifier controls only if their
  corresponding accepted implementation exists when this task executes.
- Interpret current band/mode support, qualification limits and experimental
  opt-ins without converting a narrow conducted result into broad RF claims.
  Include the actual WSPR Type 2/3 receiver/context limitations where relevant.
- Diagnose common access, configuration, timing and output-readiness failures;
  obtain useful support information without exposing secrets; recover or reset
  only with explicit explanation of what settings are retained or removed.

Write direct instructions with prerequisites, action, expected result and a
recovery step where failure is plausible. Keep internal schemas, lock ownership
details, SDK commands and test harnesses out of normal operator flows. Link to
engineering sources only where a useful technical reference warrants it.
Keep root README/CONTRACT orientation and normative contracts appropriate to
their purpose; point operator how-to content at the new site instead of
maintaining duplicate current manuals there.

The backlog remains authoritative for future scope: basic amplifier enable is
Finish now; optional settling/lead/tail timing and automatic NTP-server
discovery/preference remain future work. Do not implement or advertise those
future features during documentation work.

## Screenshots and rendered review

Plan screenshots around decisions or states that text alone does not explain.
Capture the final accepted interface relevant to this documentation version,
with representative safe settings, readable labels, useful context, concise
captions and meaningful alternative text. Use consistent crops and display
sizes, preserve aspect ratios and optimize asset size without blurring text.
Replace materially inaccurate images rather than decorating obsolete screens.

Record source commit, served UI/firmware identity, browser/viewport, scenario
and image hashes in the engineering evidence. If WsprryPi screens are needed,
verify the compatible companion version and use them strictly as a read-only
reference. Do not claim a staged, simulated or fixture-rendered screenshot is
proof of an actual board workflow. Never fabricate hardware results or edit
an image to imply an unavailable feature. Capture non-sensitive sample values;
keep credentials, private URLs, serials and unsanitized captures out of Git.

Prefer existing accepted evidence or non-transmitting browser inspection.
This task does not require a new RF campaign, firmware load, reset or changed
radio settings just to obtain pictures. Follow AGENTS.md and any current setup
authorization for necessary device interaction; restore authorized changes and
record them. If an essential screen cannot be obtained honestly, identify that
specific gap instead of substituting a misleading image.

Use the available Impeccable skill for the actual rendered site review,
announcing its use when applied. Review representative desktop and narrow
mobile pages, navigation/search, keyboard focus and mobile menu controls,
headings, contrast, image readability, long labels, code wrapping and overflow.
Retain RTD theme functionality while adapting the reference style.

## Migrate content and repair live paths

After each operator destination is complete and verified, remove its superseded
current operator instructions and redundant operator-only assets from
/engineering. Split mixed documents: retain the engineering discussion and
provide a concise pointer to the canonical operator instructions. Do not leave
a duplicate operator manual in the renamed directory. Preserve engineering
records, protocols, schemas, upstream licenses and source-bound historical
evidence; an original recorded command or screenshot inside evidence is not a
second maintained operator guide. Do not rewrite historical outcomes or hashes.

Update active references throughout the Pico repository, including AGENTS.md,
README.md, CONTRACT.md, development entry points, saved execution prompts,
CMake inputs, scripts, tests and any CI jobs. The sole backlog and this prompt
move to engineering/development; update their live entry links. Historical
source-coordinate strings may intentionally continue to name docs paths at
their original commit. Distinguish those from paths a current tool opens, and
record relocation mappings instead of falsifying provenance.

This rename affects executable consumers, not only Markdown links. At
preparation CMake and network host checks read docs/protocol vectors; Python
and JavaScript tests and helpers load those files; radio-vectors.mjs writes
there; third-party notices link docs/licenses; provisioning checks inspect
docs/bluefy. Inventory current consumers with rg and repair them explicitly.
Use path-only changes or equivalent minimal test/build adjustments. Do not
disable a check, change protocol semantics or regenerate frozen evidence merely
to make the new directory layout pass.

At preparation GitHub Pages used legacy publication from devel:/docs at
https://wsprrypi.github.io/WsprryPico/, including /bluefy/. The user permits
retiring this publication. Remove stale operator links to it and retire its
unused generated output/configuration as appropriate; preserve canonical
src/provisioning/web source and relevant release/provisioning test coverage.
If a check currently relies on the retired deployment directory, preserve its
source validation using an ignored temporary generated output or another
minimal appropriate arrangement. Do not retain a public Bluefy mirror or add a
replacement Pages workflow solely to preserve the old URL. Record the actual
Pages disposition and any narrowly necessary Pico-only settings change.

## Sphinx build and Read the Docs Community

Create a Pico-specific docs/conf.py, docs/index.md, dependency requirements,
static assets and root RTD configuration. Use the reference's Sphinx/MyST/RTD
theme approach with compatible pinned documentation dependencies and a local
Pico virtual environment. Keep virtual environments, generated HTML, caches
and raw captures ignored. Do not reuse or modify the sibling's environment or
install a firmware SDK/toolchain as a documentation dependency.

Check the current official [RTD configuration reference](https://docs.readthedocs.com/platform/stable/config-file/v2.html).
Use version 2 configuration, an actually supported OS/Python combination,
docs/conf.py and docs/requirements.txt, with warnings treated as failures.
Do not blindly copy the reference's older platform pins or enable every output
format; validate every format you choose to deliver. Keep engineering files,
local environments and private evidence outside the public source corpus.

Record the exact environment and reproduction commands. Using the selected
virtual environment's Python, validate a clean strict HTML build equivalent to
`python -m sphinx -n -W --keep-going -b html docs docs/_build/html` and inspect
the rendered output. Fix missing references, anchors, assets and meaningful
warnings rather than adding broad suppressions. Check internal links, actual
download destinations and selected external links. Run affected deterministic
checks from the current development README for relocated vectors, generated
web assets, provisioning, schema and build inputs; report the exact commands
and results. Use the established toolchain/CI when a build check requires it.

Follow the official [Community publication tutorial](https://docs.readthedocs.com/platform/stable/tutorial/index.html)
and [version documentation](https://docs.readthedocs.com/platform/stable/versions.html).
Reuse an existing suitable WsprryPico Community project if present, otherwise
create/import the public Pico repository using the authorized account. Verify
the actual project slug, source repository and selected branch. RTD's initial
latest version follows the repository's default branch, which was main at
preparation; configure the RTD project/version deliberately for the accepted
devel source. Do not change the GitHub default branch, merge main or call a
development build a stable release merely to obtain a working site.

Prepare and review the complete local result before publishing source changes.
Commit/push the reviewed source when needed to trigger RTD, then inspect the
actual build logs and public HTTPS pages. Verify the built commit, version,
home page, navigation, search, screenshots, CSS/JS, representative deep links
and download links. A local HTML build or configured webhook alone does not
establish publication. Record the real public URL and successful RTD build URL
and identity; do not guess a free slug or claim publication from an HTTP landing
page that serves the wrong branch.

Use existing authenticated tools where available. If account login, email
verification or an external authorization step actually requires the user,
complete all independent local work first and identify the precise remaining
step. Do not buy a plan, change organization ownership or broaden account
permissions as an incidental workaround. Leave item 9 in flight if publication
or an essential documentation/screenshot requirement remains unresolved.

## Evidence closeout and adversarial review

Save a concise result record under engineering/development with the migration
coverage/path mapping, source/image identities, dependency versions, exact
checks and results, screenshot provenance, Pages disposition, RTD configuration
and live build/publication evidence. Keep large raw logs/captures outside Git
and record stable locations and hashes where needed. Separate source/link
checks, rendered UI evidence, physical acceptance and publication results.

Perform an independent read-only adversarial review of the complete candidate;
use a separate reviewer agent if available. Explicitly authorize that reviewer
to inspect this slice without modifying files. Provide the original request,
diff, rendered site, migration map, checks and existing limits. Review before
publication, then include the actual live deployment in final review.

Require the reviewer to challenge operator completeness and exact supported
behavior; stale UI/images; secret leakage; developer material in public
navigation/search; duplicated migrated instructions; lost engineering content,
license notices or provenance; broken live path consumers and evidence hashes;
misleading firmware/download identity; accessibility/mobile problems; abandoned
links to the retired publication; unintended sibling edits; wrong RTD branch
or source SHA; and claims of publication unsupported by a successful live build.

Repair every actionable in-scope finding, repeat affected build/check/rendered
or live-site verification, and return the revised candidate for review until
no actionable finding remains. Do not implement another backlog item to hide
a documentation gap; report its concrete effect on this task. Keep the review
findings and dispositions in this task's closeout without creating another
current/future work list.

## Commit, push and report

Mark only item 9 ✅ when the operator content and screenshots are accurate,
migration coverage is closed, duplicated current operator text is removed,
engineering material is retained with working live paths, affected checks pass,
adversarial findings are resolved and the verified RTD site is publicly served
from the intended source. Otherwise keep it ⏳ and record the specific gap.

Inspect staged names, hunks and generated files before each commit. Commit
only this slice, excluding unrelated changes even in a shared backlog file.
Use non-force pushes to the intended branch. If remote work advances, inspect
and integrate it without overwriting another task or rewriting published history.
If closeout changes require a final follow-up commit, verify the resulting docs
deployment as appropriate and state both the content/build and final commit
identities so publication provenance remains clear.

Independently verify the final local HEAD against the live remote tip and
report the actual remaining staged/unstaged/untracked work. Return the new
operator-site URL and build evidence, renamed engineering location, material
migration decisions/removals, checks, review result, limitations and commits.
Reprint the complete canonical Finish now punchlist with current statuses,
saved-prompt links, original order and NTP Work grouping.
