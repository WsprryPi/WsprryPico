#include "standalone/dry_run_engine.hpp"

#include <limits>

namespace wsprrypico::standalone {
bool DryRunEngine::schedule(const wtp::Job& job, std::uint64_t start,
                            const wtp::LocalStartConditions& conditions) {
    if (state_ != wtp::EngineState::Idle || !conditions.clock || job.total_duration_ns == 0 ||
        job.total_duration_ns > std::numeric_limits<std::uint64_t>::max() - start)
        return false;
    const auto window = wtp::start_window_ns(conditions.start_utc_ns);
    const auto limit = std::numeric_limits<std::uint64_t>::max();
    if (start > limit - window || conditions.start_utc_ns > limit - window ||
        job.total_duration_ns > limit - (start + window) ||
        job.total_duration_ns > limit - (conditions.start_utc_ns + window))
        return false;
    start_ = start;
    duration_ = job.total_duration_ns;
    conditions_ = conditions;
    state_ = wtp::EngineState::Armed;
    return true;
}
wtp::EngineReport DryRunEngine::poll(std::uint64_t now) {
    if (state_ == wtp::EngineState::Armed && now >= start_) {
        const auto clock = conditions_.clock->snapshot();
        const auto elapsed = now - start_;
        const bool usable =
            clock.state == wtp::ClockState::Synchronized ||
            (clock.state == wtp::ClockState::Holdover && conditions_.maximum_holdover_age_ns &&
             clock.sync_age_ns <= conditions_.maximum_holdover_age_ns);
        const auto mapped = clock.utc_now_ns >= elapsed ? clock.utc_now_ns - elapsed : 0;
        const auto error = mapped > conditions_.start_utc_ns ? mapped - conditions_.start_utc_ns
                                                             : conditions_.start_utc_ns - mapped;
        // Model the shared UTC-second policy; this is not physical launch evidence.
        state_ = usable && clock.leap == wtp::LeapState::Normal &&
                         clock.uncertainty_ns <= conditions_.maximum_uncertainty_ns &&
                         elapsed < wtp::start_window_ns(conditions_.start_utc_ns) &&
                         error <= clock.uncertainty_ns
                     ? wtp::EngineState::Running
                     : wtp::EngineState::Missed;
        if (state_ == wtp::EngineState::Running)
            start_ = now;
    }
    if (state_ == wtp::EngineState::Running && now >= start_ && now - start_ >= duration_)
        state_ = wtp::EngineState::Complete;
    return {state_, false,
            (state_ == wtp::EngineState::Running || state_ == wtp::EngineState::Complete)
                ? std::optional<std::uint64_t>{start_}
                : std::nullopt};
}
} // namespace wsprrypico::standalone
