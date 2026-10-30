# Configuration updates

`Wsprry-Control/1` provides POST `/api/control/v1/config/update` with a
closed `{contract,schema,target,mode,config}` envelope. The stable schema is
`config-update`; the ordinary mode is `merge`. Historical complete PUT and
replacement strategies are unsupported. GET `/api/control/v1/config` reports
redacted current configuration and its exact ETag, without exposing an internal
storage-format version as an API negotiation.

A patch is a nonempty closed subset of current settings. Omission preserves
saved values. Explicit false and zero are values. Nested station/Wi-Fi patches
preserve unrelated leaves; arrays replace their scoped value and pin plans
remain complete validated plans. Null is only the defined password-preserve
sentinel or a nullable field, never a generic reset request. Initial complete
configuration uses the same update authority with all required initial values.

Pico constructs and validates the complete candidate before the verified
journal transaction. Exact current device/boot target and If-Match are required.
Ownership, output, storage health, STOP, schedules and profile authority remain
with the existing scheduler and journals. A merge does not clear a fault,
claim a job or enable transmission by implication. Reset operations are explicit
and scoped; no reset-by-omission behavior exists.

Ordinary station, network and schedule forms send only their intended fields.
They do not reconstruct saved credentials or copy advanced fields from a GET.
Profile-owned station/network settings retain their transactional setup paths;
generic updates cannot bypass ownership. Hardware changes retain restart and
output-inhibition latching. Hostname, frequency, correction, timeout, timing and
filter settings retain their documented authoritative resources.

A lost response leaves the save unconfirmed. Preserve the browser draft, read
saved state and review before another deliberate save. Do not retry, change
strategy or substitute a carrier automatically. A successful durable write can
survive disconnect; deferred network/restart effects still require the matching
complete-response delivery receipt.

The [control contract](../browser-api.md) and machine-readable
[resource schema](../protocol/control-1.schema.json) define current shapes.
