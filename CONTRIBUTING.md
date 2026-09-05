# Contributing

Read [the project contract](CONTRACT.md), [architecture](docs/architecture.md)
and [development guide](docs/development/README.md) before making changes.

Keep changes focused and preserve existing work. Update the relevant design
or protocol documentation with behavior changes, clearly identifying drafts.
Use the established review, implementation, repair and reassessment workflow;
commit and publication are separate actions requiring authorization.

Follow .editorconfig and .clang-format. Use portable C/C++ application logic
with Pico-specific adapters. Add meaningful deterministic tests for changed
behavior, including failure and cancellation paths where applicable.

Normal validation must not open a device, flash firmware or emit RF. Hardware
checks must state the board, firmware, setup, bounds, expected evidence, stop
procedure and cleanup. Do not treat a host test as target qualification.

Before adding a dependency or copying WsprryPi code, record its source revision,
license, attribution, purpose and build/distribution impact. Original
contributions are provided under [MIT](LICENSE.md); upstream terms remain intact.

Do not include Wi-Fi passwords, tokens, private keys, local machine paths or
unreviewed captures in contributions. A pull request should explain the problem,
resulting behavior, validation and material limitations.
