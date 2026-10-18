#pragma once

#include "wtp/job_service.hpp"

#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::time {
enum class ObservationSource { Sntp, Controller, Browser };

struct RateObservation {
    std::uint64_t utc_ns = 0, raw_ns = 0, uncertainty_ns = 0;
    std::int32_t rate_ppb = 0;
    std::uint32_t rate_uncertainty_ppb = 0;
    std::uint64_t generation = 0;
};

class ObservationSink {
  public:
    virtual ~ObservationSink() = default;
    virtual bool observe(ObservationSource source, std::uint64_t utc_ns,
                         std::uint64_t sampled_monotonic_ns, std::uint64_t uncertainty_ns,
                         wtp::LeapState leap,
                         std::optional<std::uint64_t> leap_transition_utc_ns = {},
                         std::string_view principal = {}) = 0;
    virtual bool observe_rate(std::uint64_t utc_ns, std::uint64_t sampled_monotonic_ns,
                              std::uint64_t uncertainty_ns, std::int32_t rate_ppb,
                              std::uint32_t rate_uncertainty_ppb, std::uint64_t generation) {
        (void)rate_ppb;
        (void)rate_uncertainty_ppb;
        (void)generation;
        return observe(ObservationSource::Sntp, utc_ns, sampled_monotonic_ns, uncertainty_ns,
                       wtp::LeapState::Normal);
    }
    // Import an independently maintained NTP model without refreshing its
    // original source age. Used by μChrony; no second NTP servo is applied.
    virtual bool observe_ntp_model(const RateObservation& source, const wtp::ClockSnapshot& model,
                                   std::uint32_t max_clock_error_ppb) {
        (void)source;
        (void)model;
        (void)max_clock_error_ppb;
        return false; // A sink must explicitly support age-preserving model import.
    }
    virtual void invalidate(ObservationSource source) = 0;
};
} // namespace wsprrypico::time
