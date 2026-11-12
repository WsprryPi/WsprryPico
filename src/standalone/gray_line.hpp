// SPDX-License-Identifier: MIT
#pragma once
#include "wtp/json.hpp"

#include <charconv>
#include <optional>

namespace wsprrypico::standalone {
struct GrayLinePeriod {
    bool enabled = false;
    std::int32_t lower_mdeg = -6000, upper_mdeg = 6000;
    std::optional<std::uint32_t> wspr_dial_frequency_hz;
    std::optional<std::uint64_t> message_frequency_nhz;
    bool qualifies(double elevation_degrees) const {
        const double value = elevation_degrees * 1000;
        return enabled && value >= lower_mdeg && value < upper_mdeg;
    }
    bool operator==(const GrayLinePeriod&) const = default;
};
struct GrayLine {
    bool gps = false;
    GrayLinePeriod morning, evening;
    bool enabled() const {
        return morning.enabled || evening.enabled;
    }
    bool operator==(const GrayLine&) const = default;
};
inline std::optional<GrayLine> parse_gray_line(wtp::json::Value value) {
    using namespace wtp::json;
    if (!fields(value, {"location", "morning", "evening"}) ||
        (value.get("location")->raw != "\"manual\"" && value.get("location")->raw != "\"gps\""))
        return {};
    GrayLine result;
    result.gps = value.get("location")->raw == "\"gps\"";
    const auto signed_number = [](Value v, std::int32_t& out) {
        const auto text = std::string(v.raw);
        const auto parsed = std::from_chars(text.data(), text.data() + text.size(), out);
        return parsed.ec == std::errc{} && parsed.ptr == text.data() + text.size() &&
               std::to_string(out) == text;
    };
    for (const auto name : {"morning", "evening"}) {
        const auto v = *value.get(name);
        auto& p = name == std::string_view("morning") ? result.morning : result.evening;
        if (!fields(v, {"enabled", "lower_mdeg", "upper_mdeg", "wspr_dial_frequency_hz",
                        "message_frequency_nhz"}) ||
            (v.get("enabled")->raw != "true" && v.get("enabled")->raw != "false") ||
            !signed_number(*v.get("lower_mdeg"), p.lower_mdeg) ||
            !signed_number(*v.get("upper_mdeg"), p.upper_mdeg) || p.lower_mdeg < -90000 ||
            p.upper_mdeg > 90000 || p.lower_mdeg >= p.upper_mdeg)
            return {};
        p.enabled = v.get("enabled")->boolean();
        if (v.get("wspr_dial_frequency_hz")->raw != "null") {
            std::int32_t frequency = 0;
            if (!signed_number(*v.get("wspr_dial_frequency_hz"), frequency) || frequency < 6503 ||
                frequency > 159998496)
                return {};
            p.wspr_dial_frequency_hz = std::uint32_t(frequency);
        }
        if (v.get("message_frequency_nhz")->raw != "null") {
            std::uint64_t frequency = 0;
            if (!decimal(*v.get("message_frequency_nhz"), frequency, true) || !frequency)
                return {};
            p.message_frequency_nhz = frequency;
        }
    }
    return result;
}
inline std::string serialize_gray_line(const GrayLine& g) {
    const auto period = [](const GrayLinePeriod& p) {
        return "{\"enabled\":" + std::string(p.enabled ? "true" : "false") +
               ",\"lower_mdeg\":" + std::to_string(p.lower_mdeg) +
               ",\"upper_mdeg\":" + std::to_string(p.upper_mdeg) + ",\"wspr_dial_frequency_hz\":" +
               (p.wspr_dial_frequency_hz ? std::to_string(*p.wspr_dial_frequency_hz) : "null") +
               ",\"message_frequency_nhz\":" +
               (p.message_frequency_nhz ? wtp::json::quote(std::to_string(*p.message_frequency_nhz))
                                        : "null") +
               "}";
    };
    return "{\"location\":" + wtp::json::quote(g.gps ? "gps" : "manual") +
           ",\"morning\":" + period(g.morning) + ",\"evening\":" + period(g.evening) + "}";
}
} // namespace wsprrypico::standalone
