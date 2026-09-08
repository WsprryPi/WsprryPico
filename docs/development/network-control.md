# Phase 11 network control

The implementation provides optional TLS WTP/TCP, HTTPS browser API v1, embedded
operator assets, network status/management and local certificate tooling. Host
TLS/API/browser tests and firmware cross-linking are distinct from physical
network/RF acceptance. No Phase 11 image has been flashed or operated on hardware
by this execution. Phase 12 retains SoftAP/BLE and runtime credential provisioning;
Phase 13 retains final RF/timing/reliability qualification.

## Operator setup and certificates

Network control is disabled by default (`WSPRRY_PICO_NETWORK_PORT=0`). Existing
Wi-Fi/SNTP/USB and recovery behavior remains available. Use the existing Console
configuration to join Wi-Fi; the TLS server requires usable device UTC before
accepting clients. Reserve a stable IPv4 address in DHCP so it continues matching
the device certificate. No cloud service, public domain or public certificate
authority is required.

The helper uses locally installed OpenSSL and Python. It creates a **separate
CA for each device**, server credentials and independently named client identities.
Keep its directory and a backup private. The CA private key is unencrypted on disk
with owner-only permissions; keep it offline when not issuing credentials. Do
not use the same CA across a fleet. Firmware contains its device private key;
credential-bearing build directories are private and generated credentials are
owner-readable only. Such UF2 files are private deployment artifacts, never release
artifacts or source-controlled files.

Example commands use documentation-only IP `192.0.2.10`; substitute the reserved
address and your device name. These commands only create local files:

```sh
python3 scripts/network_certificates.py init \
  --directory config/local/network/pico-a --device pico-a --address 192.0.2.10
python3 scripts/network_certificates.py issue-client \
  --ca-directory config/local/network/pico-a --name operator-browser \
  --output config/local/network/pico-a/operator-browser
python3 scripts/network_certificates.py export-browser \
  --client-directory config/local/network/pico-a/operator-browser \
  --output config/local/network/pico-a/operator-browser.p12
python3 scripts/network_certificates.py inspect --directory config/local/network/pico-a
```

Export prompts for a password of at least 12 characters without echoing it; no
password appears in the command line. An optional private `--password-file` supports
local automation. Commands refuse to overwrite previous identity bundles. `inspect`
shows public identities, SHA-256 fingerprints, expiration and a 30-day renewal flag.
Initial CA lifetime is ten years; server/client certificates last one year.

Import the CA certificate into your chosen trust store and the password-protected
PKCS#12 identity into your browser/keychain. This is an explicit operator action:
no script installs trust, modifies a keychain or bypasses browser certificate
warnings. Browse to `https://<reserved-ip>:<configured-port>/` and select the
appropriate client identity. For a WTP controller, issue a separate client bundle
and supply its certificate/private key plus the device CA to its TLS transport.
The current WsprryPi integration is USB: a shipped WsprryPi TLS transport and its
settings are **not implemented in this repository**.

Build an inhibited network-enabled image using the generated server bundle:

```sh
cmake --preset pico2-w \
  -DWSPRRY_PICO_NETWORK_PORT=18443 \
  -DWSPRRY_PICO_NETWORK_CREDENTIAL_DIR="$PWD/config/local/network/pico-a/server"
cmake --build --preset pico2-w
```

The port is an explicit deployment choice, not a WTP-assigned default. Directory
contents must be `server.crt`, `server.key` and `client-ca.crt`. Missing/invalid inputs
fail closed; runtime TLS initialization must also parse and match the keypair.
The SDK and Mbed TLS source revisions are verified. The SDK's pinned Mbed TLS
3.6.6 requires its PSA RNG source, absent from the SDK's older source list; the
firmware build explicitly links that existing source with its upstream license.
TLS 1.2, TLS client mode, PSK/resumption, session tickets and early data are disabled.

Flashing still requires explicit authorization for the chosen board/image. The
standard target remains RF-inhibited; `WsprryPico-StandaloneRF` is separately built
and not qualified for TLS/RF coexistence. Restore the default build configuration
with `-DWSPRRY_PICO_NETWORK_PORT=0` when producing a non-credential image.

### Renewal and compromised credentials

Issue a replacement browser/controller identity into a **new** output directory,
export/import it, test it, then remove the old identity from the client. Existing
clients remain trusted until expiration; issuing a replacement does not revoke
an earlier certificate.

Create a replacement server bundle without overwriting the old one:

```sh
python3 scripts/network_certificates.py renew-server \
  --ca-directory config/local/network/pico-a --device pico-a --address 192.0.2.10 \
  --output config/local/network/pico-a/server-renewed
```

Rebuild using the replacement directory, then separately authorize flashing.
Clients continue trusting the same CA. An address change also requires a new server
certificate. There is no on-device CRL/OCSP service or runtime rotation yet. If a
client credential or the CA is compromised, create a new device CA with `init` in
a new directory, reissue authorized clients, rebuild/reflash the device with the
new trust chain and replace client trust. This invalidates **all** old clients for
that device. Runtime credential installation/revocation remains Phase 12 work.

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

New TLS handshakes are refused throughout physical armed/running intervals. A
browser cannot reconnect during such a job, including a long future arming lead;
use physical Console ABORT if necessary. An already connected WTP owner can issue
ABORT. The page announces this restriction before job submission and preserves
successful ARM status instead of misdiagnosing the expected connection pause.
When network control is disabled, the earlier armed/running deferral of Wi-Fi
polling is preserved. When enabled, RF is serviced around foreground network
work, but actual refill/handshake/network contention remains a target acceptance
gate. This implementation does not establish continuous browser monitoring while
an RF job or another WTP network client owns the active TLS connection.

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
