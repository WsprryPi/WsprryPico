#pragma once

#include "wtp/job_service.hpp"

#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::time {
enum class ObservationSource { Sntp, Controller };

class ObservationSink {
  public:
    virtual ~ObservationSink() = default;
    virtual bool observe(ObservationSource source, std::uint64_t utc_ns,
                         std::uint64_t sampled_monotonic_ns, std::uint64_t uncertainty_ns,
                         wtp::LeapState leap,
                         std::optional<std::uint64_t> leap_transition_utc_ns = {},
                         std::string_view principal = {}) = 0;
    virtual void invalidate(ObservationSource source) = 0;
};
} // namespace wsprrypico::time
