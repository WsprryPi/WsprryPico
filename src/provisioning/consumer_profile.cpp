#include "provisioning/consumer_profile.hpp"

#include "encoding/wspr.hpp"
#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "provisioning/storage.hpp"
#include "standalone/config.hpp"
#include "wtp/json.hpp"
#include "wtp/sha256.hpp"

#include <algorithm>
#include <charconv>

namespace wsprrypico::provisioning {
namespace {
using wtp::json::Value;

bool text_field(Value value, std::string_view name, std::string& out) {
    const auto field = value.get(name);
    if (!field || field->type() != '"')
        return false;
    out = field->string();
    return true;
}

bool decimal_field(Value value, std::string_view name, std::uint64_t& out, bool nonzero = true) {
    const auto field = value.get(name);
    return field && wtp::json::decimal(*field, out, nonzero);
}

bool lower_hex(std::string_view value, std::size_t count) {
    return value.size() == count && std::all_of(value.begin(), value.end(), [](char c) {
               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
           });
}

bool printable(std::string_view value, std::size_t minimum, std::size_t maximum) {
    return value.size() >= minimum && value.size() <= maximum &&
           std::all_of(value.begin(), value.end(),
                       [](unsigned char c) { return c >= 32 && c <= 126; });
}

bool pem(std::string_view value, std::string_view begin, std::string_view end) {
    if (!value.starts_with(begin) || value.size() < begin.size() + end.size())
        return false;
    while (value.ends_with('\n') || value.ends_with('\r'))
        value.remove_suffix(1);
    return value.ends_with(end) && std::all_of(value.begin(), value.end(), [](unsigned char c) {
               return c == '\n' || c == '\r' || (c >= 32 && c <= 126);
           });
}

bool private_key(std::string_view value) {
    return pem(value, "-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----") ||
           pem(value, "-----BEGIN EC PRIVATE KEY-----", "-----END EC PRIVATE KEY-----");
}

void append_quote(std::string& out, std::string_view value) {
    out += '"';
    constexpr char digits[] = "0123456789abcdef";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') {
            out += '\\';
            out += static_cast<char>(c);
        } else if (c < 32) {
            out += "\\u00";
            out += digits[c >> 4];
            out += digits[c & 15];
        } else
            out += static_cast<char>(c);
    }
    out += '"';
}

void append_tls(std::string& out, const ConsumerTls& tls) {
    out += "{\"hostname\":";
    append_quote(out, tls.hostname);
    out += ",\"port\":443,\"ca_certificate\":";
    append_quote(out, tls.ca_certificate);
    out += ",\"ca_private_key\":";
    append_quote(out, tls.ca_private_key);
    out += ",\"server_certificate\":";
    append_quote(out, tls.server_certificate);
    out += ",\"server_private_key\":";
    append_quote(out, tls.server_private_key);
    out += ",\"ca_not_after_utc\":";
    append_quote(out, std::to_string(tls.ca_not_after_utc));
    out += ",\"server_not_after_utc\":";
    append_quote(out, std::to_string(tls.server_not_after_utc));
    out += '}';
}

void clear(std::string& value);

bool valid(const ConsumerProfile& profile) {
    const auto hostname = network::canonical_local_hostname(profile.tls.hostname);
    if (!network::valid_device_id(profile.device_id) || !profile.owner_epoch ||
        profile.owners.empty() || profile.owners.size() > 4 ||
        !standalone::valid_wifi_credentials(profile.ssid, profile.password, profile.time_server) ||
        !encoding::wspr_type1(profile.callsign, profile.locator, profile.power_dbm) ||
        !lower_hex(profile.request_sha256, 64) || profile.tls.port != 443 || !hostname ||
        *hostname != profile.tls.hostname ||
        !pem(profile.tls.ca_certificate, "-----BEGIN CERTIFICATE-----",
             "-----END CERTIFICATE-----") ||
        !private_key(profile.tls.ca_private_key) ||
        !pem(profile.tls.server_certificate, "-----BEGIN CERTIFICATE-----",
             "-----END CERTIFICATE-----") ||
        !private_key(profile.tls.server_private_key) || !profile.tls.server_not_after_utc ||
        profile.tls.server_not_after_utc > profile.tls.ca_not_after_utc ||
        profile.clients.size() > 4)
        return false;
    std::string tls_check;
    append_tls(tls_check, profile.tls);
    const bool tls_fits = tls_check.size() <= 2304;
    clear(tls_check);
    if (!tls_fits)
        return false;

    std::vector<std::uint8_t> decoded;
    for (std::size_t i = 0; i < profile.owners.size(); ++i) {
        const auto& owner = profile.owners[i];
        if (!network::bootstrap_unb64url(owner, decoded, 65, 65) || decoded[0] != 4 ||
            std::find(profile.owners.begin(), profile.owners.begin() + i, owner) !=
                profile.owners.begin() + i)
            return false;
    }
    std::string previous;
    for (std::size_t i = 0; i < profile.clients.size(); ++i) {
        const auto& client = profile.clients[i];
        if (!printable(client.name, 1, 32) ||
            !network::bootstrap_unb64url(client.csr_der, decoded, 1, 320) ||
            decoded.front() != 0x30 ||
            client.csr_sha256 != network::bootstrap_hex(wtp::sha256(decoded)) ||
            !lower_hex(client.public_key_sha256, 64) || !client.serial || !client.not_after_utc ||
            client.not_after_utc > profile.tls.ca_not_after_utc ||
            (!previous.empty() && previous >= client.public_key_sha256))
            return false;
        for (std::size_t j = 0; j < i; ++j)
            if (profile.clients[j].serial == client.serial)
                return false;
        previous = client.public_key_sha256;
    }
    return true;
}

void clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
} // namespace

std::string serialize_consumer_profile(const ConsumerProfile& profile) {
    if (!valid(profile))
        return {};
    std::string out = "{\"version\":1,\"device_id\":";
    out.reserve(max_profile_bytes);
    append_quote(out, profile.device_id);
    out += ",\"owner_epoch\":";
    append_quote(out, std::to_string(profile.owner_epoch));
    out += ",\"owners\":[";
    for (std::size_t i = 0; i < profile.owners.size(); ++i) {
        if (i)
            out += ',';
        append_quote(out, profile.owners[i]);
    }
    out += "],\"network\":{\"ssid\":";
    append_quote(out, profile.ssid);
    out += ",\"password\":";
    append_quote(out, profile.password);
    out += ",\"time_server\":";
    append_quote(out, profile.time_server);
    out += "},\"station\":{\"callsign\":";
    append_quote(out, profile.callsign);
    out += ",\"locator\":";
    append_quote(out, profile.locator);
    out += ",\"power_dbm\":" + std::to_string(profile.power_dbm) + "},\"tls\":";
    append_tls(out, profile.tls);
    out += ",\"clients\":[";
    for (std::size_t i = 0; i < profile.clients.size(); ++i) {
        const auto& client = profile.clients[i];
        if (i)
            out += ',';
        out += "{\"name\":";
        append_quote(out, client.name);
        out += ",\"csr_der\":";
        append_quote(out, client.csr_der);
        out += ",\"csr_sha256\":";
        append_quote(out, client.csr_sha256);
        out += ",\"public_key_sha256\":";
        append_quote(out, client.public_key_sha256);
        out += ",\"serial\":";
        append_quote(out, std::to_string(client.serial));
        out += ",\"not_after_utc\":";
        append_quote(out, std::to_string(client.not_after_utc));
        out += '}';
    }
    out += "],\"request_sha256\":";
    append_quote(out, profile.request_sha256);
    out += '}';
    if (out.size() > max_profile_bytes) {
        clear(out);
        return {};
    }
    return out;
}

std::optional<ConsumerProfile> parse_consumer_profile(std::string_view text) {
    using namespace wtp::json;
    if (text.empty() || text.size() > max_profile_bytes)
        return {};
    const auto root = parse(text);
    if (!root ||
        !fields(*root, {"version", "device_id", "owner_epoch", "owners", "network", "station",
                        "tls", "clients", "request_sha256"}) ||
        root->get("version")->raw != "1")
        return {};
    ConsumerProfile out;
    std::uint64_t power = 0;
    const auto owners = root->get("owners"), network_value = root->get("network"),
               station = root->get("station"), tls = root->get("tls"),
               clients = root->get("clients");
    if (!text_field(*root, "device_id", out.device_id) ||
        !decimal_field(*root, "owner_epoch", out.owner_epoch) ||
        !text_field(*root, "request_sha256", out.request_sha256) || !owners ||
        owners->type() != '[' || !network_value ||
        !fields(*network_value, {"ssid", "password", "time_server"}) || !station ||
        !fields(*station, {"callsign", "locator", "power_dbm"}) || !tls ||
        !fields(*tls, {"hostname", "port", "ca_certificate", "ca_private_key", "server_certificate",
                       "server_private_key", "ca_not_after_utc", "server_not_after_utc"}) ||
        !clients || clients->type() != '[' || !text_field(*network_value, "ssid", out.ssid) ||
        !text_field(*network_value, "password", out.password) ||
        !text_field(*network_value, "time_server", out.time_server) ||
        !text_field(*station, "callsign", out.callsign) ||
        !text_field(*station, "locator", out.locator) ||
        !text_field(*tls, "hostname", out.tls.hostname) || tls->get("port")->raw != "443" ||
        !text_field(*tls, "ca_certificate", out.tls.ca_certificate) ||
        !text_field(*tls, "ca_private_key", out.tls.ca_private_key) ||
        !text_field(*tls, "server_certificate", out.tls.server_certificate) ||
        !text_field(*tls, "server_private_key", out.tls.server_private_key) ||
        !decimal_field(*tls, "ca_not_after_utc", out.tls.ca_not_after_utc) ||
        !decimal_field(*tls, "server_not_after_utc", out.tls.server_not_after_utc)) {
        scrub(out);
        return {};
    }
    const auto power_value = station->get("power_dbm");
    if (!power_value || power_value->raw.empty() || power_value->raw.size() > 3 ||
        power_value->type() < '0' || power_value->type() > '9') {
        scrub(out);
        return {};
    }
    const auto power_text = static_cast<std::string>(power_value->raw);
    const auto power_result =
        std::from_chars(power_text.data(), power_text.data() + power_text.size(), power);
    if (power_result.ec != std::errc{} ||
        power_result.ptr != power_text.data() + power_text.size() || power > 255) {
        scrub(out);
        return {};
    }
    out.power_dbm = static_cast<unsigned>(power);
    for (const auto element : owners->elements(4)) {
        if (element.type() != '"') {
            scrub(out);
            return {};
        }
        out.owners.push_back(element.string());
    }
    for (const auto element : clients->elements(4)) {
        if (!fields(element, {"name", "csr_der", "csr_sha256", "public_key_sha256", "serial",
                              "not_after_utc"})) {
            scrub(out);
            return {};
        }
        ConsumerClient client;
        if (!text_field(element, "name", client.name) ||
            !text_field(element, "csr_der", client.csr_der) ||
            !text_field(element, "csr_sha256", client.csr_sha256) ||
            !text_field(element, "public_key_sha256", client.public_key_sha256) ||
            !decimal_field(element, "serial", client.serial) ||
            !decimal_field(element, "not_after_utc", client.not_after_utc)) {
            scrub(out);
            return {};
        }
        out.clients.push_back(std::move(client));
    }
    auto canonical = serialize_consumer_profile(out);
    const bool match = !canonical.empty() && canonical == text;
    clear(canonical);
    if (!match) {
        scrub(out);
        return {};
    }
    return out;
}

void scrub(ConsumerProfile& profile) {
    clear(profile.device_id);
    profile.owner_epoch = 0;
    for (auto& owner : profile.owners)
        clear(owner);
    profile.owners.clear();
    clear(profile.ssid);
    clear(profile.password);
    clear(profile.time_server);
    clear(profile.callsign);
    clear(profile.locator);
    profile.power_dbm = 0;
    clear(profile.tls.hostname);
    clear(profile.tls.ca_certificate);
    clear(profile.tls.ca_private_key);
    clear(profile.tls.server_certificate);
    clear(profile.tls.server_private_key);
    profile.tls.ca_not_after_utc = profile.tls.server_not_after_utc = 0;
    for (auto& client : profile.clients) {
        clear(client.name);
        clear(client.csr_der);
        clear(client.csr_sha256);
        clear(client.public_key_sha256);
        client.serial = client.not_after_utc = 0;
    }
    profile.clients.clear();
    clear(profile.request_sha256);
}
} // namespace wsprrypico::provisioning
