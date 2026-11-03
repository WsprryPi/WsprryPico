// SPDX-License-Identifier: MIT
#include "hardware/gps_settings.hpp"

#include "wtp/json.hpp"

#include <charconv>

namespace wsprrypico::hardware {
std::optional<unsigned> gps_uart(unsigned rx) {
    switch (rx) {
    case 1:
    case 13:
    case 17:
        return 0;
    case 5:
    case 9:
    case 21:
        return 1;
    default:
        return {};
    }
}
namespace {
std::optional<unsigned> tx_uart(unsigned tx) {
    switch (tx) {
    case 0:
    case 12:
    case 16:
    case 28:
        return 0;
    case 4:
    case 8:
    case 20:
        return 1;
    default:
        return {};
    }
}
template <class T> bool integer(wtp::json::Value value, T& out) {
    if (value.raw.empty() || value.raw.size() > 11)
        return false;
    const std::string text(value.raw);
    const auto result = std::from_chars(text.data(), text.data() + text.size(), out);
    return result.ec == std::errc{} && result.ptr == text.data() + text.size() &&
           std::to_string(out) == text;
}
} // namespace
std::string validate_gps_settings(const GpsSettings& s) {
    const auto uart = gps_uart(s.rx_gp);
    if (!uart || !eligible(s.pps_gp) || !(s.pps_gp & 1u) || s.pps_gp == s.rx_gp)
        return "invalid_gps_pins";
    if (s.receiver != GpsSettings::Receiver::Qlg3 && s.receiver != GpsSettings::Receiver::E108)
        return "unsupported_gps_receiver";
    if (s.baud != 9600 && s.baud != 19200 && s.baud != 38400 && s.baud != 115200)
        return "unsupported_gps_baud";
    if (s.tx_gp && (s.receiver == GpsSettings::Receiver::Qlg3 || !tx_uart(*s.tx_gp) ||
                    tx_uart(*s.tx_gp) != uart || s.tx_gp == s.pps_gp))
        return "unsupported_gps_transmit";
    auto policy = s.pairing();
    policy.qualified = true;
    if (!time::gps::valid(policy) || s.capture_uncertainty_us < 1 ||
        s.capture_uncertainty_us > 100'000 || s.position_maximum_age_s < 1 ||
        s.position_maximum_age_s > 3600 || s.calibration_maximum_age_s < 10 ||
        s.calibration_maximum_age_s > 86400)
        return "invalid_gps_policy";
    if (s.location != GpsSettings::Location::Manual && s.location != GpsSettings::Location::Gps)
        return "invalid_gps_location";
    if (s.daylight != GpsSettings::Daylight::Always && s.daylight != GpsSettings::Daylight::Day &&
        s.daylight != GpsSettings::Daylight::Night)
        return "invalid_gps_daylight";
    if ((!s.enabled && (s.location == GpsSettings::Location::Gps || s.automatic_rf_calibration ||
                        s.daylight != GpsSettings::Daylight::Always)) ||
        (s.automatic_rf_calibration && !s.pairing_qualified))
        return "gps_required";
    return {};
}
std::string validate_gps(const PinPlan& pins, const std::optional<Si5351Settings>& si,
                         const GpsSettings& s, const FilterSettings& filters) {
    if (auto error = validate_gps_settings(s); !error.empty())
        return error;
    if (!s.enabled)
        return {};
    auto allocation = validate(pins);
    if (pins.engine == PinPlan::Engine::I2c) {
        if (!si)
            return "si5351_configuration_required";
        const auto complete = validate_si5351(pins, *si, 1u << ((s.pps_gp >> 1u) & 7u), filters);
        if (!complete.valid())
            return "invalid_si5351_allocation";
        allocation = complete.pins;
    } else {
        if (auto error = validate_filters(filters, pins); !error.empty())
            return error;
        for (unsigned i = 0; i < filters.output_count; ++i)
            allocation.owners[filters.outputs[i].gp] = "filter_selector";
    }
    if (!allocation.valid())
        return allocation.error;
    for (const auto gp : {std::optional(s.rx_gp), std::optional(s.pps_gp), s.tx_gp})
        if (gp && !allocation.owners[*gp].empty())
            return "gps_pin_conflict";
    // PPS and Si5351 loopback reserve complete, separate PWM slices.
    return {};
}
std::optional<GpsSettings> parse_gps(std::string_view text) {
    using namespace wtp::json;
    const auto root = text.size() <= 1024 ? parse(text) : std::nullopt;
    if (!root ||
        !fields(*root,
                {"enabled", "receiver", "rx_gp", "pps_gp", "tx_gp", "baud", "pps_active_high",
                 "pairing_qualified", "utc_second_offset", "pps_offset_ns",
                 "minimum_message_delay_ms", "maximum_message_delay_ms", "receiver_uncertainty_us",
                 "capture_uncertainty_us", "location", "position_maximum_age_s",
                 "automatic_rf_calibration", "calibration_maximum_age_s", "daylight"}))
        return {};
    GpsSettings s;
    for (auto [key, out] : std::array<std::pair<const char*, unsigned*>, 9>{
             {{"rx_gp", &s.rx_gp},
              {"pps_gp", &s.pps_gp},
              {"baud", &s.baud},
              {"minimum_message_delay_ms", &s.minimum_message_delay_ms},
              {"maximum_message_delay_ms", &s.maximum_message_delay_ms},
              {"receiver_uncertainty_us", &s.receiver_uncertainty_us},
              {"capture_uncertainty_us", &s.capture_uncertainty_us},
              {"position_maximum_age_s", &s.position_maximum_age_s},
              {"calibration_maximum_age_s", &s.calibration_maximum_age_s}}})
        if (!integer(*root->get(key), *out))
            return {};
    if (!integer(*root->get("utc_second_offset"), s.utc_second_offset) ||
        !integer(*root->get("pps_offset_ns"), s.pps_offset_ns))
        return {};
    if (root->get("tx_gp")->raw != "null") {
        unsigned tx = 0;
        if (!integer(*root->get("tx_gp"), tx))
            return {};
        s.tx_gp = tx;
    }
    for (auto [key, out] : std::array<std::pair<const char*, bool*>, 4>{
             {{"enabled", &s.enabled},
              {"pps_active_high", &s.pps_active_high},
              {"pairing_qualified", &s.pairing_qualified},
              {"automatic_rf_calibration", &s.automatic_rf_calibration}}}) {
        const auto value = *root->get(key);
        if (value.raw != "true" && value.raw != "false")
            return {};
        *out = value.boolean();
    }
    for (const auto key : {"receiver", "location", "daylight"})
        if (root->get(key)->type() != '"')
            return {};
    const auto receiver = root->get("receiver")->string();
    if (receiver == "qlg3")
        s.receiver = GpsSettings::Receiver::Qlg3;
    else if (receiver == "e108")
        s.receiver = GpsSettings::Receiver::E108;
    else
        return {};
    const auto location = root->get("location")->string();
    if (location == "manual")
        s.location = GpsSettings::Location::Manual;
    else if (location == "gps")
        s.location = GpsSettings::Location::Gps;
    else
        return {};
    const auto daylight = root->get("daylight")->string();
    if (daylight == "always")
        s.daylight = GpsSettings::Daylight::Always;
    else if (daylight == "day")
        s.daylight = GpsSettings::Daylight::Day;
    else if (daylight == "night")
        s.daylight = GpsSettings::Daylight::Night;
    else
        return {};
    if (!validate_gps_settings(s).empty())
        return {};
    return s;
}
std::string serialize_gps(const GpsSettings& s) {
    const auto flag = [](bool value) { return value ? "true" : "false"; };
    return "{\"enabled\":" + std::string(flag(s.enabled)) + ",\"receiver\":\"" +
           (s.receiver == GpsSettings::Receiver::Qlg3 ? "qlg3" : "e108") +
           "\",\"rx_gp\":" + std::to_string(s.rx_gp) + ",\"pps_gp\":" + std::to_string(s.pps_gp) +
           ",\"tx_gp\":" + (s.tx_gp ? std::to_string(*s.tx_gp) : "null") +
           ",\"baud\":" + std::to_string(s.baud) +
           ",\"pps_active_high\":" + flag(s.pps_active_high) +
           ",\"pairing_qualified\":" + flag(s.pairing_qualified) +
           ",\"utc_second_offset\":" + std::to_string(s.utc_second_offset) +
           ",\"pps_offset_ns\":" + std::to_string(s.pps_offset_ns) +
           ",\"minimum_message_delay_ms\":" + std::to_string(s.minimum_message_delay_ms) +
           ",\"maximum_message_delay_ms\":" + std::to_string(s.maximum_message_delay_ms) +
           ",\"receiver_uncertainty_us\":" + std::to_string(s.receiver_uncertainty_us) +
           ",\"capture_uncertainty_us\":" + std::to_string(s.capture_uncertainty_us) +
           ",\"location\":\"" + (s.location == GpsSettings::Location::Gps ? "gps" : "manual") +
           "\",\"position_maximum_age_s\":" + std::to_string(s.position_maximum_age_s) +
           ",\"automatic_rf_calibration\":" + flag(s.automatic_rf_calibration) +
           ",\"calibration_maximum_age_s\":" + std::to_string(s.calibration_maximum_age_s) +
           ",\"daylight\":\"" +
           (s.daylight == GpsSettings::Daylight::Day     ? "day"
            : s.daylight == GpsSettings::Daylight::Night ? "night"
                                                         : "always") +
           "\"}";
}
} // namespace wsprrypico::hardware
