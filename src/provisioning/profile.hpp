#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
inline constexpr std::size_t max_profile_bytes = 7168;

struct Profile {
    std::string device_id;
    std::string ssid;
    std::string password;
    std::string time_server;
    std::string hostname;
    unsigned port = 0;
    std::string server_certificate;
    std::string server_private_key;
    std::string client_ca;
    bool operator==(const Profile&) const = default;
};

struct CredentialMaterial {
    std::string_view device_id;
    std::string_view hostname;
    unsigned port = 0;
    std::string_view server_certificate;
    std::string_view server_private_key;
    std::string_view client_ca;
};

CredentialMaterial credentials(const Profile& profile);

std::optional<Profile> parse_profile(std::string_view text);
std::string serialize_profile(const Profile& profile);
void scrub(Profile& profile);

class CredentialValidator {
  public:
    virtual ~CredentialValidator() = default;
    // Platform implementations verify the chain, key pair, exact SAN,
    // device binding, purpose, validity and accepted algorithms.
    virtual bool validate(const Profile& profile) = 0;
};
} // namespace wsprrypico::provisioning
