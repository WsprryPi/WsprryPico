// SPDX-License-Identifier: MIT
#pragma once
#include "logging/logger.hpp"
#include "wtp/job_service.hpp"

#include <cstdio>
#include <optional>

namespace wsprrypico::logging {
struct TransmissionRecord {
    std::string_view job, utc_source;
    std::uint64_t start_utc_ns;
    wtp::ClockSnapshot clock;
    struct Station {
        std::string_view locator, source;
        std::uint64_t position_raw_ns;
    } station;
    struct Correction {
        std::string_view source;
        std::int32_t ppb;
        std::uint64_t generation, observed_raw_ns;
        std::uint32_t uncertainty_ppb;
    } correction;
};
// Three bounded, linked records at accepted ARM, never per symbol. Transport
// loss/rate limiting retains the logger's explicit sequence/drop accounting.
// Location-bearing provenance stays on local USB; the UDP allowlist is unchanged.
// An opaque controller waveform has no inferred or substituted station locator.
inline void record_transmission(Logger& logger, const TransmissionRecord& r) {
    std::array<char, Logger::message_bytes + 1> text{};
    const auto emit = [&](const char* code, int count) {
        if (count > 0 && std::size_t(count) < text.size())
            logger.event(6, code, {text.data(), std::size_t(count)}, r.clock.monotonic_now_ns,
                         r.clock.utc_now_ns, false);
    };
    emit("TX_TIME",
         std::snprintf(
             text.data(), text.size(),
             "job=%.*s start_ns=%llu source=%.*s age_ns=%llu uncertainty_ns=%llu model=%llu",
             int(r.job.size()), r.job.data(), static_cast<unsigned long long>(r.start_utc_ns),
             int(r.utc_source.size()), r.utc_source.data(),
             static_cast<unsigned long long>(r.clock.sync_age_ns),
             static_cast<unsigned long long>(r.clock.uncertainty_ns),
             static_cast<unsigned long long>(r.clock.model_generation)));
    emit("TX_LOCATION",
         std::snprintf(text.data(), text.size(),
                       "job=%.*s locator=%.*s source=%.*s fix_raw_ns=%llu", int(r.job.size()),
                       r.job.data(), int(r.station.locator.size()), r.station.locator.data(),
                       int(r.station.source.size()), r.station.source.data(),
                       static_cast<unsigned long long>(r.station.position_raw_ns)));
    emit(
        "TX_CORRECTION",
        std::snprintf(
            text.data(), text.size(),
            "job=%.*s source=%.*s ppb=%ld generation=%llu observed_raw_ns=%llu uncertainty_ppb=%lu",
            int(r.job.size()), r.job.data(), int(r.correction.source.size()),
            r.correction.source.data(), static_cast<long>(r.correction.ppb),
            static_cast<unsigned long long>(r.correction.generation),
            static_cast<unsigned long long>(r.correction.observed_raw_ns),
            static_cast<unsigned long>(r.correction.uncertainty_ppb)));
}
} // namespace wsprrypico::logging
