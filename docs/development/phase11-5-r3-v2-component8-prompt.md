# Component 8: reduce replay-stage LOAD memory use

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`, starting from
`ba28bd5ff0ba7bc59b0e8258ebc8a5b6ac6fdd9e`. Reproduce the first identical
512-event LOAD replay's memory peak through the production parser, decoder,
service and response encoder. Component 7 verified the primary reply with
31,384 bytes of TLS allocation, then stopped during replay because allocator
peak headroom was 29,288 bytes against the required 32,768-byte reserve.

Read README.md, CONTRACT.md, docs/architecture.md, project instructions and
current development guidance. Inspect the working tree and preserve existing
work. Use component 7's scope, result and review under `docs/development/` and
private evidence under `build/phase11-5-r3-group2-component7/evidence/`.

1. Preserve the exact C7 request identity: 52,105 framed bytes, SHA-256
   `e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670`.
   Extend the production endpoint regression in `tests/load_reply_driver.cpp`
   and `tests/load_reply_tests.py` across primary, identical replay and fresh-ID
   replay. Include E6 retained history and aged request-cache preparation.
2. Account for retained jobs, cached replies, decoded events, temporary JSON
   views, input storage, output pages and measured TLS costs. Count allocation
   lifetimes rather than accumulating all pages ever allocated. Separate target
   measurements, host ABI costs, calibrated estimates and uncertainty. Preserve
   the unchanged reserve and historical failed results.
3. Identify a supported allocation overlap and implement the smallest justified
   correction. Add a regression that fails before the correction and passes
   afterward. Verify exact complete replies, framing, CRC, schema, identities,
   adjustment values, retained-state behavior and absence of repeated RF
   preparation. Test empty/maximum/over-limit arrays, paged traversal and relevant
   refusal or allocation-failure paths.
4. Review adversarially for correctness, lifetime errors, protocol behavior and
   misleading memory claims. Repair actionable findings, rerun affected checks
   and reassess until those checks pass. Use the documented host build/test flow,
   sanitizers for changed lifetimes, and the available pinned RP2350 cross-build.
5. Save this prompt, reproducible results, analysis and review in the repository.
   Keep raw captures, credentials and generated firmware private. Update current
   progress while preserving earlier results. Commit and push the reviewed work,
   independently verify remote parity, and report the fix, tests and remaining
   physical acceptance gates.

This step covers software repair and validation. It includes no device control,
flash, Wi-Fi/fixture manipulation or RF output. The component 7 physical reserve
failure remains recorded. Host results and a build do not close the pending
bounded target replay/observation check or broader Group 2 acceptance.
