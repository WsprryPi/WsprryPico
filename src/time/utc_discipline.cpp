#include "time/utc_discipline.hpp"

#include "time/mapping.hpp"

#include <limits>

namespace wsprrypico::time {
namespace {
bool add(std::uint64_t left, std::uint64_t right, std::uint64_t& result) {
    if (right > std::numeric_limits<std::uint64_t>::max() - left)
        return false;
    result = left + right;
    return true;
}
} // namespace

UtcDiscipline::UtcDiscipline(MonotonicNow now, void* context, DisciplineConfig config)
    : now_(now), context_(context), config_(config),
      config_valid_(now && config.synchronized_for_ns <= config.holdover_for_ns &&
                    config.holdover_for_ns <= 604'800'000'000'000ULL &&
                    config.max_observation_age_ns <= config.holdover_for_ns &&
                    config.max_rate_observation_age_ns <= config.holdover_for_ns &&
                    config.max_uncertainty_ns > 0 &&
                    config.oscillator_drift_ppb <= 1'000'000'000ULL) {}

bool UtcDiscipline::observe(std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                            std::uint64_t uncertainty_ns, wtp::LeapState leap,
                            std::optional<std::uint64_t> leap_transition_utc_ns) {
    return accept(utc_ns, sampled_monotonic_ns, uncertainty_ns, leap, leap_transition_utc_ns,
                  config_.max_observation_age_ns);
}
bool UtcDiscipline::accept(std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                           std::uint64_t uncertainty_ns, wtp::LeapState leap,
                           std::optional<std::uint64_t> leap_transition_utc_ns,
                           std::uint64_t maximum_age) {
    if (!config_valid_)
        return false;
    const auto now = now_(context_);
    if (sampled_monotonic_ns > now || (valid_ && sampled_monotonic_ns <= monotonic_ns_) ||
        now - sampled_monotonic_ns > maximum_age || uncertainty_ns > config_.max_uncertainty_ns ||
        leap == wtp::LeapState::Unknown ||
        (leap == wtp::LeapState::Normal && leap_transition_utc_ns) ||
        (leap != wtp::LeapState::Normal && !leap_transition_utc_ns))
        return false;
    std::uint64_t projected{};
    if (!add(utc_ns, now - sampled_monotonic_ns, projected))
        return false;
    rate_ppb_ = 0;
    rate_uncertainty_ppb_ = 0;
    ++generation_;
    valid_ = true;
    utc_ns_ = utc_ns;
    monotonic_ns_ = sampled_monotonic_ns;
    uncertainty_ns_ = uncertainty_ns;
    leap_ = leap;
    leap_transition_utc_ns_ = leap_transition_utc_ns;
    return true;
}

bool UtcDiscipline::observe_rate(std::uint64_t utc, std::uint64_t raw, std::uint64_t uncertainty,
                                 std::int32_t rate, std::uint32_t rate_uncertainty,
                                 std::uint64_t generation) {
    if (rate < -100'000 || rate > 100'000 || rate_uncertainty > 100'000)
        return false;
    if (!accept(utc, raw, uncertainty, wtp::LeapState::Normal, {},
                config_.max_rate_observation_age_ns ? config_.max_rate_observation_age_ns
                                                    : config_.max_observation_age_ns))
        return false;
    rate_ppb_ = rate;
    rate_uncertainty_ppb_ = rate_uncertainty;
    (void)generation; // Estimator generation is separate from this clock model generation.
    return true;
}
void UtcDiscipline::invalidate() {
    ++generation_;
    valid_ = false;
}

wtp::ClockSnapshot UtcDiscipline::snapshot() const {
    if (!config_valid_)
        return {wtp::ClockState::Unsynchronized,
                0,
                0,
                std::numeric_limits<std::uint64_t>::max(),
                std::numeric_limits<std::uint64_t>::max(),
                wtp::LeapState::Unknown,
                {},
                0,
                0,
                generation_};
    const auto now = now_(context_);
    if (!valid_ || now < monotonic_ns_)
        return {wtp::ClockState::Unsynchronized,
                0,
                now,
                std::numeric_limits<std::uint64_t>::max(),
                std::numeric_limits<std::uint64_t>::max(),
                wtp::LeapState::Unknown,
                {},
                0,
                0,
                generation_};
    const auto age = now - monotonic_ns_;
    std::uint64_t utc{}, grown{};
    std::uint64_t drift{};
    wtp::ClockSnapshot anchor;
    anchor.utc_now_ns = utc_ns_;
    anchor.monotonic_now_ns = monotonic_ns_;
    anchor.rate_ppb = rate_ppb_;
    if (!growth(age, config_.oscillator_drift_ppb + rate_uncertainty_ppb_, drift) ||
        !project(anchor, now, utc) || !add(uncertainty_ns_, drift + (rate_ppb_ != 0), grown))
        return {wtp::ClockState::Unsynchronized,
                0,
                now,
                std::numeric_limits<std::uint64_t>::max(),
                age,
                wtp::LeapState::Unknown,
                {},
                0,
                0,
                generation_};
    auto state = wtp::ClockState::Unsynchronized;
    if (age <= config_.synchronized_for_ns)
        state = wtp::ClockState::Synchronized;
    else if (age <= config_.holdover_for_ns)
        state = wtp::ClockState::Holdover;
    return {state,
            utc,
            now,
            grown,
            age,
            leap_,
            leap_transition_utc_ns_,
            rate_ppb_,
            rate_uncertainty_ppb_,
            generation_};
}

} // namespace wsprrypico::time
