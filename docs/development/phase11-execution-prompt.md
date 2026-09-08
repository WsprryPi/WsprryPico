# Phase 11 execution prompt

Work directly in `devel` in WsprryPico. Begin from the clean, fetched baseline
91e57e6. Read README.md, CONTRACT.md, architecture, WTP/1, the development
baseline and recent Phase 10 changes. Preserve unrelated work; other repositories
are read-only. Commit and push the finished, reviewed change as requested.

## Orientation and findings

Phase 10 is complete in the current roadmap and target evidence. The recent
changes preserve local sample-clock realization, RF servicing between complete
WTP request stages, SNTP refresh after long frames and coherent launch status.
The standard image remains inhibited. Standalone config, flash journals, SNTP,
autonomous scheduling and USB WTP already share one JobService. lwIP currently
disables TCP; network polling is deferred throughout Armed/Running. Browser
resources are proposals only. Config persistence requires idle service and a
reboot; configuration reads must never reveal the Wi-Fi password.

WTP/1 requires TLS >=1.3, mutual authentication with device-specific credentials,
and ALPN `wtp/1`. Do not add plaintext WTP or weaken the normative contract.
The local pinned SDK contains Mbed TLS 3.6.6 and TLS 1.3 server implementation.
Disable TLS 1.2, session tickets/resumption, early data and client-side TLS.
Use a server certificate/key and a device-specific client CA, supplied by explicit
ignored local build input. No generic credentials, installed secrets or live
device operations are part of this execution.

Read-only WsprryPi UI inventory: operation.js/index.js depend on PHP state,
settings endpoints, jQuery and Bootstrap; maintenance controls target Linux.
Owned WsprryPi source is MIT, vendor assets retain separate upstream licenses.
Build small original static assets using familiar station, schedule, status and
network terminology; preserve the shared API direction without migrating Linux
or copying its dependency bundle. Implement plain HTML/CSS/JS for the constrained
embedded server, accessible labels, keyboard focus and responsive layout.

## Implementation

1. Add a portable bounded HTTP/1.1 parser with strict request line, headers,
   content length, duplicate/ambiguous framing rejection, no chunked transfer or
   pipelining, finite receive/write timeouts and one response per connection.
2. Define browser API v1 resource/error/authentication/precision/revision
   semantics. Implement capabilities, job and clock status, redacted config,
   schedules, complete-job operations and owner-checked abort. Route job requests
   through the existing codec and JobService; never add a separate RF start path.
   Preserve full 64-bit time/frequency integers as decimal strings.
3. Use mandatory TLS client authentication for HTTP and WTP. Bind principals to
   certificate identity. Protect browser mutations with strict same-origin checks,
   JSON content type and a required custom header; prohibit CORS. Require a
   boot-scoped configuration revision for config/schedule/network writes. Reject
   writes while owned/armed/running/faulted, and report persistence/reboot needs.
4. Enable bounded lwIP TCP and add a foreground, nonblocking Mbed TLS adapter.
   Use one authenticated connection at a time, with at most one bounded pending
   TCP connection so sequential browser requests survive TLS shutdown overlap. Dispatch
   ALPN `wtp/1` to Endpoint and `http/1.1` to HTTP. Keep USB canonical. Close on
   link loss or timeout; preserve JobService disconnect semantics. Do no parsing,
   flash writes or TLS handshake work inside lwIP receive callbacks. Service RF
   around network work, and refuse new handshakes during armed/running jobs.
5. Supply network status including initialization, enabled/link/IP state and
   listener/credential availability; support idle-only enable/disable and saved
   Wi-Fi settings with the existing reboot/recovery behavior. SoftAP/BLE remain
   Phase 12. No live flashing, USB, GPIO or RF actions are authorized here.
6. Embed compact original browser assets, showing honest connection, storage,
   clock, owner and RF state. Provide station/Wi-Fi/schedule editing, job inspection
   and owner-aware job control. Advertise unsupported features explicitly.
7. Provide local certificate init/issue/renew/inspect and password-protected
   browser export tooling. Never automatically install trust. Add a physical
   Console ABORT override through JobService for recovery during RF network pauses.
8. Add deterministic host tests for malformed HTTP, authentication/origin checks,
   revision conflicts, password redaction, ownership, disconnect/backpressure,
   and job behavior. Exercise the actual TLS adapter using mock TCP/clock/RNG
   boundaries and locally generated ephemeral test credentials when feasible.
   Cross-link both inhibited and StandaloneRF firmware; measure assets and memory.
9. Update docs with build inputs, operator workflow, contract and exact evidence.
   Distinguish host validation, cross-link results and pending target qualification.
   Do not claim Phase 11 physical acceptance from host tests.

## Acceptance and review

Run documented host CMake/CTest, protocol validator, appropriate sanitizers,
firmware/image checks and browser validation. Perform adversarial review against
framing/resource exhaustion, TLS trust, CSRF/DNS rebinding, revision races,
credential disclosure, owner isolation and local execution under disconnection.
Fix actionable issues, rerun affected checks and repeat adversarial assessment.
Record each pass and any unresolved target-only limitations. Verify diff/links,
commit on `devel`, push `origin/devel`, confirm remote parity, and report the commit,
checks, behavior and remaining hardware acceptance gate.
