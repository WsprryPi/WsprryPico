#!/usr/bin/env python3
"""Guard first-class, fail-closed TCP/WTP production invariants."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
server = (ROOT / "src/network/pico/server.cpp").read_text()
bootstrap = (ROOT / "src/network/pico/bootstrap_server.cpp").read_text()
server_header = (ROOT / "src/network/pico/server.hpp").read_text()
main = (ROOT / "src/standalone/pico/main.cpp").read_text()
network_cmake = (ROOT / "cmake/network.cmake").read_text()
mbedtls = (ROOT / "src/network/pico/mbedtls_config.h").read_text()
protocol = (ROOT / "docs/protocol/WTP.md").read_text()
lwipopts = (ROOT / "src/standalone/pico/lwipopts.h").read_text()

# Product default is off; a deployment selects its port explicitly.
assert 'set(WSPRRY_PICO_NETWORK_PORT "0"' in network_cmake
assert "TLS listener port; 0 disables network control" in network_cmake
assert "port() const" in server_header and "return credentials_.port;" in server_header

# The engineering TLS binding remains certificate authenticated.
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
assert 'principal_ = "local-network";' in server
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
assert re.search(r"static wsprrypico::network::PicoServer server\s*\(\s*service,", main)
assert "static wsprrypico::standalone::Scheduler scheduler(store, service);" in main

# The AP-local listener also serves recovery for engineering/corrupt profiles.
# Ordinary station mutations retain their independent consumer-source checks.
bootstrap_gate = main.index("const bool bootstrap_started")
bootstrap_call = main.index("bootstrap.start();", bootstrap_gate)
assert "derived_identity && blank_access_available()" in main[bootstrap_gate:bootstrap_call]
assert "network_setup_authority()" in bootstrap
assert "bootstrap.configure_recovery(" in main
assert "reset_coordinator.blocks_admission() || recovery_reset_at" in main
assert "reset_pending" in main[main.index("auto command ="):main.index("if (text == \"INFO\")")]
assert "server.start_plain(plain_lan_port)" in main
listener_slots = re.search(r"#define MEMP_NUM_TCP_PCB_LISTEN\s+(\d+)", lwipopts)
assert listener_slots and int(listener_slots.group(1)) >= 3

# Normative transport text defines explicit TLS and Plain LAN bindings.
for required in ("identical frame stream", "TLS 1.3", "ALPN", "wtp/1", "Plain LAN", "MUST NOT automatically fall back"):
    assert required in protocol

print("Production TCP/WTP remains first-class, shared and fail closed")

# Unknown durable setup outcomes cannot expire/cancel into rollback or accept
# an ACK/new save before reboot/readback resolves the journal authority.
mutation = bootstrap[bootstrap.index("HttpResponse PicoBootstrapServer::mutation("):]
reconcile_guard = mutation.index("if (bootstrap_commit_.reconcile())")
for route in ("/api/bootstrap/v1/start", "/api/bootstrap/v1/submit", "/api/bootstrap/v1/ack"):
    assert reconcile_guard < mutation.index(route)
poll = bootstrap[bootstrap.index("void PicoBootstrapServer::poll("):
                 bootstrap.index("void PicoBootstrapServer::configure(")]
assert re.search(r"if\s*\(bootstrap_commit_\.cancellation_allowed\(\)\)\s*"
                 r"slot_\.expire\(now_ms\);", poll)
assert "const bool healthy = profile_ && profile_->healthy() && bootstrap_commit_.result_verified();" in bootstrap
assert 'bootstrap_commit_.reconcile() ? "reconcile" : slot_name(slot_.state())' in bootstrap
assert bootstrap.index("void erase(std::array<std::uint8_t, 32>& bytes);") < bootstrap.index("void PicoBootstrapServer::poll(")
