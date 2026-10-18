# USB installer implementation and acceptance

Status: **in flight**. Software and physical acceptance remain separate. The
operator authorized consolidation with μChrony and the documentation cleanup
on 2026-10-18. The shared Pico `devel` checkout now contains the combined sources;
the isolated installer tree remains a preserved validation snapshot. Publication,
Pi deployment pinning and physical preserving-upgrade acceptance remain open.

## Source and device identities

The original implementation and validation snapshot is at
`/Users/lbussy/.codex/worktrees/pico-usb-installer/WsprryPico`, based on Pico devel
`582b7221b78537813e997b1be0c880dbadab0697`. Integration retains the newer μChrony
phase-slew clock fields, NTP-learning flash reservation and cleaned documentation.
WsprryPi changes
start from devel `fe701cf4c2b05e46cb84927188984084503d1cea`. Its package deployment
pin will be frozen after a coordinated reviewed Pico commit exists.

The operator confirmed the new board is **Pico C**, a Pico 2 W:

- USB/chip serial: `1545B6EFBF78028C`; RP2350 A2 QFN60.
- WTP device ID: `c2a3a2a314c948b50a8562a1aeb69669`.
- Mac physical parent/location: `34603008` (`0x02100000`).
- No RF path was identified for this installer test. No transmit job was sent.

## Physical initial installation and read-only recovery

The initial backup found unidentified program fragments, erased WsprryPico
saved-state banks, and only the exact RP2350 E10 workaround in the final sector.
The first ordinary install correctly refused before writing. The operator then
explicitly authorized replacing the unidentified application bytes.

Anonymous devel bookmark resolution selected normal CI version
`0.1.0-ci.39084514130.1`, run `39084514130`, attempt 1, source
`582b7221b78537813e997b1be0c880dbadab0697`, published tag
`v0.1.0-ci.39084514130.1`. Whole-run verify/publish success, retained receipt,
release/tag/source, metadata and exact public downloads were checked.

- UF2: `WsprryPico-0.1.0-ci.39084514130.1-pico2_w.uf2`, 4,688,384 bytes.
- UF2 SHA-256: `4e5c5f1de45f12ae5499f2e6ff4e07115f22d69e1e3a476c0f4ba7c01e4513b0`.
- Manifest SHA-256: `b22ff0980a384b3443537455c73ec89417a67ccfa106ce1d22fc7a8e46e040e6`.

USB-enabled picotool 2.3.0 was built from existing pinned local sources, without
an SDK/tool installation. Executable SHA-256:
`6ddca221ea6975470a340d4e0ebcb2e4079189b0088a24c1d2c98e2543e5ab26`.
Application programming, independent tool verification, full readback and
reserved-byte equality succeeded. Initial postboot discovery failed because
macOS attaches CDC clients under data interfaces; a transient empty ioreg plist
also needed handling. Both discovery defects were repaired. Explicit recovery
then verified the already-programmed running application without another write.
It reported the exact installed firmware/source and unconfigured saved state.

Backup and reserved-state hashes remain private. Raw backups and transactions
remain under the operator's owner-only state directory, outside Git and web
roots. The last device check verified the above CI image and unconfigured
settings on Pico C. This task has not loaded the new maintenance firmware or
created or removed any release/tag.
The absent main bookmark and absent compatible stable image produce refusal;
explicit devel was used for this physical test.

## Validation so far

The combined `devel` source passes a fresh Linux portable build on wspr5 and
13 focused CTest suites covering μChrony, NTP replay, USB maintenance, installer,
standalone scheduling, reset and flash layout. All 32 installer and 29 packaging
tests pass. Normal and inhibited Pico firmware cross-builds pass their linked
engine, reserved-flash, stack, heap and USB checks. WTP artifacts, bootstrap
Bash/ShellCheck, changed Markdown paths and whitespace checks pass. The Pi
companion's five deployment tests and firmware UI unit/integration checks pass;
its source remains unchanged and uncommitted on Pi `devel`. These consolidation
checks involve no firmware load, device operation, host-clock change or RF test.
They do not establish a full canonical CI pass or physical upgrade acceptance.

- Python installer behavior: 32 tests pass, including two branch fixtures,
  invalid provenance/assets/UF2, offline selection, explicit confirmation,
  failed backups, byte mismatch, guarded upgrade, semantic mismatch refusal,
  same-boot recovery, conflicting selectors and local-build failure without
  fallback, bounded unchanged-refusal history, failed atomic-write retry and
  repeated application/BOOTSEL recovery. Controlled fixtures are software
  evidence, not physical upgrades.
- Clean isolated host build succeeds. The focused CTest selection passes 5/5:
  `usb_local_management_tests`, `usb_maintenance_tests`, `usb_installer_tests`,
  `standalone_tests` and `wsprrypico_core_tests`.
- Broad isolated host run: 194 registered; environmental failures included
  unavailable jsonschema/Noble dependencies, sandbox loopback/write restrictions
  and the Mac's existing system compiler/linker mismatch. This is not a claim
  that the complete host suite passed. Dependency-complete Linux CI is pending.
- Normal and explicit inhibited firmware cross-builds and linked
  engine/storage/USB/stack/heap checks pass with the pinned existing SDK and
  compiler. The explicit developer path
  completed a fresh dirty normal build and returned a labelled local bundle:
  UF2 SHA-256 `bdfb45ccd3cbb686542eff69cc1b7226215e5a78cfdb5670a473e4d956bf6e92`.
  It was not installed and is not relabelled as CI firmware.
- Pi UI unit behavior and five private deployment/adapter tests pass. Actual
  source-owned UI renders at 1440×1100 and 390×844 in light/dark for checked,
  pending, refusal, failure, reconnect and success states, with no horizontal
  overflow. Impeccable's detector reports no findings; screenshots were inspected.
- Pi Linux installer C++ tests and the complete configuration/runtime client
  compile pass in an authorized wspr4 `/tmp` snapshot (Debian 13.7 aarch64,
  g++ 14.2). OpenSSL 3.5.7 development headers were extracted from the Debian
  package, using existing runtime libraries. Build metadata is disabled only
  for this exported non-Git test tree. No system package, service, checkout or
  transmitter hardware was changed. JavaScript tests run on the Mac because
  this Linux host has no Node runtime; no Linux aggregate/whole-suite pass is
  claimed.
- Linux browser API, USB-management and installer C++ test binaries pass;
  `web_server_control_routes.cpp` also passes a separate g++ syntax check with
  the repository component include paths. WTP contract validation passes
  23 schema, seven raw JSON, one framing and eight transition cases. Bootstrap
  and Pi lifecycle Bash syntax/ShellCheck and both diff checks pass.

The current validation commands include:

```sh
python3 tests/usb_installer_tests.py
python3 scripts/validate_wtp_contract.py
cmake --build <isolated-host-build> --target usb_maintenance_tests -j4
ctest --test-dir <isolated-host-build> --output-on-failure \
  -R '^(usb_local_management_tests|usb_maintenance_tests|usb_installer_tests|standalone_tests|wsprrypico_core_tests)$'
cmake --build <isolated-firmware-build> --target WsprryPico WsprryPico-Inhibited -j4
```

The host and firmware outputs are `build/usb-installer/clean-host` and
`build/usb-installer/firmware-local-validated` in the shared Pico checkout;
both compile the isolated source. Pi checks use
`python3 scripts/tests/pico_usb_deploy_test.py`,
`node WsprryPi-UI/tests/wtp_firmware_test.js` and
`node WsprryPi-UI/tests/wtp_firmware_ui_integration_test.js`. The authorized
Linux export uses `make pico-usb-installer-cpp-test wtp-config-client-build`
from its `src` directory with `BUILD_METADATA_ENABLED=0`, its extracted
OpenSSL include/pkg-config paths and `WTP_NETWORK_CXXFLAGS='-O0 -g0'`.

## Independent review and remaining acceptance

The read-only reviewer identified and prompted repairs for the snapshot/reset
race, private destination/durability and retention, failure-record masking,
semantic watermark/suspension comparison, archive/receipt binding, pending setup
operations, postboot standalone scheduling, ambiguous finish ACK messages,
local-image identity and silently conflicting selectors. The new FLASH_UPDATE
boot hold is established before scheduler construction. Disconnect, timeout or
cancel does not release it; matching postboot verification and acknowledged
finish do. A release-requested record handles uncertain acknowledgement.
Later review also repaired process-group cleanup, verified-source/schema
execution, physical-inhibit reset admission, selected-member UI invalidation,
private browser-result filtering, compact local identity retention, Linux
runtime compilation, and repeated recovery/unchanged-refusal retention.
Final read-only reassessment reports no remaining actionable source/doc
findings. The reviewer independently reran the 32 installer tests, five Pi
deployment/adapter tests, UI unit, Impeccable detector, Bash syntax and diff
checks. Target builds and Linux C++ checks are separate implementation-agent
evidence, not independently rerun by the reviewer.

Open gates: publication through reviewed non-force pushes, immutable Pi deployment pin, published
bootstrap verification, canonical CI containing the new maintenance firmware,
physical preserving upgrade and recovery on Pico C, and the real Pi USB entry
point. Linux/Pi USB programming has not been physically qualified. Neither
mock tests, cross-builds nor initial installation establish these gates or RF
qualification. Backlog item 7 remains in flight until required evidence exists.
