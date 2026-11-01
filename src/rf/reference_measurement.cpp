// SPDX-License-Identifier: MIT
#include "rf/reference_measurement.hpp"

#include <cmath>

namespace wsprrypico::rf {
bool valid_reference_policy(const ReferencePolicy& p) {
    if (p.use != ReferenceUse::MeasurementOnly && p.use != ReferenceUse::TrustedLocal)
        return false;
    if (p.minimum_window_ns < 1'000'000'000ULL || p.minimum_window_ns > p.maximum_window_ns ||
        p.maximum_window_ns > 60'000'000'000ULL || !p.maximum_age_ns ||
        p.maximum_age_ns > 300'000'000'000ULL || !p.maximum_measurement_uncertainty_ppb ||
        p.maximum_measurement_uncertainty_ppb > 100'000)
        return false;
    if (p.use == ReferenceUse::TrustedLocal)
        return p.trusted_uncertainty_ppb && *p.trusted_uncertainty_ppb > 0 &&
               *p.trusted_uncertainty_ppb <= 100'000;
    return !p.trusted_uncertainty_ppb;
}
ReferenceMeasurement measure_reference(const ReferenceWindow& w, long double nominal,
                                       std::uint64_t generation, const ReferencePolicy& policy) {
    ReferenceMeasurement m;
    const auto fail = [&](std::string_view error) {
        m.error = error;
        return m;
    };
    if (!valid_reference_policy(policy))
        return fail("invalid_policy");
    m.policy = policy;
    if (!std::isfinite(nominal) || nominal < 1'000 || nominal > 10'000'000)
        return fail("invalid_reference_frequency");
    if (!generation || generation != w.plan_generation)
        return fail("plan_changed");
    if (!w.coherent || w.end_raw_ns <= w.start_raw_ns)
        return fail("incoherent_capture");
    const auto duration = w.end_raw_ns - w.start_raw_ns;
    if (duration < policy.minimum_window_ns || duration > policy.maximum_window_ns)
        return fail("window_duration");
    if (!w.edges)
        return fail("missing_signal");
    // One edge of phase quantization plus the adapter's combined endpoint
    // bound. This is an uncertainty allowance, not a statistical confidence fit.
    if (w.endpoint_uncertainty_ns >= duration)
        return fail("capture_uncertainty");
    const auto hz = static_cast<long double>(w.edges) * 1'000'000'000 / duration;
    const auto ratio = hz / nominal;
    if (!std::isfinite(ratio) || ratio < 0.99L || ratio > 1.01L)
        return fail("implausible_ratio");
    const auto count_error = 1.L / w.edges;
    const auto timing_error = static_cast<long double>(w.endpoint_uncertainty_ns) /
                              (duration - w.endpoint_uncertainty_ns);
    // Bound the absolute ratio/rate error, not relative error divided by the
    // observed frequency. Add 1 ppb for numerical platform representations.
    m.uncertainty_ppb =
        ratio * (count_error + timing_error + count_error * timing_error) * 1'000'000'000 + 1;
    if (m.uncertainty_ppb > policy.maximum_measurement_uncertainty_ppb)
        return fail("measurement_uncertainty");
    m.observed_raw_ns = w.end_raw_ns;
    m.duration_ns = duration;
    m.plan_generation = generation;
    m.observed_hz = hz;
    m.ratio = ratio;
    if (policy.use == ReferenceUse::TrustedLocal) {
        // Frequency per raw second divided by expected frequency gives real
        // seconds per raw second. It must never become Si5351 RF correction.
        const auto rate = (ratio - 1) * 1'000'000'000;
        if (std::fabs(rate) > 100'000)
            return fail("local_rate_out_of_range");
        m.local_rate_ppb = static_cast<std::int32_t>(std::llround(rate));
        const auto reference_fraction = *policy.trusted_uncertainty_ppb / 1'000'000'000.L;
        m.uncertainty_ppb = (m.uncertainty_ppb + ratio * *policy.trusted_uncertainty_ppb) /
                            (1 - reference_fraction);
    }
    return m;
}
bool reference_fresh(const ReferenceMeasurement& m, const ReferencePolicy& policy,
                     std::uint64_t now, std::uint64_t generation) {
    return valid_reference_policy(policy) && m.valid() && m.policy == policy && generation &&
           m.plan_generation == generation && now >= m.observed_raw_ns &&
           now - m.observed_raw_ns <= policy.maximum_age_ns;
}
} // namespace wsprrypico::rf
