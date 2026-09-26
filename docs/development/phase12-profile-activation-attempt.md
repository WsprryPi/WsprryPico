# Phase 12 profile activation: Candidate A physical attempt

Status: **open; profile activation not yet accepted** (2026-09-25 CDT).

This record preserves the first physical failure and the preceding negative
tests. It does not claim completed station, TLS, Bluefy or Phase 12 acceptance.
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
unset clock and rejected the otherwise current certificate. This is a
source-backed diagnosis, not yet a physical proof that the repaired image will
accept the exact profile.

The repair installs the disciplined UTC hook at standalone startup, retains it
across TLS server stop/start, and requires a non-unsynchronized clock for a new
profile's strict certificate validation. It does **not** relax date, chain,
purpose, algorithm, SAN or key-pair checks. The native-Pi execution sequence
now calls authenticated `sync-time` before the next valid apply. A host TLS
test forces the clock to zero before any server starts, proves rejection, then
proves accepted UTC permits validation and loss of UTC rejects it again.

## Gates still open

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
This is a source-backed explanation for this exact failure, not yet a physical
proof of the next repair. A profile-local compact quote and a separate
`oversize` mapping passed the exact 7,168-byte host apply/reload regression
without private material. The full host suite passed 87/87 with the Xcode 26.5
SDK, the focused sanitizer suite passed 5/5, and RF-inhibited Pico firmware and
both provisioning/field-access link checks built. The first full host run used
the broken CommandLineTools 27.0 SDK and failed three unrelated linker tests;
the correctly configured full rerun passed.

1. Validate, commit, rebuild and flash the compact-quote repair after a fresh
   Candidate A safety/identity preflight.
2. Obtain fresh accepted controller UTC on the repaired target and verify field
   status before another profile apply.
3. Physically repeat the 7,168-byte apply/confirmation and verify generation,
   activation, station, TLS identity, client CA, WTP and cleanup.
4. Complete the ordinary Bluefy apply and its negative/cleanup rows, then
   adversarially reassess, repair any findings, restore safe state, commit and
   push. Until then Step 1 and Phase 12 remain open.
