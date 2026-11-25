#include "standalone/dry_run_engine.hpp"

#include "time/mapping.hpp"

#include <limits>

namespace wsprrypico::standalone {
bool DryRunEngine::schedule(const execution::Job& job, std::uint64_t start,
                            const execution::LocalStartConditions& conditions) {
    if (state_ != execution::EngineState::Idle || !conditions.clock || job.total_duration_ns == 0 ||
        job.total_duration_ns > std::numeric_limits<std::uint64_t>::max() - start)
        return false;
    const auto window = execution::start_window_ns(conditions.start_utc_ns);
    const auto limit = std::numeric_limits<std::uint64_t>::max();
    if (start > limit - window || conditions.start_utc_ns > limit - window ||
        job.total_duration_ns > limit - (start + window) ||
        job.total_duration_ns > limit - (conditions.start_utc_ns + window))
        return false;
    start_ = start;
    duration_ = job.total_duration_ns;
    conditions_ = conditions;
    state_ = execution::EngineState::Armed;
    return true;
}
execution::EngineReport DryRunEngine::poll(std::uint64_t now) {
    if (state_ == execution::EngineState::Armed && now >= start_) {
        const auto clock = conditions_.clock->snapshot();
        const auto elapsed = now - start_;
        const bool usable =
            clock.state == execution::ClockState::Synchronized ||
            (clock.state == execution::ClockState::Holdover && conditions_.maximum_holdover_age_ns &&
             clock.sync_age_ns <= conditions_.maximum_holdover_age_ns);
        std::uint64_t mapped{}, utc_elapsed{};
        const bool mapping_valid = time::project(clock, start_, mapped) &&
                                   time::elapsed_utc(elapsed, clock.rate_ppb, utc_elapsed, true);
        const auto error = mapped > conditions_.start_utc_ns ? mapped - conditions_.start_utc_ns
                                                             : conditions_.start_utc_ns - mapped;
        // Model the shared UTC-second policy; this is not physical launch evidence.
        state_ = mapping_valid && usable && clock.leap == execution::LeapState::Normal &&
                         clock.uncertainty_ns <= conditions_.maximum_uncertainty_ns &&
                         utc_elapsed < execution::start_window_ns(conditions_.start_utc_ns) &&
                         error <= clock.uncertainty_ns
                     ? execution::EngineState::Running
                     : execution::EngineState::Missed;
        if (state_ == execution::EngineState::Running)
            start_ = now;
    }
    if (state_ == execution::EngineState::Running && now >= start_ && now - start_ >= duration_)
        state_ = execution::EngineState::Complete;
    return {state_, false,
            (state_ == execution::EngineState::Running || state_ == execution::EngineState::Complete)
                ? std::optional<std::uint64_t>{start_}
                : std::nullopt};
}
} // namespace wsprrypico::standalone
