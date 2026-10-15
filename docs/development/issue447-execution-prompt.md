# Issue 447 configuration-preservation execution prompt

Implement [WsprryPi #447](https://github.com/WsprryPi/WsprryPi/issues/447) in
WsprryPico. This prompt records the bounded scope resumed by the maintainer on
October 15, 2026. Pi client/UI changes and its full supported-version matrix
remain in [#448](https://github.com/WsprryPi/WsprryPi/issues/448).

## Baseline and scope

Start from committed Pico `dfffdd5220db8b7cf1acf5e74950dbd294283c55` on an
isolated `codex/issue-447-config-preservation` feature branch. Inspect current
instructions, status, staged/unstaged changes, configuration authority and
consumer/field adapters. Keep the active application checkout and unrelated
work untouched. Current consumer LAN access is committed; historical AP-only
and incomplete Phase 14 descriptions must not determine the current design.

Preserve WTP/1, one JobService, one scheduler, existing flash journals and
configuration limits. Do not implement fleet parity, recurrence transfer,
new carriers, RF engines, provisioning or qualification-policy changes. Do
not change Pi's client or canonical interoperability pin under this issue.

## Contract to implement

### Legacy API PUT

Keep the existing required Config v1 shape and validation. When authoritative
saved configuration exists, `PUT /api/v1/config` preserves omitted `pins`,
`allow_unqualified_frequency`, `allow_non_amateur_frequency`,
`expires_utc_s` and nested `wifi.ntp_ipv4`. Supplied values, including false,
zero and a complete default pin plan, apply intentionally. Mandatory station,
Wi-Fi, enabled and schedule fields retain their legacy required meanings.

This is an intentional compatibility-policy change: omission on an ordinary
save no longer means reset. Do not infer client age or intent from headers or
version guesses. Initial setup without saved configuration retains existing
defaults. The durable parser and Console CONFIG remain explicit complete
replacement; do not change their omission semantics or journal bytes.

### Capability-advertised configuration update

Add `POST /api/v1/config/update`, with a 2,048-byte UTF-8 request limit,
including whitespace. Advertise the operation, independently versioned schema,
supported modes, request limit and 1,800-byte complete-result bound in JSON
capabilities. Use existing HTTP POST support; do not introduce PATCH.

The closed envelope is exactly:

```json
{
  "schema": "transmitter-config-update/1",
  "target": {
    "scope": "member",
    "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "boot_id": "00000000000000000000000000000001"
  },
  "mode": "merge",
  "config": {"allow_unqualified_frequency": false}
}
```

Require an existing healthy authoritative configuration, exact device/boot
target and the current common If-Match. `mode` is `merge` or `replace`.

- Merge accepts a nonempty closed subset of implemented Config v1 fields.
  Station and Wi-Fi objects merge known supplied leaves and must be nonempty
  when present. Arrays replace atomically, without append or element merging.
  Pins use a complete existing plan, never a new partial pin schema.
- Replace requires a complete Config v1 document and intentionally defaults
  omitted optional values, exactly as complete decoding does today. Selecting
  replace is the explicit intent signal; no ordinary PUT or merge infers reset
  from omission. This is not factory reset or profile replacement.
- Explicit false and zero are values. Null is invalid except existing pin-plan
  null slots and the established `wifi.password:null` preservation sentinel.
  A null password requires authoritative existing credentials/configuration;
  replacement does not silently erase it. Explicit passwords retain validation.
- Unknown members, duplicate keys, unsupported schema/mode, malformed values,
  oversized requests/results and invalid resulting configuration reject.
  An empty schedule array is valid only when the resulting configuration
  permits it. Unchanged saves still consume journal generation for ABA safety.

Construct a bounded candidate from supported fields, then run the existing
complete parser, pin validation, consumer-profile authority checks and
Scheduler CONFIG/verified journal path. No mutation may precede complete
validation. Do not add persistent settings or an alternate store.

## Authority and transport protection

Retain authentication, Host/Origin/Fetch Metadata/CSRF rules and exact common
ETag forwarding. Preserve idle/unowned/inactive/nonfaulted admission, local
STOP, consumed-slot watermarks, pending setup/network/restart exclusions and
serial writers. A loaded foreign job is never aborted or adopted by settings.

Preserve saved versus active pins and restart/output-inhibit latches. Benign
station changes may retain a pin-restart latch; no save may clear it or a fault
or grant RF authority. An output-disable failure after persistence must report
the actual application failure and leave saved/active state reconcilable.

Classify the new POST as Configure in the existing authenticated field adapter.
The committed Consumer-Radio adapter already carries inner POST; exercise it
through its actual authenticated dispatch. Retain profile-owned Wi-Fi/station
identity, profile generation, setup transaction exclusion, cookie/session
admission and pre-clock/blank restrictions. Add no listener or carrier. Plain
LAN WTP, USB WTP and BLE WTP do not become JSON management transports.

Return the existing redacted configuration/result ETag and reboot requirement;
keep response within 4,096 bytes. Do not echo credentials in failures or traces.
Do not automatically retry ambiguous mutations. A lost reply can follow a
committed save, so authoritative readback/revision reconciliation is required.

## Required implementation evidence

1. Run the actual unchanged Pi management JavaScript in a hardware-free DOM/HTTP
   fixture, capture its emitted legacy PUT, and feed that request to the actual
   Pico BrowserApi and journal. Preserve nondefault pins, both frequency flags,
   credentials and cursor through station edits/reload. Keep the producer source
   provenance explicit; do not hand-build a supposedly captured Pi request.
2. Cover all omitted optionals, explicit false/default resets, new merge/replace,
   nested station/Wi-Fi updates, array replacement and invalid complete results.
   Prove initial/durable/Console defaults remain unchanged.
3. Test malformed, duplicate, escaped duplicate/unknown, unsupported, null,
   oversized, deeply nested and paged input. Include input near both byte bounds
   and a merge whose complete result exceeds 1,800 bytes.
4. Test missing/stale/ABA/boot/target revisions and serialized competing writers;
   owned/loaded/armed/running/faulted/uncertain output; pending setup/network/
   restart work; retained pin-restart and post-commit output-disable failure.
5. Inject failed/interrupted persistence and verify authoritative reload,
   no partial application, generation/cursor/STOP retention, redaction and
   ambiguous committed writes. Reuse existing recovery/fault infrastructure.
6. Exercise engineering BrowserApi, authenticated field Configure classification
   and committed consumer dispatch without broadening any admission policy.
   Run relevant existing application, network, storage, WTP scheduling/ownership/
   cancellation/recovery, schema/vector and browser regressions.

## Environment and documentation

No native macOS C++ build retries, incidental tool installation or SDK download.
Use existing Linux tools and pinned dependencies. The maintainer authorizes Pi
hosts and Pico A/B as needed; start with isolated hardware-free checks and
preserve installed software/configuration. Physical or RF evidence, if needed,
must identify exact image/device/operation/restoration and remain separate from
software results. No RF transmission is necessary for these parser/persistence
software assertions. Do not use the disconnected external test SSD.

Write closed schema/vectors and update browser API, standalone, pin and shared
application documentation where semantics change. Document the breaking
reset-by-omission policy explicitly, client migration, carriers, limits,
initial/Console distinctions and #448's remaining integration boundary.
Record implementation/review/validation results in a companion issue447 review
record. Operator-docs follow-up is separate; do not edit another documentation
repository without its authorization. No UI presentation change is planned;
if one becomes necessary, use Impeccable and desktop/mobile rendering first.

## Independent review, publication and completion

After implementation and relevant validation, give a separate reviewer agent
the complete diff, contract, acceptance table and evidence. Require it to
challenge silent resets, partial validation, dropped unknown fields, optional
defaults, password null/redaction, profile authority, stale/ABA/target writes,
false capability claims, memory bounds, storage failures and old-client behavior.
Record every actionable finding; repair it, run affected checks, and request a
fresh adversarial assessment. Repeat until no actionable in-scope finding remains.

Review the complete diff/staged content, commit only attributable feature work,
push the feature branch and verify remote SHA parity. Merge the reviewed feature
to `devel` as explicitly requested, without force-push or rewriting others' work;
push and independently verify remote devel parity. Preserve unrelated changes
and do not publish a release. After successful merge/parity verification, remove
the task's feature worktree and delete its local and remote feature branch as
the maintainer additionally requested. Record applicable CI and issue evidence.

Close #447 only if its required gates are satisfied. Otherwise report exactly
what is delivered and keep unresolved dependency/physical gates explicit; #448's
Pi client/version-pair work is not silently completed by Pico software checks.
The final report includes prompt/review paths, behavior, exact checks/results,
adversarial repairs and final assessment, Documentation Impact, branch/commits,
merge/push/parity, actual working-tree state and any remaining acceptance.
