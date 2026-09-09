# Connectivity, memory and remote settings investigation

Status: product corrections deployed and verified; intermittent packet-path and
overnight reliability gates remain open. The user reports a web page that became unresponsive overnight,
then confirms a power/reset before this investigation. Preserve the distinction
between execution sandbox denial, transport failure, TLS rejection and application
responsiveness. No cause or memory leak is assumed from that report.

## Baseline and current work

Pico 2 W USB serial 0BF4B4AEC9FFB344, full device
fd6127d11d6aca42a9905fa3fb1bf1d5, original inhibited alias image revision
a9662c3f8323-dirty. First USB sample on 2026-09-09 reports boot
3c90334e9efbfab2e2c242038e76a0ac and approximately 83 seconds uptime.
Heap allocated 14,096 bytes, available 399,088 bytes, sampled peak 86,280 bytes;
this post-reset snapshot cannot establish or exclude an overnight leak.

The identical controlled Mac probe fails inside the sandbox with EPERM for both
wspr5 and Pico and fails hostname lookup. Explicitly unsandboxed execution connects
to wspr5, resolves the Pico alias and fetches authenticated TLS 1.3 HTTP status.
Mac route is en0, .27; Linux route is wlan1, .117; both name the Pico's actual MAC
88:a2:9e:0a:60:df at .47. Mac BPF capture separately requires administrator access;
unsandboxed execution alone does not grant that OS privilege. Linux privileged
capture is available and is bound to actual interfaces.

Private raw evidence is under `build/phase11-4-connectivity-diagnosis/` and
`/home/pi/phase11-4-acceptance/connectivity-memory-20260909-1`. A bounded sampler
reads USB INFO every two seconds while up to 60 normal, early-closed and missing-
client connections execute. It records current heap, available heap, stack/peak,
boot, clock, network progress and available TLS allocator/connection metrics.
Load stops after three consecutive failures, followed by 45 seconds quiescence.
This is a short diagnostic campaign, not overnight or general RF qualification.

## User-requested product corrections

- Accept a DNS hostname for the time server, re-resolve/retry without blocking the
  foreground loop, preserve legacy IPv4 configuration and all SNTP source/time
  checks. DNS failure must not falsely synchronize UTC or bypass ARM/TLS gating.
- Apply station/schedule changes while idle without requiring a reboot. Compare
  network settings with those actually active at boot so successive saves cannot
  hide a pending network change. Preserve stopped/suspended state and watermark.
- Offer an authenticated, revision-bound browser restart for changes that require
  it. Queue it behind acknowledgement of its own HTTP response; aborted delivery,
  a newly acquired owner or unsafe output cancels it. Recheck authority at reset.
  Do not repeat an ambiguous restart. The browser must report reconnection or
  an unconfirmed result, with no USB-only path required for normal remote use.
- Extend independent USB diagnostics if needed so a failed browser cannot conceal
  TLS allocator or bounded network-pool exhaustion. Do not label peak allocation
  or outstanding normal connection state as a leak.

## Validation and boundaries

Use deterministic config/scheduler/API/browser and bounded resolver failure tests,
existing pinned SDK/Mbed TLS builds, affected actual-TLS integration and final
adversarial review. Keep generated firmware, credentials and captures private.
Any physical candidate remains standard inhibited firmware on this exact board;
retain saved operator settings, journals, full identity and authoritative cleanup.
No installed service change, RF job, router mutation or dependency download is
needed for the current diagnostic workload. Record exact candidate hashes before
any approved flash and preserve the original failed observations.

## Retained findings and review corrections

The original 60-connection campaign completed all four phases. Forty normal HTTPS
reads produced 34 HTTP 200 responses and six TLS handshake timeouts; all ten raw
early closes connected. Ten missing-client attempts produced six explicit TLS
errors and four timeouts, with no authenticated response observed. The probe used
a six-second handshake deadline, shorter than the firmware's ten-second handshake
policy (plus possible pending admission). These failures are retained as probe
timeouts, not evidence of a Pico hang. USB responded in all 229 samples without a
boot change. The final 23 quiet samples reported 14,616 allocated general-heap
bytes with no upward trend. The operator saved power 20 during this campaign;
that and expiring response-cache entries prevent treating it as a constant-state
allocation experiment. It does not exclude an overnight leak.

Adversarial review found and corrected a browser-reset authority race: final
reset must use the browser's strict idle gate, never the Console-only latched-
fault recovery exception. The RF cross-build also caught a pointer-to-reference
error because the RF engine binding is a reference; the callback now uses the
common engine interface. Host tests exercise cancelled delivery, unrelated
completion, stale revisions, duplicate finish and ownership acquisition. Actual
Mbed TLS tests withhold the initiating TCP ACK and verify cancellation/exactly-one
restart dispatch. The browser sends no second mutation after lost acknowledgement
or an unchanged boot.

The first physical candidate, SHA-256
`59f65d2436d73b44de96474f941b1ab7d7c62ec0ad3338f34dd05d3a228dbeb4`,
exposed a new diagnostics-size defect: INFO was 2,008 bytes before link-up, then
exceeded the 2,048-byte Console queue and was dropped. HTTPS remained responsive.
This candidate is superseded. The queue is now bounded at 8,192 bytes with the
unchanged 64-byte foreground service budget; failed response enqueue attempts an
explicit capacity error. Existing full/wrapped/blocked Console-versus-WTP tests
were rerun at the new bound. Recovery binds WTP HELLO/CAPS/STATUS to the exact USB
serial and uses the smaller Console STATUS before BOOTSEL, rather than trusting
the unavailable INFO response. All failed observations remain in private logs.


The no-power-save comparison used a separate inhibited diagnostic image
`cdd57b155e30bd416464dbc24548eac6e4c9708f1de5786140dffac035a4baa7`.
Three reads before enabling SDK default sleep completed in 0.836–2.313 seconds;
three after 70 seconds idle with sleep enabled took 0.842–5.285 seconds; three
after disabling sleep took 1.173–1.797 seconds. All nine reads passed. A redundant
runtime mode command in cleanup triggered watchdog recovery at stage 5; retained
fault registers were zero, and USB confirmed inactive/disabled/healthy state.
This diagnostic image and its runtime mode command are superseded. The released
adapter configures and reads back sleep-disabled mode only during interface
startup/re-enable. The experiment supports a latency difference, not a universal
cause for the intermittent outage. In particular, the Mac later failed ARP with
sleep disabled while Linux answered all three broadcast and three unicast ARP
probes. This remaining packet-path issue must not be called fixed.

The time-server address already configured by the operator, 69.89.207.199,
has reverse name `ntp2.wiktel.com`; a separate unsandboxed forward DNS lookup
returned the same address. The hostname test therefore preserves the provider.
The existing wspr5 chrony instance is synchronized but denies NTP service to
this Pico address; no chrony ACL or installed service was changed.

The Chrome restart test on image
`aa485c7b4a9dabf5545bd18a987c38f378ceaa2d919f499e3f1b7e3b5ee768b2`
received HTTP acceptance but reported an unchanged boot after 90 seconds. USB
confirmed the unchanged boot and pending network settings. Review found a
response-completion race: peer closure was checked before the acknowledged
response, and the acknowledgement boundary incorrectly included TLS close-notify
bytes. The correction tracks acknowledgement through the complete HTTP response
separately. A subsequent FIN/RST cannot cancel that acknowledgement; incomplete
delivery, link loss, shutdown and newly acquired ownership still cancel. Actual
TLS regression tests inject ACK plus FIN and ACK plus RST before the next
application poll, alongside the original withheld-ACK cancellation case.

The 30-connection campaign on that same image completed 20 authenticated HTTP 200
reads, five pre-TLS closes and five missing-client TLS rejections. All 79 USB
samples responded with the same boot ID. There were no TLS or lwIP allocation
failures. TLS allocation returned to 4,396 bytes in 21 of the 22 final samples;
the other overlapped a browser request. Final lwIP heap use was 200 bytes,
TCP segments and packet-pool use zero, and one TCP PCB remained during browser
activity. General heap ended at 18,872 bytes. Browser power changes overlapped
this final period, so it is not a strictly quiescent or overnight leak test.
Subsequent idle USB reads showed zero TCP PCBs as well. This evidence belongs
to the recorded image, not an assertion about every future build.

## Validation record

The host suite passed 34/34 checks before the final review corrections. The seven
affected scheduler, Console, USB, API, browser, actual-TLS and pinned production
client checks then passed; five affected sanitizer checks also passed. The final
response-close correction passed actual-TLS and pinned-client tests again, both
normally and under sanitizers (2/2 each). An initial attempt to run those two
builds concurrently failed to bind their shared fixed loopback port; the failure
is retained, and the sanitizer run was repeated alone, without changing checks.
The pinned client is WsprryPi `2e47641f6ebdff104e32999f5194f2e0dc408e06` in
a clean private clone, not the independently modified working checkout.

The exact Pico SDK is 2.3.0,
`98a542c1a62fb549ffb5d66a3e5892b06276b670`, with Arm toolchain 15.3.1.
Both standard inhibited and standalone RF targets cross-compile. Only the
inhibited image is deployed. The image check verifies the 16 KiB primary stack,
nonoverlapping heap/core-1 stack and reserved journals. Browser fixture checks
cover desktop/mobile layout, draft preservation, ownership gates, lost replies
and unchanged-boot handling. The rendered restart controls were visually checked.

Review also retained numeric-address rejection for legacy hexadecimal/octal
spellings, canonicalized DNS names before lwIP `.local` lookup, preserved the
SNTP denial policy across DNS changes, and verified that later station saves do
not conceal a pending network change. No RF, second-device conflict, overnight
reliability or universal LAN reachability qualification is implied.

## Restart correction device and browser result

Standard inhibited restart-correction UF2 SHA-256:
`45d5ebe740c86ce9ee8a4aa05151cb06c14b4359922fa6ae6b91b69c256febd0`.
Its embedded revision is `5fbc3e8065a1-dirty`; private
`candidate-restart-fix.json` binds the image to 95 source/build-input hashes,
checked against the working source at deployment. It uses the same approved device CA,
operator/controller identities and alias server certificate (SHA-256
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`).
No new trust import or installed service mutation occurred in this investigation.

Chrome saved a temporary power change from 20 to 23 dBm and reported
“Settings saved and applied,” without restarting. It then restored 20 dBm.
The time-server hostname `ntp2.wiktel.com` was saved through the same form.
After deployment of the response-close correction, Chrome's Restart device
confirmation was accepted once. At 06:43:30 America/Chicago on 2026-09-09 the
page reported “Device restarted. Saved settings are active.” Independent USB
inspection verified boot changed from `6de9af469977d156729c4ad9d9ee9ceb` to
`73db27d40933d0723211fdf3a75cf9d0`, without recovery-boot/fault status.

Final USB INFO/WTP HELLO/CAPS/STATUS confirmed the exact board, inhibited engine,
empty/unowned/inactive output and healthy storage. Power remains 20 dBm,
schedules remain disabled with period/phase 120/0, and watermark remains
`1788714601000000000`. DNS resolved the time-server name to 69.89.207.199,
SNTP accepted a sample, UTC synchronized and `reboot_required` is false.
Wi-Fi is enabled with power save disabled; the certified short alias is advertised.
The Chrome page remains open and connected.

The final adversarial reassessment revisited HTTP response/close ordering,
cancelled delivery, revision replay, owner acquisition before reset, network
configuration tracking, resolver callback lifetime and stale-peer rejection,
Console capacity and resource-accounting claims. The identified source defects in
that scope were corrected and affected checks rerun; the later startup watchdog
failure below remains unresolved. Intermittent Mac/AP packet
delivery remains unresolved, and the reset morning device cannot supply its
pre-reset heap history. A longer observed run is still needed before claiming
overnight leak freedom. Phase 11.4 and its existing second-board gates stay open.

## Requested default time server

The operator subsequently selected `pool.ntp.org` as the default. New browser
configuration and an omitted version-1 `wifi.ntp_ipv4` now use that hostname.
Explicitly saved servers remain unchanged; empty/invalid supplied values still
fail validation. The setup example uses the hostname directly instead of a
provisioning-time IP lookup. The earlier provider-name test above remains valid
historical evidence, but is not the final selected setting.

The final inhibited image with this default has SHA-256
`d351875886e8167ae98ebfc39533ba9eba22e2fc5b54e707bef0d4aeac57c901`.
Private `candidate-pool-default.json` records its complete source manifest and
the same `5fbc3e8065a1-dirty` embedded revision. Both firmware targets and the image
layout check passed. Six affected host checks, including actual TLS and the
pinned production client, passed again; the two affected config/API sanitizer
checks passed. Review verified missing-field defaulting, explicit-server
preservation and consistent browser prefilling without migrating stored settings.

The first cold startup of this image failed physical verification: boot
`2813da5de1b01ec9706f6e2b13dc7a17` was followed by watchdog recovery boot
`7506c6f2eabcf32a83de94f9d7ca86ba`, stage 14, with zero fault hash/PC/status.
Stage 14 covers network status/discovery, DNS and SNTP processing after the SDK
poll; it does not identify the exact stalled call. The saved time server was
still `ntp2.wiktel.com`, so this was not a `pool.ntp.org` resolution test.
USB confirmed responsive recovery, inactive/unowned state, healthy storage and
preserved settings. This is a retained startup reliability failure, not a memory
leak diagnosis. One bounded Console reboot was used to recover; a successful
retry cannot erase this open watchdog/startup gate.

Recovery returned normal connected/synchronized boot
`05e1149c1c07668ef2be331dd2b4377f`. Chrome then saved `pool.ntp.org` and issued
one confirmed restart. USB independently verified new normal boot
`798ca1a723137001a0ae39dfaf04ebee`, resolved address 94.100.20.238, an accepted
SNTP sample, synchronized UTC and `reboot_required:false`. That address is an
observation, not a new hardcoded default. Power 20 dBm, disabled 120/0 schedules,
the original watermark and empty/unowned/inactive inhibited state were preserved.
No further source changes followed the final image manifest verification.

The pool-setting restart succeeded over USB, but Chrome exhausted its reconnect
window. A fresh explicitly unsandboxed Mac probe connected to wspr5 while Pico
TCP timed out, mDNS lookup failed and HTTPS returned host-down. A separate Linux
TLS read failed before TLS with no-route-to-host. USB still supplied authoritative
status. These are retained final-image reachability failures, distinct from the
earlier sandbox EPERM observations and from successful DNS/SNTP application.

One bounded Console Wi-Fi OFF/ON cycle restored browser access without changing
boot `798ca1a723137001a0ae39dfaf04ebee`, settings or watermark. At 06:55:35
America/Chicago, Chrome again displayed connected/synchronized status,
`pool.ntp.org`, power 20 dBm, disabled schedules and inactive/unowned output.
The page is left open in that state. This recovery is evidence of restored access,
not closure of the intermittent connectivity or startup-watchdog gates.
