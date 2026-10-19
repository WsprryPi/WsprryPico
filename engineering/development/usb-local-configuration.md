# USB local configuration authority

The production USB management adapter selects `usb_physical` internally. It
reuses `BrowserApi`, its common ETag/If-Match revision, typed target envelope,
configuration validators and the existing standalone journals. Network callers
cannot select that authority through request JSON. The firmware owner admits
only an identified healthy device without reset intent or unsafe ownership;
configuration mutations require the same idle transmitter as existing writes.
USB administrative authority does not grant transmitter ownership.

`network::LocalUsbApi::handle(request, transaction)` routes supported `/api/v1/`
application resources and the explicit USB Wi-Fi resource. Its
`finish(transaction, delivered)` applies or cancels only that transaction's
pending restart/network effects. The UMP1 owner supplies physical connection,
boot/session/target binding and response acknowledgment; a parsed request alone
is not proof of delivery. Durable saves survive delivery failure and must be
reconciled through authoritative readback before another mutation.

## Hostname and display

GET/PUT `/api/v1/hostname` retains `transmitter-hostname/1`. The PUT envelope is
`{schema,target,hostname}`; `hostname` is a canonical `.local` name or `null` to
select the existing device default. Readback separates saved, active and
default names, writable status and pending restart. An unconfigured USB device
uses the canonical default and can save another name without Wi-Fi or UTC.
USB has no independent nickname store.

The Pi displays the verified saved name as the common name, with USB transport
and immutable device identity separate. Saved renames do not assert an already
renamed network responder. Engineering names remain bound to deployment TLS
credentials and are read-only. Consumer certificate renames retain the CA and
server private key and require qualified time; the local UTC hook is separate
from the existing network-commissioning SNTP qualification.

## Explicit Wi-Fi lifecycle

GET `/api/usb/v1/wifi` returns `transmitter-wifi/1`, the exact member target,
`wifi`, profile `generation`, `pending_restart` and `storage_healthy`. `wifi` is
`null` for no saved connection, otherwise `{ssid,password:null,time_server}`.
No response returns a password.

PUT requires If-Match and `{schema,target,wifi:{ssid,password,time_server}}`.
A string password replaces the credential. A null password preserves only the
currently saved connection's password and requires the same SSID; it cannot
silently transfer a password to a different network. DELETE requires If-Match
and `{schema,target,wifi:null}`. PUT does not accept null as an alternate delete.
The supported cardinality remains one saved network.

These operations save configuration without an association trial, DHCP, DNS,
SNTP, TLS generation or AP. They leave the USB connection/time channel usable.
Saved network changes require the supported explicit restart/application step;
readback does not claim the running station has already changed. A successful
profile save latches the scheduler's existing restart-required state, so
application, configuration and standalone-status projections agree. Later
Config saves cannot clear that profile restart latch; STOP and pin latches are
preserved. Existing
`/api/v1/network` requests control runtime enabled state separately.

Deletion is not disablement, omitted fields, password preservation or factory
reset. It preserves station, pins, schedules, hostname, STOP, transmitter
watermarks and retained trust. Before the authoritative profile selection
commits, matching saved-progress network fields and standalone network fields
are replaced with the selected values (empty credentials for deletion). This
prevents later draft application or profile overlay from resurrecting a removed
connection. The final profile journal selection is the Wi-Fi commit boundary.
An interrupted request can leave preceding draft/base housekeeping committed;
it does not authorize a blind replay. The selected profile remains decisive,
and a storage fault/refused acknowledgment requires readback or recovery.

A versioned profile is retained even after deleting the final connection. A
blank USB device never borrows old standalone credentials or fabricates an
engineering certificate. Network sessions retain their existing profile and
password-generation invalidation policy; USB authority is independent of the
removed password.

## Profile persistence and station atomicity

Consumer profile journal versions 1 and 2 remain valid and preserve their
commissioned station/network and TLS rules. New source-5 consumer version 3
uses `usb_managed=true` internally, persists explicit `tls_pending`, permits
empty SSID/password, and omits the station snapshot. Station authority for this
version is the existing standalone Config journal. It retains owner, TLS,
client and commissioning-receipt fields. No new flash region is allocated.

A one-time migration copies the complete effective pre-migration configuration
into the standalone journal before selecting version 3. That preparation does
not change the effective station or radio configuration. The requested complete
Config is then committed through the existing single Config journal, so an
interrupted save cannot combine a new station with an old radio configuration.
Saved-progress is never automatically promoted to a runnable configuration.
USB exposes the existing GET progress, POST progress/update and POST
progress/apply resources, with the same target, common revision, draft revision,
field validation and explicit application domain. Independent station fields
can be saved without a network or complete Config. Only an explicit successful
USB apply creates or updates the runnable Config. A read-only network observer
cannot apply a consumer station-identity draft; the original consumer gate
remains in force for network callers. Network commissioning can still create its supported complete consumer profile;
ordinary network radio configuration retains its station-identity restrictions.

For engineering profiles, journal version 2 permits explicitly absent Wi-Fi
while preserving the exact deployment TLS material and credential-bound name.
Its schema size is the same as version 1. Consumer version 3 removes the station
snapshot, so its extra pending flag does not reduce existing usable profile
capacity. Existing legacy consumer versions remain in use for Wi-Fi-only edits
unless absent-network or standalone station authority requires migration.

Old firmware that cannot parse these new profile versions fails closed; it is
not a supported rollback vehicle after migration. It must not recover an older
network profile or reopen superseded trust. Published firmware compatibility
and source-pair records must distinguish retained WTP compatibility from new
USB management/profile support.

## Validation scope

`usb_local_management_tests` exercises actual local/API/coordinator/journal code
for blank hostname and no-network configuration, Wi-Fi create/replace/delete/
recreate, password preservation, revision and target refusals, network-carrier
separation, cold reconstruction, interrupted profile writes, draft credential
non-resurrection, and retained pins/schedules/STOP/watermarks. Existing hostname
and network suites cover their unchanged network policies. The production-pair
`usb_management_driver` runs UMP1, TimeExchange and these real services over
stdin/stdout with volatile flash and no network/Pico SDK. It establishes wire
interoperability, not physical USB, flash endurance, network association,
restart/re-enumeration or transmitter RF qualification.

Current USB discovery is `transmitter-management/3`, with five carrier rows and
selected `usb_physical`. The network /2 projection remains unchanged, including
its legacy closed USB exclusion. Neither that projection nor USB WTP connectivity
is the authority for USB JSON support; negotiate UMP1 and read its capabilities.

The independent [GPIO-drive descriptor](gpio-drive.md) selects config/3,
update/3 with `transmitter-config-update/2`, application/3, hardware/2 and
progress/2. Legacy resource shapes remain closed. Ordinary omitted drive saves
preserve it; explicit replacement/reset defaults to 4 mA. Draft saving does
not apply drive, while explicit progress domain `drive` does so through complete
Config validation and the sticky restart/output-inhibit latch. No save programs
the physical pad; nullable pad readback is a cached ARM-initialization register
verification, distinct from saved and immutable boot selection.

Source: [local settings/profile lifecycle](../../src/provisioning/local_settings.cpp),
[local dispatch](../../src/network/local_usb_api.hpp),
[BrowserApi](../../src/network/api.cpp) and
[existing local-management tests](../../tests/usb_local_management_tests.cpp).
