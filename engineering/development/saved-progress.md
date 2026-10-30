# Saved progress

The stable `progress` resource belongs to `Wsprry-Control/1` at
`/api/control/v1/progress`. Save changes through `progress/update` and explicitly
apply a saved revision/domain through `progress/apply`. Historical draft
resource generations and complete-save fallback workflows are unsupported.

A draft is non-runnable persisted work. Fields can be saved independently with
per-field outcomes; invalid units do not become applied settings. Callsign,
locator, reported power, schedule, network, pin and drive drafts retain their
own validation. Clearing a draft is explicit and differs from a false or zero
setting. Omitted draft values use the applied configuration where the domain
permits it; incomplete station identity cannot enable a frequency or schedule.

Save binds the current contract, member device/boot, exact revision and request
identity. The receipt identifies the actual canonical submitted bytes. Changed
payload under a repeated request identity refuses. Repeated or lost replies do
not authorize another mutation automatically. Read authoritative draft and
applied state before another deliberate save.

Application uses the saved revision and selected domain, never newer unsaved
browser values. Complete resulting configuration, profile authority, ownership,
storage health and output guards remain mandatory. Application does not grant
WTP ownership or clear STOP. Hardware application preserves restart inhibition,
including A/B/A changes; network and credentials retain their transactional
profile authority. Independent journals are not presented as one atomic write.

Readback distinguishes draft revision, applied configuration/profile revision,
field outcomes, complete station, application domains and current recurrence.
The [control contract](../browser-api.md) and
[current schema](../protocol/control-1.schema.json) define bounded closed shapes.
