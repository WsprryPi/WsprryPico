# Testing prerelease publication

Accepted 2026-10-19 after independent review and authenticated draft plus
anonymous public-download audits. This record concerns software publication;
no board was flashed, no service/device setting changed and no RF was emitted.

## Frozen identities and prerequisites

- Entry: clean `devel` at `46b110a353e35cd4b3cdcdfcd9feeb6f2a1490e8`.
- Frozen firmware/source commit **F**: `675d56dc94008568bff34c7068ce59afa364fac3`.
- Version/tag: `0.1.0-testing.1` / `v0.1.0-testing.1`.
- [Public testing release](https://github.com/WsprryPi/WsprryPico/releases/tag/v0.1.0-testing.1),
  release ID `417837561`, published `2026-10-19T23:05:28Z`.
- Annotated remote tag object `8a015679c7f9ab9885b8aeacad94ddb0703b70ad` peels to F. F is an ancestor of
  accepted remote devel. The default main branch did not select the source.
- This later evidence-only record belongs to **E**, distinct from F. Its exact
  commit is reported after committing; no source hash is embedded in itself.

Historical accepted prerequisites are ancestors of F: USB
`100e749c815f7485d5097c9086852d3b97adca9f`, GPIO implementation
`d6de1f3cf14dc49266c4401c3bca91b8ce9da688`, scoped drive acceptance
`33f3d5ce7093a853a667f18dd157f46c8c945ecd`, normal/inhibited default acceptance
`da79bd0a25289f3afe22f777c36fb57cfb57ef07`, and short decode acceptance
`9497ec42bad305d3b1833d7e680a8614bbd7332a`.

The historical drive hardware pair was Pico `d6de1f3cf14dc49266c4401c3bca91b8ce9da688`
and Pi `fe701cf4c2b05e46cb84927188984084503d1cea`. Current CI instead checks the
exact Pi source `c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf` in software fixtures.
No physical test of that pair and this release is claimed. The historical
P15.15 hardware record used adversarial self-review; this publication used a
separate read-only reviewer.

The accepted short Type 2/3 observation explicitly superseded its original CI
image requirement by operator selection of a local build. It remains limited
to Pico A at 3.570100 MHz, source `14698ca1dba32914959530a3b5a0cf41f74caf8f`,
UF2 `6cbe319e996b4a935dc7ba311583832e68228177cb2b7434573776ab19284528`.
It is not a decode of this candidate. No firmware/application/CMake inputs
changed during this release preparation; existing physical evidence is not renewed.

## Checks and artifact audit

[Testing CI run 39337091361/1](https://github.com/WsprryPi/WsprryPico/actions/runs/39337091361)
completed successfully at F. All 160 registered Linux CTest suites passed,
with zero failures/skips. WTP, npm/browser, consumer UI, packaging failure,
normal/inhibited/compatibility image and two-build identical-UF2 checks passed.
The automatic publication job was intentionally skipped for this manual testing
candidate; it was not a skipped software test. Ordinary push CI run
39337082201 and separate installer CI run 39337082355 passed at F.

Local affected validation passed: 42 packaging tests, 85 installer tests,
six installer-publication tests, WTP validation (23 schema, seven raw JSON,
one framing, eight transition cases), and whitespace checks. No local macOS
C++ compilation was attempted. Full portable/SDK checks and cross-builds ran
on the identified Linux CI runner.

The [exact CI manifest](phase15-17/release-manifest.json),
[original checksums](phase15-17/SHA256SUMS),
[testing provenance receipt](phase15-17/testing-publication.json) and
[public audit](phase15-17/publication-audit.json) retain the complete identities.
The original deployment/audit Actions archives are public release assets.
Raw logs, linked ELF/map, firmware and private task scripts remain outside Git.

UF2 `WsprryPico-0.1.0-testing.1-pico2_w.uf2`: **4849664 bytes**, SHA-256
`969cace3ecf7f8221df0f7777e3efd9105cd942560f10b1491e1613360b423b5`. Manifest SHA-256 `05d7c30028cf8f43a4cdb1dc5d1e55058373b2002e281bf292f0f5067d319f87`;
notes SHA-256 `35b8a080b09fe4c2a709ad157302432066e2d57c768b2b223c0db71fc13d6087`. The exact release body is maintained in
[release notes](phase15-17-release-notes.md).

Static image checks retain a 32,768-byte primary stack and 16,384-byte RF worker stack. The linker gap from BSS end `0x2005e148` to heap limit `0x20078000` is 106,168 bytes; this is not measured runtime free heap. The RAM renderer is 660 bytes, initialized data 15,224 bytes and the worker object 166,176 bytes. All 9,472 UF2 blocks are validated: ordinary application extents are `[0x10000000,0x1024ff00)`, below the `0x103ee000` link limit, plus exactly one pinned E10 special block.

The SDK, compiler, picotool and linked submodule pins are unchanged. Exact
CMake/Ninja/Python/Node, runner and dependency versions, flags and resolved
commands are in the CI manifest/audit. Independent local inspection used
picotool 2.3.0 from clean pinned source
`6f6458d792b93685a11423b244a585eaa99eafcf`, executable SHA-256
`c146c628c5b4b2dc9e3fad0ccff858a7f0aa20a2c19e7af4563e825100ef963f`.

Both draft and public audits required all nine explicit assets, matching names,
uploaded states, sizes and API SHA-256 digests. Every draft asset was downloaded
through its authenticated asset API; every published asset was downloaded
anonymously from its exact public tag URL into a new directory. All bytes
matched the independent baseline retained before upload. Both sets were
re-extracted and revalidated against source F, schema, actual test reports,
generated/linked identity, normal engine, UF2 family/numbering/extents, ELF
payload and checksums. Assets were never overwritten, tags never moved and
no existing release was deleted. Hashes are integrity checks, not signatures.

## Review and repaired preparation failure

The independent reviewer required an explicit testing-version/CI context in
reproduction instructions and direct testing-manifest creation coverage. Both
were repaired before the first source freeze.

Initial source `1fab06e40ce8e85821671c514cbd301ee030e6eb` then failed CI runs
39336019432, 39336039746 and installer run 39336019387. The new schema's `allOf`
keyword was unsupported by the installer's deliberately bounded interpreter.
The full CTest run passed 159/160 suites and failed the installer suite before
firmware/deployment assets were produced. No testing tag or release existed.

The repair removed that unsupported keyword, retained strict testing metadata,
version, event/branch and eligibility checks in the canonical verifier, and
added a regression through the unchanged installer schema interpreter. All
focused tests passed independently, then new clean F and fresh CI replaced the
failed preparation. No installer implementation or dependency was changed.

Independent prepublication and complete-draft reassessments passed without findings, bound to F, the exact notes/manifest/UF2 hashes and nine-asset baseline SHA-256 `6423a4ac398002b77133c6e3272fbd9fcca1e11ba413f453c55afc65be560440`. The final evidence/public-audit reassessment is recorded in the accompanying publication audit. An initial draft URL assertion refused GitHub's temporary unpublished URLs before any asset downloads. Its draft-only assumption was corrected; exact final public URLs remained mandatory, and the complete authenticated and anonymous reruns passed.

## Compatibility, installer and qualification limits

Normal firmware is uninhibited Pico 2 W/RP2350, PIO/DMA, 138 MHz with nominal
2/4/8/12 mA RF-pin drive and a 4 mA default. Generic bytes have no station,
frequency, credentials or enabled schedule. USB/network/storage authority and
existing RF-admission rules remain. The manifest records independent WTP/API
and on-flash Config/progress versions and required notices.

Application bytes stay below `0x103ee000`; the final 72 KiB remains reserved
for NTP learning, progress, scratch, access, BTstack, profiles, standalone
configuration/watermark and E10 treatment. No saved-bank payload or whole-flash
erase is part of this image's ordinary update. Older firmware may reject
extended records; migration/downgrade and power-interruption preservation are
unqualified. Publication did not validate a device update.

This manually reviewed testing series explicitly sets deployment/default
eligibility false. The current installer and `download.py --published` retain
their run-derived CI contracts and do not consume this testing release. The
supported installer defaults to verified main CI; devel is explicit. Main's
firmware bookmark remained unchanged; normal devel CI may advance through its
own successful source/run. No testing publication updated either bookmark.
Stable/latest-full-release absence was confirmed before and after publication
by the release inventory and a structured latest-release HTTP 404.

The operator manual and installer already exist. Historical band/mode results
retain their original board/source/path scope, 6 m receiver-retune condition,
exact 40.001/60.001 MHz Pico A/138 MHz points and compact-job constraints.
Native direct 4 m remains unavailable at 138 MHz and unqualified at 150 MHz;
native direct 2 m remains unavailable. There is no new all-band, alternate-clock,
nondefault-drive, LPF, calibrated-power/timing, antenna-ready or reliability
qualification. Other family repositories remained read-only.
