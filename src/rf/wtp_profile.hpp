#pragma once

#include "rf/waveform.hpp"

#include <string>
#include <utility>

namespace wsprrypico::rf {
// Shared numeric limits for the experimental stream engine and its inhibited
// lifecycle simulator. These bounds do not imply physical RF qualification.
inline wtp::ServiceConfig wtp_profile(std::string engine) {
    wtp::ServiceConfig config;
    config.capability_engine = std::move(engine);
    config.supported_modes = {"wspr", "tone", "qrss", "fskcw", "dfcw"};
    config.minimum_frequency_nhz = minimum_frequency_nhz;
    config.maximum_frequency_nhz = maximum_frequency_nhz;
    config.max_events = max_events;
    config.max_job_duration_ns = max_duration_ns;
    return config;
}
} // namespace wsprrypico::rf
