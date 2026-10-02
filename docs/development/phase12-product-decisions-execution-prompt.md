# Phase 12 selected product decisions — execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Implement this prompt,
validate it, conduct independent adversarial review, repair actionable findings
and repeat assessment until the implemented scope has no unresolved actionable
finding. Commit and push scoped work, independently verify remote parity, and
report source evidence separately from target acceptance.

## Read and preserve

Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md, the development
guide, current closure matrix, reset/access/profile/activation contracts and
production code before implementation. Preserve the six concurrent files named
in the closure matrix byte-for-byte. Do not modify other repositories, install
or download dependencies, flash devices, access USB/debuggers, change networks,
inject target faults or emit RF. Physical authority remains absent. GP14 stays
opt-in/default-off. RF ledger remains 16 acquisitions / 11 jobs.

## Selected behavior

1. Allow durable optional station-detail saves without fresh SNTP. Return an
   explicit settings-saved/readiness-pending result until trustworthy time is
   available. Preserve existing certificates and authorized clients, do not
   rotate trust or activate unvalidated TLS. Implement bounded pending state and
   restart-safe transition to readiness once accepted time is available. Browser
   hints are not elevated to trusted time; existing RF launch admission stays.
2. Provisioning reset clears network credentials, consumer/TLS provisioning,
   engineering access and BLE bonds. Preserve effective station settings even
   when they currently reside in the consumer profile being removed, schedules
   and no-repeat watermark. Full erase additionally clears those operational
   records. Both preserve the RP2350-E10 boot-workaround sector. Require
   idle/inactive JobService/output authority and durable reset intent. Resume
   interrupted reset at boot before any superseded network, trust, scheduled or
   job authority can become active. Storage failures fail closed and remain
   recoverable; never revive stale fallback state.
3. Provide separate recovery-page actions, two explicit confirmations and a
   typed operator phrase: `reset provisioning` or `erase`. No USB confirmation
   and no new physical gesture. The open AP provides no operator authentication;
   these controls prevent accidental destruction only. Explain exact clearing
   and preservation before confirmation. Bind requests to current device/boot,
   reset level and bounded one-use request, prevent replay/cross-device/expired
   submissions and ambiguous-response automatic retry. Preserve normal setup.

## Implementation and validation

Keep portable policy/storage orchestration independent of Pico adapters. Reuse
existing journals, reset coordinator, source tombstones, request crypto and one
JobService. Version stored/wire data explicitly when required; read old formats
safely and reject malformed pending records. Clear transient secrets. Avoid
unbounded waits, flash loops and catch-all success/failure claims. Add meaningful
behavioral tests for offline save/reboot/readiness, populated trust preservation,
reset levels, consumer-station migration, busy/inactive guards, every durable
interruption boundary, failed clear/resume, wrong device/boot/phrase, expiration,
replay, request-result uncertainty and browser confirmation behavior.

Run affected deterministic tests, full current host suite, meaningful sanitizers,
WTP contract checks, formatting/whitespace and pinned inhibited/normal-RF firmware
builds without target access. Review linked memory layout and E10 exclusion.
Have independent reviewers attack production wiring, failure/reboot paths and
browser/request state, not merely happy-path test coverage. Iterate fixes and
reassess. Record selected contracts, actual results, limitations and remaining
physical gates in scoped documentation; Phase 12 remains OPEN_PARTIAL until its
physical matrix passes. Stage only attributable files, commit, push devel, verify
remote SHA independently and preserve unrelated file hashes.
