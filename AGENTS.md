# Project instructions

## Scope and working practices

- Read README.md, CONTRACT.md and docs/architecture.md before implementation.
- Preserve user changes and inspect the current working state before editing.
- Keep changes within the requested slice. Other WsprryPi-family repositories
  are independent; reading them does not authorize changing them.
- Do not initialize Git, stage, commit, push or publish unless requested.
  Do not reset, stash or remove existing work or Git metadata without authorization.
- Fix actionable review findings and rerun affected checks before claiming completion.
- Report what changed, checks performed, limitations and actual repository state.

## Pico architecture

- WsprryPico is a standalone application and a WsprryPi hardware backend.
- The defined target is Pico 2 W / RP2350. Do not port RP1 DKMS or Linux
  hardware access.
- Keep the portable job, protocol and encoder logic separate from Pico SDK,
  transport, storage and RF engine adapters.
- USB CDC is the reference transport. RF timing is always local to RP2350;
  complete jobs must not depend on per-symbol USB or network delivery.
- Keep WTP device-neutral and independently versioned in docs/protocol/WTP.md.
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
  available checks are in docs/development/README.md.
