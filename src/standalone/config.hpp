#pragma once
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace wsprrypico::standalone {
inline constexpr std::size_t max_config_bytes = 1800;
struct Schedule {
    std::uint32_t period_s = 0, phase_s = 0;
    bool operator==(const Schedule&) const = default;
};
struct Config {
    bool enabled = false;
    std::string callsign, locator;
    unsigned power_dbm = 0;
    std::string ssid, password, ntp_ipv4;
    std::vector<Schedule> schedules;
    bool operator==(const Config&) const = default;
};
std::optional<Config> parse_config(std::string_view text);
std::string serialize_config(const Config& config);
} // namespace wsprrypico::standalone
