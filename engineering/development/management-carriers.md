# Management carriers

Job transport and JSON administration have separate authority. WTP carries
complete jobs to one JobService; management configuration uses the shared
validators, target/revision checks and journals. Neither negotiated management
nor a successful login grants transmitter ownership.

## Carrier and profile policy

| Carrier | JSON authority | Conditions and boundaries |
| --- | --- | --- |
| Engineering station HTTPS | TLS 1.3 client-certificate principal | Exact certified Host/Origin, configured listener and usable UTC; shared resources and idle/health gates |
| Engineering field HTTPS | Server TLS plus AP-scoped password/cookie session | Provisioned field allowlist; blank/preclock Configure denied; hostname and GET config/2 unavailable; no selected Pi field-cookie client |
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

Network discovery is closed `transmitter-management/4`; USB selects /5 and advertises the physical carrier. These preserve the /2 network and /3 USB shapes respectively, with only `idle_ms:1800000` and `absolute_ms:28800000` changed. Historical /1, /2 and /3 remain frozen at five minutes idle and fifteen minutes absolute; /1 has one consumer session, while /2 and /3 have three sessions and one pending login. Updated Pi clients validate each supported version exactly and select local deadlines only from authenticated discovery. Older clients explicitly refuse /4 and /5; there is no fallback. A legacy network view's `usb_json_management` exclusion does not claim that current UMP1 firmware lacks USB management. Clients accept only exact supported descriptors, schema/route tuples, limits and selected target bindings. Unknown versions refuse without a hidden downgrade or carrier substitution.

Resource schemas are independent of the `/api/v1/` namespace. Application,
station, hardware, GPIO drive, amplifier and saved-progress extensions use their
explicit capability descriptors; old closed shapes remain unchanged. See the
[current API resource inventory](../browser-api.md#resources),
[USB management/time](../protocol/USB-Management.md),
[USB local configuration](usb-local-configuration.md) and
[Consumer-Radio/1](../protocol/Consumer-Radio-v1.md).

## Mutation, delivery and refusal

All writes retain exact target/revision, full validation, verified journal
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
