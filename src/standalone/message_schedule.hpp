// SPDX-License-Identifier: MIT
#pragma once
#include "encoding/message_wire.hpp"
#include "time/sntp.hpp"

#include <limits>
namespace wsprrypico::standalone {
inline constexpr std::uint64_t message_preparation_ns = 2'000'000'000ULL;
struct MessageSchedule {
    bool enabled = false;
    std::uint64_t first_start_utc_ns = 0, expires_utc_s = 0;
    std::uint32_t period_s = 0;
    encoding::MorseMessage message;
};
inline std::optional<MessageSchedule> parse_message_schedule(wtp::json::Value root) {
    using namespace wtp::json;
    if (!fields(root, {"enabled", "first_start_utc_ns", "period_s", "expires_utc_s", "message"}))
        return {};
    MessageSchedule s;
    const auto enabled = *root.get("enabled"), period = *root.get("period_s"),
               expiry = *root.get("expires_utc_s");
    const auto number = [](Value v) {
        return !v.raw.empty() && v.raw.size() <= 10 &&
               std::all_of(v.raw.begin(), v.raw.end(), [](char c) { return c >= '0' && c <= '9'; });
    };
    if ((enabled.raw != "true" && enabled.raw != "false") || !number(period) || !number(expiry) ||
        !decimal(*root.get("first_start_utc_ns"), s.first_start_utc_ns, true))
        return {};
    if (period.integer() < 60 || period.integer() > 86400 || period.integer() % 60 ||
        expiry.integer() < 0)
        return {};
    s.enabled = enabled.boolean();
    s.period_s = static_cast<std::uint32_t>(period.integer());
    s.expires_utc_s = static_cast<std::uint64_t>(expiry.integer());
    if (s.first_start_utc_ns < time::sntp_min_utc_ns ||
        s.first_start_utc_ns >= time::sntp_max_utc_ns ||
        (s.expires_utc_s && (s.expires_utc_s * 1'000'000'000ULL <= s.first_start_utc_ns ||
                             s.expires_utc_s > time::sntp_max_utc_ns / 1'000'000'000ULL)))
        return {};
    auto message = encoding::decode_message(*root.get("message"), false);
    if (!message ||
        !std::all_of(
            message->text.begin(), message->text.end(),
            [](char c) {
                return std::string_view(
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 /?.,-+=")
                           .find(c) != std::string_view::npos;
            }) ||
        (message->mode == "dfcw" && message->mark_frequency_nhz >= message->space_frequency_nhz))
        return {};
    auto measured = encoding::measure_message(*message);
    if (!measured.error.empty() || measured.calculated_duration_ns + message_preparation_ns >
                                       std::uint64_t{s.period_s} * 1'000'000'000ULL)
        return {};
    if (s.expires_utc_s &&
        measured.calculated_duration_ns > s.expires_utc_s * 1'000'000'000ULL - s.first_start_utc_ns)
        return {};
    s.message = std::move(*message);
    return s;
}
inline std::string serialize_message_schedule(const MessageSchedule& s) {
    return "{\"enabled\":" + std::string(s.enabled ? "true" : "false") +
           ",\"first_start_utc_ns\":" + wtp::json::quote(std::to_string(s.first_start_utc_ns)) +
           ",\"period_s\":" + std::to_string(s.period_s) +
           ",\"expires_utc_s\":" + std::to_string(s.expires_utc_s) +
           ",\"message\":" + encoding::serialize_message(s.message) + "}";
}
// UTC period/phase ceiling and consumed-start rule adapted from WsprryPi
// devel 5bc24e893646, src/wtp_integration/fleet_schedule.cpp (MIT).
inline std::optional<std::uint64_t> next_message_slot(const MessageSchedule& s,
                                                      std::uint64_t earliest, std::uint64_t last) {
    constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
    const auto period = std::uint64_t{s.period_s} * 1'000'000'000ULL;
    if (!period || last == maximum)
        return {};
    earliest = std::max(earliest, last + 1);
    auto next = s.first_start_utc_ns;
    if (earliest > next) {
        const auto delta = earliest - next;
        const auto steps = delta / period + (delta % period != 0);
        if (steps > (maximum - next) / period)
            return {};
        next += steps * period;
    }
    if (next >= time::sntp_max_utc_ns)
        return {};
    return next;
}
} // namespace wsprrypico::standalone
