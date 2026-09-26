# Phase 12 profile activation: Candidate A physical attempt

Status: **native-Pi maximum profile accepted; Bluefy/iPhone gate open**
(2026-09-25 CDT).

This record preserves the first physical failures, their repairs, and the
subsequent RF-inhibited native-Pi acceptance. It does not claim Bluefy/iPhone,
RF, full Step 1 or Phase 12 acceptance.
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
consumer commissioning solution. Bluefy physical apply and negative rows
remain open until they are run on the published matching release.

## Remaining gates

1. Complete the ordinary-profile Bluefy/iPhone apply and its negative,
   disconnect and cleanup rows. The Mac was locked during this run and could
   not expose iPhone Mirroring; the operator was away, so no phone action was
   attempted or claimed.
2. Perform a final adversarial review of the whole tranche, repair any new
   findings, recheck RF-inhibited restoration, and publish the evidence. Until
   the phone gate is satisfied, Step 1 and Phase 12 remain open.
