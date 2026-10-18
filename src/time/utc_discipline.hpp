#pragma once

#include "time/observation.hpp"
#include "wtp/job_service.hpp"

namespace wsprrypico::time {

struct DisciplineConfig {
    std::uint64_t synchronized_for_ns = 5'000'000'000ULL;
    std::uint64_t holdover_for_ns = 30'000'000'000ULL;
    std::uint64_t max_observation_age_ns = 2'000'000'000ULL;
    std::uint64_t max_uncertainty_ns = 1'000'000'000ULL;
    std::uint64_t oscillator_drift_ppb = 50'000;
    std::uint64_t max_rate_observation_age_ns = 0; // Zero inherits the ordinary observation limit.
};

class UtcDiscipline final : public wtp::Clock, public ObservationSink {
  public:
    using MonotonicNow = std::uint64_t (*)(void*);
    UtcDiscipline(MonotonicNow now, void* context, DisciplineConfig config = {});
    bool observe(std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                 std::uint64_t uncertainty_ns, wtp::LeapState leap,
                 std::optional<std::uint64_t> leap_transition_utc_ns = {});
    bool observe(ObservationSource, std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                 std::uint64_t uncertainty_ns, wtp::LeapState leap,
                 std::optional<std::uint64_t> leap_transition_utc_ns, std::string_view) override {
        return observe(utc_ns, sampled_monotonic_ns, uncertainty_ns, leap, leap_transition_utc_ns);
    }
    bool observe_rate(std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                      std::uint64_t uncertainty_ns, std::int32_t rate_ppb,
                      std::uint32_t rate_uncertainty_ppb, std::uint64_t generation) override;
    bool observe_ntp_model(const RateObservation& source, const wtp::ClockSnapshot& model,
                           std::uint32_t max_clock_error_ppb) override;
    void invalidate();
    void invalidate(ObservationSource) override {
        invalidate();
    }
    [[nodiscard]] wtp::ClockSnapshot snapshot() const override;

  private:
    bool accept(std::uint64_t utc, std::uint64_t raw, std::uint64_t uncertainty,
                wtp::LeapState leap, std::optional<std::uint64_t> transition,
                std::uint64_t maximum_age);
    MonotonicNow now_;
    void* context_;
    DisciplineConfig config_;
    bool config_valid_ = false;
    bool valid_ = false;
    std::uint64_t utc_ns_ = 0, monotonic_ns_ = 0, uncertainty_ns_ = 0;
    std::int32_t rate_ppb_ = 0;
    std::uint32_t rate_uncertainty_ppb_ = 0;
    std::uint64_t generation_ = 0;
    wtp::LeapState leap_ = wtp::LeapState::Unknown;
    std::optional<std::uint64_t> leap_transition_utc_ns_;
    bool imported_ntp_ = false;
    std::uint64_t source_ns_ = 0, imported_generation_ = 0, rate_until_ns_ = UINT64_MAX;
    std::int32_t subsequent_rate_ppb_ = 0;
    std::uint32_t imported_growth_ppb_ = 1000;
};

} // namespace wsprrypico::time
