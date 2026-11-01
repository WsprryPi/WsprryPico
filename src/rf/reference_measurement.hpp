// SPDX-License-Identifier: MIT
#pragma once

#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::rf {
enum class ReferenceUse { MeasurementOnly, TrustedLocal };
// Capture endpoints must use the raw monotonic timer, never disciplined UTC.
// The adapter supplies a coherent extended edge count and an explicit bound
// on endpoint error. An ambiguous rollover invalidates the whole window.
struct ReferenceWindow {
    std::uint64_t start_raw_ns = 0, end_raw_ns = 0, edges = 0;
    std::uint64_t endpoint_uncertainty_ns = 0, plan_generation = 0;
    bool coherent = false;
};
struct ReferencePolicy {
    bool operator==(const ReferencePolicy&) const = default;
    ReferenceUse use = ReferenceUse::MeasurementOnly;
    // Explicit operator declaration required for trusted use; no TCXO default.
    std::optional<std::uint32_t> trusted_uncertainty_ppb;
    std::uint64_t maximum_age_ns = 30'000'000'000ULL;
    std::uint64_t minimum_window_ns = 10'000'000'000ULL;
    std::uint64_t maximum_window_ns = 60'000'000'000ULL;
    std::uint32_t maximum_measurement_uncertainty_ppb = 1'000;
};
struct ReferenceMeasurement {
    std::uint64_t observed_raw_ns = 0, duration_ns = 0, plan_generation = 0;
    long double observed_hz = 0, ratio = 0, uncertainty_ppb = 0;
    // UTC seconds per raw second minus one, ONLY if the independently trusted
    // reference meets the configured allowance. It supplies no UTC epoch.
    std::optional<std::int32_t> local_rate_ppb;
    ReferencePolicy policy;
    std::string_view error;
    bool valid() const {
        return error.empty() && duration_ns && plan_generation;
    }
};
bool valid_reference_policy(const ReferencePolicy&);
ReferenceMeasurement measure_reference(const ReferenceWindow&, long double achieved_nominal_hz,
                                       std::uint64_t active_plan_generation,
                                       const ReferencePolicy&);
bool reference_fresh(const ReferenceMeasurement&, const ReferencePolicy&, std::uint64_t now_raw_ns,
                     std::uint64_t active_plan_generation);
} // namespace wsprrypico::rf
