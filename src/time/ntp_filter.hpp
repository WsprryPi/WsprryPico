#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>

namespace wsprrypico::time {
inline constexpr std::uint64_t ntp_fresh_ns = 90'000'000'000ULL;
struct NtpSample {
    std::uint64_t id = 0, epoch = 0, send_ns = 0, raw_ns = 0, utc_ns = 0;
    std::uint64_t uncertainty_ns = 0, rtt_ns = 0;
    std::uint64_t reference_ns = 0, server_receive_ns = 0, server_send_ns = 0;
    std::uint32_t root_delay = 0, root_dispersion = 0;
    std::uint8_t stratum = 0, leap = 0;
    std::int8_t precision = 0;
};
struct RateEstimate {
    bool qualified = false;
    std::int32_t utc_rate_ppb = 0;
    std::uint32_t uncertainty_ppb = 100'000;
    std::uint64_t generation = 0, sampled_ns = 0, span_ns = 0;
    unsigned samples = 0;
    const char* reason = "startup";
};
std::optional<std::int32_t> oscillator_correction(const RateEstimate& rate);
std::string rate_json(const RateEstimate& rate);
std::string sample_json(const NtpSample& sample);
} // namespace wsprrypico::time
