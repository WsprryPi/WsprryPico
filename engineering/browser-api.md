# Shared transmitter control contract

The shared logical API uses `/api/control/v1` and the contract identifier
`Wsprry-Control/1`. Resource types have stable `schema` discriminators under
that contract; application, station, hardware, progress and settings updates
do not negotiate independent schema generations. Superseded `/api/v1`
control routes and historical views are unsupported.

WsprryPico owns the contract definitions. WsprryPi consumes the same current
contract. Firmware release identities identify builds; they do not select a
settings schema or substitute for capability negotiation. WTP/1 remains the
independent device-neutral finite-job protocol.

## Resource model

Capabilities describe implemented features, current availability, selected
management carrier and bounded policy values. Known resource documents are
closed objects: missing or extra fields, duplicate keys, wrong types,
unsupported units and inconsistent advertisement/readback are rejected.
Unknown optional feature identifiers grant no authority and can be left unused
only at explicitly defined extension points.

Application state distinguishes saved configuration, applied station state,
immutable boot-active hardware, pending restart and live observations. Saved
drafts are non-runnable. Saving a draft does not apply settings, enable a
schedule or establish transmitter readiness. Application requires an explicit
saved revision and domain.

Hardware includes current pin roles, amplifier-enable pin and polarity, GPIO
drive and their saved/active observations. Amplifier timing and filter settings
retain their authoritative domain resources. Manual RF correction, standalone
frequency, NTP timeout and profile-owned settings retain their own storage
and application rules; a configuration projection must not report invented
defaults in place of those authoritative values.

## Pi client route authority

The producer route registry describes Pico browser/API operations. It does not
grant every operation to every companion client. The authoritative `client_routes`
metadata defines the Pi management subset and a separate consumer-session scope
for logout. Pi network and Consumer-Radio clients enforce the generated scopes
before transport access. Raw job administration, restart, hostname, password and
commissioning endpoints are outside the Pi management scope. Dedicated job,
profile and session paths retain their own authority. Every scoped route must be
a bounded, unique member of the producer registry for the same HTTP method.

## Updates and revisions

Ordinary settings updates contain only intended fields. Omission preserves
unrelated settings; explicit false and zero are values. Secrets are redacted
on read and never reconstructed from redacted configuration. Reset is an
explicit scoped operation. The complete resulting configuration is validated
before its authoritative atomic transaction commits. Independent journal and
profile transactions do not become one atomic write merely because a control
view composes them.

Mutations require the current contract, exact device/boot target and current
If-Match revision, plus the selected carrier's authenticated authority.
Profile generations and request identities retain their defined bindings.
Malformed or unsupported context refuses before writes. No legacy full-save
reconstruction, mutation retry, alternate peer or carrier fallback is used.

A lost or malformed reply leaves the outcome unconfirmed. Read authoritative
saved state and review the retained draft before another deliberate save.
Restart and network effects retain complete-response delivery confirmation;
USB requires the matching ACK. Disconnect cancels undelivered deferred effects,
not durable writes or accepted jobs.

## Transports and access

Engineering HTTPS, authenticated consumer control and local USB dispatch the
same logical control documents to the same application authorities. Carrier
selection never grants transmitter ownership. USB physical authority cannot
be requested by a network caller. Consumer raw HTTP does not expose management
mutations; authenticated encrypted wrappers remain mandatory. Public setup
mutations remain scoped to their existing commissioning authority.

Public discovery grants GET access only to the explicit redacted public
registry. Resource existence or write support does not make a resource public.
Passwords, keys and certificate material remain excluded. Public reads do not
create or renew a login, claim a job or authorize writes.

Session durations and payload budgets are typed policy data within documented
implementation and security ceilings. Clients validate bounds and relationships
rather than matching historical descriptor literals. Authentication semantics,
units, enum meanings and safety constraints remain fixed by the contract.

## Hardware and execution

Pin roles are exclusive. Drive and amplifier/filter changes retain boot
activation and restart/output-inhibition latching, including A-to-B-to-A saves.
An amplifier-enable pin is disabled by default. Lead and tail default to 200 ms
and accept 0–1000 whole milliseconds. They surround one complete finite job;
stop/fault cleanup disables the amplifier without waiting for normal tail.
Readback does not measure amplifier readiness, RF power or filter response.

All job producers use the existing JobService. WTP framing, ownership,
scheduling, UTC admission and local RP2350 RF timing are independent of this
control reset. No control save transmits or proves readiness.

## Version policy and evidence

Only the current control major is supported. Before the first shared-control
stable release, the major stays at 1 while the one current schema and semantics
evolve, including breaking changes, through coordinated Pi/Pico changes and both
required integration suites. After the release transition, incompatible changes
require an explicitly reviewed new control major. New optional
features use defined extension points; policy values within defined bounds
do not create another resource generation.

Transport/authentication formats, flash records and deployment manifests retain
versions for their independently parsed bytes. Their identifiers do not reset
when a control representation changes. Stored records are never reinterpreted
under a cosmetically reset version.

Coordinated changes update Pico production handlers and every Pi/browser
consumer, generated asset, adapter, fixture and documentation. Both production
network and USB integration suites must pass for the explicit candidate source
pair. Contract digests identify reviewed artifacts; runtime compatibility does
not require matching product versions, Git commits or entire build digests.
Software tests establish no physical USB, installation, service, timing or RF
qualification.


## Prerelease lifecycle and first release

The authoritative [control lifecycle policy](protocol/control-policy.json) is in
`prerelease` phase. The major, `Wsprry-Control/1`, `/api/control/v1/` and schema ID
stay fixed. Resource discriminators remain unversioned; resource route generations
and version selectors are forbidden. Schema contents may change before the first
release without maintaining historical compatibility. Producer, consumers,
generated assets, documentation and required network/USB integration checks move
together for every change.

`scripts/check_control_policy.py` enforces the policy during Pico CMake configure,
metadata generation and CI. Pi vendors the exact policy and checker with provenance
hashes, verifies them during generation and checks them in non-hardware CI. This
policy does not freeze firmware/application SemVer, WTP, authentication/crypto,
USB framing, logging wire formats, journals or deployment bundle formats. Those
independent boundaries retain their own existing validation and version rules.

The first shared-control stable release requires a reviewed transition, after the
intended schema and paired checks are final:

```sh
python3 scripts/check_control_policy.py --record-first-release 1.0.0
python3 scripts/generate_control_contract.py
```

The release number is the actual first stable release identifier; `1.0.0` is an
example. The command records `phase:"released"`, the identifier and the SHA-256 of
canonical JSON (sorted keys, compact separators and UTF-8). It does not publish a
release. Vendor the policy into Pi, rerun the paired gates and review/commit the
transition with the release sources. Pico stable-tag CI refuses a prerelease policy;
released mode refuses schema digest drift. Subsequent incompatible control changes
need an explicit policy/checker review for a new major. Editing a stored digest to
approve schema drift is not a release procedure. No release transition has occurred.
