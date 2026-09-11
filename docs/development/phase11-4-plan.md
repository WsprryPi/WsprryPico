# Phase 11.4 joint inhibited acceptance plan

Status: **CLOSED within the bounded inhibited acceptance scope**. B2 and D2 pass
the [controlled native Linux campaign](phase11-4-three-radio-results.md), and the
[full eight-hour soak](phase11-4-controlled-soak-run.md) passed with reviewed
continuity, stable memory and verified restoration. Physical results belong to
the single matrix below; software checks cannot close its gates. Phase 11.5–11.7
remain separate. This plan coordinates WsprryPico and WsprryPi.
See [procedure](phase11-4-acceptance.md), [Pico review](phase11-4-review.md) and
the companion WsprryPi `docs/development/phase11-4-review.md`.

## Source and evidence identity

Initial local checkouts were clean `devel`, including staged/unstaged/untracked
inspection. Remote `refs/heads/devel` was independently read on 2026-09-08:

- Pico: `a9662c3f8323bba64986ff26972d43570af145b4`.
- Pi: `2e47641f6ebdff104e32999f5194f2e0dc408e06`.
- Baseline runtime pair is Pico `d8cde03f8127b3c2aaf727f2c21c20960f658e84` and Pi
  `efcc792cb45780c8b87ebfa83838ecb9eb9cdf47`. Actual diffs establish that the
  subsequent commits change documentation/test/reference support, not runtime.
  Preserve the exact companion gates; do not repin both to later metadata HEADs.

Private evidence root for this attempt is
`/Users/lbussy/GitHub/WsprryPico/build/phase11-4-evidence/` (owner-only, ignored).
Each attempted operation must retain start/end UTC, exact argv, exit status,
raw response/log path and SHA-256. A retry gets a new attempt name; never overwrite
the first failure. Each physical attempt adds source/ELF/UF2/executable hashes,
device/boot/session/job identities, client interface/address and certificate
fingerprints. Keep screenshots, keys, PKCS#12, firmware and private configuration
outside Git. Sanitize summaries before committing them.

## Equipment and authority ledger

The user identifies the sole Pico 2 W as the original board attached to `wspr5`;
Chrome on this Mac is the browser. No second board is available. Existing private
Wi-Fi files are under `config/local/`; do not print their contents or overwrite
stored device configuration from an old file.

Read-only OS inventory on `wspr5` confirmed USB serial `0BF4B4AEC9FFB344`:

- Console interface 00:
  `/dev/serial/by-id/usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00`, currently
  `/dev/ttyACM1`.
- WTP interface 02: same alias ending `-if02`, currently `/dev/ttyACM2`.
- Separate GPSDO interface is not part of this acceptance and must not be opened.

The user separately authorized bounded read-only USB INFO/STATUS and WTP
HELLO/CAPS/GET_CLOCK/STATUS/PING. That permission persists. It does not authorize
CLAIM, ABORT, flash, reboot, configuration writes or network faults.
Read-only inventory and USB inspection made no remote file changes.

Client inventory: Mac macOS 26.6.2 (25G83); `dns-sd` installed. Linux `wspr5`,
Debian 13.6 aarch64, kernel `6.18.34+rpt-rpi-2712`, interface `wlan1`, observed
address `192.168.1.117/24`. NSS `hosts` uses
`files mdns4_minimal [NOTFOUND=return] dns`; `getent` exists, while the inspected
PATH has neither `resolvectl` nor `avahi-resolve-host-name`. The actual baseline NSS result is recorded in B2 below.

Existing `wsprrypi` service is active, root-owned, running
`/usr/local/bin/wsprrypi -J -i /usr/local/etc/wsprrypi.ini`. Its executable hash
is `0c8d2a578a766d2b8292467a0c41babd39ae27196a707d8cc701565815f52bdf`;
the separate Linux checkout is at `f210e4d165e0e30f94ee9332e70af45e0367e4cb`.
The reviewed network runtime commit was unavailable in that checkout's object
database. Do not treat this binary as the reviewed network candidate or move
that checkout. Any private host staging/build/invocation, service or installed
configuration action requires its own concrete authorization.

## Initial observed state and candidate

Authorized initial USB inspection returned matching Console/HELLO device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5` and boot
`2b655f956ecdaabdd2f204be0b3662d0`. Console revision is `a3ec67d059b3`, firmware
`0.0.0-devel`; CAPS engine is `inhibited-standalone-simulator`. STATUS is `empty`,
`output_active:false`, no owner/job or terminal records. Storage is healthy;
autonomous scheduling is disabled, with retained 120-second schedule and watermark
`1788714601000000000`. Device clock was synchronized, normal leap, approximately
166 ms uncertainty and 45 s sample age. These are dated observations, not continuing
output authority. The old firmware does not supply the new deployment diagnostic.

Baseline candidate (separately approved and flashed; historical identity):

- Standard **WsprryPico** only, Release `pico2_w`/RP2350 ARM Secure;
  source/embedded revision `a9662c3f8323`, built before documentation edits.
- ELF: `build/phase11-4-firmware/firmware/WsprryPico.elf`, SHA-256
  `c169f5e9facec8b5f8367c93cb851503d42867885bf06a5e68b7f1fec3d66cf6`.
- UF2: same directory `WsprryPico.uf2`, SHA-256
  `3f65842af62b94fd0c34c8c2f5a9e50cd316aa479e7d8b88552d19396181926f`.
- SDK `98a542c1a62fb549ffb5d66a3e5892b06276b670`, Arm GNU 15.3.1;
  profile 138 MHz limits, with no physical RF clock selection in this image.
- New private per-device CA/server/controller/browser bundles:
  `config/local/network/phase11-4-fd6127d1/`. The same CA and browser identity were subsequently imported with explicit approval.
- Port 18443; certified hostname
  `wsprrypico-fd6127d11d6aca42a9905fa3fb1bf1d5.local`, no IP SAN.
- Server fingerprint
  `9e283308ec8d312b475ec9a71f71f31e4c843764c69e22386ae4bae4ef648416`.
  `deployment.json` and actual certificate were validated together.
- `check_standalone_image.py` passed stack/heap/journal/UF2 checks. Linked symbols
  show DryRunEngine and no StreamEngine/PicoPioDma/start_worker. Offline picotool
  identifies `Standalone RF-inhibited a9662c3f8323`. No installed-flash hash is
  claimed from the supplied UF2 hash.

## Physical execution packets

Approve operations only after their exact paths/images/client identities are
filled in. The procedure expressly requires separate device/USB/flash/router/
trust/service authorization. Related operations can be approved together; do not
re-ask for an approved scope. Only the ungranted packets remain pending. The ledger below records approvals already exercised.

1. **Baseline deployment:** refresh authorized read-only state immediately before
   mutation. Stage only the approved UF2 and audited helper in a new private
   directory on wspr5, check transferred hashes, use its existing
   `/home/pi/phase10-wtp-acceptance/picotool-build/picotool` only after inspecting
   its version/options. Console BOOTSEL and flash must target the same serial;
   refuse ambiguity. Program application pages only, never erase journals. Reboot
   into this candidate and verify A1/A2. Do not restore an RF image as cleanup.
2. **Host/client/trust:** build the reviewed Pi source in an isolated private
   Linux directory; record binary hash and build profile with ancillary GPIO
   excluded. Prepare a separate complete INI with WTP network selection, exact
   DNS/device IDs and controller paths, zero PPM, all local GPIO/amplifier/LED/
   selector/fades off, boot/repeat/transmit disabled initially. Do not run the
   production network client with `WSPRRYPI_DISABLE_HARDWARE_ACCESS=1`: it must
   reject before DNS/socket use. Physical invocation needs explicit authorization.
   Avoid conflicting listeners; specify an isolated port before exposing the
   shared UI. Installed service/configuration changes require a separate packet.
   Browser import packet must identify exact CA fingerprint and separate browser
   PKCS#12, keychain and cleanup. Enter its export/import password privately.
3. **Finite jobs:** propose at most 16 jobs per approval, each at most 30 seconds,
   single complete tone/QRSS job at nominal 3,570,100 Hz, total at most 480 seconds
   of inhibited lifecycle. Reconcile CAPS first; never use continuous Test Tone.
   Actual production CLI job shape must be derived from supported finite QRSS
   settings; bounded Tone is a runtime API feature, not the Test Tone CLI.
   Use 500,000,000 ns request budget only when explicitly approved and admitted by
   fresh device/host clocks. Allow at least 8 s preparation and negotiated minimum
   lead plus 7 s; reject a missed budget instead of silently shifting a job.
   Keep job IDs, complete LOAD bytes/results and ARM tuples. Direct browser jobs
   and production-host jobs use separate principals and sessions. Inhibited
   Running still reports output false; it is not an electrical timing measurement.
4. **Faults/renewal/persistence:** approve endpoint-specific transport interruption
   and response-loss instrumentation only with a concrete finite timeout and
   cleanup. TLS stays end-to-end authenticated; ciphertext loss alone cannot prove
   which WTP response was lost. A response-layer case needs matching client/device
   operation evidence. Approve every renewal/wrong-board/IP-SAN image separately
   by hash. Persistent config/schedule changes need an exact before/after record,
   preserved password, schedule history and watermark. Restore only that approved
   delta. Restart/power cycle requires prior inactive/unowned evidence.
5. **LAN/conflict:** real DHCP reassignment must be limited to this Pico lease on
   an identified router; never edit hosts, rely on a reservation for normal operation,
   or disrupt wspr5's LAN. A specifically authorized Pico-only temporary reservation
   may force a real DHCP transition, provided it is removed and cleanup verified.
   Bound peer captures and diagnostics. The missing second board blocks two-board
   acceptance. An approved host alias responder can test a narrower conflict
   mechanism, but cannot establish independent physical per-device trust.

## Single-board execution update

The user authorized all tests and then specifically authorized the bounded
installed-service pause; Mac unlock and shared Wi-Fi/DHCP were confirmed.
The comprehensive [execution prompt](phase11-4-single-board-prompt.md) was rendered
and executed. The [single-board record](phase11-4-single-board-run.md) records
actual results, original failures, image hashes, repairs and current blockers.
Its evidence root is `build/phase11-4-single-board-evidence/`; older paths below
remain under `build/phase11-4-evidence/`. This table is the current joint status;
historical paragraphs after it retain earlier attempts and approvals.

## Joint case matrix

Each case uses the identity ledger above and its own attempt record. `A0` refers
to the installed pre-candidate image; all other device results must bind the
candidate actually used. Evidence names below are relative to the private root;
`pending` means no attempt. A PASS requires the expected observation, not just
exit zero. BLOCKED identifies an absent prerequisite; NOT RUN means prerequisites
are available but the test has not executed. Defects/retests are appended, never
substituted for earlier attempts.

| ID / requirement | Equipment / authorization | Procedure and expected observation | Evidence / status | Defect / retest |
| --- | --- | --- | --- | --- |
| Eight-hour soak | Inhibited Pico A; onboard AP and independent USB Linux client; Ethernet management | Full uninterrupted interval, stable comparable memory, authenticated reads and verified restoration | PASS: 5,593 USB INFO, 467 WTP checks, 740 DNS/HTTPS checks; no recorded failures; stable post-warm-up memory | [Reviewed soak](phase11-4-controlled-soak-run.md); all observers closed cleanly, both captures zero drops, host/Picos restored |
| A0 current state | Sole board + authorized read-only USB | Cross-check Console INFO/STATUS with HELLO/CAPS/clock/STATUS; matching device/boot, explicit inactive/unowned and saved scheduling | `usb-authorized.*`; PASS for old image | SSH sandbox failures retained in `usb-initial*`; explicit-IP SSH succeeded, not mDNS acceptance |
| A1 candidate inhibition/identity | Approved exact image, flash/reboot and USB | Check CMake/ELF/UF2, transfer hash, flash selected serial, fresh INFO/HELLO/CAPS/STATUS; correct revision/engine and deployment match, inactive/unowned, journals retained | `postflash.*`, `flash.*`, `mac-postflash.*`, `mac-flash.*`, `final-usb.*`; PASS both approved images | Exact programmed data verified by picotool; preserve original image evidence |
| A2 device UTC gating | Candidate + USB/network reads | Record SNTP and GET_CLOCK before TLS, reject unsynchronized or excessive-uncertainty dependent jobs; no time falsification | PASS bounded device scope: synchronized 1 ns rejection, expired-holdover and naturally unsynchronized ARM rejection; real SNTP recovery and finite positive completion | [A2 completion](phase11-4-a2-results.md) binds same-boot USB evidence; earlier `jobs-attempt-1` and boot-unsynchronized observations retained; no clock falsification |
| B1 Mac system mDNS | Candidate + Mac LAN resolution | Bound `dns-sd -G v4` to 15 s, record interface/current address and failures; corroborate no hosts entry | `mac-dns-sd.*`, `mac-wifi-recovered-dns.*`; PASS observed baseline and recovered short name | Real interface 14/en0 answer; 15 s bound; initial short-name failures retained, no sustained-discovery claim |
| B2 Linux NSS mDNS | Candidate + two independent wspr5 native Linux clients | Bound native lookup and authenticated recovery across repeated cycles | PASS controlled Linux scope: eight consecutive same-boot cases, two independent resolver caches, five authenticated recovery checks per peer/case | [Three-radio acceptance](phase11-4-three-radio-results.md); historical infrastructure evidence retained; [eight-hour soak passed](phase11-4-controlled-soak-run.md) |
| B3 production integration | Approved isolated Linux build/config/invocation | Hash real executable, configure exact endpoint/CA/controller/device; observe fresh resolved/authenticated/WTP identities and startup inspection | PASS exact isolated application hostname and IP+DNS startup/management; `host-production-attempt-{2,3,5}.*` | Service pause specifically approved and restored; retained build/wrapper failures in single-board record |
| C1 real browser trust | Approved CA/browser identity/keychain import | Chrome hostname HTTPS, inspect SAN/issuer/validity/fingerprint and client selection; no bypass/proxy | PASS short-name Chrome status, client selection, SAN, issuer, validity, exact fingerprint and TLS 1.3; `browser-short-name-observation.json` + task UI record | Default PKCS#12 and scoped trust failed; compatibility export and explicitly approved CA SSL trust passed |
| C2 concurrent status/authority | C1+B3+approved finite jobs | Persistent WTP plus browser reads in Loaded/Armed/Running; foreign mutation rejected, owner accurate; failed read becomes unknown | PASS bounded scope: actual Chrome Loaded with a controlled production pause, prior Armed and current Running/Complete; foreign HTTPS `NOT_OWNER`; deployed failed read becomes Unknown | [C2 completion](phase11-4-c2-results.md) binds deployed `23ac5b1` and timing limits; [prior coverage](browser-production-coverage.md) preserves original attempts |
| C3 revisions/drafts/secrets | Approved exact idle config/schedule delta | Save/load with ETag, stale 412 and missing 428, preserve drafts and redaction through both paths; compare saved config | PASS bounded production management writes, Chrome stale draft/reload, exact baseline+ETag restoration; prior direct cases retained | [Coverage record](browser-production-coverage.md); transient 409 and invalid-power 400 retained; no general availability claim |
| C4 deferred network change | Approved idle Wi-Fi off/on | Observe complete response ACK before application, aborted response cancels, recheck idle; restore with Console | PASS bounded transaction scope: complete-response ACK before observed disable, pre-ACK reset cancellation, unrelated-close isolation and new-owner idle recheck; zero-drop captures | [C4 completion](phase11-4-c4-results.md); original failed GET retained; post-WIFI-ON TCP timeout required one additional recovery cycle, so connectivity reliability remains open |
| D1 real DHCP reassignment | Controlled AP and independent native Linux/Chromium peer selected by user | Record old/new lease, same name/CA/server fingerprint/device; peer resolution, advertisements, browser status and production connection use new IP, no duplicate submission | PASS native Linux/Chromium scope: same-boot .10 → .20, current native resolution, authenticated WTP/HTTPS, same-process/tab secure browser status reload and actual production client; macOS compatibility untested | [Native browser completion](phase11-4-browser-d1-results.md): onboard AP/USB peer, verified Bohica-IoT/host restoration; no LOAD/ARM |
| D2 orderly disable | Approved idle Wi-Fi off/on; onboard AP and two USB clients | Actual goodbye, native cache withdrawal, same-name probing and repeated recovery | PASS controlled Linux scope: eight full 150-second outages; matching TTL0 A/PTR at all three NICs, distributed native negatives, three recovery probes and authenticated recovery | [Three-radio acceptance](phase11-4-three-radio-results.md); no campaign reboot, zero capture drops; historical evidence retained |
| D3 actual link loss | Explicitly approved Bohica-IoT outage; Wi-Fi-only management accepted | No successful goodbye claim after loss; record peer expiry, recovery/address/state and finite-job/owner continuity under terminal lease rules | PASS bounded: actual link loss, native Mac removal/Linux negatives, same-boot recovery and active inhibited-job completion | [D3 execution](phase11-4-d3-results.md); first job non-overlap, second recovery timing gap, cross-host TTL limits and separate Chrome failure retained |
| E1 distinct boards/trust | Two identified Pico 2 W boards with independent CAs | Distinct MAC-suffix deployment names/full WTP IDs and bidirectional trust acceptance/rejection | PASS bounded: three rounds per board on Mac and Linux; 12 WTP sessions, 48 HTTPS controls, 36 intended TLS rejections | [E1 execution](phase11-4-e1-results.md): boot-derived short default implemented on B; A retains existing short certificate and old diagnostic; bootstrap watchdog/discovery failures retained |
| E2 alias conflict during job | Approved second board or exact alternative responder | Certified alias conflict; actual winner/loser, no suffix, finite inhibited job continues | PASS controlled host claimant: Pico latches conflict/empty advertised name while original TLS-owned job completes; no rename or duplicate LOAD/ARM | [E2/E3 record](phase11-4-e2-e3-results.md); single-Pico alternative, not E1 two-board trust evidence |
| E3 conflict recovery | E2 + approved idle retry | Remove claimant, prove latch, release owner, WIFI OFF/ON, capture same-name probes/announcement and verify peers | PASS: captured claimant withdrawal, retained conflict latch, three Pico probe datagrams and cache-flush announcement; Mac/Linux resolve only Pico and authenticate | [E2/E3 record](phase11-4-e2-e3-results.md); unchanged boot/configuration; not D2 Pico goodbye/cache-expiry evidence |
| F1 server renewal | New same-CA bundle + approved exact reflash | Same device/DNS identity/CA, new fingerprint/validity, existing valid clients and DHCP workflow continue | PASS same-name same-CA renewal and original-client reads; `flash-renewal-1`, `renewal-clients-1` | Altered-value persistence verified; actual DHCP reassignment remains D1 |
| F2 client replacement | Separate client identities and approved browser import | Rotate after authoritative idle cleanup; replacement works, old valid identity still trusted | PASS: actual Chrome replacement leaf selected; replacement and original production finite jobs complete with cleanup | [F2/F3/F6 record](phase11-4-f2-f3-f6-results.md); issuance is not revocation; same CA retained |
| F3 identity failures | Bounded negative TLS requests, verified server and valid UTC | Wrong name/CA, missing/untrusted/expired client and absent IP SAN reject at intended layer | PASS on repaired inhibited images: alerts 116/48/45; client mismatch 62/20/64; HTTP 200 controls | [F2/F3/F6 repair and retained failures](phase11-4-f2-f3-f6-results.md); SDK remains unchanged, hash-checked build overlay |
| F4 wrong-board deployment | Separately approved mismatched image | Manifest/certificate internally valid but board ID differs; INFO false, listener/name fail closed, output remains inhibited | PASS runtime mismatched image; `flash-wrong-board-1`, `wrong-board-settled`, `wrong-board-tcp` | Actual full ID retained; listener/name fail closed; recovered with correct image |
| F5 IP with DNS identity | Approved production TLS/HTTP reads | Known IP + expected DNS authenticates DNS SAN and hostname Host/Origin; independent WTP device check | PASS actual production IP+DNS authenticated identity and management, with independent WTP ID | OpenSSL-only and earlier timeout evidence remain separate; does not replace mDNS |
| F6 literal IP SAN success | Exact temporary IP-SAN image and actual Chrome URL | Matching IP SAN authenticates numeric browser URL and HTTP authority | PASS: Chrome secure/valid IP origin, matching server fingerprint and live boot/status | [F2/F3/F6 record](phase11-4-f2-f3-f6-results.md); hostname-only certificate restored with TLS fixes retained |
| G1 finite completion | Approved bounded host and direct-browser jobs | Complete CAPS-valid LOAD before ARM; matching job terminal STATUS and explicit inactive output | PASS actual Chrome completion and corrected production 60-second-lead finite completion with authoritative cleanup | [Coverage record](browser-production-coverage.md); original silent-wait failure and earlier wrapper failure retained; inhibited only |
| G2 cancellation/foreign owner | Approved bounded jobs and owner mutations | Loaded/Armed/Running ABORT where supported; foreign ABORT/RELEASE rejected; explicit owner cleanup | PASS earlier direct Loaded/Armed/Running, actual Chrome Armed/Running, production Running cancellation, foreign HTTPS rejection | [Coverage record](browser-production-coverage.md); late Chrome/expired-lease attempts retained; browser Loaded-only action is not exposed |
| G3 loss after acknowledged ARM | Approved endpoint-only connection cut | Device completes autonomously; reconnect same session with HELLO+STATUS, retain ownership/terminal proof | PASS direct acknowledged-ARM disconnect and same-session autonomous completion reconciliation | Output unknown during disconnect; matching terminal and inactive/unowned cleanup then proven |
| G4 lost LOAD/ARM/ABORT replies | Audited bounded response-loss mechanism | Prove request reached device and response delivery was prevented; exact request replay after STATUS | PASS: per-socket BPF drop, zero-drop PCAP, independent USB effect and same-session exact replay for all three operations; one terminal job record | [G4–G7 record](phase11-4-g4-g7-results.md); direct WTP wire-loss evidence, separate from production G5/G6 |
| G5 failed DNS/TLS reconnect | Approved isolated controller fault | Retain unknown output/history; no additional LOAD/ARM; explicit original-session recovery | PASS: real production socket cut, resolver EAI_AGAIN injection and actual TLS wrong-name verification failure; original-session recovery preserves failed report | [G4–G7 record](phase11-4-g4-g7-results.md); process-local resolver boundary injection, no LAN DNS outage claimed |
| G6 process/boot/device changes | Approved test-process restart, board restart/identity mechanism | New process cannot adopt old work; changed identity latches without resubmission | PASS bounded single-board scope: new-process nonadoption, real Pico boot change, controlled authenticated endpoint with different WTP device ID | [G4–G7 record](phase11-4-g4-g7-results.md); controlled endpoint is not E1 two-real-board evidence |
| G7 USB versus Console recovery | Explicit owned USB recovery and Console override | USB cannot steal TLS job; Console ABORT suspends scheduling and confirms disable/release | PASS: USB CLAIM BUSY and ABORT/RELEASE NOT_OWNER, unchanged TLS job; Console override produces matching aborted record, suspended schedule and inactive/unowned status | [G4–G7 record](phase11-4-g4-g7-results.md); saved configuration and watermark preserved |
| H1 persistence | Approved saved delta and restart/power cycle | Config/schedule/watermark retained, no repeat, fresh boot; compare before/after and terminal evidence before reset | PASS disabled 240/120 delta persisted through renewal; original 120/0 restored and retained across three later flashes | Healthy storage and unchanged watermark; boot-local terminal history recorded before reset, not claimed persistent |
| H2 final cleanup | Approved cleanup set + read-only verification | Verify both devices inactive/unowned and saved state; restore host routes, profiles, power and services | PASS: both Picos verified, A returned to Bohica-IoT and B unchanged; all radio/host settings restored; Ethernet and three ordinary Wi-Fi SSH checks pass | [Latest restoration](phase11-4-three-radio-results.md); no campaign process, namespace, temporary AP or test NTP allowance remains active |

## Subsequent approvals, client evidence and shorter-name candidate

The user authorized and we completed baseline staging/flash/reboot, CA and separate
browser identity imports, browser read-only operation, and isolated production-host
source/controller staging and build. Initial hostname-scoped CA trust did not work
in Chrome. Automatic approval review rejected widening it without explicit consent;
the user then explicitly approved SSL trust for this device CA. That change succeeded.
CA SHA-256: `2ef7ec890d48e9283286ee09c6b549756f3d3cff530e5cb030ced6ae4c40442b`.
Browser identity SHA-256:
`499676f4c6e5639c950a7a388d69af0f8c31d3875534f90feb2edb566997fef4`.
Both remain in the Mac login keychain as authorized. No other trust was changed.
Chrome displayed Connected, empty job, inactive output, available owner and the
inhibited engine. Security panel explicitly reported valid/trusted HTTPS, TLS 1.3,
X25519/AES_128_GCM and the expected per-device CA. These are baseline observations;
short-name browser acceptance needs a new observation after the new flash.

The isolated Linux source is clean Pi 2e47641, cloned from a full Git bundle into
`/home/pi/phase11-4-acceptance/source-git`. Build command from its `src` directory:
`make release BACKENDS=simulated ANCILLARY_GPIO=0 SUDO=`. Executable:
`src/build/bin/pi-reviewed-source` (name derives from the bundle's remote name),
SHA-256 `3acd44dd6a8933cc816604a4514d8517e7586a2da40bff628378e080af5c6857`.
No production invocation has occurred. The archive-only build failed because the
release target requires Git metadata; `host-build.log` retains it. The full-bundle
build passed (`host-build-git.log` on wspr5). Original checkout/service are intact.

The user requested a much shorter hostname and proposed a MAC suffix. This
acceptance uses the existing deliberate alias mechanism, leaving the full-ID
default and full board identity checks unchanged. `arp -n 192.168.1.47` on the Mac
reported station MAC `88:a2:9e:0a:60:df` on en0; this is peer-cache evidence, not a
new on-device MAC diagnostic or trust source. Last six lowercase hex characters
give **`wsprrypico-0a60df.local`**. A suffix can collide; normal conflict handling
remains required. The preliminary 12-hex device-ID-default edit was withdrawn
before deployment. No runtime source or companion pin changed.

Replacement candidate (subsequently explicitly approved and flashed):

- Same standard RF-inhibited WsprryPico target and unchanged a9662c3 runtime.
  Embedded revision `a9662c3f8323-dirty` reflects tracked tooling/docs work.
- New bundle `config/local/network/phase11-4-fd6127d1/server-mac-suffix`, same CA,
  full device ID and existing clients; DNS SAN exactly `wsprrypico-0a60df.local`,
  no IP SAN. Server fingerprint
  `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
- Build `build/phase11-4-mac-suffix-firmware`, configure/build logs and UTC argv
  manifests `mac-suffix-configure.*` / `mac-suffix-build.*` in private evidence.
- ELF SHA-256 `f968b3462b635f76c3d2a3667400146a28e28c61a83c9b84d2dbe4cc9a2176bf`.
- UF2 SHA-256 `68b617ca7efdcbea65cd7a592d93f346d560aa0aef1e8e16e65d6f2add9d3ca6`.
- Layout/journal check PASS; DryRunEngine present, physical RF engines absent,
  `WSPRRY_PICO_RF_OUTPUT_DISABLED=1`. Credentials remain ignored/private.

Concrete migration packet: fresh authorized Console/WTP reads must match the
baseline board, inhibited engine, inactive/unowned state and saved disabled
schedule/watermark. Stage the new UF2 under a distinct filename in the existing
private wspr5 acceptance directory, verify the exact hash, send Console BOOTSEL
only to serial 0BF4B4AEC9FFB344, and use the same existing picotool with `load -v -x`
and `--ser` selection. Preserve journals. Reboot and repeat INFO/HELLO/CAPS/STATUS,
Mac system and Linux NSS resolution plus authenticated Chrome status at the new
hostname. Existing approved CA/browser imports cover the same identities; no new
trust import is needed. No jobs, configuration writes or service changes belong
to this migration packet. No old/RF image is restored as cleanup.

## Review and exit

Before publishing results, independently re-read source and evidence for cached
DNS/hosts overrides, stale executables, wrong-board admission, TLS versus WTP
identity, negative-case layer, replay/ownership/unknown handling, preserved failed
attempts, actual DHCP/conflict packets, authorization and secrets. Fix actionable
findings, rerun affected deterministic tests and invalidate physical results tied
to a changed runtime. Record each assessment in the review files.

Phase 11.4 closes only when required physical cases pass. Phases 11.5 measured
target resources/contention, 11.6 conducted RF and 11.7 final joint closure remain
open. Phase 12 provisioning and Phase 13 qualification/release are outside scope.

## Documentation Impact

Update this joint plan, acceptance procedure and both review records as evidence
arrives. Review standalone/host acceptance guides for obsolete image assumptions.
Keep normative WTP/1, shared identity and host idle-management contracts unchanged.
The separate operator repository is read-only. Required follow-up paths are listed
in the review records; no manual edits or publication are authorized here.

## Short-name reachability failure and proposed bounded diagnosis

The authorized short-name flash and USB verification passed (`mac-flash.*`,
`mac-postflash.*`). New boot: efa316aecb3f7c9e29484eca66e068d3. Configured/advertised
name is wsprrypico-0a60df.local, deployment match true, same 192.168.1.47 address,
clock samples continue, no owner/job/output and preserved disabled scheduling.
The initial short-name peer result was **FAIL**, not overridden by the device's active flag:
Linux getent returned 2, Chrome reported DNS_PROBE_FINISHED_NXDOMAIN, Mac dns-sd
showed no answer within the bounded attempt, and explicit-IP HTTPS timed out.
The first piped dns-sd output was not flushed at termination; the PTY retest
retains its starting header and lack of answer. Mac route inspection reported
REJECT for the cached ARP host route. The cause has not been established.

Recovery/diagnosis packet, subsequently explicitly approved and attempted:

- Read and record fresh INFO/STATUS and WTP STATUS on the same approved endpoints;
  refuse mutation unless inhibited, empty, inactive, unowned and schedule-disabled.
- Capture at most 45 seconds on Mac en0, restricted to ARP involving 192.168.1.47
  and UDP 5353 involving the Mac/Pico addresses. Store capture privately under
  the existing ignored evidence root. No TLS payload or unrelated interface.
- Send one Console WIFI OFF and then WIFI ON on serial 0BF4B4AEC9FFB344, with
  exact device/revision checks. These alter volatile Wi-Fi enable state only;
  do not persist configuration, reset journals, submit jobs or reboot.
- Repeat bounded Mac/Linux name resolution, Chrome read-only HTTPS and USB
  state. Preserve failed attempts. Finish with Wi-Fi enabled and authoritative
  inactive/unowned status; stop dependent mutations if recovery fails.
- No router/DHCP/hosts/cache changes or service actions are included. A goodbye
  attempt counter alone does not prove the Mac received a goodbye packet.


## Recovery disposition, final observations and next gates

The user authorized the single WIFI OFF/ON and bounded capture packet. Fresh
inhibited/empty/inactive/unowned guards passed; both Console commands succeeded.
Capture could not start: `sudo -n tcpdump` required local administrator
authentication. No packet file or successful goodbye delivery is claimed.
`wifi-capture.*` retains that failure. Wi-Fi finished enabled; mDNS reprobed active
with registrations 2 and goodbye attempts 1. Boot, saved scheduling and watermark
were unchanged. The Mac resolved the short name on en0, address 192.168.1.47,
TTL 120 (`mac-wifi-recovered-dns.*`). Linux getent succeeded immediately after the
cycle (task command record), but failed again in the independent final check
(`final-linux-nss.*`, exit 2). B2 remains FAIL; the cause is not established.

Chrome 152.0.7977.83 subsequently loaded Connected status at the short URL, using
the already approved operator-browser identity (serial
4B30B4409ADBF57F6457473C93C9942C). Native site information reported secure connection
and valid certificate. Certificate Viewer and origin security details independently
showed the exact new fingerprint/SAN, expected issuer, validity
2026-09-08 23:34:01 UTC through 2027-09-08 23:34:01 UTC, and TLS 1.3,
X25519/AES_128_GCM, ECDSA/SHA-256. `browser-short-name-observation.json` records the
observation provenance; raw UI evidence is in the task record. The prior browser
NXDOMAIN/ERR_BLOCKED_BY_CLIENT attempts remain failures. No warning bypass,
extension change, trust reimport or certificate-transparency policy change occurred.

At 2026-09-08 23:55:43 UTC, `final-usb.*` confirmed image revision
a9662c3f8323-dirty, boot efa316aecb3f7c9e29484eca66e068d3, same full device identity,
inhibited engine, empty job, output false, no owner, saved scheduling disabled,
watermark 1788714601000000000, Wi-Fi enabled and short name active at 192.168.1.47.
`final-ip-dns-identity.*` additionally returned authenticated HTTP 200 status
using explicit IP plus the short DNS reference/HTTP authority. This does not
remove the separate Linux NSS failure. Browser page is retained for the operator.

The prepared controller now has a distinct, never-invoked
`/home/pi/phase11-4-acceptance/controller-idle-mac.ini`, SHA-256
b425992d6d9d6730eef270dcd8989894c7d25436d1c2b80eeaff81a1e6824ed6.
Only the target hostname differs from the prior idle INI. Production startup
reserves singleton port 1234 before ordinary argument handling; isolated web/
socket ports do not solve coexistence with the running installed service.
Next B3 work therefore needs an appropriate independent Linux client or a
concrete, separately authorized pause/restart plan after authoritative inspection
of the existing service's own output and restart behavior. No singleton bypass
or service pause was performed. Final installed PID 239923, active state,
executable hash and checkout revision matched the initial inventory.

Next physical work: obtain privileged packet evidence for recurring discovery
failure, complete B3 and the protected shared-management/finite-job/recovery
packets, identify a second board or approved narrower conflict mechanism, and
obtain the specific DHCP, certificate-negative/renewal, persistence and restart
approvals. One available board still blocks E1. These are not software passes.


The user subsequently reported that the hostname resolves fine. The report is
retained as current user evidence without assuming its client. One prompted
wspr5 recheck (`user-resolution-recheck.*`) again returned exit 2; this is specific
to the tested Linux NSS path, alongside successful Mac resolution and Chrome
operation. It is not evidence that the hostname fails for every client.
