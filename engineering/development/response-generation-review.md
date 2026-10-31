# Bounded-response adversarial assessment

Reviewed 2026-10-31. Scope covers the HTTP/USB response generation implementation,
consumer encryption, owned snapshots, resource admission, retry and ACK authority,
measurement probes and the previously blocked Pi browser-fixture sequence.

## Findings and corrections

| Finding | Impact | Correction and regression evidence |
| --- | --- | --- |
| P2: serialization helpers made no progress after a source failure | `body_text` and `wire` looped forever when a source returned zero before its advertised length; replaying a consumed large cipher reproduced this in a three-second timeout. | Both return an empty failure result, never a partial document. Tests cover an intentionally truncated source and the actual consumed cipher. |
| P2: short LOAD replies paid fixed generator overhead | The zero-adjustment HTTP fixture rose from 388 to 3,360 peak allocation bytes; encrypted HTTP rose from 476 to 4,184 and USB from 1,389 to 5,664. | The shared production response selector retains the original materialized path through 32 adjustments. Expanded probes confirm the original small-response peaks and unchanged large-response savings. Byte comparisons cover 0, 1, 16, 32, 33, 162, 256 and 512 adjustments. |
| P2: browser fixtures assumed the startup tab had navigated | The supplemental USB test attached to `about:blank`; application globals were absent and the rest of the sequence could not run. | All four affected fixtures now deliberately start blank and explicitly navigate their owned target. Startup navigation and ordinary CDP commands have bounded deadlines. USB, network, Fleet and recovery fixtures passed without weakening application assertions. |
| P2: logging source-list warnings were lost during asynchronous refresh | The complete workflow exposed an intermittent overflow-label failure: `refreshSources` rebuilt the bounded picker, then collection-status readback erased its warning. The duplicate-origin warning shared that lifetime bug. | Overflow and duplicate-origin states survive status refresh, reset with peer/collector bindings, and stale collector menu entries are discarded. A deterministic refresh-order test covers the full list, collector replacement, duplicate-origin readback and peer removal without losing current All sources history. Existing body-text color makes the warning readable in both themes. |

### Small-response regression removed

Peak requested allocation bytes for zero-adjustment fixtures:

| Carrier | Published implementation | Reviewed fix | Saved |
| --- | ---: | ---: | ---: |
| HTTP | 3,360 | 388 | 2,972 |
| Encrypted HTTP | 4,184 | 476 | 3,708 |
| USB management | 5,664 | 1,389 | 4,275 |

The initial reproduction used three runs with identical allocation counts; the
final expanded comparison used 21 runs. These figures are host response-path
allocations, excluding preexisting job storage and allocator overhead. The
large fixtures retain the published 3,360/4,184/5,664-byte peaks for plain HTTP,
encrypted HTTP and USB respectively.

## Follow-up assessment

A second assessment examined the revised selector and its memory admission,
complete/partial/zero-progress serialization, retry caching, source ownership
across producer/session teardown, cipher/tag boundaries, nullable allocation
failure, frame-length expansion and transport delivery authority. The refreshed
complete workflow then exposed the logging warning race above.
A further assessment after that correction checked refresh ordering, warning
priority, source-binding/collector epochs and retained-history behavior, in
addition to the response ownership and failure paths. No additional actionable
defect was found in the final pass.

The escaped USB limit tests admit exactly 65,536 payload bytes with partial
writes and explicit ACK. A 65,537-byte payload closes and cancels before any
header is exposed. Truncated sources produce no partial host document. The
large cipher remains exact after session teardown, and subsequent replay fails
without a busy loop. The production API uses the same selector as the probes.

The corrected browser fixtures exercise actual rendered Pi pages with mocked
HTTP responses. They remain distinct from the actual production network and
USB source-pair integration suites. No schema, wire limit, authentication or
mutation authority was relaxed.

## Measurement and validation

The [updated measurement report](response-generation-results.md) includes the
expanded 21-run baseline/candidate comparison, raw-input manifest and target
linked-image cost. The baseline is Pico `408c0865db7d543ba9ffdc3ac4db45b3c97053b5`;
review changes were tested over Pico `11c086a27a4ca00d9e3857614f4aa45afc628ba2`
and Pi `f31aebc835ecf7eedb101d654cc7b9faab354ab2` on their matching feature branches.
Uncommitted review changes are included in the tested candidate snapshots.

Evidence is retained under `build/response-generation-evidence/`, including
`review-metrics.json`, final host and sanitizer logs, native browser logs and
Linux paired-carrier logs. Physical USB, target heap/stack high-water, device
installation and RF qualification were not performed.

Final native results: 170/170 host checks, six selected ASan/UBSan checks and
ten Pico native browser suites passed. The normal Pico 2 W cross-build passed
its linked-image and memory/stack/journal audits. The four corrected Pi
browser suites passed their full UI assertions. Edited-source selection and
missing-source/compiler-error refusal passed for the reviewed candidate inside
a temporary loopback-only network namespace, avoiding fixed-port collisions.

The Pi logging feedback correction follows the existing Operate design and
Impeccable hardening guidance: existing wording and polite status regions are
preserved, menu overflow remains visible after readback, changed bindings clear
stale evidence, and the established body-text color supplies readable contrast.
Desktop 1,280 px and mobile 360 px were inspected together in light/dark themes;
the browser regression also checks 390 px and 200% text scaling. This changes
status lifetime and legibility, without changing logging wire formats or policy.

Both required actual production network and USB suites passed again for the
reviewed response implementation. Runtime coverage passed 910 checks; network
and configuration interoperability passed actual TLS, strict schemas/negative
cases, persistence and shipped client paths. USB passed framing/ACK, request
binding, refusal-before-writes and the full production Pi/Pico pair. The refreshed
remaining workflow checks passed simulated application/INI behavior, UDP logging,
TLS observer, catalog, private-namespace routing and rollback. Logging controls,
UDP Logs, real-stream USB Logs and the complete Pi UI unit suite passed.

Final SHA-256 comparison matched all 679 Pico code/build/test files and eight
Pi candidate files between the local worktrees and Linux harness. The review
was performed on the stated parent revisions plus the exact uncommitted changes
included in the resulting feature-branch commits. No GitHub Actions run is
claimed; the checked-in workflow recipes were executed locally.

The warning measured 8.18:1 contrast in light mode and 11.27:1 in dark mode at
16 px, with polite status semantics, at both inspected widths. The mechanical
design scan flagged incumbent SFMono fallback names and a 10 px toolbar radius;
these predate this fix and are outside the changed warning rule. Raw log data
keeps its established console typography and grouping. Impeccable also reported
an already-stale design sidecar, which is outside this correction.

### Review reproduction

The measurement report contains the exact required network/USB command sequence.
Additional focused commands use the same candidate roots and pinned dependencies:

```sh
ctest --test-dir "$HOST" --output-on-failure
ctest --test-dir "$SANITIZERS" --output-on-failure \
  -R '^(response_sources|response_usb_pair|http_server_tests|usb_management_tests|usb_management_vectors|consumer_radio_crypto_tests)$'
CHROME_BIN=/usr/bin/chromium node "$PI/WsprryPi-UI/tests/wtp_usb_ui_integration_test.js"
WSPRRYPI_UI_CAPTURE=0 CHROME_BIN=/usr/bin/chromium \
  node "$PI/WsprryPi-UI/tests/wtp_network_ui_integration_test.js"
CHROME_BIN=/usr/bin/chromium node "$PI/WsprryPi-UI/tests/wtp_pi_fleet_ui_integration_test.js"
WSPRRYPI_UI_CAPTURE=0 WSPRRYPI_RUN_RECOVERY_BROWSER=1 CHROME_BIN=/usr/bin/chromium \
  node "$PI/WsprryPi-UI/tests/wtp_recovery_ui_integration_test.js"
# Rendered Logs HTML is produced by the checked-in workflow's PHP command.
LOGGING_RENDERED_HTML="$RENDERED_LOGS" LOGGING_EVIDENCE_DIR="$VISUALS" \
  CHROME_BIN=/usr/bin/chromium node "$PI/WsprryPi-UI/tests/udp_logging_logs_browser_test.js"
LOGGING_REAL_STREAM=1 LOGGING_RENDERED_HTML="$RENDERED_LOGS" \
  CHROME_BIN=/usr/bin/chromium node "$PI/WsprryPi-UI/tests/usb_logging_browser_test.js"
npm --prefix "$PI/WsprryPi-UI" run test:unit
```

Read-only test-hook refreshes force the old ordering: retained events populate
the bounded picker before asynchronous policy/status readback finishes. The
replacement-collector case removes the previous menu before accepting new claims;
peer removal clears current warnings while keeping All sources history.
