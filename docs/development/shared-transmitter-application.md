# Shared transmitter application foundation

The Pico member now exposes versioned application, station and hardware JSON
resources through its existing authenticated HTTPS BrowserApi. They project the
same standalone configuration journal and use the same scheduler and JobService
as existing browser, USB, network and autonomous paths. This is a Pico software
foundation for the [fleet contract](../transmitter-application-contract.md);
WsprryPi mapping and full application parity remain separate repository work.

See the [execution prompt](shared-transmitter-application-execution-prompt.md),
[review and validation](shared-transmitter-application-review.md),
[closed schemas](../protocol/transmitter-application-1.schema.json),
[request vectors](../protocol/transmitter-application-1-vectors.json) and
[hardware inventory coverage](../protocol/transmitter-application-1-coverage.json).

## Resources and carriers

| Route | Resource version and behavior |
| --- | --- |
| `GET /api/v1/application` | `transmitter-application/1`; member identity, embedded station/hardware resources, member recurrence and capability boundaries. |
| `GET/PUT /api/v1/station` | `transmitter-station/1`; station defaults and scoped station replacement. |
| `GET/PUT /api/v1/hardware` | `transmitter-hardware/1`; saved/active pin plans and scoped supported pin replacement. |

`/api/v1/capabilities` advertises these resources and their paths. The resource
version is independent of WTP/1, Field-GATT/1, firmware and Config v1.
Application is read-only; schedules, network provisioning and jobs retain their
existing routes. `/api/v1/pins` supplies the eligible GPIOs, fixed I2C pairs and
adapter support; `/api/v1/pins/validate` reviews candidates without applying them.
Existing `/api/v1/status` remains the authoritative job, ownership, time and
output observation. The new application document does not substitute for it.

Existing engineering station HTTPS uses its certificate principal. Existing
field HTTPS retains cookie/session admission and classifies these routes, plus
pin review, as Configure operations: blank and provisioned-preclock access is
denied, and normal authenticated access retains its existing restrictions. The
new routes do not open the consumer HTTP portal, add a consumer station listener,
change default listener enablement, or create JSON management over USB, BLE or
Plain LAN WTP. A WTP connection alone does not imply a management carrier.

## Identity and revision

Every response identifies `target.scope:"member"`, `target.device_id` and
`target.boot_id`. Updates carry the target from authoritative member readback.
Do not translate a member update into controller-local settings or select a
different node after a connection error.

GET responses return the common opaque, quoted ETag. PUT requires that exact
value in If-Match, along with the existing authentication, Host/Origin,
content-type and `X-WsprryPico-Request: 1` policy. All configuration projections
share a token derived from device/boot identity, network administration revision,
durable configuration journal sequence and canonical configuration. Identical
saves consume the generation; A-to-B-to-A writes cannot revive the A token.
Successful saves invalidate old tokens across old and new routes. This is an
optimistic concurrency token, not a secret or authorization credential.

`saved_generation` is a decimal string for the journal sequence, or null when
no healthy saved configuration exists. Hardware `active_revision` is a separate
opaque digest bound to device/boot identity and the boot-selected pin plan. It is an observation value,
not the If-Match token. Hardware `active` is null when the scheduler was constructed
without healthy configuration; later provisioning does not invent a boot-applied
plan. Plan selection does not prove electrical pin state or RF qualification.

## Station updates

A station update contains only schema, target and the complete station object:

```json
{
  "schema": "transmitter-station/1",
  "target": {
    "scope": "member",
    "device_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "boot_id": "00000000000000000000000000000001"
  },
  "station": {"callsign": "K1ABC", "locator": "FN42AB", "power_dbm": 10}
}
```

`power_dbm` is reported WSPR message power. It is neither electrical pad/synth
drive nor measured RF output. Supported values are 0, 3, 7, 10, 13, 17, 20, 23,
27, 30, 33, 37, 40, 43, 47, 50, 53, 57 and 60 dBm. Locators are four or six
uppercase Maidenhead characters; the Type 1 encoder uses the first four.
New station writes must compile with the existing Type 1 encoder. A structurally
valid portable or extended callsign can therefore be rejected as
`unsupported_station_encoding`. Existing Config v1 station acceptance is retained.

Station saves apply to future locally compiled jobs. They preserve Wi-Fi
credentials, time server, schedules, expiry, recurrence enablement, watermarks,
pin plans and STOP suspension. They cannot change already owned/loaded work.

## Hardware updates and restart

A hardware update contains schema `transmitter-hardware/1`, target and `pins`.
The pin object is the complete plan documented in the
[pin allocation guide](pin-allocation.md). Shared resources reuse those exact
GP numbers, fixed pair IDs and exclusive ownership rules; no second pin model
or peripheral authority is introduced.

Only direct PIO assignments, supported active-low button assignments and the
shared onboard/external/disabled indicator can be saved. Amplifier, LPF and
Si5351/I2C execution remain unavailable. Candidate eligibility does not authorize
operation. Drive, reference calibration and waveform fields are also unavailable;
unknown fields are rejected. The coverage map records every Pi inventory row
and distinguishes implemented, partial, platform-specific and future adapters.

Hardware GET reports saved pins and generation separately from the active boot
plan and active revision. Changing pins commits the supported configuration and
latches JobService output inhibition until restart. `pending_restart` reports
that latch; restoring old pins or editing station data cannot clear it. The
application's `reboot_required` also covers pending network boot settings.
`execution_engine` reports the service's actual engine, including an inhibited
or simulated engine; selecting a direct pin plan does not authorize RF output.

## Mutation and persistence

Writes require an existing healthy Config v1 and the existing idle, unowned,
inactive, nonfaulted gate. Missing configuration returns `not_configured`; initial
setup continues through the existing configuration/provisioning flow. Loaded,
armed, running or owned work blocks writes. Pending network/restart response
transactions also exclude them. The core-0 application owner serializes these
routes, Console, scheduler and WTP admission.

Each update reconstructs and validates the complete supported configuration,
then uses Scheduler CONFIG and the existing verified journal commit. There is
no new journal, persistence record or flash region. Station and hardware writes
retain existing enablement; hardware saves do not grant ownership, enable
recurrence, clear STOP/fault/inhibit state, renew a lease or select a clock.
Storage failure reports an error and unhealthy storage; new reads withhold
untrusted saved values. Existing journal recovery and boot admission inhibition
continue to apply. On an ambiguous result, read authoritative configuration,
storage health, saved/active plans and job status before retrying.

PUT bodies are limited to **1,024 UTF-8 bytes**, including whitespace. The
complete resulting Config v1 still fits its **1,800-byte** limit. New resource
responses have a **4,096-byte** software validation budget. The existing HTTP
job-body limit is unchanged. Schemas describe structural constraints; target
matching, encoder representability, pin conflicts, supported adapters, revision,
admission and storage remain runtime checks. The vectors state structural and
HTTP outcomes separately, including duplicate members and oversized bodies.

| HTTP result | Relevant errors |
| --- | --- |
| 400 | `invalid_json`, `invalid_resource`, `unsupported_resource_schema`, `invalid_config`, `unsupported_station_encoding`, `invalid_pin_plan`, `unsupported_pin_adapter`, structured pin conflict details. |
| 401/403 | Existing authentication, Host/Origin and field access refusal. |
| 409 | `target_mismatch`, `not_configured`, `busy`, `network_change_pending`. |
| 412/428 | `revision_conflict`, `revision_required`. |
| 413 | `resource_body_too_large`. |
| 503 | `storage_fault`, `output_disable_failed` or existing bounded memory refusal. |

An output-disable failure can occur after the journal commit. It returns 503,
leaves the new plan saved but pending, retains the JobService output inhibit and
latches a scheduler configuration fault reported as hardware `application_error`;
read saved/active configuration and job status to reconcile it. A successful
save is never reported when shutdown confirmation fails. Further configuration
and local admissions remain blocked until a new boot; the hardware fault is not
silently cleared by a later station edit. No new WTP state is introduced.

Default legacy configuration serialization is unchanged. The pin branch's
explicit Config v1 extension and nondefault-pin downgrade boundary remain in
force. No additional fields are added to that stored document by these resources.

## Remaining implementation gates

The local scheduler continues member-owned WSPR recurrence at the build-selected
base frequency. Application expiry and frequency observations use decimal
strings; schedule period/phase retain the existing integer semantics. The
controller may independently dispatch complete finite WTP jobs but must not also
dispatch occurrences belonging to an enabled member schedule. This foundation
does not implement recurrence transfer, automatic offline fallback or expanded
autonomous modes/frequencies.

Pi native/remote mapping, controller integration, calibration/drive, amplifier
and filter lifecycle, Pico Si5351, expanded recurrence, target measurements and
conducted RF remain the contract's separate gates. No Phase 11/12 acceptance or
physical/RF qualification is closed by this software work.
