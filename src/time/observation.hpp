#pragma once

#include "wtp/job_service.hpp"

#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::time {
enum class ObservationSource { Sntp, Controller, Browser, Gps };

struct RateObservation {
    std::uint64_t utc_ns = 0, raw_ns = 0, uncertainty_ns = 0;
    std::int32_t rate_ppb = 0;
    std::uint32_t rate_uncertainty_ppb = 0;
    std::uint64_t generation = 0;
};

struct LocalFrequencyReference {
    std::uint64_t sampled_raw_ns = 0, valid_until_raw_ns = 0, generation = 0;
    std::int32_t rate_ppb = 0;
    std::uint32_t uncertainty_ppb = 0;
    bool operator==(const LocalFrequencyReference&) const = default;
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
    virtual bool observe_reference_model(const RateObservation&, const wtp::ClockSnapshot&,
                                         std::uint32_t) {
        return false;
    }
    virtual bool observe_frequency_reference(const LocalFrequencyReference&, std::uint64_t) {
        return false;
    }
    virtual void retire_frequency_reference(std::uint64_t, bool) {}
    // Empty means that no browser epoch owns this rate-reference status.
    virtual std::string_view browser_frequency_reference_status(std::uint64_t) const {
        return {};
    }
    virtual void invalidate(ObservationSource source) = 0;
    // Independent trusted frequency disagreement cannot be bypassed by
    // choosing another epoch source. It supplies no replacement UTC sample.
    virtual void frequency_reference_conflict(bool conflict) {
        if (conflict)
            invalidate(ObservationSource::Sntp);
    }
};
} // namespace wsprrypico::time
