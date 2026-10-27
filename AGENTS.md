# Project instructions

## Scope and working practices

- Read README.md, CONTRACT.md and engineering/architecture.md before implementation.
- Preserve user changes and inspect the current working state before editing.
- Keep changes within the requested slice. Other WsprryPi-family repositories
  are independent; reading them does not authorize changing them.
- Do not initialize Git, stage, commit, push or publish unless requested.
  Do not reset, stash or remove existing work or Git metadata without authorization.
- Fix actionable review findings and rerun affected checks before claiming completion.
- Report what changed, checks performed, limitations and actual repository state.
- Keep published project documentation on Read the Docs. Do not reintroduce GitHub Pages or any Pages deployment workflows, publishing branches, environments or repository settings.

## Pi/Pico capability and protocol completion gate

Changes to advertised capabilities, protocol/API schemas, descriptors, carrier support, wire formats, limits/units, session policies or protocol-facing interfaces are coordinated WsprryPi/WsprryPico changes.

- Inspect the producer and every affected companion client before implementation. Update capability advertisements, version descriptors, companion negotiation/parsing, strict validators, runtime consumption, serialization, generated assets, paired test adapters and documentation together in the same task.
- Preserve exact closed-contract validation for every supported version, including historical limits and semantics. Validate document shape before field access. Reject unsupported versions/carriers, missing or extra fields, wrong types, inconsistent advertised/returned schemas, and invalid device/boot/profile bindings before mutation.
- Keep independently versioned contracts independent. Introduce an explicit version when a closed contract changes; do not silently redefine historical versions, accept arbitrary version ranges, relax validation, substitute an older peer, or add hidden downgrade/carrier fallback to make tests pass.
- Both actual network and USB integration suites must pass before completion, including when a change initially appears specific to one carrier. Exercise the production Pi client/coordinator and Pico handlers, crypto, serialization, framing/ACK and journals using the intended candidate sources from both repositories. Mock-only checks, isolated unit tests, builds, old green CI or tests against stale or unintended snapshots do not satisfy this gate.
- Use the checked-in WsprryPi `.github/workflows/debian-non-hardware.yml` recipes for `wtp-network-loopback` and `wtp-usb-management-pair`. Network coverage includes `wtp-network-runtime-test`, `wtp-network-interop-test` and `wtp-config-interop-test`; USB coverage includes building the actual Pico `usb_management_driver`, `wtp-usb-pair-client-build`, `wtp-usb-management-test` and running `WsprryPi-UI/tests/wtp_usb_pair_test.js` through the production Pi/Pico pair. Select the actual edited/candidate Pico source and required pinned dependencies explicitly.
- Cover valid historical/current contracts and negative cases for unknown versions, malformed descriptors/documents, changed limits, identity/revision mismatches and refusal before writes. Update affected test adapters when production interfaces change; preserve production-path coverage.
- Failed, cancelled, timed-out or skipped required integration checks remain unresolved. Investigate and fix or rerun them; do not declare completion while either required suite lacks a successful result for the intended source pair. An inherited companion mismatch that prevents validating the changed contract is part of the integration work.
- Keep repository authority and Git boundaries separate. Ensure required companion changes are available on the intended paired refs; do not claim delivery on `devel` or `main` when the companion update exists only on an unmerged side branch. Report missing authority or unavailable dependencies as blockers instead of leaving a companion follow-up behind a completion claim.
- Report both source revisions and any tested uncommitted changes, exact commands/results and relevant CI links. These integration fixtures are hardware-free software evidence; physical USB, installation, service, timing and RF qualification remain separate.

## Repository and work-harness cleanup

- For an explicit request to clean up WsprryPico or this project/repository,
  follow [the reusable cleanup prompt](engineering/development/repository-cleanup-prompt.md).
- Inventory deletion, rewrite, retention and hold decisions before cleanup
  changes. Cover project artifacts in the checkout, local work areas and
  identified Raspberry Pi harnesses; preserve user work and shared tools.
- Documentation describes the current product in direct, impersonal language.
  Selected future work belongs in the consolidated backlog or an issue.
  Remove obsolete evidence and development narratives without creating an archive.
- Operator-facing prose, especially README.md, explains current capabilities
  and use in plain language. Replace engineering status and validation narratives
  with capability descriptions; retain needed technical detail in engineering
  documentation. Do not substitute engineering links for operator explanations,
  add documentation placeholders or promise future documentation.
- Delete completed, superseded and abandoned execution prompts and temporary
  handoffs after consolidating any needed technical content. Repair their
  references; do not archive them or retain them solely because a completed
  checklist item links to them. Keep only handoffs needed for selected unfinished
  work and genuinely reusable instructions.
- Apply the same inventory, rewrite, reference-repair and validation process to
  development phase and step references, including those in README.md and
  SECURITY.md. Preserve phase/step organization only in explicitly retained,
  currently used planning documents such as ROADMAP.md, consolidated-backlog.md
  or an equivalent active plan. Preserve actual operating instructions and
  technical uses of phase or step.
- Reading or maintaining the prompt alone does not invoke cleanup.

## Pico architecture

- WsprryPico is a standalone application and a WsprryPi hardware backend.
- The defined target is Pico 2 W / RP2350. Do not port RP1 DKMS or Linux
  hardware access.
- Keep the portable job, protocol and encoder logic separate from Pico SDK,
  transport, storage and RF engine adapters.
- USB CDC is the reference transport. RF timing is always local to RP2350;
  complete jobs must not depend on per-symbol USB or network delivery.
- Keep WTP device-neutral and independently versioned in engineering/protocol/WTP.md.
- Preserve the shared JSON browser API direction. Do not introduce Apache/PHP
  into firmware or a third protocol repository.
- Record unresolved design choices as proposals, not implemented contracts.

## Source, dependencies and licensing

- Follow .editorconfig and .clang-format. Use C/C++ and CMake for Pico firmware;
  pin language standards, SDK and toolchain versions when adding build targets.
- Keep owned implementation and headers under src/, tests under tests/, and
  SDK/build helpers under cmake/ or scripts/ as needed. Do not create empty scaffolding.
- Original project contributions use MIT. Preserve upstream licenses and
  attribution when reusing code; inspect exact source provenance first.
- Do not download an SDK or install tools as an incidental formatting step.
- Keep credentials, local SDK paths, captures and generated firmware out of source control.

## Validation and hardware

- Default validation is deterministic and hardware-free. Test behavior and
  failure paths appropriate to each change; avoid tests that merely mirror code.
- Infer hardware-test authorization from the user's task and setup statements.
  A statement such as "Pico A is connected to the SDR", "Pico B is connected
  to the SDR", or both named Picos being connected authorizes RF testing on
  those boards for the current task. This includes the routine firmware loads,
  USB device control, debugger/GPIO operations and restoration needed to run
  the tests. Proceed without separate hardware/RF approval or per-job prompts.
- Follow the user's current setup statements and any stated limits or stop
  instructions, including when older prompts or packets request separate
  authorization. Keep tests finite, verify device/setup identity, preserve
  settings and restore the setup. Permission to build or run unit tests alone
  does not establish a connected RF-test setup.
- Record exact board, firmware, engine, clock, mode and setup for hardware evidence.
  Mock or host results do not qualify target timing or RF output.
- Do not invent working build/test commands. Current development status and
  available checks are in engineering/development/README.md.
