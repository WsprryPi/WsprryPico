# Phase 11.4 F2, F3 and F6 certificate acceptance

F2, F3 and F6 passed their remaining bounded physical cases on 2026-09-09.
Phase 11.4 remains open for the other rows in the [joint matrix](phase11-4-plan.md).
The [execution prompt](phase11-4-f2-f3-f6-prompt.md) was executed, reviewed,
repaired and reassessed. Raw evidence stays private under
`build/phase11-4-f2-f3-f6/`; the [hash index](phase11-4-f2-f3-f6-evidence.json)
binds retained artifacts. No credentials or generated firmware are published.

## Identity and boundaries

- Sole Pico 2 W/RP2350 on wspr5: serial `0BF4B4AEC9FFB344`, device
  `fd6127d11d6aca42a9905fa3fb1bf1d5`, Console if00 and WTP if02.
- Start: repository `5ee5bcf`, deployed runtime `23ac5b1aee66`, boot
  `1c4730e38aa4e6f8549cbc8c475846bd`. Both working trees were initially clean.
- Tested runtime: `5ee5bcf93c56-dirty`, with exact source and generated-overlay
  provenance in private candidate manifests. This is a precommit build of the
  reviewed repair, not a claim that unmodified 5ee5bcf contains these fixes.
- Only `inhibited-standalone-simulator`; UF2 journal bounds, inhibited build
  definition and DryRunEngine linkage checked. No StreamEngine/RfWorker linked.
- Mac Chrome profile Lee and local OpenSSL, wspr5 Linux/Python/OpenSSL, shared
  DHCP LAN; Pico address `192.168.1.47`, alias `wsprrypico-0a60df.local:18443`.
  SSH/LAN checks ran outside sandbox restrictions. No hosts-file override,
  discovery proxy, certificate-warning bypass or clock falsification was used.
- Existing device CA fingerprint remains
  `2ef7ec890d48e9283286ee09c6b549756f3d3cff530e5cb030ced6ae4c40442b`.
  No new CA or trust-scope change. The user separately approved the replacement
  browser import after automatic approval review rejected the broader test grant
  for that specific persistent keychain operation.

| Deployment | UF2 SHA-256 | Server certificate SHA-256 | Boot |
| --- | --- | --- | --- |
| Temporary DNS + IP SAN | `90c07f9efa0cfa85d5103d73bebd09fdae0f52c2d5db947b0603823f552b0c2b` | `6469f132caae8a28b650fcf1aed244404da9e8664a42180fe23e7d6ca2edbb65` | `a46ac05fd094b279701b94e4d1266e41` |
| Final DNS-only, TLS fixes retained | `2711a54ba57b7754907a5e20dd84d6920dcb5ffe8524c69b8ff2ae569a0686e4` | `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016` | `c2ed521e566499e42583d2d212540cfa` |

Both exact images were staged owner-only, hash checked, loaded with the existing
picotool using the selected serial, verified and rebooted without journal erase.
Rebuilds after the final build-integration review reproduced both UF2 hashes.
The final image restores the original server certificate while retaining the
F3 runtime repair; it does not restore the old faulty TLS implementation.

## F2: replacement and original clients

Replacement browser leaf SHA-256:
`ba303252eb5af503ba2ed9e9c83e701fe012defa1707d0c41769e567dd6e768a`.
It was exported using the documented macOS PKCS#12 profile, imported into the
login keychain, selected in actual Chrome and inspected in its native certificate
details. Serial `00E711A67AF77DEAC4DCE00AC25AB77B0A`, clientAuth purpose and
fingerprint matched. The user completed the protected Mac keychain prompt.

Chrome then loaded the real literal-IP station page, reported secure connection
and valid server certificate, and showed fresh inactive/unowned status at
10:06:08 CDT. Its actual `/api/v1/status` response contained the IP-image boot
and completed replacement-controller job, independently tying the page to live
state. The original hostname tab subsequently refreshed against the restored
DNS-only image and showed its new boot, inactive output and disabled schedules.
Original browser credentials also passed the final direct HTTPS positive controls.
The replacement identity remains installed for continued use; original identities
and existing CA trust remain installed. Issuance does not revoke them.

The production application was the isolated, clean source
`923ab570fe53ef2ccca7d12e519c9dc36adf7e93`, executable SHA-256
`993ad62def487e5f03d82a5a7a1f5f82b972b16bd36eaa5b0d9a8c13a7166323`,
under `/home/pi/wsprrypi-browser-coverage-20260909`. The actual application ran
unprivileged with its production TLS transport, separate private INIs and
explicit TCP destination plus expected DNS identity. Certificate paths and leaf
fingerprints were verified before invocation. No simulated host transport,
credential fallback or installed binary/configuration replacement was used.

| Controller | Client certificate SHA-256 | Actual production job | Result |
| --- | --- | --- | --- |
| Replacement | `b1d4dd33681ccc61c8309778ac67669228953d12866084009723143c51176eb8` | `fe786a576e852fc60000000000000001` | Complete, authoritative inactive, cleanup passed |
| Original again | `c615a0f65d94c08bf65a776393f9d72c09f813fe59a1bfb2bd3ef4e6d023b0a1` | `eb801a45036651bb0000000000000001` | Complete, authoritative inactive, cleanup passed |

Each was one QRSS E with three-second dots at nominal 3,570,100 Hz, fully handed
to the inhibited Pico with a future start and 500 ms uncertainty budget. Actual
CAPS/clock/state were checked. Processes ended before the ten-minute repeat.
Both runs used the IP-SAN firmware/boot above; neither qualifies physical RF.
Before each bounded service pause, installed configuration was checked for
transmit false/boot Never and the RP1 provider authoritatively reported output
false. Graceful application exit, USB owner null/output false, configuration and
watermark comparisons, service active and provider output false were verified
after each run. Installed binary/INI hashes were unchanged.

## F3: defects, repairs and exact rejection layers

The prior missing/untrusted/expired-client record errors reproduced on both the
physical Pico and actual-TLS host adapter. Tightening the test to require specific
certificate alerts failed before the repair. Source inspection identified the
post-Server-Finished outbound-key selection defect and obsolete missing-client
alert. The [patch provenance](tls-certificate-alerts.md) records the narrowly
modified pinned Mbed TLS translation units and Apache-2.0 licensing.

An adversarial seven-byte-write/alternating-backpressure test then exposed lost
untrusted/expired alerts: the common verifier ignored WANT_WRITE. Routing TLS 1.3
verification failures through the pending-alert state repaired this too. The
Pico adapter holds a failed connection inert until queued bytes are acknowledged
or a one-second deadline expires, then closes it without application dispatch.

The external SDK checkout is unchanged. Production builds and host tests use the
same hash-checked generated overlay, with unique source replacements and refusal
of changed upstream inputs or output inside the SDK. No TLS validation was relaxed.

Both deployed repaired images passed the following controls; the SAN outcome
appropriately differed between the temporary and final certificates:

| Case | Observed validation layer and result |
| --- | --- |
| Valid original browser before/after | Verified TLS 1.3 and HTTP 200 |
| Wrong hostname | Client certificate verification, hostname mismatch (62) |
| Wrong CA | Client certificate verification, issuer-chain failure (20) |
| Missing client | Device fatal `certificate_required`, alert 116, no HTTP |
| Untrusted client | Device fatal `unknown_ca`, alert 48, no HTTP |
| Expired client | Device fatal `certificate_expired`, alert 45, no HTTP |
| Literal IP with matching SAN | Client IP verification succeeded on temporary image |
| Literal IP without SAN | Client IP verification rejected final image, mismatch (64) |

Negative requests were only GETs; traces preserve the handshake and fatal alert,
not just absent HTTP. Existing expired/rogue leaf purposes, chains and dates were
inspected without changing clocks or bypassing the build validator.

## F6: actual Chrome numeric authority

The temporary certificate contained exactly the real full device identity,
certified DNS alias and current DHCP IPv4 SAN. Chrome's address bar showed
`https://192.168.1.47:18443/`; native site information said Connection is secure
and Certificate is valid. Its certificate viewer SHA-256 matched the temporary
image certificate in the deployment table. The numeric-origin page fetched live
status with the replacement client, so this is actual Chrome/numeric HTTP
authority evidence, beyond the earlier direct TLS-only case. The final deployed
certificate intentionally has no IP SAN; use the hostname for continued access.

## Retained attempts and adversarial assessments

- First read-only wrapper invocation omitted required run arguments and exited
  before I/O. Corrected invocation passed USB and Linux HTTPS preflight.
- First host listener bind failed inside the sandbox. Outside-sandbox repetition
  reached the real TLS record-layer regression; no network failure was inferred
  from the denied loopback bind.
- Initial OpenSSL trace mode mixed trace and HTTP stdout, causing positive
  prefix assertions to fail although full HTTP 200 responses were retained.
  Separate trace files restored the exact oracle; no firmware fix was credited
  for this harness error.
- Initial normal-write repair passed; adversarial partial writes failed for rogue
  clients. The pending-alert repair passed normal and fragmented cases, then
  the bounded unacknowledged-alert slot-release test also passed.
- Full host suite initially passed 33/34. The certificate-only CMake fixture
  exposed TLS overlay integration at the wrong layer. Moving SDK overlay setup
  to the firmware entry point preserved the real gate without weakening it;
  the certificate-gate test passed on repeat. Rebuilt UF2 hashes were unchanged.
- Mac and Linux failed TCP admission after the IP-image flash despite healthy
  USB/link/SNTP. One bounded Console Wi-Fi cycle restored reads. After restoring
  the DNS-only image, the first Mac positive control timed out; one further
  bounded Wi-Fi cycle restored final HTTPS. These failures remain evidence of
  the separate intermittent-connectivity gate, not certificate passes.
- Chrome certificate inspection/keychain interaction exceeded the bounded
  handshake window. An initial navigation also received cross_site_request.
  Explicit address-bar navigation after selection/authorization produced the
  successful real page. No warning bypass or security-policy relaxation occurred.
- Review corrected the held-ACK test oracle: it now marks the next accepted
  connection before connecting and keeps the rejected peer open during the
  positive probe, so an early peer close cannot masquerade as deadline cleanup.
- Final review checked exact principal inputs, actual browser leaf selection,
  immutable SDK provenance, no duplicate source linkage, alert retry/nonces,
  no application admission on failure, bounded closure, identity/boot binding,
  unchanged journals, service restoration and secret exclusion. No actionable
  in-scope finding remained after the affected repeats.

## Validation and final state

The full host run covered 34 tests, with its one fixture failure corrected and
passed on focused repetition. Actual pinned WsprryPi interoperability passed.
Final actual-TLS rejection/lifecycle tests, including held ACKs and fragmented
writes, passed. ASan/UBSan actual-TLS tests passed. WTP contract validation,
C++ formatting, Python compilation, standalone ELF/UF2 bounds, overlay refusal
checks, documentation links and diff whitespace were checked. Remote CI is not
claimed. The local WsprryPi checkout remains clean on devel at `89f23e5`;
its tested isolated production checkout is independently pinned above. Short acceptance does not establish overnight memory/leak freedom.

Final boot is `c2ed521e566499e42583d2d212540cfa`, engine inhibited, state empty,
output false, no owner/job, storage healthy. Saved station AA0NT/EM18/power 20,
disabled 120/0 schedule, expiry zero and watermark `1788714601000000000` were
preserved. `pool.ntp.org`, Wi-Fi enabled and power management disabled remain.
Mac Chrome, Mac verified TLS and Linux verified HTTPS recovered. Installed
wsprrypi.service was restored after both production runs, provider output false.

The final review does not close B2, DHCP/link discovery D1-D3, multi-device/conflict
E1-E3, production recovery G4-G7 or the connectivity/startup/overnight reliability
follow-up. Previous A2/C2/C4 evidence retains its own exact runtime scope.
Phase 11.5 resource/contention and 11.6 conducted RF remain separate.

## Documentation Impact

Updated this result, the execution prompt, joint matrix, review entry point,
network certificate guide, patch provenance and third-party notices. Considered
WTP, Browser API, architecture and certificate lifetime/revocation contracts;
those contracts remain unchanged. No frontend asset or UI behavior was changed.
WsprryPi source and its independent working tree remain untouched.

Operator follow-up remains outside the authorized documentation repository:
`Wsprry_Pi_Docs/docs/Advanced_Operations/ini_configuration/transmitter_backends.md`
needs network credential replacement, one-year leaf/ten-year CA lifecycle,
Mac login-keychain authorization and hostname-versus-IP-SAN instructions.
No files in that separate repository were edited.
