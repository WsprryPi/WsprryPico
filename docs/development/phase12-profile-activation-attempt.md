# Phase 12 profile activation: Candidate A physical attempt

Status: **native-Pi maximum profile, repaired Bluefy/iPhone activation, and
generation-3 BLE/mTLS readback accepted within this RF-inhibited Candidate A
slice** (2026-09-26 CDT).

This record preserves the first physical failures, their repairs, and the
subsequent RF-inhibited native-Pi and bounded Bluefy/iPhone acceptance. It
does not claim full Bluefy/iPhone, RF, Step 1 or Phase 12 acceptance.
Only Candidate A was operated. Candidate B was observation-only.

## Exact candidate and boundary

- Branch/source: `devel`, `ef33ec27953c`.
- Pico 2 W USB serial: `0BF4B4AEC9FFB344`.
- Device ID: `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- BLE address: `88:A2:9E:0A:60:E0`.
- Firmware UF2 SHA-256:
  `2309fbb310f5077c4cab3882c5c26953370f89dda48b537ed16719b3385969d5`.
- Boot ID after flash: `5a32116cc5eaec5dfab41ff10b57d07c`.
- Engine: `inhibited-standalone-simulator`; WTP state empty; output inactive.
- Initial and post-failure profile: generation 0, factory source, healthy journal.
- Public default local password active; access generation 3.
- `wspr5`: Raspberry Pi 5, Debian 13, Bluetooth controller
  `2C:CF:67:62:76:68`. Management was later reported on Ethernet
  `192.168.1.54`; an older `192.168.1.77` observation is not current.
- Native client initially matched source SHA-256
  `cdfdd584f45dc724ad0a57b35fef84621751286791bb283cc61fe20c971373e0`.
  The operator-facing prompt repair was then installed on `wspr5` with SHA-256
  `11b37fab55444ef11efe505e1e4c1be066d2de366aa095b41cc904a156b95d72`
  and committed as `2e81424`.

## Preserved physical sequence

| Case | Observed client result | Target result |
| --- | --- | --- |
| Deliberately wrong fresh password, 8–63 printable characters | `authentication_required` after staged transfer; the initial expectation of `wrong_password` was incorrect | Generation 0; BLE disconnected; no activation |
| Correct password, no USB confirmation | `confirmation_timeout` | Generation 0; BLE disconnected; fresh `inspect` succeeded |
| Correct password, interrupt at USB instruction | `interrupted` | Generation 0; BLE disconnected; fresh `inspect` succeeded |
| Exact 7,168-byte profile, correct fresh password and identity-bound USB confirmation | USB Console `{"ok":true}`, then BLE `credential_invalid` | Generation 0; factory profile; healthy journal; empty state; output inactive |

The 7,168-byte private input remained owner-only on `wspr5`; its SHA-256 was
`f73da469459ee8174fc2750cb70a089fe0d7f036a7b1c709db42517e5a84f2ac`.
The native client canonicalized it to exactly 7,168 bytes. An ordinary profile
and a 7,169-byte local rejection were prepared separately; neither private
profile content nor any password is recorded here.

The certificate is valid from 2026-09-08 through 2027-09-08, has the exact
device hostname SAN, P-256/ECDSA-SHA256 and server EKU. On `wspr5`, OpenSSL
verified the chain, certificate/key public-key match and identical decoded
certificate and CA between ordinary and maximum-size profiles. These checks do
not themselves qualify Mbed TLS target acceptance. An attempted off-device
preflight was rejected by automatic security review because it would export the
entire private profile; no export occurred.

## Failure diagnosis and repair candidate

The target reported no UTC (`clock_state=unsynchronized`, `utc_now_ns=0`) during
the failed apply. The first profile was being validated before a configured TLS
server existed. In source `PicoServer::start()` installed the Mbed TLS time hook
only after the server was configured; an unprovisioned target returned before
that hook was installed. Certificate-validity verification therefore used an
unset clock and rejected the otherwise current certificate. At that point this
was a source-backed diagnosis, not a physical proof that the repaired image
would accept the exact profile.

The repair installs the disciplined UTC hook at standalone startup, retains it
across TLS server stop/start, and requires a non-unsynchronized clock for a new
profile's strict certificate validation. It does **not** relax date, chain,
purpose, algorithm, SAN or key-pair checks. The native-Pi execution sequence
now calls authenticated `sync-time` before the next valid apply. A host TLS
test forces the clock to zero before any server starts, proves rejection, then
proves accepted UTC permits validation and loss of UTC rejects it again.

## Repaired physical sequence

The repaired source was committed as `3844769f8423`. A clean build embedded
`Standalone RF-inhibited 3844769f8423`; the UF2 SHA-256 was
`efea4ac3b204feb4a56ceef525dcb4762ea4d1b41b7c3370a29e69bf6e95402b`.
Before flash, Candidate A still identified as `ef33ec27953c`, profile
generation 0, healthy storage (config sequence 72, watermark sequence 12),
access generation 3, empty WTP state and inactive output. A serial-targeted
BOOTSEL transition exposed RP2350 chip ID `0x0bf4b4aec9ffb344`; serial-targeted
`picotool load -v -x` verified the new UF2 and rebooted it. Postflash Console
`INFO`, `STATUS`, `STORAGE`, `ACCESS STATUS` and `BLE STATUS` identified
`3844769f8423`, boot ID `7254cc35e44ddb36b8fd124c4fc9168c`, profile
generation 0, the same journal sequences and access generation, healthy storage,
empty WTP state and inactive output. The engine remained
`inhibited-standalone-simulator`. No profile was applied in this boot yet; the
clock was unsynchronized, as expected after reboot.

Authenticated native-Pi `sync-time` on the repaired image returned
`{"accepted":true}`. An authenticated field-status read then reported
`time_source=controller`, `time_disagreement=false`, and finite uncertainty
(`352102498` ns). The owner-only 7,168-byte private file still had SHA-256
`f73da469459ee8174fc2750cb70a089fe0d7f036a7b1c709db42517e5a84f2ac`.
A subsequent BLE transfer reached the identity-bound USB confirmation prompt;
Console confirmation on Candidate A returned `{"ok":true}`. The BLE client
then returned `storage_fault`. No retry was made. Post-failure Console reads
showed generation 0/factory, healthy profile/config/watermark journals with
unchanged config sequence 72 and watermark sequence 12, access generation 3,
empty WTP state and inactive output. The clock later aged back to
`unsynchronized`; a new accepted sync is required before any further apply.

Source review identified a boundary mismatch: the native client serialized PEM
CR/LF as short JSON escapes, but firmware `serialize_profile()` expanded them
to six-byte Unicode escapes. The 7,168-byte input has 2,628 CR/LF characters;
the longer reserialization exceeds `max_profile_bytes` before storage is
called, and the manager incorrectly mapped that condition to `storage_fault`.
At that point this was a source-backed explanation, not a physical proof of the
next repair. A profile-local compact quote and a separate
`oversize` mapping passed the exact 7,168-byte host apply/reload regression
without private material. The full host suite passed 87/87 with the Xcode 26.5
SDK, the focused sanitizer suite passed 5/5, and RF-inhibited Pico firmware and
both provisioning/field-access link checks built. The first full host run used
the broken CommandLineTools 27.0 SDK and failed three unrelated linker tests;
the correctly configured full rerun passed.

The compact-quote source was committed as `969473d2ef17`. Its clean
RF-inhibited UF2 SHA-256 was
`d7f89d05aa319bc20c2c7bc6eeb32def430f36507b2329cb90ce63e1b23764e5`.
Before flash, Candidate A still reported generation 0, healthy storage,
unchanged config/watermark sequences 72/12, access generation 3, empty state
and inactive output. Serial-targeted BOOTSEL identified RP2350 chip
`0x0bf4b4aec9ffb344`; serial-targeted picotool load/verify succeeded. The
postflash image reported `969473d2ef17`, boot ID
`4535fcf95e5c5095a412d041f3e7fac0`, generation 0, unchanged journals and
RF-inhibited/inactive output.

An initial automated `sync-time` invocation sent terminal input before its
hidden password prompt was ready; it stalled, was interrupted, and Console
showed no UTC or profile change. The deliberate clean retry returned
`{"accepted":true}`; Console then showed `clock_state=synchronized`, finite
uncertainty `351960164` ns, empty state and inactive output. With the same
owner-only 7,168-byte input, the native client transferred over BLE, printed
the exact identity-bound USB instruction, received Console `{"ok":true}` in
the confirmation window, and returned `{"generation":1}`.

Activation rebooted to boot ID `a00923c2482173991faf6f2af2a5941d`.
Post-activation Console `INFO`, `STATUS`, `STORAGE`, `ACCESS STATUS` and
`BLE STATUS` showed source `provisioned`, generation 1, provisioning fault 0,
healthy profile/config/watermark journals with config/watermark sequences
72/12, access generation 3, empty WTP state, and inactive output under
`inhibited-standalone-simulator`. Station link status 3 acquired
`192.168.1.47`; `wsprrypico-0a60df.local` was the configured and advertised
hostname with active mDNS and no conflict. The profile's `time.local` resolved
to `192.168.1.54`; SNTP accepted samples and the clock remained synchronized.
No RF-starting command was sent.

The native Pi client then reconnected on the retained BLE identity and
completed read-only WTP/1 `HELLO` and `STATUS` for the new boot, with no owner,
job or active output. From the Mac, a matching existing controller certificate
chain established TLS 1.3 with hostname validation and ALPN `wtp/1`, and
read-only TCP WTP `HELLO`/`STATUS` returned the exact device and boot IDs,
empty state and inactive output. The TLS server certificate SHA-256 was
`06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`,
matching the public certificate in the applied private profile. A matching
browser certificate established TLS 1.3 with ALPN `http/1.1`; read-only
`GET /api/v1/status` returned HTTP 200 and the expected boot, address and
inactive output. No client key was copied to `wspr5`.

Adversarial client-auth probes first proved TCP connection to the exact target,
then observed TLS rejection for both no client certificate and a certificate
issued by an unrelated CA; neither received a WTP response. A later Console
read still showed generation 1, healthy storage, synchronized clock, active
station control, zero TLS allocation failures, empty state and inactive output.

## Adversarial reassessment

The first review found two independent acceptance defects: the unset
certificate-validation clock on an unprovisioned target and the internal
CR/LF expansion that made a valid boundary profile appear to be a storage
failure. Both were repaired without relaxing certificate or transfer limits,
covered by host/sanitizer/link checks, and then exercised on the exact target.
The next review identified that a negative TLS probe could falsely pass on a
network outage; the negative checks were rerun with a proven TCP connection
before observing TLS errors. Positive mutual TLS and WTP/HTTPS reads passed
before the negatives, and Console confirmed healthy listening afterward.
No unresolved defect was found in the native-Pi profile-activation slice.
This does not replace the unperformed Bluefy/iPhone assessment, nor does
RF-inhibited evidence qualify physical RF output. The public default local
password remains active on this test device; no credential rotation was
authorized or attempted.

## Operator-reported Bluefy continuation

On 2026-09-25 the operator reported the checked-in online-verified Bluefy
release `45041c11076f` on the iPhone; offline cache remained unavailable.
The page selected the exact Candidate A ID at profile generation 1, authorized
the selected device, returned read-only WTP `0.0.0-devel`/empty/inactive, and
reported field time `sntp`, LED off and no indicator fault. A contemporaneous
USB Console read showed generation 1, healthy access/storage, the inhibited
engine, empty state and inactive output. No Bluefy profile transfer, failure
case or apply was attempted because the prepared private profile was not on
the phone. The operator was asked to cancel and clear the tab; completion of
that cleanup was not independently observed.

The checked-in Bluefy page now offers a **test-only** prepared JSON file import
so the operator need not copy individual PEM fields. It reads a bounded file
locally, requires the exact selected device ID and the usual fresh password,
uses the unchanged Field-GATT/1 apply path and clears file selection on every
terminal path. It neither generates nor distributes that file; this is not a
consumer commissioning solution.

## Bluefy file-import physical continuation (2026-09-26)

The operator reported the online-verified page release `9f4272fa7457` in
Bluefy. The owner-only 1,972-byte ordinary profile was AirDropped to the
operator's confirmed iPhone without pasting any credential into chat. Current
iPhone, iOS and Bluefy version numbers were not re-reported for this session;
the earlier model/version report is historical, not a fresh observation.
Candidate A remained the exact Pico 2 W/device ID above, running RF-inhibited
firmware `969473d2ef17` with profile generation 1, healthy config/watermark
journals at sequences 72/12, empty WTP state and inactive output.

| Bluefy row | Operator-visible result | Independent target check |
| --- | --- | --- |
| Select/authorize | Same exact Candidate A selected and authorized | Generation 1; BLE healthy; inhibited/empty/inactive |
| Deliberately wrong fresh password | `Provisioning failed: authentication_required.` | Generation 1; healthy storage; no activation |
| Correct password, no USB confirmation | `Profile staged` followed by `Provisioning failed: confirmation_timeout` | Generation 1; journals 72/12; no activation |
| Cancel at staged confirmation | `Cancelled and disconnected.` | Generation 1; journals 72/12; new authorized BLE WTP read returned empty/inactive |
| Ordinary profile, correct fresh password, exact USB confirmation | Console `{"ok":true}`; Bluefy `Profile generation 2 committed.` | Generation 2 persisted across activation restart; journals 72/12; empty/inactive |

The first activation restart entered **watchdog recovery**, boot
`d9def09a1b2cb6a71acd0600bfed8deb`, with fault stage 14 and panic-format
hash `2090325528`. The exact installed ELF maps that hash to lwIP's
`don't call tcp_abort/tcp_abandon for listen-pcbs` assertion. This is a real
post-commit failure: network startup was suppressed, so the generation-2
station/TLS row did **not** pass on the activation boot. A single controlled
idle USB reboot returned `{"ok":true,"rebooting":true}`. The subsequent
boot `d6f6b06263e03211e42530f2b0d6d241` was not a recovery boot: it
retained generation 2, associated at `192.168.1.47`, activated mDNS and SNTP,
and kept WTP empty/output inactive under the inhibited engine. The operator
also reauthorized Bluefy and obtained read-only WTP empty/inactive after the
activation. This secondary recovery does not erase the failed activation-boot
gate or qualify TLS/mTLS on generation 2.

Adversarial source review found that `PicoServer::stop()` aborted its LISTEN
PCB during profile activation. The same invalid close existed in the blank
bootstrap listener. Both now use lwIP `tcp_close()` with an asserted successful
LISTEN close. The transport contract check guards both call sites. The pinned
SDK 2.3.1 RF-inhibited target links, and the full host suite passes 95/95 with
the Xcode 26.5 SDK and loopback access. A clean-revision flash and affected
physical retest were subsequently performed as recorded below.

### Repaired activation retest

The repaired source was committed locally as `932d10d` and built against
pinned Pico SDK 2.3.1. Its RF-inhibited UF2 SHA-256 was
`03aaa25cd58c389292bbad583b4584b113df442295c3654f60b087bf9d3913c0`.
Serial-targeted `picotool load -v -x` verified the image on the exact Candidate
A serial. Postflash Console identified revision `932d10dc1c43`, generation 2,
non-recovery boot `2195e13093a6a43431bd9d9615f0dd84`, healthy access and
storage, and unchanged config/watermark sequences 72/12. Station Wi-Fi, mDNS
and SNTP returned; WTP was empty and output inactive under the inhibited
engine. No RF-starting command was sent.

Applying the *identical* original ordinary profile returned Bluefy `Profile
generation 2 committed.` after exact USB confirmation, but the target retained
generation 2 and its boot ID. Source review showed this is an intentional
idempotent no-op, not an activation test. The owner-only 1,973-byte retest file
therefore changed only the JSON `wifi.time_server` spelling from `time.local`
to `time.local.`; the network adapter strips the terminal dot, preserving the
same runtime SNTP endpoint. No credential material is recorded here.

The first attempted retest after AirDrop did **not** commit: Console
confirmation returned `authentication_required`, Bluefy later reported a
timeout after all 281 writes, and the target remained generation 2, healthy
and inactive. The selected file was not independently verified for this
attempt. The operator subsequently confirmed they had not disconnected before
this retry. The required fresh reconnect/authorization sequence was therefore
not performed; this attempt is an invalid operator sequence, not an open device
defect or an acceptance pass. On the next attempt
the operator reported `Profile staged`, exact identity-bound USB
confirmation returned `{"ok":true}`, and Bluefy reported `Profile generation
3 committed.`

The target then reported provisioned generation 3 on new boot
`904b2699bec96e09249d4ba9f50591b9`, **not** a recovery boot, with fault
stage/hash/status zero and provisioning fault zero. Config/watermark journal
sequences remained 72/12 and storage was healthy. Access generation 3 remained
healthy; station link acquired `192.168.1.47`, mDNS was active for
`wsprrypico-0a60df.local`, and `time.local` resolved to `192.168.1.54` with
accepted SNTP samples and synchronized clock. Console WTP readback was empty,
output inactive and `reboot_required=false`. The operator reconnected and
reauthorized Bluefy, then reported read-only WTP `0.0.0-devel; state empty;
output inactive.` The listener-close assertion did not recur on this affected
activation path.

From `wspr5`, a TCP connection to the configured port 18443 succeeded and an
uncredentialed OpenSSL probe negotiated TLS 1.3 with the expected server
certificate CN. That probe did not authenticate a client or perform WTP, and
OpenSSL did not verify the issuer; it is **not** positive mTLS acceptance. A
direct Mac TCP probe timed out, despite the Pi-to-Pico TCP result. The operator
confirmed they had not disconnected the preceding session before this probe,
so it did not meet the intended independent-client test setup. It is closed as
a non-qualifying run, not evidence of a Pico reachability or sandbox defect;
broader concurrent-client behavior remains a separate matrix. Matching client
private credentials were not copied to `wspr5`. These initial probes were not
positive generation-3 mTLS/WTP or HTTPS evidence.

On a later direct Mac retry **outside the sandbox** on 2026-09-26, mDNS
resolved `wsprrypico-0a60df.local` to `192.168.1.47` and TCP port 18443
connected. The existing local controller identity verified the server chain
and hostname, established TLS 1.3 with ALPN `wtp/1`, and completed read-only
WTP `HELLO` and `STATUS`. The reply identified Candidate A and boot
`904b2699bec96e09249d4ba9f50591b9`, with state empty and output inactive.
The existing browser identity separately established verified TLS 1.3 with
ALPN `http/1.1`; `GET /api/v1/status` returned HTTP 200, the same boot ID,
empty state and inactive output. Both connections observed server certificate
SHA-256 `06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016`.
The subsequent USB Console `INFO` still reported generation 3, healthy storage,
no recovery/provisioning fault, synchronized time, active station control,
zero TLS allocation failures and inactive RF output. No client private key was
copied to `wspr5`, pasted into chat or committed to Git. This closes
the **positive generation-3** mTLS/WTP and HTTPS readback row; it does not
repeat the separate negative-client-auth or broader network matrices. The
later positive retry supersedes the invalid first Mac probe; no internal TCP
cause is inferred from that timeout.

The operator confirmed that Bluefy cleared both the password field and
selected-file name after the successful apply, deleted both AirDropped JSON
files from the iPhone, and closed the Bluefy tab. The two owner-only temporary
JSON files and their temporary folder were deleted from this Mac after exact
path/mode/size checks. The pre-existing private source profile on `wspr5` was
not changed.

The final adversarial assessment separates three superficially similar
outcomes: the generation-2 identical-profile response did not activate; the
first attempted retest timed out without a commit; only the subsequent
changed-profile attempt both incremented generation and survived a normal
activation boot.
The independent Console and Bluefy readbacks agree on inactive WTP authority.
The earlier watchdog recovery and first attempted retest's confirmation
rejection remain in this record. The operator confirmed they omitted the
required disconnect before the latter retry, so it is closed as an invalid
test sequence rather than a device defect or passing row. The later positive
generation-3 client-authenticated TCP reads passed independently. Source,
host and RF-inhibited target results still do not qualify RF output.

## Remaining gates

1. Complete offline-cache, end-user commissioning and the other Stage A
   matrices. Keep disconnect/reconnect/authorization explicit in the operator
   sequence.
2. Preserve this bounded adversarial assessment and complete the remaining
   physical matrices. Step 1 and Phase 12 remain open until all applicable
   gates pass; RF-inhibited work never qualifies RF output.
