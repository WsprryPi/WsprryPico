# USB logging

The Pico exports diagnostic events on its existing Console CDC interface. WTP and USB management retain their original descriptors, framing, identities and execution authority. USB logging does not require Wi-Fi, synchronized UTC, a job owner or a fleet-controller role. The Pi collector is independent of the browser view and never submits or cancels RF jobs.

## Record and identity

`wsprry-log/1` is the common logical origin record. Pico serial messages use [RFC 5424](https://www.rfc-editor.org/rfc/rfc5424.html), facility `local7` (23), version 1, the current boot's hostname, application `WsprryPico`, NILVALUE PROCID, an event-code MSGID and NILVALUE structured data. The MSG is one ASCII JSON object. Project fields do not invent an enterprise number or an unregistered structured-data identifier.

| JSON field | Meaning |
| --- | --- |
| `schema` | `wsprry-log/1` |
| `origin_kind` | `pico` or `pi` |
| `origin_id` | Stable 32-character device identity; never the hostname |
| `origin_name` | Mutable display hostname, at most 63 ASCII characters on Pico |
| `boot_id` | 32-character origin boot/process identity |
| `sequence` | Decimal-string unsigned 64-bit origin sequence |
| `event` | Bounded event code, at most 32 characters |
| `severity` | Syslog severity 0–7; lower numbers are more severe |
| `facility` | 23 |
| `utc_ns` | Decimal-string UTC nanoseconds, or JSON null when unavailable |
| `monotonic_ns` | Decimal-string origin uptime nanoseconds |
| `dropped` | Decimal-string cumulative dropped-event count for this boot |
| `message` | Fixed diagnostic text, at most 192 ASCII characters on Pico |

Pico identity reuses the WTP device ID. Boot identity and sequence survive Console reconnects; sequence starts with the first event of a boot, advances even for filtered events, and stops admission at unsigned 64-bit exhaustion rather than wrapping. Gaps do not by themselves identify a delivery failure. Queue/rate drops are reported separately. Sequence is never a journald cursor or a timestamp.

Pi origin identity reuses the domain-separated WTP host identity derived from `/etc/machine-id`; the raw machine ID is never logged or sent to the browser. A machine replacement or regenerated machine ID changes identity. Cloning a disk without regenerating its machine ID clones identity and must be corrected before enrollment. Hostname changes only alter presentation. Native application journal records have a separately generated process-session ID and sequence; historical records and systemd service messages without origin fields retain explicitly unavailable origin metadata.

The receiving Pi adds `WSPRRY_COLLECTOR_ID`, `WSPRRY_RECEIPT_US`, `WSPRRY_INGRESS=usb` and `WSPRRY_FORWARDERS=[]`. Origin fields use `WSPRRY_ORIGIN_*`; event code and dropped count use `WSPRRY_EVENT` and `WSPRRY_DROPPED`. Journald supplies its own trusted underscore-prefixed fields, receipt timestamp and cursor. The importer does not fabricate `_HOSTNAME`, `_BOOT_ID` or `_SYSTEMD_UNIT`. USB record claims are checked against the explicitly saved device and current Console boot, but claimed identity is not cryptographic authentication.

## Console carrier

Each record is one line: `@SYSLOG <decimal-byte-count> <RFC5424-record>\n`. The count includes only the RFC message. The marker is project-specific USB serial framing; ordinary network syslog collectors cannot accept this serial stream directly. The Pi parser caps a line at 1,536 bytes and discards overlong input through the next newline before resynchronizing. It rejects invalid lengths, duplicate JSON keys, unknown fields, noncanonical decimal counters, priority/header/time inconsistencies, control characters and mismatching device/boot identity.

`SYSLOG STATUS` reads the independently versioned logger resource and revision. `SYSLOG START <device_id> <boot_id>` grants connection-local streaming permission. `SYSLOG STOP` returns to ordinary Console use. `SYSLOG SAVE <json>` accepts a closed envelope containing `revision` and `resource`, passes the resource through the same physical-USB API handler, and requires the exact current revision and target. The Pi collector uses STATUS and START; normal firmware settings use the management/browser API.

Streaming permission is never persisted. Falling DTR, unmount or reconfiguration stops the stream, clears pending Console output and resets the command parser. Reopening requires a new STATUS/START exchange. Administrative replies, including paged INFO, complete before another log record can enter the Console queue. Partial and zero physical USB writes retain the accepted record's suffix in the existing transport ring. A disconnect may truncate an in-flight record; no enqueue or write is a delivery acknowledgment.

## Pico settings and resource bounds

`GET` and `PUT /api/v1/logging` use `transmitter-logging/1`. PUT requires `If-Match` and a member target with exact device/boot identity. Its `logging` object contains only `enabled` and integer `maximum_severity` (0–7). GET returns `saved`, `active`, target and ETag. Unsupported firmware returns an error; clients must not reinterpret legacy closed configuration objects to add these settings. A missing/uncertain save reply requires authoritative readback before another save.

Default export is disabled with maximum severity 6. Settings are stored in the existing CRC-verified configuration journal under `standalone-state/4`; legacy Config and `standalone-state/3` remain readable, and unrelated station settings/schedules are preserved. Nondefault logger settings require firmware supporting state version 4. Older firmware fails closed on that state; rollback requires a compatible settings-preserving procedure, not erasing or silently choosing an earlier enabled configuration.

One core-0-owned logger has 16 fixed records, a 192-character message bound, a fixed 1,400-byte formatting workspace and a compile-time total object ceiling of 7 KiB. Event admission and record formatting allocate no heap memory. The rate ceiling is eight events per monotonic second, including faults. Filtering happens before queue admission. Overflow drops the new event and increments the dropped counter, preserving admitted FIFO order. There is no priority-dependent blocking or recursive overflow logging.

Events cover application startup, Console sessions, USB control transitions, clock-state transitions, journal commits, ownership/output changes and job state/faults. Event text is selected by the implementation; requests, configurations, credentials and proofs are not serialized. Control/non-ASCII bytes become underscores; messages are truncated before admission. HTML is escaped by the browser through `textContent`. There are no per-symbol/per-sample events, IRQ callers or RF-core logging operations.

Core 0 admits at most one whole record between complete Console replies. The USB transport still submits at most 64 Console bytes per main-loop service. Logging neither waits for a host nor changes clock discipline, schedules or accepted jobs. Disconnection clears the optional queue; early boot is not a persistent event archive. Loss counters and the new stream's boot identity describe that limitation.

## Pi collector and operator workflow

The application owns one optional collector worker, started and stopped with its runtime. Policy is stored beside the active INI as `<ini>.usb-logs.json`, under `host-usb-logging/1`, independently of Pico settings. `GET`/`PUT /api/v1/host/logging` require the host collector identity, revision and saved Fleet profile identities. There are at most eight enabled/saved source entries. Collection defaults off. Firmware must separately enable export in its own settings.

The collector resolves Console by the selected physical USB parent, serial, VID/PID and interface role 0, using the same verified metadata adapter as roles 2 and 4. It does not choose a tty by ordering. It obtains an exclusive Console handle and the shared updater lease, checks maintenance holds every worker cycle and releases Console before firmware maintenance. WTP and management remain independent. Operators turn off a source's collection before opening Console in another tool, then re-enable collection afterward.

Each device has independent framing, boot, sequence, retry and diagnostic state. Device identity changes fail closed. Re-enumeration resolves the same saved serial/physical parent again; a different device is not silently enrolled. A worker cycle admits at most 1,024 read bytes and one bounded write per source, with a 50 ms cooperative interval, a three-second identity handshake deadline and five-second reconnect spacing. The parser additionally limits each source to 16 records per host second. Duplicate/non-increasing sequences are rejected within the same observed boot.

The Pi sends imported records directly to journald from the existing application process, preserving Pico severity independently of native debug filtering. The Logs endpoint remains scoped to `wsprrypi.service`; arbitrary unit/all-system access is unavailable. Its selector chooses All sources, Local Pi or a saved/observed Pico. Source and severity have independent browser resume cursors. Journal sequence/cursor, origin sequence, origin event time and receipt time remain separate. A Pico without UTC is shown with the receipt timestamp explicitly labeled `received`.

Logs provides view pause/resume, bounded severity filtering, export of the retained normalized JSON records, collection status and an explicit saved-policy readback action. Pausing, changing a filter or closing the page does not stop collection. The view retains at most 8,000 rows/records; journal retention remains the host administrator's journald policy. Pico settings can be read/saved from the Pico's Connection section or the Pi Fleet USB controls.

## Forwarding boundary

UDP sending, listening and member-to-collector forwarding remain pending. The logical origin fields and separate collector/provenance fields are the extension boundary. Future forwarding must preserve `(origin_kind, origin_id, boot_id, sequence)` and append bounded relay identities instead of replacing origin. Duplicate suppression must include ingress trust classification; unauthenticated UDP claims must never suppress verified USB records. No UDP listener, destination, package replacement or forwarding policy is enabled by this feature.

## Review and validation record

The implementation was assessed across firmware timing/resource boundaries, identity, persistence, Console ownership, journal projection and browser recovery. The independent Impeccable reviews covered the Logs toolbar/options and both logging-setting editors at desktop/mobile sizes in light/dark themes. Twelve setting-editor captures and eight Logs captures were inspected; fixture records are synthetic and do not establish authenticated device readback.

| Finding | Severity | Repair and closure evidence |
| --- | --- | --- |
| A paused stream could leave the primary action ineffective. | Medium | Resume now explicitly clears pause; browser tests cover the primary action and online transitions. Independent re-review passed. |
| An initial cursor could be scoped before the collector identity was verified. | Medium | Resume/store requires verified identity, and a collector change restarts the stream. The production-script browser harness covers initial identity and filter isolation. Independent re-review passed. |
| A removed Fleet profile could leave saved collection impossible to disable. | Medium | Saved policies remain visible and disabling removes the policy entry. Browser tests cover removal and recovery. Independent re-review passed. |
| Pico logging controls could remain actionable after access lock/disconnection. | Medium | The incumbent controls gate now covers the editor, retires pending reads and invalidates the saved target/revision. Access/browser regressions and independent re-review passed. |
| Fleet failure recovery named unrelated settings. | Low | Recovery now identifies logging settings and requires readback. Independent re-review passed. |
| Unconfirmed START could be presented as streaming. | Medium | The collector now requires the complete START acknowledgment within its bounded handshake deadline. |
| Collector configuration could accept duplicate keys or unsafe file ownership/permissions. | Medium | Closed JSON parsing rejects duplicates; bounded private regular-file reads and atomic durable writes preserve policy authority. Deterministic checks cover persistence, stale/wrong identity, missing profiles and unsafe permissions. |
| Native/service journal scope and receipt/origin metadata could diverge. | Medium | Normalization retains distinct origin/receipt fields and checks trusted service scope, including PID-1 lifecycle messages, before source filtering. PHP tests cover normalization, injection and scope. |

The final review keeps source tests, visual fixtures, physical USB evidence and RF qualification distinct. The portable Pi semantics suite has an existing Test Tone lifecycle assertion failure reproduced on the untouched source baseline. The Mac Pico suite has an existing event-storage assertion failure reproduced on its untouched baseline; the Linux event-storage test passes. These results do not qualify RF output or transmitter timing.

The finite physical producer test used wspr5 and USB serial `1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`, with the `inhibited-standalone-simulator` engine and no RF jobs. UF2 SHA-256 was `f9011a43b50f3fe1cd95e5b5e89eb4e5e3b8bef8f2cfe17efbcf5134f9c81b76`, test boot `0e2c66c7bfa81a6c6009d2e09b45fe32`. Framing/header/sequence checks, saved logger readback, INFO coexistence, STOP and DTR restart behavior passed. Reserved settings were preserved during loading; the original full flash and public settings were restored and verified. Private backups remain on wspr5 outside source control.

End-to-end collector/journal acceptance and final source-pair publication remain open until recorded below. UDP remains pending.
