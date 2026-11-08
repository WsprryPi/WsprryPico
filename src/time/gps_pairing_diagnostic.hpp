// SPDX-License-Identifier: MIT
#pragma once
#include "wtp/json.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::time::gps {
// Bounded bench snapshot of the existing internal status serializer. No wire
// resource, settings schema, receiver position, or production callback is added.
inline constexpr std::array<std::string_view, 18> pairing_diagnostic_errors{
    "",
    "capture_lost",
    "invalid_pps",
    "pps_discontinuity",
    "unqualified_pairing",
    "invalid_utc",
    "ambiguous_utc",
    "unpaired_utc",
    "invalid_pps_offset",
    "future_pps_epoch",
    "pairing_acquisition",
    "receiver_command_failed",
    "ambiguous_pps_edge",
    "pps_counter_unarmed",
    "capture_uncertainty_exceeded",
    "pps_counter_wrap",
    "pps_capture_clock_changed",
    "pps_capture_bracket_invalid"};
struct PairingDiagnostic {
    std::uint64_t raw_ns{}, candidate_utc_ns{}, candidate_raw_ns{}, candidate_pps_ns{},
        observation_raw_ns{};
    std::uint32_t observations{}, rejected_sentences{}, uart_errors{}, dropped{},
        capture_rejections{};
    std::uint16_t error{}, flags{};
};
static_assert(sizeof(PairingDiagnostic) == 64);
inline std::optional<PairingDiagnostic> pairing_diagnostic(std::string_view status,
                                                           std::uint64_t now) {
    namespace json = wtp::json;
    const auto doc = json::parse(status);
    if (!doc || !json::fields(*doc, {"serial_present",
                                     "pps_present",
                                     "time_valid",
                                     "position_valid",
                                     "satellites",
                                     "observation_raw_ns",
                                     "age_ns",
                                     "position",
                                     "candidate_utc_ns",
                                     "candidate_raw_ns",
                                     "candidate_pps_raw_ns",
                                     "observations",
                                     "rejected_sentences",
                                     "dropped",
                                     "uart_errors",
                                     "irq_latency_ns",
                                     "maximum_irq_latency_ns",
                                     "capture_error_bound_ns",
                                     "capture_rejections",
                                     "error"}))
        return {};
    PairingDiagnostic result{};
    result.raw_ns = now;
    const auto decimal = [&](const char* name, std::uint64_t& value) {
        const auto field = doc->get(name);
        return field && field->type() == '"' && json::decimal(*field, value);
    };
    const auto counter = [&](const char* name, std::uint32_t& value) {
        const auto field = doc->get(name);
        if (!field || field->type() < '0' || field->type() > '9')
            return false;
        std::uint32_t number = 0;
        for (const auto c : field->raw) {
            if (c < '0' || c > '9' || number > (UINT32_MAX - unsigned(c - '0')) / 10)
                return false;
            number = number * 10 + unsigned(c - '0');
        }
        value = number;
        return true;
    };
    if (!decimal("candidate_utc_ns", result.candidate_utc_ns) ||
        !decimal("candidate_raw_ns", result.candidate_raw_ns) ||
        !decimal("candidate_pps_raw_ns", result.candidate_pps_ns) ||
        !decimal("observation_raw_ns", result.observation_raw_ns) ||
        !counter("observations", result.observations) ||
        !counter("rejected_sentences", result.rejected_sentences) ||
        !counter("uart_errors", result.uart_errors) || !counter("dropped", result.dropped) ||
        !counter("capture_rejections", result.capture_rejections))
        return {};
    unsigned bit = 0;
    for (const char* name : {"serial_present", "pps_present", "time_valid", "position_valid"}) {
        const auto field = doc->get(name);
        if (!field || (field->type() != 't' && field->type() != 'f'))
            return {};
        result.flags |= unsigned(field->boolean()) << bit++;
    }
    const auto field = doc->get("error");
    if (!field || field->type() != '"')
        return {};
    const auto error = field->string();
    for (std::uint16_t i = 0; i < pairing_diagnostic_errors.size(); ++i)
        if (error == pairing_diagnostic_errors[i]) {
            result.error = i;
            return result;
        }
    return {};
}
} // namespace wsprrypico::time::gps
