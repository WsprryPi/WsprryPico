#include "network/bootstrap_codec.hpp"
#include "provisioning/consumer_profile.hpp"
#include "provisioning/storage.hpp"
#include "wtp/json.hpp"
#include "wtp/sha256.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <limits>
#include <string>

using namespace wsprrypico;

namespace {
std::string certificate() {
    return "-----BEGIN CERTIFICATE-----\nAQ==\n-----END CERTIFICATE-----\n";
}
std::string private_key() {
    return "-----BEGIN PRIVATE KEY-----\nAQ==\n-----END PRIVATE KEY-----\n";
}
std::string owner(unsigned tag) {
    std::array<std::uint8_t, 65> point{};
    point[0] = 4;
    point[64] = static_cast<std::uint8_t>(tag);
    return network::bootstrap_b64url(point);
}
provisioning::ConsumerProfile profile() {
    provisioning::ConsumerProfile value;
    value.device_id = "fd6127d11d6aca42a9905fa3fb1bf1d5";
    value.owner_epoch = 1;
    value.owners = {owner(1)};
    value.ssid = "Network";
    value.password = "pass\"word";
    value.time_server = "time.example.org";
    value.callsign = "K1ABC";
    value.locator = "FN20";
    value.power_dbm = 30;
    value.tls.hostname = "wsprrypico-0a60df.local";
    value.tls.ca_certificate = certificate();
    value.tls.ca_private_key = private_key();
    value.tls.server_certificate = certificate();
    value.tls.server_private_key = private_key();
    value.tls.ca_not_after_utc = 2'000'000'000;
    value.tls.server_not_after_utc = 1'800'000'000;
    value.request_sha256 = std::string(64, 'a');
    return value;
}
void replace(std::string& text, const std::string& old, const std::string& next) {
    const auto offset = text.find(old);
    assert(offset != text.npos);
    text.replace(offset, old.size(), next);
}
} // namespace

int main() {
    auto value = profile();
    auto canonical = provisioning::serialize_consumer_profile(value);
    assert(!canonical.empty() && canonical.size() < provisioning::max_profile_bytes);
    assert(canonical.find(wtp::json::quote(value.tls.ca_certificate)) != canonical.npos);
    auto decoded = provisioning::parse_consumer_profile(canonical);
    assert(decoded && *decoded == value);
    provisioning::scrub(*decoded);
    assert(decoded->password.empty() && decoded->tls.ca_private_key.empty());
    auto six = value;
    six.callsign = "PJ4/K1ABC/P";
    six.locator = "FN20XX";
    const auto six_wire = provisioning::serialize_consumer_profile(six);
    assert(provisioning::parse_consumer_profile(six_wire) == six);
    const auto six_network = provisioning::replace_consumer_network(
        six_wire, six.device_id, "FieldNet", "field-password", "time.example.org",
        std::string(64, 'b'));
    const auto six_readback = provisioning::parse_consumer_profile(six_network);
    assert(six_readback && six_readback->locator == "FN20XX");
    for (auto grid : {"FN20A", "FN20AAA", "FN20AY", "FN20aa", "SN20AA"}) {
        six.locator = grid;
        assert(provisioning::serialize_consumer_profile(six).empty());
        auto invalid = six_wire;
        replace(invalid, "FN20XX", grid);
        assert(!provisioning::parse_consumer_profile(invalid));
    }

    const auto replacement = provisioning::replace_consumer_network(
        canonical, value.device_id, "FieldNet", "field-password", "time.example.org",
        std::string(64, 'b'));
    auto updated = provisioning::parse_consumer_profile(replacement);
    value.ssid = "FieldNet";
    value.password = "field-password";
    value.time_server = "time.example.org";
    value.request_sha256 = std::string(64, 'b');
    assert(updated && *updated == value); // Station, owners, TLS and clients are retained.
    provisioning::scrub(*updated);
    assert(provisioning::replace_consumer_network(canonical, std::string(32, '0'), "FieldNet",
                                                  "field-password", "time.example.org",
                                                  std::string(64, 'b'))
               .empty());
    assert(provisioning::replace_consumer_network(canonical, value.device_id, "FieldNet", "short",
                                                  "time.example.org", std::string(64, 'b'))
               .empty());
    provisioning::scrub(value);
    value = profile();

    auto open_setup = value;
    open_setup.owner_epoch = 0;
    open_setup.owners.clear();
    const auto open_wire = provisioning::serialize_consumer_profile(open_setup);
    assert(!open_wire.empty());
    assert(provisioning::parse_consumer_profile(open_wire) == open_setup);
    open_setup.owner_epoch = 1;
    assert(provisioning::serialize_consumer_profile(open_setup).empty());

    auto changed = canonical;
    replace(changed, "\"owner_epoch\":\"1\"", "\"owner_epoch\":\"01\"");
    assert(!provisioning::parse_consumer_profile(changed));
    changed = canonical;
    replace(changed, "\"version\":1", "\"version\":1,\"version\":1");
    assert(!provisioning::parse_consumer_profile(changed));
    changed = canonical;
    replace(changed, "\"owners\":[", "\"owners\": [");
    assert(!provisioning::parse_consumer_profile(changed));

    value.owners = {owner(1), owner(2), owner(3), owner(4)};
    canonical = provisioning::serialize_consumer_profile(value);
    assert(!canonical.empty());
    value.owners.push_back(owner(5));
    assert(provisioning::serialize_consumer_profile(value).empty());
    value.owners.pop_back();
    value.owners[1] = value.owners[0];
    assert(provisioning::serialize_consumer_profile(value).empty());
    value.owners[1] = owner(2);

    std::array<std::uint8_t, 3> csr{0x30, 0x01, 0x00};
    provisioning::ConsumerClient client;
    client.name = "wspr5";
    client.csr_der = network::bootstrap_b64url(csr);
    client.csr_sha256 = network::bootstrap_hex(wtp::sha256(csr));
    client.public_key_sha256 = std::string(64, 'b');
    client.serial = 1;
    client.not_after_utc = 1'800'000'000;
    value.clients = {client};
    canonical = provisioning::serialize_consumer_profile(value);
    assert(!canonical.empty());
    assert(provisioning::parse_consumer_profile(canonical));
    value.clients[0].csr_sha256[0] = '0';
    assert(provisioning::serialize_consumer_profile(value).empty());
    value.clients[0] = client;

    value.clients = {client, client};
    assert(provisioning::serialize_consumer_profile(value).empty());
    value.clients[1].public_key_sha256 = std::string(64, 'c');
    assert(provisioning::serialize_consumer_profile(value).empty()); // Reused serial.
    value.clients = {client};
    value.tls.ca_certificate = "bad";
    assert(provisioning::serialize_consumer_profile(value).empty());
    value.tls.ca_certificate = certificate();
    value.tls.hostname = "WsprryPico-0a60df.local";
    assert(provisioning::serialize_consumer_profile(value).empty());

    // The accepted four-owner/four-client contract must fit the real journal
    // limit even with maximum CSR DER, JSON escaping and the full TLS budget.
    value = profile();
    value.owner_epoch = std::numeric_limits<std::uint64_t>::max();
    value.callsign = "AA0NT/ABCDEF";
    value.locator = "EM18XX";
    value.owners = {owner(1), owner(2), owner(3), owner(4)};
    value.ssid = std::string(32, '"');
    value.password = std::string(63, '"');
    value.time_server = std::string(63, 'a') + "." + std::string(63, 'a') + "." +
                        std::string(63, 'a') + "." + std::string(61, 'a');
    value.tls.hostname = std::string(63, 'a') + ".local";
    value.tls.ca_not_after_utc = std::numeric_limits<std::uint64_t>::max();
    value.tls.server_not_after_utc = value.tls.ca_not_after_utc - 1;
    std::array<std::uint8_t, 320> maximal_csr{};
    maximal_csr[0] = 0x30;
    for (unsigned i = 0; i < 4; ++i) {
        client.name = std::string(32, '"');
        client.csr_der = network::bootstrap_b64url(maximal_csr);
        client.csr_sha256 = network::bootstrap_hex(wtp::sha256(maximal_csr));
        client.public_key_sha256 = std::string(64, static_cast<char>('a' + i));
        client.serial = std::numeric_limits<std::uint64_t>::max() - i;
        client.not_after_utc = value.tls.ca_not_after_utc - 1;
        value.clients.push_back(client);
    }
    canonical = provisioning::serialize_consumer_profile(value);
    assert(!canonical.empty());
    const auto tls_start = canonical.find("\"tls\":") + 6;
    const auto tls_end = canonical.find(",\"clients\":", tls_start);
    assert(tls_end != canonical.npos && tls_end - tls_start < 2304);
    value.tls.ca_certificate.insert(value.tls.ca_certificate.find("-----END"),
                                    2304 - (tls_end - tls_start), 'A');
    canonical = provisioning::serialize_consumer_profile(value);
    assert(!canonical.empty() && canonical.size() <= provisioning::max_profile_bytes);
    assert(provisioning::parse_consumer_profile(canonical) == value);
    value.clients.push_back(client);
    assert(provisioning::serialize_consumer_profile(value).empty());
    value.clients.pop_back();
    value.tls.ca_certificate.insert(value.tls.ca_certificate.find("-----END"), 1, 'A');
    assert(provisioning::serialize_consumer_profile(value).empty());
    provisioning::scrub(value);
    assert(value.password.empty() && value.tls.server_private_key.empty());
}
