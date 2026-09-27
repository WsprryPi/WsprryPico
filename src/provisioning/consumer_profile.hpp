#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace wsprrypico::provisioning {
struct ConsumerClient {
    std::string name;
    std::string csr_der;
    std::string csr_sha256;
    std::string public_key_sha256;
    std::uint64_t serial = 0;
    std::uint64_t not_after_utc = 0;
    bool operator==(const ConsumerClient&) const = default;
};

struct ConsumerTls {
    std::string hostname;
    unsigned port = 443;
    std::string ca_certificate;
    std::string ca_private_key;
    std::string server_certificate;
    std::string server_private_key;
    std::uint64_t ca_not_after_utc = 0;
    std::uint64_t server_not_after_utc = 0;
    bool operator==(const ConsumerTls&) const = default;
};

struct ConsumerProfile {
    std::string device_id;
    std::uint64_t owner_epoch = 0;
    std::vector<std::string> owners;
    std::string ssid, password, time_server;
    std::string callsign, locator;
    unsigned power_dbm = 0;
    ConsumerTls tls;
    std::vector<ConsumerClient> clients;
    std::string request_sha256;
    bool operator==(const ConsumerProfile&) const = default;
};

// Structural, canonical journal admission only. A platform credential
// validator must additionally verify P-256 points, CSRs, certificate chains,
// key pairs, validity, SAN and exact device identity before activation.
std::optional<ConsumerProfile> parse_consumer_profile(std::string_view text);
std::string serialize_consumer_profile(const ConsumerProfile& profile);
void scrub(ConsumerProfile& profile);
} // namespace wsprrypico::provisioning
