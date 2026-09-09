# Browser and production-client coverage

The bounded 2026-09-09 continuation completed actual Chrome submission and
cancellation, production settings writes, production completion/cancellation,
and concurrent Chrome Armed/Running/terminal observations. It exposed and fixed
a WsprryPi scheduled-wait connection timeout and two Pico browser failure-state
issues. Phase 11.4 remains open: Chrome did not capture the brief production
Loaded state, and the previously recorded physical/network qualification gates
remain outstanding.

The [execution prompt](browser-production-coverage-prompt.md) records the scope.
The user separately approved inhibited acceptance, installed-service pauses with
restoration, and an isolated WsprryPi companion fix with commit/push. After the
user committed their WsprryPi work, the isolated branch was rebased onto latest
`origin/devel` at `89f23e5`; the original checkout was preserved.

## Exact evidence identity

- Pico 2 W / RP2350 on wspr5, USB serial `0BF4B4AEC9FFB344`, WTP device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`; Console `-if00`, WTP `-if02`.
- All physical cases used installed revision `f88fa71eef5e`, boot
  `b3cf6adbca443d954750abaa161cde18`, engine
  `inhibited-standalone-simulator`. UF2 SHA-256:
  `7345d87f8816b8890971bc6ce785778f273ff8d6fbe470d9fdd005714ca2b751`.
- Certified alias `wsprrypico-0a60df.local:18443`; observed address
  `192.168.1.47`. Server certificate SHA-256:
  `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
  Existing browser and controller certificates were used. TLS verification was
  retained. Production tests explicitly selected the fresh USB-reported address
  with the certified DNS identity; these are not NSS/mDNS qualification.
- Original production application: source `2e47641f6ebdff104e32999f5194f2e0dc408e06`,
  binary SHA-256 `3acd44dd6a8933cc816604a4514d8517e7586a2da40bff628378e080af5c6857`.
- Corrected application: source `923ab570fe53ef2ccca7d12e519c9dc36adf7e93`,
  isolated directory `/home/pi/wsprrypi-browser-coverage-20260909`, binary
  `src/build/bin/wsprrypi-browser-coverage`, SHA-256
  `993ad62def487e5f03d82a5a7a1f5f82b972b16bd36eaa5b0d9a8c13a7166323`.
  Built with `make release BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= -j2`;
  acceptance explicitly selected `--backend wtp`, with ancillary GPIO disabled.
  This exercised the real application/configuration/scheduler/controller path.

## Physical subcases

All jobs used nominal 3,570,100 Hz and the inhibited engine. There were eight
accepted finite jobs: five Chrome tone plans of 30 seconds and three production
QRSS `E` plans of 20 seconds, at most 210 seconds of planned simulated execution.
The original 60-second-lead failure did not reach LOAD/ARM. No RF output,
GPIO operation, firmware flash, trust change or network reconfiguration occurred
in this continuation.

| Subcase | Result and evidence |
| --- | --- |
| G1 actual Chrome completion | Job `34b0677dc8d84ce19751c2f23a97c80d`: Armed, Running, Complete; matching USB terminal record, inactive and unowned. |
| G2 actual Chrome Armed cancellation | `26bd776df36b45ff97546b05888f9e6f`: Abort produced matching aborted state. A later Release returned `LEASE_EXPIRED`; natural lease expiry, not that failed Release, removed ownership. |
| G2 actual Chrome Running cancellation | `43f062cc86cb4377a0ffe388db1a9e8b`: Chrome observed Running at 12:43:53Z and immediately clicked Abort. Matching aborted USB terminal record and inactive/unowned status followed. |
| G1 corrected production completion | `edd768b3a53fb8760000000000000001`: requested start 12:46:34Z, 60-second lead; complete authoritative job, cleanup OK, no shifted start. |
| C2 concurrent actual Chrome | The same production job was Armed at 12:46:29Z, Running at 12:46:34Z, Complete at 12:46:54Z and empty/unowned at 12:46:56Z. Foreign owner ID remained accurate and Abort/Release were disabled. Production history captured Loaded; Chrome did not. |
| G2 production cancellation | `7e879120cd36366d0000000000000001`: production `/api/v1/jobs` ABORT after Running; typed outcome `cancelled`, matching authoritative `aborted` job, `stopped:true`, cleanup OK. This was not a direct WTP cancellation substituted for the application. |
| C2/G2 foreign authority | Distinct browser-certificate HTTPS session against that production job received 409 `NOT_OWNER` for ABORT and RELEASE. At 12:48:14Z, follow-up status still showed the matching Running job and production owner `67abd3815287c9a9288aaddd8c5b1769`, output false. |
| C3 production settings | Actual production API returned missing-revision 428, changed power 20→23 with a new ETag, rejected stale revision with 412, and read back 23 with password null. Chrome kept draft 27 across Refresh and stale Save; explicit reload displayed 23. Production restored the exact baseline configuration and original ETag, and Chrome reloaded 20. |

Browser Loaded-only submission is not exposed as a separate shipped action:
its form performs HELLO/CLAIM/LOAD/ARM sequentially. Deterministic browser checks
cover foreign Loaded/Armed/Running controls, and direct physical Loaded cases in
the earlier record remain valid. These do not replace the missing actual Chrome
observation of the production Loaded interval.

## Original failures retained

- The first settings observer treated transient null capabilities during
  reconnection as a valid identity-bearing object and failed. The wrapper was
  corrected to distinguish transitional observations; the service was restored.
- The initial proposed power 21 was correctly rejected as invalid WSPR power.
  The approved small delta was exercised with valid 23; the 400 is retained.
- The first restoration read returned 409 `host_busy_or_output_unresolved`.
  No write followed that failed read. A later fresh read/ETag allowed exact
  restoration; this does not qualify uninterrupted network availability.
- Original production job `101a5433470b51980000000000000001`, scheduled 60 seconds
  ahead, failed before ARM with a closed transport and unresolved cleanup.
  Independent USB established inactive/unowned state. A separate 30-second-lead
  control job `c2f1d4db21b736cc0000000000000001` completed on the old binary.
- Early foreign checks found no owner or arrived after terminal release and
  returned `LEASE_EXPIRED`. They were not counted as active-owner rejection.
- Chrome job `9e5c6a68c5f74e93addaecdb0f12d93a` was aborted after its start, but its
  last browser observation was Armed. Job `979e72f732654118964ff24e9bf92c82`
  was observed Running, but the subsequent cancellation arrived too late and
  the device completed it. Neither substitutes for the final observed-running
  cancellation case. A browser automation deadline before dispatch is also
  retained; it was not treated as a device mutation result.

## Implementation and adversarial assessments

**Round 1 — failure reproduction and repairs.** The production scheduler silently
waited longer than the Pico server's documented 30-second idle budget. Its sole
session owner now sends bounded read-only STATUS observations during Waiting.
It does not CLAIM early, retry a failed mutation or shift the slot. Failed
observations latch Blocked; stop/reload and clock admission are rechecked after
I/O. A new 60-second regression failed before the repair and passed afterward.

Browser review found that unknown output could leave submission/release enabled,
and the mutation-error notice asserted that status was checked even when its
refresh failed. Submission now requires the existing authoritative idle gate;
release requires explicit inactive output. Failed reconciliation says that status
remains unknown. Lost CLAIM/LOAD/ARM tests prove no subsequent mutation/retry;
foreign-state controls and unknown-output cases are covered.

**Round 2 — challenge the fixes and evidence.** Exercised lost STATUS, changed boot,
stop/reload during a status transaction, cancellation followed by a fresh request,
and a delay crossing the start time. No failed pending request reached
CLAIM/LOAD/ARM. Real TLS and physical production tests retained the requested
start. Review corrected overly broad interpretations of late Chrome observations,
expired-lease rejection and transitional null fields. These attempts remain
separate from the successful replacement cases.

**Round 3 — final assessment.** Reviewed complete source/test/document diffs,
identity-bound reports, source/binary hashes, original failures, cleanup and exact
settings restoration. The new browser short-circuit conditions keep null snapshots
safe; uncertain output does not authorize release. No additional actionable
implementation finding remains in this slice. The short unobserved Chrome Loaded
interval, new-browser deployment and broader physical gates remain explicit
limitations, not inferred passes.

## Validation

- Pico affected CTest suites: `network_tests`, `network_browser_tests`,
  `network_tls_tests`, `network_11_1_interop`,
  `inhibited_network_acceptance_tests`: **5/5 pass** (36.40 seconds final run).
  Existing interop pins were preserved.
- `node tests/network_browser_tests.js`: pass; the new lost-response assertion
  reproduced the old misleading notice before the repair.
- `node tests/network_browser_render.js build/browser-production-coverage/ui`:
  isolated actual Chrome with local fixtures, desktop 1280×900 and mobile 390×844;
  unknown/unavailable output, owner controls, draft retention and no overflow pass.
  Desktop/mobile screenshots were inspected using Impeccable hardening guidance.
  These are local fixture evidence, not device screenshots.
- Standard inhibited firmware cross-build and
  `python3 scripts/check_standalone_image.py build/phase11-4-remote-settings-firmware/firmware/WsprryPico.elf`:
  pass, including stack/heap and reserved journal/UF2 boundaries. The new browser
  source was **not flashed**; all physical cases above used installed `f88fa71`.
- WsprryPi `make wtp-scheduler-test SUDO=`: 54,641 checks, normal and ASan/UBSan.
  `wtp-backend-test`, `wtp-status-test`, `wtp-application-test`: respectively
  5,472 / 20,959 / 38,957 checks passed.
- `make wtp-network-interop-test SUDO= PICO_SOURCE=/private/tmp/pico-browser-interop-pin-20260909 MBEDTLS_SOURCE=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls`:
  pass against unchanged pinned Pico `d8cde03` and MbedTLS `0bebf8b`;
  actual TLS 60-second wait, management, partial I/O, lost mutations and recovery.
  Actual second-IPv4 loopback rebind was explicitly skipped on this macOS host
  (`127.0.0.2` unavailable); injected-address contract still ran.
- Both repository diffs passed whitespace checks. No SDK/tool installation or
  protocol/component/interop-pin change was needed.

## Final state and evidence retention

Final USB INFO/HELLO/CAPS/STATUS show the same deployed boot/revision, healthy
storage, `empty`, `output_active:false`, null owner/job and matching completion/
aborted records. Standalone remains disabled, station AA0NT/EM18/power20,
schedule 120/0, original watermark `1788714601000000000`, existing Wi-Fi/time
configuration. The production settings readback exactly equals its original
baseline, including the revision and redacted password semantics.

Every service pause used an independent finally restoration path and checked
installed binary/INI hashes against that run's baseline. Final service is active;
final installed binary SHA-256 is
`c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273`, INI SHA-256
`e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8`.
The corrected candidate was not installed over that binary. Provider output was
explicitly false before, during pause and after restoration in retained runs.

Private logs, configs, original failures, helpers and renders remain ignored in
`build/browser-production-coverage/`; selected wspr5 run directories are archived
in `remote-evidence.tar.gz`, SHA-256
`da1ac9123bcf9fcfcad338745e47433744f51d6fefc336d492de376e0a9a3d48`.
No keys, Wi-Fi secrets, captures or generated firmware are committed.

## Documentation Impact

Updated this execution/review record, the comprehensive prompt and joint
C2/C3/G1/G2 matrix; the companion updates its scheduling contract and acceptance
record. Existing WsprryPi operator backend guidance was considered unchanged:
there is no new operator control or configuration option. No separate operator
repository edit is required for this internal connection-liveness repair.
The broader phase remains open for Chrome Loaded observation, device deployment
of the new UI safeguards, DHCP/address faults, second-board trust, certificate
rotation, long-running reliability, target resources and RF qualification.
