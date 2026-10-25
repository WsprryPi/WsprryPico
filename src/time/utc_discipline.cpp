#include "time/utc_discipline.hpp"

#include "time/mapping.hpp"

#include <algorithm>
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
                    config.non_ntp_holdover_for_ns <= 604'800'000'000'000ULL &&
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
    imported_ntp_ = false;
    observation_source_ = ObservationSource::Sntp;
    rate_until_ns_ = UINT64_MAX;
    subsequent_rate_ppb_ = 0;
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
    if (rate < -utc_max_rate_ppb || rate > utc_max_rate_ppb ||
        rate_uncertainty > utc_max_rate_uncertainty_ppb)
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
bool UtcDiscipline::observe_ntp_model(const RateObservation& source,
                                      const wtp::ClockSnapshot& model,
                                      std::uint32_t max_clock_error_ppb) {
    if (!config_valid_ || !consistent_import(source, model) || !model.utc_now_ns ||
        model.sync_age_ns > model.monotonic_now_ns || model.monotonic_now_ns > now_(context_) ||
        now_(context_) - model.monotonic_now_ns > config_.max_observation_age_ns ||
        model.uncertainty_ns > 3'000'000'000ULL || model.rate_ppb < -utc_max_rate_ppb ||
        model.rate_ppb > utc_max_rate_ppb || model.subsequent_rate_ppb < -utc_max_rate_ppb ||
        model.subsequent_rate_ppb > utc_max_rate_ppb ||
        model.rate_uncertainty_ppb > utc_max_rate_uncertainty_ppb ||
        max_clock_error_ppb > utc_max_rate_uncertainty_ppb ||
        model.state == wtp::ClockState::Unsynchronized || model.leap == wtp::LeapState::Unknown ||
        (model.leap != wtp::LeapState::Normal && !model.leap_transition_utc_ns) ||
        (model.leap == wtp::LeapState::Normal && model.leap_transition_utc_ns) ||
        model.rate_until_monotonic_ns < model.monotonic_now_ns || !model.model_generation ||
        source.generation != model.model_generation ||
        source.raw_ns != model.monotonic_now_ns - model.sync_age_ns ||
        (imported_ntp_ && model.model_generation < imported_generation_) ||
        (imported_ntp_ && model.model_generation == imported_generation_ &&
         model.monotonic_now_ns - model.sync_age_ns != source_ns_))
        return false;
    if (!imported_ntp_ || imported_generation_ != model.model_generation)
        ++generation_;
    imported_generation_ = model.model_generation;
    imported_ntp_ = valid_ = true;
    observation_source_ = ObservationSource::Sntp;
    utc_ns_ = model.utc_now_ns;
    monotonic_ns_ = model.monotonic_now_ns;
    source_ns_ = model.monotonic_now_ns - model.sync_age_ns;
    uncertainty_ns_ = model.uncertainty_ns;
    rate_ppb_ = model.rate_ppb;
    rate_uncertainty_ppb_ = model.rate_uncertainty_ppb;
    imported_growth_ppb_ = max_clock_error_ppb;
    rate_until_ns_ = model.rate_until_monotonic_ns;
    subsequent_rate_ppb_ = model.subsequent_rate_ppb;
    leap_ = model.leap;
    leap_transition_utc_ns_ = model.leap_transition_utc_ns;
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
    const auto age = now - (imported_ntp_ ? source_ns_ : monotonic_ns_);
    const auto model_age = now - monotonic_ns_;
    std::uint64_t utc{}, grown{};
    std::uint64_t drift{};
    wtp::ClockSnapshot anchor;
    anchor.utc_now_ns = utc_ns_;
    anchor.monotonic_now_ns = monotonic_ns_;
    anchor.rate_ppb = rate_ppb_;
    anchor.rate_until_monotonic_ns = rate_until_ns_;
    anchor.subsequent_rate_ppb = subsequent_rate_ppb_;
    const auto growth_ppb = imported_ntp_ ? std::max(imported_growth_ppb_, rate_uncertainty_ppb_)
                                          : config_.oscillator_drift_ppb + rate_uncertainty_ppb_;
    if (!growth(model_age, growth_ppb, drift) || !project(anchor, now, utc) ||
        !add(uncertainty_ns_, drift + (rate_ppb_ != 0), grown))
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
    const auto maximum_age =
        observation_source_ != ObservationSource::Sntp && config_.non_ntp_holdover_for_ns
            ? config_.non_ntp_holdover_for_ns
            : config_.holdover_for_ns;
    if (age <= std::min(config_.synchronized_for_ns, maximum_age))
        state = wtp::ClockState::Synchronized;
    else if (age <= maximum_age)
        state = wtp::ClockState::Holdover;
    auto result = wtp::ClockSnapshot{state,
                                     utc,
                                     now,
                                     grown,
                                     age,
                                     leap_,
                                     leap_transition_utc_ns_,
                                     now >= rate_until_ns_ ? subsequent_rate_ppb_ : rate_ppb_,
                                     rate_uncertainty_ppb_,
                                     generation_};
    result.rate_until_monotonic_ns = now >= rate_until_ns_ ? UINT64_MAX : rate_until_ns_;
    result.subsequent_rate_ppb = subsequent_rate_ppb_;
    return result;
}

} // namespace wsprrypico::time
