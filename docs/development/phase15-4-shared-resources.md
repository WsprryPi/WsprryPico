# P15.4 shared-resource controller adoption

Status: implementation and local software acceptance passed; publication and
lead pushed-head CI acceptance pending. Implementation is led by
[WsprryPi's P15.4 record](https://github.com/WsprryPi/WsprryPi/blob/devel/docs/development/phase15-4-shared-resources.md).

Pico's existing application, station, hardware and pin resources are sufficient
for the selected controller workflow. This slice changes no Pico implementation,
wire schema, journal format, ownership authority or RF engine. The exact current
implementation dependency is `ddb00dd7960373cec271f7816c0e1b10117416e9`, whose
changes from accepted P15.3 `d6208dbc88005383041c5ec306b738db7ec22796` are documentation
only. Later companion documentation commits do not replace that tested source pin.

Pi now uses explicit `/api/v1/member/application`, `/api/v1/member/station`,
`/api/v1/member/hardware`, `/api/v1/member/pins` and
`/api/v1/member/pins/validate`, under its protected host boundary and
existing runtime coordinator. Engineering mTLS and explicit Consumer-Radio/1
station/AP management reach the existing actual Pico handlers. The closed
`transmitter-management/1` operation list and legacy `authenticated_https`
resource metadata remain unchanged. No new discovery version or fallback is added.

Application is read-only. Complete station and hardware saves remain separate
transactions under the common configuration ETag, exact member/device/boot and
selected carrier/profile context. Pin preview retains its bare plan body and
nonpersistent semantics. It does not activate hardware. Scoped writes preserve
unrelated configuration, STOP suspension and consumed-slot cursors. Consumer
profile station identity remains read-only through these controls and belongs
to transactional setup; Type 1 station-write encoding limits remain unchanged.

The supported hardware mapping is direct PIO RF GP, optional active-low button
GP and onboard/external/disabled TX indicator including external polarity.
I2C pairs can be inspected, but I2C RF, amplifier, LPF, drive, calibration and
waveform controls are unavailable. Pi displays saved versus active/null hardware,
pending restart, output inhibition, storage faults and post-commit
`output_disable_failed` separately. No scoped save restarts, reconnects WTP, enables
recurrence, claims work or transmits. No full Pi/Pico application parity is claimed.

## Acceptance boundaries

The lead record retains exact commands, versions, source pairs, failures and
repairs, independent adversarial review and final CI/remote verification.
Required software coverage includes actual UI-produced requests through protected
host routing and production runtime into engineering TLS and genuine consumer
station/AP crypto, actual journal reload, no-mutation preview/refusals, complete
schema/target/revision checks, stale contexts, uncertainty, profile/encoder
refusals, ownership and output faults. Historical legacy/extended/p152/p153
rows remain active rather than replacing accepted P15.1-P15.3 evidence.

Pico's full host suite, contract validator and affected ASan/UBSan tests are
rerun on its clean unchanged implementation: 187/187 host checks, the contract
validator and 10/10 affected sanitizers passed. All five Pi source-pair rows,
358 production runtime checks, nine actual resource carrier/state cases and
all nine instrumented resource cases passed. Final independent UI/source
reassessment found no actionable findings after repair. No firmware cross-link
is required because this slice changes no Pico implementation. No device, firmware flashing,
installed service, GPIO or RF operation is part of this software acceptance.
Consumer-Radio's group-password trust and active-endpoint offline-guessing limits
remain unchanged; this is not an unrestricted security qualification.

## Documentation Impact

Updated: this adoption/acceptance reference, development index, application
contract/API adoption pointers and Phase 15 roadmap status. Normative resource
schemas, Config/update, WTP/1, P15.1-P15.3 closures and later roadmap items are
considered unchanged. P15.5 concurrency and P15.6 independent sessions remain
separate work.

The operator documentation repository is outside write scope. P15.14 must update
Fleet setup and transmitter controls, REST member routes and context headers,
profile-owned station and Type 1 restrictions, explicit Load/Validate/Save,
saved/active/null and restart/fault feedback, carrier login/expiry and uncertain
write readback. Replace materially inaccurate desktop/mobile light/dark
screenshots after those workflows settle; do not publish interim operator docs.
