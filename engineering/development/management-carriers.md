# Management carriers

Job transport and JSON administration have separate authority. WTP carries
complete jobs to one JobService; management configuration uses the shared
validators, target/revision checks and journals. Neither negotiated management
nor a successful login grants transmitter ownership.

## Carrier and profile policy

| Carrier | JSON authority | Conditions and boundaries |
| --- | --- | --- |
| Engineering station HTTPS | TLS 1.3 client-certificate principal | Exact certified Host/Origin, configured listener and usable UTC; shared resources and idle/health gates |
| Engineering field HTTPS | Server TLS plus AP-scoped password/cookie session | Provisioned field allowlist; blank/preclock Configure denied; hostname and GET config unavailable; no selected Pi field-cookie client |
| Consumer station/AP HTTP | Saved Wi-Fi-password Consumer-Radio/1 encrypted session | Actual interface, exact authority, device/boot/profile generation; association+IPv4 suffice for management; job UTC policy is independent |
| USB management/time CDC | Internal `usb_physical` local authority | No Wi-Fi/password/UTC prerequisite for negotiation and ordinary saves; UMP1 boot/session/target binding, revision and matching response ACK |
| Plain LAN WTP / consumer TLS-WTP | No JSON administration | Complete WTP jobs only; management requires an independently selected carrier |
| BLE WTP | No shared JSON administration | Engineering Field-GATT/password/session policy; dedicated provisioning commands stay outside WTP/1 |

Normal and explicitly inhibited consumer/engineering application variants admit
USB WTP and the separate management/time CDC. Console, WTP and UMP1 framing
remain separate; USB connectivity alone does not negotiate a JSON capability.
Consumer public setup mutations are AP-only. Authenticated LAN setup uses the
same transactional profile authority through the encrypted wrapper. Raw station
HTTP never acquires public AP mutation authority.

Consumer sessions use three fixed slots and at most one pending ordinary login; full capacity refuses without eviction. Pending login has a 30-second deadline, active sessions retain thirty-minute idle/eight-hour absolute limits, and the separate [recovery exchange](session-recovery.md) has a five-second proof workspace. Two bounded port-80 tasks service requests cooperatively. Slot, transport and memory capacities are independent; they do not promise simultaneous maximum-size allocation. HTTP page delivery remains unauthenticated.

## Discovery and versioning

`Wsprry-Control/1` uses `/api/control/v1` for every admitted management
carrier. A stable `management` resource describes the selected carrier,
profile, availability and bounded policy data. USB and network use the same
shape; historical management generations and resource-view selection are
unsupported. Authentication, selected-carrier and device/boot/profile bindings
remain mandatory. Policy values are validated by type, bounds and relationships;
unsupported context refuses before writes, with no carrier fallback.

The [control contract](../browser-api.md) governs current resource types.
[USB management/time](../protocol/USB-Management.md) and
[Consumer-Radio/1](../protocol/Consumer-Radio-v1.md) retain their independently
framed/authenticated envelopes and unchanged delivery authority.

## Mutation, delivery and refusal

All control mutations require root `contract:"Wsprry-Control/1"` and retain exact target/revision, full validation, verified journal
selection, STOP/cursors, member-owned recurrence and saved/boot/restart
semantics. Unknown, unsafe, owned, faulted or storage-ambiguous contexts refuse.
Changed hardware remains inhibited until explicit restart, including A/B/A saves.
Public discovery supplies hints and no authenticated principal.

Deferred network/restart effects require the exact complete-response delivery
receipt: TCP acknowledgement for HTTP or the matching resource ACK for UMP1.
Lost delivery cancels undelivered effects, not accepted jobs or durable saves.
Read authoritative saved/active state and review before another explicit save;
never retry an uncertain mutation automatically. Physical USB identity is not
cryptographic device authentication. Source/host tests establish no general
physical USB, peer/fleet, timing or RF qualification.
