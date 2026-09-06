#include "time/utc_discipline.hpp"

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
                    config.max_uncertainty_ns > 0 &&
                    config.oscillator_drift_ppb <= 1'000'000'000ULL) {}

bool UtcDiscipline::observe(std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                            std::uint64_t uncertainty_ns, wtp::LeapState leap,
                            std::optional<std::uint64_t> leap_transition_utc_ns) {
    if (!config_valid_)
        return false;
    const auto now = now_(context_);
    if (sampled_monotonic_ns > now || (valid_ && sampled_monotonic_ns <= monotonic_ns_) ||
        now - sampled_monotonic_ns > config_.max_observation_age_ns ||
        uncertainty_ns > config_.max_uncertainty_ns || leap == wtp::LeapState::Unknown ||
        (leap == wtp::LeapState::Normal && leap_transition_utc_ns) ||
        (leap != wtp::LeapState::Normal && !leap_transition_utc_ns))
        return false;
    std::uint64_t projected{};
    if (!add(utc_ns, now - sampled_monotonic_ns, projected))
        return false;
    valid_ = true;
    utc_ns_ = utc_ns;
    monotonic_ns_ = sampled_monotonic_ns;
    uncertainty_ns_ = uncertainty_ns;
    leap_ = leap;
    leap_transition_utc_ns_ = leap_transition_utc_ns;
    return true;
}

void UtcDiscipline::invalidate() {
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
                {}};
    const auto now = now_(context_);
    if (!valid_ || now < monotonic_ns_)
        return {wtp::ClockState::Unsynchronized,
                0,
                now,
                std::numeric_limits<std::uint64_t>::max(),
                std::numeric_limits<std::uint64_t>::max(),
                wtp::LeapState::Unknown,
                {}};
    const auto age = now - monotonic_ns_;
    std::uint64_t utc{}, grown{};
    const auto seconds = age / 1'000'000'000ULL;
    const auto remainder = age % 1'000'000'000ULL;
    if (config_.oscillator_drift_ppb &&
        seconds > std::numeric_limits<std::uint64_t>::max() / config_.oscillator_drift_ppb)
        return {
            wtp::ClockState::Unsynchronized, 0, now, std::numeric_limits<std::uint64_t>::max(), age,
            wtp::LeapState::Unknown,         {}};
    auto drift = seconds * config_.oscillator_drift_ppb;
    const auto fraction = remainder * config_.oscillator_drift_ppb;
    drift += fraction / 1'000'000'000ULL;
    if (fraction % 1'000'000'000ULL)
        ++drift;
    if (!add(utc_ns_, age, utc) || !add(uncertainty_ns_, drift, grown))
        return {
            wtp::ClockState::Unsynchronized, 0, now, std::numeric_limits<std::uint64_t>::max(), age,
            wtp::LeapState::Unknown,         {}};
    auto state = wtp::ClockState::Unsynchronized;
    if (age <= config_.synchronized_for_ns)
        state = wtp::ClockState::Synchronized;
    else if (age <= config_.holdover_for_ns)
        state = wtp::ClockState::Holdover;
    return {state, utc, now, grown, age, leap_, leap_transition_utc_ns_};
}

} // namespace wsprrypico::time
