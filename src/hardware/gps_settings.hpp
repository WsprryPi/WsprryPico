// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/si5351_settings.hpp"
#include "time/gps.hpp"

namespace wsprrypico::hardware {
struct GpsSettings {
    bool enabled = false;
    enum class Receiver { Qlg3, E108 } receiver = Receiver::Qlg3;
    unsigned rx_gp = 1, pps_gp = 3, baud = 9600;
    std::optional<unsigned> tx_gp;
    bool pps_active_high = true;
    bool pairing_qualified = false;
    int utc_second_offset = 0;
    std::int32_t pps_offset_ns = 0;
    unsigned minimum_message_delay_ms = 0, maximum_message_delay_ms = 800;
    unsigned receiver_uncertainty_us = 100, capture_uncertainty_us = 100;
    enum class Location { Manual, Gps } location = Location::Manual;
    unsigned position_maximum_age_s = 30;
    bool automatic_rf_calibration = false;
    unsigned calibration_maximum_age_s = 3600;
    enum class Daylight { Always, Day, Night, DayManual, NightManual } daylight = Daylight::Always;
    bool daylight_uses_gps() const {
        return daylight == Daylight::Day || daylight == Daylight::Night;
    }
    bool operator==(const GpsSettings&) const = default;
    time::gps::PairingPolicy pairing() const {
        return {pairing_qualified,
                utc_second_offset,
                minimum_message_delay_ms * 1'000'000ULL,
                maximum_message_delay_ms * 1'000'000ULL,
                receiver_uncertainty_us * 1000ULL,
                pps_offset_ns};
    }
};
// Actual peripheral mappings on exposed Pico 2 W pins; not arbitrary GPIOs.
std::optional<unsigned> gps_uart(unsigned rx_gp);
std::string validate_gps_settings(const GpsSettings&);
std::string validate_gps(const PinPlan&, const std::optional<Si5351Settings>&, const GpsSettings&,
                         const FilterSettings& = {});
std::optional<GpsSettings> parse_gps(std::string_view);
std::string serialize_gps(const GpsSettings&);
} // namespace wsprrypico::hardware
