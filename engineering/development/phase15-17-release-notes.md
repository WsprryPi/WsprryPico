# WsprryPico 0.1.0-testing.1

Testing prerelease for **Pico 2 W / RP2350 Arm Secure**. Tag
`v0.1.0-testing.1` identifies clean source `675d56dc94008568bff34c7068ce59afa364fac3`.
The normal uninhibited `WsprryPico` application uses direct GPIO PIO/DMA at
138 MHz, with nominal RF-pin drive choices 2/4/8/12 mA and a 4 mA default.
Saved configuration, ownership, clock, frequency and output-admission rules
still govern transmission. A generic image contains no station identity,
selected transmit frequency, credentials or enabled schedule.

USB Console, WTP and USB management/time are separate CDC interfaces. Local
USB management works without Wi-Fi and does not itself grant transmitter
ownership. GPIO-drive changes persist and require explicit restart; saved,
boot-active and cached ARM-time pad-register observations remain distinct.
WSPR reported dBm is message content, not measured output power. μChrony
disciplines UTC; manual PPM alone corrects RF. NTP-derived RF calibration and
GPS/PPS input are unavailable.

## Downloads and integrity

Download these exact assets from this tag:

- [Normal UF2](https://github.com/WsprryPi/WsprryPico/releases/download/v0.1.0-testing.1/WsprryPico-0.1.0-testing.1-pico2_w.uf2)
- [Manifest](https://github.com/WsprryPi/WsprryPico/releases/download/v0.1.0-testing.1/release-manifest.json)
- [Checksums](https://github.com/WsprryPi/WsprryPico/releases/download/v0.1.0-testing.1/SHA256SUMS)
- `LICENSE.md`, `THIRD_PARTY_NOTICES.md`, `DEPENDENCY-LICENSES.txt`
- Original Actions `deployment.zip` and `audit.zip`, plus `testing-publication.json`
  binding their immutable artifact IDs/digests, source/run and reviewed notes.

The UF2 SHA-256 is `969cace3ecf7f8221df0f7777e3efd9105cd942560f10b1491e1613360b423b5` (4849664 bytes).
Verify all six deployment files before any flash operation, from their directory:

```sh
# macOS
shasum -a 256 -c SHA256SUMS
# Linux
sha256sum -c SHA256SUMS
```

SHA256SUMS covers the UF2, manifest and all three notices; it excludes itself.
The publication receipt separately covers the original archives and reviewed
notes. These hashes establish byte integrity, not a signature or attestation.
Do not rename or substitute an inhibited, bench or compatibility image.

## Software validation and compatibility

[Canonical CI run 39337091361, attempt 1](https://github.com/WsprryPi/WsprryPico/actions/runs/39337091361)
built these exact bytes with the consumer profile from source `675d56dc94008568bff34c7068ce59afa364fac3`.
All 160 registered Linux CTest suites passed with zero failures/skips;
WTP schema/framing/transition checks, browser checks and packaging failure
checks passed. Normal, inhibited and compatibility firmware builds passed;
two independent fresh normal builds produced identical UF2 bytes. The skipped
publication job is deliberate: this manual testing dispatch requires independent
review and a verified draft before publication. It is not a skipped software test.
The retained ELF/map, identity header, compile commands, dependency inventory,
resolved CMake/Ninja commands, reports and resource/flash checks are in audit.zip.

Build pins are Pico SDK 2.3.1 `079c6f39023649b154152db30f1d781e884879bc`,
Arm GNU 15.3.1 and picotool 2.3.0
`6f6458d792b93685a11423b244a585eaa99eafcf`. The manifest retains exact
linked SDK submodules, runner/tool versions, source tree and recipe.

WTP/1, USB-Management/1, Consumer-Radio/1 and Field-GATT/1 remain independently
versioned. Shared views include application/3, hardware/2, progress/2 and
gpio-drive/1 under `/api/v1/`. Config JSON remains version 1; saved-progress
records /1, /2 and /3 are readable. The exact CI-tested WsprryPi companion is
`c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf`; these are software interoperability
checks, not a physical test of this release on that pair. Historical drive
acceptance used Pico `d6de1f3cf14dc49266c4401c3bca91b8ce9da688` and Pi
`fe701cf4c2b05e46cb84927188984084503d1cea`.

## Updates, installer selection and recovery

The [operator manual](https://wsprrypico.readthedocs.io/en/devel/) is published.
The [installer and preserving-update procedure](https://github.com/WsprryPi/WsprryPico/blob/675d56dc94008568bff34c7068ce59afa364fac3/docs/install.md#preserve-settings-during-an-update)
are available. Ordinary installer upgrades default to the latest verified
compatible **main CI image**; devel is explicit. Eligible run-derived CI
prereleases are selectable through their own verified branch indexes. Stable
is a distinct selection policy; this publication creates no stable image.

**This manually reviewed `testing.1` series is outside the current installer's
accepted CI-version/receipt contract and is not eligible for its default.**
The installer will refuse this bundle; do not relabel it as a CI image. Its
main/devel branch bookmarks remain independent. No installer implementation
or device update was performed for this publication. The canonical
`download.py --published` path likewise applies to run-derived CI releases;
verify this release's original archives with `bundle.py` and the recorded
source/version instead.

For ordinary supported preserving updates, finish/abort work through its owner,
release control, disable standalone schedules, pause a competing Pi service,
and use the installer upgrade transaction. Retain its private same-board flash
backup and transaction for recovery, then verify saved settings and new boot
identity before enabling schedules deliberately. An interrupted update requires
its retained recovery command, not a newly selected image. Backups contain
credentials and must stay private. These instructions describe supported CI
updates; they do not claim a tested installer path to this manual candidate.

This candidate's application ends before `0x103ee000`; the final 72 KiB retains
NTP learning, progress, scratch, access, BTstack, profiles, standalone
configuration/watermarks and the SDK E10 reservation. UF2 payload checks reject
saved-journal content and retain only the pinned RP2350 E10 workaround treatment.
A whole-flash erase is not part of an ordinary update. No migration or downgrade
preservation is claimed: older firmware may reject nondefault drive or newer
progress/configuration. Erase/reset is a separate explicit recovery operation;
automatic rollback and physical power-interruption recovery are unqualified.
Manual programming of this testing image requires its own deliberate bench
procedure and settings-preservation verification; this release is not device-upgrade acceptance.

## RF scope and known limits

The [conducted band/mode dispositions](https://github.com/WsprryPi/WsprryPico/blob/675d56dc94008568bff34c7068ce59afa364fac3/engineering/development/band-support.md)
apply to their original boards/images/clocks/paths. The earlier 2200 m through
10 m and 6 m matrix is historical evidence; 6 m WSPR includes receiver-only
+125 Hz retuning. It does not qualify this rebuild. P15.13 establishes only
Pico A, GP2, 138 MHz at **40.001 and 60.001 MHz**, with fixed receiver-audio
translations +125/+200 Hz and the recorded compact-job/admission conditions.
It does not establish whole 8 m/5 m bands or alternate clocks. Native direct
4 m is unavailable at 138 MHz and unqualified at 150 MHz; native direct 2 m is
unavailable. Nondefault drive has no all-band/mode qualification.

The accepted [short Type 2/3 decode](https://github.com/WsprryPi/WsprryPico/blob/675d56dc94008568bff34c7068ce59afa364fac3/engineering/development/short-wspr-type23-decode-results.md)
used a specifically authorized local image from
`14698ca1dba32914959530a3b5a0cf41f74caf8f`, UF2
`6cbe319e996b4a935dc7ba311583832e68228177cb2b7434573776ab19284528`,
on Pico A at 3.570100 MHz. The operator explicitly superseded that observation's
CI-image requirement, as recorded in the [original acceptance](https://github.com/WsprryPi/WsprryPico/blob/9497ec42bad305d3b1833d7e680a8614bbd7332a/docs/development/short-wspr-type23-decode-results.md#operator-selections-and-frozen-image).
It is not a decode of this release image. Release preparation changes tooling
and metadata only and does not renew historical physical evidence.

No new RF, device flashing, LPF, calibrated power/frequency/timing,
alternate-clock, dual-board, antenna-ready emissions or release-reliability
qualification accompanies this publication. Output needs appropriate external
filtering, attenuation/load and operating authority. HTTP page delivery and
the development USB VID/PID retain their documented limits. Review the
[pinned project contract](https://github.com/WsprryPi/WsprryPico/blob/675d56dc94008568bff34c7068ce59afa364fac3/CONTRACT.md)
and notices before use.
