#!/usr/bin/env python3
"""Guard first-class, fail-closed TCP/WTP production invariants."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
server = (ROOT / "src/network/pico/server.cpp").read_text()
bootstrap = (ROOT / "src/network/pico/bootstrap_server.cpp").read_text()
server_header = (ROOT / "src/network/pico/server.hpp").read_text()
main = (ROOT / "src/standalone/pico/main.cpp").read_text()
network_cmake = (ROOT / "cmake/network.cmake").read_text()
mbedtls = (ROOT / "src/network/pico/mbedtls_config.h").read_text()
protocol = (ROOT / "docs/protocol/WTP.md").read_text()

# Product default is off; a deployment selects its port explicitly.
assert 'set(WSPRRY_PICO_NETWORK_PORT "0"' in network_cmake
assert "TLS listener port; 0 disables network control" in network_cmake
assert "port() const" in server_header and "return credentials_.port;" in server_header

# The only production TCP listener is certificate-authenticated TLS 1.3.
assert "MBEDTLS_SSL_VERSION_TLS1_3" in server
assert "mbedtls_ssl_conf_min_tls_version" in server
assert "mbedtls_ssl_conf_max_tls_version" in server
assert "MBEDTLS_SSL_VERIFY_REQUIRED" in server
assert 'static const char* protocols[] = {"wtp/1", "http/1.1", nullptr};' in server
assert "mbedtls_ssl_get_peer_cert" in server
assert "mbedtls_ssl_get_verify_result" in server
assert "mbedtls_ssl_get_alpn_protocol" in server
assert '#undef MBEDTLS_SSL_PROTO_TLS1_2' in mbedtls
assert '#undef MBEDTLS_SSL_TLS1_3_KEY_EXCHANGE_MODE_PSK_ENABLED' in mbedtls
assert '#undef MBEDTLS_SSL_EARLY_DATA' in mbedtls

# Certificate identity becomes the transport principal; WTP is not decoded or
# authorized by a parallel network-specific job implementation.
assert 'principal_ = "tls-cert:";' in server
assert "endpoint_.connect(principal_);" in server
assert "plain_offset_ += endpoint_.receive(bytes, now);" in server
assert "wtp::Endpoint endpoint_;" in server_header

# Activation closes the TLS listener before reboot, and recovery can close the
# bootstrap listener. lwIP panics if tcp_abort is used on either LISTEN PCB.
for source in (server, bootstrap):
    assert "tcp_close(listener_)" in source
    assert "tcp_abort(listener_)" not in source

# USB, BLE and TCP endpoints share the one production JobService. Complete-job
# execution therefore retains one ownership, scheduler and local timing source.
assert main.count("static wsprrypico::wtp::JobService service(") == 1
assert "static wsprrypico::wtp::Endpoint endpoint(service," in main
assert "static wsprrypico::wtp::Endpoint ble_endpoint(service," in main
assert "static wsprrypico::network::PicoServer server(service," in main
assert "static wsprrypico::standalone::Scheduler scheduler(store, service);" in main

# The bounded listen-PCB slot belongs to exactly one surface. A provisioned
# image must not reserve the blank-device plaintext listener ahead of TLS.
bootstrap_gate = main.index("const bool bootstrap_started")
bootstrap_call = main.index("bootstrap.start();", bootstrap_gate)
assert "RuntimeSource::Unprovisioned" in main[bootstrap_gate:bootstrap_call]

# Normative transport text explicitly rejects plaintext and downgrade.
for required in ("identical frame stream", "TLS 1.3", "ALPN", "wtp/1", "Plaintext TCP"):
    assert required in protocol

print("Production TCP/WTP remains first-class, shared and fail closed")
