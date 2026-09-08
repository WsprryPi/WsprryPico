#pragma once

#include "rf/wtp_profile.hpp"
#include "time/sntp.hpp"

namespace wsprrypico::standalone {
inline time::DisciplineConfig clock_profile() {
    time::DisciplineConfig config;
    config.synchronized_for_ns = 90'000'000'000ULL;
    config.holdover_for_ns = 180'000'000'000ULL;
    return config;
}

inline wtp::ServiceConfig wtp_profile(bool physical_rf) {
    auto config = rf::wtp_profile(physical_rf ? "pio-dma-gp2" : "inhibited-standalone-simulator");
    config.maximum_arm_uncertainty_ns = time::standalone_max_uncertainty_ns;
    config.maximum_holdover_age_ns = 90'000'000'000ULL;
    return config;
}
} // namespace wsprrypico::standalone
