#pragma once

#include "rf/wtp_profile.hpp"
#include "standalone/config.hpp"
#include "time/sntp.hpp"

#include <algorithm>

namespace wsprrypico::standalone {
inline time::DisciplineConfig clock_profile(unsigned ntp_timeout_s = default_ntp_timeout_s) {
    time::DisciplineConfig config;
    config.unlimited_ntp_holdover = ntp_timeout_s == 0;
    config.holdover_for_ns =
        std::uint64_t{ntp_timeout_s ? ntp_timeout_s : default_ntp_timeout_s} * 1'000'000'000ULL;
    config.synchronized_for_ns = std::min<std::uint64_t>(90'000'000'000ULL, config.holdover_for_ns);
    config.max_rate_observation_age_ns = config.synchronized_for_ns;
    config.non_ntp_holdover_for_ns = 90'000'000'000ULL;
    return config;
}

inline wtp::ServiceConfig wtp_profile(bool physical_rf,
                                      unsigned ntp_timeout_s = default_ntp_timeout_s) {
    auto config = rf::wtp_profile(physical_rf ? "pio-dma-gp2" : "inhibited-standalone-simulator");
    config.maximum_arm_uncertainty_ns =
        ntp_timeout_s ? time::standalone_max_uncertainty_ns : UINT64_MAX;
    config.maximum_holdover_age_ns =
        ntp_timeout_s ? std::uint64_t{ntp_timeout_s} * 1'000'000'000ULL : UINT64_MAX;
    return config;
}
} // namespace wsprrypico::standalone
