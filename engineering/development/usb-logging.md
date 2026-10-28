# USB logging

The Pico exports diagnostic events on its dedicated Logging CDC interface (instance 3, control/data interfaces 6/7). Console remains independently available. WTP and USB management retain their original descriptors, framing, identities and execution authority. USB logging does not require Wi-Fi, synchronized UTC, a job owner or a fleet-controller role. The Pi collector is independent of the browser view and never submits or cancels RF jobs.

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

Pico identity reuses the WTP device ID. Boot identity and sequence survive Logging reconnects; sequence starts with the first event of a boot, advances even for filtered events, and stops admission at unsigned 64-bit exhaustion rather than wrapping. Gaps do not by themselves identify a delivery failure. Queue/rate drops are reported separately. Sequence is never a journald cursor or a timestamp.

Pi origin identity reuses the domain-separated WTP host identity derived from `/etc/machine-id`; the raw machine ID is never logged or sent to the browser. A machine replacement or regenerated machine ID changes identity. Cloning a disk without regenerating its machine ID clones identity and must be corrected before enrollment. Hostname changes only alter presentation. Native application journal records have a separately generated process-session ID and sequence; historical records and systemd service messages without origin fields retain explicitly unavailable origin metadata.

The receiving Pi adds `WSPRRY_COLLECTOR_ID`, `WSPRRY_RECEIPT_US`, `WSPRRY_INGRESS=usb` and `WSPRRY_FORWARDERS=[]`. Origin fields use `WSPRRY_ORIGIN_*`; event code and dropped count use `WSPRRY_EVENT` and `WSPRRY_DROPPED`. Journald supplies its own trusted underscore-prefixed fields, receipt timestamp and cursor. The importer does not fabricate `_HOSTNAME`, `_BOOT_ID` or `_SYSTEMD_UNIT`. USB record claims are checked against the explicitly saved device and current Logging boot, but claimed identity is not cryptographic authentication.

## Dedicated USB carrier

Each record is one line: `@SYSLOG <decimal-byte-count> <RFC5424-record>\n`. The count includes only the RFC message. The marker is project-specific USB serial framing; ordinary network syslog collectors cannot accept this serial stream directly. The Pi parser caps a line at 1,536 bytes and discards overlong input through the next newline before resynchronizing. It rejects invalid lengths, duplicate JSON keys, unknown fields, noncanonical decimal counters, priority/header/time inconsistencies, control characters and mismatching device/boot identity.

The dedicated port uses the closed `usb-logging/1` carrier. `SYSLOG STATUS` returns exactly `schema`, `target` and `active`; target contains exactly `device_id` and `boot_id`. Active contains exactly `enabled`, `maximum_severity` (0–7), `streaming`, `connected`, `queued` (0–16) and decimal-string `dropped`. A connected status must report `connected:true`. The collector rejects unknown versions, fields, types, changed bounds, duplicate keys and mismatched identities before START. This carrier is independent of the unchanged `transmitter-logging/1` settings resource and `wsprry-log/1` event model.

`SYSLOG START <device_id> <boot_id>` grants connection-local streaming permission. Its acknowledgment contains exactly `schema`, the same `target` and `streaming:true`. `SYSLOG STOP` stops streaming and returns the same shape with `streaming:false`. Other commands, invalid target bindings, control characters and overlong command lines are refused. Logging accepts at most 128 command bytes and reads at most 64 bytes per service iteration. It has no configuration-write commands. Console retains `SYSLOG STATUS` and revision/target-guarded `SYSLOG SAVE` administration; Console START/STOP are refused with `use_logging_port`.

Streaming permission is never persisted. Falling Logging DTR stops the stream, clears pending Logging output and resets only Logging's command parser. Whole-device unmount or reconfiguration resets all four sessions. Reopening requires a new STATUS/START exchange. Complete handshake replies and records enter an independent 2,048-byte ring atomically; physical short/zero writes retain their suffix. No accepted line is interleaved with another line. A disconnect may truncate an in-flight line; no enqueue or write is a delivery acknowledgment. Console commands, partial lines, INFO output and individual Console close/open transitions do not affect the stream. Physical disconnect, bus reset, firmware maintenance and reboot affect the shared USB device.

## Pico settings and resource bounds

`GET` and `PUT /api/v1/logging` use `transmitter-logging/1`. PUT requires `If-Match` and a member target with exact device/boot identity. Its `logging` object contains only `enabled` and integer `maximum_severity` (0–7). GET returns `saved`, `active`, target and ETag. Unsupported firmware returns an error; clients must not reinterpret legacy closed configuration objects to add these settings. A missing/uncertain save reply requires authoritative readback before another save.

Default export is disabled with maximum severity 6. Settings are stored in the existing CRC-verified configuration journal under `standalone-state/4`; legacy Config and `standalone-state/3` remain readable, and unrelated station settings/schedules are preserved. Nondefault logger settings require firmware supporting state version 4. Older firmware fails closed on that state; rollback requires a compatible settings-preserving procedure, not erasing or silently choosing an earlier enabled configuration.

One core-0-owned logger has 16 fixed records, a 192-character message bound, a fixed 1,400-byte formatting workspace and a compile-time total object ceiling of 7 KiB. Event admission and record formatting allocate no heap memory. The rate ceiling is eight events per monotonic second, including faults. Filtering happens before queue admission. Overflow drops the new event and increments the dropped counter, preserving admitted FIFO order. There is no priority-dependent blocking or recursive overflow logging.

Events cover application startup, Logging sessions, USB control transitions, clock-state transitions, journal commits, ownership/output changes and job state/faults. Event text is selected by the implementation; requests, configurations, credentials and proofs are not serialized. Control/non-ASCII bytes become underscores; messages are truncated before admission. HTML is escaped by the browser through `textContent`. There are no per-symbol/per-sample events, IRQ callers or RF-core logging operations.

Core 0 admits at most one whole reply or record per Logging poll. The USB transport submits at most 64 bytes per connected function per main-loop service. Logging neither waits for a host nor changes clock discipline, schedules or accepted jobs. Disconnection clears the optional queue; early boot is not a persistent event archive. Loss counters and the new stream's boot identity describe that limitation.

## Pi collector and operator workflow

The application owns one optional collector worker, started and stopped with its runtime. Policy is stored beside the active INI as `<ini>.usb-logs.json`, under `host-usb-logging/1`, independently of Pico settings. `GET`/`PUT /api/v1/host/logging` require the host collector identity, revision and saved Fleet profile identities. There are at most eight enabled/saved source entries. Collection defaults off. Firmware must separately enable export in its own settings.

The collector resolves Logging by the selected physical USB parent, serial, VID/PID and interface role 6, using the same verified metadata adapter as roles 2 and 4. It does not choose a tty by ordering. It obtains an exclusive Logging handle and the shared updater lease, checks maintenance holds every worker cycle and releases Logging before firmware maintenance. Console, WTP and Management remain independently usable during collection. Firmware without role 6 reports `dedicated_logging_unsupported`; upgrade that Pico to collect logs. The collector never probes or collects through Console.

Each device has independent framing, boot, sequence, retry and diagnostic state. Device identity changes fail closed. Re-enumeration resolves the same saved serial/physical parent again; a different device is not silently enrolled. A worker cycle admits at most 1,024 read bytes and one bounded write per source, with a 50 ms cooperative interval, a three-second identity/status deadline, five-second saved/active status refresh and five-second reconnect spacing. The parser additionally limits each source to 16 records per host second. Duplicate/non-increasing sequences are rejected within the same observed boot.

The Pi sends imported records directly to journald from the existing application process, preserving Pico severity independently of native debug filtering. The original Logs endpoint remains scoped to `wsprrypi.service`; arbitrary unit/all-system access is unavailable. Its selector chooses All sources, Local Pi or an attached, saved or previously observed Pico. Read-only USB descriptors supply the established serial-derived identity for attached-source filtering without opening Console or granting collection authority. Collection still requires a saved USB Fleet profile and a matching live STATUS identity; a descriptor claim alone never enrolls collection. Source and severity have independent browser resume cursors. Journal sequence/cursor, origin sequence, origin event time and receipt time remain separate. A Pico without UTC is shown with the receipt timestamp explicitly labeled `received`.

Logs provides view pause/resume, bounded severity filtering, export of the retained normalized JSON records, collection status and an explicit saved-policy readback action. Pausing, changing a filter or closing the page does not stop collection. The view retains at most 8,000 rows/records; journal retention remains the host administrator's journald policy. Pico settings can be read/saved from the Pico's Connection section or the Pi Fleet USB controls.

## Forwarding boundary

The independent [UDP logging contract](udp-logging.md) defines sending, listening and selected USB forwarding without changing this closed USB wire contract. Forwarding preserves `(origin_kind, origin_id, boot_id, sequence)` and adds exactly one relay observation. Duplicate suppression includes ingress trust classification; unauthenticated UDP claims cannot suppress verified USB records. Logs stream version 2 adds the separately trusted logging unit while preserving the original endpoint. Enabling USB logging alone does not enable a UDP listener, destination or forwarding policy.

## USB resource budget and validation

The four CDC functions have eight interfaces, four associations and twelve endpoint descriptors. Existing notification/OUT/IN assignments remain Console `81/02/82`, WTP `83/04/84` and Management `85/06/86`; Logging appends `87/08/88`. The pinned RP2350 TinyUSB driver allocates a 64-byte notification buffer and two double-buffered 64-byte bulk endpoints per function: 320 bytes per function, 1,280 bytes for four functions, within the 3,712-byte endpoint data area after fixed control structures/buffers. Each function also has independent 64-byte software RX/TX FIFOs and 64-byte transfer buffers. Logging adds the 2,048-byte application output ring and its bounded session state; the existing 16-record logger budget is unchanged.

Descriptor expansion tests check exact old and new endpoint identities. Transport tests exercise four concurrent functions, independent reads, short/zero writes, saturation, DTR and whole-device resets. The production Logging session and Pi handshake validators cover target/version/type/bounds errors, reply-before-record serialization and reconnect negotiation. Required Pi network and USB management integration fixtures use explicitly selected matching candidate sources. These hardware-free checks remain distinct from physical simultaneous-operation evidence and RF qualification.

## Validation bounds

Original USB-channel qualification used WsprryPico `73e879b380b3ef62d66a8423a9f09e1923616686` and WsprryPi `bcc6f501047c441d7031fd4333a4ea59e0d50c2a`, with operator documentation `575ff6b85178caf795e451443257079e04cd627f` in WsprryPi-Docs. The implementation and subsequent Console STATUS and logger shutdown fixes are integrated into `devel`; the completed feature branches are retired after merging. The evidence below remains bound to its recorded source pair and does not imply a release or RF qualification.

The [Pico firmware/software workflow](https://github.com/WsprryPi/WsprryPico/actions/runs/40551111013) passed for that Pico revision. The [Pi non-hardware workflow](https://github.com/WsprryPi/WsprryPi/actions/runs/40551129506) passed all seven jobs for that exact source pair, including `wtp-network-loopback` and `wtp-usb-management-pair`. The workflow records the pinned SDK, TLS dependencies and actual selected Pico revision. Linux host testing passed all 133 Pico tests; the separate actual Pi network-runtime fixture passed 910 checks. Firmware and inhibited-firmware builds and target audits passed. The linked ARM Logging session occupies 284 bytes and the logger 5,616 bytes; these are separate from the ring and USB buffers described above.

Physical USB testing on wspr5 used the production Pi collector and three Pico 2 W devices with serials `1545B6EFBF78028C`, `0BF4B4AEC9FFB344` and `CDDBF8767C506C07`. Each ran the clean Pico revision above with `pio-dma-gp2`, a 138 MHz system clock, no active mode and output inactive. The programmed UF2 SHA-256 is `f008279dfa5369df10565e1a24e15817d8f59aa109ba9fcc9b34d07032e2ded3`. Serial and physical USB-parent identity were verified before programming; full flash recovery images were retained privately and settings/persistent data were preserved. No RF jobs were submitted.

The Pi collector simultaneously held Logging handles for all three Picos without holding their Console handles. On every board, Console INFO, five actual read-only WTP operations and Management reads succeeded during collection, and origin-scoped records reached the real service journal. The first device additionally passed nine lifecycle/stress checks: four-function concurrency, Console reopen and command isolation, Logging DTR restart with the collector descriptor held, maintenance handle/lease release, malformed/overlong input, stalled-reader pressure, guarded BOOTSEL re-enumeration, post-reboot Console use and journal identity projection. The final pressure run admitted 26 valid records and reported 57 dropped events while Console remained responsive; this demonstrates bounded loss, not lossless delivery.

The deployed Pi binary SHA-256 is `3c2cc2439fdf2c914bb5564ac2901d7bab57d6cfd3d3a938860b91135fc06305`. Its original `rpi-gpio,rp1-gpclk,si5351,simulated,wtp` backends and ancillary GPIO support were preserved. The service remained active; native INI, Fleet catalog/assignments and collector policy were preserved byte-for-byte. Private deployment, flash and test evidence is retained under `/home/pi/usb-channel-20261027/private` on wspr5; it is not included in source control.

Repeated adversarial assessments identified and closed a stopped-stream recovery error, missing discovery cases and command-framing/documentation inconsistencies. The affected checks were rerun; final review found no remaining material implementation issue. Browser regression checks covered desktop/mobile and light/dark states; strict documentation builds and local-link checks passed.

Validation limits remain explicit. Physical four-function enumeration was tested on Linux, not Windows or macOS. A macOS `event_storage_tests` assertion was reproduced on the untouched baseline; the other 131 selected macOS tests passed, and Linux passed the complete suite. The original source pair returned `profile_runtime_unavailable` for Console STATUS on this saved setup and could retain the Pi `--version` process during logger exit. Follow-up fixes permit read-only Console STATUS before profile-dependent control admission and synchronize the logger shutdown predicate with both worker mutexes. The original run used bounded probes that were killed and reaped; its active service validation passed. Timing, RF output, Windows/macOS physical USB, and release installation are not qualified by these tests.
