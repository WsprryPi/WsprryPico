# Shared transmitter application

`Wsprry-Control/1` exposes one current application, station and hardware
representation under `/api/control/v1`. The [control contract](../browser-api.md)
and [resource schema](../protocol/control-1.schema.json) are authoritative.
No historical projection or per-resource generation is negotiated.

Application state binds the selected member device/boot and composes station,
hardware, recurrence, capabilities and WSPR planning observations. Station
supports current Type 1/2/3 planning. Hardware includes amplifier-enable pin and
polarity, drive strength and distinct saved versus boot-active observations.
Filter and amplifier timing remain authoritative domain resources. An aggregate
view does not transfer ownership of separate journals or profile transactions.

WsprryPi's general member coordinator consumes the current representation,
including amplifier-enabled plans. It validates targets, complete pin roles,
GPIO exclusivity, returned capabilities and current revisions before writes.
USB and supported authenticated network carriers use the same model through
their existing production adapters. Native Pi GPIO controls remain separate.

Ordinary updates preserve omissions and commit only complete validated
configuration candidates. Saved drafts remain independently non-runnable until
explicit application. Pending restart, nullable readback, unknown output and
storage faults remain explicit. Pin, drive, amplifier and selector changes
retain boot activation and A/B/A restart latching.

Settings authority never grants transmitter ownership. WTP/1 and the local
JobService retain complete-job admission, ownership, execution and cleanup.
Software pair tests do not establish physical GPIO, installation, timing or RF
qualification. Full fleet/application parity remains bounded by the implemented
capabilities in the [fleet contract](../transmitter-application-contract.md).
