# Phase 11.4 F2/F3/F6 execution prompt

Complete certificate lifecycle acceptance F2, F3 and F6 in WsprryPico, coordinating
actual WsprryPi production-client evidence. Execute this prompt, review the
implementation and evidence adversarially, repair actionable findings, rerun
affected checks and repeat assessment. Commit scoped changes and push to
origin/devel. Preserve all original failures and unrelated open acceptance gates.

## Scope, authority and starting identity

Read project instructions, README, CONTRACT, architecture, development checks,
network certificate/identity contracts, WTP, browser API, joint acceptance matrix
and earlier single-board and browser/production evidence. Inspect both working
trees and preserve user work. Starting Pico commit is 5ee5bcf; runtime last
observed 23ac5b1aee66. Independently verify current runtime and authoritative state.
The sole Pico 2 W/RP2350 is on wspr5, USB serial 0BF4B4AEC9FFB344,
full WTP ID fd6127d11d6aca42a9905fa3fb1bf1d5, Console if00 and WTP if02.
Use only the standard inhibited-standalone-simulator image. Existing restoration
UF2 SHA-256 is a7013feccf36abb9c9da17db057d4d12158942a019d74d787f56336f64a6c8f2.
Do not touch adjacent GPSDO, GPIO, RF engines, router settings or unrelated trust.

The user's all-tests grant and specific bounded service-pause grant authorize
this slice's USB reads/control, inhibited candidate and restoration flashes,
replacement browser identity import and isolated production-client rotation.
Prepare exact image hashes, validated certificate metadata and reviewed cleanup
before each operation. Keep the existing device CA and original clients; do not
change CA trust scope, revoke identities or overwrite credentials. Retain the
replacement browser identity for continued use. Keep production config/binary
unchanged and restore the installed service after each bounded pause.

LAN/SSH checks must run outside the filesystem/network sandbox. Distinguish
environment permission failures from actual network/device failures. Use existing
tools, private ignored build/phase11-4-f2-f3-f6 evidence and owner-only credential
folders. Never print passwords or key contents or commit credential artifacts.

## F2: actual client replacement

Verify separate original and replacement browser/controller public fingerprints,
validity, purpose, CA and private-file permissions. Export the replacement browser
identity using the existing macOS-compatible PKCS#12 helper and private password
file. Import only that identity into the login keychain using existing device-CA
trust. In actual Chrome select the replacement leaf and verify authenticated live
status from the real certified Pico origin. Bind the observed client certificate
selection and server certificate, full device ID and current boot; cached success
or direct OpenSSL requests cannot substitute for actual Chrome evidence.

Use the exact reviewed isolated production executable, with full hash and source
identity verified, separate replacement controller credentials and a private INI.
Verify installed provider output inactive, saved transmit false/boot Never, and
Pico inactive/unowned before pausing wsprrypi.service. Run the real application
with its production TLS transport; prove replacement principal authentication and
live identity/status, using bounded inhibited finite work only if needed to prove
ownership. Shut down gracefully, establish inactive/unowned cleanup, then prove
original valid controller/browser credentials still work. Issuance is not
revocation. Restore service and verify installed config/binary hashes unchanged.

## F3: intended rejection layer

Reproduce the retained missing/untrusted/expired-client failures with verified
server name/CA and positive controls on the same healthy device. Verify negative
certificate chain/purpose/dates offline; never falsify clocks or weaken validators.
Collect bounded TLS handshake/alert traces and inspect the pinned Mbed TLS source
and firmware adapter error/closure behavior. Distinguish client-side name/CA/SAN
rejection, device certificate verification rejection and unrelated record/TCP
failure. No HTTP/WTP mutation is permitted for negative cases. Missing application
response alone cannot prove the intended certificate rejection layer.

If the server mishandles failed handshakes or alert delivery, repair its owning
adapter with meaningful deterministic/actual-TLS regression coverage; do not
weaken certificate verification or merely accept arbitrary failures. Build and
validate the exact standard inhibited candidate, record source/ELF/UF2 identities,
flash only the known board without journal erase, and repeat affected physical
negatives bracketed by positive controls. Preserve pre-fix failures. Repeat wrong
hostname/CA and absent IP SAN controls as relevant to the final deployed image.

## F6: actual Chrome literal-IP identity

Read the current DHCP address from USB. Prepare a new server bundle under the
same approved CA with exact full device ID, wsprrypico-0a60df.local DNS SAN and
matching current IP SAN. Validate manifest, keypair, chain, dates, SANs and purpose
with production tooling. Build the current reviewed inhibited runtime in a new
private build directory; inspect inhibition, engine, memory/journal layout and
ELF/UF2 hashes. Preserve saved configuration, disabled schedules and watermark.
Flash the verified candidate and independently establish USB identity/state,
SNTP, deployment match and server fingerprint. In actual Chrome navigate directly
to the literal-IP HTTPS URL, select the authorized client, observe secure origin
and live authenticated status. No certificate warning bypass, injected DNS, proxy
or cached page qualifies. Verify hostname access still works. Restore the recorded
current inhibited image (or reviewed repaired baseline if F3 required a fix), and
verify its fingerprint and absent-IP-SAN rejection again.

## Review, cleanup and publication

Challenge stale browser sessions, unintended original-client selection, wrong
application binary, cached status, chain-versus-leaf trust, expired test setup,
record errors masking rejection, changed boot/state, failed service cleanup and
claims transferred across firmware. Record each finding and its disposition;
repair and rerun until no actionable in-scope findings remain. Keep physical,
host-test and later resource/RF evidence distinct. If a genuine external blocker
remains, retain the gate and report its exact unfinished operation.

Finally verify USB INFO/HELLO/CAPS/STATUS, expected firmware/boot, output inactive,
no owner, schedules/config/watermark preserved, pool.ntp.org unchanged, Wi-Fi
and authenticated HTTPS restored, original clients usable, service restored and
private artifacts excluded. Update the joint matrix and durable sanitized results,
link the prompt, identify operator-documentation follow-up without editing its
separate repository. Run relevant documented tests, documentation-link and diff
checks, inspect staged contents for secrets/unrelated work, commit and push each
changed authorized repository, verify remote parity and report actual state.
Print a table of the remaining Phase 11.4 items. Do not close 11.5 or 11.6.
