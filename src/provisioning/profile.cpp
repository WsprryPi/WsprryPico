#include "provisioning/profile.hpp"

#include "network/identity.hpp"
#include "standalone/config.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <charconv>

namespace wsprrypico::provisioning {
namespace {
bool string_field(const std::optional<wtp::json::Value>& value) {
    return value && value->type() == '"';
}
bool pem(std::string_view text, std::string_view begin, std::string_view end, std::size_t maximum) {
    if (text.size() < begin.size() + end.size() || text.size() > maximum ||
        !text.starts_with(begin))
        return false;
    while (text.ends_with('\n') || text.ends_with('\r'))
        text.remove_suffix(1);
    if (!text.ends_with(end))
        return false;
    return std::all_of(text.begin(), text.end(), [](unsigned char c) {
        return c == '\n' || c == '\r' || (c >= 32 && c < 127);
    });
}
bool private_key(std::string_view text) {
    return pem(text, "-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----", 2048) ||
           pem(text, "-----BEGIN EC PRIVATE KEY-----", "-----END EC PRIVATE KEY-----", 2048);
}
void secure_clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}

// Match the compact JSON escapes used by field clients. Expanding PEM CR/LF
// into six-byte Unicode escapes would make a valid 7,168-byte wire profile
// exceed the durable profile limit after validation.
std::string profile_quote(std::string_view text) {
    std::string out;
    out.reserve(text.size() + 2);
    out += '"';
    constexpr char digits[] = "0123456789abcdef";
    for (unsigned char c : text) {
        switch (c) {
        case '"':
            out += "\\\"";
            break;
        case '\\':
            out += "\\\\";
            break;
        case '\b':
            out += "\\b";
            break;
        case '\f':
            out += "\\f";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            if (c < 32) {
                out += "\\u00";
                out += digits[c >> 4];
                out += digits[c & 15];
            } else
                out += static_cast<char>(c);
        }
    }
    return out + '"';
}
} // namespace

CredentialMaterial credentials(const Profile& profile) {
    return {profile.device_id,          profile.hostname,       profile.port,
            profile.server_certificate, profile.server_private_key, profile.client_ca};
}

std::optional<Profile> parse_profile(std::string_view text) {
    using namespace wtp::json;
    if (text.empty() || text.size() > max_profile_bytes)
        return {};
    auto root = parse(text);
    if (!root || !fields(*root, {"version", "device_id", "wifi", "tls"}) ||
        root->get("version")->raw != "1" || !identifier(*root->get("device_id")))
        return {};
    const auto wifi = root->get("wifi");
    const auto tls = root->get("tls");
    if (!wifi || !tls || !fields(*wifi, {"ssid", "password", "time_server"}) ||
        !fields(*tls,
                {"hostname", "port", "server_certificate", "server_private_key", "client_ca"}) ||
        !string_field(wifi->get("ssid")) || !string_field(wifi->get("password")) ||
        !string_field(wifi->get("time_server")) || !string_field(tls->get("hostname")) ||
        !string_field(tls->get("server_certificate")) ||
        !string_field(tls->get("server_private_key")) || !string_field(tls->get("client_ca")))
        return {};
    const auto port_value = tls->get("port");
    if (!port_value || port_value->type() < '0' || port_value->type() > '9')
        return {};
    unsigned port = 0;
    const auto port_text = static_cast<std::string>(port_value->raw);
    const auto port_result =
        std::from_chars(port_text.data(), port_text.data() + port_text.size(), port);
    if (port_result.ec != std::errc{} || port_result.ptr != port_text.data() + port_text.size() ||
        port == 0 || port > 65535)
        return {};

    Profile result;
    result.device_id = root->get("device_id")->string();
    result.ssid = wifi->get("ssid")->string();
    result.password = wifi->get("password")->string();
    result.time_server = wifi->get("time_server")->string();
    auto hostname = network::canonical_local_hostname(tls->get("hostname")->string());
    if (!hostname ||
        !standalone::valid_wifi_credentials(result.ssid, result.password, result.time_server)) {
        scrub(result);
        return {};
    }
    result.hostname = *hostname;
    result.port = port;
    result.server_certificate = tls->get("server_certificate")->string();
    result.server_private_key = tls->get("server_private_key")->string();
    result.client_ca = tls->get("client_ca")->string();
    if (!pem(result.server_certificate, "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----",
             3072) ||
        !private_key(result.server_private_key) ||
        !pem(result.client_ca, "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----", 3072)) {
        scrub(result);
        return {};
    }
    return result;
}

std::string serialize_profile(const Profile& profile) {
    return "{\"version\":1,\"device_id\":" + profile_quote(profile.device_id) +
           ",\"wifi\":{\"ssid\":" + profile_quote(profile.ssid) +
           ",\"password\":" + profile_quote(profile.password) +
           ",\"time_server\":" + profile_quote(profile.time_server) +
           "},\"tls\":{\"hostname\":" + profile_quote(profile.hostname) +
           ",\"port\":" + std::to_string(profile.port) +
           ",\"server_certificate\":" + profile_quote(profile.server_certificate) +
           ",\"server_private_key\":" + profile_quote(profile.server_private_key) +
           ",\"client_ca\":" + profile_quote(profile.client_ca) + "}}";
}

void scrub(Profile& profile) {
    secure_clear(profile.password);
    secure_clear(profile.server_private_key);
    secure_clear(profile.server_certificate);
    secure_clear(profile.client_ca);
    secure_clear(profile.ssid);
    secure_clear(profile.time_server);
    secure_clear(profile.hostname);
    secure_clear(profile.device_id);
    profile.port = 0;
}
} // namespace wsprrypico::provisioning
