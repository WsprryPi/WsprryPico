#pragma once
#include "wtp/job_service.hpp"

namespace wsprrypico::time {
// Integer rational arithmetic shared by forward projection and alarm inversion.
// No epoch-sized floating point or target-dependent 128-bit arithmetic.
inline bool scale(std::uint64_t value, std::uint64_t numerator, std::uint64_t denominator,
                  std::uint64_t& result, bool ceil = false) {
    constexpr auto limit = std::numeric_limits<std::uint64_t>::max();
    if (!denominator || numerator > 2'000'000'000ULL || denominator > 2'000'000'000ULL)
        return false;
    const auto q = value / denominator, r = value % denominator;
    if (numerator && q > limit / numerator)
        return false;
    const auto product = r * numerator;
    const auto fraction = product / denominator + (ceil && product % denominator != 0);
    const auto whole = q * numerator;
    if (whole > limit - fraction)
        return false;
    result = whole + fraction;
    return true;
}
inline bool elapsed_utc(std::uint64_t raw, std::int32_t rate_ppb, std::uint64_t& utc,
                        bool ceil = false) {
    if (rate_ppb < -100'000 || rate_ppb > 100'000)
        return false;
    return scale(raw, std::uint64_t(1'000'000'000LL + rate_ppb), 1'000'000'000, utc, ceil);
}
inline bool project(const wtp::ClockSnapshot& anchor, std::uint64_t raw, std::uint64_t& utc) {
    const bool future = raw >= anchor.monotonic_now_ns;
    const auto delta = future ? raw - anchor.monotonic_now_ns : anchor.monotonic_now_ns - raw;
    std::uint64_t elapsed{};
    if (!elapsed_utc(delta, anchor.rate_ppb, elapsed, !future))
        return false;
    if (future) {
        if (elapsed > std::numeric_limits<std::uint64_t>::max() - anchor.utc_now_ns)
            return false;
        utc = anchor.utc_now_ns + elapsed;
    } else {
        if (elapsed > anchor.utc_now_ns)
            return false;
        utc = anchor.utc_now_ns - elapsed;
    }
    return true;
}
inline bool inverse(const wtp::ClockSnapshot& anchor, std::uint64_t utc, std::uint64_t& raw) {
    if (anchor.rate_ppb < -100'000 || anchor.rate_ppb > 100'000)
        return false;
    const bool future = utc >= anchor.utc_now_ns;
    const auto delta = future ? utc - anchor.utc_now_ns : anchor.utc_now_ns - utc;
    std::uint64_t elapsed{};
    // Ceiling for future and floor for past both choose the first raw ns at/after UTC.
    if (!scale(delta, 1'000'000'000, std::uint64_t(1'000'000'000LL + anchor.rate_ppb), elapsed,
               future))
        return false;
    if (future) {
        if (elapsed > std::numeric_limits<std::uint64_t>::max() - anchor.monotonic_now_ns)
            return false;
        raw = anchor.monotonic_now_ns + elapsed;
    } else {
        if (elapsed > anchor.monotonic_now_ns)
            return false;
        raw = anchor.monotonic_now_ns - elapsed;
    }
    return true;
}
inline bool duration_utc_bound(std::uint64_t raw, const wtp::ClockSnapshot& clock,
                               std::uint64_t& duration) {
    if (clock.rate_ppb < -100'000 || clock.rate_ppb > 100'000 ||
        clock.rate_uncertainty_ppb > 100'000)
        return false;
    const auto upper =
        std::max<std::int64_t>(0, std::int64_t(clock.rate_ppb) + clock.rate_uncertainty_ppb);
    return scale(raw, 1'000'000'000 + upper, 1'000'000'000, duration, true);
}
inline bool growth(std::uint64_t age, std::uint64_t ppb, std::uint64_t& uncertainty) {
    return scale(age, ppb, 1'000'000'000, uncertainty, true);
}
} // namespace wsprrypico::time
