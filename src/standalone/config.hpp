#pragma once
#include "hardware/pins.hpp"
#include "rf/amplifier_timing.hpp"
#include "wtp/json.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace wsprrypico::standalone {
inline constexpr unsigned default_ntp_timeout_s = 3600;
inline constexpr unsigned minimum_ntp_timeout_s = 60;
inline constexpr unsigned maximum_ntp_timeout_s = 86400;
inline constexpr std::size_t max_config_bytes = 1800;
inline constexpr char default_time_server[] = "pool.ntp.org";
struct Schedule {
    std::uint32_t period_s = 0, phase_s = 0;
    bool operator==(const Schedule&) const = default;
};
struct Config {
    hardware::PinPlan pins;
    rf::AmplifierTiming amplifier_timing;
    unsigned gpio_drive_ma = 4; // Nominal direct RF pad current, never WSPR power.
    std::int32_t manual_correction_ppb = 0;
    bool ntp_rf_calibration =
        false; // Legacy storage compatibility only; never selects RF correction.
    // No transmit frequency is selected by a firmware image or legacy record.
    std::optional<std::uint32_t> wspr_dial_frequency_hz;
    bool enabled = false;
    bool allow_unqualified_frequency = false;
    bool allow_non_amateur_frequency = false;
    std::uint64_t expires_utc_s = 0; // Zero preserves unbounded version-1 schedules.
    std::string callsign, locator;
    unsigned power_dbm = 0;
    std::string ssid, password;
    std::string ntp_ipv4 = default_time_server; // Legacy key also accepts a DNS hostname.
    std::vector<Schedule> schedules;
    unsigned ntp_timeout_s = default_ntp_timeout_s;
    bool operator==(const Config&) const = default;
};
std::optional<Config> parse_config(std::string_view text);
std::string serialize_config(const Config& config, bool amplifier_view = false);
bool valid_gpio_drive(unsigned ma);
bool valid_gpio_drive_token(wtp::json::Value value);
bool valid_ntp_timeout_token(wtp::json::Value value);
bool valid_time_server(std::string_view value);
// Standalone USB dial to nominal RF targets. Calibration and NCO realization
// belong to the engine, after these exact requested targets are constructed.
inline constexpr std::uint64_t audio_offset_nhz = 1'500'000'000'000ULL;
inline constexpr std::uint64_t spacing_nhz = 1'464'843'750ULL;
inline constexpr std::uint64_t center_to_tone0_nhz = 2'197'265'625ULL;
inline constexpr std::uint32_t minimum_wspr_dial_hz = 98'503;
inline constexpr std::uint32_t maximum_wspr_dial_hz = 74'998'496;
std::optional<std::array<std::uint64_t, 4>> wspr_tones(std::uint64_t dial_hz);
bool valid_wspr_frequency_token(wtp::json::Value value);
bool wspr_frequency_allowed(const Config& config, std::uint64_t minimum_nhz,
                            std::uint64_t maximum_nhz);
bool valid_wifi_credentials(std::string_view ssid, std::string_view password,
                            std::string_view time_server);
} // namespace wsprrypico::standalone
