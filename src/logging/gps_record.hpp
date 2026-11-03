// SPDX-License-Identifier: MIT
#pragma once
#include "logging/logger.hpp"
#include "time/gps_calibration.hpp"

#include <cstdio>

namespace wsprrypico::logging {
// Fixed local-only capture evidence, never raw NMEA, coordinates or credentials.
inline void record_gps_capture(Logger& logger, const time::gps::Observation& observation,
                               const std::optional<time::gps::CycleSnapshot>& cycle, bool admitted,
                               std::uint64_t nominal_nhz, std::uint64_t now) {
    std::array<char, Logger::message_bytes + 1> text{};
    const auto emit = [&](const char* code, int count) {
        if (count > 0 && std::size_t(count) < text.size())
            logger.event(7, code, {text.data(), std::size_t(count)}, now, 0, false);
    };
    emit("GPS_PPS",
         std::snprintf(text.data(), text.size(),
                       "seq=%llu raw_ns=%llu utc_ns=%llu admitted=%u nominal_nhz=%llu",
                       static_cast<unsigned long long>(observation.sequence),
                       static_cast<unsigned long long>(observation.raw_ns),
                       static_cast<unsigned long long>(observation.utc_ns), unsigned(admitted),
                       static_cast<unsigned long long>(nominal_nhz)));
    const auto c = cycle.value_or(time::gps::CycleSnapshot{});
    emit("GPS_COUNT",
         std::snprintf(
             text.data(), text.size(),
             "seq=%llu coherent=%u edges=%llu raw_ns=%llu error_ns=%llu plan=%llu capture=%llu",
             static_cast<unsigned long long>(observation.sequence), unsigned(c.coherent),
             static_cast<unsigned long long>(c.edges), static_cast<unsigned long long>(c.raw_ns),
             static_cast<unsigned long long>(c.uncertainty_ns),
             static_cast<unsigned long long>(c.plan_generation),
             static_cast<unsigned long long>(c.capture_id)));
}
} // namespace wsprrypico::logging
