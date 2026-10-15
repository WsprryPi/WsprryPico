#include "network/consumer_radio.hpp"

#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"

#include <algorithm>
#include <cstring>
#include <limits>
#include <vector>

namespace wsprrypico::network {
namespace {
using wtp::json::Value;
bool elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t limit) {
    return now < then || now - then >= limit;
}
template <std::size_t N>
bool hex_field(const Value& root, std::string_view name, std::array<std::uint8_t, N>& bytes) {
    const auto value = root.get(name);
    return value && value->type() == '"' && bootstrap_unhex(value->string(), bytes);
}
bool same_id(const Value& root, std::string_view name, std::string_view expected) {
    const auto value = root.get(name);
    return value && wtp::json::identifier(*value) && value->string() == expected;
}
bool printable(std::string_view value, std::size_t maximum) {
    return value.size() <= maximum && std::all_of(value.begin(), value.end(), [](unsigned char c) {
               return c >= 32 && c < 127;
           });
}
} // namespace

bool consumer_radio_network_idle(const provisioning::Activity& activity) {
    return activity.output_known && !activity.output_active && !activity.armed &&
           !activity.running && !activity.failed;
}

std::array<std::uint8_t, consumer_radio_transcript_bytes>
consumer_radio_transcript(const ConsumerRadioBinding& binding) {
    std::array<std::uint8_t, consumer_radio_transcript_bytes> result{};
    std::size_t at = 0;
    const auto append = [&](const auto& bytes) {
        std::memcpy(result.data() + at, bytes.data(), bytes.size());
        at += bytes.size();
    };
    std::memcpy(result.data(), consumer_radio_domain, sizeof(consumer_radio_domain));
    at += sizeof(consumer_radio_domain);
    append(binding.device);
    append(binding.boot);
    append(binding.session);
    for (unsigned i = 0; i < 8; ++i)
        result[at++] = static_cast<std::uint8_t>(binding.generation >> (56 - i * 8));
    append(binding.browser_key);
    append(binding.pico_key);
    append(binding.challenge);
    append(binding.browser_nonce);
    return result;
}

std::array<std::uint8_t, consumer_radio_header_bytes>
consumer_radio_header(std::span<const std::uint8_t, 16> session, std::uint64_t sequence) {
    std::array<std::uint8_t, consumer_radio_header_bytes> result{'C', 'R', '0', '1'};
    std::copy(session.begin(), session.end(), result.begin() + 4);
    for (unsigned i = 0; i < 8; ++i)
        result[20 + i] = static_cast<std::uint8_t>(sequence >> (56 - i * 8));
    return result;
}
bool consumer_radio_header_matches(wtp::InputView packet, std::span<const std::uint8_t, 16> session,
                                   std::uint64_t sequence) {
    if (packet.size() < consumer_radio_header_bytes + consumer_radio_tag_bytes ||
        packet.size() > max_http_body)
        return false;
    const auto expected = consumer_radio_header(session, sequence);
    return std::equal(expected.begin(), expected.end(), packet.begin(),
                      [](std::uint8_t a, char b) { return a == static_cast<std::uint8_t>(b); });
}

bool ConsumerRadioApi::available() const {
    const auto* profile = runtime_.consumer_profile();
    return admission_open_ && store_.healthy() &&
           store_.source() == provisioning::ProfileSource::ConsumerProfile && profile &&
           profile->device_id == device_ && store_.sequence() == runtime_.generation() &&
           !profile->password.empty();
}
void ConsumerRadioApi::listeners(bool ap, std::string_view station_ip, std::string_view hostname) {
    if (station_ip == station_ip_ && hostname == hostname_ && ap == ap_available_)
        return;
    const auto name = canonical_local_hostname(hostname);
    const std::string ip = canonical_ipv4(station_ip) && station_ip != "0.0.0.0"
                               ? std::string(station_ip)
                               : std::string{};
    const std::string host = name ? *name : std::string{};
    for (auto& session : sessions_)
        if ((session.interface == ConsumerInterface::AccessPoint && !ap) ||
            (session.interface == ConsumerInterface::Station &&
             (ip != station_ip_ || host != hostname_)))
            close(session);
    ap_available_ = ap;
    station_ip_ = ip;
    hostname_ = host;
}

bool ConsumerRadioApi::page_admitted(const HttpRequest& request,
                                     ConsumerInterface interface) const {
    auto host = request.header("host");
    if (host.ends_with(":80"))
        host.remove_suffix(3);
    // Exact bounded authorities: no userinfo, paths, alternative ports, suffix
    // matches, numeric aliases or arbitrary Host values supplied by DNS rebinding.
    return available() && ((interface == ConsumerInterface::AccessPoint && ap_available_ &&
                            host == "192.168.4.1") ||
                           (interface == ConsumerInterface::Station && !station_ip_.empty() &&
                            (host == station_ip_ || (!hostname_.empty() && host == hostname_))));
}
void ConsumerRadioApi::poll(std::uint64_t now_ms) {
    const bool healthy = available();
    for (auto& session : sessions_) {
        if (session.state == State::None)
            continue;
        if (!healthy || session.binding.generation != store_.sequence() ||
            elapsed(now_ms, session.started_ms,
                    session.state == State::Pending ? login_ms : absolute_ms) ||
            (session.state == State::Active && elapsed(now_ms, session.seen_ms, idle_ms)))
            close(session);
    }
}
bool ConsumerRadioApi::active(std::uint64_t now_ms) {
    poll(now_ms);
    return std::any_of(sessions_.begin(), sessions_.end(),
                       [](const Session& s) { return s.state != State::None; });
}
void ConsumerRadioApi::finish_request(std::uint64_t transaction, bool apply) {
    for (auto& session : sessions_) {
        if (session.pending_transaction != transaction)
            continue;
        // Clear before callbacks: committing a profile can invalidate all sessions.
        session.pending_transaction.reset();
        api_.finish_request(transaction, apply);
        if (setup_delivery_)
            setup_delivery_(transaction, apply, setup_context_);
        return;
    }
}
void ConsumerRadioApi::close(Session& session) {
    if (session.pending_transaction)
        finish_request(*session.pending_transaction, false);
    if (session.crypto)
        session.crypto->clear();
    auto* crypto = session.crypto;
    session = {};
    session.crypto = crypto;
}
void ConsumerRadioApi::close() {
    for (auto& session : sessions_)
        close(session);
}
ConsumerRadioApi::Session* ConsumerRadioApi::select(wtp::InputView packet) {
    if (packet.size() < consumer_radio_header_bytes + consumer_radio_tag_bytes ||
        packet.size() > max_http_body || packet.substr(0, 4) != "CR01")
        return nullptr;
    for (auto& session : sessions_)
        if (session.state != State::None &&
            std::equal(session.binding.session.begin(), session.binding.session.end(),
                       packet.substr(4, 16).begin(),
                       [](std::uint8_t a, char b) { return a == static_cast<std::uint8_t>(b); }))
            return &session;
    return nullptr;
}
bool ConsumerRadioApi::admitted(const HttpRequest& request, bool binary) const {
    auto host = request.header("host");
    if (host.ends_with(":80"))
        host.remove_suffix(3);
    return request.method == "POST" && request.header("origin") == "http://" + std::string(host) &&
           request.header("x-wsprrypico-radio") == "1" &&
           request.header("content-type") ==
               (binary ? "application/octet-stream" : "application/json") &&
           (request.header("sec-fetch-site").empty() ||
            request.header("sec-fetch-site") == "same-origin") &&
           request.header("cookie").empty() && request.body_view().size() <= max_http_body;
}
HttpResponse ConsumerRadioApi::start(const HttpRequest& request, std::uint64_t now_ms,
                                     ConsumerInterface interface) {
    if (std::any_of(sessions_.begin(), sessions_.end(),
                    [](const Session& s) { return s.state == State::Pending; }))
        return http_error(409, "radio_login_pending");
    auto slot = std::find_if(sessions_.begin(), sessions_.end(),
                             [](const Session& s) { return s.crypto && s.state == State::None; });
    if (slot == sessions_.end())
        return http_error(409, "radio_session_capacity");
    auto& session = *slot;
    if (last_start_ms_ && !elapsed(now_ms, *last_start_ms_, 1'000))
        return http_error(429, "radio_login_rate_limited");
    if (request.body_view().size() > 512)
        return http_error(413, "radio_body_too_large");
    const auto root = wtp::json::parse(request.body_view());
    std::uint64_t generation = 0;
    if (!root ||
        !wtp::json::fields(
            *root, {"version", "device_id", "boot_id", "generation", "public_key", "nonce"}) ||
        !root->get("version") || root->get("version")->raw != "1" ||
        !same_id(*root, "device_id", device_) || !same_id(*root, "boot_id", boot_) ||
        !root->get("generation") || !wtp::json::decimal(*root->get("generation"), generation) ||
        generation != store_.sequence())
        return http_error(400, "invalid_radio_identity");
    const auto key = root->get("public_key");
    std::vector<std::uint8_t> decoded;
    if (!key || key->type() != '"' || !bootstrap_unb64url(key->string(), decoded, 32, 32) ||
        !hex_field(*root, "nonce", session.binding.browser_nonce))
        return http_error(400, "invalid_radio_key");
    std::copy(decoded.begin(), decoded.end(), session.binding.browser_key.begin());
    session.binding.generation = generation;
    if (session_serial_ == UINT64_MAX)
        return http_error(503, "radio_session_unavailable");
    if (!bootstrap_unhex(device_, session.binding.device) ||
        !bootstrap_unhex(boot_, session.binding.boot) || !random_.fill(session.binding.session) ||
        std::all_of(session.binding.session.begin(), session.binding.session.end(),
                    [](std::uint8_t b) { return b == 0; }) ||
        std::any_of(sessions_.begin(), sessions_.end(),
                    [&](const Session& other) {
                        return other.state != State::None &&
                               other.binding.session == session.binding.session;
                    }) ||
        !random_.fill(session.binding.challenge) || !session.crypto->begin()) {
        close(session);
        return http_error(503, "radio_session_unavailable");
    }
    // Nonreused boot-local serial prevents stale packets selecting a later occupant,
    // even if a broken RNG repeats an old (now unoccupied) random session ID.
    const auto serial = ++session_serial_;
    for (unsigned i = 0; i < 8; ++i)
        session.binding.session[8 + i] = static_cast<std::uint8_t>(serial >> (56 - i * 8));
    session.binding.pico_key = session.crypto->public_key();
    last_start_ms_ = now_ms;
    session.interface = interface;
    session.authority = request.header("host");
    session.state = State::Pending;
    session.started_ms = session.seen_ms = now_ms;
    return {200,
            "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                ",\"boot_id\":" + wtp::json::quote(boot_) +
                ",\"generation\":" + wtp::json::quote(std::to_string(generation)) +
                ",\"session_id\":" + wtp::json::quote(bootstrap_hex(session.binding.session)) +
                ",\"public_key\":" + wtp::json::quote(bootstrap_b64url(session.binding.pico_key)) +
                ",\"challenge\":" + wtp::json::quote(bootstrap_hex(session.binding.challenge)) +
                ",\"login_ms\":30000}",
            "application/json",
            {}};
}
HttpResponse ConsumerRadioApi::finish(Session& session, const HttpRequest& request,
                                      std::uint64_t now_ms) {
    if (session.state != State::Pending || !request.buffered_body ||
        request.buffered_body.use_count() != 1 ||
        !consumer_radio_header_matches(request.body_view(), session.binding.session, 0))
        return http_error(401, "radio_authentication_required");
    // Every complete finish consumes the pending exchange, even a bad password.
    session.state = State::None;
    if (!session.crypto->authenticate(*request.buffered_body, session.binding,
                                      runtime_.consumer_profile()->password)) {
        close(session);
        return http_error(401, "radio_authentication_failed");
    }
    const auto plain = "{\"authenticated\":true,\"device_id\":" + wtp::json::quote(device_) +
                       ",\"boot_id\":" + wtp::json::quote(boot_) + "}";
    auto response = session.crypto->seal(plain, session.binding, 0);
    if (!response) {
        close(session);
        return http_error(503, "radio_session_unavailable");
    }
    session.state = State::Active;
    session.started_ms = session.seen_ms = now_ms;
    return std::move(*response);
}
HttpResponse ConsumerRadioApi::exchange(Session& session, const HttpRequest& request,
                                        std::uint64_t now_ms, std::uint64_t transaction) {
    if (session.state == State::Active && session.next_sequence == UINT64_MAX) {
        close(session);
        return http_error(401, "radio_authentication_required");
    }
    if (session.state != State::Active || session.pending_transaction || !request.buffered_body ||
        request.buffered_body.use_count() != 1 ||
        !consumer_radio_header_matches(request.body_view(), session.binding.session,
                                       session.next_sequence))
        return http_error(401, "radio_authentication_required");
    // TCP allocates nonreused IDs at accept time. A slow earlier upload may
    // dispatch after a later connection, so dispatch order cannot be monotonic.
    if (!transaction || std::any_of(sessions_.begin(), sessions_.end(), [&](const Session& other) {
            return other.pending_transaction == transaction;
        }))
        return http_error(409, "radio_transaction_reused");
    const auto sequence = session.next_sequence++;
    const auto plaintext = session.crypto->open(*request.buffered_body, session.binding, sequence);
    if (!plaintext) {
        close(session);
        return http_error(401, "radio_authentication_failed");
    }
    session.seen_ms = now_ms;
    const auto root = wtp::json::parse(*plaintext);
    HttpResponse result = http_error(400, "invalid_radio_request");
    if (root && wtp::json::fields(*root, {"method", "path", "if_match", "body"})) {
        const auto method = root->get("method"), path = root->get("path"),
                   match = root->get("if_match"), body = root->get("body");
        if (method && path && match && body && method->type() == '"' && path->type() == '"' &&
            (method->string() == "GET" || method->string() == "POST" ||
             method->string() == "PUT") &&
            path->string().starts_with("/api/v1/") && printable(path->string(), 128) &&
            (match->raw == "null" || (match->type() == '"' && printable(match->string(), 80))) &&
            (method->string() == "GET" ? body->raw == "null" : body->type() == '{')) {
            if (method->string() == "POST" && path->string() == "/api/v1/consumer/logout" &&
                body->raw == "{}") {
                auto response =
                    session.crypto->seal("{\"status\":200,\"etag\":null,\"body\":{\"ok\":true}}",
                                         session.binding, sequence);
                close(session);
                return response ? std::move(*response)
                                : http_error(503, "radio_response_unavailable");
            }
            HttpRequest inner;
            inner.method = method->string();
            inner.path = path->string();
            inner.buffered_body = request.buffered_body;
            inner.selected_body = body->raw == "null" ? wtp::InputView{} : body->raw;
            // A trusted adapter supplies the already-authenticated principal;
            // this internal Host/Origin pair is never a public plaintext API.
            const std::string authority = "192.168.4.1";
            inner.headers = {{"host", authority},
                             {"origin", "https://" + authority},
                             {"sec-fetch-site", "same-origin"},
                             {"content-type", "application/json"},
                             {"x-wsprrypico-request", "1"}};
            if (match->type() == '"')
                inner.headers["if-match"] = match->string();
            if (inner.path.starts_with("/api/v1/consumer/setup/") && setup_handler_) {
                inner.path.erase(0, std::string_view("/api/v1/consumer/setup").size());
                inner.headers["origin"] = "http://192.168.4.1";
                inner.headers["x-wsprrypico-bootstrap"] = "1";
                inner.headers["x-wsprrypico-owner"] = "1";
                result = setup_handler_(inner, transaction, setup_context_);
            } else if (inner.method != "GET" && setup_busy_ && setup_busy_(setup_context_))
                result = http_error(409, "setup_pending");
            else
                result =
                    api_.handle(inner, "consumer-radio:" + bootstrap_hex(session.binding.session),
                                authority, transaction,
                                session.interface == ConsumerInterface::Station
                                    ? ManagementCarrier::ConsumerStation
                                    : ManagementCarrier::ConsumerAp);
            session.pending_transaction = transaction;
        }
    }
    const auto prefix = "{\"status\":" + std::to_string(result.status) + ",\"etag\":" +
                        (result.etag.empty() ? "null" : wtp::json::quote(result.etag)) +
                        ",\"body\":";
    wtp::FrameBuffer envelope;
    const auto size = prefix.size() + result.body_size() + 1;
    if (size > max_http_body - consumer_radio_header_bytes - consumer_radio_tag_bytes ||
        !wtp::memory_admitted(size * 2 + 4096) || !envelope.reserve(size)) {
        finish_request(transaction, false);
        close(session);
        return http_error(503, "radio_response_unavailable");
    }
    envelope.append(wtp::InputView(prefix));
    for (std::size_t at = 0; at < result.body_size();) {
        const auto part = result.body_at(at);
        envelope.append(part);
        at += part.size();
    }
    envelope.append(wtp::InputView("}"));
    if (!wtp::json::parse(envelope.view())) {
        finish_request(transaction, false);
        close(session);
        return http_error(503, "radio_response_unavailable");
    }
    auto response = session.crypto->seal(envelope.view(), session.binding, sequence);
    if (!response) {
        finish_request(transaction, false);
        close(session);
        return http_error(503, "radio_response_unavailable");
    }
    return std::move(*response);
}
HttpResponse ConsumerRadioApi::handle(const HttpRequest& request, std::uint64_t now_ms,
                                      std::uint64_t transaction, ConsumerInterface interface) {
    poll(now_ms);
    if (!available())
        return http_error(409, "consumer_radio_unavailable");
    if (!page_admitted(request, interface))
        return http_error(403, "forbidden");
    if (request.path == "/api/consumer/v1/identity" && request.method == "GET" &&
        page_admitted(request, interface))
        return {200,
                "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                    ",\"boot_id\":" + wtp::json::quote(boot_) +
                    ",\"generation\":" + wtp::json::quote(std::to_string(store_.sequence())) +
                    ",\"authentication\":\"saved_wifi_passphrase\"}",
                "application/json",
                {}};
    const bool binary = request.path != "/api/consumer/v1/start";
    if (!admitted(request, binary))
        return http_error(403, "forbidden");
    if (request.path == "/api/consumer/v1/start")
        return start(request, now_ms, interface);
    auto* session = select(request.body_view());
    if (!session)
        return http_error(401, "radio_authentication_required");
    if (interface != session->interface || request.header("host") != session->authority)
        return http_error(403, "radio_session_context_mismatch");
    if (request.path == "/api/consumer/v1/finish")
        return finish(*session, request, now_ms);
    if (request.path == "/api/consumer/v1/request")
        return exchange(*session, request, now_ms, transaction);
    return http_error(404, "not_found");
}
} // namespace wsprrypico::network
