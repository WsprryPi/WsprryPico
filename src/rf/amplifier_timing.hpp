#pragma once
#include <cstdint>

namespace wsprrypico::rf {
// Member-local RF-off intervals. They never contribute waveform samples.
struct AmplifierTiming {
    unsigned lead_ms = 200, tail_ms = 200;
    static constexpr unsigned maximum_ms = 1000;
    bool valid() const {
        return lead_ms <= maximum_ms && tail_ms <= maximum_ms;
    }
    std::uint64_t lead_ns() const {
        return std::uint64_t(lead_ms) * 1'000'000;
    }
    std::uint64_t tail_ns() const {
        return std::uint64_t(tail_ms) * 1'000'000;
    }
    bool operator==(const AmplifierTiming&) const = default;
};
// Last admitted job only. Times are monotonic ns sampled after board readback;
// zero means unobserved. This establishes GPIO/register observations, not RF power.
struct AmplifierObservation {
    std::uint64_t epoch = 0, enable_ns = 0, rf_start_ns = 0, rf_off_ns = 0, disable_ns = 0;
    unsigned lead_ms = 0, tail_ms = 0;
    bool configured = false, normal_rf_completion = false;
};
} // namespace wsprrypico::rf
