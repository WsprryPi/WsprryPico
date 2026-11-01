// SPDX-License-Identifier: MIT
#pragma once
#include "logging/logger.hpp"
#include "wtp/job_service.hpp"

namespace wsprrypico::logging {
// Observe core-0 clock state, rather than individual time-source updates. A
// usable clock can alternate between synchronized and holdover routinely.
class ClockStateLogger {
  public:
    void observe(Logger& logger, const wtp::ClockSnapshot& clock, std::uint64_t monotonic_ns) {
        if (clock.state == previous_)
            return;
        const bool unavailable = clock.state == wtp::ClockState::Unsynchronized;
        const auto severity = unavailable                                    ? 4U
                              : previous_ == wtp::ClockState::Unsynchronized ? 6U
                                                                             : 7U;
        const auto message = unavailable                                ? "UTC unavailable"
                             : clock.state == wtp::ClockState::Holdover ? "UTC holdover"
                                                                        : "UTC synchronized";
        logger.event(severity, "CLOCK_STATE", message, monotonic_ns,
                     unavailable ? 0 : clock.utc_now_ns);
        previous_ = clock.state;
    }

  private:
    wtp::ClockState previous_ = wtp::ClockState::Unsynchronized;
};
} // namespace wsprrypico::logging
