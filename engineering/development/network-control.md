# Network control and certificates

The application supplies Consumer-Radio HTTP management and explicitly configured engineering HTTPS. [Consumer access](consumer-lan-access.md) defines the station/AP browser path and temporary setup policy; [field access](field-access.md) defines engineering enrollment, passwords/bonds, controller time, and reset. All paths share one JobService. Host validation and cross-linking establish no general physical network/RF or fleet interoperability.

## Current management carriers

| Carrier | Authentication and availability | Operation boundary |
| --- | --- | --- |
| Engineering station HTTPS | TLS 1.3, client certificate fingerprint principal, certified Host/Origin, configured listener, and usable UTC | Shared JSON resources; same target, revisions, validators, and idle/safety gates |
| Engineering field HTTPS | AP-scoped server TLS, password-issued Secure/HttpOnly cookie, and session; existing access health/clock policy | Blank/preclock Configure denied; closed field allowlist currently excludes hostname and GET config |
| Consumer station / AP | Pico password, volatile Consumer-Radio/1 encrypted session bound to actual interface, Host, device/boot, and profile generation | Shared JSON through encrypted wrappers only; station/Wi-Fi edits use authenticated transactional setup. HTTP page delivery remains unauthenticated |
| USB physical management | Separate UMP1 CDC, internal physical principal; no Pico Wi-Fi/UTC prerequisite for negotiation and ordinary saves | Shared JSON plus explicit USB Wi-Fi/AP/time operations; boot/session/target binding, exact revisions, matching response ACK, and finite deadline |

Support does not imply current listener availability or mutation admission. All carriers preserve one JobService and local RP2350 timing; UTC acquisition and per-job uncertainty admission do not calibrate the RF oscillator. Console line commands and UMP1 management frames retain separate roles. Physical USB identity is not cryptographic device authentication.

Every admitted network and USB carrier advertises the same `management` shape within `Wsprry-Control/1`, including five carrier rows, and the actual selected carrier. Root control documents carry `contract:"Wsprry-Control/1"`; mutations require it before domain validation. Historical management generations and control views are unsupported. See [API discovery](../browser-api.md), [USB framing/delivery](../protocol/USB-Management.md), and [Consumer-Radio/1](../protocol/Consumer-Radio-v1.md). HTTP effects wait for the matching complete-response acknowledgement; UMP1 effects wait for the matching resource ACK. Lost delivery cancels undelivered deferred effects, not durable saves or accepted jobs. Read authoritative saved/active state and review before another explicit mutation; never replay an uncertain write automatically.

Source: [carrier projections](../../src/network/management.cpp), [TLS/interface admission](../../src/network/pico/server.cpp), [field dispatch](../../src/network/softap_api.cpp), [consumer dispatch](../../src/network/consumer_radio.cpp), [transactional setup forwarding](../../src/network/pico/bootstrap_server.cpp), [USB dispatch](../../src/network/local_usb_api.hpp), and [UMP1 endpoint](../../src/usb/management_endpoint.cpp). Their existing carrier, field, consumer, and USB tests bound software behavior. Physical interoperability remains limited to identified setups.

## Operator setup and certificates

Consumer management uses its existing encrypted authenticated session on HTTP. Engineering management uses the existing device-specific certificate bundle, TLS 1.3 mutual authentication, and `http/1.1` ALPN. Engineering access still requires its existing qualified clock and profile policy. Shared management remains separate from native execution admission.

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

Export prompts for a password of at least 12 characters without echoing it; no password appears in the command line. An optional private `--password-file` supports local automation. Commands refuse to overwrite previous identity bundles. `inspect` shows public identities, SHA-256 fingerprints, expiration, and a 30-day renewal flag. Initial CA lifetime is ten years; server/client certificates last one year.

For the macOS Keychain importer, add `--macos-keychain` to `export-browser` and choose a new output filename. The explicit compatibility profile uses SHA-1/3DES package wrapping and SHA-1 MAC; the default remains modern OpenSSL wrapping. Both retain password protection, private file permissions, and refusal to overwrite. This only packages the existing client identity: certificate signatures, TLS 1.3, mTLS, validity, and server identity checks are unchanged. Keep compatibility packages private and use a strong export password. A host decode alone is not evidence of browser/keychain import.

Chrome's macOS trust integration does not accept a hostname-specific keychain trust-policy entry. The separately authorized device CA needs SSL trust in the chosen keychain; Chrome still validates each server's DNS/IP SAN. Approve that trust scope explicitly. Do not bypass an authority warning or install a global fleet CA.

Import the CA certificate into the selected trust store and the password-protected PKCS#12 identity into the browser/keychain. This is an explicit operator action: no script installs trust, modifies a keychain, or bypasses browser certificate warnings. Browse to `https://wsprrypico-<last-six-MAC-hex>.local:<configured-port>/` and select the appropriate client identity. For an authenticated engineering management client, issue a separate client bundle and supply its certificate/private key and the device CA to the HTTPS transport. The source-pair checks below exercise the selected companion client against Pico management.

Build an inhibited network-enabled image using the generated server bundle:

```sh
cmake --preset pico2-w -B build/local-engineering-inhibited \
  -DPICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/local-engineering-inhibited/_deps" \
  -DPICOTOOL_GIT_REPOSITORY_URL="$PICOTOOL_FETCH_FROM_GIT_PATH/picotool-src" \
  -DWSPRRY_PICO_NETWORK_PORT=18443 \
  -DWSPRRY_PICO_NETWORK_CREDENTIAL_DIR="$PWD/config/local/network/pico-a/server"
cmake --build build/local-engineering-inhibited --target WsprryPico-Inhibited
```

Choose an unused build directory and supply the pinned local dependencies as the build guide describes. Output is `build/local-engineering-inhibited/firmware/WsprryPico-Inhibited.uf2`. The `pico2-w` build preset selects normal `WsprryPico`, so it is not an inhibited build command. This example only builds; it does not operate a board.

The deployment explicitly selects the listening port. Directory contents are `server.crt`, `server.key`, `client-ca.crt`, and public `deployment.json`. The manifest is the sole build hostname/device-ID input. Configuration verifies its exact SANs, fingerprint, keypair, chain, purpose, and validity against the actual certificate. Wrong-board images fail the runtime deployment identity gate. Network-enabled application builds require a device-bound `.local` DNS identity; manifest-less/IP-only bundles may still be inspected by the lifecycle tool but are rejected by the firmware configuration gate. Missing/invalid inputs fail closed; runtime TLS initialization rechecks chain, keypair, validity, exact DNS SAN, server purpose, and P-256/SHA-256 algorithms after UTC synchronizes. The SDK and Mbed TLS source revisions are verified. The SDK's pinned Mbed TLS 3.6.6 requires its PSA RNG source, absent from the SDK's older source list; the firmware build explicitly links that existing source with its upstream license. TLS 1.2, TLS client mode, PSK/resumption, session tickets, and early data are disabled.

Flashing still requires explicit authorization for the chosen board/image. The standard `WsprryPico` target is RF-capable; `WsprryPico-Inhibited` is explicitly selected for diagnostics, and `WsprryPico-StandaloneRF` remains compatible and not qualified for TLS/RF coexistence. Restore the default build configuration with `-DWSPRRY_PICO_NETWORK_PORT=0` when producing a non-credential image.

The [certificate-alert integration](tls-certificate-alerts.md) describes the hash-checked fixes applied when building the pinned Mbed TLS sources; the SDK checkout stays unchanged.

### End-user provisioning boundary

These commands remain developer provisioning, not a finished end-user setup flow. Current production firmware can boot from a committed runtime profile, enforces access-journal health fail closed, starts encrypted BLE provisioning and local control, and connects the network-only delivery-safe profile activator. The Raspberry Pi/Linux client can write the complete profile transaction. Its deterministic coverage and bounded live local-control evidence do not by themselves qualify a general end-user provisioning path.

Consumer commissioning uses the device-served AP Wi-Fi-first page and optional station setup, followed by ordinary LAN Consumer-Radio access. USB management can create/replace/delete the saved connection without a Pico network. Blank engineering HTTPS remains read-only; that does not remove the separately authorized consumer HTTP commissioning transactions. Engineering BLE/profile provisioning retains explicit device-bound trust enrollment and an off-device CA private key. Qualified controller UTC may arrive through enrolled BLE, engineering field HTTPS, or the independent USB time exchange.

BLE and SoftAP have deterministic policy, parser, and client tests. Cross-builds and bounded peer checks do not establish general physical interoperability.

The device-served SoftAP portal supplies offline consumer setup.

### Renewal and compromised credentials

Issue a replacement browser/controller identity into a **new** output directory, export/import it, test it, then remove the old identity from the client. Existing clients remain trusted until expiration; issuing a replacement does not revoke an earlier certificate.

Create a replacement server bundle without overwriting the old one:

```sh
python3 scripts/network_certificates.py renew-server \
  --ca-directory config/local/network/pico-a --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --mac-address 88:a2:9e:0a:60:df --output config/local/network/pico-a/server-renewed
```

Rebuild using the replacement directory, then separately authorize flashing. Clients continue trusting the same CA. DHCP address changes do not require renewal for hostname access. Current firmware has no on-device CRL/OCSP service or runtime rotation. If a client credential or CA is compromised today, create a new device CA with `init` in a new directory, reissue authorized clients, rebuild/reflash with the new trust chain, and replace client trust.

The runtime profile path commits one complete replacement bundle atomically. Commit immediately supersedes the old client CA and closes network admission; only the applying terminal response may complete before exactly-once activation after delivery or five seconds. Neither generation may admit a new network principal during that interval, so there is no implicit dual-trust interval. Committed corruption fails closed without trust resurrection. The replacement also invalidates old-generation SNTP authority and late DNS/SNTP callbacks. It requires fresh local-password step-up and, while the public default is active, physical or USB confirmation. That runtime path is implemented in both application variants. These source rules establish no general physical provisioning, timing, or RF qualification.

### Explicit IP, deliberate hostname change, and legacy migration

Add `--address 192.0.2.10` to `init` or `renew-server` to include an optional IP SAN (repeat for up to four addresses). A literal-IP browser URL requires that exact IP SAN. WsprryPi can instead connect to an explicit IP with the expected hostname configured independently; its HTTP authority then uses that hostname.

For a deliberate deployment alias, use the same device ID and an explicit `--hostname pico-workbench.local` when renewing into a new output directory:

```sh
python3 scripts/network_certificates.py renew-server \
  --ca-directory config/local/network/pico-a --device-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --hostname pico-workbench.local --output config/local/network/pico-a/server-renamed
```

This requires a certificate update, explicit rebuild/reflash, and corresponding client target/expected-identity update. It creates no runtime setting or schema migration. The default uses the final three bytes of the observed Wi-Fi station MAC, lowercase without separators: `88:a2:9e:0a:60:df` produces `wsprrypico-0a60df.local`. Supply `--mac-address` on initial issuance and renewal; without it or an explicit `--hostname`, hostname provisioning fails before writing credentials. It never falls back to a full-ID name. Renewal does not infer an existing alias; preserve deliberate aliases explicitly with `--hostname`.

Six MAC hex characters are a convenient LAN label, not a uniqueness guarantee: different MAC prefixes can share the same suffix. Normal probing/conflict handling still applies. The full 32-hex Pico device ID remains in the deployment manifest and is checked independently of the short name. TLS authenticates the certified DNS SAN and CA; knowing a MAC grants no TLS trust. Profile admission deliberately uses that observable suffix in the public default local-access password, so a nearby party may obtain ordinary field control until the operator customizes it. Existing explicit full-ID names remain valid aliases and are not automatically renamed.

Firmware reads the station MAC after Wi-Fi driver initialization at boot and reports it as `station_mac`; `stable_hostname` is its derived short default. Both are empty before a successful valid MAC read, including network-free recovery boots. They remain the last observed board identity during ordinary Wi-Fi disable. `configured_hostname` and `advertised_hostname` report the certificate-bound deployment actually used. Derivation does not rewrite the certificate or select an uncertified name.

To migrate an existing IP-only CA directory, renew using the actual device ID, observed `--mac-address`, and a new output directory; rebuild with that bundle. Its existing valid client identities remain trusted. The old `init --device pico-a --address 192.0.2.10` workflow remains IP-only and has no advertisement.

mDNS registration begins after Wi-Fi has a usable IPv4 address and the configured listener is available. Successful probing reports `active`. DHCP replacement reprobes and announces the new address with cache-flush semantics. Link loss removes local registration; only an orderly disable with a usable link attempts a goodbye. A conflict latches and never selects an uncertified automatic suffix. Resolve the duplicate device/name, then explicitly retry with idle Console `WIFI OFF`/`WIFI ON` or restart. Name discovery failure does not stop a finite job or establish inactive output. See the [shared identity contract](network-identity.md) and [responder implementation](mdns-responder.md).

Management discovery advertises `_http._tcp` with its exact current management TXT descriptor. Discovery is a locator, not authentication.

Linux clients need functioning system `.local` resolution, such as a properly configured Avahi/NSS mDNS integration or systemd-resolved mDNS on the active link. Check `getent ahostsv4 <hostname>` and, where installed, `resolvectl query <hostname>` or `avahi-resolve-host-name -4 <hostname>`. macOS can inspect with `dns-sd -G v4 <hostname>` (Ctrl-C to stop). A successful unicast lookup or injected loopback test does not prove that local multicast/NSS is configured. No helper edits hosts/NSS, installs resolver services, or changes trust stores. See the [management-carrier contract](management-carriers.md) for interface and authentication requirements.

## Runtime and recovery

USB management and admitted network carriers dispatch shared JSON resources to the same application authorities, persistent Store, and Scheduler. Complete native jobs execute locally. Credential/private-key data never appears in API status. See the [API contract](../browser-api.md) for schemas and errors.

The production BLE adapter frames the bounded provisioning command stream through fixed 64-byte records and releases activation only after its final ATT indication is confirmed on core 0. BLE provides the commissioning and local management operations in [Field-GATT/1](../protocol/Field-GATT.md). Engineering SoftAP authority uses server-authenticated HTTPS plus a random password-authenticated session principal scoped to that interface; engineering station HTTPS retains mTLS. Consumer station/AP management uses its separate encrypted Consumer-Radio envelope on HTTP. Provisioned pre-clock SoftAP is limited to identity, challenge, password, controller time, and nonsensitive status. Blank engineering HTTPS is read-only; consumer HTTP commissioning has its separate admitted transactions. These policies do not establish arbitrary physical peer/fleet interoperability.

The pinned CYW43 driver supplies DHCP on `192.168.4.1/24`. A blank device's consumer setup URL is `http://192.168.4.1/`; its genuine page encrypts credential submission but HTTP does not authenticate page delivery. Provisioned engineering field access uses `https://<station-MAC-derived-hostname>[<configured-port>]/`, normally resolved by AP-interface mDNS, so Safari validates the existing device certificate by hostname. `ACCESS SOFTAP <full-device-id>` requests a 120-second join grace while access storage is healthy; field, recovery, and fallback requests remain controlled by the access manager. An associated Wi-Fi client retains every AP path independently of browser traffic or authentication. The final disconnect starts a ten-minute inactivity interval. Unjoined initial access expires after ten minutes, or after the Console's 120-second grace. Expired access requires a new deliberate request or a new outage after stable station recovery.

The browser offers manual status refresh, station/Wi-Fi/schedule edits, explicit reload of saved settings, authenticated native schedule stop, and Wi-Fi disconnect. It does not expose generic job upload, UTC ARM, or owner abort/release. Unsaved edits retain their original revision until deliberately reloaded or successfully saved. Network and config writes reject owned/armed/running/faulted states. Station/schedules/flags affect subsequent admissions; network boot changes and sticky pin/drive latches require restart. Saving does not program a pad or clear STOP. Read saved versus active state before applying another mutation, especially after an ambiguous reply. The RF state displayed by the page is a timestamped snapshot, not a continuously observed signal.

Console `INFO` includes IPv4/link, enabled/requested state, SNTP counters, and whether network control is configured/listening. `WIFI OFF` / `WIFI ON` remain inhibited-image Console controls. Browser Wi-Fi disconnect is idle-only and volatile; reconnect with Console or restart. Current firmware recovery boots start network-free. The access-recovery operation instead increments the access epoch and forces persistent field mode while preserving the runtime profile, station, schedules, and watermark. Provisioning reset also commits an unprovisioned tombstone or an explicitly confirmed build-bundle mode; it never exposes legacy standalone Wi-Fi or old build trust by absence. `ABORT` on the physical Console suspends standalone scheduling and aborts any current job through JobService, records its terminal result, and releases ownership only after verified shutdown. A disable failure remains a latched fault. `STOP` suspends standalone scheduling with its restart-cleared semantics. No network operation grants this physical override.

Engineering HTTPS retains two isolated TLS clients, bounded pending admission, and one computing handshake. Management status remains readable while native execution is Armed/Running; disconnect cannot retime it. Generic job/abort wrappers are unavailable. Authenticated native schedule stop uses its explicit target/revision-bound cleanup path. Slow or excess management clients cannot reset another session or replay history. See [browser API bounds](../browser-api.md) and [native execution safety](../protocol/Native-Execution.md).

The physical standalone image gives core 1 exclusive ownership of StreamEngine, PIO/DMA, and launch interrupts. Core 0 owns JobService, scheduler, USB, storage, SNTP, lwIP/CYW43, TLS/PSA/RNG, and HTTP. A single release/acquire rendezvous transfers immutable borrowed commands while the caller waits; there is no abandoned work queue. Core 1 continuously services RF when core 0 is in crypto or parsing. UTC is copied as a complete discipline state and ages locally on core 1. Flash writes remain idle-only and use SDK multicore flash lockout. No TLS step is described as a measured latency bound. XIP/SRAM/DMA contention and watchdog/flash behavior still require separately authorized target acceptance.

Console `INFO` adds RF-worker service-gap/poll/roundtrip, command count, core stack canaries, sampled heap peak, and TLS allocation peak. API `transport` diagnostics include TLS/session limits and progress observations. Engineering mTLS remains off by default; Consumer-Radio retains independent encrypted HTTP management. The standard image is RF-capable; inhibition is explicit.

## Hardware-free validation

The [CI fixture contract](software-build-ci.md#fixture-ownership-clocks-and-resources) defines observed synchronization, enclosing budgets, owned cleanup, module-relative worker paths, and exclusive loopback resources. Use the current registered CTest names and reject empty focused selections. Both actual production source-pair recipes are defined in the [CI source-pair guide](software-build-ci.md#build-reuse-and-source-pairs).

The normal host suite adds HTTP/API tests, browser behavior tests (when Node is available), certificate lifecycle tests, and Console abort failure-path checks. Actual TLS tests use the SDK-pinned local library and ephemeral test certificates:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/path/to/pico-sdk/lib/mbedtls
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

The TLS driver binds loopback only, port 18443, and replaces raw TCP/clock/RNG boundaries with host adapters. It never opens a USB device or accesses RF hardware. Tests verify real TLS 1.3, certificate usage, mandatory ALPN, plaintext/TLS 1.2 rejection, HTTP parsing, CSP hashes, origin checks, revisions, secret redaction, queued connections, slow-client deadlines, and native Test Tone status and stop. Host socket tests require permission to bind loopback in restricted sandboxes. Generated test credentials expire after a day; host configuration validates the cached fixture and deterministically regenerates an expired or incomplete fixed-build-directory copy before compiling the tests.

A local simulation preview is available for visual checks:

```sh
python3 scripts/preview_network_browser.py --build build-host
```

It serves `http://127.0.0.1:18300/` and forwards to the host TLS driver using test credentials. It rewrites the local test authority/origin; it is **not** a deployable authentication proxy and cannot connect to a Pico. Do not run it alongside the TLS test, which uses the same loopback port. Stop it with Ctrl-C.


## Companion interoperability and sanitizers

Optional actual client interoperability compiles caller-selected WsprryPi sources, including edited working files. Source paths and available Git identity are informational; a historical revision or clean checkout is not required. Missing required files and compiler/contract errors still fail. The options never fetch, edit, or build inside the companion checkout:

```sh
cmake -S . -B build-host \
  -DWSPRRY_PICO_WSPRRYPI_SOURCE=/path/to/selected/WsprryPi \
  -DWSPRRY_PICO_NETWORK_CLIENT_SOURCE=/path/to/selected/WsprryPi \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/path/to/pico-sdk/lib/mbedtls
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

The `host_client_interop_tests` fixture compiles and exercises the selected companion's retained byte-stream interface. The `network_11_1_interop` target runs the actual selected Pi TLS/HTTP client against Pico's native status and stop handlers and retired-route refusals. Native engine and authority tests preserve typed execution safety without an external job client. Pi's current-source network and USB acceptance suites independently exercise production management, protected pairing, crypto, journals, and source selection. Use unused build directories, serialize fixtures sharing loopback ports, and retain the separately pinned MbedTLS dependency policy. OpenSSL development files must already be installed; set `OPENSSL_ROOT_DIR` if CMake needs its location.

ASan/UBSan applies to C and C++ (including Mbed TLS):

```sh
cmake -S . -B build/network-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/path/to/pico-sdk/lib/mbedtls \
  -DWSPRRY_PICO_NETWORK_CLIENT_SOURCE=/path/to/selected/WsprryPi \
  -DCMAKE_C_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer' \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'
cmake --build build/network-sanitize --parallel
ctest --test-dir build/network-sanitize --output-on-failure
```

A separate ThreadSanitizer build can omit TLS and run `rf_worker_tests` and `rf_worker_failure_tests` with `-DCMAKE_CXX_FLAGS='-fsanitize=thread -fno-omit-frame-pointer'`. These test software synchronization, not Pico interrupt/flash latency.
