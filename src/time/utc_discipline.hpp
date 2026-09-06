#pragma once

#include "wtp/job_service.hpp"

namespace wsprrypico::time {

struct DisciplineConfig {
    std::uint64_t synchronized_for_ns = 5'000'000'000ULL;
    std::uint64_t holdover_for_ns = 30'000'000'000ULL;
    std::uint64_t max_observation_age_ns = 2'000'000'000ULL;
    std::uint64_t max_uncertainty_ns = 1'000'000'000ULL;
    std::uint64_t oscillator_drift_ppb = 50'000;
};

class UtcDiscipline final : public wtp::Clock {
  public:
    using MonotonicNow = std::uint64_t (*)(void*);
    UtcDiscipline(MonotonicNow now, void* context, DisciplineConfig config = {});
    bool observe(std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                 std::uint64_t uncertainty_ns, wtp::LeapState leap,
                 std::optional<std::uint64_t> leap_transition_utc_ns = {});
    void invalidate();
    [[nodiscard]] wtp::ClockSnapshot snapshot() const override;

  private:
    MonotonicNow now_;
    void* context_;
    DisciplineConfig config_;
    bool config_valid_ = false;
    bool valid_ = false;
    std::uint64_t utc_ns_ = 0, monotonic_ns_ = 0, uncertainty_ns_ = 0;
    wtp::LeapState leap_ = wtp::LeapState::Unknown;
    std::optional<std::uint64_t> leap_transition_utc_ns_;
};

} // namespace wsprrypico::time
