// SPDX-License-Identifier: MIT
#include "wtp/arm_admission.hpp"

#include "time/mapping.hpp"

namespace wsprrypico::wtp {
namespace {
constexpr std::uint64_t kLeapExclusionNs = 1'000'000'000ULL;
std::uint64_t saturating_add(std::uint64_t a, std::uint64_t b) {
    return b > UINT64_MAX - a ? UINT64_MAX : a + b;
}
} // namespace
ErrorCode assess_arm(std::uint64_t duration_ns, const ArmBody& arm, const ClockSnapshot& now,
                     const ServiceConfig& config, std::uint64_t resolution,
                     std::uint64_t& start_monotonic_ns) {
    if (now.state == ClockState::Unsynchronized) {
        return ErrorCode::ClockUnsynchronized;
    }
    if (now.state == ClockState::Holdover &&
        (config.maximum_holdover_age_ns == 0 || now.sync_age_ns > config.maximum_holdover_age_ns)) {
        return ErrorCode::ClockUnsynchronized;
    }
    if (now.uncertainty_ns > arm.max_start_uncertainty_ns ||
        now.uncertainty_ns > config.maximum_arm_uncertainty_ns) {
        return ErrorCode::ClockUncertain;
    }
    const bool pending_leap =
        now.leap == LeapState::InsertPending || now.leap == LeapState::DeletePending;
    if (now.leap == LeapState::Unknown || pending_leap != now.leap_transition_utc_ns.has_value()) {
        return ErrorCode::LeapUnsafe;
    }
    if (arm.start_utc_ns < now.utc_now_ns ||
        arm.start_utc_ns - now.utc_now_ns < config.minimum_arm_lead_ns) {
        return ErrorCode::ArmTooLate;
    }
    const auto ahead = arm.start_utc_ns - now.utc_now_ns;
    if (ahead > config.maximum_arm_ahead_ns) {
        return ErrorCode::ArmTooFar;
    }
    if (ahead > std::numeric_limits<std::uint64_t>::max() - now.monotonic_now_ns ||
        duration_ns > std::numeric_limits<std::uint64_t>::max() - arm.start_utc_ns) {
        return ErrorCode::InvalidMessage;
    }
    if (resolution == 0)
        return ErrorCode::DeviceFault;
    std::uint64_t nominal_start{};
    if (!time::inverse(now, arm.start_utc_ns, nominal_start))
        return ErrorCode::InvalidMessage;
    const auto adjustment = (resolution - nominal_start % resolution) % resolution;
    const auto window = start_window_ns(arm.start_utc_ns);
    const auto limit = std::numeric_limits<std::uint64_t>::max();
    if (nominal_start > limit - window || arm.start_utc_ns > limit - window ||
        adjustment >= window || duration_ns > limit - (nominal_start + window) ||
        duration_ns > limit - (arm.start_utc_ns + window))
        return ErrorCode::InvalidMessage;
    const auto budget = std::min(arm.max_start_uncertainty_ns, config.maximum_arm_uncertainty_ns);
    std::uint64_t rounding_utc{}, future_growth{};
    if (!time::elapsed_utc(adjustment + (now.rate_ppb != 0), now.rate_ppb, rounding_utc, true) ||
        !time::growth(nominal_start - now.monotonic_now_ns, now.rate_uncertainty_ppb,
                      future_growth) ||
        future_growth > budget - now.uncertainty_ns ||
        rounding_utc > budget - now.uncertainty_ns - future_growth)
        return ErrorCode::ClockUncertain;
    // WTP reports the exact mapping. Round the hardware target upward so timer
    // quantization never requests an early launch. Clock uncertainty remains
    // independent of permitted scheduling delay within the requested UTC second.
    start_monotonic_ns = nominal_start;
    if (duration_ns > std::numeric_limits<std::uint64_t>::max() - start_monotonic_ns)
        return ErrorCode::InvalidMessage;
    std::uint64_t horizon_duration{};
    const auto horizon_latest = arm.start_utc_ns + window - 1;
    if (!time::duration_utc_bound(duration_ns, now, horizon_duration) ||
        horizon_latest >= now.valid_until_utc_ns ||
        horizon_duration >= now.valid_until_utc_ns - horizon_latest)
        return ErrorCode::LeapUnsafe;
    if (now.leap_transition_utc_ns) {
        const auto transition = *now.leap_transition_utc_ns;
        const auto exclusion_start =
            transition > kLeapExclusionNs ? transition - kLeapExclusionNs : 0;
        const auto exclusion_end = saturating_add(transition, kLeapExclusionNs);
        std::uint64_t duration{};
        const auto latest = arm.start_utc_ns + window - 1;
        if (!time::duration_utc_bound(duration_ns, now, duration) || duration > limit - latest)
            return ErrorCode::InvalidMessage;
        const auto job_end = latest + duration;
        if (arm.start_utc_ns <= exclusion_end && job_end >= exclusion_start) {
            return ErrorCode::LeapUnsafe;
        }
    }
    return ErrorCode::None;
}

} // namespace wsprrypico::wtp
