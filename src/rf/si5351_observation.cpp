// SPDX-License-Identifier: MIT
#include "rf/si5351_observation.hpp"

#include "wtp/json.hpp"

#include <cmath>

namespace wsprrypico::rf::si5351 {
namespace {
std::string state(ClockOutputState value) {
    switch (value) {
    case ClockOutputState::RegisterDisabled:
        return "\"register_disabled\"";
    case ClockOutputState::RegisterEnabled:
        return "\"register_enabled\"";
    default:
        return "\"unknown\"";
    }
}
} // namespace
std::string observation_json(const Engine::Observation& o,
                             const std::optional<ReferenceMeasurement>& measurement,
                             std::string_view error, std::uint64_t now,
                             std::string_view clock_reference_state,
                             std::uint64_t clock_reference_observed_raw_ns) {
    const auto decimal = [](auto value) { return wtp::json::quote(std::to_string(value)); };
    std::string measured = "null";
    const bool fresh = measurement && reference_fresh(*measurement, measurement->policy, now,
                                                      measurement->plan_generation);
    if (fresh) {
        const auto& m = *measurement;
        measured =
            "{\"start_raw_ns\":" + decimal(m.start_raw_ns) +
            ",\"observed_raw_ns\":" + decimal(m.observed_raw_ns) +
            ",\"duration_ns\":" + decimal(m.duration_ns) + ",\"edges\":" + decimal(m.edges) +
            ",\"endpoint_uncertainty_ns\":" + decimal(m.endpoint_uncertainty_ns) +
            ",\"plan_generation\":" + decimal(m.plan_generation) +
            ",\"observed_millihz\":" + decimal(std::llround(m.observed_hz * 1000)) +
            ",\"ratio_error_ppb\":" + decimal(std::llround((m.ratio - 1) * 1'000'000'000)) +
            ",\"uncertainty_ppb\":" +
            std::to_string(static_cast<std::uint64_t>(std::ceil(m.uncertainty_ppb))) +
            ",\"local_rate_ppb\":" +
            (m.local_rate_ppb ? std::to_string(*m.local_rate_ppb) : "null") +
            ",\"reference_use\":" +
            wtp::json::quote(m.policy.use == ReferenceUse::TrustedLocal ? "trusted_local"
                                                                        : "measurement_only") +
            ",\"age_ns\":" + decimal(now - m.observed_raw_ns) + "}";
    }
    return "{\"transmit\":" + state(o.transmit) + ",\"reference_output\":" + state(o.reference) +
           ",\"communication\":" +
           wtp::json::quote(o.transmit == ClockOutputState::Unknown ||
                                    o.reference == ClockOutputState::Unknown
                                ? "unknown"
                                : "register_control_verified") +
           ",\"engineering_enabled\":" + (o.engineering_allowed ? "true" : "false") +
           ",\"inhibited\":" + (o.inhibited ? "true" : "false") + ",\"epoch\":" + decimal(o.epoch) +
           ",\"enable_command_completed_ns\":" + decimal(o.enable_command_completed_ns) +
           ",\"disable_command_completed_ns\":" + decimal(o.disable_command_completed_ns) +
           ",\"reference_measurement\":" + measured +
           ",\"clock_reference_state\":" + wtp::json::quote(clock_reference_state) +
           ",\"clock_reference_observed_raw_ns\":" + decimal(clock_reference_observed_raw_ns) +
           ",\"measurement_error\":" +
           (measurement && !fresh ? wtp::json::quote("stale_or_invalid_measurement")
            : error.empty()       ? "null"
                                  : wtp::json::quote(error)) +
           "}";
}
} // namespace wsprrypico::rf::si5351
