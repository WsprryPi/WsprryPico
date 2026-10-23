#include "network/consumer_radio.hpp"

#include "application/resources.hpp"
#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"
#include "wtp/sha256.hpp"

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

std::array<std::uint8_t, 32> consumer_recovery_context(std::span<const std::uint8_t, 16> target,
                                                       ConsumerInterface interface,
                                                       std::string_view authority) {
    std::vector<std::uint8_t> bytes(target.begin(), target.end());
    bytes.push_back(interface == ConsumerInterface::AccessPoint ? 1 : 2);
    bytes.push_back(static_cast<std::uint8_t>(authority.size()));
    bytes.insert(bytes.end(), authority.begin(), authority.end());
    return wtp::sha256(bytes);
}
std::array<std::uint8_t, 32> consumer_radio_digest(const ConsumerRadioBinding& binding) {
    const auto transcript = consumer_radio_transcript(binding);
    if (std::all_of(binding.recovery_context.begin(), binding.recovery_context.end(),
                    [](auto b) { return b == 0; }))
        return wtp::sha256(transcript);
    constexpr char domain[] = "WsprryPico/Consumer-Recovery/1";
    std::array<std::uint8_t, consumer_radio_transcript_bytes + sizeof(domain) + 32> bytes{};
    auto out = std::copy(transcript.begin(), transcript.end(), bytes.begin());
    out = std::copy_n(reinterpret_cast<const std::uint8_t*>(domain), sizeof(domain), out);
    std::copy(binding.recovery_context.begin(), binding.recovery_context.end(), out);
    return wtp::sha256(bytes);
}
std::array<std::uint8_t, 16> consumer_recovery_selector(const ConsumerRadioBinding& binding) {
    constexpr char domain[] = "WsprryPico/Consumer-Recovery/1/selector";
    std::array<std::uint8_t, sizeof(domain) + 48> bytes{};
    auto out =
        std::copy_n(reinterpret_cast<const std::uint8_t*>(domain), sizeof(domain), bytes.begin());
    out = std::copy(binding.device.begin(), binding.device.end(), out);
    out = std::copy(binding.boot.begin(), binding.boot.end(), out);
    std::copy(binding.session.begin(), binding.session.end(), out);
    const auto digest = wtp::sha256(bytes);
    std::array<std::uint8_t, 16> result{};
    std::copy_n(digest.begin(), result.size(), result.begin());
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

std::string_view ConsumerRadioApi::authentication_password() const {
    if (!admission_open_ || !runtime_.control_healthy(store_))
        return {};
    std::string_view password;
    if (store_.source() == provisioning::ProfileSource::ConsumerProfile) {
        const auto* profile = runtime_.consumer_profile();
        if (!profile || profile->device_id != device_)
            return {};
        password = profile->password;
    } else if (store_.source() == provisioning::ProfileSource::NetworkOnly) {
        const auto* profile = runtime_.network_profile();
        if (!profile || profile->device_id != device_)
            return {};
        password = profile->password;
    } else
        return {};
    if (password_store_ && password_store_->state() != provisioning::AccessStoreState::Erased) {
        const auto* saved = password_store_->record();
        if (!saved || saved->reset.pending())
            return {};
        if (!saved->radio_password.empty())
            password = saved->radio_password;
    }
    return password;
}
bool ConsumerRadioApi::available() const {
    return !authentication_password().empty();
}

std::array<std::uint8_t, 32> ConsumerRadioApi::password_digest() const {
    const auto* record = password_store_ ? password_store_->record() : nullptr;
    const std::string_view password = record ? std::string_view(record->radio_password) : "";
    return wtp::sha256(
        std::span(reinterpret_cast<const std::uint8_t*>(password.data()), password.size()));
}

HttpResponse ConsumerRadioApi::password_resource(const HttpRequest& request) {
    if (!password_store_)
        return http_error(404, "not_found");
    const auto revision = "\"password:" + std::to_string(store_.sequence()) + ':' +
                          std::to_string(password_store_->sequence()) + "\"";
    if (request.method != "GET") {
        if (request.method != "PUT")
            return http_error(405, "method_not_allowed");
        if (!api_.access_change_ready())
            return http_error(409, "busy");
        if (request.header("if-match").empty())
            return http_error(428, "revision_required");
        if (request.header("if-match") != revision)
            return http_error(412, "revision_conflict");
        if (request.body_view().size() > 512)
            return http_error(400, "invalid_password");
        const auto root = wtp::json::parse(request.body_view());
        if (!root || application::validate_envelope(*root, "pico-password/1", "password", device_,
                                                    boot_) != application::Envelope::Valid)
            return http_error(400, "invalid_password");
        const auto field = root->get("password");
        if (field->type() != '"' && field->raw != "null")
            return http_error(400, "invalid_password");
        if (field->raw == "null" &&
            ((runtime_.consumer_profile() && runtime_.consumer_profile()->password.empty()) ||
             (runtime_.network_profile() && runtime_.network_profile()->password.empty())))
            return http_error(409, "wifi_password_unavailable");
        auto password = field->raw == "null" ? std::string{} : field->string();
        const bool valid = field->raw == "null" || provisioning::valid_local_password(password);
        const bool saved =
            valid && password_store_->set_radio_password(password, initial_field_password_);
        volatile char* secret = password.data();
        for (std::size_t i = 0; i < password.size(); ++i)
            secret[i] = 0;
        if (!valid)
            return http_error(400, "invalid_password");
        if (!saved)
            return http_error(503, "password_save_unconfirmed");
    }
    const auto* saved = password_store_->record();
    HttpResponse result{
        200,
        "{\"schema\":\"pico-password/1\",\"target\":" + application::target(device_, boot_) +
            ",\"wifi_default\":" + (!saved || saved->radio_password.empty() ? "true" : "false") +
            ",\"saved\":true}",
        "application/json",
        {}};
    result.etag = "\"password:" + std::to_string(store_.sequence()) + ':' +
                  std::to_string(password_store_->sequence()) + "\"";
    return result;
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
    if ((recovery_.interface == ConsumerInterface::AccessPoint && !ap) ||
        (recovery_.interface == ConsumerInterface::Station &&
         (ip != station_ip_ || host != hostname_)))
        close(recovery_);
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
    if (password_store_ && password_store_->sequence() != password_sequence_) {
        const auto current = password_digest();
        // Field/BLE updates share this journal but do not change Pico login.
        if (current != password_digest_)
            close();
        password_digest_ = current;
        password_sequence_ = password_store_->sequence();
    }
    const bool healthy = available();
    if (recovery_.state != State::None &&
        (!healthy || recovery_.binding.generation != store_.sequence() ||
         elapsed(now_ms, recovery_.started_ms, 5'000)))
        close(recovery_);
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
    if (setup_closed_ && std::any_of(session.binding.session.begin(), session.binding.session.end(),
                                     [](auto b) { return b != 0; }))
        setup_closed_(session.binding.session, setup_context_);
    if (session.crypto)
        session.crypto->clear();
    auto* crypto = session.crypto;
    session = {};
    session.crypto = crypto;
}
void ConsumerRadioApi::close() {
    for (auto& session : sessions_)
        close(session);
    close(recovery_);
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
                                      authentication_password())) {
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
HttpResponse ConsumerRadioApi::recovery_discovery(const HttpRequest& request,
                                                  ConsumerInterface interface) const {
    if (!recovery_.crypto)
        return http_error(404, "not_found");
    std::string entries;
    for (const auto& s : sessions_) {
        if (s.state == State::None || s.interface != interface ||
            s.authority != request.header("host"))
            continue;
        if (!entries.empty())
            entries += ',';
        entries +=
            "{\"selector\":" +
            wtp::json::quote(bootstrap_hex(consumer_recovery_selector(s.binding))) +
            ",\"state\":" + wtp::json::quote(s.state == State::Pending ? "pending" : "active") +
            "}";
    }
    return {200,
            "{\"schema\":\"consumer-recovery/1\",\"device_id\":" + wtp::json::quote(device_) +
                ",\"boot_id\":" + wtp::json::quote(boot_) +
                ",\"generation\":" + wtp::json::quote(std::to_string(store_.sequence())) +
                ",\"authority\":" + wtp::json::quote(request.header("host")) + ",\"interface\":" +
                wtp::json::quote(interface == ConsumerInterface::AccessPoint ? "ap" : "station") +
                ",\"proof_ms\":5000,\"sessions\":[" + entries + "]}",
            "application/json",
            {}};
}
HttpResponse ConsumerRadioApi::recovery_start(const HttpRequest& request, std::uint64_t now_ms,
                                              ConsumerInterface interface) {
    if (!recovery_.crypto)
        return http_error(404, "not_found");
    if (recovery_.state != State::None)
        return http_error(409, "radio_recovery_pending");
    if (last_recovery_ms_ && !elapsed(now_ms, *last_recovery_ms_, 1'000))
        return http_error(429, "radio_recovery_rate_limited");
    if (request.body_view().size() > 640)
        return http_error(413, "radio_body_too_large");
    const auto root = wtp::json::parse(request.body_view());
    std::uint64_t generation = 0;
    ConsumerRadioBinding binding;
    std::array<std::uint8_t, 16> target{};
    std::vector<std::uint8_t> key;
    if (!root ||
        !wtp::json::fields(*root, {"version", "device_id", "boot_id", "generation", "public_key",
                                   "nonce", "target_selector"}) ||
        !root->get("version") || root->get("version")->raw != "1" ||
        !same_id(*root, "device_id", device_) || !same_id(*root, "boot_id", boot_) ||
        !root->get("generation") || !wtp::json::decimal(*root->get("generation"), generation) ||
        generation != store_.sequence() || !hex_field(*root, "target_selector", target) ||
        !hex_field(*root, "nonce", binding.browser_nonce) || !root->get("public_key") ||
        root->get("public_key")->type() != '"' ||
        !bootstrap_unb64url(root->get("public_key")->string(), key, 32, 32))
        return http_error(400, "invalid_radio_recovery");
    unsigned matches = 0;
    for (const auto& s : sessions_)
        if (s.state != State::None && consumer_recovery_selector(s.binding) == target) {
            ++matches;
            if (s.interface != interface || s.authority != request.header("host"))
                return http_error(403, "radio_session_context_mismatch");
        }
    if (matches > 1)
        return http_error(503, "radio_recovery_unavailable");
    binding.generation = generation;
    std::copy(key.begin(), key.end(), binding.browser_key.begin());
    // Count even failed RNG/crypto attempts; malformed input performs no crypto.
    last_recovery_ms_ = now_ms;
    if (session_serial_ == UINT64_MAX || !bootstrap_unhex(device_, binding.device) ||
        !bootstrap_unhex(boot_, binding.boot) || !random_.fill(binding.session) ||
        std::all_of(binding.session.begin(), binding.session.end(), [](auto b) { return !b; }) ||
        !random_.fill(binding.challenge) || !recovery_.crypto->begin()) {
        close(recovery_);
        return http_error(503, "radio_recovery_unavailable");
    }
    const auto serial = ++session_serial_;
    for (unsigned i = 0; i < 8; ++i)
        binding.session[8 + i] = static_cast<std::uint8_t>(serial >> (56 - i * 8));
    binding.pico_key = recovery_.crypto->public_key();
    binding.recovery_context = consumer_recovery_context(target, interface, request.header("host"));
    recovery_.binding = binding;
    recovery_.state = State::Pending;
    recovery_.started_ms = now_ms;
    recovery_.interface = interface;
    recovery_.authority = request.header("host");
    recovery_target_ = target;
    return {200,
            "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                ",\"boot_id\":" + wtp::json::quote(boot_) +
                ",\"generation\":" + wtp::json::quote(std::to_string(generation)) +
                ",\"session_id\":" + wtp::json::quote(bootstrap_hex(binding.session)) +
                ",\"public_key\":" + wtp::json::quote(bootstrap_b64url(binding.pico_key)) +
                ",\"challenge\":" + wtp::json::quote(bootstrap_hex(binding.challenge)) +
                ",\"login_ms\":5000,\"recovery\":{\"target_selector\":" +
                wtp::json::quote(bootstrap_hex(target)) +
                ",\"authority\":" + wtp::json::quote(recovery_.authority) + ",\"interface\":" +
                wtp::json::quote(interface == ConsumerInterface::AccessPoint ? "ap" : "station") +
                "}}",
            "application/json",
            {}};
}
HttpResponse ConsumerRadioApi::recovery_finish(const HttpRequest& request,
                                               ConsumerInterface interface) {
    if (recovery_.state != State::Pending || !request.buffered_body ||
        request.buffered_body.use_count() != 1 || request.body_view().size() != 76 ||
        !consumer_radio_header_matches(request.body_view(), recovery_.binding.session, 0))
        return http_error(401, "radio_recovery_required");
    if (interface != recovery_.interface || request.header("host") != recovery_.authority)
        return http_error(403, "radio_session_context_mismatch");
    recovery_.state = State::None; // One complete proof, including bad proofs.
    if (!recovery_.crypto->authenticate(*request.buffered_body, recovery_.binding,
                                        authentication_password())) {
        close(recovery_);
        return http_error(401, "radio_recovery_rejected");
    }
    Session* victim = nullptr;
    for (auto& s : sessions_) {
        if (s.state != State::None && consumer_recovery_selector(s.binding) == recovery_target_ &&
            s.interface == interface && s.authority == recovery_.authority) {
            if (victim) {
                close(recovery_);
                return http_error(503, "radio_recovery_unavailable");
            } else
                victim = &s;
        }
    }
    const auto plain = "{\"retired\":true,\"present\":" + std::string(victim ? "true" : "false") +
                       ",\"target_selector\":" + wtp::json::quote(bootstrap_hex(recovery_target_)) +
                       ",\"device_id\":" + wtp::json::quote(device_) +
                       ",\"boot_id\":" + wtp::json::quote(boot_) + "}";
    auto response = recovery_.crypto->seal(plain, recovery_.binding, 0);
    if (response && victim)
        close(*victim); // False delivery only; never acknowledge another reply.
    close(recovery_);
    return response ? std::move(*response) : http_error(503, "radio_recovery_unavailable");
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
    bool password_saved = false;
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
            if (inner.path == "/api/v1/consumer/password") {
                if (inner.method != "GET" && setup_busy_ && setup_busy_(setup_context_))
                    result = http_error(409, "setup_pending");
                else
                    result = password_resource(inner);
                password_saved = inner.method == "PUT" && result.status == 200;
            } else if (inner.path.starts_with("/api/v1/consumer/setup/") && setup_handler_) {
                inner.path.erase(0, std::string_view("/api/v1/consumer/setup").size());
                // Each production setup decoder has its own closed header
                // policy. Do not carry ordinary API or the other adapter's
                // marker into the owner-claim decoder.
                inner.headers = {{"host", authority},
                                 {"origin", "http://192.168.4.1"},
                                 {"content-type", "application/json"},
                                 {inner.path.starts_with("/api/owner/") ? "x-wsprrypico-owner"
                                                                        : "x-wsprrypico-bootstrap",
                                  "1"}};
                result =
                    setup_handler_(inner, transaction, session.binding.session, setup_context_);
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
        if (password_saved)
            close();
        else
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
        if (password_saved)
            close();
        else
            close(session);
        return http_error(503, "radio_response_unavailable");
    }
    auto response = session.crypto->seal(envelope.view(), session.binding, sequence);
    if (password_saved) {
        password_sequence_ = password_store_->sequence();
        password_digest_ = password_digest();
        close(); // The sealed reply owns its ciphertext; retire even if delivery is lost.
    }
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
    if (request.path == "/api/consumer/v1/presentation" && request.method == "GET")
        return {200,
                "{\"schema\":\"device-presentation/1\",\"device_id\":" + wtp::json::quote(device_) +
                    ",\"boot_id\":" + wtp::json::quote(boot_) +
                    ",\"hostname\":" + wtp::json::quote(hostname_) + "}",
                "application/json",
                {}};
    if (request.path == "/api/consumer/v1/recovery" && request.method == "GET")
        return recovery_discovery(request, interface);
    if (request.path == "/api/consumer/v1/identity" && request.method == "GET" &&
        page_admitted(request, interface))
        return {200,
                "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                    ",\"boot_id\":" + wtp::json::quote(boot_) + ",\"generation\":" +
                    wtp::json::quote(std::to_string(store_.sequence())) + ",\"authentication\":" +
                    wtp::json::quote(password_store_ && password_store_->record() &&
                                             !password_store_->record()->radio_password.empty()
                                         ? "pico_password"
                                         : "saved_wifi_passphrase") +
                    "}",
                "application/json",
                {}};
    const bool binary = request.path != "/api/consumer/v1/start" &&
                        request.path != "/api/consumer/v1/recovery/start";
    if (!admitted(request, binary))
        return http_error(403, "forbidden");
    if (request.path == "/api/consumer/v1/start")
        return start(request, now_ms, interface);
    if (request.path == "/api/consumer/v1/recovery/start")
        return recovery_start(request, now_ms, interface);
    if (request.path == "/api/consumer/v1/recovery/finish")
        return recovery_finish(request, interface);
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
