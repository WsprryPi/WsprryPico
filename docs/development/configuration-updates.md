# Configuration preservation and explicit replacement

Configuration uses the existing Config v1 scheduler and verified journal.
These operations grant no job ownership, clear no STOP/fault, and change no WTP/1
messages, recurrence authority, provisioning profiles or flash layout.

## Legacy saves and migration

`PUT /api/v1/config` retains its mandatory Config v1 fields: `version`, `enabled`,
complete `station`, `wifi.ssid`, `wifi.password`, and `schedules`. With existing
healthy saved configuration, omitted optional settings are preserved:

| Optional setting | Ordinary API PUT | Initial setup, Console CONFIG or explicit replacement |
| --- | --- | --- |
| `pins` | Saved plan | Default plan |
| `allow_unqualified_frequency` | Saved value | false |
| `allow_non_amateur_frequency` | Saved value | false |
| `expires_utc_s` | Saved expiry | 0, no expiry |
| `wifi.ntp_ipv4` | Saved time server | `pool.ntp.org` |

This intentionally changes the old API reset-by-omission policy. Clients that
relied on it must send explicit reset values or select replacement below.
Missing fields never identify an old client or a reset request. Client headers
and firmware dates do not select policy. Initial setup, durable decoding,
default serialized bytes and Console `CONFIG` retain their existing meanings.

Explicit false, zero, time-server values and complete default pin plans apply.
`wifi.password:null` retains its existing preserve semantics and requires an
authoritative existing configuration/password. It remains null on readback;
no error echoes credentials. Null is not generic deletion or reset.

## Advertised atomic merge and replacement

Read the selected Pico's `/api/v1/capabilities` `configuration_updates` object:

```json
{"schema":"transmitter-config-update/1","path":"/api/v1/config/update","method":"POST","modes":["merge","replace"],"max_update_bytes":2048,"max_config_bytes":1800,"legacy_put_omission":"preserve_optional"}
```

POST requires exactly `schema`, `target`, `mode`, `config`. The target is the
authoritative application's `scope:"member"`, `device_id`, `boot_id`; If-Match
is the exact common ETag. This operation requires healthy existing saved
configuration; initial setup continues through existing PUT/provisioning paths.

```json
{
  "schema": "transmitter-config-update/1",
  "target": {
    "scope": "member",
    "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "boot_id": "00000000000000000000000000000001"
  },
  "mode": "merge",
  "config": {"wifi":{"ntp_ipv4":"pool.ntp.org","password":null}}
}
```

The identities are synthetic. An older server without this capability must not
receive the envelope. WTP CAPS and Pi host projections do not establish support;
Pi adoption/fallback/version-pair work remains in
[WsprryPi #448](https://github.com/WsprryPi/WsprryPi/issues/448).

| Input | Merge | Replace |
| --- | --- | --- |
| Missing field | Preserve | Mandatory Config v1 fields required; optional fields default |
| Station/Wi-Fi object | Nonempty subset of known leaves | Complete existing Config v1 object |
| Schedules | Replace entire array | Replace entire array |
| Pins | Complete existing plan | Complete plan, or default if omitted |
| False / zero | Apply | Apply |
| Password null | Preserve | Preserve |
| Other null | Reject, except existing unallocated pin slots | Same |
| Empty config | Reject | Reject: required fields absent |

`mode:"replace"` supplies deliberate replacement/reset intent. A complete
document in that mode may omit pins/flags to restore defaults. Merge can reset
them by explicitly sending a complete default pin plan and false flags. Arrays
never append or merge by index. Empty schedules require compatible resulting
enablement; all schedules, station data and pin plans pass complete validation.
Unknown fields, duplicate keys, unsupported schema/mode and malformed values
reject. The [closed schema](../protocol/transmitter-config-update-1.schema.json)
and [vectors](../protocol/transmitter-config-update-1-vectors.json) distinguish
structural validity from runtime target, cross-field and admission checks.
The existing JSON parser accepts signed 32-bit integer tokens: nonzero expiry
currently ends at 2,147,483,647 UTC seconds. This update preserves that parser
bound rather than changing the shared WTP codec.

## Authority, bounds and uncertain outcomes

Engineering HTTPS, authenticated field HTTPS and committed Consumer-Radio
dispatch use the existing handler. No listener or management carrier is added.
Authentication, Host/Origin/Fetch Metadata/CSRF and common ETag checks apply.
Field Configure remains denied to blank/preclock sessions. Profile-owned Wi-Fi
and station identity use existing setup transactions, not radio configuration.

Mutations require idle, unowned, inactive, nonfaulted state. Loaded, armed,
running, unresolved output and pending setup/network/restart retain their
exclusions. Identical and A-to-B-to-A saves consume journal generations.
Wrong device/boot or missing/stale revisions cannot authorize an update.

One complete validated candidate reaches one verified commit. New requests are
limited to **2,048 UTF-8 bytes**, including whitespace; the resulting Config
remains **1,800 bytes**. Legacy PUT retains its incoming 1,800-byte bound.
Responses use existing redacted `config`, `reboot_required` and resulting ETag,
within **4,096 bytes**. Shared memory admission may refuse requests sooner.

Station/schedule/flag changes affect subsequent admissions without reboot.
Network/pin changes retain saved-versus-active and restart reporting. Restoring
old pins or saving station data cannot clear pin-restart/output inhibition.
Benign station changes may retain the latch. Post-commit shutdown failure
returns `output_disable_failed`, leaving saved/active state and the fault
reconcilable. Storage failures never report success; torn records retain
fail-closed recovery. STOP and the separate consumed-slot cursor survive.

Never automatically repeat an ambiguous mutation or switch strategies after a
lost reply. A write may already be committed. Read authoritative saved/active
state, revision, storage health and status before explicitly reconciling a
new action. Software evidence does not qualify physical or RF behavior.
