# LPF/band-selector usefulness assessment

## Decision and scope

Item 4 is **deferred, not implemented or accepted**. For the present fixed-frequency standalone workflow, optional automatic selection adds hardware, configuration and support work without removing a recurring band-change operation. A small direct-GPIO selector remains a credible, inexpensive enhancement for unattended jobs that use different filters. That benefit does not yet justify committing the coordinated implementation against an unspecified installation. This is a conditional product decision, not a finding that automatic filtering is generally uneconomic.

The assessment uses the repository state inspected on 2026-10-28, America/Chicago. No selector inventory, selected filter bank, required band-change cadence or recurring operator intervention has been established for this task. The operator's deployed workload remains unknown; the documented standalone workflow is the comparison baseline. Absence of an inventory is not evidence that the operator owns no filters. Reassess the decision when a concrete use case is identified; do not treat missing physical hardware alone as a reason to stop justified software implementation.

The [saved execution prompt](lpf-band-selector-execution-prompt.md) remains the implementation and acceptance authority for this unfinished feature. Existing amplifier timing, pin assignments, WTP/1, capabilities and operator workflows are unchanged. Automatic filter selection remains unavailable.

## Inspected baseline

| Repository | Inspected `devel` revision | Initial working state |
| --- | --- | --- |
| WsprryPico | `33635a442dfad74e54c22cb3fdffdc72808156ab` | Clean before the assessment/reference edits. |
| WsprryPi | `e8d10e11c155cfbb4f441e39ae2e42f5f7e08915` | Clean; inspected, unchanged. |
| WsprryPi-Docs | `9dc709e4c46d8c6834a2c4471783854f0bb36819` | Clean; inspected, unchanged. |

All three checkouts report `devel` tracking `origin/devel`. None reports a Git submodule; the inspected Pi first-party UI is ordinary tracked content, so no separate UI submodule publication is needed at this baseline. These are inspected source revisions, not an LPF-tested source pair or fresh device identities.

The Pico [pin planner](../../src/hardware/pins.cpp) validates exclusive resources, but `operational()` requires an empty LPF allocation and choices advertise `lpf:false`. Its [configuration parser](../../src/standalone/config.cpp) rejects unsupported plans, and its current [Radio pins editor](../../src/network/web/index.html) explains that switching is unavailable. A nonempty `lpf_gps` candidate is not executable selector support.

The [standalone configuration](../../src/standalone/config.hpp) has one WSPR dial shared by its schedule entries; Type 2/3 frames use that same dial. Individual message jobs have their own frequencies. A fixed external filter appropriate to all intended RF frequencies can therefore serve a single-band installation without automatic switching. This is a use-case comparison, not a claim that one filter covers arbitrary message frequencies. [Current operation](../../docs/configure.md#frequency-and-schedules) does not provide standalone WSPR band rotation.

Pi inspection covered `src/band_gpio_selector.cpp`, frequency selection in `src/scheduling.cpp`, management in `src/wtp_integration/configuration.cpp` and `usb_management.cpp`, the first-party selected-member controls, and `.github/workflows/debian-non-hardware.yml`. Existing Pi Band GPIO and `@GPIO[H|L]` behavior already provide Pi-side selection. They do not program a Pico selector, establish LPF coverage or substitute for member-local switching and recovery. Remote Pico operation can benefit from a local selector even when the controller is a Pi.

## Hardware and incremental cost

The following are hypothetical purchases, not an inventory or an order. Primary supplier pages were checked on 2026-10-29 UTC. Prices are displayed US dollars and exclude shipping, tax, assembly, drivers, power distribution, connectors, wiring and enclosure.

| Example | Displayed parts cost | Interpretation |
| --- | --- | --- |
| One fixed [QRP Labs LPF kit](https://shop.qrp-labs.com/LPF) | $4.60 | A single filter example, subject to actual frequency, power and response suitability. |
| [QRP Labs ULPF relay-board kit](https://shop.qrp-labs.com/ULPF) | $16.00 | Filter modules are separate. |
| Board plus five filter kits | $16.00 + 5 × $4.60 = **$39.00** | Five populated board positions, before the excluded interface/system costs. |
| Switching added to the same five-filter manual installation | **$16.00 plus drivers and integration** | The filter modules themselves are common to both alternatives; counting them again would overstate the switching premium. |

The [revision-5 assembly manual](https://www.qrp-labs.com/images/ultimatelpf/assembly_ulpf2.pdf) describes five board positions. Its sixth filter requires the additional relay/filter position on a U3/U3S main board; a Pico plus this board is not a six-position assembly. The normal jumper arrangement keeps the highest-frequency filter in the RF path, including when another filter is selected. An all-relays-inactive command must not be described as a verified RF disconnect.

The supplier's [3.3 V driver guidance](https://www.qrp-labs.com/ultimatelpf/relaydriver) specifies 5 V, 28 mA coils and explains why a 3.3 V high level at the coil control can fail to release a relay. Pico GPIO must drive suitable logic-compatible drivers, not the coils. The shown transistor arrangement makes a logic-high command energize its relay. Actual driver polarity, external inactive bias, power sequencing and release/operate time need verification on the selected assembly. No driver BOM or delivered-system price is asserted here.

## Benefit, resources and support burden

| Operating case | Incremental benefit | Assessment |
| --- | --- | --- |
| One fixed frequency or a set entirely served by one suitable fixed filter | No recurring selection operation is removed. | Prefer fixed filtering. |
| Occasional attended changes needing different filters | Can avoid manual reconnection, but adds driver wiring and configuration. | Depends on actual intervention frequency and installation; no savings established here. |
| Unattended Pi-produced or remote jobs requiring different filters | Member-local selection can remove site visits/manual changes and reject jobs outside declared coverage. | Credible economic case; identify this workload before selecting the implementation. |

Automatic admission against declared coverage can also reduce configuration errors during attended frequency changes. That benefit is real even without unattended band rotation, but it still depends on correct declared coverage and wiring; GPIO readback does not identify the installed filter or measure its response. A sufficiently valuable error-prevention requirement is another reason to reassess this decision.

There are 26 eligible external GPIOs. Default RF GP2 and button GP14 leave 24; an optional amplifier leaves 23, and an external indicator leaves 22. Five distinct selector outputs would leave 17 with all those optional roles present. The onboard LED consumes no exposed GPIO. This arithmetic follows the [pin contract](../pin-assignment-contract.md); it does not assign pins or establish electrical suitability. An expander or general relay framework is not justified by this example.

Existing reusable pieces include exclusive allocation, restart/output-inhibit latching, atomic journals, authenticated revision-bound management and the member-local [amplifier launch/cleanup authority](amplifier-enable.md). They reduce development work but do not supply filter names, declared coverage, whole-job selection, break-before-make, separate settling, frozen accepted-job state or selector fault recovery. Extending the sink must preserve the independently configured amplifier lead and tail and the promised RF deadline.

Implementation also requires a separately versioned management model, exact historical compatibility, omission preservation, journal recovery, Pico and Pi selected-member editors, generated assets and both actual USB/network source-pair suites. Pi's band table cannot establish Pico filter coverage. The [shared application contract](../transmitter-application-contract.md#amplifier-and-filter-execution) already requires every RF-on frequency in the complete job to fit one selected filter. A bare GPIO toggle would not deliver that behavior.

No firmware target was changed or built for this assessment, so there is no measured LPF flash, RAM, stack or timing delta. The prior [amplifier timing record](amplifier-timing-validation.md#software-evidence) reports a 136/136 Linux host pass and linked firmware/resource audits; its later combined-diagnostics experiment also records constrained decode headroom. Those are historical baseline observations, not current LPF acceptance or proof of available capacity. A future implementation must measure bounded configuration/serialization and accepted-job storage rather than assume spare memory.

No current selector wiring, independently instrumented relay timing setup or measured filter response was verified. The prior [amplifier physical record](amplifier-timing-validation.md) does not qualify a filter bank. Hardware acquisition is not the sole deferral reason: the decisive missing benefit is an identified workload that actually requires automatic selection. If that workload is established before hardware arrives, independent software work can proceed while physical acceptance stays explicitly open.

No engineering-hour price, maintenance rate or avoided-visit value is available, so no monetary payback interval is claimed. Parts are inexpensive enough that they do not rule the feature out. For the documented fixed-frequency workflow, no recurring filter-changing operation is removed; the coordinated firmware, compatibility and recovery burden remains. For a remote multiband deployment or a concrete filter-error prevention requirement, that comparison can reverse. No quantitative negative return on investment has been established.

## Reassessment and acceptance

Reopen implementation when an intended job sequence needs different filters and automatic selection removes a concrete operating burden, or when declared-coverage admission addresses an identified configuration-error risk. Record the required RF ranges and cadence, the selected board/topology or bounded target interface, GPIO/driver/bias constraints and a physical acceptance plan. Ownership of hardware is not a prerequisite to all software work. Do not add band rotation, Si5351, filter construction or PCB work merely to manufacture a use case for this slice.

The likely smallest useful option remains a bounded set of named, exclusively owned direct-GPIO resources with explicit polarity, declared coverage and settling, disabled by default. Counts, range units, ambiguity handling, persistence representation and timing bounds remain proposals until justified against the chosen workload, resources and hardware. The existing 26-pin candidate-parser ceiling is not a selected operational filter count.

Both production-path integration suites and finite physical switching acceptance remain required for an implementation under the saved prompt. They were not run for this assessment because no executable, schema, descriptor, protocol or management behavior changed. No LPF tests, deployment, RF transmission, relay exercise or restoration took place; there is no new hardware or RF qualification. Current operator manuals remain accurate and require no behavior change for this decision. The saved prompt is retained because the feature remains unfinished.

## Adversarial review

Self-review identified and corrected the following assessment risks. This is not an independent review.

| Pass | Severity / finding | Correction and closure criterion |
| --- | --- | --- |
| 1 | Medium: advertised six-band operation could be mistaken for six standalone Pico filter positions. | Use five board positions and five filters in the cost example; explain the U3/U3S-only sixth position and revision-5 cascaded filter. Closed against the supplier manual. |
| 1 | Medium: absence of an inventory could be mislabeled as proof that no hardware exists, or physical availability could become the sole deferral gate. | State the unknown inventory and bound the decision to the unestablished automatic-selection workload; explicitly allow justified software work before hardware. Closed by the decision and reassessment conditions. |
| 1 | Medium: the whole automatic bank price could be compared with one manual filter for a multiband workload, overstating its premium. | Compare the same five filters on both sides; the switching premium is the board plus drivers/integration. Closed by the cost table. |
| 2 | Medium: existing Pi Band GPIO could be presented as remote Pico selection, or inactive GPIO as RF isolation. | Preserve both boundaries explicitly in the inspected-baseline and hardware sections. Closed by source/manual review. |
| 2 | Low: historical memory/resource observations or documentation checks could imply LPF acceptance. | Label historical observations, measure no resource delta, keep item 4 open, and distinguish documentation validation from all implementation gates. Closed by the resource and acceptance sections. |
| 2 | Medium: the documented fixed-frequency workflow could be mistaken for the operator's verified deployment, and error prevention could be omitted from the benefit comparison. | State that the deployed workload is unknown, avoid a quantitative negative-ROI claim, and include declared-coverage error prevention as another reassessment trigger. Closed by the scope, benefit and reassessment text. |

The second pass leaves no actionable issue in the bounded assessment. Implementation and its acceptance remain deferred; they are not review findings closed by documentation.

## Documentation validation

The following commands passed for this assessment and its backlog/prompt references:

```sh
docs/.venv/bin/python -m sphinx -E -a -n -W --keep-going -b html docs docs/_build/html
docs/.venv/bin/python scripts/check_documentation.py
docs/.venv/bin/python tests/test_image_delivery.py
git diff --check
```

The link checker examined 84 Markdown sources, 17 HTML pages and 1,456 local targets with zero errors; the image-delivery check passed its one test. These checks validate documentation only. The operator manual was considered and left unchanged because automatic selection remains unavailable; Pi and Pi operator documentation require no change for this assessment. There are no new LPF implementation, resource, integration or physical acceptance results.
