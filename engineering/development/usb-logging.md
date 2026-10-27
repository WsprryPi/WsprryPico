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

Each device has independent framing, boot, sequence, retry and diagnostic state. Device identity changes fail closed. Re-enumeration resolves the same saved serial/physical parent again; a different device is not silently enrolled. A worker cycle admits at most 1,024 read bytes and one bounded write per source, with a 50 ms cooperative interval, a three-second identity/status deadline, five-second saved/active status refresh and five-second reconnect spacing. The parser additionally limits each source to 16 records per host second. Duplicate/non-increasing sequences are rejected within the same observed boot.

The Pi sends imported records directly to journald from the existing application process, preserving Pico severity independently of native debug filtering. The Logs endpoint remains scoped to `wsprrypi.service`; arbitrary unit/all-system access is unavailable. Its selector chooses All sources, Local Pi or an attached, saved or previously observed Pico. Read-only USB descriptors supply the established serial-derived identity for attached-source filtering without opening Console or granting collection authority. Collection still requires a saved USB Fleet profile and a matching live STATUS identity; a descriptor claim alone never enrolls collection. Source and severity have independent browser resume cursors. Journal sequence/cursor, origin sequence, origin event time and receipt time remain separate. A Pico without UTC is shown with the receipt timestamp explicitly labeled `received`.

Logs provides view pause/resume, bounded severity filtering, export of the retained normalized JSON records, collection status and an explicit saved-policy readback action. Pausing, changing a filter or closing the page does not stop collection. The view retains at most 8,000 rows/records; journal retention remains the host administrator's journald policy. Pico settings can be read/saved from the Pico's Connection section or the Pi Fleet USB controls.

## Forwarding boundary

UDP sending, listening and member-to-collector forwarding remain pending. The logical origin fields and separate collector/provenance fields are the extension boundary. Future forwarding must preserve `(origin_kind, origin_id, boot_id, sequence)` and append bounded relay identities instead of replacing origin. Duplicate suppression must include ingress trust classification; unauthenticated UDP claims must never suppress verified USB records. No UDP listener, destination, package replacement or forwarding policy is enabled by this feature.

## Review and validation record

The implementation was assessed across firmware timing/resource boundaries, identity, persistence, Console ownership, journal projection and browser recovery. The independent Impeccable reviews covered the Logs toolbar/options and both logging-setting editors at desktop/mobile sizes in light/dark themes. Twelve setting-editor captures and twelve Logs/options/attached-source captures were inspected; fixture records are synthetic and do not establish authenticated device readback.

| Finding | Severity | Repair and closure evidence |
| --- | --- | --- |
| A paused stream could leave the primary action ineffective. | Medium | Resume now explicitly clears pause; browser tests cover the primary action and online transitions. Independent re-review passed. |
| An initial cursor could be scoped before the collector identity was verified. | Medium | Resume/store requires verified identity, and a collector change restarts the stream. The production-script browser harness covers initial identity and filter isolation. Independent re-review passed. |
| A removed Fleet profile could leave saved collection impossible to disable. | Medium | Saved policies remain visible and disabling removes the policy entry. Browser tests cover removal and recovery. Independent re-review passed. |
| Pico logging controls could remain actionable after access lock/disconnection. | Medium | The incumbent controls gate now covers the editor, retires pending reads and invalidates the saved target/revision. Access/browser regressions and independent re-review passed. |
| Fleet failure recovery named unrelated settings. | Low | Recovery now identifies logging settings and requires readback. Independent re-review passed. |
| Unconfirmed START or changed firmware export settings could leave misleading collector status. | Medium | The collector requires the complete START acknowledgment and refreshes target-bound active status every five seconds with a three-second reply deadline. |
| Collector configuration could accept duplicate keys or unsafe file ownership/permissions. | Medium | Closed JSON parsing rejects duplicates; bounded private regular-file reads and atomic durable writes preserve policy authority. Deterministic checks cover persistence, stale/wrong identity, missing profiles and unsafe permissions. |
| Missing HTTP route classification blocked the new resources at the backend guard. | High | Both exact logging paths now use the protected GET/PUT class. Network/origin tests reject off-LAN and cross-origin requests; a real HTTP test distinguishes available routing from an unstarted collector. |
| Pi rejected the Pico's existing version-4/5 management contracts. | High | The same USB pair failure was reproduced on untouched Pi baseline `5bc24e893646140d44f0bf9a20d61115d0eadda9`; the Pico management header was unchanged by logging. Published compatibility commits `88aaf83c56092ea8a5f5e9bd7c97c346677be6eb` and `014e0b96cdf9c2a17106692541d3a7b48e1fbe5f` were incorporated with provenance, preserving closed versioned validation and negotiated idle deadlines. |
| Quiet-tail resume replayed existing records because zero new rows was treated as cursor loss. | Medium | An exact, scoped, non-emitting cursor probe distinguishes a retained tail from rotation. The installed Apache regression verifies no duplicate replay and recovery for an invalid cursor. |
| CI policy tests incorrectly depended on production USB startup and the runner machine ID. | Medium | An explicit typed policy-only fixture uses a synthetic identity and cannot inventory or open USB; the production hardware guard stays intact. Both Mac and Linux checks run with hardware access disabled. |
| Native/service journal scope and receipt/origin metadata could diverge. | Medium | Normalization retains distinct origin/receipt fields and checks trusted service scope, including PID-1 lifecycle messages, before source filtering. PHP tests cover normalization, injection and scope. |

The final review keeps source tests, visual fixtures, physical USB evidence and RF qualification distinct. The portable Pi semantics suite has an existing Test Tone lifecycle assertion failure reproduced on the untouched source baseline. The Mac Pico suite has an existing event-storage assertion failure reproduced on its untouched baseline; the Linux event-storage test passes. These results do not qualify RF output or transmitter timing.

The finite physical producer test used wspr5 and USB serial `1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`, with the `inhibited-standalone-simulator` engine and no RF jobs. UF2 SHA-256 was `f9011a43b50f3fe1cd95e5b5e89eb4e5e3b8bef8f2cfe17efbcf5134f9c81b76`, test boot `0e2c66c7bfa81a6c6009d2e09b45fe32`. Framing/header/sequence checks, saved logger readback, INFO coexistence, STOP and DTR restart behavior passed. Reserved settings were preserved during loading; the original full flash and public settings were restored and verified. Private backups remain on wspr5 outside source control.

## Accepted USB validation on 2026-10-27

The coordinated USB workflow passed finite acceptance on wspr5 (Debian 13, ARM64). The second physical campaign used Pico 2 W serial `1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`, firmware source `4580eec5922ca5deb1ab7bfbed8c03efc05829bf`, the `inhibited-standalone-simulator` engine, observed system clock 150,000,000 Hz, mode none and zero RF jobs. UF2 SHA-256 was `f8f1efdf2b8a04c2900b29334c5cf02fb71436ac7be712e69f3774b882ba1596`; initial test boot was `d1cf7215f2d6a35a202412f56a659490`, and the guarded bootloader/re-enumeration check returned boot `85cd43f7d22ce730a630a6924b1bc902`. This inhibited-build clock is evidence of this test only, not the production RF sample-clock contract.

The real collector acknowledged the Console stream and projected Pico origin, severity, sequence, ingress and collector metadata under trusted `wsprrypi.service` journal scope. A second attached legacy board independently reported unsupported firmware while the new sender continued. Management resource reads and logging enable/disable saves coexisted with collection. Firmware status refreshed without reopening Console. Maintenance released Console, DTR reset required a new START, and bootloader re-enumeration acquired the same physical board with a new boot identity. Saved policy disablement/readback and catalog/policy restoration passed.

Installed Apache SSE checks covered All, Local Pi and a selected Pico, preserved origin metadata, ignored attempts to broaden the unit filter and retained source isolation on resume. The initial test expectation incorrectly excluded legitimate PID-1 lifecycle records in `init.scope`; that expectation was corrected and the campaign rerun. A subsequent read-only regression identified and repaired redundant quiet-tail replay. The final installed adapter passes retained-cursor/no-duplicate, invalid-cursor recovery and request-child cleanup checks. Disconnect cleanup completed in approximately eight seconds and descendants remained absent for the additional two-second observation.

The campaign restored and verified the original complete 4 MiB flash, including saved settings; pre-campaign flash SHA-256 was `e3eacf548382a6204532ee9af9556f52104bb6d066ab92a5fb61d76b83fdf4aa`. The selected board again runs its original `9884fe6ef8c0` application. The other two boards were not flashed. The test-only Fleet catalog and collection policy were restored exactly. All three attached Picos remain selectable by stable identity, while collection is disabled by default. Compatible firmware and an explicit USB Fleet profile are required before enabling collection.

| Check | Result |
| --- | --- |
| Pico Linux host CTest | 132 passed in the full 133-test run; the omitted new browser-test file was copied and that test passed separately. No remaining Linux host-test failure. |
| Pico Mac affected tests | Logging, network browser and access-control checks: 5/5 passed. The unrelated full-suite event-storage failure was reproduced on the untouched Mac baseline. |
| Pico linked firmware | Inhibited and production RF images cross-built with existing pinned SDK/toolchain; linked-image audits passed. Physical validation used only the inhibited image. |
| Firmware CI | [Supported pull-request verification](https://github.com/WsprryPi/WsprryPico/actions/runs/40500939077) passed at source `4580eec5922ca5deb1ab7bfbed8c03efc05829bf`. A feature-branch manual dispatch was correctly rejected by the existing input policy; publication stayed disabled. |
| Pi parser/policy | Bounded framing, wrong identities/boots, duplicate keys, injection, 64-bit limits, oversized severities, catalog admission, private persistence and revisions passed. The final isolated policy fixture also runs with `WSPRRYPI_DISABLE_HARDWARE_ACCESS=1`. |
| Pi HTTP integration | Network/origin guards passed; real protected-route/runtime validation passed 878 production WTP checks on Linux. Earlier focused USB checks passed 2,789 assertions. The final published compatibility adapter passed closed configuration/session-policy checks and the actual UI/Pi/Pico USB producer test, including settings, progress, revisions, UMP framing and ACKs. |
| UI behavior | Full PHP/JavaScript unit suite passed on Linux; production browser harness passed source/cursor isolation, pause/resume, policy recovery, attached-source non-enrollment, injection and zero-height routine-caption checks. |
| Visual review | Independent Impeccable reviews passed desktop/mobile light/dark Logs, options and settings states; default caption removal and unsaved attached-source guidance were separately reviewed. Captures are synthetic presentation fixtures. |
| Installed service and UI | wspr5 service/API, imported journal records, scoped Apache replay/follow and child cleanup passed. Native INI and all five disabled Fleet assignments were preserved. |
| Documentation | Both strict Sphinx builds passed; Pico local-target checks found zero errors. Operator material remains in Read the Docs sources. |

The portable Pi semantics suite still has the independently reproduced baseline Test Tone lifecycle assertion described above; it is not a passing full semantics result. Pi CI initially exposed an abbreviated cross-repository checkout ref and a policy test that depended on hardware startup. The checkout is rerun with the full Pico commit and the policy test now has an explicit USB-inhibited fixture. Final CI status and published source/deployment identities are recorded in the source-pair section below. These checks do not qualify physical RF timing, frequency accuracy, electrical behavior or release readiness. UDP proposal and implementation remain pending.


## Published source pair and deployment

All three repositories use the pushed `codex/usb-syslog` branch. Pico implementation source is `4580eec5922ca5deb1ab7bfbed8c03efc05829bf`; later Pico commits record acceptance only. Pi application/UI source is `539bc9d428a4eeb46d0ae3306305bc8c791dc974`. Operator documentation is `446da8a12f6412d0069e7a4c8cb53aa0ac5dd31d`. Pico's [draft review PR](https://github.com/WsprryPi/WsprryPico/pull/1) retains the implementation and verification history. No release, tag, merge or asset publication was performed.

The physical collector campaign ran the Pi implementation at `55c5efc26a4596a101fdaeaec74f2271f8f11cf1` with Pico source `4580eec5922ca5deb1ab7bfbed8c03efc05829bf`. Subsequent Pi changes removed the requested routine caption, fixed PHP cursor replay, isolated policy tests and integrated the published versioned-management compatibility commits; the default production collector behavior is preserved by the test-only isolation change. The final source was built and installed on wspr5 with `BACKENDS=rp1-gpclk,simulated ANCILLARY_GPIO=0`, preserving the installed RP1 backend selection. Installed stripped executable SHA-256 is `2bfd3c67795c40f52ffb8c6722355a818ff1cc0d76ace0842288444809cafc0f`; the UI manifest build ID is `sha256:5f55b70f42b94b93f96349f3d466e422e91c9dc42d305d95b384dce055fb5a49`. The service is active, native INI and Fleet assignments are unchanged, all saved assignments remain disabled and collection policy is empty. Three attached Pico identities appear in Source. Original Pico firmware/settings were restored; enabling live export requires an intentionally installed compatible image.

The first targeted update was rejected by the installed 64 MiB executable-read guard because an 86 MiB unstripped debug image was supplied. Automatic rollback restored the original running binary. A stripped approximately 9 MiB deployment image passed the same guard; the guard was not weakened. The final targeted update was verified and `/home/pi/finished` was created only after success. Private rollback material and finite-test evidence remain in `/home/pi/usb-syslog-validation-20261027/private`, outside source control.

The Pi checkout used for implementation is `/private/tmp/wsprrypi-shared-frequency-contract`; the older `/Users/lbussy/GitHub/WsprryPi` main checkout was left unchanged. The current Pi development tree owns `WsprryPi-UI` and `src/LCBLog` as ordinary directories, so there are no component submodule commits or parent gitlinks to publish. UI and LCBLog were reviewed as component boundaries and compiled/tested through their parent entry points. Local root `.impeccable/` captures remain untracked and excluded from commits. The Docs branch preserves the user's unrelated unpushed `codex/shared-frequency-contract` commit `48eeb80f33e96a08cb37d873eae5725700ba60d8` without including it in this feature branch.

Final Pi CI is [run 40505605841](https://github.com/WsprryPi/WsprryPi/actions/runs/40505605841), using Pi source `539bc9d428a4eeb46d0ae3306305bc8c791dc974` and full Pico source `4580eec5922ca5deb1ab7bfbed8c03efc05829bf`. Its actual UI/Pi/Pico USB management pair and strict I2C profile passed. The broader Linux release, macOS simulated, Debian hardware-free and TLS/network jobs were still running when this record was saved; their success is not claimed. No further device work is pending. USB implementation and bounded runtime acceptance are complete; final full-CI disposition remains the open combined-backlog gate.
