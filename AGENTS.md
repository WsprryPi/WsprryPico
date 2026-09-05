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
- Begin with Pico 2 W / RP2350. Do not port RP1 DKMS or Linux hardware access.
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
- Keep hardware tests opt-in. Flashing, USB device control, debugger access,
  GPIO changes and RF output require explicit authorization for the intended action.
- Never infer live RF authority from permission to build firmware or run unit tests.
- Record exact board, firmware, engine, clock, mode and setup for hardware evidence.
  Mock or host results do not qualify target timing or RF output.
- Do not invent working build/test commands. Current development status and
  available checks are in docs/development/README.md.
