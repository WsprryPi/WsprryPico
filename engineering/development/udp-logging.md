# UDP logging implementation candidate

UDP logging is under qualification. This engineering contract accompanies the [reviewed design](udp-syslog-proposal.md); it is not runtime acceptance or operator support evidence. The combined backlog remains unfinished until all coordinated acceptance gates pass.

The implementation retains independent `wsprry-udp/1`, `transmitter-udp-logging/1`, `host-udp-logging/1` and `udp-logging-capabilities/1` resources. Existing USB logging, management descriptors, Consumer-Radio sessions and WTP command contracts retain their historical meanings. The shared portable codec and fixed event policy are mirrored in Pi and Pico source; their fixtures exercise the actual selected sources.

Pico event creation assigns one origin sequence and snapshots the cumulative origin drop count before independent USB and UDP admission. A delayed USB delivery retains that snapshot; the live USB status counter continues to report subsequent USB losses. The UDP sink has sixteen fixed records, a five-second lifetime, separate filters and token bucket, and a hard ceiling of eight submissions per monotonic second. Its core-0 station adapter owns a distinct IPv4 PCB and a bounded pool buffer. Network generation changes invalidate queued events. A submitted datagram has unknown receipt.

The dedicated Pi worker reads only the real `wsprrypi.service` journal and emits imports under its own real `wsprrypi-log.service` unit. Export requires matching local collector identity, native or verified USB ingress, selected USB profile/device binding where applicable, and producer-owned fixed export templates. Unknown native event classes and arbitrary MESSAGE bodies are excluded. UDP imports and worker diagnostics never forward. No UDP payload supplies trusted underscore-prefixed journal metadata.

The verified Pi executable embeds the separately built logging worker. Installation extracts and compares that image before installing the dedicated executable and hardened static-user service. Existing precompiled application images without the worker retain disabled UDP policies and report the feature unavailable; an enabled policy refuses such a downgrade. Installed host logging stacks and firewall rules remain unchanged. The logging user's supplementary journal group grants broad host-journal read access; it does not grant device or transmitter authority.

## Independent finite test resource

Test-event discovery is independent of settings discovery. `GET /api/v1/udp-logging/test/capabilities` on a Pico and `GET /api/v1/host/udp-logging/test/capabilities` on a Pi return the exact closed `udp-logging-test-capabilities/1` descriptor. It contains `schema`, exact settings `target`, `resource`, `request_schema`, `event_code` and `maximum_rate`. The request schema is `udp-logging-test/1`, maximum rate is two requests per second, and the event code is `UDP_TEST` on Pico or `PI_LOG` on Pi. Unknown descriptors disable testing without guessing an older diagnostic resource.

The corresponding test resource accepts only authenticated `POST` with exact `{schema,target}` and the authoritative settings If-Match revision. It checks identity, revision, idle admission where applicable, enabled export and the event/severity filter before admitting one fixed diagnostic event. It does not write settings or flash, submit a radio job, acknowledge a collector or retry automatically. Its exact reply is `{schema,target,accepted,receipt}`, with boolean local admission and receipt `unknown`. The member proxy uses the same selected-device, boot, profile, carrier and revision guards as settings. The UI offers testing only after saved-state readback and independent diagnostic discovery.

## Storage and bundles

The independent UDP settings journal occupies `[0x3ec000,0x3ee000)`, leaving existing regions fixed. Current application images end at `103ec000`. Release manifest 2 and developer bundle 2 declare storage/update contract 2 explicitly; old manifest and developer bundle 1 retain their own exact historical ends. Developer bundle 2 supports explicit normal and inhibited engines, keeps the retained image filename stable, and validates linked engine identity. The shared installer hashes the actual source inputs and retains the exact bundle and same-board reference through postboot verification.

New transactions preserve the selected layout's reserved region. Historical installer receipts retain their original NTP-inclusive preservation hash boundary. A contract-2 application cannot be replaced by an image whose application reservation expands into the UDP journal; a reviewed settings-preserving migration is required. No erase or deletion of a same-board reference substitutes for that migration.

## Evidence boundaries

Hardware-free codec, persistence, API, UI and actual production source-pair results are software evidence. Target image fit, stack/pool pressure, installer/service operation, physical USB/network transport, restoration and RF isolation require their own recorded results. The finite runtime campaign in the reviewed design remains mandatory. Failed, timed-out or skipped checks remain unresolved.

Current candidate results and unfinished physical/restoration gates are recorded in the [qualification record](udp-logging-qualification.md).
