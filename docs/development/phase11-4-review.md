# Phase 11.4 inhibited device acceptance review

The [D1–D3 record](phase11-4-d1-d3-results.md) adds captured Pico goodbyes, native
Mac cache removal/re-add and Linux negative lookups, with a complete final bounded
D2 packet audit. Repeated recovery failed once and Chrome later returned an
address error, so D2 remains partial. D1 has an identified router but needs the
scoped temporary-reservation exception; D3 needs the selective physical fault.
Fifteen negative audit cases and the repeated adversarial assessment passed.

The [E2/E3 completion](phase11-4-e2-e3-results.md) records a controlled LAN alias
conflict during a real inhibited job, unchanged completion and explicit recovery
of the same certified name. Packet and peer observations pass. E1 still requires
a second physical board; the host claimant does not establish independent trust.

The [G4–G7 completion](phase11-4-g4-g7-results.md) records socket-level lost
replies, real production reconnect failures, process nonadoption, actual boot
and controlled-device identity latches, and USB versus Console recovery. Final
Mac/Linux reads pass; intermittent reliability and the remaining D/E cases are
still open. The controlled endpoint does not replace two physical boards.

The [F2/F3/F6 completion](phase11-4-f2-f3-f6-results.md) records actual client
replacement, corrected certificate-rejection alerts, Chrome literal-IP acceptance
and restoration of the hostname-only inhibited image. Other matrix gates remain open.

Status: **OPEN**. The single-board continuation completed actual production
startup/finite execution, direct inhibited lifecycle/authority checks, Chrome
revision/draft behavior, renewal, wrong-board rejection, literal-IP client checks
and altered-value persistence. Intermittent ARP/NSS/TCP reliability and
unexecuted physical subcases remain open. Only one
Pico is available. See the [current joint matrix](phase11-4-plan.md) and
[execution/repeated adversarial record](phase11-4-single-board-run.md).

The [2026-09-09 browser/production continuation](browser-production-coverage.md)
adds actual Chrome completion/cancellation, production settings writes and
concurrent Chrome Armed/Running evidence. It fixes the companion scheduler's
silent-wait timeout and two browser unknown-output/error-feedback issues, with
repeated adversarial assessment. Its new browser source is locally tested and
cross-built; physical evidence remains bound to installed `f88fa71`. The earlier
no-source-change statements below describe the earlier continuation only.

The continuation adds an opt-in acceptance driver and deterministic refusal/recovery
tests, with four affected CTest suites passing. It restores the original inhibited
image/settings and installed service. No firmware/runtime/protocol/UI/SDK/component
source or CI pin changes. Actual source, hashes, failed attempts, approval resolution
and final state are recorded in the continuation. The sections below retain the
historical baseline and shorter-name work; their earlier service/authorization
statements describe that period, not the later specifically approved execution.

## Scope and source review

Initial clean local `devel` pair: Pico `a9662c3f8323bba64986ff26972d43570af145b4`,
Pi `2e47641f6ebdff104e32999f5194f2e0dc408e06`. Both matched independently read
origin/devel. Diffs from the reviewed runtime pair d8cde03/efcc792 contain only
documentation/test/reference work. No runtime, protocol, reusable component, SDK, CI pin or UI source has changed.
The certificate helper adds an explicit macOS PKCS#12 export profile, with
regression coverage. The shorter name uses the existing certified-alias mechanism.

Reviewed Pico README/CONTRACT/architecture, implementation plan, development,
WTP/browser/identity contracts, 11.2/11.3 records, network/mDNS/certificate guides,
USB and standalone/Phase 10 procedures. Implementation review covered
`firmware/CMakeLists.txt`, `src/standalone/pico/main.cpp`, profile/DryRunEngine,
network server/time/admission/HTTP authority, mDNS lifecycle and matching tests.
Pi review covered its project instructions, 11.1/11.3 records, TLS/resolver/HTTP
adapter, production configuration/clock/recovery contracts, test orchestration,
Make targets and exact companion pins. These source observations are not physical
acceptance of the unexecuted cases.

## Physical evidence

Private raw evidence: `build/phase11-4-evidence/`. Command manifests for device
operations contain UTC start/end, exact argv and exit status. The generated
`usb-inspect-program.py` streams unchanged inspected local helper modules into
remote Python memory; it writes no remote helper files and performs only the
authorized Console INFO/STATUS and five read-only WTP requests. Its schema is
embedded from the current normative file. The Console helper checks device ID;
review additionally cross-checked both boot identities, CAPS and STATUS.

Initial inspection (`usb-authorized.*`) confirmed the original board serial
0BF4B4AEC9FFB344, WTP device fd6127d11d6aca42a9905fa3fb1bf1d5 and old inhibited
a3ec67d059b3 image. Stored scheduling was disabled; no owner/output/job. A fresh
preflash read (`preflash-refresh.*`) reconfirmed these conditions and watermark
1788714601000000000 immediately before the separately approved BOOTSEL operation.

The private candidate from clean a9662c3 was built using the standard
`WsprryPico` target only, validated deployment identity and separate per-device
CA. Exact ELF/UF2/certificate hashes are in the plan. Stack/heap/journal/UF2
inspection passed; offline picotool and linked engine inspection identify the
inhibited image. This does not constitute physical RF measurement.

After explicit user approval, staged the exact hashed UF2 in owner-only
`/home/pi/phase11-4-acceptance/` on wspr5. Existing picotool 2.3.0 selected only
serial 0BF4B4AEC9FFB344, loaded with `-v -x`, verified programmed data and rebooted.
No full erase, journal reset, persistent config write, RF-capable image, service
action or job submission occurred. `stage-image.*`, `bootsel.*` and `flash.*`
retain the operations, including picotool's verification result.

`postflash.*` reports:

- Revision `a9662c3f8323`, boot `9bb67733fb3188942bb1fdc399041cd7`, same device ID.
- `deployment_identity_matches:true`; CAPS `inhibited-standalone-simulator`.
- STATUS `empty`, `output_active:false`, no owner/job, empty terminal records.
- Healthy storage, autonomous scheduling disabled, retained schedule and watermark.
- Device SNTP synchronized, normal leap, approximately 125 ms uncertainty,
  42 s sample age; no host clock seed or time/configuration change.
- Wi-Fi address `192.168.1.47`, control listening, mDNS `active`, one registration,
  no conflict/failure, exact certified default hostname advertised.

`mac-dns-sd.*` records a real `dns-sd -G v4` response for that hostname/address on
interface index 14 (`en0`, Mac 192.168.1.27), TTL 120. The long-running diagnostic
was deliberately stopped after 15 seconds. No hosts-file entry matched. Linux
`linux-getent.*` records successful `getent ahostsv4` on wspr5 through its real NSS
path. Optional resolvectl/Avahi utilities were absent from the inspected PATH;
they are not reported as passing. Production-client resolution/TLS remains a
separate case. There was no DHCP reassignment or peer packet capture.

## Findings, repairs and repeated assessment

| Finding | Disposition |
| --- | --- |
| Historical USB driver expects pre-standalone text banner, old engine and unsynchronized clock | Updated procedure to use current Console/WTP tools, explicit identity/engine/output cross-checks and correct standalone image checker. Historical driver/evidence retained. |
| Layout validation alone could be mistaken for inhibition/board verification | Plan separately binds target definition, DryRunEngine symbols, embedded revision/manifest, image hashes and actual INFO/HELLO/CAPS/STATUS. |
| Standalone/Phase 10 guides still describe no browser and universal active-job network deferral | Corrected to optional TLS management, current worker/lockout ownership and conditional listener-dependent polling. No runtime change. |
| wspr5 installed executable is not the reviewed network candidate | Recorded installed hash and independent checkout revision; isolated reviewed source staging/build was separately approved and completed. No moving checkout or replacing service implicitly. |
| Original matrix omitted explicit subcases/layer distinctions | Joint matrix names persistence, all cancellation/loss/restart cases, client replacement, IP SAN, wrong-board runtime gate and missing equipment. |
| Keychain rejected modern OpenSSL PKCS#12 while OpenSSL could decode it | Added opt-in `--macos-keychain` SHA-1/3DES packaging; actual Mac import succeeded, existing identity preserved, TLS unchanged. |
| Hostname-scoped CA SSL trust remained untrusted in Chrome | Automatic approval review rejected widening the scope; explicit user approval followed, SSL trust for only this device CA succeeded. No warning bypass. |
| MAC-suffix name requested during acceptance | Existing `--hostname` alias produces wsprrypico-0a60df.local, retaining full WTP device identity and conflict handling; separate exact-image flash approved. Chrome/Mac recovered after an authorized Wi-Fi cycle; Linux NSS later failed again. |
| mDNS utility success could be mislabeled full host integration | Mac system and Linux NSS evidence recorded separately from B3 production-client TLS/WTP, with actual address/interface and no injected resolution. |

Second source/evidence assessment checked the repaired procedure against current
Console fields and firmware profile, preserved original failures, expected device/
boot and deployment binding, explicit output false, absence of owner, unchanged
watermark and inhibited-only target selection. No additional actionable runtime
defect has been established by the executed cases. Unexecuted physical cases and
later target resource/RF work remain unresolved, not passes.

Retained failed attempts: restricted-shell SSH name resolution failed; an explicit
IP SSH attempt was sandbox-denied. The authorized retry used the observed wspr5
address and existing `HostKeyAlias=wspr5.local`, preserving SSH authentication.
That transport workaround is not counted as Pico mDNS acceptance. Initial Git
remote reads also failed under restricted DNS; permitted read-only retries returned
the expected heads. The first host CTest run failed to start its two loopback TLS
listeners (`TLS start error -1`); both passed with local sockets permitted.

## Browser import and physical Chrome evidence

Mac: macOS 26.6.2, Chrome 152.0.7977.83, Lee profile. CA/browser public
fingerprints and keychain scope are in the plan. The raw credential files,
PKCS#12 password, client keys and compatibility package remain private/ignored.
Initial raw-key import failed as an unknown format. Modern PKCS#12 import failed
MAC verification despite successful OpenSSL decoding. The explicit compatibility
package imported one identity and its CA. The first hostname-scoped CA trust
entry still produced ERR_CERT_AUTHORITY_INVALID. The user subsequently approved
SSL trust for this exact device CA after automatic approval review rejected that
broader scope without express approval. The approved trust change passed and the
existing browser client identity was selected. No certificate warning was bypassed.

A connection reset after client selection and one `cross_site_request` navigation
were retained. A subsequent direct address navigation loaded the actual Pico page.
Do not claim the cause of the reset was proved; server timeouts are diagnostic,
not proof that the selection dialog caused this particular failure. The request
policy remained unchanged. Chrome displayed Connected, empty job, inactive output,
available owner, synchronized clock, inhibited engine and the certified long name.
The Security panel reported valid/trusted HTTPS, TLS 1.3, X25519/AES_128_GCM and
expected device CA. A separate OpenSSL read with the same browser identity also
returned HTTP 200 (`browser-identity-openssl.*`); it is not a Chrome substitute.

Impeccable guided a narrow visual review of the incumbent surface. The live
320 by 568 responsive viewport showed a readable status layout and disabled
owner controls; config/schedule fields loaded with password blank and scheduling
disabled. Screenshots/accessibility observations are in the task tool record,
not published with private station fields. No settings or jobs were submitted.
This is an initial visual/status observation, not the unexecuted shared Pi UI,
revision-conflict, concurrent ownership, mutation or unavailable-state matrix.

The certificate wrapper options are documented by
[OpenSSL](https://docs.openssl.org/3.1/man1/openssl-pkcs12/).
[Chromium's macOS trust implementation](https://chromium.googlesource.com/chromium/src/%2B/a9d6aa6ffdfea124df722090104e0e491d6bf071/net/cert/internal/trust_store_mac.cc)
explains its rejection of a PolicyString-constrained trust entry; the current
Chrome failures and successful approved repair are the actual physical evidence.

## Shorter-name deployment and retained reachability failure

The user preferred the last six hex characters of the Wi-Fi MAC to a truncated
WTP hash. Mac ARP cache at the verified Pico IP reported 88:a2:9e:0a:60:df; that
cache is a naming observation, never board authentication. The alias is
`wsprrypico-0a60df.local`. Existing source supports it without changing the full-ID
default, WTP, manifest schema or TLS identity policy. A speculative 12-character
ID-default edit was withdrawn before deployment. Documentation explains that
renewals of an alias must repeat `--hostname` and suffixes can collide.

The new same-CA bundle, certificate fingerprint and exact image hashes are in
the plan. Runtime source/CMake/firmware directories have no diff from a9662c3;
embedded revision is a9662c3f8323-dirty because tooling/docs were being edited.
The two build caches differ in the server-bundle input. Layout/inhibition checks
passed. An attempted `check_standalone_image.py --help` was unsupported by that
positional script and failed in its nm parser; the documented ELF invocation
then passed. This invocation error is not an image failure.

After explicit approval, `mac-preflash-refresh.*`, `mac-stage-image.*`,
`mac-bootsel.*` and `mac-flash.*` retain the identity/state prechecks, distinct
filename and exact hash, selected-board BOOTSEL, flash verification and reboot.
`mac-postflash.*` reports new boot efa316aecb3f7c9e29484eca66e068d3, same full device
ID, deployment match, configured/advertised short name, mDNS active and IP
192.168.1.47. Output is false, state empty, owner/job absent, disabled schedule
and watermark 1788714601000000000 preserved. SNTP samples continue.

The initial short-name peer retest **failed**. Linux NSS returned exit 2 with no answer
(`linux-alias-getent.*`), Chrome reported DNS_PROBE_FINISHED_NXDOMAIN, and the
bounded Mac dns-sd attempt had no answer. Its first piped output was buffered at
termination; `mac-alias-dns-sd-pty.*` records the subsequent header-only attempt.
Explicit-IP HTTPS with the short DNS identity timed out at 20 seconds; the wrapper
raised before persisting metadata, so that attempt is retained in the task tool
record and is not presented as a complete timestamped evidence file. Mac's host
route showed REJECT; repeated USB diagnostics still show active Wi-Fi/SNTP and
inactive/unowned state (`mac-network-diagnosis-usb.*`). Cause remains unresolved.
The device active flag is not evidence of successful peer discovery. The user then separately authorized a bounded packet capture and one idle Wi-Fi retry;
its disposition is below.

## Recovery, final browser identity and repeated assessment

`wifi-precheck.*` established the exact inhibited/idle/disabled state before the
approved single Console WIFI OFF/ON. Both commands succeeded. The Mac capture
failed to start because sudo required administrator authentication (`wifi-capture.*`);
no captured goodbye or peer cache-expiry evidence exists. `wifi-postcheck.*`
reported enabled Wi-Fi, active short name, registrations 2, goodbye attempts 1,
same boot and inactive/unowned state. Mac system resolution succeeded on en0 at
192.168.1.47, TTL 120 (`mac-wifi-recovered-dns.*`). Linux NSS initially succeeded
after the cycle, then failed again (`final-linux-nss.*`, exit 2). The first result
was not a lasting repair and B2 remains FAIL. No additional cycle was performed.

Chrome subsequently loaded the short URL and authenticated with the existing
operator-browser certificate. Native site information reported secure connection
and valid certificate. The actual Chrome certificate viewer showed SHA-256
06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016,
DNS SAN wsprrypico-0a60df.local, the expected per-device CA and validity from
2026-09-08 23:34:01 UTC to 2027-09-08 23:34:01 UTC. Its current-origin details
showed TLS 1.3, X25519/AES_128_GCM and ECDSA/SHA-256. Connected status showed empty
job, inactive output, available owner, inhibited engine and advertised short name.
`browser-short-name-observation.json` is a manually recorded summary of those
actual UI observations; raw UI output remains in the task record.

The browser's aggregate DevTools overview also showed an insecure label and
origin details noted CT noncompliance. These diagnostics are retained alongside
the native valid/secure site information. Chromium's
[CT documentation](https://chromium.googlesource.com/chromium/src/net/%2B/HEAD/docs/certificate-transparency.md)
explains that manually installed private CAs do not require CT. No CT policy,
extension or certificate-warning bypass was applied. Unsupported raw-CDP
certificate retrieval and an empty/truncated event capture were not used as
certificate evidence. Earlier NXDOMAIN and ERR_BLOCKED_BY_CLIENT navigations
remain recorded; later direct address navigation succeeded.

`final-usb.*` at 23:55:43 UTC confirms the short-name image and boot, inactive
output, empty/unowned state, unchanged disabled schedule/watermark and enabled
Wi-Fi. `final-ip-dns-identity.*` returned HTTP 200 with explicit IP, short DNS
identity and matching HTTP authority after recovery; independent USB WTP identity
still matches. This supplementary OpenSSL result does not qualify the Pi application
or resolve the recurring Linux NSS failure. The browser page is retained and
DevTools/certificate panels are closed.

Final host inventory (`final-linux.*`) retains the original active service PID
239923, installed executable hash and independent checkout revision. A new
owner-only idle controller INI stages the short name without altering the older
file; exact hash is in the joint plan. Source review found production's unconditional
singleton port 1234: choosing different HTTP/socket ports does not allow an
isolated second application process. A separate suitable Linux client or a safe,
explicitly approved existing-service pause/restart is required before B3.
No service was stopped and no production executable or finite job was invoked.

The final assessment checked actual certificate-viewer identity against the
hashed image bundle, preserved full device/boot checks and failed peer history,
confirmed no hosts/resolver/trust-policy bypass, and kept capture failure separate
from goodbye counters. Tooling/docs findings are repaired and tested. Recurring
Linux discovery is an unresolved actionable physical finding requiring packet
evidence; no source cause or speculative firmware repair is claimed. Phase 11.4
cannot close on these results.

## Hardware-free validation

All logs below are in the private evidence root. Existing local dependencies were
used; no SDK download, package installation or service setup occurred.

| Command/check | Actual result |
| --- | --- |
| Fresh Debug CMake `build/phase11-4-host`, pinned Mbed TLS/TinyUSB, existing offline-analysis Python, clean Pi client at 2e47641 | Configure/build PASS; benign duplicate static-library linker warning retained |
| `ctest --test-dir build/phase11-4-host --output-on-failure` | First attempt 31/33 PASS, two loopback startups failed under sandbox; `host-ctest-first.log` |
| Same build `ctest --rerun-failed --output-on-failure` with permitted loopback | 2/2 PASS, 36.18 s; `host-ctest-retry.log`; aggregate all 33 passed, original failure retained |
| Included clean-pinned `network_11_1_interop` | Actual Pi client/TLS and Pico server/core over loopback PASS, not hardware; Mac second-address limitation retained |
| `python3 scripts/validate_wtp_contract.py` | PASS; `contract.log` |
| `cmake --build build/phase11-4-firmware --target WsprryPico --parallel 4` | PASS; exact candidate in plan, `firmware-configure.log`/`firmware-build.log` |
| `check_standalone_image.py`, offline picotool, ELF symbols | PASS layout/inhibited target checks; actual flash followed separate approval |
| Pi protocol/plan/USB/backend/scheduler/status/application suites | PASS; `pi-core.log`, synthetic peers/USB only |
| Pi TLS/production/runtime/API/process suites, simulated ancillary-free profile | PASS; `pi-network.log`, 34 TLS cases, 1995 production and 2012 rotation checks |
| Pi portable semantics with hardware guard | PASS; `pi-semantics.log`, explicitly portable subset, including 23 publication tests |
| `python3 tests/network_certificate_tests.py` after export repair and MAC-alias coverage | PASS; `certificate-mac-alias-tests.log`; actual package decode, same identity, wrong-password rejection, non-overwrite, alias SAN and full manifest ID checks |

No memory/lifecycle runtime change required a new sanitizer campaign. The prior
11.3 sanitizer evidence is historical and not relabeled as a run here. Pi's
opposite-direction exact-source rebuild has not been repeated for these tooling/docs
changes; its pin remains intact. No remote CI result is claimed for this attempt.

## Documentation Impact

Updated: joint plan, expanded acceptance procedure, this review, standalone
guide, network-control certificate/alias guidance and Phase 10 host acceptance's
current network-polling explanation;
companion Pi review records its owned evidence and remaining host gates.
Considered unchanged: README/CONTRACT/architecture, implementation roadmap,
normative WTP/1, shared browser API and identity contract,
mDNS guide, historical 11.2/11.3 and USB evidence. Their scope/identity limits
remain binding. No UI source changed. The limited live visual observation above does not close
the remaining browser behavior cases.

Inspected Wsprry_Pi_Docs read-only. Exact follow-up, without edits/publication:

- `docs/Advanced_Operations/ini_configuration/transmitter_backends.md`: network
  keys, DNS versus IP identity and Linux NSS prerequisites.
- `docs/Command_Line_Operations/transmitter_backends.md`: explicit network
  transport, finite workloads, independent clocks and recovery.
- `docs/User_Interface/Setup/Transmitter/index.md`: current Connection/identity
  fields, development visibility and retained drafts.
- `docs/User_Interface/Operations/index.md`: DHCP/conflict/reconnect observations.
- `docs/Advanced_Operations/rest_api.md`: protected shared resources/revisions and
  host/Pico authority distinction.
- `docs/User_Interface/Maintenance/network_safety.md`: device trust, failed
  observations and separately authorized Console recovery.

## Remaining gates and final-state boundary

Consult the matrix for each required case. Single-board availability prevents
two-board acceptance. Router, production invocation, job/fault, additional renewal, config/persistence
and cleanup approvals are independent of baseline and alias flashes. The latest
USB observation is the short-name image, inhibited, inactive/unowned and schedule
disabled. Chrome and explicit-IP HTTPS passed after recovery, while final Linux NSS
failed. The timestamped final state and remaining discovery gate are recorded above.
The original wspr5 service/configuration has not been changed. Private new files
are retained for this acceptance; the approved CA and separate browser identity remain in the login keychain.

Phase 11.5 resource/contention, 11.6 conducted RF and 11.7 final joint closure
remain open. Phase 12/13 remain outside this task. Repository publication and
final working-tree/parity results are reported with the commits, not assumed here.


The user subsequently reported that the hostname resolves fine. The report is
retained as current user evidence without assuming its client. One prompted
wspr5 recheck (`user-resolution-recheck.*`) again returned exit 2; this is specific
to the tested Linux NSS path, alongside successful Mac resolution and Chrome
operation. It is not evidence that the hostname fails for every client.
