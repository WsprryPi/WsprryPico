# Phase 11 network control

The implementation provides optional TLS WTP/TCP, HTTPS browser API v1, embedded
operator assets, network status/management and local certificate tooling. Host
TLS/API/browser tests and firmware cross-linking are distinct from physical
network/RF acceptance. The [Phase 11.4 record](phase11-4-review.md) identifies the
inhibited images actually operated and the remaining physical gates.
Phase 12 retains SoftAP/BLE and runtime credential provisioning;
Phase 13 retains final RF/timing/reliability qualification.

## Operator setup and certificates

Network control is disabled by default (`WSPRRY_PICO_NETWORK_PORT=0`). Existing
Wi-Fi/SNTP/USB and recovery behavior remains available. Use the existing Console
configuration to join Wi-Fi; the TLS server requires usable device UTC before
accepting clients. Use DHCP with the stable per-device `.local` hostname; no
address reservation is required. No cloud service, public domain or public certificate
authority is required.

The helper uses locally installed OpenSSL and Python. It creates a **separate
CA for each device**, server credentials and independently named client identities.
Keep its directory and a backup private. The CA private key is unencrypted on disk
with owner-only permissions; keep it offline when not issuing credentials. Do
not use the same CA across a fleet. Firmware contains its device private key;
credential-bearing build directories are private and generated credentials are
owner-readable only. Such UF2 files are private deployment artifacts, never release
artifacts or source-controlled files.

Obtain the stable 32-hex WTP device ID from an existing recorded INFO/HELLO result
(or separately authorized USB inspection). The examples use the illustrative ID
`aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`; replace it with the actual device ID. The
helper derives `wsprrypico-<last-six-MAC-hex>.local` from the observed Wi-Fi
station MAC. The Pico reads its own MAC when the driver initializes at boot;
Console INFO exposes `network.station_mac` and the derived `stable_hostname`.
Before first credential provisioning, use an authorized inhibited bootstrap with
Wi-Fi configuration to obtain that MAC. Do not substitute a USB serial or WTP ID.
The following MAC is illustrative; replace it with the board's actual value.
These commands create local files:

```sh
python3 scripts/network_certificates.py init \
  --directory config/local/network/pico-a --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --mac-address 88:a2:9e:0a:60:df
python3 scripts/network_certificates.py issue-client \
  --ca-directory config/local/network/pico-a --name operator-browser \
  --output config/local/network/pico-a/operator-browser
python3 scripts/network_certificates.py export-browser \
  --client-directory config/local/network/pico-a/operator-browser \
  --output config/local/network/pico-a/operator-browser.p12
python3 scripts/network_certificates.py issue-client \
  --ca-directory config/local/network/pico-a --name wsprrypi-controller \
  --output config/local/network/pico-a/wsprrypi-controller
python3 scripts/network_certificates.py inspect --directory config/local/network/pico-a
python3 scripts/network_certificates.py validate --directory config/local/network/pico-a/server
```

Export prompts for a password of at least 12 characters without echoing it; no
password appears in the command line. An optional private `--password-file` supports
local automation. Commands refuse to overwrite previous identity bundles. `inspect`
shows public identities, SHA-256 fingerprints, expiration and a 30-day renewal flag.
Initial CA lifetime is ten years; server/client certificates last one year.

For the macOS Keychain importer, add `--macos-keychain` to `export-browser` and
choose a new output filename. On the Phase 11.4 Mac, OpenSSL's default modern
PKCS#12 package was readable by OpenSSL but Keychain rejected it with MAC
verification failure. The explicit compatibility profile uses SHA-1/3DES package
wrapping and SHA-1 MAC; the default remains modern OpenSSL wrapping. Both retain
password protection, private file permissions and refusal to overwrite. This
only packages the existing client identity: certificate signatures, TLS 1.3,
mTLS, validity and server identity checks are unchanged. Keep compatibility
packages private and use a strong export password. A host decode alone is not
evidence of browser/keychain import.

Chrome's macOS trust integration does not accept a hostname-specific keychain
trust-policy entry. The separately authorized device CA needs SSL trust in the
chosen keychain; Chrome still validates each server's DNS/IP SAN. Approve that
trust scope explicitly. Do not bypass an authority warning or install a global
fleet CA. The [11.4 record](phase11-4-review.md) retains the initial rejected
package and hostname-scoped-trust attempts and their dispositions.

Import the CA certificate into your chosen trust store and the password-protected
PKCS#12 identity into your browser/keychain. This is an explicit operator action:
no script installs trust, modifies a keychain or bypasses browser certificate
warnings. Browse to `https://wsprrypico-<last-six-MAC-hex>.local:<configured-port>/` and select the
appropriate client identity. For a WTP controller, issue a separate client bundle
and supply its certificate/private key plus the device CA to its TLS transport.
WsprryPi Phase 11.1 provides the host TLS transport and settings in its own
repository. This repository owns the Pico implementation; the pinned client
interoperability check below exercises the companion sources unchanged.

Build an inhibited network-enabled image using the generated server bundle:

```sh
cmake --preset pico2-w \
  -DWSPRRY_PICO_NETWORK_PORT=18443 \
  -DWSPRRY_PICO_NETWORK_CREDENTIAL_DIR="$PWD/config/local/network/pico-a/server"
cmake --build --preset pico2-w
```

The port is an explicit deployment choice, not a WTP-assigned default. Directory
contents are `server.crt`, `server.key`, `client-ca.crt` and public `deployment.json`.
The manifest is the sole build hostname/device-ID input. Configuration verifies
its exact SANs, fingerprint, keypair, chain, purpose and validity against the
actual certificate. Wrong-board images fail the runtime deployment identity gate.
Manifest-less valid IP-only bundles retain legacy operation without mDNS.
Missing/invalid inputs fail closed; runtime TLS initialization also checks the keypair.
The SDK and Mbed TLS source revisions are verified. The SDK's pinned Mbed TLS
3.6.6 requires its PSA RNG source, absent from the SDK's older source list; the
firmware build explicitly links that existing source with its upstream license.
TLS 1.2, TLS client mode, PSK/resumption, session tickets and early data are disabled.

Flashing still requires explicit authorization for the chosen board/image. The
standard target remains RF-inhibited; `WsprryPico-StandaloneRF` is separately built
and not qualified for TLS/RF coexistence. Restore the default build configuration
with `-DWSPRRY_PICO_NETWORK_PORT=0` when producing a non-credential image.

The [certificate-alert integration](tls-certificate-alerts.md) describes the
hash-checked fixes applied when building the pinned Mbed TLS sources; the SDK
checkout stays unchanged. [F2/F3/F6 acceptance](phase11-4-f2-f3-f6-results.md)
records replacement-client and actual Chrome IP-SAN results.

### End-user provisioning limitation

These commands are developer provisioning, not a finished Windows setup flow.
The current firmware embeds credentials at build time and has no runtime USB
credential installer or guided Windows provisioning application. A proposed
end-user flow would flash a generic UF2, identify the board over USB, collect
Wi-Fi settings, generate/install its independent credentials and verify the
short URL without asking the user to compile firmware. That flow is not yet
implemented. E1 identity/trust acceptance does not qualify end-user setup.

### Renewal and compromised credentials

Issue a replacement browser/controller identity into a **new** output directory,
export/import it, test it, then remove the old identity from the client. Existing
clients remain trusted until expiration; issuing a replacement does not revoke
an earlier certificate.

Create a replacement server bundle without overwriting the old one:

```sh
python3 scripts/network_certificates.py renew-server \
  --ca-directory config/local/network/pico-a --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --mac-address 88:a2:9e:0a:60:df --output config/local/network/pico-a/server-renewed
```

Rebuild using the replacement directory, then separately authorize flashing.
Clients continue trusting the same CA. DHCP address changes do not require renewal
for hostname access. There is no on-device CRL/OCSP service or runtime rotation yet. If a
client credential or the CA is compromised, create a new device CA with `init` in
a new directory, reissue authorized clients, rebuild/reflash the device with the
new trust chain and replace client trust. This invalidates **all** old clients for
that device. Runtime credential installation/revocation remains Phase 12 work.

### Explicit IP, deliberate hostname change and legacy migration

Add `--address 192.0.2.10` to `init` or `renew-server` to include an optional IP
SAN (repeat for up to four addresses). A literal-IP browser URL requires that
exact IP SAN. WsprryPi can instead connect to an explicit IP with the expected
hostname configured independently; its HTTP authority then uses that hostname.

For a deliberate deployment alias, use the same device ID and an explicit
`--hostname pico-workbench.local` when renewing into a new output directory:

```sh
python3 scripts/network_certificates.py renew-server \
  --ca-directory config/local/network/pico-a --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --hostname pico-workbench.local --output config/local/network/pico-a/server-renamed
```

This requires a certificate update, explicit rebuild/reflash and corresponding
client target/expected-identity update. It creates no runtime setting or schema
migration. The default uses the final three bytes of the observed Wi-Fi station
MAC, lowercase without separators: `88:a2:9e:0a:60:df` produces
`wsprrypico-0a60df.local`. Supply `--mac-address` on initial issuance and renewal;
without it or an explicit `--hostname`, hostname provisioning fails before writing
credentials. It never falls back to a full-ID name. Renewal does not infer an
existing alias; preserve deliberate aliases explicitly with `--hostname`.

Six MAC hex characters are a convenient LAN label, not a uniqueness guarantee:
different MAC prefixes can share the same suffix. Normal probing/conflict handling
still applies. The full 32-hex WTP device ID remains in the deployment manifest
and is checked independently of the short name. TLS authenticates the certified
DNS SAN and CA; knowing a MAC grants no trust. Existing explicit full-ID names
remain valid aliases and are not automatically renamed.

Firmware reads the station MAC after Wi-Fi driver initialization at boot and
reports it as `station_mac`; `stable_hostname` is its derived short default.
Both are empty before a successful valid MAC read, including network-free
recovery boots. They remain the last observed board identity during ordinary
Wi-Fi disable. `configured_hostname` and `advertised_hostname` report the
certificate-bound deployment actually used. Derivation does not rewrite the
certificate or select an uncertified name.

To migrate an existing IP-only CA directory, renew using the actual device ID,
observed `--mac-address` and a new output directory; rebuild with that bundle.
Its existing valid client identities remain trusted. The old
`init --device pico-a --address 192.0.2.10` workflow remains IP-only and has no
advertisement.

mDNS registration begins after Wi-Fi has a usable IPv4 address and the configured
listener is available. Successful probing reports `active`. DHCP replacement
reprobes and announces the new address with cache-flush semantics. Link loss
removes local registration; only an orderly disable with a usable link attempts
a goodbye. A conflict latches and never selects an uncertified automatic suffix.
Resolve the duplicate device/name, then explicitly retry with idle Console
`WIFI OFF`/`WIFI ON` or restart. Name discovery failure does not stop a finite job
or establish inactive output. See the [shared identity contract](phase11-3-identity.md)
and [responder implementation](mdns-responder.md).

Linux clients need functioning system `.local` resolution, such as a properly
configured Avahi/NSS mDNS integration or systemd-resolved mDNS on the active link.
Check `getent ahostsv4 <hostname>` and, where installed, `resolvectl query <hostname>`
or `avahi-resolve-host-name -4 <hostname>`. macOS can inspect with
`dns-sd -G v4 <hostname>` (Ctrl-C to stop). These commands are for later authorized
operational diagnosis. A successful unicast lookup or injected loopback test does
not prove that local multicast/NSS is configured. No helper edits hosts/NSS,
installs resolver services or changes trust stores. See WsprryPi's `docs/wtp-network.md`
for connection settings and the [opt-in 11.4 procedure](phase11-4-acceptance.md).

## Runtime and recovery

USB remains the canonical WTP transport. TCP supplies authenticated certificate
principals to the same Endpoint/JobService. HTTP handlers use the same strict
codec, persistent Store and Scheduler. Credential/private-key data never appears
in API status. See the [API contract](../browser-api.md) for schemas and errors.

The browser offers manual status refresh, station/Wi-Fi/schedule edits, explicit
reload of saved settings, complete job upload/UTC arm, owner abort/release and
Wi-Fi disconnect. Unsaved edits retain their original revision until deliberately
reloaded or successfully saved. Network and config writes reject owned/armed/
running/faulted states. Saving config requires a restart to apply, as with Console.
The RF state displayed by the page is a timestamped snapshot, not a continuously
observed signal.

Console `INFO` includes IPv4/link, enabled/requested state, SNTP counters and
whether network control is configured/listening. `WIFI OFF` / `WIFI ON` remain
inhibited-image Console controls. Browser Wi-Fi disconnect is idle-only and
volatile; reconnect with Console or restart. Recovery boots start network-free.
`ABORT` on the physical Console suspends standalone scheduling and aborts any
current job through JobService, records its terminal result and releases ownership
only after verified shutdown. A disable failure remains a latched fault. `STOP`
retains its earlier standalone-only meaning. No network operation grants this
physical override.

Phase 11.2 admits two isolated TLS clients, at most one WTP stream, one waiting
TCP connection and one computing handshake. The persistent WTP controller can
retain ownership while an independent browser reads status during Armed/Running.
A browser can abort its own job through another authenticated HTTPS request;
a foreign principal or session cannot. Slow/extra clients are bounded and cannot
reset another endpoint, response or replay history. See [browser API bounds](../browser-api.md).

The physical standalone image gives core 1 exclusive ownership of StreamEngine,
PIO/DMA and launch interrupts. Core 0 owns JobService, scheduler, USB, storage,
SNTP, lwIP/CYW43, TLS/PSA/RNG and HTTP. A single release/acquire rendezvous transfers
immutable borrowed commands while the caller waits; there is no abandoned work
queue. Core 1 continuously services RF when core 0 is in crypto or parsing. UTC
is copied as a complete discipline state and ages locally on core 1. Flash writes
remain idle-only and use SDK multicore flash lockout. No TLS step is described as
a measured latency bound. XIP/SRAM/DMA contention and watchdog/flash behavior still
require separately authorized target acceptance.

Console `INFO` adds RF-worker service-gap/poll/roundtrip, command count, core stack
canaries, sampled heap peak and TLS allocation peak. API `transport` diagnostics
include TLS/session limits and progress observations. Network control remains off
by default; the standard image is still RF-inhibited. The [11.2 record](phase11-2-review.md)
contains budgets, tests and the unexecuted target procedure.

## Hardware-free validation

The normal host suite adds HTTP/API tests, browser behavior tests (when Node is
available), certificate lifecycle tests and physical Console abort failure tests.
Actual TLS tests use the SDK-pinned local library and ephemeral test certificates:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/path/to/pico-sdk/lib/mbedtls
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py
```

The TLS driver binds loopback only, port 18443, and replaces raw TCP/clock/RNG
boundaries with host adapters. It never opens a USB device or accesses RF hardware.
Tests verify real TLS 1.3, certificate usage, mandatory ALPN, plaintext/TLS 1.2
rejection, HTTP parsing, CSP hashes, origin checks, revisions, secret redaction,
queued connections, slow-client deadlines, maximum WTP payloads and 512-event
local completion after ARM/disconnect. Host socket tests require permission to
bind loopback in restricted sandboxes. Generated test credentials expire after a
day; regenerate them with `scripts/generate_network_test_credentials.py`, then
reconfigure/rebuild the host target when returning later.

A local simulation preview is available for visual checks:

```sh
python3 scripts/preview_network_browser.py --build build-host
```

It serves `http://127.0.0.1:18300/` and forwards to the host TLS driver using test
credentials. It rewrites the local test authority/origin; it is **not** a deployable
authentication proxy and cannot connect to a Pico. Do not run it alongside the TLS
test, which uses the same loopback port. Stop it with Ctrl-C.

See the [Phase 11 review record](phase11-review.md) for checks, repairs and current
qualification limits, and the [execution prompt](phase11-execution-prompt.md) for
the scope used in this change.

## Companion interoperability and sanitizers

Optional actual client interoperability uses unmodified reviewed WsprryPi sources at
`2e47641f6ebdff104e32999f5194f2e0dc408e06`. Use an explicit clean checkout of that
revision; the option never fetches, edits or builds inside the companion checkout:

```sh
cmake -S . -B build-host \
  -DWSPRRY_PICO_NETWORK_CLIENT_SOURCE=/path/to/clean/2e47641/WsprryPi \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/path/to/pico-sdk/lib/mbedtls
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

The test `network_11_1_interop` (historical target name) builds the existing client, application,
scheduler and TLS/HTTP implementation; the companion's own harness independently
enforces its Pico source pin. An isolated local source copy is useful
when its working checkout is advancing. The tested pair is Pico runtime
`d8cde03f8127b3c2aaf727f2c21c20960f658e84` and Pi `2e47641` (runtime unchanged from `efcc792`); the later Pico
reference/test/documentation commit does not alter that runtime input. OpenSSL development files must already
be installed; set `OPENSSL_ROOT_DIR` if CMake needs their location.

ASan/UBSan applies to C and C++ (including Mbed TLS):

```sh
cmake -S . -B build/phase11-3-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/path/to/pico-sdk/lib/mbedtls \
  -DWSPRRY_PICO_NETWORK_CLIENT_SOURCE=/path/to/clean/2e47641/WsprryPi \
  -DCMAKE_C_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer' \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'
cmake --build build/phase11-3-sanitize --parallel
ctest --test-dir build/phase11-3-sanitize --output-on-failure
```

A separate ThreadSanitizer build can omit TLS and run `rf_worker_tests` and
`rf_worker_failure_tests` with `-DCMAKE_CXX_FLAGS='-fsanitize=thread -fno-omit-frame-pointer'`.
These test software synchronization, not Pico interrupt/flash latency. Optional
actual desktop/mobile rendering uses an already installed Chrome and Node with
built-in WebSocket support: `node tests/network_browser_render.js`. Set
`CHROME_BIN` outside macOS. It starts an isolated local fixture server/profile,
keeps credentials mocked and saves ignored images under `build/phase11-2-ui`.
