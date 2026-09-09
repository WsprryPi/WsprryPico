#pragma once
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace wsprrypico::standalone {
inline constexpr std::size_t max_config_bytes = 1800;
inline constexpr char default_time_server[] = "pool.ntp.org";
struct Schedule {
    std::uint32_t period_s = 0, phase_s = 0;
    bool operator==(const Schedule&) const = default;
};
struct Config {
    bool enabled = false;
    std::uint64_t expires_utc_s = 0; // Zero preserves unbounded version-1 schedules.
    std::string callsign, locator;
    unsigned power_dbm = 0;
    std::string ssid, password;
    std::string ntp_ipv4 = default_time_server; // Legacy key also accepts a DNS hostname.
    std::vector<Schedule> schedules;
    bool operator==(const Config&) const = default;
};
std::optional<Config> parse_config(std::string_view text);
std::string serialize_config(const Config& config);
bool valid_time_server(std::string_view value);
} // namespace wsprrypico::standalone
