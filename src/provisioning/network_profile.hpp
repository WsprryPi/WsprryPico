#pragma once

#include "standalone/config.hpp"

#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
struct NetworkProfile {
    std::string device_id;
    std::string ssid;
    std::string password;
    std::string time_server = standalone::default_time_server;
    bool operator==(const NetworkProfile&) const = default;
};

bool valid_network_profile(const NetworkProfile& profile);
std::optional<NetworkProfile> parse_network_profile(std::string_view text);
std::string serialize_network_profile(const NetworkProfile& profile);
void scrub(NetworkProfile& profile);
} // namespace wsprrypico::provisioning
